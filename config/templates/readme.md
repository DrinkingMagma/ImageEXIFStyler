# 模板 JSON 配置说明

`config/templates` 目录中的每个 `.json` 文件都是一个图片处理模板。文件名就是 UI 中显示的模板名称，例如 `标准水印.json` 对应模板名 `标准水印`。

模板文件会先经过 Jinja2 渲染，再作为 JSON 解析成处理流水线。因此，模板里既可以写普通 JSON 值，也可以写 `{{ ... }}` 表达式来读取 EXIF、图片尺寸或自动 logo。需要注意的是，渲染后的结果必须是合法 JSON 数组。

## 基本结构

模板渲染后的结果必须是一个 JSON 数组，数组中的每一项是一个处理节点：

```json
[
  {
    "processor_name": "rounded_corner",
    "border_radius": "{{vh(2)}}"
  },
  {
    "processor_name": "shadow",
    "shadow_radius": "{{vh(1)}}",
    "shadow_color": "black"
  }
]
```

通用字段：

| 字段 | 说明 | 取值 |
| --- | --- | --- |
| `processor_name` | 必填。处理器名称，决定当前节点执行什么功能。 | 见下方处理器列表 |
| `select` | 可选。指定当前节点使用哪些历史输出作为输入。 | 必须是 JSON 字符串，例如 `"[2,3,4]"` |
| `buffer_path` | 可选。指定要加载的图片路径，常用于重新读取原图。 | 路径字符串数组，例如 `["{{file_path}}"]` |
| `save_buffer` | 可选。是否保存当前节点的中间结果，主要用于调试。 | JSON 布尔值 `true` / `false`，不要写成字符串 |
| `output` | 可选。保存中间结果的目录。 | 路径字符串，默认 `./tmp` |

默认情况下，每个非合并处理器会接收上一节点的输出。合并处理器不写 `select` 时，会按内部历史缓冲区自动取图：第一个合并器会拿到原始输入图像和它之前所有节点的输出，后续合并器会从上一个合并器的输出开始继续收集。为了避免合并到不需要的图层，复杂模板建议显式写 `select`。

`select` 的索引从 `0` 开始：`0` 表示原始输入图像，`1` 表示第一个节点的输出，`2` 表示第二个节点的输出，以此类推。

## Jinja2 可用变量和函数

| 名称 | 说明 | 示例 |
| --- | --- | --- |
| `exif` | 当前图片的 EXIF 字典。 | `{{ exif.Make|default('-') }}` |
| `filename` | 当前图片文件名，不含扩展名。 | `{{ filename }}` |
| `file_dir` | 当前图片所在目录。 | `{{ file_dir }}` |
| `file_path` | 当前处理图片路径。预览时可能是临时缩略图路径。 | `{{ file_path }}` |
| `files` | 当前处理图片路径列表。 | `{{ files[0] }}` |
| `vw(percent)` | 按 EXIF 中的 `ImageWidth` 计算像素值。 | `{{ vw(10) }}` 表示宽度的 10% |
| `vh(percent)` | 按 EXIF 中的 `ImageHeight` 计算像素值。 | `{{ vh(3) }}` 表示高度的 3% |
| `auto_logo(brand=None)` | 根据 EXIF `Make` 或指定品牌返回 `config/logos` 下匹配的 logo 路径；配置关闭 logo 时返回空字符串。 | `{{ auto_logo()|replace('\\', '/') }}` |

常用 EXIF 字段：

| 字段 | 含义 |
| --- | --- |
| `Make` | 相机/设备品牌 |
| `Model` | 相机/设备型号 |
| `LensModel` | 镜头型号 |
| `FNumber` | 光圈，例如 `F2.8` |
| `ExposureTime` / `ShutterSpeed` / `ShutterSpeedValue` | 快门速度，例如 `1/125` |
| `ISO` / `ISOSpeedRatings` | ISO |
| `FocalLength` | 原始焦距 |
| `FocalLengthIn35mmFormat` | 35mm 等效焦距 |
| `DateTimeOriginal` / `DateTime` / `DateTimeDigitized` | 拍摄或写入时间 |
| `ImageWidth` / `ImageHeight` / `ImageSize` | 图片尺寸 |

提示：EXIF 字段可能不存在，建议使用 `default` 或 `or` 设置兜底值，例如：

```jinja2
{{ exif.LensModel|default('-') }}
{{ exif.ShutterSpeed or exif.ShutterSpeedValue|default('-') }}
```

## 值类型约定

| 类型 | 说明 | 示例 |
| --- | --- | --- |
| 数字 | 多数宽高、半径、间距字段会转换为 `int` 或 `float`，可写数字，也可写 Jinja 表达式字符串；`gradient_color` 的 `width` / `height` 使用原始值，建议写成 JSON 数字。 | `100`、`"{{vh(2)}}"`、`{{vw(50)}}` |
| 布尔值 | 优先使用 JSON 布尔值。`trim`、`is_bold`、`trim_left`、`trim_right`、`trim_top`、`trim_bottom` 支持 `"false"`、`"0"` 等字符串；`save_buffer` 等通用字段不要写成字符串。 | `true`、`false` |
| 颜色 | 支持颜色名、十六进制、RGBA 十六进制、RGB/RGBA 数组或字符串。 | `"white"`、`"#242424"`、`"#ffffff00"`、`"255,255,255,128"` |
| 字体 | 相对路径会从 `config/fonts` 下查找，也可以写绝对路径。 | `"AlibabaPuHuiTi-2-85-Bold.otf"` |
| 图片/logo 路径 | 建议使用绝对路径或 Jinja 返回的路径；项目内路径通常相对启动目录解析。 | `"{{auto_logo()|replace('\\', '/')}}"` |
| JSON 字符串 | 某些字段会再次 `json.loads`，需要写成字符串。 | `"select": "[2,3,4]"`、`"offset": "[0, -{{vh(3)}}]"`、`"weights": "[100,-100]"`、`"offsets": "[[0,0],[0,-20]]"` |

## 处理器参数

### 生成器

生成器会创建新图像或文字图像。

| `processor_name` | 功能 | 参数 |
| --- | --- | --- |
| `solid_color` | 生成纯色图片。 | `width`、`height`、`color` |
| `gradient_color` | 生成渐变图片。 | `width`、`height`、`start_color`、`end_color`、`direction`、`interpolate_method` |
| `rich_text` | 生成单段文字图片。 | `text`、`font_path`、`height`、`color`、`is_bold`、`trim` |
| `multi_rich_text` | 将多段文字横向拼成一张文字图片。 | `text_segments`、`text_alignment`、`text_spacing`、`height` |
| `image` | 从路径读取图片。 | `path`，可为单个路径字符串或路径数组 |

`gradient_color.direction` 可取：`horizontal`、`vertical`、`diagonal`、`radial`。

`gradient_color.interpolate_method` 可取：`linear`、`ease_in`、`ease_out`、`ease_in_out`。

`gradient_color.width` 和 `gradient_color.height` 如果使用 Jinja 表达式，建议不要加引号，例如：

```jinja2
{
  "processor_name": "gradient_color",
  "width": {{vw(100)}},
  "height": {{vh(100)}},
  "start_color": "#000000",
  "end_color": "#ffffff",
  "direction": "vertical"
}
```

`multi_rich_text.text_alignment` 使用与 `concat.alignment` 相同的取值，未填写时按 `bottom` 处理；`text_spacing` 未填写时为 `0`，`height` 未填写时为 `100`。

`text_segments` 中每一段支持：

```json
{
  "text": "NIKON",
  "font_path": "AlibabaPuHuiTi-2-85-Bold.otf",
  "color": "white",
  "is_bold": true,
  "trim": true
}
```

### 滤镜

滤镜会处理输入图像。

| `processor_name` | 功能 | 参数 |
| --- | --- | --- |
| `blur` | 高斯模糊。 | `blur_radius`，默认 `5` |
| `resize` | 缩放图片。 | `width`、`height`、`scale` 三种方式任选；同时给 `width` 和 `height` 时会强制缩放到指定尺寸 |
| `trim` | 裁掉四周背景/透明边。 | `trim_left`、`trim_right`、`trim_top`、`trim_bottom`，默认均为 `true` |
| `margin` | 给图片增加边距。 | `left_margin`、`right_margin`、`top_margin`、`bottom_margin`、`margin_color` |
| `margin_with_ratio` | 自动补边到指定比例。 | `ratio`，例如 `"3:2"`、`"16:9"`；未填写时使用 EXIF 中的 `ImageWidth:ImageHeight`；可配合 `margin_color` |
| `watermark` | 在底部增加水印信息栏。 | 见下方水印参数 |
| `watermark_with_timestamp` | 在图像右下附近叠加文字水印。 | 同 `multi_rich_text`，可额外设置 `height` |
| `rounded_corner` | 给图像添加圆角透明蒙版。 | `border_radius` |
| `shadow` | 给图像添加投影。 | `shadow_color`、`shadow_radius` |
| `crop` | 居中裁剪并支持偏移。 | `width`、`height`、`offset`，例如 `"[0, -{{vh(3)}}]"` |

`watermark` 参数：

| 参数 | 说明 |
| --- | --- |
| `color` | 水印底部画布颜色，默认 `white` |
| `delimiter_color` | logo 与右侧文字之间的分割线颜色，默认 `black` |
| `delimiter_width` | 分割线宽度，默认约为图片宽度的 `0.3%` |
| `left_margin` / `right_margin` / `top_margin` / `bottom_margin` | 水印画布边距；`bottom_margin` 默认约为图片高度的 `12%` |
| `middle_spacing` | 上下两行文字间距，默认约为 `bottom_margin` 的 `5%` |
| `right_alignment` | 右侧两行文字的横向对齐。当前实现只对 `left` 做特殊处理；未填写、`right`、`center` 都按右对齐逻辑处理 |
| `left_top` / `left_bottom` | 必填。左侧上/下文字处理器配置，通常用 `rich_text` 或 `multi_rich_text` |
| `right_top` / `right_bottom` | 必填。右侧上/下文字处理器配置，通常用 `rich_text` |
| `left_logo` / `right_logo` / `center_logo` | logo 图片路径。空字符串、`none`、`null` 会被忽略 |
| `center_logo_height` | 中央 logo 高度；不填时使用底部水印区域高度 |

示例：

```json
{
  "processor_name": "watermark",
  "color": "white",
  "delimiter_color": "#D8D8D6",
  "right_alignment": "left",
  "right_logo": "{{auto_logo()|replace('\\', '/')}}",
  "left_top": {
    "processor_name": "multi_rich_text",
    "text_segments": [
      {
        "text": "{{ (exif.Make|default('') + ' ' + exif.Model|default(''))|trim|default('-') }}",
        "font_path": "AlibabaPuHuiTi-2-85-Bold.otf",
        "color": "black",
        "is_bold": true
      }
    ]
  },
  "left_bottom": {
    "processor_name": "rich_text",
    "text": "{{ exif.LensModel|default('-') }}",
    "color": "#242424"
  },
  "right_top": {
    "processor_name": "rich_text",
    "text": "{{ exif.FocalLengthIn35mmFormat|default('-') }} {{ exif.FNumber|default('-') }} ISO{{ exif.ISO|default('0') }}",
    "color": "#242424"
  },
  "right_bottom": {
    "processor_name": "rich_text",
    "text": "{{ exif.DateTimeOriginal|default('-') }}",
    "color": "#242424"
  }
}
```

### 合并器

合并器会把多张图合成一张图。

| `processor_name` | 功能 | 参数 |
| --- | --- | --- |
| `concat` | 按水平或垂直方向拼接多张图。 | `direction`、`alignment`、`spacing`、`background` |
| `alignment` | 将多张图叠放到同一画布中。 | `horizontal_alignment`、`vertical_alignment`、`background`、`offsets`、`weights` |

通用对齐取值：

| 取值 | 含义 |
| --- | --- |
| `start` | 起始侧 |
| `center` | 居中 |
| `end` | 结束侧 |
| `top` / `middle` / `bottom` | 垂直语义别名，分别等价于 `start` / `center` / `end` |
| `left` / `right` | 水平语义别名，分别等价于 `start` / `end` |

`concat.direction` 可取：`horizontal`、`vertical`。

`alignment.offsets` 和 `alignment.weights` 需要写成 JSON 字符串：

```json
{
  "processor_name": "alignment",
  "select": "[5,7]",
  "weights": "[100,-100]",
  "offsets": "[[0,0],[0,-20]]"
}
```

`weights` 数值越小越先绘制，后绘制的图会覆盖前面的图。

`offsets` 中的偏移值会在粘贴前取反：`[10,20]` 会让对应图层相对对齐基准向左、向上移动，`[-10,-20]` 会向右、向下移动。

## 如何自定义模板

1. 复制一个现有模板，例如复制 `标准水印.json` 为 `我的模板.json`。
2. 保持模板渲染后的内容为合法 JSON 数组，编码使用 UTF-8。UI 会按文件名识别模板，模板名就是 `我的模板`。
3. 修改文字内容时优先使用 `default` 处理缺失 EXIF，例如 `{{ exif.Model|default('-') }}`。
4. 修改尺寸、间距、圆角、模糊半径时，建议优先使用 `vw()` / `vh()`，这样模板能适配不同分辨率。
5. 新增字体时放到 `config/fonts`，并在 `font_path` 中填写文件名；新增 logo 时放到 `config/logos`，并在模板中写入路径或使用 `auto_logo()`。
6. 如果需要复杂效果，可以按顺序叠加多个处理器，并用 `select` 指定历史输出参与拼接或叠放。
7. 保存后在 UI 的模板库或编辑器中重新选择模板进行预览。如果模板无法渲染，优先检查 JSON 语法、`processor_name` 拼写、`select` 索引、颜色格式和字体/logo 路径。

## 常见模板片段

给主图增加圆角和阴影：

```json
[
  {
    "processor_name": "rounded_corner",
    "border_radius": "{{vh(2)}}"
  },
  {
    "processor_name": "shadow",
    "shadow_radius": "{{vh(1)}}",
    "shadow_color": "black"
  }
]
```

生成两行文字并垂直拼接：

```json
[
  {
    "processor_name": "rich_text",
    "text": "{{ exif.Make|default('-') }} {{ exif.Model|default('') }}",
    "font_path": "AlibabaPuHuiTi-2-85-Bold.otf",
    "height": "{{vh(3)}}",
    "trim": true,
    "color": "white"
  },
  {
    "processor_name": "rich_text",
    "text": "{{ exif.FocalLengthIn35mmFormat|default('-') }} {{ exif.FNumber|default('-') }} ISO{{ exif.ISO|default('0') }}",
    "font_path": "AlibabaPuHuiTi-2-45-Light.otf",
    "height": "{{vh(3)}}",
    "trim": true,
    "color": "white"
  },
  {
    "processor_name": "concat",
    "alignment": "center",
    "spacing": "{{vh(2)}}",
    "direction": "vertical",
    "select": "[1,2]"
  }
]
```
