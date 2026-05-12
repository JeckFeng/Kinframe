# KinFrame v0.1 PRD 转向版开发计划

本文档基于 `docs/Kinframe_PRD.md` 和 `docs/Frontend_Rendering_Strategies.md` 重写。此前 v0.1 已完成登录、上传、MinIO、EXIF、preview、异步 Worker、批量上传和备份恢复，但产品方向已经从“家庭相册管理”调整为“AI 驱动的家庭影像 PPT 放映”。因此 v0.1 后续目标改为：在尽量复用现有底座的前提下，完成 `/showcase` 全屏放映和受控 Slide Renderer 的最小可用版本。

## 1. v0.1 新目标

v0.1 不再继续投入传统相册体验升级，而是完成以下最小闭环：

1. 保留现有登录、上传、MinIO、EXIF、preview、thumbnail、Worker 和备份恢复。
2. 重构当前系统，使登录后默认进入 `/showcase`。
3. 引入可扩展分类和 PPT 播放所需的时间轴数据。
4. 为每张照片生成可播放的 fallback `slide_design_json`。
5. 实现最小 Slide Renderer，能渲染安全、受控的全屏 slide。
6. 实现隐藏顶部菜单、隐藏左侧分类栏、键盘导航和底部时间轴。
7. 暂不接入真实 Ollama/DeepSeek，但保留 AI 工作流接口和数据结构。

## 2. v0.1 明确不做

1. 不在本阶段完成完整 AI 视觉识别。
2. 不在本阶段完成 DeepSeek 高质量设计生成。
3. 不实现复杂 scoped CSS，第一版只允许 CSS Variables。
4. 不做公开注册、社交分享、评论、点赞。
5. 不做地图相册、人脸识别、年度回忆。
6. 不把图库作为主体验；图库只作为辅助浏览页面保留。
7. 不保证当前 Docker 镜像支持 HEIC 转换；若不可用必须明确失败。

## 3. 阶段总览

| 阶段 | 名称 | 核心目标 | 优先级 |
|---|---|---|---|
| 0 | 当前系统重构与 PRD 基线切换 | 把已完成 v0.1 从相册路线调整到 PPT 放映路线 | P0 |
| 1 | 数据模型升级 | 分类、照片状态、AI 字段、slide_designs 表 | P0 |
| 2 | Fallback Slide Design 生成 | 无 AI 环境下每张照片都有可播放设计 JSON | P0 |
| 3 | 最小 Slide Renderer | 前端根据设计 JSON 渲染全屏 slide | P0 |
| 4 | `/showcase` 放映主体验 | 隐藏菜单、分类栏、时间轴、键盘导航 | P0 |
| 5 | 上传表单与任务状态适配 | AI 开关、是否加入放映、状态机细化 | P1 |
| 6 | 管理与验收收口 | 任务查看、重新生成、验收脚本、文档 | P0 |

## 4. 阶段 0：当前系统重构与 PRD 基线切换

### 目标

把当前已经完成的 v0.1 系统从“相册 MVP”重构为“PPT 放映系统底座”。这个阶段不追求新增 AI 能力，重点是修正产品主线、路由、导航、状态和验收口径。

### 当前可保留能力

1. 后端 FastAPI 项目结构。
2. Nuxt 3 前端项目结构。
3. 登录、登出、Session Cookie。
4. 管理员创建用户。
5. MinIO 私有存储和 presigned URL。
6. 单图和批量上传。
7. EXIF 解析、preview、thumbnail。
8. `photo_processing_jobs` 和 Worker。
9. 备份、恢复和恢复演练脚本。
10. 后端测试和 v0.1 验收脚本基础。

### 当前必须重构任务

1. 重构路由主线。
   - 步骤 1：新增 `/showcase` 页面。
   - 步骤 2：`/` 登录后跳转 `/showcase`，未登录跳转 `/login`。
   - 步骤 3：登录成功后从 `/gallery` 改为 `/showcase`。
   - 步骤 4：`/gallery` 和 `/photo/:id` 保留为辅助页面。
2. 重构前端布局。
   - 步骤 1：现有 `AppHeader` 不再作为 showcase 主界面的常驻顶部栏。
   - 步骤 2：普通页面仍可使用现有导航。
   - 步骤 3：showcase 使用隐藏式顶部菜单和隐藏式左侧分类栏。
3. 重构状态机口径。
   - 步骤 1：兼容现有 `processing/ready/failed`。
   - 步骤 2：引入 PRD 状态：`uploaded`、`processing`、`exif_parsed`、`preview_generated`、`vision_analyzed`、`design_generated`、`ready`、`failed`。
   - 步骤 3：当前无 AI 时允许跳过 `vision_analyzed`，但状态命名和接口要能承载后续 AI。
4. 重构分类口径。
   - 步骤 1：默认分类从旧英文枚举映射到“生活照、摄影照、宠物照”。
   - 步骤 2：保留 slug 兼容，例如 `life`、`photography`、`pet`。
   - 步骤 3：准备从固定枚举迁移到 `categories` 表。
5. 重构验收脚本。
   - 步骤 1：`just accept-v0-1` 必须验证 `/showcase`。
   - 步骤 2：上传后照片最终能在 `/showcase` 播放。
   - 步骤 3：恢复演练要验证照片和 slide design 数量。

### 完成指标

1. 文档和代码入口都不再默认指向图库作为主体验。
2. 新路由 `/showcase` 已成为后续开发主入口。
3. 现有上传、Worker、备份恢复测试继续通过。
4. `README.md` 明确当前 v0.1 是 PRD 转向版。

### 行为边界

1. 不删除现有图库和详情页。
2. 不破坏当前已上传照片。
3. 不要求本阶段接入真实 AI。
4. 不允许为了 showcase 改动而公开 MinIO bucket。

## 5. 阶段 1：数据模型升级

### 目标

补齐 PPT 放映和 AI 设计需要的数据结构。

### 开发任务

1. 新增 `categories` 表。
   - 步骤 1：字段包括 `id`、`slug`、`name`、`description`、`sort_order`、`is_active`。
   - 步骤 2：插入默认分类：生活照、摄影照、宠物照。
   - 步骤 3：迁移现有照片分类。
2. 扩展 `photos` 表。
   - 步骤 1：增加 `ai_caption`。
   - 步骤 2：增加 `ai_category_suggestion`。
   - 步骤 3：增加 `ai_caption_enabled`。
   - 步骤 4：增加 `ai_category_enabled`。
   - 步骤 5：增加 `include_in_showcase`。
   - 步骤 6：增加 `time_source`。
3. 新增 `slide_designs` 表。
   - 步骤 1：字段包括 `id`、`photo_id`、`version`、`design_json`。
   - 步骤 2：字段包括 `source`、`status`、`validation_errors`。
   - 步骤 3：同一照片允许保留多个版本，但只读取最新 active 版本。
4. 调整任务表。
   - 步骤 1：job_type 支持 `photo_ingest`、`slide_design_generate`。
   - 步骤 2：保留 attempts、max_attempts、error_message。
   - 步骤 3：管理员后续可重试任务。

### 完成指标

1. Alembic 可无损升级现有数据。
2. 旧照片能映射到默认分类。
3. 新照片能写入 AI 开关字段。
4. 后端测试覆盖分类迁移和 slide design 存储。

### 验收指标

1. `uv run alembic upgrade head` 通过。
2. `uv run pytest` 通过。
3. `GET /api/photos` 仍兼容旧前端字段。

### 行为边界

1. 迁移不得删除现有照片。
2. 旧 `life/travel/pet` 兼容期内不能直接废弃。
3. `design_json` 必须是 JSONB 或等价 JSON 字段，不存字符串化 JSON。

## 6. 阶段 2：Fallback Slide Design 生成

### 目标

在没有 Ollama 和 DeepSeek 的情况下，也能为每张照片生成合法、可播放的 slide design。

### 开发任务

1. 定义最小 `slide_design.schema.json`。
   - 步骤 1：包含 `photoId`、`templateId`、`templateParams`、`layers`、`styleTokens`、`renderPolicy`。
   - 步骤 2：限制坐标范围为 0 到 1。
   - 步骤 3：限制 zIndex 范围。
2. 定义第一批模板。
   - 步骤 1：`cinematic_fullscreen`。
   - 步骤 2：`warm_memory`。
   - 步骤 3：`minimal_white`。
3. 实现后端 fallback generator。
   - 步骤 1：根据分类选择模板。
   - 步骤 2：根据照片方向选择图片区域。
   - 步骤 3：用户留言写入 text layer。
   - 步骤 4：拍摄时间写入 timeline layer。
4. Worker 接入。
   - 步骤 1：preview/thumbnail 成功后生成 fallback design。
   - 步骤 2：写入 `slide_designs`。
   - 步骤 3：状态进入 `design_generated` 或 `ready`。

### 完成指标

1. 每张 ready 照片至少有一个 slide design。
2. slide design 通过 schema 校验。
3. 无用户留言时不生成假文案。
4. 失败时记录错误并允许重试。

### 验收指标

1. 上传一张照片后，数据库中出现对应 slide design。
2. `GET /api/photos/{photo_id}/slide-design` 返回设计 JSON。
3. AI 未配置时照片仍可播放。

### 行为边界

1. fallback generator 不调用外部 AI。
2. 不生成任意 HTML、JavaScript。
3. CSS 第一版只允许白名单 CSS variables。

## 7. 阶段 3：最小 Slide Renderer

### 目标

前端实现可控渲染器，用于把 slide design JSON 渲染成一页全屏 PPT。

### 开发任务

1. 创建渲染目录。
   - 步骤 1：`frontend/app/slide-renderer/configs/`。
   - 步骤 2：`frontend/app/slide-renderer/components/`。
   - 步骤 3：`frontend/app/slide-renderer/validators/`。
2. 实现配置文件。
   - 步骤 1：`slide_templates.json`。
   - 步骤 2：`layer_primitives.json`。
   - 步骤 3：`ai_css_whitelist.json`。
3. 实现组件。
   - 步骤 1：`SlideRenderer.vue`。
   - 步骤 2：`LayerRenderer.vue`。
   - 步骤 3：`ImageLayer.vue`。
   - 步骤 4：`TextLayer.vue`。
   - 步骤 5：`TimelineLayer.vue`。
4. 实现前端校验。
   - 步骤 1：校验模板是否存在。
   - 步骤 2：过滤未知 layer。
   - 步骤 3：过滤不允许 CSS token。

### 完成指标

1. 合法 design JSON 能渲染全屏 slide。
2. 图片、文案、时间轴至少能显示。
3. 非法 layer 不会破坏页面。
4. 移动端不出现明显溢出。

### 验收指标

1. Nuxt build 通过。
2. 至少 3 份示例 design JSON 可渲染。
3. Playwright 或验收脚本能打开 showcase 页面并看到照片。

### 行为边界

1. 不执行 AI 生成 JavaScript。
2. 不直接插入 AI 生成 HTML。
3. 不允许 AI 控制顶部菜单、左侧分类栏和路由逻辑。

## 8. 阶段 4：`/showcase` 放映主体验

### 目标

实现新 PRD 的第一屏体验：登录后进入全屏 PPT 放映页面。

### 开发任务

1. 实现 `/showcase` API。
   - 步骤 1：返回分类列表。
   - 步骤 2：返回当前分类照片列表。
   - 步骤 3：返回每张照片的 preview URL 和 slide design。
2. 实现 `/showcase` 页面。
   - 步骤 1：全屏布局。
   - 步骤 2：默认展示当前分类第一张照片。
   - 步骤 3：无照片时展示空分类状态和上传入口。
3. 实现隐藏顶部菜单。
   - 步骤 1：鼠标移至顶部浮现。
   - 步骤 2：离开后隐藏。
   - 步骤 3：包含上传、图库、后台、退出。
4. 实现隐藏左侧分类栏。
   - 步骤 1：鼠标移至左侧浮现。
   - 步骤 2：显示分类、数量、当前分类。
5. 实现键盘导航。
   - 步骤 1：`←` / `→` 切换同分类照片。
   - 步骤 2：`↑` / `↓` 切换分类。
6. 实现底部时间轴。
   - 步骤 1：显示当前照片位置。
   - 步骤 2：显示拍摄时间或上传时间。
   - 步骤 3：点击节点跳转照片，第一版可选。

### 完成指标

1. 登录后默认进入 `/showcase`。
2. `/showcase` 无传统滚动图库。
3. 方向键切换可用。
4. 顶部菜单和左侧分类栏默认隐藏。
5. 底部时间轴随照片变化。

### 验收指标

1. `just accept-v0-1` 检查 `/showcase`。
2. 上传照片后最终能在 `/showcase` 出现。
3. 空分类有可理解提示。

### 行为边界

1. `/gallery` 继续保留为辅助页面。
2. showcase 不直接加载公开 MinIO URL。
3. 处理失败的照片不能阻断其他照片播放。

## 9. 阶段 5：上传表单与任务状态适配

### 目标

让上传页符合新 PRD 的入库规则。

### 开发任务

1. 上传表单新增字段。
   - 步骤 1：AI 文案开关。
   - 步骤 2：AI 自动分类开关。
   - 步骤 3：是否加入放映。
   - 步骤 4：分类可留空，留空时等待 AI 或 fallback 分类。
2. 后端上传接口适配。
   - 步骤 1：保存新字段。
   - 步骤 2：用户留言优先。
   - 步骤 3：未启用 AI 文案时不展示 AI 文案。
3. 状态查询适配。
   - 步骤 1：返回更细状态。
   - 步骤 2：返回 slide design 状态。
   - 步骤 3：返回失败原因。
4. 前端上传反馈适配。
   - 步骤 1：显示“正在解析照片信息”。
   - 步骤 2：显示“正在生成幻灯片设计”。
   - 步骤 3：完成后提示将加入 PPT。

### 完成指标

1. 用户留言优先规则正确。
2. AI 文案开关字段被保存。
3. include_in_showcase 控制照片是否进入放映。
4. 上传结果逐项显示处理状态。

### 验收指标

1. 开启/关闭 AI 文案的请求都有测试。
2. 未选择分类的照片不会导致上传失败。
3. 上传完成后可进入 showcase。

### 行为边界

1. 当前无 AI 时不得伪造 AI 文案。
2. 用户明确选择分类时，AI 后续不得自动覆盖，除非用户开启自动修正。

## 10. 阶段 6：管理与验收收口

### 目标

补齐 v0.1 PRD 转向版的管理入口、验收脚本和文档。

### 开发任务

1. 最小管理入口。
   - 步骤 1：保留 `/admin/users`。
   - 步骤 2：新增 `/admin/jobs` 或最小任务列表。
   - 步骤 3：任务可查看错误原因。
   - 步骤 4：预留重新生成 slide design 操作。
2. 验收脚本升级。
   - 步骤 1：检查登录后进入 `/showcase`。
   - 步骤 2：检查上传后生成 slide design。
   - 步骤 3：检查 `/showcase` 能加载照片。
   - 步骤 4：检查备份恢复后 slide design 数量一致。
3. 文档更新。
   - 步骤 1：README 改为 PPT 放映系统说明。
   - 步骤 2：记录当前 AI 未接入边界。
   - 步骤 3：记录如何运行 Worker 和验收脚本。

### 完成指标

1. `just test-backend` 通过。
2. 前端 Docker 构建通过。
3. `just accept-v0-1` 覆盖新 PRD 的 v0.1 最小闭环。
4. 备份恢复演练通过。

### 验收指标

1. 新上传照片可从上传页进入处理。
2. Worker 处理后照片可在 `/showcase` 播放。
3. `/gallery` 辅助页面仍可使用。
4. 恢复演练后照片、对象、slide design 计数一致。

### 行为边界

1. 不把 AI Agent 不完整能力伪装成已完成。
2. 不以图库通过替代 showcase 通过。
3. 不移除数据安全脚本。

## 11. v0.1 完成后的交付状态

v0.1 PRD 转向版完成后，应达到：

1. 家庭成员登录后看到 `/showcase`。
2. 至少能播放 fallback 设计的全屏 slide。
3. 顶部菜单、左侧分类栏、键盘导航和时间轴可用。
4. 上传照片后经过 Worker 入库，最终进入 PPT。
5. 没有真实 AI 时也能稳定运行。
6. 后续可以在同一 Worker 流程中接入 Ollama 和 DeepSeek。
