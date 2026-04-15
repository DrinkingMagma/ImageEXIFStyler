# 核心功能来源声明

本项目的核心图片处理、EXIF水印、品牌Logo与模板化处理思路及代码实现来源于 [leslievan/semi-utils](https://github.com/leslievan/semi-utils)。当前仓库在此基础上整理为一个面向本地使用的桌面应用，重点补充了图形界面以及 Windows 打包流程。

# ImageEXIFStyler

ImageEXIFStyler 是一个用于给照片生成 EXIF 信息边框、水印和展示版式的 Python 桌面工具。它会读取图片中的 EXIF 信息，结合本地 JSON 模板渲染图片，并支持单张预览导出和批量处理。[解压即用]()

项目适合以下场景：

- 给摄影作品自动添加相机、镜头、焦距、光圈、快门、ISO 和拍摄时间等信息。
- 根据照片 EXIF 中的相机品牌自动匹配品牌 Logo。
- 使用模板快速生成统一风格的照片边框、背景模糊、标准水印或自定义版式。
- 批量处理多张照片并按模板名、质量参数自动生成输出文件名。
- 打包为 Windows 可执行程序，带应用 Logo 和运行时资源。

## 界面预览

### 编辑器

编辑器用于导入单张图片、切换模板、查看实时预览并导出结果。

<img src="config/images/editor.png" alt="编辑器界面" width="780">

### 批量处理

批量处理页面用于添加多张图片、统一设置模板和导出参数，并查看每张图片的处理状态。

<img src="config/images/batch%20process.png" alt="批量处理界面" width="780">

### 模板库

模板库集中展示当前可用模板和对应预览图，也可以基于当前模板创建副本。

<img src="config/images/template%20library.png" alt="模板库界面" width="780">

### 设置页

设置页用于调整默认模板、输出目录、导出质量、自动 Logo 等偏好。

<img src="config/images/settings.png" alt="设置页界面" width="780">

## 主要功能

### 单图编辑

程序启动后默认进入编辑器页面。用户可以导入一张图片，选择右侧模板，程序会异步生成实时预览。预览成功后可以导出为 JPEG 或 PNG。

导出文件名会自动附加模板名和质量后缀，例如：

```text
IMG_0001_标准水印_Q100.jpg
```

### 批量处理

批量处理页面支持一次添加多张图片，统一选择模板、导出目录和 JPEG 质量。程序会按推荐线程数并发处理，并在界面中显示每张图片的状态、进度、输出结果和失败信息。

批量导出会尽量保留输入目录结构，避免不同目录下的同名文件互相覆盖。

### 模板库

模板库会读取 `config/templates` 下的 `.json` 文件，并使用 `UI/template_images` 中的同名预览图展示模板。

当前项目包含的模板与示例图如下：

| 模板 | 模板文件 | 示例图 | 说明 |
| --- | --- | --- | --- |
| `标准水印` | `config/templates/标准水印.json` | <img src="UI/template_images/标准水印.jpg" alt="标准水印示例" width="260"> | 经典 EXIF 水印，展示相机型号、镜头、焦距、光圈、快门、ISO、拍摄时间和相机品牌 Logo。 |
| `标准水印2` | `config/templates/标准水印2.json` | <img src="UI/template_images/标准水印2.jpg" alt="标准水印2示例" width="260"> | 在标准水印基础上加入圆角、阴影和留白，更适合社交平台展示。 |
| `背景模糊` | `config/templates/背景模糊.json` | <img src="UI/template_images/背景模糊.jpg" alt="背景模糊示例" width="260"> | 使用原图生成模糊背景，并在前景叠放带参数信息的主体图。 |
| `背景模糊（无EXIF）` | `config/templates/背景模糊（无EXIF）.json` | <img src="UI/template_images/背景模糊（无EXIF）.jpg" alt="背景模糊无EXIF示例" width="260"> | 适合缺少 EXIF 的图片，保留背景模糊版式，减少对相机参数字段的依赖。 |
| `背景模糊（尼康专用）` | `config/templates/背景模糊（尼康专用）.json` | <img src="UI/template_images/背景模糊（尼康专用）.jpg" alt="背景模糊尼康专用示例" width="260"> | 面向尼康照片的定制样式，突出 Nikon/Z 系列信息并搭配背景模糊效果。 |

用户可以在模板库中基于当前模板创建副本，再编辑 `config/templates` 下对应的 JSON 文件进行扩展。

### 设置页

设置页用于管理常用运行参数：

- 默认模板
- 输出目录
- JPEG 导出质量
- 自动品牌 Logo 开关
- 硬件加速开关占位配置

自动品牌 Logo 开关会影响模板中的 `auto_logo()`：关闭后，使用 `auto_logo()` 的模板不会再自动注入相机品牌 Logo。

### 品牌 Logo

项目有两类 Logo：

- 应用品牌 Logo：位于 `UI/logo.svg` 和 `UI/logo.ico`，用于运行时界面、窗口图标和打包后的 exe 图标。
- 相机品牌 Logo：位于 `config/logos`，用于模板水印中的相机品牌识别。

`auto_logo()` 会根据 EXIF 的 `Make` 字段从 `config/logos` 中匹配品牌文件，例如 Canon、Nikon、Sony、Fujifilm、Leica、DJI 等。

## 工作原理

ImageEXIFStyler 的图片渲染流程由 JSON 模板描述。模板会先经过 Jinja2 渲染，再作为 JSON 数组解析成处理流水线。

模板中可以读取：

- 当前图片路径
- 文件名
- 图片尺寸
- EXIF 字典
- 自动品牌 Logo 路径

常用表达式示例：

```jinja2
{{ exif.Make|default('-') }}
{{ exif.Model|default('') }}
{{ exif.FocalLengthIn35mmFormat|default('-') }}
{{ exif.FNumber|default('-') }}
{{ exif.ShutterSpeed or exif.ShutterSpeedValue|default('-') }}
{{ auto_logo()|replace('\\', '/') }}
```

模板处理器主要分为三类：

| 类型  | 说明                    | 示例处理器                                                                        |
| --- | --------------------- | ---------------------------------------------------------------------------- |
| 生成器 | 创建纯色、渐变、文字或外部图片图层     | `solid_color`、`gradient_color`、`rich_text`、`multi_rich_text`、`image`         |
| 滤镜  | 对图像做裁剪、缩放、圆角、阴影、水印等处理 | `blur`、`resize`、`trim`、`margin`、`watermark`、`rounded_corner`、`shadow`、`crop` |
| 合并器 | 拼接或叠放多张图层             | `concat`、`alignment`                                                         |

更详细的模板语法见 [config/templates/readme.md](config/templates/readme.md)。

## 项目结构

```text
ImageEXIFStyler/
  main.py                  程序入口
  requirements.txt         Python 依赖版本锁定文件
  build_exe.ps1            Windows 打包脚本
  PACKAGING.md             打包说明
  core/                    配置、日志、EXIF、模板加载和 Jinja2 辅助函数
  processor/               图片处理器、生成器、滤镜和合并器
  UI/                      桌面界面
    logo.svg               运行时应用 Logo
    logo.ico               exe 图标和窗口图标
    editor/                单图编辑页面
    batch/                 批量处理页面
    settings/              设置页面
    template_library/      模板库页面
    shared/                Qt 兼容层、主题、渲染服务和公共工具
    template_images/       模板预览图
  config/
    config.ini             运行配置
    images/                README 使用的软件界面截图
    templates/             JSON 模板
    logos/                 相机品牌 Logo
    fonts/                 模板字体
  input/                   默认输入目录
  output/                  默认输出目录
  logs/                    日志目录
```

## 运行环境

项目当前默认使用 Conda 环境 `ies`。仓库提供的 `requirements.txt` 按当前 `ies` 环境中的版本锁定，包含源码运行和 Windows 打包所需的 Python 包。

主要依赖版本：

- Python 3.9+
- PySide6 `6.10.3`
- Pillow `11.3.0`
- Jinja2 `3.1.6`
- PyInstaller `6.19.0`（仅打包需要）
- pillow-heif `1.1.1`（可选，仅 HEIC 输入需要）
- loguru `0.7.3`（可选，未安装时会回退到标准 logging）

当前代码会优先尝试 PySide6，如果不可用再尝试 PyQt5。`requirements.txt` 按当前项目环境锁定为 PySide6；PyQt5 只是源码层面的备用兼容路径。

安装依赖：

```powershell
conda create -n ies python=3.9
conda activate ies
python -m pip install -r requirements.txt
```

## 本地运行

```powershell
conda activate ies
python main.py
```

如果没有使用 `ies` 环境，`main.py` 会阻止启动。需要修改环境名时，可调整 `main.py` 中的：

```python
REQUIRED_CONDA_ENV = "ies"
```

## 打包

Windows 下使用项目内的 PowerShell 脚本打包：

```powershell
.\build_exe.ps1 -Clean
```

默认打包行为：

- 使用 PyInstaller onedir 模式生成 `dist/ImageEXIFStyler/ImageEXIFStyler.exe`
- 将 Python、Qt、Pillow 等运行依赖拆到 `_internal` 目录中的 DLL 和支持文件，减小 exe 本体大小
- 设置 exe 图标为 `UI/logo.ico`
- 复制 `config`、`UI/template_images`、`UI/logo.*` 等运行时资源到 `dist/ImageEXIFStyler`
- 创建 `input`、`output`、`logs` 目录
- 默认排除 HEIC 支持以减小体积
- 默认排除 `numpy`、`cv2`、`matplotlib`、`scipy`、`loguru`、`IPython`、`ipykernel` 和未使用的 Qt 绑定等可选模块

默认目录包结构：

```text
dist/
  ImageEXIFStyler/
    ImageEXIFStyler.exe
    _internal/
      *.dll
      ...
    config/
    UI/
    input/
    output/
    logs/
```

发布或移动程序时需要复制整个 `dist/ImageEXIFStyler` 文件夹，不能只复制 `ImageEXIFStyler.exe`。`_internal` 中的 DLL 和运行时文件是程序启动所必需的。

当前默认 onedir 打包结果中，exe 本体约 `3.6 MiB`，整个目录包约 `194 MiB`。目录包总大小可能比 onefile 更大，因为依赖文件不再压缩进单个 exe，但 exe 本体会显著变小。

如果需要旧的一体化单文件 exe：

```powershell
.\build_exe.ps1 -Clean -OneFile
```

单文件模式会把运行时归档附加进 exe，因此 exe 本体会明显更大。

如果需要打包 HEIC 输入支持：

```powershell
.\build_exe.ps1 -Clean -IncludeHeif
```

如果需要调试启动错误，可以显示控制台窗口：

```powershell
.\build_exe.ps1 -Clean -Console
```

如果需要复制到指定安装目录：

```powershell
.\build_exe.ps1 -Clean -InstallDir "D:\Apps\ImageEXIFStyler"
```

更多说明见 [PACKAGING.md](PACKAGING.md)。

## 自定义模板

模板文件位于 `config/templates`。每个 `.json` 文件就是一个模板，文件名就是 UI 中显示的模板名称。

新增模板的推荐流程：

1. 复制一个现有模板，例如复制 `标准水印.json` 为 `我的模板.json`。
2. 修改 JSON 中的处理器顺序、文字内容、颜色、字体、边距和 Logo 设置。
3. 如需读取 EXIF，使用 Jinja2 表达式并添加兜底值。
4. 如需新增字体，放入 `config/fonts`。
5. 如需新增相机品牌 Logo，放入 `config/logos`。
6. 回到 UI 重新选择模板并预览。

模板渲染后的结果必须是合法 JSON 数组。常见问题通常来自 JSON 逗号、引号、`processor_name` 拼写、`select` 索引或图片路径错误。

## 输出与日志

默认输出目录为 `output`，日志目录为 `logs`。相关配置保存在 `config/config.ini`。

日志默认按日期写入：

```text
logs/app_YYYY-MM-DD.log
```

## 注意事项

- EXIF 字段并不总是存在，模板中建议使用 `default` 或 `or` 处理缺失值。
- 默认打包不包含 HEIC 支持；需要处理 `.heic` 文件时请使用 `-IncludeHeif` 打包。
- Windows 资源管理器可能缓存 exe 图标。如果刚打包后仍显示旧图标，可以重命名 exe、刷新目录或重启资源管理器。
- 当前硬件加速设置仅保存开关状态，渲染流程暂未启用硬件加速。

## 致谢

感谢 [leslievan/semi-utils](https://github.com/leslievan/semi-utils) 提供核心功能来源和处理思路。本项目在其基础上面向本地桌面使用场景做了界面化和打包整理。
