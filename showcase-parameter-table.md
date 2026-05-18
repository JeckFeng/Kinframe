# Showcase Frontend Parameter Table

这份表用于微调当前 `showcase` 的双层 slide 效果。  
行号基于当前工作区代码状态。

## 参数表

| # | 参数 | 当前值 / 表达式 | 代码位置 | 调整说明 |
|---|---|---|---|---|
| 1 | 背景层图片大小尺寸参数 | `frameHeightPx = clamp(viewportHeight * 0.34, 220, 380)`；`frameWidthPx = clamp(frameHeightPx * 1.28, 280, 520)` | `frontend/composables/useShowcaseRail.ts:84-85` | 这是背景层每张图的基础尺寸来源。增大 `0.34`、`220/380`、`1.28`、`280/520` 都会改变背景图卡的最终显示尺寸。 |
| 1 | 背景层图片大小尺寸参数 | `width: layout.frameWidthPx`；`height: layout.frameHeightPx` | `frontend/components/showcase/ShowcaseRail.vue:49-53` | 这里把上面的布局尺寸实际写进背景层每张图片 slot。 |
| 1 | 背景层图片大小尺寸参数 | `width: 100%`；`height: 100%` | `frontend/assets/css/showcase.css:117-120` | 背景图始终铺满自己的 slot。 |
| 2 | 背景层图片放大比例参数 | 当前没有独立的数值型 `scale(...)` 参数；实际效果由 `object-fit: cover` 决定 | `frontend/assets/css/showcase.css:117-125` | 目前背景图“放大/裁切感”不是单独比例，而是由 `object-fit: cover` 加上第 1 项的 slot 尺寸共同决定。若你想做独立缩放，最合适的插入点就是 `.showcase-slide-image` 这里。 |
| 3 | 背景层平移速度 `v` | 基准速度系数为 `1.0`，体现在 `backgroundTravelXPx = -(renderBaseOffsetPx + sharedRenderX)` | `frontend/composables/useShowcaseRail.ts:183,191` | 当前背景层速度没有单独常量，`sharedRenderX` 本身就是背景层速度基准。如果想调慢/调快，可把 `sharedRenderX` 改成 `sharedRenderX * 系数`。 |
| 4 | 前景层黑色遮罩颜色 | `#000000` | `frontend/assets/css/showcase.css:149-153` | 四块遮罩 matte 的颜色都由这里控制。 |
| 5 | 前景层黑色遮罩透明度 | 当前基础透明度为 `100%`，因为使用的是 `#000000`；另外整块 slot 还叠加了动态 `opacity` | `frontend/assets/css/showcase.css:133,149-153`；`frontend/components/showcase/ShowcaseCard.vue:33`；`frontend/composables/useShowcaseRail.ts:160` | 静态透明度没有单独 alpha，当前是全不透明黑。若要整体变透明，最直接是把 `#000000` 改成 `rgba(0, 0, 0, alpha)`。同时要注意 `--slot-opacity` 还会根据 active/inactive 做动态淡化。 |
| 6 | 前景层镂空窗格大小尺寸参数 | `holeWidthPx = frameWidthPx`；`holeHeightPx = frameHeightPx` | `frontend/composables/useShowcaseRail.ts:103-104` | 这是洞口本身的尺寸来源。想让洞更大/更小，可以在这里直接改成相对 `frameWidthPx` / `frameHeightPx` 的比例。 |
| 6 | 前景层镂空窗格大小尺寸参数 | `--hole-width`；`--hole-height` | `frontend/components/showcase/ShowcaseCard.vue:29-30` | 把洞口尺寸写成 CSS 变量。 |
| 6 | 前景层镂空窗格大小尺寸参数 | `width: var(--hole-width)`；`height: var(--hole-height)` | `frontend/assets/css/showcase.css:185-193` | 真正决定镂空窗格 DOM 盒子的尺寸。 |
| 7 | 前景层黑色遮罩大小尺寸参数 | `matteWidthPx = frameWidthPx + mattePadXPx * 2`；`matteHeightPx = frameHeightPx + mattePadYPx * 2` | `frontend/composables/useShowcaseRail.ts:86-87,101-102` | 遮罩外框尺寸由图片尺寸再加上下左右 padding 得来。调 `mattePadXPx` / `mattePadYPx` 是最直接的办法。 |
| 7 | 前景层黑色遮罩大小尺寸参数 | `--matte-width`；`--matte-height` | `frontend/components/showcase/ShowcaseCard.vue:27-28` | 把遮罩外框尺寸写入 CSS 变量。 |
| 7 | 前景层黑色遮罩大小尺寸参数 | `width: var(--matte-width)`；`height: var(--matte-height)` | `frontend/assets/css/showcase.css:138-147` | 真正决定黑色遮罩外框尺寸的地方。 |
| 8 | 文案板颜色参数 | `rgba(0, 0, 0, 0.8)` | `frontend/assets/css/showcase.css:220-230` | 外层文案板背景色。 |
| 8 | 文案板颜色参数 | `rgba(0, 0, 0, 0.8)` | `frontend/assets/css/showcase.css:233-238` | 内层文案内容区背景色。当前内外两层颜色一致。 |
| 9 | 文案板透明度参数 | `0.8`（写在 `rgba(0, 0, 0, 0.8)` 的 alpha 通道里） | `frontend/assets/css/showcase.css:227,237` | 文案板透明度不单独拆成变量，当前直接写死在颜色 alpha 里。 |
| 10 | 前景层平移速度参数 | `DEFAULT_MASK_SPEED_MULTIPLIER = 1.5` | `frontend/composables/useShowcaseRail.ts:14` | 这是前景层相对于背景层的速度倍率主参数。 |
| 10 | 前景层平移速度参数 | `maskSpeedMultiplier = input.maskSpeedMultiplier ?? DEFAULT_MASK_SPEED_MULTIPLIER`；`foregroundTravelXPx = -(renderBaseOffsetPx + sharedRenderX * maskSpeedMultiplier)` | `frontend/composables/useShowcaseRail.ts:177,192` | 这里是前景层速度倍率的实际使用位置。 |

## 额外说明

### 1. 当前哪些参数是“独立参数”

- 比较独立、适合直接调的参数：
  - `frontend/composables/useShowcaseRail.ts:84-87`
  - `frontend/composables/useShowcaseRail.ts:14`
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

- 想调背景图整体大小：先看 `frontend/composables/useShowcaseRail.ts:84-85`
- 想调前景洞口大小：先看 `frontend/composables/useShowcaseRail.ts:103-104`
- 想调黑色遮罩外框大小：先看 `frontend/composables/useShowcaseRail.ts:86-87,101-102`
- 想调前景/背景速度差：先看 `frontend/composables/useShowcaseRail.ts:14,177,192`
- 想调黑色和透明度：先看 `frontend/assets/css/showcase.css:149-153,227,237`
