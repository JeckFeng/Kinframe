# KinFrame `slide_designs.json` 能力层实施方案

> 适用范围：KinFrame 采用“基础模板体系 + 模板参数化 + 图层混合 + AI 生成式 CSS”的幻灯片渲染方案。本文档用于指导前端渲染器、后端 AI 工作流、JSON Schema 校验、AI 输出约束和设计数据存储的开发。

---

## 1. 方案目标

KinFrame 的核心目标不是做传统相册网格，而是做一个“AI 驱动的家庭影像 PPT 放映网站”。每张照片对应一页艺术化幻灯片。AI 不直接生成生产环境网页代码，而是生成受控的设计数据，由前端渲染器稳定渲染。

本方案采用以下四层能力：

```text
基础模板体系
+ 模板参数化
+ 图层混合
+ AI 生成式 CSS
```

四层能力的关系如下：

| 层级 | 作用 | 谁定义 | 是否允许 AI 生成 |
|---|---|---|---|
| 基础模板体系 | 定义页面骨架、布局槽位、模板类型 | 前端/系统预置 | AI 只能选择模板，不能新增模板代码 |
| 模板参数化 | 调整模板内的图片区、文案区、时间轴区等参数 | 系统提供参数能力 | AI 可以生成参数值 |
| 图层混合 | 添加背景、蒙版、光斑、形状、纹理、文字、时间轴等图层 | 系统定义图层类型 | AI 可以组合图层并填写参数 |
| AI 生成式 CSS | 调整视觉质感、色彩氛围、阴影、滤镜、动效、字体气质 | 系统定义白名单 | AI 可以生成 CSS Variables 和受限 scoped CSS |

核心原则：

```text
AI 负责设计决策，不负责直接生成可执行网页代码。
前端负责受控渲染，不盲目执行 AI 输出。
JSON 负责结构与布局，CSS 负责视觉质感。
```

---

## 2. 需要定义几个 JSON 文件？

建议定义 **5 个核心 JSON 文件**，外加 **1 个可选预设文件**。

### 2.1 核心文件清单

| 文件 | 类型 | 作用 | 是否由 AI 生成 | 是否进入 Git |
|---|---|---|---|---|
| `slide_templates.json` | 系统配置 | 定义基础模板体系、模板槽位、模板参数范围 | 否 | 是 |
| `layer_primitives.json` | 系统配置 | 定义图层类型、公共字段、样式能力、合法取值 | 否 | 是 |
| `ai_css_whitelist.json` | 系统配置 | 定义 AI 可生成的 CSS Variables 与 scoped CSS 白名单 | 否 | 是 |
| `slide_design.schema.json` | JSON Schema | 校验 AI 生成的单页设计数据 | 否 | 是 |
| `slide_designs.json` | 设计实例 | 每张照片对应的 AI 设计结果 | 是 | 运行数据，不建议直接进 Git |

### 2.2 可选文件

| 文件 | 类型 | 作用 | 是否由 AI 生成 | 是否进入 Git |
|---|---|---|---|---|
| `design_presets.json` | 系统预设 | 预置常用调色板、蒙版、光斑、胶片纹理、时间轴样式 | 否 | 是 |

### 2.3 推荐目录结构

```text
kinframe/
├── frontend/
│   └── app/
│       └── slide-renderer/
│           ├── configs/
│           │   ├── slide_templates.json
│           │   ├── layer_primitives.json
│           │   ├── ai_css_whitelist.json
│           │   └── design_presets.json
│           ├── schemas/
│           │   └── slide_design.schema.json
│           ├── components/
│           │   ├── SlideRenderer.vue
│           │   ├── LayerRenderer.vue
│           │   ├── BackgroundLayer.vue
│           │   ├── ImageLayer.vue
│           │   ├── TextLayer.vue
│           │   ├── ShapeLayer.vue
│           │   ├── MaskLayer.vue
│           │   └── TimelineLayer.vue
│           └── validators/
│               ├── validateSlideDesign.ts
│               └── sanitizeAiCss.ts
│
├── backend/
│   └── app/
│       ├── schemas/
│       │   └── slide_design.schema.json
│       ├── agents/
│       │   └── slide_design_agent.py
│       ├── services/
│       │   ├── slide_design_validator.py
│       │   └── ai_css_sanitizer.py
│       └── prompts/
│           └── slide_design_prompt.md
│
└── data/
    └── exports/
        └── slide_designs.json
```

说明：

1. `slide_designs.json` 在生产系统中更推荐存入 PostgreSQL 的 `slide_designs.design_json` JSONB 字段。
2. 文件形式的 `slide_designs.json` 适合导出、备份、调试、离线预览。
3. `slide_design.schema.json` 建议前后端共用同一份 schema，避免前端能渲染、后端却无法校验，或反过来。

---

## 3. JSON 与 CSS 的职责边界

为了避免模板参数化、图层系统和 AI 生成式 CSS 相互冲突，必须明确边界。

### 3.1 JSON 负责什么？

JSON 负责 **结构、语义、布局、图层、元素存在性和渲染数据**。

JSON 可以控制：

```text
模板选择
画布比例
安全边距
元素是否存在
元素类型
元素位置
元素大小
元素层级 zIndex
元素旋转角度
元素锚点 anchor
图层可见性
图片裁剪与适配方式
蒙版位置和大小
形状类型
形状位置和大小
填充类型
渐变色 stops
阴影参数
文案内容
字体大小
字体粗细
字体方向
文字对齐方式
时间轴位置
动画语义
响应式行为
```

### 3.2 CSS 负责什么？

AI 生成式 CSS 只负责 **视觉质感和局部风格增强**。

CSS 可以控制：

```text
主题颜色变量
字体质感变量
文字阴影变量
图片阴影变量
模糊强度变量
滤镜强度变量
颗粒感强度变量
渐变氛围变量
过渡时长变量
缓动曲线变量
背景混合模式强度
文本发光效果
图片胶片质感
轻微 hover/enter 视觉效果
```

### 3.3 CSS 不应该控制什么？

CSS 不应该控制核心结构，否则会和 JSON 冲突。

CSS 禁止控制：

```text
主图位置
主图尺寸
文案坐标
文案容器尺寸
蒙版位置
蒙版尺寸
形状位置
形状尺寸
zIndex
菜单栏位置
分类导航位置
时间轴结构位置
页面 DOM 结构
任意 JavaScript
全局 body/html/#app 样式
外部资源导入
```

### 3.4 冲突处理规则

如果 JSON 和 CSS 同时尝试控制同一类属性，处理优先级如下：

```text
1. 安全校验规则最高
2. JSON 结构布局优先于 CSS
3. 模板默认值低于 slide_designs.json
4. layer.style 的显式值高于 templateParams
5. CSS Variables 只能作为视觉 token 被引用，不能反向改变布局
6. scoped CSS 中如果出现禁用属性，直接丢弃该属性
```

---

## 4. 文件一：`slide_templates.json`

### 4.1 文件作用

`slide_templates.json` 定义系统内置的基础模板体系。它描述每种模板的布局槽位、默认参数、允许参数范围和适合场景。

AI 可以选择模板，也可以填写模板参数，但不能生成新的模板代码。

### 4.2 文件路径

```text
frontend/app/slide-renderer/configs/slide_templates.json
```

### 4.3 顶层结构

```json
{
  "version": "1.0.0",
  "templates": []
}
```

### 4.4 模板字段定义

每个模板建议包含以下字段：

| 字段 | 类型 | 是否必填 | 说明 |
|---|---|---|---|
| `id` | string | 是 | 模板唯一 ID |
| `name` | string | 是 | 模板显示名称 |
| `description` | string | 是 | 模板说明 |
| `intents` | string[] | 是 | 适合的照片场景，如 travel/life/pet |
| `moods` | string[] | 是 | 适合的情绪，如 poetic/warm/cinematic |
| `aspectRatios` | string[] | 是 | 支持画布比例，默认 `16:9` |
| `slots` | object | 是 | 模板槽位 |
| `defaultParams` | object | 是 | 默认参数 |
| `paramSchema` | object | 是 | 参数范围与枚举 |
| `allowedLayerTypes` | string[] | 是 | 允许叠加的图层类型 |
| `maxExtraLayers` | number | 是 | 额外图层最大数量 |
| `renderComponent` | string | 是 | 前端 Vue 组件名 |

### 4.5 模板示例

```json
{
  "version": "1.0.0",
  "templates": [
    {
      "id": "cinematic_fullscreen",
      "name": "电影感全屏",
      "description": "适合风景、旅行、城市夜景等具有强画面张力的照片。照片接近全屏，文案以电影字幕形式出现。",
      "intents": ["travel", "photography"],
      "moods": ["cinematic", "quiet", "grand"],
      "aspectRatios": ["16:9"],
      "slots": {
        "photo": {
          "required": true,
          "defaultBounds": { "x": 0, "y": 0, "w": 1, "h": 1 },
          "safeBounds": { "x": 0, "y": 0, "w": 1, "h": 1 }
        },
        "caption": {
          "required": false,
          "defaultBounds": { "x": 0.12, "y": 0.76, "w": 0.76, "h": 0.12 },
          "safeBounds": { "x": 0.08, "y": 0.62, "w": 0.84, "h": 0.22 }
        },
        "timeline": {
          "required": true,
          "defaultBounds": { "x": 0.12, "y": 0.92, "w": 0.76, "h": 0.04 }
        }
      },
      "defaultParams": {
        "photoFit": "cover",
        "captionPlacement": "bottom_center",
        "timelinePlacement": "bottom",
        "vignetteEnabled": true,
        "captionPanelEnabled": false
      },
      "paramSchema": {
        "photoFit": ["cover", "contain"],
        "captionPlacement": ["bottom_left", "bottom_center", "bottom_right"],
        "timelinePlacement": ["bottom"],
        "vignetteEnabled": "boolean",
        "captionPanelEnabled": "boolean"
      },
      "allowedLayerTypes": ["mask", "shape", "texture", "text", "timeline", "meta"],
      "maxExtraLayers": 8,
      "renderComponent": "CinematicFullscreenTemplate"
    },
    {
      "id": "magazine_left",
      "name": "杂志式左图右文",
      "description": "适合生活照、宠物照和有人物主体的照片。照片偏左，右侧保留文案和时间信息。",
      "intents": ["life", "pet", "portrait"],
      "moods": ["warm", "editorial", "soft"],
      "aspectRatios": ["16:9"],
      "slots": {
        "photo": {
          "required": true,
          "defaultBounds": { "x": 0.08, "y": 0.12, "w": 0.56, "h": 0.72 }
        },
        "caption": {
          "required": false,
          "defaultBounds": { "x": 0.68, "y": 0.56, "w": 0.24, "h": 0.2 }
        },
        "timeline": {
          "required": true,
          "defaultBounds": { "x": 0.68, "y": 0.84, "w": 0.24, "h": 0.06 }
        }
      },
      "defaultParams": {
        "photoFit": "cover",
        "photoRadius": "large",
        "captionPlacement": "right_middle",
        "timelinePlacement": "right_bottom",
        "captionPanelEnabled": true
      },
      "paramSchema": {
        "photoFit": ["cover", "contain"],
        "photoRadius": ["none", "small", "medium", "large", "xl"],
        "captionPlacement": ["right_top", "right_middle", "right_bottom"],
        "timelinePlacement": ["right_bottom", "bottom"],
        "captionPanelEnabled": "boolean"
      },
      "allowedLayerTypes": ["shape", "mask", "texture", "text", "timeline", "meta"],
      "maxExtraLayers": 10,
      "renderComponent": "MagazineLeftTemplate"
    }
  ]
}
```

### 4.6 第一版建议内置模板

第一版至少内置 8 个模板：

```text
cinematic_fullscreen      电影感全屏
poetic_landscape          诗意风景
magazine_left             杂志式左图右文
gallery_center            艺术馆居中
warm_memory               温暖生活
pet_portrait              宠物肖像
dark_exhibition           暗色展厅
minimal_white             极简白底
```

第二版再扩展：

```text
film_negative             胶片负片
soft_blur_background      柔焦背景
seasonal_memory           季节记忆
travel_postcard           旅行明信片
family_archive            家庭档案
```

---

## 5. 文件二：`layer_primitives.json`

### 5.1 文件作用

`layer_primitives.json` 定义图层系统的能力边界。前端渲染器只渲染这里声明过的图层类型和字段。

AI 不能创造未知图层类型。

### 5.2 文件路径

```text
frontend/app/slide-renderer/configs/layer_primitives.json
```

### 5.3 坐标系统

所有元素位置默认使用 0 到 1 的归一化坐标。

```json
{
  "position": {
    "x": 0.1,
    "y": 0.2,
    "w": 0.5,
    "h": 0.3
  }
}
```

含义：

```text
x = 画布宽度的 10%
y = 画布高度的 20%
w = 画布宽度的 50%
h = 画布高度的 30%
```

统一字段命名：

```text
使用 x/y/w/h，不使用 width/height。
因为 x/y/w/h 更适合作为画布坐标系统字段。
```

### 5.4 公共图层字段

所有图层都应支持以下公共字段：

| 字段 | 类型 | 是否必填 | 说明 |
|---|---|---|---|
| `id` | string | 是 | 图层唯一 ID |
| `type` | string | 是 | 图层类型 |
| `zIndex` | number | 是 | 图层顺序，越大越靠上 |
| `visible` | boolean | 否 | 是否显示，默认 true |
| `position` | object | 否 | 位置与大小 |
| `anchor` | string | 否 | 锚点，如 center/top_left |
| `rotation` | number | 否 | 旋转角度，单位 degree |
| `opacity` | number | 否 | 透明度，0 到 1 |
| `blendMode` | string | 否 | 混合模式 |
| `style` | object | 否 | 样式对象 |
| `animation` | object | 否 | 动画对象 |
| `responsive` | object | 否 | 响应式策略 |

### 5.5 图层类型

第一版建议支持：

```text
background    背景层
image         图片层
text          文本层
shape         形状层
mask          蒙版层
timeline      时间轴层
meta          元数据层
texture       纹理层
frame         相框层
vignette      暗角层
```

第二版可扩展：

```text
decoration    装饰元素
captionPanel  文案面板
light          光效层
noise          噪声颗粒层
```

### 5.6 填充 Fill 模型

`fill` 是图层视觉的核心字段。

支持类型：

```text
solid
linearGradient
radialGradient
conicGradient
image
noise
glass
none
```

示例：纯色填充

```json
{
  "fill": {
    "type": "solid",
    "color": "#101820",
    "opacity": 0.88
  }
}
```

示例：线性渐变

```json
{
  "fill": {
    "type": "linearGradient",
    "angle": 135,
    "stops": [
      { "color": "#0F172A", "opacity": 1, "position": 0 },
      { "color": "#334155", "opacity": 0.92, "position": 0.58 },
      { "color": "#D6A86C", "opacity": 0.7, "position": 1 }
    ]
  }
}
```

示例：径向渐变

```json
{
  "fill": {
    "type": "radialGradient",
    "center": { "x": 0.5, "y": 0.5 },
    "radius": 0.6,
    "stops": [
      { "color": "#FFF1D6", "opacity": 0.35, "position": 0 },
      { "color": "#FFF1D6", "opacity": 0, "position": 1 }
    ]
  }
}
```

### 5.7 阴影 Shadow 模型

阴影使用 JSON 定义，不交给 AI CSS 随意控制布局阴影。

```json
{
  "shadow": {
    "enabled": true,
    "type": "soft",
    "x": 0,
    "y": 32,
    "blur": 80,
    "spread": -12,
    "color": "#000000",
    "opacity": 0.38
  }
}
```

支持类型：

```text
none
soft
dramatic
glow
inner
film
```

### 5.8 蒙版 Mask 模型

蒙版作为独立图层，也可以作为图层内部的 `mask` 字段。

推荐第一版采用独立 `mask` 图层，语义更清晰。

```json
{
  "id": "left_gradient_mask",
  "type": "mask",
  "zIndex": 20,
  "position": { "x": 0, "y": 0, "w": 0.45, "h": 1 },
  "shape": "rect",
  "opacity": 1,
  "style": {
    "fill": {
      "type": "linearGradient",
      "angle": 90,
      "stops": [
        { "color": "#000000", "opacity": 0.58, "position": 0 },
        { "color": "#000000", "opacity": 0, "position": 1 }
      ]
    },
    "blur": 24,
    "blendMode": "multiply"
  }
}
```

蒙版可控制：

```text
位置 x/y/w/h
形状 shape
透明度 opacity
渐变方向 angle
渐变 stops
模糊 blur
混合模式 blendMode
```

### 5.9 形状 Shape 模型

形状图层支持：

```text
rect
roundedRect
circle
ellipse
line
polygon
blob
lightOrb
```

示例：光斑

```json
{
  "id": "warm_light_orb",
  "type": "shape",
  "zIndex": 8,
  "shape": "circle",
  "position": { "x": 0.68, "y": 0.08, "w": 0.3, "h": 0.3 },
  "style": {
    "fill": {
      "type": "radialGradient",
      "stops": [
        { "color": "#F2D6A2", "opacity": 0.34, "position": 0 },
        { "color": "#F2D6A2", "opacity": 0, "position": 1 }
      ]
    },
    "blur": 60,
    "blendMode": "screen"
  }
}
```

示例：文案底板

```json
{
  "id": "caption_panel",
  "type": "shape",
  "zIndex": 30,
  "shape": "roundedRect",
  "position": { "x": 0.58, "y": 0.62, "w": 0.32, "h": 0.18 },
  "style": {
    "fill": {
      "type": "solid",
      "color": "#101820",
      "opacity": 0.36
    },
    "borderRadius": 28,
    "backdropBlur": 18,
    "shadow": {
      "enabled": true,
      "type": "soft",
      "x": 0,
      "y": 20,
      "blur": 50,
      "spread": -8,
      "color": "#000000",
      "opacity": 0.28
    }
  }
}
```

### 5.10 文本 Text 模型

文本层负责标题、文案、日期、地点等。

```json
{
  "id": "caption",
  "type": "text",
  "zIndex": 50,
  "content": "山谷中的光，像一封迟来的信。",
  "position": { "x": 0.58, "y": 0.72, "w": 0.32, "h": 0.14 },
  "style": {
    "fontFamily": "serif_elegant",
    "fontSize": {
      "type": "clamp",
      "min": 20,
      "preferredVw": 2,
      "max": 36
    },
    "fontWeight": 400,
    "fontStyle": "normal",
    "writingMode": "horizontal-tb",
    "textOrientation": "mixed",
    "lineHeight": 1.6,
    "letterSpacing": "0.04em",
    "textAlign": "left",
    "verticalAlign": "top",
    "color": "#F8F4EA",
    "opacity": 0.92,
    "textShadow": {
      "enabled": true,
      "x": 0,
      "y": 8,
      "blur": 24,
      "color": "#000000",
      "opacity": 0.35
    }
  }
}
```

字体方向字段：

```text
writingMode:
  horizontal-tb      横排，默认
  vertical-rl        竖排，从右到左
  vertical-lr        竖排，从左到右

textOrientation:
  mixed              默认
  upright            单字直立
  sideways           横向旋转
```

### 5.11 图片 Image 模型

```json
{
  "id": "main_photo",
  "type": "image",
  "zIndex": 10,
  "source": "photo.preview",
  "position": { "x": 0.08, "y": 0.12, "w": 0.56, "h": 0.72 },
  "style": {
    "fit": "cover",
    "objectPosition": "center center",
    "borderRadius": 32,
    "shadow": {
      "enabled": true,
      "type": "soft",
      "x": 0,
      "y": 32,
      "blur": 80,
      "spread": -12,
      "color": "#000000",
      "opacity": 0.38
    },
    "filter": {
      "brightness": 1,
      "contrast": 1.02,
      "saturation": 0.98,
      "blur": 0
    }
  }
}
```

图片适配：

```text
fit: cover | contain | fill
objectPosition: center center | top center | bottom center | left center | right center
```

### 5.12 时间轴 Timeline 模型

```json
{
  "id": "timeline",
  "type": "timeline",
  "zIndex": 70,
  "position": { "x": 0.12, "y": 0.92, "w": 0.76, "h": 0.04 },
  "style": {
    "variant": "minimal_line",
    "lineWidth": 1,
    "lineColor": "#F8F4EA",
    "lineOpacity": 0.56,
    "activeDotSize": 8,
    "activeDotColor": "#F8F4EA",
    "labelVisible": true,
    "labelFormat": "YYYY.MM.DD",
    "labelPosition": "above",
    "fontFamily": "sans_refined",
    "fontSize": 13,
    "fontWeight": 300
  }
}
```

时间轴位置由 JSON 控制。AI CSS 可以控制时间轴颜色变量和过渡质感，但不能改变时间轴坐标。

---

## 6. 文件三：`ai_css_whitelist.json`

### 6.1 文件作用

`ai_css_whitelist.json` 定义 AI 可以生成哪些 CSS Variables 和哪些 scoped CSS 属性。

本方案建议采用两级 AI CSS：

```text
第一优先级：CSS Variables / Design Tokens
第二优先级：受限 scoped CSS rules
```

AI 生成式 CSS 尽量宽松，但必须禁止会破坏布局、注入资源或影响全局页面的能力。

### 6.2 文件路径

```text
frontend/app/slide-renderer/configs/ai_css_whitelist.json
```

### 6.3 CSS Variables 命名空间

建议所有变量使用 `--kf-` 前缀。

```json
{
  "version": "1.0.0",
  "cssVariables": {
    "color": [
      "--kf-color-bg-primary",
      "--kf-color-bg-secondary",
      "--kf-color-bg-accent",
      "--kf-color-text-primary",
      "--kf-color-text-secondary",
      "--kf-color-text-muted",
      "--kf-color-line",
      "--kf-color-dot",
      "--kf-color-mask",
      "--kf-color-glow"
    ],
    "gradient": [
      "--kf-gradient-bg",
      "--kf-gradient-mask",
      "--kf-gradient-orb",
      "--kf-gradient-caption-panel"
    ],
    "opacity": [
      "--kf-opacity-bg",
      "--kf-opacity-photo",
      "--kf-opacity-caption",
      "--kf-opacity-mask",
      "--kf-opacity-grain",
      "--kf-opacity-vignette",
      "--kf-opacity-timeline"
    ],
    "blur": [
      "--kf-blur-bg",
      "--kf-blur-mask",
      "--kf-blur-panel",
      "--kf-blur-glow"
    ],
    "shadow": [
      "--kf-shadow-photo",
      "--kf-shadow-caption",
      "--kf-shadow-panel",
      "--kf-shadow-glow"
    ],
    "filter": [
      "--kf-filter-photo",
      "--kf-filter-bg",
      "--kf-filter-texture"
    ],
    "typography": [
      "--kf-font-caption-family",
      "--kf-font-meta-family",
      "--kf-font-caption-size",
      "--kf-font-meta-size",
      "--kf-font-caption-weight",
      "--kf-font-meta-weight",
      "--kf-letter-spacing-caption",
      "--kf-line-height-caption"
    ],
    "radius": [
      "--kf-radius-photo",
      "--kf-radius-panel",
      "--kf-radius-shape"
    ],
    "motion": [
      "--kf-motion-duration-enter",
      "--kf-motion-duration-exit",
      "--kf-motion-duration-photo",
      "--kf-motion-easing",
      "--kf-motion-scale-from",
      "--kf-motion-scale-to"
    ],
    "texture": [
      "--kf-grain-opacity",
      "--kf-grain-size",
      "--kf-vignette-opacity",
      "--kf-light-leak-opacity"
    ]
  }
}
```

### 6.4 CSS Variables 值类型约束

```json
{
  "valueTypes": {
    "color": "hex | rgb | rgba | hsl | hsla",
    "opacity": "number:0..1",
    "blur": "px:0..120",
    "shadow": "css-box-shadow-without-url",
    "filter": "safe-css-filter",
    "fontFamily": "known-font-token | safe-system-font-stack",
    "fontSize": "px | rem | clamp",
    "duration": "ms:0..5000",
    "easing": "ease | ease-in | ease-out | ease-in-out | cubic-bezier",
    "radius": "px:0..96"
  }
}
```

### 6.5 scoped CSS 允许选择器

AI 如果生成 scoped CSS，只能使用这些选择器前缀：

```json
{
  "allowedSelectors": [
    ".kf-slide",
    ".kf-slide[data-template]",
    ".kf-slide[data-category]",
    ".kf-layer",
    ".kf-layer[data-layer-id]",
    ".kf-photo-layer",
    ".kf-text-layer",
    ".kf-shape-layer",
    ".kf-mask-layer",
    ".kf-timeline-layer",
    ".kf-caption",
    ".kf-meta",
    ".kf-photo-frame",
    ".kf-caption-panel"
  ]
}
```

禁止选择器：

```text
html
body
#app
*
script
iframe
input
button
a[href]
任何逗号组合中包含禁用选择器的规则
任何父级逃逸选择器
```

### 6.6 scoped CSS 允许属性白名单

尽量宽松，但不允许控制核心布局。

```json
{
  "allowedProperties": [
    "color",
    "background",
    "background-color",
    "background-image",
    "background-size",
    "background-position",
    "background-blend-mode",
    "opacity",
    "box-shadow",
    "text-shadow",
    "filter",
    "backdrop-filter",
    "mix-blend-mode",
    "border",
    "border-color",
    "border-width",
    "border-style",
    "border-radius",
    "outline",
    "outline-color",
    "outline-width",
    "letter-spacing",
    "word-spacing",
    "line-height",
    "font-family",
    "font-size",
    "font-weight",
    "font-style",
    "font-variation-settings",
    "font-feature-settings",
    "text-transform",
    "text-decoration",
    "text-decoration-color",
    "text-underline-offset",
    "text-rendering",
    "-webkit-font-smoothing",
    "transition",
    "transition-property",
    "transition-duration",
    "transition-timing-function",
    "animation-name",
    "animation-duration",
    "animation-timing-function",
    "animation-delay",
    "animation-iteration-count",
    "animation-direction",
    "animation-fill-mode",
    "transform",
    "transform-origin",
    "clip-path",
    "mask-image",
    "mask-size",
    "mask-position",
    "mask-repeat",
    "-webkit-mask-image",
    "-webkit-mask-size",
    "-webkit-mask-position",
    "-webkit-mask-repeat"
  ]
}
```

注意：虽然这里允许 `transform`、`clip-path`、`mask-image`，但只用于视觉微调。不得用它们替代 JSON 中的位置和大小控制。

### 6.7 scoped CSS 禁止属性

```json
{
  "forbiddenProperties": [
    "position",
    "top",
    "right",
    "bottom",
    "left",
    "width",
    "height",
    "min-width",
    "min-height",
    "max-width",
    "max-height",
    "z-index",
    "display",
    "grid",
    "grid-template",
    "grid-template-columns",
    "grid-template-rows",
    "flex",
    "flex-direction",
    "justify-content",
    "align-items",
    "place-items",
    "overflow",
    "pointer-events",
    "cursor",
    "content",
    "visibility"
  ]
}
```

### 6.8 禁止 CSS 能力

```text
禁止 @import
禁止 @font-face
禁止 url(http...)
禁止 url(https...)
禁止 javascript:
禁止 expression()
禁止 behavior
禁止外部资源
禁止修改全局滚动
禁止隐藏整个应用
禁止设置 pointer-events 影响交互
```

---

## 7. 文件四：`slide_design.schema.json`

### 7.1 文件作用

`slide_design.schema.json` 用于校验 AI 输出的单页幻灯片设计数据。

后端必须校验。前端也建议再次校验或轻量校验。

### 7.2 文件路径

```text
frontend/app/slide-renderer/schemas/slide_design.schema.json
backend/app/schemas/slide_design.schema.json
```

### 7.3 顶层字段定义

| 字段 | 类型 | 是否必填 | 说明 |
|---|---|---|---|
| `version` | string | 是 | 设计协议版本 |
| `slideId` | string | 是 | 幻灯片 ID |
| `photoId` | string | 是 | 照片 ID |
| `templateId` | string | 是 | 使用的基础模板 |
| `canvas` | object | 是 | 画布配置 |
| `templateParams` | object | 是 | 模板参数 |
| `mediaRefs` | object | 是 | 图片资源引用 |
| `captionPolicy` | object | 是 | 文案来源规则 |
| `styleTokens` | object | 是 | AI CSS tokens |
| `layers` | array | 是 | 图层列表 |
| `timeline` | object | 是 | 时间轴数据 |
| `renderPolicy` | object | 是 | 渲染策略 |
| `aiMeta` | object | 否 | AI 生成过程元信息 |

### 7.4 Schema 骨架示例

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://kinframe.local/schemas/slide_design.schema.json",
  "title": "KinFrame Slide Design Schema",
  "type": "object",
  "required": [
    "version",
    "slideId",
    "photoId",
    "templateId",
    "canvas",
    "templateParams",
    "mediaRefs",
    "captionPolicy",
    "styleTokens",
    "layers",
    "timeline",
    "renderPolicy"
  ],
  "properties": {
    "version": { "type": "string", "const": "1.0.0" },
    "slideId": { "type": "string" },
    "photoId": { "type": "string" },
    "templateId": { "type": "string" },
    "canvas": { "$ref": "#/$defs/canvas" },
    "templateParams": { "type": "object" },
    "mediaRefs": { "$ref": "#/$defs/mediaRefs" },
    "captionPolicy": { "$ref": "#/$defs/captionPolicy" },
    "styleTokens": { "$ref": "#/$defs/styleTokens" },
    "layers": {
      "type": "array",
      "minItems": 1,
      "maxItems": 24,
      "items": { "$ref": "#/$defs/layer" }
    },
    "timeline": { "$ref": "#/$defs/timeline" },
    "renderPolicy": { "$ref": "#/$defs/renderPolicy" },
    "aiMeta": { "type": "object" }
  },
  "$defs": {}
}
```

### 7.5 语义校验规则

JSON Schema 只能做结构校验，还需要额外语义校验。

后端必须执行：

```text
templateId 必须存在于 slide_templates.json
layer.type 必须存在于 layer_primitives.json
zIndex 不允许重复严重冲突
position x/y/w/h 默认应在 -0.2 到 1.2 之间
核心图层不得完全离开画布
主图 image layer 必须存在
timeline layer 必须存在
caption text layer 仅在 final_caption 存在时生成
图层数量不得超过模板 maxExtraLayers + 模板基础图层数量
CSS Variables 必须在 ai_css_whitelist.json 中
scoped CSS 选择器必须在白名单中
scoped CSS 属性必须在白名单中
禁止外部 URL
禁止 JS 注入
```

---

## 8. 文件五：`slide_designs.json`

### 8.1 文件作用

`slide_designs.json` 是 AI 为每张照片生成的具体幻灯片设计结果。

生产环境中，它可以作为 PostgreSQL JSONB 存储，也可以导出成文件。

### 8.2 文件形式

如果导出为文件，推荐：

```json
{
  "version": "1.0.0",
  "project": "KinFrame",
  "slides": []
}
```

如果存入数据库，每条 `slide_designs.design_json` 只保存单页对象。

### 8.3 完整单页示例

```json
{
  "version": "1.0.0",
  "slideId": "slide_20260512_001",
  "photoId": "photo_20260512_001",
  "templateId": "magazine_left",
  "canvas": {
    "aspectRatio": "16:9",
    "baseWidth": 1920,
    "baseHeight": 1080,
    "safeArea": {
      "top": 0.08,
      "right": 0.08,
      "bottom": 0.08,
      "left": 0.08
    }
  },
  "mediaRefs": {
    "original": "minio://kinframe-photos/originals/2026/05/photo_001.heic",
    "preview": "minio://kinframe-photos/previews/2026/05/photo_001.webp",
    "thumbnail": "minio://kinframe-photos/thumbnails/2026/05/photo_001.webp"
  },
  "captionPolicy": {
    "captionSource": "ai_generated",
    "userMessage": null,
    "aiCaptionEnabled": true,
    "aiCaption": "光从山谷尽头铺开，像一段安静的旅程。",
    "finalCaption": "光从山谷尽头铺开，像一段安静的旅程。"
  },
  "templateParams": {
    "photoFit": "cover",
    "photoRadius": "large",
    "captionPlacement": "right_middle",
    "timelinePlacement": "right_bottom",
    "captionPanelEnabled": true
  },
  "styleTokens": {
    "cssVariables": {
      "--kf-color-bg-primary": "#101820",
      "--kf-color-bg-secondary": "#2F4858",
      "--kf-color-bg-accent": "#D6A86C",
      "--kf-color-text-primary": "rgba(248, 244, 234, 0.94)",
      "--kf-color-text-secondary": "rgba(248, 244, 234, 0.72)",
      "--kf-opacity-vignette": "0.42",
      "--kf-opacity-grain": "0.08",
      "--kf-blur-panel": "18px",
      "--kf-shadow-photo": "0 32px 80px rgba(0, 0, 0, 0.38)",
      "--kf-shadow-caption": "0 12px 42px rgba(0, 0, 0, 0.32)",
      "--kf-filter-photo": "contrast(1.03) saturate(0.96)",
      "--kf-motion-duration-enter": "1200ms",
      "--kf-motion-easing": "cubic-bezier(0.22, 1, 0.36, 1)"
    },
    "scopedCss": "[data-layer-id='main_photo'] { filter: var(--kf-filter-photo); } [data-layer-id='caption'] { text-shadow: var(--kf-shadow-caption); }"
  },
  "layers": [
    {
      "id": "bg",
      "type": "background",
      "zIndex": 0,
      "position": { "x": 0, "y": 0, "w": 1, "h": 1 },
      "style": {
        "fill": {
          "type": "linearGradient",
          "angle": 135,
          "stops": [
            { "color": "#101820", "opacity": 1, "position": 0 },
            { "color": "#2F4858", "opacity": 0.92, "position": 0.55 },
            { "color": "#D6A86C", "opacity": 0.62, "position": 1 }
          ]
        }
      }
    },
    {
      "id": "warm_light_orb",
      "type": "shape",
      "zIndex": 5,
      "shape": "circle",
      "position": { "x": 0.68, "y": 0.08, "w": 0.3, "h": 0.3 },
      "style": {
        "fill": {
          "type": "radialGradient",
          "stops": [
            { "color": "#F2D6A2", "opacity": 0.34, "position": 0 },
            { "color": "#F2D6A2", "opacity": 0, "position": 1 }
          ]
        },
        "blur": 60,
        "blendMode": "screen"
      }
    },
    {
      "id": "main_photo",
      "type": "image",
      "zIndex": 10,
      "source": "photo.preview",
      "position": { "x": 0.08, "y": 0.12, "w": 0.56, "h": 0.72 },
      "style": {
        "fit": "cover",
        "objectPosition": "center center",
        "borderRadius": 32,
        "shadow": {
          "enabled": true,
          "type": "soft",
          "x": 0,
          "y": 32,
          "blur": 80,
          "spread": -12,
          "color": "#000000",
          "opacity": 0.38
        }
      }
    },
    {
      "id": "caption_panel",
      "type": "shape",
      "zIndex": 30,
      "shape": "roundedRect",
      "position": { "x": 0.66, "y": 0.54, "w": 0.26, "h": 0.2 },
      "style": {
        "fill": {
          "type": "solid",
          "color": "#101820",
          "opacity": 0.34
        },
        "borderRadius": 28,
        "backdropBlur": 18
      }
    },
    {
      "id": "caption",
      "type": "text",
      "zIndex": 40,
      "content": "光从山谷尽头铺开，像一段安静的旅程。",
      "position": { "x": 0.69, "y": 0.58, "w": 0.2, "h": 0.12 },
      "style": {
        "fontFamily": "serif_elegant",
        "fontSize": { "type": "clamp", "min": 20, "preferredVw": 1.8, "max": 34 },
        "fontWeight": 400,
        "fontStyle": "normal",
        "writingMode": "horizontal-tb",
        "lineHeight": 1.6,
        "letterSpacing": "0.04em",
        "textAlign": "left",
        "color": "#F8F4EA",
        "opacity": 0.94
      }
    },
    {
      "id": "timeline",
      "type": "timeline",
      "zIndex": 70,
      "position": { "x": 0.68, "y": 0.84, "w": 0.24, "h": 0.05 },
      "style": {
        "variant": "minimal_line",
        "lineWidth": 1,
        "lineColor": "#F8F4EA",
        "lineOpacity": 0.56,
        "activeDotSize": 8,
        "activeDotColor": "#F8F4EA",
        "labelVisible": true,
        "labelFormat": "YYYY.MM.DD",
        "labelPosition": "above",
        "fontFamily": "sans_refined",
        "fontSize": 13,
        "fontWeight": 300
      }
    }
  ],
  "timeline": {
    "takenAt": "2026-05-12T16:30:00+08:00",
    "displayDate": "2026.05.12",
    "categoryOrderIndex": 12,
    "categoryTotal": 86
  },
  "renderPolicy": {
    "fallbackTemplateId": "gallery_center",
    "maxLayerCount": 24,
    "allowScopedCss": true,
    "allowMotion": true,
    "reduceMotionFallback": true
  },
  "aiMeta": {
    "visionModel": "ollama-local-vision",
    "languageModel": "deepseek-api",
    "detectedSubject": "mountain valley with soft light",
    "mood": "quiet_poetic",
    "dominantColors": ["#101820", "#2F4858", "#D6A86C"],
    "generatedAt": "2026-05-12T20:00:00+08:00"
  }
}
```

---

## 9. 文件六，可选：`design_presets.json`

### 9.1 文件作用

`design_presets.json` 用于复用高质量设计片段，减少 AI 输出复杂度，也提高审美稳定性。

它可以包含：

```text
调色板 presets
阴影 presets
蒙版 presets
光斑 presets
时间轴 presets
字体 presets
纹理 presets
动效 presets
```

### 9.2 示例

```json
{
  "version": "1.0.0",
  "palettes": [
    {
      "id": "misty_mountain_blue",
      "name": "雾蓝山谷",
      "colors": ["#101820", "#2F4858", "#D6A86C", "#F8F4EA"]
    }
  ],
  "shadows": [
    {
      "id": "soft_gallery_shadow",
      "value": {
        "enabled": true,
        "type": "soft",
        "x": 0,
        "y": 32,
        "blur": 80,
        "spread": -12,
        "color": "#000000",
        "opacity": 0.38
      }
    }
  ],
  "masks": [
    {
      "id": "left_cinematic_fade",
      "type": "mask",
      "shape": "rect",
      "position": { "x": 0, "y": 0, "w": 0.45, "h": 1 },
      "style": {
        "fill": {
          "type": "linearGradient",
          "angle": 90,
          "stops": [
            { "color": "#000000", "opacity": 0.58, "position": 0 },
            { "color": "#000000", "opacity": 0, "position": 1 }
          ]
        }
      }
    }
  ]
}
```

AI 可以引用 preset：

```json
{
  "presetRef": "left_cinematic_fade"
}
```

前端或后端在渲染前展开 preset。

---

## 10. 渲染流程

### 10.1 上传后生成设计

```text
用户上传照片
  ↓
保存原图到 MinIO
  ↓
ExifTool 解析 EXIF
  ↓
生成预览图和缩略图
  ↓
提取主色调
  ↓
Ollama 视觉模型识别内容
  ↓
DeepSeek 根据模板能力、图层能力、CSS 白名单生成 slide_designs.json
  ↓
后端 JSON Schema 校验
  ↓
后端语义校验
  ↓
后端 CSS 白名单清洗
  ↓
存入 PostgreSQL JSONB
  ↓
前端读取设计数据并渲染
```

### 10.2 前端渲染流程

```text
加载 slide_designs.json
  ↓
校验 templateId 是否存在
  ↓
加载模板组件
  ↓
注入 styleTokens.cssVariables 到当前 slide root
  ↓
清洗并注入 scopedCss
  ↓
根据 layers 按 zIndex 排序
  ↓
LayerRenderer 分发到具体图层组件
  ↓
渲染时间轴、图片、文本、形状、蒙版
```

### 10.3 DOM 结构建议

```html
<section class="kf-slide" data-template="magazine_left" data-category="travel">
  <style scoped-ai-css>...</style>
  <div class="kf-layer kf-background-layer" data-layer-id="bg"></div>
  <div class="kf-layer kf-shape-layer" data-layer-id="warm_light_orb"></div>
  <div class="kf-layer kf-photo-layer" data-layer-id="main_photo"></div>
  <div class="kf-layer kf-shape-layer" data-layer-id="caption_panel"></div>
  <div class="kf-layer kf-text-layer" data-layer-id="caption"></div>
  <div class="kf-layer kf-timeline-layer" data-layer-id="timeline"></div>
</section>
```

---

## 11. AI 输出提示词约束

给 DeepSeek 的系统提示词中必须说明：

```text
你不能生成 HTML。
你不能生成 JavaScript。
你不能生成完整 CSS 文件。
你只能生成符合 slide_design.schema.json 的 JSON。
你只能选择 slide_templates.json 中存在的 templateId。
你只能使用 layer_primitives.json 中存在的 layer.type。
你只能使用 ai_css_whitelist.json 中允许的 CSS Variables 和 scoped CSS 属性。
你必须优先使用用户留言。
如果用户没有留言且 aiCaptionEnabled=true，才生成 AI 文案。
如果用户没有留言且 aiCaptionEnabled=false，不要生成主文案。
你必须输出可解析 JSON，不要输出解释文字。
```

---

## 12. JSON 与 CSS 冲突示例

### 12.1 错误示例

JSON 中定义了文案位置：

```json
{
  "id": "caption",
  "position": { "x": 0.68, "y": 0.58, "w": 0.22, "h": 0.14 }
}
```

AI scoped CSS 又定义：

```css
[data-layer-id='caption'] {
  left: 10%;
  top: 10%;
  width: 80%;
}
```

这是冲突。`left/top/width` 必须被 sanitizer 删除。

### 12.2 正确示例

```css
[data-layer-id='caption'] {
  color: var(--kf-color-text-primary);
  text-shadow: var(--kf-shadow-caption);
  letter-spacing: var(--kf-letter-spacing-caption);
}
```

这只影响视觉，不改变结构。

---

## 13. 开发实施阶段

### 阶段 1：定义配置文件

交付物：

```text
slide_templates.json
layer_primitives.json
ai_css_whitelist.json
design_presets.json
```

验收指标：

```text
至少定义 8 个基础模板
至少定义 10 种图层类型
至少定义完整 CSS Variables 白名单
至少定义 scoped CSS 允许属性和禁止属性
```

### 阶段 2：定义 Schema 与后端校验器

交付物：

```text
slide_design.schema.json
slide_design_validator.py
ai_css_sanitizer.py
```

验收指标：

```text
非法 templateId 会被拒绝
非法 layer.type 会被拒绝
非法 CSS 选择器会被拒绝
非法 CSS 属性会被删除
超出范围的坐标会被修正或拒绝
```

### 阶段 3：实现前端 SlideRenderer

交付物：

```text
SlideRenderer.vue
LayerRenderer.vue
BackgroundLayer.vue
ImageLayer.vue
TextLayer.vue
ShapeLayer.vue
MaskLayer.vue
TimelineLayer.vue
```

验收指标：

```text
能够渲染背景、图片、文本、形状、蒙版、时间轴
能够按照 zIndex 排序
能够注入 CSS Variables
能够注入清洗后的 scoped CSS
能够在窗口变化时保持 16:9 画布比例
```

### 阶段 4：接入 AI 生成流程

交付物：

```text
slide_design_agent.py
slide_design_prompt.md
AI 输出 JSON 示例集
```

验收指标：

```text
AI 输出可以通过 schema 校验
AI 输出可以被前端渲染
有用户留言时不生成替代文案
无用户留言且启用 AI 文案时生成文案
无用户留言且未启用 AI 文案时不生成文案
```

### 阶段 5：视觉质量测试

验收指标：

```text
文字不应明显遮挡照片主体
文字与背景应有足够对比度
图层数量不应导致性能下降
同一分类内整体风格有一致性
不同照片之间有明显审美变化
移动端或小屏幕有降级策略
```

---

## 14. 最终建议

KinFrame 不建议只做一个简单的 `slide_designs.json` 文件来承担所有能力。更合理的是：

```text
系统能力配置文件
+ AI 设计实例文件
+ JSON Schema 校验文件
+ CSS 白名单文件
```

推荐最终结构：

```text
1. slide_templates.json          基础模板体系
2. layer_primitives.json         图层能力体系
3. ai_css_whitelist.json         AI 生成式 CSS 白名单
4. slide_design.schema.json      设计实例校验 Schema
5. slide_designs.json            AI 生成的幻灯片设计数据
6. design_presets.json           可选，复用高质量设计预设
```

其中 `slide_designs.json` 不是孤立文件，而是对前四个系统能力文件的实例化调用。

最终职责边界应保持：

```text
模板决定骨架
模板参数决定布局调整
图层决定元素组合
JSON 决定结构和位置
AI CSS 决定视觉质感
前端渲染器决定最终 DOM 和安全执行
```

这套方案既不会像纯模板填空那样单调，也不会像 AI 直接生成 HTML/CSS/JS 那样失控，比较适合 KinFrame 的长期迭代。
