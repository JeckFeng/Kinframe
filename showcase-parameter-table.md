# Showcase Frontend Parameter Table

这份表用于微调当前 `showcase` 的双层 slide 效果。  
行号基于当前工作区代码状态。

## 参数表

全局比例参数：

- `SHOWCASE_GLOBAL_SCALE = 1.5`
- 代码位置：`frontend/composables/useShowcaseRail.ts`
- 作用范围：背景层图片、前景层黑色遮罩、前景层镂空窗格会一起按这个比例同步放大或缩小。

波形错落参数：

- `SHOWCASE_MAX_UP_OFFSET_PX = 72`
- `SHOWCASE_MAX_DOWN_OFFSET_PX = 72`
- 代码位置：`frontend/composables/useShowcaseRail.ts`
- 作用范围：背景层图片会在统一高度包络里交替上下错落；前景镂空窗格和黑色遮罩高度也会一起抬高到能包住最高图和最低图。

| # | 参数 | 当前值 / 表达式 | 代码位置 | 调整说明 |
|---|---|---|---|---|
| 1 | 背景层图片大小尺寸参数 | `frameHeightPx = scale( clamp(viewportHeight * 0.34, 220, 380) )`；`frameWidthPx = scale( clamp(baseFrameHeightPx * 1.28, 280, 520) )` | `frontend/composables/useShowcaseRail.ts:89-99` | 这是背景层每张图的基础尺寸来源。当前还会再乘上全局比例 `SHOWCASE_GLOBAL_SCALE = 1.5`。 |
| 1 | 背景层图片大小尺寸参数 | `slot.height = layout.holeHeightPx`；`image.height = layout.frameHeightPx` | `frontend/components/showcase/ShowcaseRail.vue:49-60` | 背景层现在是“更高的统一包络 slot + 内部真实图片高度”，为高低错落留出了垂直空间。 |
| 1 | 背景层图片大小尺寸参数 | `width: 100%`；`height: 100%` | `frontend/assets/css/showcase.css:117-120` | 背景图始终铺满自己的 slot。 |
| 2 | 背景层图片放大比例参数 | 当前没有独立的数值型 `scale(...)` 参数；实际效果由 `object-fit: cover` 决定 | `frontend/assets/css/showcase.css:117-125` | 目前背景图“放大/裁切感”不是单独比例，而是由 `object-fit: cover` 加上第 1 项的 slot 尺寸共同决定。若你想做独立缩放，最合适的插入点就是 `.showcase-slide-image` 这里。 |
| 3 | 背景层平移速度 `v` | 基准速度系数为 `1.0`，体现在 `backgroundTravelXPx = -(renderBaseOffsetPx + sharedRenderX)` | `frontend/composables/useShowcaseRail.ts:193,201` | 当前背景层速度没有单独常量，`sharedRenderX` 本身就是背景层速度基准。如果想调慢/调快，可把 `sharedRenderX` 改成 `sharedRenderX * 系数`。 |
| 4 | 前景层黑色遮罩颜色 | `#000000` | `frontend/assets/css/showcase.css:149-153` | 四块遮罩 matte 的颜色都由这里控制。 |
| 5 | 前景层黑色遮罩透明度 | 当前基础透明度为 `100%`，因为使用的是 `#000000`；`shell` 已固定为 `opacity: 1` | `frontend/assets/css/showcase.css:133,149-153`；`frontend/composables/useShowcaseRail.ts:170` | 静态透明度没有单独 alpha，当前是全不透明黑。如果要整体变透明，最直接是把 `#000000` 改成 `rgba(0, 0, 0, alpha)`。 |
| 6 | 前景层镂空窗格大小尺寸参数 | `holeWidthPx = frameWidthPx`；`holeHeightPx = frameHeightPx + SHOWCASE_MAX_UP_OFFSET_PX + SHOWCASE_MAX_DOWN_OFFSET_PX` | `frontend/composables/useShowcaseRail.ts:100,118-119` | 洞口宽度保持和图片一致，高度则抬高到能同时包住波峰和波谷。所有洞口宽高仍然统一。 |
| 6 | 前景层镂空窗格大小尺寸参数 | `--hole-width`；`--hole-height` | `frontend/components/showcase/ShowcaseCard.vue:29-30` | 把洞口尺寸写成 CSS 变量。 |
| 6 | 前景层镂空窗格大小尺寸参数 | `width: var(--hole-width)`；`height: var(--hole-height)` | `frontend/assets/css/showcase.css:185-193` | 真正决定镂空窗格 DOM 盒子的尺寸。 |
| 7 | 前景层黑色遮罩大小尺寸参数 | `matteWidthPx = frameWidthPx + mattePadXPx * 2`；`matteHeightPx = holeHeightPx + mattePadYPx * 2` | `frontend/composables/useShowcaseRail.ts:116-117` | 遮罩外框高度现在跟随统一窗格高度一起变大，保证能完整包住高低错落后的图片。 |
| 11 | 背景层图片高低错落参数 | `backgroundImageOffsetYPx = index % 2 === 0 ? 0 : SHOWCASE_MAX_UP_OFFSET_PX + SHOWCASE_MAX_DOWN_OFFSET_PX` | `frontend/composables/useShowcaseRail.ts:107,115`；`frontend/components/showcase/ShowcaseRail.vue:56-60` | 当前实现是交替高低错落。偶数项在高位，奇数项在低位。整条 slide 的倾斜角度不变，只是每张图在 slot 内做垂直偏移。 |
| 7 | 前景层黑色遮罩大小尺寸参数 | `--matte-width`；`--matte-height` | `frontend/components/showcase/ShowcaseCard.vue:27-28` | 把遮罩外框尺寸写入 CSS 变量。 |
| 7 | 前景层黑色遮罩大小尺寸参数 | `width: var(--matte-width)`；`height: var(--matte-height)` | `frontend/assets/css/showcase.css:138-147` | 真正决定黑色遮罩外框尺寸的地方。 |
| 8 | 文案板颜色参数 | `rgba(0, 0, 0, 0.8)` | `frontend/assets/css/showcase.css:220-230` | 外层文案板背景色。 |
| 8 | 文案板颜色参数 | `rgba(0, 0, 0, 0.8)` | `frontend/assets/css/showcase.css:233-238` | 内层文案内容区背景色。当前内外两层颜色一致。 |
| 9 | 文案板透明度参数 | `0.8`（写在 `rgba(0, 0, 0, 0.8)` 的 alpha 通道里） | `frontend/assets/css/showcase.css:227,237` | 文案板透明度不单独拆成变量，当前直接写死在颜色 alpha 里。 |
| 10 | 前景层平移速度参数 | `DEFAULT_MASK_SPEED_MULTIPLIER = 1.5` | `frontend/composables/useShowcaseRail.ts:14` | 这是前景层相对于背景层的速度倍率主参数。 |
| 10 | 前景层平移速度参数 | `maskSpeedMultiplier = input.maskSpeedMultiplier ?? DEFAULT_MASK_SPEED_MULTIPLIER`；`foregroundTravelXPx = -(renderBaseOffsetPx + sharedRenderX * maskSpeedMultiplier)` | `frontend/composables/useShowcaseRail.ts:187,202` | 这里是前景层速度倍率的实际使用位置。 |

## 额外说明

### 1. 当前哪些参数是“独立参数”

- 比较独立、适合直接调的参数：
  - `frontend/composables/useShowcaseRail.ts:14`
  - `frontend/composables/useShowcaseRail.ts:15-17`
  - `frontend/composables/useShowcaseRail.ts:91-100`
  - `frontend/assets/css/showcase.css:152`
  - `frontend/assets/css/showcase.css:227,237`

### 2. 当前哪些参数不是“独立参数”

- 背景层图片放大比例目前不是单独数值，而是由这几处共同形成：
  - `frontend/composables/useShowcaseRail.ts:84-85`
  - `frontend/assets/css/showcase.css:117-125`
- 如果后面你想把它变成一个真正可调的“缩放比例参数”，最合适的新增位置是：
  - `frontend/assets/css/showcase.css:117-125`
  - 例如在 `.showcase-slide-image` 上额外加 `transform: scale(...)`

### 3. 最常用的微调入口

- 想调背景图整体大小：先看 `frontend/composables/useShowcaseRail.ts:15,91-100`
- 想调背景图高低错落：先看 `frontend/composables/useShowcaseRail.ts:16-17,107`
- 想调前景洞口大小：先看 `frontend/composables/useShowcaseRail.ts:118-119`
- 想调黑色遮罩外框大小：先看 `frontend/composables/useShowcaseRail.ts:116-117`
- 想调前景/背景速度差：先看 `frontend/composables/useShowcaseRail.ts:14,187,202`
- 想调黑色和透明度：先看 `frontend/assets/css/showcase.css:149-153,227,237`

## 时间与地点文字全局参数

这组参数都定义在：

- `frontend/assets/css/showcase.css:1-31`

生效规则：

1. `-desktop` 变量保存桌面端参数
2. `-mobile` 变量保存移动端参数
3. 不带后缀的变量是当前生效变量
4. `max-width: 768px` 时，不带后缀的变量会自动切到 `-mobile`

### 时间文字参数

桌面端原始变量：

| 参数 | 当前值 | 作用 |
|---|---|---|
| `--showcase-info-time-font-family-desktop` | `inherit` | 时间文字桌面端字体族 |
| `--showcase-info-time-font-style-desktop` | `normal` | 时间文字桌面端字形 |
| `--showcase-info-time-font-size-desktop` | `12px` | 时间文字桌面端字号 |
| `--showcase-info-time-font-weight-desktop` | `500` | 时间文字桌面端字重 |
| `--showcase-info-time-letter-spacing-desktop` | `0.14em` | 时间文字桌面端字距 |
| `--showcase-info-time-line-height-desktop` | `1.2` | 时间文字桌面端行高 |
| `--showcase-info-time-text-transform-desktop` | `uppercase` | 时间文字桌面端大小写转换 |
| `--showcase-info-time-color-desktop` | `rgba(255, 255, 255, 0.96)` | 时间文字桌面端颜色 |
| `--showcase-info-time-text-shadow-desktop` | `0 1px 10px rgba(0, 0, 0, 0.42)` | 时间文字桌面端阴影 |

移动端原始变量：

| 参数 | 当前值 | 作用 |
|---|---|---|
| `--showcase-info-time-font-family-mobile` | `inherit` | 时间文字移动端字体族 |
| `--showcase-info-time-font-style-mobile` | `normal` | 时间文字移动端字形 |
| `--showcase-info-time-font-size-mobile` | `11px` | 时间文字移动端字号 |
| `--showcase-info-time-font-weight-mobile` | `500` | 时间文字移动端字重 |
| `--showcase-info-time-letter-spacing-mobile` | `0.12em` | 时间文字移动端字距 |
| `--showcase-info-time-line-height-mobile` | `1.2` | 时间文字移动端行高 |
| `--showcase-info-time-text-transform-mobile` | `uppercase` | 时间文字移动端大小写转换 |
| `--showcase-info-time-color-mobile` | `rgba(255, 255, 255, 0.96)` | 时间文字移动端颜色 |
| `--showcase-info-time-text-shadow-mobile` | `0 1px 10px rgba(0, 0, 0, 0.42)` | 时间文字移动端阴影 |

当前生效变量：

| 参数 | 当前默认值 | 作用 |
|---|---|---|
| `--showcase-info-time-font-family` | `var(--showcase-info-time-font-family-desktop)` | 时间文字当前生效字体族 |
| `--showcase-info-time-font-style` | `var(--showcase-info-time-font-style-desktop)` | 时间文字当前生效字形 |
| `--showcase-info-time-font-size` | `var(--showcase-info-time-font-size-desktop)` | 时间文字当前生效字号 |
| `--showcase-info-time-font-weight` | `var(--showcase-info-time-font-weight-desktop)` | 时间文字当前生效字重 |
| `--showcase-info-time-letter-spacing` | `var(--showcase-info-time-letter-spacing-desktop)` | 时间文字当前生效字距 |
| `--showcase-info-time-line-height` | `var(--showcase-info-time-line-height-desktop)` | 时间文字当前生效行高 |
| `--showcase-info-time-text-transform` | `var(--showcase-info-time-text-transform-desktop)` | 时间文字当前生效大小写转换 |
| `--showcase-info-time-color` | `var(--showcase-info-time-color-desktop)` | 时间文字当前生效颜色 |
| `--showcase-info-time-text-shadow` | `var(--showcase-info-time-text-shadow-desktop)` | 时间文字当前生效阴影 |

时间文字实际使用位置：

- `frontend/assets/css/showcase.css:270-284`

### 地点文字参数

桌面端原始变量：

| 参数 | 当前值 | 作用 |
|---|---|---|
| `--showcase-info-location-font-family-desktop` | `inherit` | 地点文字桌面端字体族 |
| `--showcase-info-location-font-style-desktop` | `normal` | 地点文字桌面端字形 |
| `--showcase-info-location-font-size-desktop` | `12px` | 地点文字桌面端字号 |
| `--showcase-info-location-font-weight-desktop` | `500` | 地点文字桌面端字重 |
| `--showcase-info-location-letter-spacing-desktop` | `0.12em` | 地点文字桌面端字距 |
| `--showcase-info-location-line-height-desktop` | `1.25` | 地点文字桌面端行高 |
| `--showcase-info-location-text-transform-desktop` | `uppercase` | 地点文字桌面端大小写转换 |
| `--showcase-info-location-color-desktop` | `rgba(255, 255, 255, 0.58)` | 地点文字桌面端颜色 |
| `--showcase-info-location-text-shadow-desktop` | `0 1px 10px rgba(0, 0, 0, 0.42)` | 地点文字桌面端阴影 |

移动端原始变量：

| 参数 | 当前值 | 作用 |
|---|---|---|
| `--showcase-info-location-font-family-mobile` | `inherit` | 地点文字移动端字体族 |
| `--showcase-info-location-font-style-mobile` | `normal` | 地点文字移动端字形 |
| `--showcase-info-location-font-size-mobile` | `11px` | 地点文字移动端字号 |
| `--showcase-info-location-font-weight-mobile` | `500` | 地点文字移动端字重 |
| `--showcase-info-location-letter-spacing-mobile` | `0.1em` | 地点文字移动端字距 |
| `--showcase-info-location-line-height-mobile` | `1.25` | 地点文字移动端行高 |
| `--showcase-info-location-text-transform-mobile` | `uppercase` | 地点文字移动端大小写转换 |
| `--showcase-info-location-color-mobile` | `rgba(255, 255, 255, 0.62)` | 地点文字移动端颜色 |
| `--showcase-info-location-text-shadow-mobile` | `0 1px 10px rgba(0, 0, 0, 0.42)` | 地点文字移动端阴影 |

当前生效变量：

| 参数 | 当前默认值 | 作用 |
|---|---|---|
| `--showcase-info-location-font-family` | `var(--showcase-info-location-font-family-desktop)` | 地点文字当前生效字体族 |
| `--showcase-info-location-font-style` | `var(--showcase-info-location-font-style-desktop)` | 地点文字当前生效字形 |
| `--showcase-info-location-font-size` | `var(--showcase-info-location-font-size-desktop)` | 地点文字当前生效字号 |
| `--showcase-info-location-font-weight` | `var(--showcase-info-location-font-weight-desktop)` | 地点文字当前生效字重 |
| `--showcase-info-location-letter-spacing` | `var(--showcase-info-location-letter-spacing-desktop)` | 地点文字当前生效字距 |
| `--showcase-info-location-line-height` | `var(--showcase-info-location-line-height-desktop)` | 地点文字当前生效行高 |
| `--showcase-info-location-text-transform` | `var(--showcase-info-location-text-transform-desktop)` | 地点文字当前生效大小写转换 |
| `--showcase-info-location-color` | `var(--showcase-info-location-color-desktop)` | 地点文字当前生效颜色 |
| `--showcase-info-location-text-shadow` | `var(--showcase-info-location-text-shadow-desktop)` | 地点文字当前生效阴影 |

地点文字实际使用位置：

- `frontend/assets/css/showcase.css:286-300`
