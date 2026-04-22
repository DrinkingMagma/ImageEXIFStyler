# 模板 JSON 配置说明

`config/templates` 目录下的每个 `.json` 文件都是一个模板。文件名去掉 `.json` 后，就是 UI 中显示的模板名称。

模板文件会先经过 Jinja2 渲染，再作为 JSON 解析成处理流水线，所以模板里既可以写普通 JSON，也可以写 `{{ ... }}` 表达式。

要求：

- 文件编码使用 `UTF-8`
- 渲染后的最终结果必须是合法的 JSON 数组
- 数组中的每一项都是一个处理节点

## 1. 基本结构

```json
[
  {
    "processor_name": "rounded_corner",
    "border_radius": "{{ vh(2) }}"
  },
  {
    "processor_name": "shadow",
    "shadow_radius": "{{ vh(1) }}",
    "shadow_color": "black"
  }
]
```

处理顺序就是数组顺序。前一个节点的输出，会成为后一个节点的输入。

## 2. 通用字段

所有节点都支持以下通用字段：

| 字段 | 是否必填 | 含义 | 取值说明 |
| --- | --- | --- | --- |
| `processor_name` | 是 | 当前节点使用的处理器名称 | 必须是已注册处理器名，例如 `rich_text`、`shadow`、`alignment` |
| `select` | 否 | 指定当前节点从历史输出里取哪些图层作为输入 | 必须是 JSON 字符串，例如 `"[0,2]"` |
| `buffer_path` | 否 | 重新从磁盘加载图片作为输入 | 通常写成路径数组，例如 `["{{ file_path }}"]` |
| `save_buffer` | 否 | 是否保存当前节点的中间结果，方便调试 | JSON 布尔值：`true` / `false` |
| `output` | 否 | 中间结果保存目录 | 路径字符串，默认 `./tmp` |

### 2.1 `select` 的索引规则

`select` 的索引从 `0` 开始：

- `0`：原始输入图像
- `1`：第一个节点的输出
- `2`：第二个节点的输出
- 以此类推

示例：

```json
{
  "processor_name": "alignment",
  "select": "[0,3]"
}
```

表示把“原图”和“第 3 个节点的输出”叠加。

注意：

- `select` 不是 JSON 数组，而是“JSON 字符串”
- 如果不写 `select`：
  - 普通处理器默认接收“上一个节点”的输出
  - 合并类处理器会按内部规则收集最近一段缓冲区
- 复杂模板建议显式写 `select`，避免拿错图层

## 3. Jinja2 可用变量与函数

模板渲染时可直接使用以下上下文：

| 名称 | 含义 | 示例 |
| --- | --- | --- |
| `exif` | 当前图片的 EXIF 字典 | `{{ exif.Make|default('-') }}` |
| `filename` | 当前文件名，不含扩展名 | `{{ filename }}` |
| `file_dir` | 当前文件所在目录 | `{{ file_dir }}` |
| `file_path` | 当前处理图片路径 | `{{ file_path }}` |
| `files` | 当前处理图片路径列表 | `{{ files[0] }}` |
| `template_inputs` | 当前模板的自定义输入值 | `{{ template_inputs.custom_text|default('Hello World!') }}` |
| `vw(percent)` | 按 `ImageWidth` 计算像素值 | `{{ vw(10) }}` 表示宽度的 10% |
| `vh(percent)` | 按 `ImageHeight` 计算像素值 | `{{ vh(3) }}` 表示高度的 3% |
| `auto_logo(brand=None)` | 根据品牌自动匹配 `config/logos` 中的 logo | `{{ auto_logo()|replace('\\', '/') }}` |

`auto_logo()` 规则：

- 优先根据传入 `brand`
- 未传入时使用 `exif.Make`
- 若配置中关闭 logo，返回空字符串
- 找不到时尝试返回 `config/logos/default.png`

## 4. 常用 EXIF 字段

| 字段 | 含义 |
| --- | --- |
| `Make` | 相机/设备品牌 |
| `Model` | 相机/设备型号 |
| `LensModel` | 镜头型号 |
| `FNumber` | 光圈，如 `F2.8` |
| `ExposureTime` / `ShutterSpeed` / `ShutterSpeedValue` | 快门，如 `1/125` |
| `ISO` / `ISOSpeedRatings` | ISO |
| `FocalLength` | 原始焦距，如 `50mm` |
| `FocalLengthIn35mmFormat` | 35mm 等效焦距 |
| `DateTimeOriginal` / `DateTime` / `DateTimeDigitized` | 时间 |
| `ImageWidth` / `ImageHeight` / `ImageSize` | 图片尺寸 |

建议所有 EXIF 读取都带兜底：

```jinja2
{{ exif.LensModel|default('-') }}
{{ exif.ShutterSpeed or exif.ShutterSpeedValue|default('-') }}
```

## 5. 值类型与写法规则

### 5.1 数字

多数数值字段最终会被转成 `int` 或 `float`。

常见写法：

- 直接写 JSON 数字：`100`
- 写成 Jinja 表达式结果：`{{ vh(3) }}`
- 某些字段也能接受字符串数字：`"100"`

建议：

- `solid_color.width / height`
- `gradient_color.width / height`

这类字段优先输出成 JSON 数字，不要额外包引号。

### 5.2 布尔值

优先使用 JSON 布尔值：

- `true`
- `false`

部分字段也兼容字符串形式：

- `"false"`
- `"0"`
- `"no"`
- `"off"`

但通用字段如 `save_buffer` 仍建议只写真正的 JSON 布尔值。

### 5.3 颜色

颜色字段支持以下形式：

- 颜色名：`"white"`
- 十六进制 RGB：`"#242424"`
- 十六进制 RGBA：`"#ffffff00"`
- RGB 字符串：`"255,255,255"`
- RGBA 字符串：`"255,255,255,128"`
- 数组或元组字符串：`"(255,255,255,128)"`、`"[255,255,255,128]"`

### 5.4 字体路径

`font_path` 支持：

- 相对路径：从 `config/fonts` 下查找
- 绝对路径：直接使用

示例：

```json
"font_path": "HFIntimate-2.ttf"
```

### 5.5 需要写成 JSON 字符串的字段

以下字段内部会再次调用 `json.loads`，所以必须写成字符串：

| 字段 | 示例 |
| --- | --- |
| `select` | `"[0,2]"` |
| `offset` | `"[0, -20]"` |
| `offsets` | `"[ [0,0], [0,-20] ]"` |
| `weights` | `"[100,-100]"` |

## 6. 处理器列表与参数说明

### 6.1 生成器类

生成器会“创建新图像”或“读取外部图像”。

#### `solid_color`

生成纯色图。

| 参数 | 是否必填 | 含义 | 取值 |
| --- | --- | --- | --- |
| `width` | 是 | 画布宽度 | 正整数像素 |
| `height` | 是 | 画布高度 | 正整数像素 |
| `color` | 是 | 填充颜色 | 见颜色写法 |

示例：

```json
{
  "processor_name": "solid_color",
  "width": 1200,
  "height": 800,
  "color": "#101010"
}
```

#### `gradient_color`

生成渐变背景。

| 参数 | 是否必填 | 含义 | 取值 |
| --- | --- | --- | --- |
| `width` | 是 | 画布宽度 | 正整数像素 |
| `height` | 是 | 画布高度 | 正整数像素 |
| `start_color` | 是 | 起始颜色 | 见颜色写法 |
| `end_color` | 是 | 结束颜色 | 见颜色写法 |
| `direction` | 否 | 渐变方向 | `horizontal` / `vertical` / `diagonal` / `radial`，默认 `horizontal` |
| `interpolate_method` | 否 | 渐变插值方式 | `linear` / `ease_in` / `ease_out` / `ease_in_out`，默认 `linear` |

#### `rich_text`

生成单段文字图层。

| 参数 | 是否必填 | 含义 | 取值 |
| --- | --- | --- | --- |
| `text` | 是 | 文字内容 | 字符串 |
| `font_path` | 否 | 字体文件 | 相对 `config/fonts` 或绝对路径 |
| `height` | 否 | 目标文字高度 | 数字，默认 `100` |
| `color` | 否 | 文字颜色 | 默认 `black` |
| `is_bold` | 否 | 加粗模式 | 布尔值；当前实现是额外放大约 1.13 倍，不会自动切换粗体字体文件 |
| `trim` | 否 | 是否裁掉文字上下透明留白 | 布尔值；当前只裁上边和下边 |

说明：

- 空文本会被替换成单个空格，避免生成失败
- 推荐配合透明背景叠加使用

#### `multi_rich_text`

把多段文字横向拼成一张文字图。

| 参数 | 是否必填 | 含义 | 取值 |
| --- | --- | --- | --- |
| `text_segments` | 是 | 文字片段列表 | 数组，每项见下表 |
| `text_alignment` | 否 | 各片段在横向拼接时的垂直对齐方式 | 与 `concat.alignment` 相同，默认 `bottom` |
| `text_spacing` | 否 | 片段间距 | 数字，默认 `0` |
| `height` | 否 | 所有片段统一使用的高度 | 数字，默认 `100` |

`text_segments` 每项支持：

| 字段 | 是否必填 | 含义 |
| --- | --- | --- |
| `text` | 是 | 文字内容 |
| `font_path` | 否 | 字体文件 |
| `color` | 否 | 文字颜色 |
| `is_bold` | 否 | 是否加粗模式 |
| `trim` | 否 | 是否裁上下透明边 |

注意：

- 子项里的 `height` 最终会被外层 `height` 覆盖
- 适合做品牌名 + 参数串的组合标题

#### `image`

从磁盘读取图片。

| 参数 | 是否必填 | 含义 | 取值 |
| --- | --- | --- | --- |
| `path` | 是 | 要加载的图片路径 | 单个字符串，或字符串数组 |

示例：

```json
{
  "processor_name": "image",
  "path": "{{ auto_logo()|replace('\\', '/') }}"
}
```

### 6.2 滤镜类

滤镜会处理输入图像。

#### `blur`

高斯模糊。

| 参数 | 是否必填 | 含义 | 取值 |
| --- | --- | --- | --- |
| `blur_radius` | 否 | 模糊半径 | 数字，默认 `5` |

#### `resize`

缩放图像。

| 参数 | 是否必填 | 含义 | 取值 |
| --- | --- | --- | --- |
| `width` | 否 | 目标宽度 | 数字 |
| `height` | 否 | 目标高度 | 数字 |
| `scale` | 否 | 按比例缩放 | 数字，例如 `2`、`0.5` |

规则：

- 同时给 `width` 和 `height`：强制缩放到指定尺寸
- 只给 `width`：按宽度等比缩放
- 只给 `height`：按高度等比缩放
- 只给 `scale`：按倍数等比缩放

#### `trim`

裁掉四周与背景近似的边缘。

| 参数 | 是否必填 | 含义 | 取值 |
| --- | --- | --- | --- |
| `trim_left` | 否 | 是否裁左边 | 布尔值，默认 `true` |
| `trim_right` | 否 | 是否裁右边 | 布尔值，默认 `true` |
| `trim_top` | 否 | 是否裁上边 | 布尔值，默认 `true` |
| `trim_bottom` | 否 | 是否裁下边 | 布尔值，默认 `true` |

说明：

- 透明图会按四角颜色估算背景
- 适合清理文字图层或透明边

#### `margin`

给图片加四边距。

| 参数 | 是否必填 | 含义 | 取值 |
| --- | --- | --- | --- |
| `left_margin` | 否 | 左边距 | 数字，默认 `0` |
| `right_margin` | 否 | 右边距 | 数字，默认 `0` |
| `top_margin` | 否 | 上边距 | 数字，默认 `0` |
| `bottom_margin` | 否 | 下边距 | 数字，默认 `0` |
| `margin_color` | 否 | 边距填充色 | 默认 `white` |

如果想看到后方图层，应把 `margin_color` 设为透明，例如：

```json
"margin_color": "#00000000"
```

#### `margin_with_ratio`

自动补边到目标比例。

| 参数 | 是否必填 | 含义 | 取值 |
| --- | --- | --- | --- |
| `ratio` | 否 | 目标宽高比 | 字符串，例如 `"3:2"`、`"16:9"` |
| `margin_color` | 否 | 补边颜色 | 与 `margin` 相同 |

规则：

- 图片过宽时补上下边
- 图片过高时补左右边
- 不写 `ratio` 时，回退到 EXIF 中的原始比例

#### `watermark`

在主图底部生成一整块水印栏。

| 参数 | 是否必填 | 含义 | 取值 |
| --- | --- | --- | --- |
| `color` | 否 | 水印栏底色 | 默认 `white` |
| `delimiter_color` | 否 | 右侧 logo 分隔线颜色 | 默认 `black` |
| `delimiter_width` | 否 | 分隔线宽度 | 默认约为主图宽度的 `0.3%` |
| `left_margin` | 否 | 左外边距 | 数字，默认 `0` |
| `right_margin` | 否 | 右外边距 | 数字，默认 `0` |
| `top_margin` | 否 | 上外边距 | 数字，默认 `0` |
| `bottom_margin` | 否 | 底部水印区高度 | 默认约为主图高度的 `12%` |
| `middle_spacing` | 否 | 上下两行文字间距 | 默认约为 `bottom_margin * 5%` |
| `right_alignment` | 否 | 右侧上下两行的横向对齐 | `left` / `center` / `right`；当前只有 `left` 会触发特殊处理，其余都按右对齐逻辑 |
| `left_top` | 是 | 左上文字节点 | 一般是 `rich_text` 或 `multi_rich_text` 配置对象 |
| `left_bottom` | 是 | 左下文字节点 | 同上 |
| `right_top` | 是 | 右上文字节点 | 同上 |
| `right_bottom` | 是 | 右下文字节点 | 同上 |
| `left_logo` | 否 | 左侧 logo 路径 | 字符串；空字符串、`none`、`null` 会被忽略 |
| `right_logo` | 否 | 右侧 logo 路径 | 同上 |
| `center_logo` | 否 | 中央 logo 路径 | 同上 |
| `center_logo_height` | 否 | 中央 logo 高度 | 数字；不写则使用底部水印区高度 |

补充行为：

- `left_top / left_bottom / right_top / right_bottom` 如果未提供 `height`，会自动使用 `bottom_margin * 0.3`
- 主图会贴到上方，底部新增水印区
- 右侧 logo 会出现在分隔线左边

#### `watermark_with_timestamp`

把文字水印叠加到图像右下区域。

它会先按 `multi_rich_text` 生成文字，再贴回原图。

可用参数：

- `text_segments`
- `text_alignment`
- `text_spacing`
- `height`

默认行为：

- `height` 不写时，约为图片高度的 `2%`
- 水印位置固定在靠右下区域，代码中约为：
  - `x = 图片宽度的 93% - 文字宽度`
  - `y = 图片高度的 95%`

#### `rounded_corner`

给图像加透明圆角。

| 参数 | 是否必填 | 含义 | 取值 |
| --- | --- | --- | --- |
| `border_radius` | 否 | 圆角半径 | 数字，默认 `10` |

注意：

- 该处理器会生成透明角
- 若最终导出为 JPG，透明区域会在转 `RGB` 时失去透明信息

#### `shadow`

给图像加外阴影。

| 参数 | 是否必填 | 含义 | 取值 |
| --- | --- | --- | --- |
| `shadow_color` | 否 | 阴影颜色 | 默认 `(0, 0, 0, 180)` |
| `shadow_radius` | 否 | 阴影模糊半径 | 数字，默认 `30` |

说明：

- 该处理器会在四周扩展画布
- 实际扩边大约是 `shadow_radius * 2`
- 阴影基于 alpha 通道生成，适合透明 PNG 图层或圆角图层

#### `crop`

按给定宽高从中心裁剪，并支持偏移。

| 参数 | 是否必填 | 含义 | 取值 |
| --- | --- | --- | --- |
| `width` | 否 | 裁剪宽度 | 数字；不写则使用原宽 |
| `height` | 否 | 裁剪高度 | 数字；不写则使用原高 |
| `offset` | 否 | 相对居中裁剪框的偏移 | JSON 字符串，如 `"[0, -20]"` |

`offset` 方向规则：

- `x` 正值：向右
- `x` 负值：向左
- `y` 正值：向下
- `y` 负值：向上

### 6.3 合并类

合并类用于拼接或叠加多个图层。

#### 对齐枚举值

| 写法 | 含义 |
| --- | --- |
| `start` | 起始侧 |
| `center` | 居中 |
| `end` | 结束侧 |
| `top` | `start` 的垂直别名 |
| `middle` | `center` 的垂直别名 |
| `bottom` | `end` 的垂直别名 |
| `left` | `start` 的水平别名 |
| `right` | `end` 的水平别名 |

#### `concat`

把多张图按横向或纵向拼起来。

| 参数 | 是否必填 | 含义 | 取值 |
| --- | --- | --- | --- |
| `direction` | 否 | 拼接方向 | `horizontal` / `vertical`，默认 `horizontal` |
| `alignment` | 否 | 另一维度的对齐方式 | 见上表，默认 `bottom` |
| `spacing` | 否 | 图层间距 | 数字，默认 `10` |
| `background` | 否 | 拼接画布底色 | 默认透明 |

示例：

```json
{
  "processor_name": "concat",
  "direction": "vertical",
  "alignment": "center",
  "spacing": "{{ vh(2) }}",
  "select": "[2,3]"
}
```

#### `alignment`

把多张图叠到同一张画布上。

| 参数 | 是否必填 | 含义 | 取值 |
| --- | --- | --- | --- |
| `horizontal_alignment` | 否 | 水平方向基准对齐 | `left` / `center` / `right`，默认 `center` |
| `vertical_alignment` | 否 | 垂直方向基准对齐 | `top` / `middle` / `bottom`，默认 `center` |
| `background` | 否 | 叠加画布底色 | 默认透明 |
| `offsets` | 否 | 每个图层的偏移量 | JSON 字符串，例如 `[[0,0],[0,-20]]` |
| `weights` | 否 | 图层绘制顺序权重 | JSON 字符串，例如 `[100,-100]` |

`weights` 规则：

- 数值越小，越先绘制
- 数值越大，越后绘制
- 后绘制的图层会盖住前面的图层

`offsets` 规则很重要：

- 代码里会先把偏移值取反再应用
- 所以：
  - `[10, 20]` 实际效果是“向左、向上”
  - `[-10, -20]` 实际效果是“向右、向下”

这和 `crop.offset` 的方向正好相反。

## 7. 常见片段

### 7.1 图片内中下方叠加自定义文字

```json
[
  {
    "processor_name": "rich_text",
    "text": "{{ template_inputs.custom_text|default('Hello World!') }}",
    "font_path": "HFIntimate-2.ttf",
    "height": "{{ vh(5.2) }}",
    "trim": true,
    "color": "white"
  },
  {
    "processor_name": "shadow",
    "shadow_radius": "{{ vh(0.6) }}",
    "shadow_color": "0,0,0,180"
  },
  {
    "processor_name": "alignment",
    "horizontal_alignment": "center",
    "vertical_alignment": "center",
    "offsets": "[[0,0],[0,-{{ vh(28) }}]]",
    "select": "[0,2]"
  }
]
```

### 7.2 图片下方新增一行自定义文字

```json
[
  {
    "processor_name": "rich_text",
    "text": "{{ template_inputs.custom_text|default('Hello World!') }}",
    "font_path": "HFIntimate-2.ttf",
    "height": "{{ vh(4.2) }}",
    "trim": true,
    "color": "white"
  },
  {
    "processor_name": "concat",
    "direction": "vertical",
    "alignment": "center",
    "spacing": "{{ vh(2.2) }}",
    "select": "[0,1]"
  }
]
```

## 8. 调试建议

1. 先保证模板渲染后是合法 JSON，再检查视觉效果。
2. 复杂模板优先显式写 `select`，不要依赖隐式缓冲区。
3. 涉及 `offset`、`offsets` 时，先记住：
   - `crop.offset`：正右正下
   - `alignment.offsets`：正左正上
4. 需要看中间结果时，可在节点上加：

```json
"save_buffer": true
```

并可选设置：

```json
"output": "./tmp"
```

5. 文字、logo、透明边、阴影问题优先排查：
   - 字体路径是否存在
   - logo 路径是否为空
   - 是否导出为 JPG 导致透明丢失
   - `shadow` 是否把画布扩大了

## 9. 自定义模板建议

1. 优先复制一个接近的现有模板再改。
2. 尺寸、间距、圆角、阴影半径优先使用 `vw()` / `vh()`，更容易适配不同分辨率。
3. 读 EXIF 时始终写 `default` 兜底。
4. 新字体放到 `config/fonts`，新 logo 放到 `config/logos`。
5. 若模板需要用户输入，统一从 `template_inputs` 读取。
