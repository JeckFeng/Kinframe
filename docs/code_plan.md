# KinFrame 最新 PRD 开发计划方案

本文档基于 `docs/Kinframe_PRD.md` 和 `docs/Frontend_Rendering_Strategies.md` 重写。KinFrame 的产品方向已从“私有家庭相册管理系统”调整为“AI 驱动的家庭影像艺术化 PPT 放映网站”。后续开发必须围绕 `/showcase` 全屏放映、AI 设计 JSON、受控 Slide Renderer、隐藏式导航和时间轴体验展开。

## 0. 总体开发原则

1. **主体验优先**：登录后默认进入 `/showcase`，图库和详情页只是辅助管理入口。
2. **照片永远是视觉主体**：AI 设计、图层、动效和 CSS tokens 都服务于照片观看，不做喧宾夺主的装饰。
3. **AI 生成设计数据，不生成可执行代码**：AI 只能输出通过 schema 校验的 JSON、CSS Variables 和受限 scoped CSS，不允许生成任意 HTML/JavaScript。
4. **确定性入库先行，AI 失败可兜底**：EXIF、preview、thumbnail、基础 slide design fallback 必须不依赖 AI；Ollama/DeepSeek 失败时照片仍可播放。
5. **保留当前 v0.1 可复用资产**：登录、上传、MinIO、Worker、preview、备份恢复继续使用，但要重构到新状态机和 PPT 工作流。
6. **数据安全持续有效**：MinIO bucket 私有，图片访问通过后端鉴权或短期 URL，备份/恢复脚本继续覆盖 PostgreSQL、MinIO 和配置文件。

## 1. 最新产品目标

第一阶段目标是实现一个私有家庭影像网站，具备：

1. 私有登录和管理员创建用户。
2. 支持照片上传、EXIF 解析、preview/thumbnail 生成和 MinIO 私有存储。
3. 登录后进入全屏 PPT 式 `/showcase`。
4. 每张照片生成一页可播放 slide。
5. 按分类形成不同 PPT，分类内按拍摄时间或上传时间排序。
6. 支持隐藏顶部菜单、隐藏左侧分类栏、键盘方向键导航和底部时间轴。
7. Worker 生成或兜底生成 `slide_design_json`。
8. 前端 Slide Renderer 根据设计 JSON 安全渲染。
9. 后续接入 Ollama 视觉识别和 DeepSeek 文案/设计生成。

## 2. 阶段总览

| 阶段 | 名称 | 核心目标 | 优先级 |
|---|---|---|---|
| 0 | 现有 v0.1 资产审计与重构基线 | 明确保留、重构、废弃内容，调整路由和状态机方向 | P0 |
| 1 | 数据模型与配置体系升级 | categories、slide_designs、AI 字段、处理状态、配置文件 | P0 |
| 2 | 确定性照片入库完善 | 上传、EXIF、preview、thumbnail、HEIC 策略、基础任务状态 | P0 |
| 3 | Slide Renderer 基础能力 | 模板配置、图层配置、schema、CSS 白名单、前端安全渲染 | P0 |
| 4 | `/showcase` 全屏放映体验 | 全屏单图、隐藏菜单、分类栏、时间轴、键盘导航 | P0 |
| 5 | 兜底设计生成工作流 | 不依赖 AI 生成可播放 slide design，保证照片可展示 | P0 |
| 6 | AI Agent 入库与设计生成 | Ollama 识别、DeepSeek 文案/设计、校验、失败兜底 | P1 |
| 7 | 管理后台升级 | 图片、分类、任务、重新生成 AI 设计、隐藏/删除照片 | P1 |
| 8 | 外网访问、部署与安全 | Caddy、Cloudflare Tunnel、HTTPS、生产 Compose、安全审计 | P1 |
| 9 | 备份恢复、验收与发布 | 恢复演练、视觉验收、端到端验收、文档收口 | P0 |

## 3. 阶段 0：现有 v0.1 资产审计与重构基线

### 目标

把当前已完成的“相册 MVP”重定位为“AI PPT 放映系统”的底座，避免继续沿传统图库方向投入。

### 主要任务

1. 盘点可复用能力：
   - 用户登录、管理员创建用户。
   - 上传、批量上传、MinIO 私有对象、presigned URL。
   - EXIF、preview、thumbnail、Worker、任务重试。
   - 备份、恢复、恢复演练。
2. 标记需要重构的能力：
   - `/` 和登录成功跳转从 `/gallery` 改为 `/showcase`。
   - `photos.status` 从简单 `processing/ready/failed` 扩展到 PRD 状态机。
   - 固定分类 `life/travel/pet` 迁移到可扩展分类模型。
   - 上传表单增加 AI 文案、AI 自动分类、是否加入放映等字段。
3. 标记需要降级为辅助能力的页面：
   - `/gallery`、`/gallery/:category`、`/photo/:id` 保留，但不再作为主体验。
4. 更新验收口径：
   - `just accept-v0-1` 后续应验证 `/showcase`，而不仅是图库。

### 完成指标

1. 文档明确当前系统哪些保留、哪些重构、哪些废弃。
2. 新计划不再把“相册体验升级”作为核心主线。
3. 后续开发的主路径变为：入库 → slide design → `/showcase` 播放。

## 4. 阶段 1：数据模型与配置体系升级

### 目标

建立支持 AI PPT 放映的数据模型和配置文件体系。

### 主要任务

1. 新增 `categories` 表：
   - `id`、`slug`、`name`、`description`、`sort_order`、`is_active`、`created_at`、`updated_at`。
   - 默认数据：生活照、摄影照、宠物照。
   - 迁移现有 `photos.category` 字符串到 `category_id` 或兼容字段。
2. 扩展 `photos` 表：
   - `ai_caption`
   - `final_caption`
   - `ai_category_suggestion`
   - `ai_caption_enabled`
   - `ai_category_enabled`
   - `include_in_showcase`
   - `hidden_at`
   - `time_source`
3. 扩展处理状态：
   - `uploaded`
   - `processing`
   - `exif_parsed`
   - `preview_generated`
   - `vision_analyzed`
   - `design_generated`
   - `ready`
   - `failed`
4. 新增 `slide_designs` 表：
   - `id`
   - `photo_id`
   - `version`
   - `design_json`
   - `source`
   - `status`
   - `validation_errors`
   - `created_at`
   - `updated_at`
5. 建立前端配置文件：
   - `slide_templates.json`
   - `layer_primitives.json`
   - `ai_css_whitelist.json`
   - `design_presets.json`
   - `slide_design.schema.json`
6. 建立后端共用 schema 和校验入口。

### 完成指标

1. Alembic 迁移可从现有 v0.1 数据无损升级。
2. 后端能读取并校验 slide design schema。
3. 默认分类存在且现有照片能映射到新分类。
4. 测试覆盖数据迁移、默认分类、状态枚举和 slide design 存储。

## 5. 阶段 2：确定性照片入库完善

### 目标

不依赖 AI，确保每张照片都能完成安全入库，并生成可用于 PPT 播放的基础素材。

### 主要任务

1. 上传接口升级：
   - 支持 jpg、jpeg、png、webp。
   - HEIC/HEIF 如果环境不可转换，返回明确错误；如果依赖可用，则转换入库。
   - 单张最大 100MB。
   - 单次最多 50 张。
2. 上传表单字段升级：
   - 分类可选。
   - 用户留言。
   - 是否允许 AI 文案。
   - 是否允许 AI 自动分类。
   - 是否立即加入放映。
3. Worker 入库流程升级：
   - 保存原图。
   - 解析 EXIF。
   - 生成 preview 和 thumbnail。
   - 提取主色调。
   - 写入 time source。
   - 创建兜底 slide design 任务。
4. 失败策略：
   - EXIF 失败不阻断播放。
   - preview/thumbnail 失败进入 failed。
   - 错误信息可查询。

### 完成指标

1. 上传后照片进入后台任务。
2. 处理成功后至少拥有 original、preview、thumbnail。
3. 没有 EXIF 的照片使用上传时间。
4. 批量上传逐项返回状态。
5. 当前照片可被后续 Slide Renderer 使用。

## 6. 阶段 3：Slide Renderer 基础能力

### 目标

建立受控前端渲染器，让设计 JSON 可以稳定渲染为全屏 slide。

### 主要任务

1. 创建目录：
   - `frontend/app/slide-renderer/configs/`
   - `frontend/app/slide-renderer/schemas/`
   - `frontend/app/slide-renderer/components/`
   - `frontend/app/slide-renderer/validators/`
2. 实现配置文件：
   - 第一版模板不少于 3 个：`cinematic_fullscreen`、`warm_memory`、`minimal_white`。
   - 定义 image、text、shape、mask、timeline、background 图层。
3. 实现校验器：
   - 校验 `templateId` 是否存在。
   - 校验 layer 类型、坐标范围、zIndex 范围。
   - 清洗 CSS Variables 和 scoped CSS。
4. 实现组件：
   - `SlideRenderer.vue`
   - `LayerRenderer.vue`
   - `ImageLayer.vue`
   - `TextLayer.vue`
   - `ShapeLayer.vue`
   - `MaskLayer.vue`
   - `TimelineLayer.vue`
5. 后端实现相同 schema 校验和 fallback design 生成。

### 完成指标

1. 给定合法 slide design JSON，前端能渲染一页完整 slide。
2. 非法字段会被拒绝或清洗，不执行 AI HTML/JS。
3. 没有 AI 设计时可使用 fallback design。
4. 不同模板能产生明显不同布局。

## 7. 阶段 4：`/showcase` 全屏放映体验

### 目标

实现 PRD 定义的主体验：登录后进入全屏 PPT 放映空间。

### 主要任务

1. 路由调整：
   - 新增 `/showcase`。
   - `/` 根据登录状态跳转 `/showcase` 或 `/login`。
   - 登录成功后跳转 `/showcase`。
2. 全屏播放界面：
   - 一页一张照片。
   - 使用 preview 或原图短期 URL。
   - 无传统滚动浏览。
3. 顶部隐藏菜单：
   - 默认隐藏。
   - 鼠标移到顶部浮现。
   - 包含上传、图库、后台、退出等入口。
4. 左侧隐藏分类栏：
   - 默认隐藏。
   - 鼠标移到左侧浮现。
   - 显示当前分类和照片数量。
5. 键盘导航：
   - `←` / `→` 切换同类照片。
   - `↑` / `↓` 切换分类。
6. 底部时间轴：
   - 显示当前照片在分类时间轴中的位置。
   - 按拍摄时间排序，无 EXIF 时按上传时间。

### 完成指标

1. 登录后默认进入 `/showcase`。
2. 第一屏是全屏 slide，不是网格图库。
3. 键盘可切换照片和分类。
4. 空分类显示空状态和上传入口。
5. 处理中的照片有明确状态，不破坏播放。

## 8. 阶段 5：兜底设计生成工作流

### 目标

在 AI 接入前，确保每张照片都能生成结构合法的 `slide_design_json`。

### 主要任务

1. 实现 fallback design generator：
   - 根据分类选择默认模板。
   - 根据照片方向选择 image fit。
   - 用户留言写入 caption layer。
   - 拍摄时间写入 timeline layer。
2. 写入 `slide_designs` 表。
3. 增加 API：
   - `GET /api/showcase`
   - `GET /api/showcase?category=...`
   - `GET /api/photos/{photo_id}/slide-design`
4. Worker 成功生成 fallback design 后，照片可进入 `design_generated` 或 `ready`。

### 完成指标

1. 无 AI 环境下上传照片最终可在 `/showcase` 播放。
2. `slide_design_json` 通过 schema 校验。
3. 用户留言优先显示。
4. 没有留言时不伪造 AI 文案。

## 9. 阶段 6：AI Agent 入库与设计生成

### 目标

接入 PRD 规定的 AI 工作流：Ollama 视觉识别 + DeepSeek 文案和设计 JSON。

### 主要任务

1. 引入 AI 配置：
   - Ollama endpoint、视觉模型名。
   - DeepSeek API key、模型名、超时和重试。
2. 实现视觉分析：
   - 输入 preview 图。
   - 输出内容描述、主体、场景、主题色、情绪、分类建议。
3. 实现 DeepSeek 设计生成：
   - 输入照片元数据、用户留言、AI 开关、模板能力、图层能力、CSS 白名单。
   - 输出 `slide_design_json`。
4. 实现安全校验：
   - JSON Schema 校验。
   - 语义校验。
   - CSS token 白名单清洗。
5. 失败兜底：
   - Ollama 失败可用默认分类或人工分类。
   - DeepSeek 失败使用 fallback design。
   - 管理员可重新生成。

### 完成指标

1. 用户留言优先于 AI 文案。
2. 未勾选 AI 文案时不展示 AI 文案。
3. AI 生成的设计 JSON 通过后端校验。
4. AI 失败时照片仍可播放。

## 10. 阶段 7：管理后台升级

### 目标

让管理员可以维护照片、分类、任务和 AI 设计结果。

### 主要任务

1. `/admin/photos`：
   - 列表、筛选、隐藏、删除、修改分类、修改文案。
2. `/admin/categories`：
   - 创建、编辑、排序、禁用分类。
3. `/admin/jobs`：
   - 查看任务状态、错误原因、重试。
4. `/admin/users`：
   - 保留现有用户管理，增加停用、重置密码。
5. 审计日志：
   - 记录关键管理操作。

### 完成指标

1. 管理员可修正 AI 分类和文案。
2. 管理员可重新生成 slide design。
3. 普通用户不能访问管理后台。
4. 关键操作有 audit log。

## 11. 阶段 8：外网访问、部署与安全

### 目标

完成私有部署和外网访问能力。

### 主要任务

1. Caddy 反向代理：
   - `/api/*` 到后端。
   - 其他路由到前端。
2. Cloudflare Tunnel：
   - 配置 tunnel。
   - HTTPS 外网访问。
3. 生产 Compose：
   - 前端、后端、Worker、PostgreSQL、Redis、MinIO、Caddy、cloudflared。
4. 安全审计：
   - Cookie Secure。
   - MinIO 私有。
   - 上传 MIME 和扩展名校验。
   - AI 输出安全校验。

### 完成指标

1. 外网 HTTPS 可访问。
2. 未登录不能访问照片和图片 URL。
3. AI 输出不能控制路由、菜单、全局样式或脚本。

## 12. 阶段 9：备份恢复、验收与发布

### 目标

完成端到端验收、恢复演练和发布文档。

### 主要任务

1. 保持并扩展现有备份恢复：
   - PostgreSQL。
   - MinIO。
   - 配置文件。
   - slide designs。
2. 验收脚本：
   - 登录后进入 `/showcase`。
   - 上传照片后最终可播放。
   - 方向键切换照片和分类。
   - AI 失败兜底模板可用。
   - 备份恢复后照片和 slide design 数量一致。
3. 视觉质量检查：
   - 文案不遮挡主体。
   - 移动端不溢出。
   - 不同模板有差异。
4. 文档：
   - README。
   - 部署说明。
   - AI 配置说明。
   - 故障排查。

### 完成指标

1. `just accept-v0-1` 或新验收命令覆盖最新 PRD P0。
2. 恢复演练通过。
3. Docker 生产构建通过。
4. 可交付给家庭成员试用。

## 13. 当前难度评估

当前 v0.1 底层能力可复用，但主体验和 AI 设计能力需要新增。整体难度评估：

| 模块 | 当前可复用度 | 难度 |
|---|---:|---|
| 登录、用户、权限 | 高 | 低 |
| 上传、MinIO、EXIF、preview | 高 | 中 |
| Worker 和任务重试 | 中高 | 中 |
| 备份恢复 | 高 | 低 |
| `/showcase` 全屏播放 | 低 | 中高 |
| Slide Renderer | 低 | 高 |
| AI Agent 工作流 | 低 | 高 |
| 管理后台升级 | 中 | 中 |
| 外网部署 | 中 | 中 |

建议先实现“无 AI 也能播放”的 `/showcase + fallback slide design`，再接入真实 AI。
