# KinFrame v0.2 最小功能版本开发计划

> 制定日期：2026-05-12  
> 依据文档：`docs/Kinframe_PRD.md`、`docs/Frontend_Rendering_Strategies.md`、`docs/code_plan.md`、`docs/problem/v0.1problem.md`  
> 版本定位：v0.2 是“PRD 闭环增强版”。目标是在 v0.1 已有登录、上传、Worker、fallback slide 和 `/showcase` 基础上，修复关键缺口，补齐鼠标导航、反向地理编码、Renderer 容错与最小 AI 生成链路。

## 1. v0.2 总目标

v0.2 需要达到以下状态：

1. v0.1 遗留的验收脚本、分类可空、Renderer 容错和前端测试缺口完成收口。
2. `/showcase` 支持键盘和鼠标双导航：左键上一张、右键下一张、滚轮切换分类。
3. 有 GPS 的照片可异步反向地理编码，并在时间轴、详情页或照片信息层展示拍摄地点。
4. Slide Renderer 能过滤未知 layer，支持更完整的安全 schema、CSS token 清洗和最小视觉测试。
5. 在 AI 可配置的前提下，完成最小 Ollama/DeepSeek 工作流；AI 失败时仍使用 fallback design 播放。
6. `just accept-v0-2` 能覆盖“上传 -> Worker -> 地理编码/AI 或 fallback -> `/showcase` 播放 -> 备份恢复”的最小闭环。

## 2. v0.2 不做范围或不能做的行为

1. 不实现公开注册、评论、点赞、社交分享。
2. 不做移动端原生 App。
3. 不做完整地图相册，只展示反向地理编码后的地点文本。
4. 不开放 AI 生成任意 HTML、JavaScript 或全局 CSS。
5. 不要求 AI 服务必须在线；AI 不可用时系统必须退回 fallback design。
6. 不把图库重新变成主体验；`/showcase` 仍是登录后的核心入口。
7. **Do not install global packages on the host to work around Docker permission issues.** Prefer fixing the mount/UID setup so Docker commands work correctly from the host. If you must run tools on the host (e.g. vitest), ensure `node_modules` is host-owned by running `pnpm install` on the host as the host user — not inside a root container with a bind mount.

## 3. 阶段总览

| 阶段 | 名称 | 核心目标 | 优先级 |
|---|---|---|---|
| 0 | v0.1 问题收口与验收基线 | 修复已知大坑，建立可信 v0.2 验收入口 | P0 |
| 1 | 数据模型与配置升级 | 支持可空分类、地理编码、AI 结果和更完整 slide schema | P0 |
| 2 | 入库 Worker 与反向地理编码 | 将 EXIF GPS 转为地点，保证失败不阻断播放 | P0 |
| 3 | `/showcase` 交互体验增强 | 鼠标导航、地点展示和状态一致性 | P0 |
| 4 | Slide Renderer v0.2 | 安全校验、未知 layer 过滤、更多图层和前端测试 | P0 |
| 5 | 最小 AI Agent 工作流 | Ollama/DeepSeek 接入、AI 文案/分类/设计、失败兜底 | P1 |
| 6 | 管理后台与人工修正 | 管理地点、分类、AI 结果、任务重试和重新生成 | P1 |
| 7 | 端到端验收、备份恢复与文档 | 形成可交付 v0.2 版本 | P0 |

---

## 4. 阶段 0：v0.1 问题收口与验收基线

### 目标

先修复 v0.1 审查报告中会影响后续开发的基础问题，确保 v0.2 不建立在错误验收和脆弱实现之上。

### 开发任务与步骤

1. 修复 showcase 验收脚本登录态。
   - 步骤 1：新增 `scripts/v0.2-acceptance.sh`，保留 `scripts/v0.1-acceptance.sh` 作为历史入口。
   - 步骤 2：在验收脚本中创建或复用测试用户，并保存 cookie。
   - 步骤 3：所有 `/api/showcase`、`/showcase`、`/api/photos/*` 调用必须带 cookie。
   - 步骤 4：验证 `/showcase` 页面不是登录页或重定向结果。
2. 修复上传分类可空。
   - 步骤 1：后端单图和批量上传允许 `category` 为空。
   - 步骤 2：无分类且 AI 未启用或失败时，使用明确 fallback 分类，例如 `life`，并记录 `category_source=fallback`。
   - 步骤 3：前端上传页增加“不选择分类/等待自动分类”选项。
   - 步骤 4：新增测试覆盖未选择分类也能上传成功。
3. 修复 Renderer 未知 layer 策略。
   - 步骤 1：前端校验器对未知 layer 执行过滤并记录 warning。
   - 步骤 2：后端保存 AI design 时可拒绝严重非法结构，但不因前端未知扩展层导致页面崩溃。
   - 步骤 3：新增包含未知 layer 的 design 样例测试。
4. 确认分类栏简洁策略。
   - 步骤 1：左侧分类栏只展示分类名称。
   - 步骤 2：不在 `/showcase` 左侧分类栏显示分类照片数量。
   - 步骤 3：空分类仍显示空状态页，但不通过数量提示表达。
5. 建立 v0.2 命令入口。
   - 步骤 1：`justfile` 增加 `accept-v0-2`。
   - 步骤 2：README 增加 v0.2 验收说明。
   - 步骤 3：所有新增命令优先在 Docker 环境内执行。

### 完成指标

1. `just accept-v0-2` 能真实登录并验证 `/showcase`。
2. 未选择分类的照片上传不失败。
3. 未知 layer 不会导致整张 slide 不可渲染。
4. 分类栏保持简洁，不显示分类照片数量。

### 验收指标

1. 测试覆盖上述关键修复点。
2. 前端 build 通过。
3. v0.2 验收脚本从干净服务启动后可重复运行。
4. 验收脚本失败时能指出具体失败环节。

---

## 5. 阶段 1：数据模型与配置升级

### 目标

为 v0.2 的地理编码、AI 结果、可扩展分类和 Renderer v0.2 建立数据基础。

### 开发任务与步骤

1. 扩展 `photos` 表。
   - 步骤 1：新增 `location_name`、`location_country`、`location_region`、`location_city`、`location_district`、`location_road`。
   - 步骤 2：新增 `geocoding_status`，取值建议为 `not_applicable/pending/succeeded/failed`。
   - 步骤 3：新增 `geocoding_provider`、`geocoding_error`、`geocoded_at`。
   - 步骤 4：新增 `category_source`，区分 `user/ai/fallback/admin`。
2. 分类模型升级。
   - 步骤 1：保留现有 slug 兼容。
   - 步骤 2：逐步移除后端 schema 对固定 Literal 的强绑定。
   - 步骤 3：上传、筛选、showcase 均以 `categories` 表为准。
   - 步骤 4：暂不强制一次性把 `photos.category` 改为外键，但要避免新增硬编码。
3. 任务模型升级。
   - 步骤 1：`photo_processing_jobs.job_type` 增加 `reverse_geocode`、`vision_analyze`、`slide_design_generate`。
   - 步骤 2：支持同一照片多阶段任务查询。
   - 步骤 3：保留 attempts、max_attempts、error_message。
4. AI 结果字段升级。
   - 步骤 1：新增或确认 `ai_caption`、`ai_category_suggestion`、`ai_analysis_json`。
   - 步骤 2：记录 AI provider、model、prompt version、raw response 摘要。
   - 步骤 3：AI 原始输出不得直接在前端执行。
5. 配置文件升级。
   - 步骤 1：`.env.example` 增加 `GEOCODING_ENABLED`、`GEOCODING_PROVIDER`、`NOMINATIM_ENDPOINT`、`AMAP_API_KEY`。
   - 步骤 2：增加 `OLLAMA_ENDPOINT`、`OLLAMA_VISION_MODEL`、`DEEPSEEK_API_KEY`、`DEEPSEEK_MODEL`、`AI_ENABLED`。
   - 步骤 3：增加超时、重试、速率限制配置。

### 完成指标

1. Alembic 可从 v0.1 数据无损升级。
2. 没有 GPS 的旧照片 `geocoding_status=not_applicable`。
3. 有 GPS 的照片可进入 `pending` 状态等待地理编码。
4. 分类校验开始依赖数据库分类，而不是硬编码枚举。

### 验收指标

1. `uv run alembic upgrade head` 通过。
2. 迁移测试覆盖旧数据、无 GPS、有 GPS、旧分类兼容。
3. `.env.example` 和 README 说明新增配置。
4. 敏感配置不写入 Git。

---

## 6. 阶段 2：入库 Worker 与反向地理编码

### 目标

照片上传后，如果 EXIF 中包含 GPS，系统能异步调用 Nominatim 或高德 API 转换为可读地名。外部 API 失败不能阻断 preview、slide design 和播放。

### 开发任务与步骤

1. 抽象地理编码服务。
   - 步骤 1：新增 `backend/app/services/geocoding.py`。
   - 步骤 2：定义统一接口：输入 `lat/lng`，输出标准地点对象。
   - 步骤 3：实现 Nominatim provider。
   - 步骤 4：实现高德 provider，API Key 只在后端环境变量读取。
   - 步骤 5：实现 disabled/noop provider，用于测试和离线环境。
2. 加入缓存和限流。
   - 步骤 1：按坐标四舍五入或 geohash 建缓存键。
   - 步骤 2：相同或近似坐标优先复用结果。
   - 步骤 3：配置请求超时和重试次数。
   - 步骤 4：遵守 provider 速率限制。
3. Worker 流程接入。
   - 步骤 1：EXIF 解析出 GPS 后写入 `geocoding_status=pending`。
   - 步骤 2：在同一 Worker 流程或独立 `reverse_geocode` job 中执行地理编码。
   - 步骤 3：成功后写入地点字段和 `succeeded`。
   - 步骤 4：失败后写入 `failed` 和错误摘要，但照片继续处理。
4. API 输出升级。
   - 步骤 1：`PhotoRead` 返回地点字段和地理编码状态。
   - 步骤 2：`/api/showcase` 返回当前照片地点摘要。
   - 步骤 3：`/api/photos/{id}/processing-status` 返回地理编码状态。
5. 测试。
   - 步骤 1：用 fake provider 测成功。
   - 步骤 2：用 fake provider 测超时/失败。
   - 步骤 3：确认失败不阻断照片进入 ready。

### 完成指标

1. 有 GPS 的照片能得到可读地点。
2. 无 GPS 的照片不会触发外部 API。
3. provider 失败时照片仍可在 `/showcase` 播放。
4. 高德 API Key 不暴露到前端。

### 验收指标

1. 后端测试覆盖 Nominatim/高德 provider 的解析逻辑或 mock 行为。
2. 验收脚本能用本地 fake provider 生成稳定地点。
3. 详情页或 showcase 信息层能看到地点文本。
4. 备份恢复后地点字段仍存在。

---

## 7. 阶段 3：`/showcase` 交互体验增强

### 目标

使 `/showcase` 达到 PRD 要求的键鼠基础体验，并展示时间轴和地点信息。

### 开发任务与步骤

1. 鼠标左右键导航。
   - 步骤 1：在 showcase 主播放区域监听 `click`。
   - 步骤 2：左键等价 `←`，进入上一张。
   - 步骤 3：监听 `contextmenu`，阻止默认右键菜单并等价 `→`。
   - 步骤 4：按钮、链接、输入框、菜单和弹窗区域不触发切换。
2. 鼠标滚轮分类切换。
   - 步骤 1：监听 `wheel`。
   - 步骤 2：`deltaY > 0` 等价 `↓`，切到下一个分类。
   - 步骤 3：`deltaY < 0` 等价 `↑`，切到上一个分类。
   - 步骤 4：使用动画锁或节流，避免一次滚动触发多次跳转。
3. 分类栏增强。
   - 步骤 1：展示分类名称和当前分类状态。
   - 步骤 2：分类切换时短暂显示分类栏。
   - 步骤 3：空分类可进入空状态页，但分类栏不显示数量。
4. 底部信息层增强。
   - 步骤 1：显示当前位置 `index / total`。
   - 步骤 2：显示拍摄时间或上传时间。
   - 步骤 3：有地点时显示地点摘要。
   - 步骤 4：文案、时间、地点不得遮挡照片主体。
5. 播放位置记忆。
   - 步骤 1：每个分类记住最后浏览位置。
   - 步骤 2：切回分类时优先恢复上次位置。
   - 步骤 3：无记录时进入该分类最新或默认第一张。

### 完成指标

1. 键盘、鼠标左键、鼠标右键、滚轮都能控制播放。
2. 交互控件区域不会误触发播放导航。
3. 分类栏不显示分类照片数量，界面保持干净简洁。
4. 有地点的照片能在 showcase 信息层展示地点。

### 验收指标

1. Playwright 或等价浏览器测试覆盖左键、右键、滚轮。
2. 右键不会弹出默认菜单。
3. 快速滚轮不会跳过多个分类。
4. 移动端或窄屏布局不出现明显文字重叠。

---

## 8. 阶段 4：Slide Renderer v0.2

### 目标

让 Slide Renderer 从“能渲染 fallback”升级为“能承载 AI 设计输出”的受控渲染层。

### 开发任务与步骤

1. Schema 和校验统一。
   - 步骤 1：后端和前端尽量共享同一份 `slide_design.schema.json`。
   - 步骤 2：字段包括 `templateId`、`templateParams`、`layers`、`styleTokens`、`renderPolicy`、`aiMeta`。
   - 步骤 3：坐标、zIndex、layer type、source、text 长度都有边界。
2. 未知 layer 和非法字段处理。
   - 步骤 1：未知 layer 在前端过滤。
   - 步骤 2：非法 HTML/JS 直接拒绝。
   - 步骤 3：未知 CSS token 删除。
   - 步骤 4：记录 validation warning，供管理员排查。
3. 扩展 layer 组件。
   - 步骤 1：补齐 `BackgroundLayer`、`ShapeLayer`、`MaskLayer`。
   - 步骤 2：`ImageLayer` 支持 `preview/thumbnail/original` source，但默认使用 preview。
   - 步骤 3：`TextLayer` 限制最大字数、最大字号和安全换行。
   - 步骤 4：`TimelineLayer` 支持时间和地点文本。
4. CSS token 和 scoped CSS。
   - 步骤 1：第一优先级支持 CSS Variables。
   - 步骤 2：如实现 scoped CSS，必须经过 selector 和 property 白名单清洗。
   - 步骤 3：禁止 `url()`、`@import`、`javascript:`、布局破坏属性和全局选择器。
5. 示例和测试。
   - 步骤 1：准备至少 3 个合法示例 design。
   - 步骤 2：准备包含未知 layer、非法 CSS、非法 template 的样例。
   - 步骤 3：加入前端测试或 Playwright 截图检查。

### 完成指标

1. 合法 design 能渲染为全屏 slide。
2. 未知 layer 被过滤，合法 layer 继续显示。
3. 非法 HTML/JS/CSS 不会进入 DOM 执行。
4. 至少 3 个模板有明显不同布局。
5. 窄屏下文字不明显溢出。

### 验收指标

1. Nuxt build 通过。
2. 前端测试或浏览器测试覆盖 3 个模板。
3. 包含恶意字段的 design 不会执行脚本，也不会破坏页面。
4. Renderer 测试纳入 `just accept-v0-2` 或单独 `just test-frontend`。

---

## 9. 阶段 5：最小 AI Agent 工作流

### 目标

在 AI 可配置时完成最小自动分析、文案、分类建议和 slide design 生成；AI 不可用时仍稳定使用 fallback。

### 开发任务与步骤

1. AI 配置和开关。
   - 步骤 1：新增 `AI_ENABLED` 总开关。
   - 步骤 2：新增 Ollama endpoint、视觉模型、超时配置。
   - 步骤 3：新增 DeepSeek API key、模型、超时、重试配置。
   - 步骤 4：AI 相关命令和 Worker 环境变量全部进入 Docker 运行配置。
2. Ollama 视觉分析。
   - 步骤 1：输入 preview 图或压缩图。
   - 步骤 2：输出主体、场景、情绪、主题色、可能分类。
   - 步骤 3：结果写入 `ai_analysis_json`。
   - 步骤 4：失败时记录错误并继续 fallback。
3. DeepSeek 文案和设计生成。
   - 步骤 1：构建 prompt，包含模板能力、layer 能力、CSS 白名单、用户留言、EXIF、地点、AI 开关。
   - 步骤 2：强制输出可解析 JSON，不允许解释文字。
   - 步骤 3：用户留言优先；未启用 AI 文案时不得展示 AI 文案。
   - 步骤 4：输出 `slide_design_json` 后执行 schema 和语义校验。
4. 失败兜底。
   - 步骤 1：Ollama 失败时保留原分类或 fallback 分类。
   - 步骤 2：DeepSeek 失败时使用 fallback design。
   - 步骤 3：AI design 校验失败时最多重试一次，然后 fallback。
   - 步骤 4：失败原因进入 jobs 和 admin 页面。
5. 测试。
   - 步骤 1：用 fake AI provider 测成功链路。
   - 步骤 2：用 fake AI provider 测无效 JSON、超时、失败。
   - 步骤 3：确认 AI 不可用时验收仍通过。

### 完成指标

1. AI 开启时，新照片能产生 AI 分析结果和 AI slide design。
2. AI 关闭时，系统行为与 fallback 模式一致。
3. AI 文案开关规则正确。
4. AI 设计通过 schema 校验后才入库。
5. AI 失败不影响照片最终播放。

### 验收指标

1. 后端测试覆盖 fake AI 成功、失败、无效 JSON。
2. 验收脚本默认不依赖真实 DeepSeek/Ollama。
3. 管理员能看到 AI 任务状态和失败原因。
4. 无用户留言且启用 AI 文案时才展示 AI 文案。

---

## 10. 阶段 6：管理后台与人工修正

### 目标

让管理员可以修正 v0.2 新增数据：地点、分类、AI 文案、AI 分类建议、slide design 和任务失败。

### 开发任务与步骤

1. 照片详情页增强。
   - 步骤 1：展示地理编码结果和状态。
   - 步骤 2：展示 AI 分析摘要、AI 文案、AI 分类建议。
   - 步骤 3：管理员可修改最终文案、分类和地点文本。
   - 步骤 4：普通用户仍不能看到敏感 AI 原始输出。
2. `/admin/jobs` 增强。
   - 步骤 1：展示 `photo_ingest/reverse_geocode/vision_analyze/slide_design_generate`。
   - 步骤 2：支持失败任务重试。
   - 步骤 3：支持对单张照片重新生成 slide design。
   - 步骤 4：重试时不应破坏已有 ready 照片，除非新结果成功。
3. 分类管理最小化。
   - 步骤 1：管理员可查看分类列表、排序和启用状态。
   - 步骤 2：可调整名称、排序和启停。
   - 步骤 3：新增分类后可用于上传和 showcase。
4. 审计与安全。
   - 步骤 1：记录管理员修改分类、文案、地点、重新生成设计的操作。
   - 步骤 2：普通用户访问 admin API 返回 403。

### 完成指标

1. 管理员能修正 AI 或地理编码错误。
2. 管理员能重试失败任务。
3. 分类管理不再依赖前端硬编码。
4. 普通用户权限边界清晰。

### 验收指标

1. 管理 API 权限测试通过。
2. 失败任务可重试并可恢复到 ready。
3. 人工修改地点/分类后 showcase 展示同步更新。
4. 审计日志或最小操作记录可查询。

---

## 11. 阶段 7：端到端验收、备份恢复与文档

### 目标

把 v0.2 做成可部署、可验收、可回滚、可交给家庭成员试用的版本。

### 开发任务与步骤

1. 验收脚本。
   - 步骤 1：新增 `just accept-v0-2`。
   - 步骤 2：启动或检查 Docker infra。
   - 步骤 3：创建用户、登录、上传测试照片。
   - 步骤 4：Worker 处理到 ready。
   - 步骤 5：验证 slide design、showcase、地点字段和分类栏简洁显示。
   - 步骤 6：验证鼠标导航可通过 Playwright 或浏览器自动化完成。
   - 步骤 7：验证 AI disabled 和 fake AI enabled 两种模式。
2. 备份恢复。
   - 步骤 1：备份包含 photos、categories、slide_designs、jobs、地点字段、AI 字段。
   - 步骤 2：恢复演练后校验照片、对象、slide design、地点和分类记录一致。
   - 步骤 3：确保 `.env` 只在显式允许时备份。
3. Docker 构建和运行。
   - 步骤 1：后端、前端镜像构建通过。
   - 步骤 2：Worker 容器带 AI 和地理编码配置。
   - 步骤 3：无真实 AI key 时仍可运行。
4. 文档。
   - 步骤 1：README 更新 v0.2 功能说明。
   - 步骤 2：新增地理编码配置说明。
   - 步骤 3：新增 AI 配置说明。
   - 步骤 4：新增常见故障排查：API 限流、AI 超时、右键无效、滚轮过快等。

### 完成指标

1. `just test-backend` 通过。
2. 前端 build 通过。
3. `just accept-v0-2` 通过。
4. 备份恢复演练通过。
5. README 能指导新环境部署和验收。

### 验收指标

1. 从干净数据库上传照片后，最终能在 `/showcase` 播放。
2. 有 GPS 测试图能显示 fake provider 地点。
3. 鼠标左键、右键、滚轮均能控制播放。
4. AI 关闭时 fallback 可用；fake AI 开启时 AI design 可用。
5. 恢复后照片、地点、分类记录和 slide design 数据一致。

---

## 12. 关键依赖关系

```text
阶段 0 验收基线
  ├── 阶段 1 数据模型
  │     ├── 阶段 2 地理编码 Worker
  │     ├── 阶段 4 Renderer v0.2
  │     └── 阶段 5 AI Agent
  ├── 阶段 3 showcase 交互
  └── 阶段 7 端到端验收

阶段 5 AI Agent 依赖阶段 4 Renderer 安全边界。
阶段 6 管理后台依赖阶段 1/2/5 的数据和任务状态。
阶段 7 必须在所有 P0 阶段完成后执行。
```

## 13. 风险与规避

| 风险 | 影响 | 概率 | 规避策略 |
|---|---|---:|---|
| 外部地理编码 API 限流或不可用 | 地点无法展示 | 中 | 默认 fake/noop provider，失败不阻断播放，增加缓存 |
| DeepSeek/Ollama 不稳定 | AI design 无法生成 | 高 | AI 默认可关闭，fake provider 测试，fallback design 始终可用 |
| Renderer 放开 scoped CSS 后产生安全风险 | 前端被污染或布局失控 | 中 | v0.2 优先 CSS Variables；scoped CSS 必须白名单清洗 |
| 分类系统仍硬编码 | 后续扩展困难 | 高 | v0.2 阶段 1 必须降低 Literal/枚举依赖 |
| 鼠标事件误触发菜单操作 | 用户体验差 | 中 | 明确交互区域排除规则，增加浏览器测试 |
| 验收脚本依赖真实外部服务 | CI/本地不可复现 | 高 | 验收默认使用 fake AI 和 fake geocoding provider |

## 14. v0.2 最终交付标准

v0.2 完成时，应满足：

1. v0.1 审查报告中的 P0/P1 问题已修复或有明确文档边界。
2. 用户登录后进入 `/showcase`，可用键盘和鼠标自然播放。
3. 上传照片后，Worker 能稳定生成 preview、thumbnail、fallback slide design，并在可用时补充地点和 AI 设计。
4. Slide Renderer 对 AI 输出有安全边界，未知 layer 不破坏页面。
5. 管理员能查看和修正分类、地点、AI 文案、任务失败。
6. Docker 环境可构建、可运行、可验收、可备份恢复。
