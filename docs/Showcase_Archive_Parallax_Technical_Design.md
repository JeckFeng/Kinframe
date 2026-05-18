# KinFrame Showcase Archive Parallax 技术设计稿

> 适用范围：本设计稿用于将 KinFrame 当前 `/showcase` 页面从“单张全屏 slide 切换”重构为“THE SHIFT 风格的黑底 archive rail 展示页”。
>
> 本文档只定义前端技术设计，不直接修改实现代码。

---

## 1. 目标与边界

### 1.1 目标

重构 `/showcase` 页面，使其具备以下能力：

1. 同一分类内通过滚轮浏览横向图片轨道，而不是切换分类。
2. 分类切换改为 `ArrowUp` / `ArrowDown` 键。
3. 图片卡片整体呈倾斜展示效果。
4. 每张图片右上角显示拍摄时间。
5. 每张图片左下角显示地点和文案。
6. 页面背景为纯黑色。
7. 当前时间轴展示逻辑在 showcase 页面停用，改为底部进度缩略图。
8. 轨道具备平滑滚动、中心高亮、图内视差和分类内浏览位置记忆。

### 1.2 非目标

本阶段不做以下内容：

1. 不引入 WebGL / OGL / Three.js。
2. 不复用当前 `SlideRenderer` 作为 showcase 主渲染器。
3. 不删除全项目的 `timeline` layer，只在 showcase 页面停用。
4. 不改动后台 slide design 生成逻辑。
5. 不在本设计稿阶段落地代码实现。

### 1.3 约束

1. 不新增动画依赖，使用原生 `requestAnimationFrame + transform`。
2. 保留现有鉴权、顶部导航和分类数据来源。
3. 保留每个分类各自的浏览记忆。
4. 必须支持 `prefers-reduced-motion` 降级。

---

## 2. 总体架构

### 2.1 页面职责拆分

`frontend/pages/showcase.vue`

1. 页面级状态与鉴权。
2. 分类数据加载。
3. 当前分类切换。
4. Rail 浏览记忆保存与恢复。
5. 顶部导航、分类侧边栏和页面级快捷键。
6. Auto-play 与 rail 的对接。

`frontend/components/showcase/ShowcaseStage.vue`

1. 舞台容器。
2. 组合 rail 与进度缩略图。
3. 对父层暴露 rail 的跳转、恢复和快照能力。

`frontend/components/showcase/ShowcaseRail.vue`

1. 横向轨道渲染。
2. 三段复制与无限循环。
3. wheel / touch 输入。
4. 惯性、lerp、中心项判定。
5. 每张卡片的视觉态计算。

`frontend/components/showcase/ShowcaseCard.vue`

1. 单张图片卡片结构。
2. 图内视差。
3. 时间、地点、文案布局。
4. active / passive / offscreen 视觉差异。

`frontend/components/showcase/ShowcaseProgressStrip.vue`

1. 底部缩略图进度条。
2. 当前项高亮。
3. 点击缩略图跳转。

`frontend/composables/useShowcaseRail.ts`

1. 轨道运动计算。
2. card visual state 计算。
3. 交互状态管理。
4. 外部方法暴露。

`frontend/composables/useShowcaseCategoryMemory.ts`

1. 按分类保存 rail 快照。
2. 恢复分类浏览位置。

---

## 3. 文件级改造清单

### 3.1 需要新增的文件

```text
frontend/components/showcase/ShowcaseStage.vue
frontend/components/showcase/ShowcaseRail.vue
frontend/components/showcase/ShowcaseCard.vue
frontend/components/showcase/ShowcaseProgressStrip.vue
frontend/components/showcase/ShowcaseCategorySidebar.vue
frontend/composables/useShowcaseRail.ts
frontend/composables/useShowcaseCategoryMemory.ts
frontend/types/showcase.ts
frontend/assets/css/showcase.css
docs/Showcase_Archive_Parallax_Technical_Design.md
```

### 3.2 需要修改的文件

```text
frontend/pages/showcase.vue
frontend/assets/css/main.css
frontend/assets/css/transitions.css
frontend/tests/e2e/showcase.spec.ts
frontend/types/api.ts
backend/app/schemas/showcase.py         # 可选：补 thumbnail_url
backend/app/api/showcase.py             # 可选：补 thumbnail_url
```

### 3.3 保留但不再作为 showcase 主通路的文件

```text
frontend/app/slide-renderer/components/SlideRenderer.vue
frontend/app/slide-renderer/components/LayerRenderer.vue
frontend/app/slide-renderer/components/TimelineLayer.vue
frontend/composables/useSlideNavigation.ts
```

---

## 4. 共享类型设计

共享类型建议落在：

`frontend/types/showcase.ts`

```ts
import type { ShowcaseCategory, ShowcasePhotoItem } from '~/types/api'

export type ShowcaseRailInteractionSource =
  | 'wheel'
  | 'touch'
  | 'thumb'
  | 'keyboard'
  | 'autoplay'
  | 'restore'
  | 'programmatic'

export type ShowcaseRailInteractionState =
  | 'idle'
  | 'driving'
  | 'settling'
  | 'snapped'
  | 'suspended'

export interface ShowcaseRailSnapshot {
  currentX: number
  targetX: number
  activeIndex: number
  activePhotoId: string | null
  itemPitchPx: number
  loopSpanPx: number
  timestamp: number
}

export interface ShowcaseRailActiveChangePayload {
  activeIndex: number
  activePhotoId: string | null
  direction: -1 | 0 | 1
  source: ShowcaseRailInteractionSource
  snapshot: ShowcaseRailSnapshot
}

export interface ShowcaseRailInteractionStatePayload {
  state: ShowcaseRailInteractionState
  source: ShowcaseRailInteractionSource | null
}

export interface ShowcaseCardVisualState {
  index: number
  translateX: number
  imageTranslateX: number
  captionTranslateX: number
  timeTranslateX: number
  opacity: number
  scale: number
  depth: number
  normalizedProgress: number
  isVisible: boolean
  isActive: boolean
}

export interface ShowcaseRailConfig {
  loop: boolean
  wheelMultiplier: number
  touchMultiplier: number
  lerp: number
  snapThresholdPx: number
  activeBiasPx: number
  overscanPx: number
}

export interface ShowcaseCategoryMemoryEntry {
  category: ShowcaseCategory
  activeIndex: number
  snapshot: ShowcaseRailSnapshot | null
  updatedAt: number
}

export interface ShowcaseProgressJumpPayload {
  index: number
  source: 'thumb'
}

export interface ShowcaseStageExpose {
  jumpToIndex: (index: number, source?: ShowcaseRailInteractionSource) => void
  jumpBy: (step: number, source?: ShowcaseRailInteractionSource) => void
  restoreSnapshot: (snapshot: ShowcaseRailSnapshot | null | undefined) => void
  getSnapshot: () => ShowcaseRailSnapshot
  suspend: () => void
  resume: () => void
}
```

### 4.1 `ShowcasePhotoItem` 的接口扩展

建议在 `frontend/types/api.ts` 和后端接口中加一个可选缩略图字段：

```ts
export interface ShowcasePhotoItem {
  photo: Photo
  preview_url: string | null
  thumbnail_url?: string | null
  slide_design: Record<string, unknown> | null
}
```

原因：

1. 底部进度条应该优先使用更小的缩略图资源。
2. 不加也能做，但会退化为用 `preview_url` 生成缩略图，代价偏高。

---

## 5. 页面与组件 API 设计

## 5.1 `frontend/pages/showcase.vue`

### 页面内部状态

```ts
const categories = ref<PhotoCategoryDefinition[]>([])
const photos = ref<ShowcasePhotoItem[]>([])
const activeCategory = ref<ShowcaseCategory>('life')
const activePhotoIndex = ref(0)
const pending = ref(true)
const errorMessage = ref('')
const reducedMotion = ref(false)
const categoryVisible = ref(false)

const stageRef = ref<ShowcaseStageExpose | null>(null)
const categoryMemory = useShowcaseCategoryMemory()
```

### 页面方法签名

```ts
async function loadShowcase(category: ShowcaseCategory): Promise<void>
async function switchCategory(offset: -1 | 1): Promise<void>
function handleRailActiveChange(payload: ShowcaseRailActiveChangePayload): void
function handleRailSettle(snapshot: ShowcaseRailSnapshot): void
function handleWheelCapture(event: WheelEvent): void
function advancePhoto(step: -1 | 1, source?: ShowcaseRailInteractionSource): void
function restoreCategorySnapshot(category: ShowcaseCategory): ShowcaseRailSnapshot | null
```

### 页面模板接线

```vue
<ShowcaseStage
  ref="stageRef"
  :photos="photos"
  :active-category="activeCategory"
  :initial-snapshot="restoreCategorySnapshot(activeCategory)"
  :reduced-motion="reducedMotion"
  @active-change="handleRailActiveChange"
  @settle="handleRailSettle"
/>
```

### 页面快捷键定义

1. `ArrowUp`：切换到上一个分类。
2. `ArrowDown`：切换到下一个分类。
3. `ArrowLeft`：可选，当前分类上一张。
4. `ArrowRight`：可选，当前分类下一张。
5. `Space`：如保留 auto-play，则切换 auto-play。
6. `C`：切换分类侧边栏显示。
7. `M`：保留去地图页。

其中 3、4 为兼容增强，不是这轮的核心验收项。

---

## 5.2 `frontend/components/showcase/ShowcaseStage.vue`

### Props

```ts
interface ShowcaseStageProps {
  photos: ShowcasePhotoItem[]
  activeCategory: ShowcaseCategory
  initialSnapshot?: ShowcaseRailSnapshot | null
  reducedMotion?: boolean
  showProgress?: boolean
}
```

### Emits

```ts
const emit = defineEmits<{
  'active-change': [payload: ShowcaseRailActiveChangePayload]
  settle: [snapshot: ShowcaseRailSnapshot]
  'interaction-state-change': [payload: ShowcaseRailInteractionStatePayload]
}>()
```

### Expose

```ts
defineExpose<ShowcaseStageExpose>({
  jumpToIndex,
  jumpBy,
  restoreSnapshot,
  getSnapshot,
  suspend,
  resume,
})
```

### 组件职责

1. 承载 rail 和 progress strip。
2. 通过 `ref` 调用 `ShowcaseRail` 的 exposed methods。
3. 在 rail active index 改变时同步更新 `ShowcaseProgressStrip`。
4. 接收 progress strip 的 `jump` 事件并调用 `jumpToIndex(index, 'thumb')`。

---

## 5.3 `frontend/components/showcase/ShowcaseRail.vue`

### Props

```ts
interface ShowcaseRailProps {
  photos: ShowcasePhotoItem[]
  initialSnapshot?: ShowcaseRailSnapshot | null
  reducedMotion?: boolean
  config?: Partial<ShowcaseRailConfig>
}
```

### Emits

```ts
const emit = defineEmits<{
  'active-change': [payload: ShowcaseRailActiveChangePayload]
  settle: [snapshot: ShowcaseRailSnapshot]
  'interaction-state-change': [payload: ShowcaseRailInteractionStatePayload]
}>()
```

### Expose

```ts
export interface ShowcaseRailExpose {
  jumpToIndex: (index: number, source?: ShowcaseRailInteractionSource) => void
  jumpBy: (step: number, source?: ShowcaseRailInteractionSource) => void
  restoreSnapshot: (snapshot: ShowcaseRailSnapshot | null | undefined) => void
  getSnapshot: () => ShowcaseRailSnapshot
  suspend: () => void
  resume: () => void
}
```

### 内部依赖

```ts
const {
  viewportRef,
  railRef,
  cardStates,
  activeIndex,
  interactionState,
  registerCardEl,
  onWheel,
  onTouchStart,
  onTouchMove,
  onTouchEnd,
  jumpToIndex,
  jumpBy,
  restoreSnapshot,
  getSnapshot,
  suspend,
  resume,
} = useShowcaseRail(...)
```

### 组件职责

1. 渲染三段复制轨道 `before/current/after`。
2. 把每个逻辑 index 的 visual state 传给 `ShowcaseCard`。
3. 在 viewport 上监听 wheel / touch。
4. 不关心分类切换与数据请求。

---

## 5.4 `frontend/components/showcase/ShowcaseCard.vue`

### Props

```ts
interface ShowcaseCardProps {
  item: ShowcasePhotoItem
  index: number
  visual: ShowcaseCardVisualState
  previewUrl: string | null
  thumbnailUrl?: string | null
  timeLabel: string
  locationLabel: string
  captionLabel: string
}
```

### Emits

当前版本不强制需要 emits。

如果后续希望点击 active 卡片进入详情页，再补：

```ts
const emit = defineEmits<{
  select: [photoId: string]
}>()
```

### 组件职责

1. 只渲染单张卡片。
2. 不参与滚动计算。
3. 根据 `visual` 使用 CSS variables 写 transform。
4. 时间、地点、文案都从 props 直接进入，不读全局状态。

---

## 5.5 `frontend/components/showcase/ShowcaseProgressStrip.vue`

### Props

```ts
interface ShowcaseProgressStripProps {
  photos: ShowcasePhotoItem[]
  activeIndex: number
  reducedMotion?: boolean
}
```

### Emits

```ts
const emit = defineEmits<{
  jump: [payload: ShowcaseProgressJumpPayload]
}>()
```

### 组件职责

1. 用 `thumbnail_url` 或 `preview_url` 渲染底部缩略图。
2. 高亮当前 active 项。
3. 点击缩略图发出 `jump` 事件。
4. 内部维护缩略图条的滚入可视范围逻辑。

---

## 5.6 `frontend/components/showcase/ShowcaseCategorySidebar.vue`

### Props

```ts
interface ShowcaseCategorySidebarProps {
  categories: PhotoCategoryDefinition[]
  activeCategory: ShowcaseCategory
  visible?: boolean
}
```

### Emits

```ts
const emit = defineEmits<{
  select: [category: ShowcaseCategory]
}>()
```

### 组件职责

1. 展示当前分类和相邻分类。
2. 不处理数据加载。
3. 点击只发出 `select(category)`。

---

## 6. composable 设计

## 6.1 `frontend/composables/useShowcaseRail.ts`

### 入参

```ts
interface UseShowcaseRailOptions {
  photos: Ref<ShowcasePhotoItem[]>
  reducedMotion: Ref<boolean>
  initialSnapshot: Ref<ShowcaseRailSnapshot | null | undefined>
  config?: Partial<ShowcaseRailConfig>
  onActiveChange?: (payload: ShowcaseRailActiveChangePayload) => void
  onSettle?: (snapshot: ShowcaseRailSnapshot) => void
  onInteractionStateChange?: (payload: ShowcaseRailInteractionStatePayload) => void
}
```

### 返回值

```ts
interface UseShowcaseRailReturn {
  viewportRef: Ref<HTMLElement | null>
  railRef: Ref<HTMLElement | null>
  cardStates: ShallowRef<ShowcaseCardVisualState[]>
  activeIndex: Ref<number>
  currentX: Ref<number>
  targetX: Ref<number>
  interactionState: Ref<ShowcaseRailInteractionState>
  registerCardEl: (index: number, el: HTMLElement | null) => void
  onWheel: (event: WheelEvent) => void
  onTouchStart: (event: TouchEvent) => void
  onTouchMove: (event: TouchEvent) => void
  onTouchEnd: (event: TouchEvent) => void
  jumpToIndex: (index: number, source?: ShowcaseRailInteractionSource) => void
  jumpBy: (step: number, source?: ShowcaseRailInteractionSource) => void
  restoreSnapshot: (snapshot: ShowcaseRailSnapshot | null | undefined) => void
  getSnapshot: () => ShowcaseRailSnapshot
  suspend: () => void
  resume: () => void
  recalc: () => void
  destroy: () => void
}
```

### 内部状态

```ts
const currentX = ref(0)
const targetX = ref(0)
const activeIndex = ref(0)
const interactionState = ref<ShowcaseRailInteractionState>('idle')
const isTicking = ref(false)

const viewportWidth = ref(0)
const itemPitchPx = ref(0)
const loopSpanPx = ref(0)
const cardEls = shallowRef<HTMLElement[]>([])
```

### 内部方法

```ts
function startTick(): void
function stopTickIfSettled(): void
function tick(): void
function normalizeDelta(deltaY: number): number
function normalizeLoopX(x: number): number
function computeActiveIndex(): number
function computeCardStates(): ShowcaseCardVisualState[]
function setInteractionState(
  state: ShowcaseRailInteractionState,
  source: ShowcaseRailInteractionSource | null,
): void
```

### 关键计算规则

1. `targetX` 只由 wheel / touch / jump / restore 改变。
2. `currentX` 每帧用 `lerp(currentX, targetX, lerpFactor)` 追踪。
3. `activeIndex` 按“离视口中心最近的卡片”计算。
4. `cardStates` 每帧根据 `normalizedProgress` 生成。
5. `normalizeLoopX` 保证无限循环不会硬停在边界。

---

## 6.2 `frontend/composables/useShowcaseCategoryMemory.ts`

### 入参

无显式入参。

### 返回值

```ts
interface UseShowcaseCategoryMemoryReturn {
  save: (category: ShowcaseCategory, entry: ShowcaseCategoryMemoryEntry) => void
  load: (category: ShowcaseCategory) => ShowcaseCategoryMemoryEntry | null
  has: (category: ShowcaseCategory) => boolean
  clear: (category?: ShowcaseCategory) => void
}
```

### 存储策略

1. 第一阶段仅存内存 `Map<ShowcaseCategory, ShowcaseCategoryMemoryEntry>`。
2. 不进 localStorage，避免跨账号污染。
3. 切分类前保存，分类载入后恢复。

---

## 7. 事件契约

## 7.1 rail active change

```ts
type ActiveChangeEvent = ShowcaseRailActiveChangePayload
```

触发时机：

1. 当前中心卡片发生变化。
2. rail 在 `wheel`、`touch`、`thumb jump`、`restore`、`autoplay` 后进入新的中心项。

父层用途：

1. 更新 `activePhotoIndex`。
2. 同步底部计数。
3. 为 auto-play 或未来详情联动提供当前图索引。

## 7.2 rail settle

```ts
type SettleEvent = ShowcaseRailSnapshot
```

触发时机：

1. `currentX` 与 `targetX` 差值小于阈值。
2. rail 停止高频滚动。

父层用途：

1. 保存分类浏览快照。
2. 用于切分类后恢复位置。

## 7.3 rail interaction-state-change

```ts
type InteractionStateChangeEvent = ShowcaseRailInteractionStatePayload
```

用途：

1. 分类切换期间先 `suspend` rail。
2. 顶部 UI 如需和“正在滚动”联动，可直接订阅。

## 7.4 progress jump

```ts
type ProgressJumpEvent = {
  index: number
  source: 'thumb'
}
```

用途：

1. 缩略图条点击跳转到指定图片。

---

## 8. DOM 结构设计

## 8.1 `showcase.vue` 页面骨架

```html
<section
  class="showcase-page"
  data-mode="archive-rail"
  data-category="life"
  data-motion="full"
>
  <header class="showcase-topbar">...</header>
  <aside class="showcase-sidebar-shell">...</aside>

  <main class="showcase-main">
    <ShowcaseStage />
  </main>
</section>
```

### 顶层 data attributes

1. `data-mode="archive-rail"`
2. `data-category="<slug>"`
3. `data-motion="full|reduced"`
4. `data-state="pending|ready|switching|error"`

## 8.2 `ShowcaseStage.vue`

```html
<section class="showcase-stage" data-rail-state="settling">
  <div class="showcase-stage-viewport">
    <ShowcaseRail />
  </div>

  <footer class="showcase-stage-progress">
    <ShowcaseProgressStrip />
  </footer>
</section>
```

## 8.3 `ShowcaseRail.vue`

```html
<div
  ref="viewportRef"
  class="showcase-viewport"
  @wheel.prevent="onWheel"
  @touchstart.passive="onTouchStart"
  @touchmove.prevent="onTouchMove"
  @touchend="onTouchEnd"
>
  <div ref="railRef" class="showcase-rail">
    <div class="showcase-rail-copy" data-copy="before">
      <article class="showcase-card-shell" data-copy="before" data-index="0">...</article>
    </div>

    <div class="showcase-rail-copy" data-copy="current">
      <article class="showcase-card-shell" data-copy="current" data-index="0">...</article>
    </div>

    <div class="showcase-rail-copy" data-copy="after">
      <article class="showcase-card-shell" data-copy="after" data-index="0">...</article>
    </div>
  </div>
</div>
```

## 8.4 `ShowcaseCard.vue`

```html
<article
  class="showcase-card-shell"
  data-index="3"
  data-active="true"
  data-visible="true"
  style="
    --card-translate-x: 123px;
    --card-scale: 1;
    --card-opacity: 1;
    --image-translate-x: 28px;
    --caption-translate-x: 10px;
    --time-translate-x: 8px;
  "
>
  <div class="showcase-card">
    <div class="showcase-card-media-frame">
      <img class="showcase-card-media" src="..." alt="" />
    </div>

    <time class="showcase-card-time">2026.05.17</time>

    <div class="showcase-card-caption">
      <p class="showcase-card-location">Shanghai, China</p>
      <p class="showcase-card-copy">家庭聚会结束后路过的街道，晚风很轻。</p>
    </div>
  </div>
</article>
```

## 8.5 `ShowcaseProgressStrip.vue`

```html
<nav class="showcase-progress-strip" aria-label="Showcase progress">
  <div class="showcase-progress-thumbs">
    <button class="showcase-progress-thumb" data-active="false">
      <img class="showcase-progress-thumb-image" src="..." alt="" />
    </button>
  </div>

  <div class="showcase-progress-meta">
    <span class="showcase-progress-count">03 / 18</span>
  </div>
</nav>
```

---

## 9. 状态与数据流

## 9.1 页面挂载流

```text
showcase.vue mounted
-> loadMe()
-> loadShowcase(activeCategory)
-> restoreCategorySnapshot(activeCategory)
-> render ShowcaseStage
-> ShowcaseRail restoreSnapshot(...)
-> emit active-change
-> page sync activePhotoIndex
```

## 9.2 rail wheel 流

```text
wheel input
-> ShowcaseRail.onWheel(event)
-> targetX += normalizedDelta * wheelMultiplier
-> interactionState = driving
-> requestAnimationFrame tick
-> currentX lerp toward targetX
-> recompute cardStates
-> recompute activeIndex
-> if activeIndex changed emit active-change
-> when settled emit settle
```

## 9.3 分类切换流

```text
ArrowUp / ArrowDown
-> showcase.vue switchCategory(offset)
-> stageRef.getSnapshot()
-> categoryMemory.save(oldCategory, snapshot)
-> stageRef.suspend()
-> loadShowcase(newCategory)
-> restoreCategorySnapshot(newCategory)
-> remount / restore rail
-> stageRef.resume()
```

## 9.4 缩略图点击流

```text
thumbnail click
-> ShowcaseProgressStrip emit jump({ index, source: 'thumb' })
-> ShowcaseStage jumpToIndex(index, 'thumb')
-> ShowcaseRail targetX updated
-> tick
-> emit active-change
-> emit settle
```

## 9.5 auto-play 流

如果保留 auto-play：

```text
timer fires
-> showcase.vue advancePhoto(1, 'autoplay')
-> stageRef.jumpBy(1, 'autoplay')
-> rail settles
-> active index and snapshot update
```

---

## 10. 视觉参数与 CSS 变量

`frontend/assets/css/showcase.css`

```css
:root {
  --showcase-bg: #000000;
  --showcase-text: rgba(255, 255, 255, 0.92);
  --showcase-text-muted: rgba(255, 255, 255, 0.56);
  --showcase-text-dim: rgba(255, 255, 255, 0.32);

  --showcase-rail-tilt-desktop: 12deg;
  --showcase-rail-tilt-tablet: 10deg;
  --showcase-rail-tilt-mobile: 7deg;

  --showcase-card-width-desktop: 34vw;
  --showcase-card-width-tablet: 46vw;
  --showcase-card-width-mobile: 72vw;

  --showcase-card-gap-desktop: 7vw;
  --showcase-card-gap-tablet: 8vw;
  --showcase-card-gap-mobile: 10vw;

  --showcase-card-inactive-opacity: 0.38;
  --showcase-card-passive-scale: 0.92;
  --showcase-card-active-scale: 1;

  --showcase-parallax-image-x-desktop: 56px;
  --showcase-parallax-image-x-tablet: 40px;
  --showcase-parallax-image-x-mobile: 24px;

  --showcase-parallax-caption-x-desktop: 18px;
  --showcase-parallax-caption-x-tablet: 14px;
  --showcase-parallax-caption-x-mobile: 10px;

  --showcase-card-time-size: 12px;
  --showcase-card-location-size: 12px;
  --showcase-card-copy-size: 16px;

  --showcase-progress-thumb-width: 72px;
  --showcase-progress-thumb-height: 48px;
  --showcase-progress-thumb-opacity: 0.4;
  --showcase-progress-thumb-active-scale: 1.08;

  --showcase-ease: cubic-bezier(0.22, 1, 0.36, 1);
}
```

### 10.1 card transform 变量

每张卡片壳层通过内联 CSS variables 驱动：

```css
.showcase-card-shell {
  transform:
    translate3d(var(--card-translate-x), 0, 0)
    scale(var(--card-scale));
  opacity: var(--card-opacity);
}

.showcase-card-media {
  transform: translate3d(var(--image-translate-x), 0, 0) scale(1.06);
}

.showcase-card-caption {
  transform: translate3d(var(--caption-translate-x), 0, 0);
}

.showcase-card-time {
  transform: translate3d(var(--time-translate-x), 0, 0);
}
```

### 10.2 reduced motion 规则

```css
@media (prefers-reduced-motion: reduce) {
  .showcase-card-shell,
  .showcase-card-media,
  .showcase-card-caption,
  .showcase-card-time,
  .showcase-progress-thumb {
    transition: none !important;
    transform: none !important;
  }
}
```

---

## 11. 关键实现约定

## 11.1 不再把 wheel 映射为分类切换

当前 `showcase.vue` 的 wheel 聚合逻辑需要移除，wheel 只交给 `ShowcaseRail`。

## 11.2 分类切换前必须保存快照

切分类前先调用：

```ts
const snapshot = stageRef.value?.getSnapshot()
categoryMemory.save(activeCategory.value, {
  category: activeCategory.value,
  activeIndex: activePhotoIndex.value,
  snapshot: snapshot ?? null,
  updatedAt: Date.now(),
})
```

## 11.3 active index 以视觉中心为准

不能靠“滚动次数 + 1”推导当前图，必须用卡片中心点离视口中心的最小距离计算。

## 11.4 rail 渲染不走高频 Vue 全量重排

每帧只更新：

1. `cardStates`
2. rail 根节点 transform
3. 当前索引

避免每帧改动大块响应式列表结构。

---

## 12. 测试设计

`frontend/tests/e2e/showcase.spec.ts`

需要重写或新增的测试：

1. showcase 加载后黑底舞台可见。
2. 右上角时间可见。
3. 左下角地点与文案可见。
4. wheel 会切换同一分类内的当前图片。
5. `ArrowDown` 切换到下一个分类。
6. `ArrowUp` 切换到上一个分类。
7. 缩略图条可见并高亮当前项。
8. 点击缩略图能跳转到指定图片。
9. 切换分类后返回原分类时恢复浏览位置。
10. reduced motion 条件下仍能正常浏览。

建议新增断言辅助：

```ts
async function readActiveProgressIndex(page: Page): Promise<number>
async function waitForRailSettle(page: Page): Promise<void>
```

---

## 13. 实施顺序

### Phase 1：骨架搭建

1. 新建 `showcase.css`。
2. 新建 `types/showcase.ts`。
3. 新建 `ShowcaseStage / ShowcaseRail / ShowcaseCard / ShowcaseProgressStrip / ShowcaseCategorySidebar` 骨架。

### Phase 2：交互接管

1. `showcase.vue` 改成页面壳层。
2. 移除旧 `SlideRenderer` 主通路。
3. 接入 `useShowcaseRail`。

### Phase 3：运动与视觉

1. 实现惯性、lerp、三段复制和 active index 判定。
2. 实现卡片倾斜、图内视差、时间/地点/文案布局。
3. 实现缩略图进度条。

### Phase 4：记忆与回归

1. 接入 `useShowcaseCategoryMemory`。
2. 恢复 auto-play 对接。
3. 更新 Playwright 测试。

---

## 14. 风险与决策

### 已决定

1. showcase 重构为固定视觉系统，不继续以 slide template 为主。
2. 第一阶段不用 WebGL。
3. 时间轴在 showcase 页面停用，改为缩略图进度条。
4. 不新增外部动画库。

### 风险

1. `preview_url` 直接作为缩略图资源时可能过重。
2. 轨道三段复制如果 index 映射处理不严谨，容易出现 active index 抖动。
3. 每帧 transform 如果实现不当，移动端会掉帧。

### 对应缓解

1. 接口补 `thumbnail_url`。
2. 所有 active index 判定都基于逻辑 index，而不是复制轨道中的 DOM 顺序。
3. 只更新 transform / opacity，不做布局级属性变更。

---

## 15. 验收标准

满足以下条件即可视为该设计稿对应的前端改造完成：

1. `/showcase` 页面不再渲染单张 `SlideRenderer` 作为主视觉。
2. 同一分类内能通过滚轮平滑浏览横向图片轨道。
3. `ArrowUp` / `ArrowDown` 可切换分类。
4. 图片右上角有拍摄时间，左下角有地点和文案。
5. 页面背景为纯黑。
6. 时间轴不再出现在 showcase 页面，底部替换为缩略图进度条。
7. 切换分类后，返回原分类能恢复上次浏览位置。
8. E2E 测试覆盖新的核心交互路径。

