# KinFrame v0.3 开发计划方案

> 文档版本：v1.0
> 创建日期：2026-05-13
> 对应 PRD 版本：v1.1
> 前置版本：v0.2（已全部完成，见 `code_plan_min_v0.2.md`）

---

## 一、v0.3 最终目标

v0.3 的核心目标是将 KinFrame 从"可用的 AI 幻灯片放映系统"升级为"具有摄影作品集质感的沉浸式家庭影像馆"。具体体现为三个维度：

1. **视觉表现力提升**：从 3 套模板扩展到 8 套，引入 Fill/Shadow 结构化模型、Texture/Vignette 氛围层、设计预设系统和 Scoped CSS 能力，让 AI 生成的每一页幻灯片都具有差异化、高质量的艺术质感。
2. **观看体验打磨**：图片预加载实现 <300ms 切换感知延迟，幻灯片切换动画流畅自然，空分类状态优雅提示，照片位置指示清晰，移动端屏幕适配可用。
3. **工程质量升级**：前后端 Schema 共享消除校验逻辑分歧，Playwright E2E 测试覆盖核心用户路径，v0.3 端到端验收脚本确保全链路可用。

---

## 二、开发阶段总览

v0.3 开发分为 **5 个阶段（Phase）**，按依赖关系顺序推进，每个阶段内部可并行开发独立 issue。

| 阶段 | 名称 | Issue | 核心目标 |
|------|------|-------|----------|
| Phase 1 | 基础配置层 | 01, 02, 07 | 模板扩展、Fill/Shadow 模型、设计预设 |
| Phase 2 | 渲染体验层 | 03, 04, 05, 06 | Texture/Vignette 图层、预加载、转场动画、空状态 |
| Phase 3 | AI 质量层 | 08, 09 | Scoped CSS 安全注入、AI Prompt 增强、设计质量评分 |
| Phase 4 | 用户功能层 | 10, 11, 12, 13 | 用户自助编辑、管理员细粒度重生成、Schema 共享、移动端适配 |
| Phase 5 | 验证交付层 | 14 | Playwright E2E 测试、v0.3 验收脚本 |

### 依赖关系图

```
Phase 1:  01 (Templates) ─────────────────────┐
          02 (Fill & Shadow) ──┬── 03 ──┐       │
          07 (Presets) ────────┘        │       │
                                        │       │
Phase 2:  03 (Texture/Vignette) ←──────┘       │
          04 (Preloading) ─── independent       │
          05 (Transitions) ── independent       │
          06 (Empty State) ── independent       │
                                        │       │
Phase 3:  08 (Scoped CSS) [HITL] ←─────┤       │
          09 (AI Prompt) ←─────────────┼───────┘
                                        │
Phase 4:  10 (User Editing) ── independent
          11 (Admin Regen) ─── independent
          12 (Schema Share) ── independent
          13 (Mobile) ──────── independent

Phase 5:  14 (Playwright + Acceptance) ←── 依赖 01–13 全部完成
```



---

## 三、Phase 1：基础配置层

### 3.1 阶段目标

建立 v0.3 视觉体系的"骨架"——扩展模板库、定义 Fill/Shadow 结构化模型、创建设计预设系统。这是所有后续视觉增强工作的基础，Phase 3 的 AI 增强和 Phase 2 的新图层类型都依赖本阶段的产出。

### 3.2 涉及 Issue

| Issue | 标题 | 类型 | 依赖 |
|-------|------|------|------|
| v0.3-01 | 5 New Slide Templates | AFK | 无 |
| v0.3-02 | Fill & Shadow Models + layer_primitives.json | AFK | 无（01 有帮助但不必须） |
| v0.3-07 | design_presets.json | AFK | 无（01、02 提升预设质量但不必须） |

三个 issue 可并行开发，共享 `frontend/app/slide-renderer/configs/` 目录下的 JSON 配置文件。

### 3.3 各 Issue 实现步骤

#### v0.3-01：5 New Slide Templates

**Step 1** — 在 `frontend/app/slide-renderer/configs/slide_templates.json` 中新增 5 个模板定义：
- `poetic_landscape`（诗意风景）：全屏照片 + 柔光渐变叠加 + 诗意文案位
- `magazine_left`（杂志式左图右文）：照片左 60% + 文案面板右 40%
- `gallery_center`（艺术馆居中）：照片居中 + 宽边距 + museum 风格
- `dark_exhibition`（暗色展厅）：暗色背景 + 照片发光边框 + 戏剧感
- `pet_portrait`（宠物肖像）：照片居中 + 暖色调 + 圆形/大圆角相框

每个模板必须包含完整字段：`slots`、`defaultParams`、`paramSchema`、`allowedLayerTypes`、`maxExtraLayers`、`preferredCategories`。

**Step 2** — 更新前端 `types.ts` 中的 `TemplateId` 联合类型，添加 5 个新 ID。

**Step 3** — 更新 `validateSlideDesign.ts` 中的 `ALLOWED_TEMPLATE_IDS` 集合。

**Step 4** — 更新后端 fallback 设计生成器（`backend/app/services/photo_jobs.py` 的 `build_fallback_design`），使其能根据分类和照片方向从新模板中选择。

**Step 5** — 编写测试：validator 接受新模板 ID、fallback 生成器为 8 个模板均产生有效设计、不同分类匹配不同模板。

#### v0.3-02：Fill & Shadow Models + layer_primitives.json

**Step 1** — 定义 TypeScript 接口（`types.ts`）：
```ts
interface Fill {
  type: 'solid' | 'linearGradient' | 'radialGradient' | 'imageBlur' | 'noise'
  color?: string; angle?: number; center?: { x: number; y: number }
  radius?: number
  stops?: Array<{ color: string; opacity: number; position: number }>
}

interface Shadow {
  enabled: boolean
  type: 'soft' | 'dramatic' | 'glow' | 'inner'
  x: number; y: number; blur: number; spread: number
  color: string; opacity: number
}
```

**Step 2** — 创建 `frontend/app/slide-renderer/configs/layer_primitives.json`，定义所有图层类型的规范：字段、允许值、形状、fill 类型、blend mode、max count、zIndex 范围。覆盖现有 6 种 + 未来 2 种（texture、vignette）共 8 种图层类型。

**Step 3** — 修改 `BackgroundLayer.vue`、`ShapeLayer.vue`、`MaskLayer.vue`，支持从 `layer.fill` 和 `layer.shadow` 读取结构化数据并渲染为对应 CSS。

**Step 4** — 更新前端 validator，校验 Fill（stops 数量 2–5、position/opacity 范围 [0,1]、颜色格式）和 Shadow（type 枚举、blur/opacity 范围）。

**Step 5** — 更新后端 Python validator 和 fallback 生成器，产生合法的 Fill 结构。

**Step 6** — 保持向后兼容：旧的 `style.gradient`/`style.color` 扁平格式仍被接受，自动转换为新 Fill 模型。

**Step 7** — 编写测试：每种 fill type 渲染正确、shadow 变体渲染正确、无效 fill 被拒绝、旧格式自动转换。

#### v0.3-07：design_presets.json

**Step 1** — 创建 `frontend/app/slide-renderer/configs/design_presets.json`，包含 6 类预设：
- **palettes**（≥12 个）：暖色调/冷色调/电影感/柔和/明亮/情绪化
- **shadows**（≥6 个）：柔和/戏剧/发光/内部/经典框架/微妙浮起
- **masks**（≥6 个）：左渐隐/右渐隐/底部渐隐/居中暗角/上下黑边/四角暗化
- **light-orbs**（≥6 个）：暖色/冷色/金色变体
- **timelines**（≥4 个）：极简线条/柔和发光/年份标记/点状
- **fonts**（≥4 个）：Serif 优雅/Sans 精致/混排编辑/温暖圆体

**Step 2** — 实现预设展开逻辑：

- 后端：在 slide design 验证/保存阶段展开 `presetRef`，确保存储的设计始终自包含
- 前端：渲染阶段作为 fallback 展开 `presetRef`

**Step 3** — 未知 `presetRef` 的处理：记录 warning 日志，跳过该图层，不崩溃。

**Step 4** — 编写测试：预设展开正确、未知预设不崩溃、往返一致（preset → expand → validate）。

### 3.4 阶段完成指标

- [ ] `slide_templates.json` 包含 8 套完整模板定义（3 旧 + 5 新）
- [ ] `layer_primitives.json` 覆盖全部 8 种图层类型的完整规范
- [ ] `design_presets.json` 包含 ≥38 个预设（12+6+6+6+4+4）
- [ ] Fill 模型在 Background/Shape/Mask 三种图层中渲染正确
- [ ] Shadow 模型在支持的图层中渲染正确
- [ ] 后端 fallback 生成器能使用全部 8 套模板
- [ ] 前端 validator 接受全部 8 个模板 ID
- [ ] 所有现有测试通过（108 后端 + 42 前端）
- [ ] 向后兼容：v0.2 格式的 slide design 仍可正常渲染

### 3.5 阶段验收脚本

```bash
# 1. 验证配置文件存在且格式正确
cat frontend/app/slide-renderer/configs/slide_templates.json | python3 -c "import json,sys; d=json.load(sys.stdin); assert len(d)>=8, f'Expected >=8 templates, got {len(d)}'"

cat frontend/app/slide-renderer/configs/layer_primitives.json | python3 -c "import json,sys; d=json.load(sys.stdin); assert len(d)>=6, f'Expected >=6 layer types, got {len(d)}'"

cat frontend/app/slide-renderer/configs/design_presets.json | python3 -c "import json,sys; d=json.load(sys.stdin); total=sum(len(v) for v in d.values()); assert total>=38, f'Expected >=38 presets, got {total}'"

# 2. 运行前后端测试套件
just test-backend
just test-frontend

# 3. 启动服务，上传测试照片到各分类，验证 fallback 设计正常渲染
just infra && just backend && just frontend
# 手动验证：访问 /showcase，检查不同分类下的幻灯片渲染
```

---

## 四、Phase 2：渲染体验层

### 4.1 阶段目标

在 Phase 1 的配置基础上，添加 Texture/Vignette 氛围图层、实现图片预加载、添加幻灯片切换动画、完善空分类状态和照片位置指示。这一阶段的产出直接提升用户的视觉和交互体验。

### 4.2 涉及 Issue

| Issue | 标题 | 类型 | 依赖 |
|-------|------|------|------|
| v0.3-03 | Texture + Vignette Layers | AFK | v0.3-02（Fill 模型） |
| v0.3-04 | Image Preloading | AFK | 无 |
| v0.3-05 | Slide Transitions & Animations | AFK | 无 |
| v0.3-06 | Empty Category State + Photo Position | AFK | 无 |

03 依赖 02 的 Fill 模型（noise/radialGradient），04/05/06 完全独立，四个 issue 的开发可最大程度并行。

### 4.3 各 Issue 实现步骤

#### v0.3-03：Texture + Vignette Layers

**Step 1** — 在 `types.ts` 中添加 `TextureLayer` 和 `VignetteLayer` 接口：
```ts
interface TextureLayer extends LayerBase {
  type: 'texture'
  fill: Fill  // 强制 fill.type: 'noise'
  opacity: number
  blendMode: 'overlay' | 'multiply' | 'screen'
}
interface VignetteLayer extends LayerBase {
  type: 'vignette'
  fill: Fill  // 强制 fill.type: 'radialGradient'
  opacity: number
  blendMode: 'multiply'
}
```

**Step 2** — 创建 `TextureLayer.vue`：全屏 SVG/CSS noise 叠加层，参数化 noise 强度和 blend mode。

**Step 3** — 创建 `VignetteLayer.vue`：全屏径向渐变叠加层，透明度中心 → 暗边。

**Step 4** — 在 `LayerRenderer.vue` 中添加两个新图层类型的 dispatch。

**Step 5** — 更新 validator：强制 fill type（texture → noise，vignette → radialGradient）、max count（texture ≤2，vignette ≤1）、opacity [0,1]。

**Step 6** — 编写测试：纹理渲染、暗角渲染、数量上限校验、fill type 校验。

#### v0.3-04：Image Preloading

**Step 1** — 在 `showcase.vue` 中实现预加载逻辑：
- 使用 `new Image()` 预加载当前照片的前后各 1 张（共 2 张）preview 图片
- 维护已加载的 photo ID 集合，避免重复加载

**Step 2** — 预加载触发时机：
- 当前照片渲染完成后触发
- 分类切换时取消旧分类的进行中预加载，开始新分类预加载

**Step 3** — 处理 presigned URL 过期：
- 每次预加载前检查 URL 是否即将过期
- 如果已过期，重新请求 API 获取新 URL

**Step 4** — 加载状态处理：
- 预加载未完成时显示 subtle shimmer/skeleton
- 当前照片始终可见，不出现白屏
- 切换时如果图片已缓存则瞬间切换，否则等待加载完成后切换

**Step 5** — 防抖处理：快速按键时不触发重复预加载或竞态条件。

**Step 6** — 编写测试：预加载行为、分类切换取消、快速导航不产生竞态。

#### v0.3-05：Slide Transitions & Animations

**Step 1** — 定义三种转场效果：
- `fade`（默认）：淡入淡出 400–800ms
- `slide-left`：水平滑动 500–900ms
- `zoom-fade`：微缩放 + 淡入淡出 600–1000ms

**Step 2** — 使用 Vue `<Transition>` 组件实现转场：
- 同行分类内切换：使用 slide 或 fade
- 跨分类切换：始终使用 fade
- 转场类型从 slide design 或全局偏好读取

**Step 3** — 添加 CSS 变量控制：
- `--kf-motion-duration-enter`：进入动画时长
- `--kf-motion-easing`：缓动函数

**Step 4** — 无障碍支持：
- 检测 `prefers-reduced-motion`，禁用所有动画

**Step 5** — 边界处理：
- 快速导航不产生动画堆叠
- 转场中不出现白色闪烁

**Step 6** — 编写测试：转场 class 应用正确、方向正确、reduce-motion 受尊重。

#### v0.3-06：Empty Category State + Photo Position Indicator

**Step 1** — 空分类状态组件：
- 显示分类名称
- 显示提示文案："这一组影像还在等待第一张照片。"
- 上传按钮（链接到 `/upload`）
- 切换到其他分类的视觉提示
- 保持 slide 模板布局结构（背景 + 时间轴区域）

**Step 2** — 照片位置指示器：
- 在底部信息栏添加位置信息："第 3/28 张"
- 照片切换时实时更新
- 分类切换时更新总数和当前位置
- 边界值正确：第 1 张显示 "第 1/28 张"，最后一张显示 "第 28/28 张"

**Step 3** — 编写测试：空状态渲染、位置指示器显示、边界情况（1 张照片、0 张照片）。

### 4.4 阶段完成指标

- [ ] TextureLayer 和 VignetteLayer 渲染正确的视觉效果
- [ ] 新图层类型的数量上限在 validator 中强制执行
- [ ] 图片预加载使相邻照片切换延迟 <300ms
- [ ] 分类切换时预加载正确取消和重建
- [ ] 三种转场效果均可正常播放，无视觉闪烁
- [ ] `prefers-reduced-motion` 时禁用动画
- [ ] 空分类显示完整提示信息 + 上传入口
- [ ] 照片位置指示器在所有导航方式下正确更新
- [ ] 所有现有测试通过（108 后端 + 42 前端）

### 4.5 阶段验收脚本

```bash
# 1. 运行测试套件
just test-backend
just test-frontend

# 2. 启动服务，手动验证
just infra && just backend && just frontend

# 3. 验证 Texture/Vignette 图层
#    在 /showcase 中检查幻灯片是否有 noise 和暗角效果

# 4. 验证预加载
#    打开浏览器 DevTools → Network 标签
#    在 /showcase 中按方向键切换照片，观察预览图加载时序
#    确认相邻照片切换 <300ms

# 5. 验证转场
#    按左右键切换照片，观察淡入淡出/滑动效果
#    切换分类，确认始终为 fade

# 6. 验证空分类
#    导航到无照片的分类，检查空状态页面

# 7. 验证位置指示器
#    检查底部栏是否显示 "第 N/M 张"
#    切换照片和分类，确认数字正确更新
```

---

## 五、Phase 3：AI 质量层

### 5.1 阶段目标

在 Phase 1–2 的配置和渲染基础上，实现 Scoped CSS 的安全注入（HITL 需安全审查）和 AI Prompt 全面增强。这一阶段让 AI 生成的幻灯片设计真正具有高质量和差异化，同时确保安全性不妥协。

### 5.2 涉及 Issue

| Issue | 标题 | 类型 | 依赖 |
|-------|------|------|------|
| v0.3-08 | Scoped CSS Support | **HITL** | v0.3-02 |
| v0.3-09 | AI Prompt & Quality Enhancement | AFK | v0.3-01, v0.3-02, v0.3-07 |

08 为 HITL 类型，需要安全审查 sign-off 后才能合并。09 是 01/02/07 的消费者，必须在三者都完成后开始。

### 5.3 各 Issue 实现步骤

#### v0.3-08：Scoped CSS Support [HITL]

**Step 1** — 定义 Selector 白名单：
- 允许：`.kf-slide`、`.kf-layer`、`.kf-photo-layer`、`.kf-text-layer`、`.kf-shape-layer`、`.kf-mask-layer`、`.kf-timeline-layer`、`.kf-caption`、`.kf-meta`、`.kf-photo-frame`、`.kf-caption-panel` 及 data 属性变体
- 禁止：`html`、`body`、`#app`、`*`、`script`、`iframe`、`input`、`button`、`a[href]`、逗号组合选择器、父级逃逸选择器

**Step 2** — 定义 Property 白名单：
- 允许：`color`、`background-*`、`opacity`、`box-shadow`、`text-shadow`、`filter`、`backdrop-filter`、`mix-blend-mode`、`border-*`、`border-radius`、`letter-spacing`、`line-height`、`font-*`、`text-*`、`transition-*`、`animation-*`、`transform`、`transform-origin`、`clip-path`、`mask-image-*`
- 禁止：`position`、`top/right/bottom/left`、`width/height/min-*`、`z-index`、`display`、`grid-*`、`flex-*`、`justify-content`、`align-items`、`overflow`、`pointer-events`、`cursor`、`content`、`visibility`

**Step 3** — 实现后端 CSS 清洗器（`backend/app/services/ai/css_sanitizer.py`）：
- 解析 CSS 字符串 → AST（使用 `cssutils` 或 `tinycss2`）
- 对每条规则：验证 selector → 标记/丢弃无效规则
- 对每条声明：验证 property → 标记/丢弃无效声明
- 检测 `@import`、`url()`、`javascript:`、`expression()` → 整块丢弃
- 重新序列化安全规则

**Step 4** — 实现前端 CSS 清洗器（`frontend/app/slide-renderer/utils/cssSanitizer.ts`）：
- 与后端相同的规则引擎，TypeScript 实现
- 在 DOM 注入前运行

**Step 5** — 清洗后的 CSS 注入：
- 创建 `<style scoped>` 元素注入当前 slide
- 不影响其他 slide

**Step 6** — 安全审查清单：
- [ ] 无外部资源加载（`url(http...)`、`@import`、`@font-face`）
- [ ] 无 JavaScript 执行（`javascript:`、`expression()`、`behavior`）
- [ ] 无全局页面操作
- [ ] 无隐藏菜单栏或分类导航的能力
- [ ] 无修改 slide 容器布局属性的能力

**Step 7** — 编写测试：合法 scoped CSS 渲染正确、恶意 CSS 被拦截、空 CSS、纯禁止规则、混合合法/非法。

#### v0.3-09：AI Prompt Enhancement & Design Quality Scoring

**Step 1** — 重构 AI Prompt 构建逻辑（`backend/app/services/ai/prompt_builder.py`）：
- 从 `slide_templates.json` 动态读取所有 8 套模板的 slots/params/categories/moods
- 从 `layer_primitives.json` 动态读取所有 8 种图层类型的字段和约束
- 从 `design_presets.json` 动态读取所有预设 ID 和视觉描述
- 包含 caption policy 规则（user_message 优先级、AI caption 开关）
- 强制 JSON-only 输出（无解释性文字）
- Prompt 模板化：配置变化时自动反映到 prompt，无需手动同步

**Step 2** — 构建设计质量评分系统（`backend/app/services/ai/quality_scorer.py`）：
- Text occlusion check：文案区不与照片中心 60% 区域重叠
- Contrast check：文字颜色 vs 背景色达到 WCAG AA（4.5:1）
- Mask intensity check：no mask opacity > 0.65
- Layer count check：总层数 ≤ template.maxExtraLayers + base layers
- Gradient stop check：2–5 stops
- 综合评分 ≥ 阈值 → 接受；< 阈值 → 触发重试

**Step 3** — 重试/回退逻辑：
- 首次质量检查失败 → 将失败详情注入 retry prompt，调用 AI 重新生成
- 重试后仍失败 → 选择分数最高的一次
- 两次都未通过结构性验证 → 回退到确定性 fallback 设计

**Step 4** — 质量评分记录：
- 评分和检查结果记录到 job metadata 或 audit log
- 便于后续分析 AI 设计质量

**Step 5** — 编写测试：prompt 包含正确的模板/图层/预设信息、各项质量检查正确通过/失败、重试行为正确、AI 禁用模式不受影响。

### 5.4 阶段完成指标

- [ ] CSS 清洗器（前后端一致）正确拦截所有类别的恶意 CSS
- [ ] 白名单 selector 和 property 正确放行
- [ ] Scoped CSS 注入不泄露到其他 slide
- [ ] 安全审查 sign-off 完成
- [ ] AI Prompt 从配置文件动态构建，内容完整准确
- [ ] 5 项质量检查均正确运行
- [ ] 质量失败 → 重试 → 回退链路完整
- [ ] 质量评分记录到 job metadata
- [ ] 所有现有测试通过

### 5.5 阶段验收脚本

```bash
# 1. 运行完整测试套件
just test-backend
just test-frontend

# 2. CSS 清洗器单元测试
#    验证：合法 CSS 通过、@import 被拦截、javascript: 被拦截
#    验证：forbidden selector 被丢弃、forbidden property 被丢弃

# 3. AI Prompt 验证（需要 AI 配置）
#    上传测试照片，检查 worker 日志中的 prompt 内容
#    确认 prompt 包含当前全部 8 套模板、图层类型和预设信息

# 4. 质量评分验证
#    检查 quality score 记录在 job metadata 中
#    手动构造低质量设计，验证重试和回退逻辑

# 5. 安全审查
#    提交安全审查请求
#    审查人员确认无安全漏洞后 sign-off
```

---

## 六、Phase 4：用户功能层

### 6.1 阶段目标

完善面向用户和管理员的操作功能：用户可编辑自己照片的文案、管理员可细粒度重生成照片设计、前后端 Schema 统一、移动端屏幕适配。所有 issue 相互独立，可完全并行开发。

### 6.2 涉及 Issue

| Issue | 标题 | 类型 | 依赖 |
|-------|------|------|------|
| v0.3-10 | User Self-Service Editing | AFK | 无 |
| v0.3-11 | Admin Granular Regeneration | AFK | 无 |
| v0.3-12 | Schema Sharing | AFK | 无 |
| v0.3-13 | Mobile Responsiveness | AFK | 无 |

### 6.3 各 Issue 实现步骤

#### v0.3-10：User Self-Service Photo Editing

**Step 1** — 后端 API：`PATCH /api/photos/{photo_id}/message`
- 验证用户是否为照片的上传者（非上传者返回 403）
- 仅更新 `user_message` 字段
- 如果 `caption_source = admin`（管理员已手动覆盖），保留管理员覆盖，不更新 `final_caption`
- 如果无管理员覆盖，`final_caption = user_message`（用户文案优先于 AI）
- 记录 audit log

**Step 2** — 前端 UI：
- 在 `/photo/[id]` 页面，如果当前用户是上传者，显示"编辑文案"按钮
- 点击后弹出 inline 文本输入框，预填当前 `user_message`
- 保存后立即更新显示，无需刷新页面

**Step 3** — 编写测试：用户编辑自己的照片成功、用户被阻止编辑他人的照片（403）、管理员覆盖被保留、无覆盖时 `final_caption` 更新、audit log 记录。

#### v0.3-11：Admin Granular Regeneration

**Step 1** — 后端 API：`POST /api/admin/photos/{photo_id}/regenerate`，接受 body：
```json
{"scope": "caption | template | css_tokens | full | fallback"}
```
- `caption`：仅重跑 AI caption 生成
- `template`：仅重跑模板选择（保留 layers/CSS/caption）
- `css_tokens`：仅重跑 style token 生成
- `full`：完整重跑（当前行为）
- `fallback`：丢弃 AI 设计，生成确定性 fallback

**Step 2** — 每种 scope 映射到特定 AI job 类型或 job 参数。

**Step 3** — AI 禁用时：caption/template/css/full 返回明确错误；fallback 始终可用。

**Step 4** — 每次重生成记录 audit log（scope + 结果）。

**Step 5** — 前端 UI：
- 将单个"Regenerate"按钮替换为下拉菜单或分段按钮组
- 触发前显示确认对话框
- 重生成进行中时禁用按钮
- 显示 job 状态轮询

**Step 6** — 编写测试：每种 scope 仅改变相关字段、fallback 在 AI 禁用时可用、AI-required scope 在 AI 禁用时返回错误、audit log 条目、UI 下拉菜单。

#### v0.3-12：Schema Sharing Between Frontend and Backend

**Step 1** — 审查并完善共享的 `slide_design.schema.json`：
- 确保覆盖所有 v0.2+ 字段：version、photoId、templateId、canvas、templateParams、mediaRefs、captionPolicy、styleTokens（cssVariables、scopedCss）、layers[]（所有 8 种类型）、timeline、renderPolicy、aiMeta
- 确保覆盖所有 v0.3 新增字段：fill、shadow、presetRef

**Step 2** — 后端验证：
- Python validator 通过 `jsonschema` 库使用共享 schema 进行第一层结构验证
- 确认覆盖所有当前字段

**Step 3** — 前端验证：
- TypeScript validator 通过 `ajv` 使用共享 schema 进行第一层结构验证
- 在语义验证之前运行

**Step 4** — 验证分层：
1. JSON Schema 验证（结构：必填字段、类型、范围）— 前后端共享
2. 语义验证（上下文：templateId 存在、图层类型在白名单、CSS 变量在白名单）— 语言特定
3. 安全清洗（CSS 清洗、HTML/JS 拒绝）— 语言特定

**Step 5** — CI 检查：添加 CI 步骤检测前后端 schema 文件是否一致。

**Step 6** — 编写测试：后端验证 → 前端验证 → 结果一致、相同无效设计被双方拒绝、相同有效设计被双方接受。

#### v0.3-13：Mobile Responsiveness

**Step 1** — Slide 画布自适应：
- 保持 16:9 宽高比，缩放至适配视口宽度
- 上下 letterbox（黑边）而非裁剪照片
- 使用 CSS 而非 JS 控制布局

**Step 2** — 分类栏适配：
- 默认隐藏
- 从屏幕左边缘右滑显示（或点击 hamburger 指示器）
- 选择后自动隐藏
- `C` 键对应触摸操作

**Step 3** — 顶部菜单适配：
- 点击顶部区域显示
- 所有菜单项触控目标 ≥44px
- 选择后或点其他区域后自动隐藏

**Step 4** — 手势导航：
- 左滑 → 下一张照片，右滑 → 上一张照片
- 上滑 → 下一个分类，下滑 → 上一个分类（或长滑垂直切换分类）

**Step 5** — UI 元素缩放：
- 时间轴压缩为点状指示器（空间紧张时隐藏文字标签）
- 文案字体响应式缩放（使用 `clamp()`）
- 底部栏仅显示位置指示器 "3/28"；时间和位置点击/长按显示

**Step 6** — CSS 策略：
- 使用媒体查询和容器查询
- 避免 JS 布局计算
- 目标断点：375px–428px 宽度（iPhone SE 到 Pro Max）

**Step 7** — 非目标：
- 不做 PWA
- 不优化平板（平板使用桌面布局）
- 不添加移动端独有功能

**Step 8** — 编写测试：响应式布局验证（移动端断点）、桌面端无回归（≥1280px）。

### 6.4 阶段完成指标

- [ ] 普通用户可编辑自己照片的 `user_message`
- [ ] 用户无法编辑他人照片（403）
- [ ] 管理员覆盖保护机制正确
- [ ] 5 种重生成 scope 均可正常工作
- [ ] fallback 在 AI 禁用时可用
- [ ] 共享 schema 覆盖所有 v0.2+ 和 v0.3 字段
- [ ] 前后端使用同一 schema 文件进行结构验证
- [ ] showcase 在 375–428px 宽度下可用
- [ ] 手势导航（滑动切换照片/分类）工作正常
- [ ] 桌面布局无回归（≥1280px）
- [ ] 所有现有测试通过

### 6.5 阶段验收脚本

```bash
# 1. 运行测试套件
just test-backend
just test-frontend

# 2. 用户自助编辑验证
#    用普通用户登录，上传照片，访问 /photo/[id]
#    验证编辑按钮可见，编辑文案并保存
#    用其他用户登录，访问同一照片，验证编辑按钮不可见

# 3. 管理员细粒度重生成验证
#    管理员访问 admin 页面
#    验证重生成下拉菜单包含 5 个选项
#    分别测试每种 scope 的效果

# 4. Schema 共享验证
diff <(cat backend/app/schemas/slide_design.schema.json | python3 -c "import json,sys; print(json.dumps(json.load(sys.stdin), sort_keys=True))") \
     <(cat frontend/app/slide-renderer/configs/slide_design.schema.json | python3 -c "import json,sys; print(json.dumps(json.load(sys.stdin), sort_keys=True))")

# 5. 移动端验证
#    打开 Chrome DevTools → 切换为 iPhone SE 视口 (375px)
#    访问 /showcase
#    验证：slide 16:9 缩放、手势滑动、分类栏滑出、触控目标 ≥44px
```

---

## 七、Phase 5：验证交付层

### 7.1 阶段目标

通过 Playwright E2E 浏览器自动化测试和 v0.3 端到端验收脚本，系统化验证所有 v0.3 功能在全链路下的正确性。这是 v0.3 发布的最后一道质量关卡。

### 7.2 涉及 Issue

| Issue | 标题 | 类型 | 依赖 |
|-------|------|------|------|
| v0.3-14 | Playwright E2E + v0.3 Acceptance | AFK | v0.3-01 至 v0.3-13 全部 |

### 7.3 实现步骤

#### Part A：Playwright E2E 测试套件

**Step 1** — 安装配置 Playwright：
- `pnpm add -D @playwright/test` 在 frontend/
- 创建 `frontend/playwright.config.ts`（headless、localhost:3000、失败截图）
- 创建 `frontend/tests/e2e/` 目录

**Step 2** — 编写 10+ 个测试场景：
1. **Login flow**：访问 `/login` → 输入凭据 → 验证重定向到 `/showcase`
2. **Showcase rendering**：验证 slide 显示照片 + 时间轴 + 底部栏
3. **Keyboard navigation**：ArrowRight → 下一张、ArrowLeft → 上一张、ArrowDown → 下一分类、ArrowUp → 上一分类
4. **Mouse navigation**：左键点击 → 上一张、右键点击 → 下一张（无上下文菜单）、滚轮上下 → 分类切换
5. **Menu behavior**：鼠标移到顶部 → 菜单显示、鼠标移开 → 菜单隐藏、`M` 键切换菜单
6. **Category bar**：鼠标移到左侧 → 分类栏显示并高亮当前分类、`C` 键切换
7. **Photo detail**：导航到照片详情页、验证元数据显示
8. **Upload flow**：上传测试图片 → 验证出现在 processing 状态 → 等待 ready
9. **Admin functions**：管理员可见 admin UI 元素、普通用户不可见
10. **Empty state**：导航到空分类、验证空状态提示出现

**Step 3** — 运行配置：
- 本地 dev server（`localhost:3000`）
- 默认 headless
- 失败时截图到 `frontend/tests/e2e/screenshots/`

**Step 4** — 添加 `just test-e2e` recipe。

#### Part B：v0.3 验收脚本

**Step 5** — 创建 `scripts/v0.3-acceptance.sh`，包含 10 个步骤：
1. 验证基础设施运行（PostgreSQL、Redis、MinIO）
2. 创建测试用户（admin + member），登录验证 cookies
3. 上传测试照片到所有分类
4. 运行 worker 处理所有照片
5. 验证 API：showcase 返回 ready 照片 + 合法 slide design
6. 验证 API：admin 端点（jobs、categories、audit logs）
7. 验证 API：v0.3 新字段存在（fill model、shadow model、presets、新模板 ID）
8. 运行 Playwright 测试（headless）
9. 验证备份/恢复包含 v0.3 数据
10. 验证移动端视口渲染（Playwright 移动端模拟）

**Step 6** — 添加 `just accept-v0-3` recipe。

**Step 7** — 更新 `README.md`：
- v0.3 功能列表
- 新增 `just` 命令：`test-e2e`、`accept-v0-3`
- Playwright 环境设置说明

### 7.4 阶段完成指标

- [ ] 10+ Playwright 测试场景全部通过
- [ ] 键盘导航测试：左右键切换照片、上下键切换分类
- [ ] 鼠标导航测试：左键上一张、右键下一张（无上下文菜单）
- [ ] 菜单显示/隐藏行为在浏览器中验证通过
- [ ] Admin vs 普通用户的可见性边界验证通过
- [ ] `just accept-v0-3` 从干净状态开始端到端通过
- [ ] Playwright 测试集成到 `just test-e2e` recipe
- [ ] 备份/恢复验证包含 v0.3 数据字段
- [ ] 移动端视口渲染验证通过
- [ ] README 已更新

### 7.5 阶段验收脚本

```bash
# 1. 从干净状态启动
just infra-down && just infra

# 2. 运行完整 v0.3 验收脚本
just accept-v0-3

# 3. 期望输出：所有 10 个步骤 PASS

# 4. 运行 Playwright E2E 测试
just test-e2e

# 5. 期望输出：所有测试用例 PASS
```

---

## 八、关键风险与缓解措施

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| Scoped CSS 安全漏洞 | 高 — XSS/UI 劫持 | 中 | HITL issue，安全审查 sign-off 前不合入；前后端双重清洗 |
| AI 设计质量不稳定 | 中 — 用户体验差 | 高 | 质量评分 + 自动重试 + fallback 回退三层保障 |
| 模板/Presets 审美质量不足 | 中 — 幻灯片缺乏质感 | 中 | 预设由人工精心设计（非 AI 生成），可迭代改进 |
| 移动端手势与桌面键鼠冲突 | 低 — 交互异常 | 低 | 触摸事件和鼠标/键盘事件互斥处理 |
| Schema 前后端不同步 | 中 — 校验结果不一致 | 中 | CI 检查 schema 文件是否一致；共享单一源文件 |
| Presigned URL 过期导致预加载失败 | 低 — 图片加载失败 | 低 | 预加载前检查 URL 时效，过期则重新获取 |
| 快速导航导致动画堆叠 | 低 — 视觉闪烁 | 中 | 转场队列管理，当前动画完成前忽略新的转场请求 |

## 九、总体时间估算

| Phase | Issue 数 | 预估工作量 | 关键路径 |
|-------|---------|-----------|----------|
| Phase 1 (基础配置层) | 3 | 5–7 天 | 02 → 03 链路的起点 |
| Phase 2 (渲染体验层) | 4 | 6–8 天 | 03 依赖 02 |
| Phase 3 (AI 质量层) | 2 | 5–7 天 | 09 依赖 01/02/07 |
| Phase 4 (用户功能层) | 4 | 4–6 天 | 全部并行 |
| Phase 5 (验证交付层) | 1 | 3–4 天 | 依赖全部 |
| **总计** | **14** | **23–32 天** | |

可并行度高的 Phase（1、2、4）可通过多人协作缩短实际日历时间。

## 十、Issue 参考索引

| ID | 文件 | 标题 | 类型 |
|----|------|------|------|
| v0.3-01 | `docs/issues_v0.3/v0.3-01-5-new-slide-templates.md` | 5 New Slide Templates | AFK |
| v0.3-02 | `docs/issues_v0.3/v0.3-02-fill-shadow-models.md` | Fill & Shadow Models + layer_primitives.json | AFK |
| v0.3-03 | `docs/issues_v0.3/v0.3-03-texture-vignette-layers.md` | Texture + Vignette Layers | AFK |
| v0.3-04 | `docs/issues_v0.3/v0.3-04-image-preloading.md` | Image Preloading | AFK |
| v0.3-05 | `docs/issues_v0.3/v0.3-05-slide-transitions.md` | Slide Transitions & Animations | AFK |
| v0.3-06 | `docs/issues_v0.3/v0.3-06-empty-category-ux.md` | Empty Category State + Photo Position | AFK |
| v0.3-07 | `docs/issues_v0.3/v0.3-07-design-presets.md` | design_presets.json | AFK |
| v0.3-08 | `docs/issues_v0.3/v0.3-08-scoped-css.md` | Scoped CSS Support | **HITL** |
| v0.3-09 | `docs/issues_v0.3/v0.3-09-ai-prompt-quality.md` | AI Prompt & Quality Enhancement | AFK |
| v0.3-10 | `docs/issues_v0.3/v0.3-10-user-self-service.md` | User Self-Service Editing | AFK |
| v0.3-11 | `docs/issues_v0.3/v0.3-11-admin-granular-regeneration.md` | Admin Granular Regeneration | AFK |
| v0.3-12 | `docs/issues_v0.3/v0.3-12-schema-sharing.md` | Schema Sharing | AFK |
| v0.3-13 | `docs/issues_v0.3/v0.3-13-mobile-responsive.md` | Mobile Responsiveness | AFK |
| v0.3-14 | `docs/issues_v0.3/v0.3-14-playwright-e2e-acceptance.md` | Playwright E2E + v0.3 Acceptance | AFK |

## 十一、全局行为规范准则：
  1. 任何新写的脚本/命令，写完必须实际执行一次，不依赖脑内模拟，用实际运行结果说话。
  2. 区分"单元测试通过"和"端到端验收通过"，不混用这两个概念
  3. 遇到错误时，先诊断根因再修改，不试错式修复