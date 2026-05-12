# KinFrame 最小功能版本 v0 开发步骤

本文档定义 KinFrame 的最小功能版本 v0。v0 的目标不是完成完整产品，而是先做出一个**本地可运行、可登录、可上传照片、可保存到 MinIO、可解析基础 EXIF、可按分类浏览照片**的核心闭环。

v0 暂不做：Ollama 视觉识别、DeepSeek 自动描述、Chatbot 入库、Cloudflare Tunnel 外网访问、复杂 Worker 队列、Windows 迁移演练、年度回忆、地图相册、人脸识别。

## v0 完成目标

1. 开发者可以用统一命令启动本地开发环境。
2. 管理员可以登录并创建家庭成员账号。
3. 登录用户可以上传 JPEG/PNG/WebP 图片。
4. 原图保存到 MinIO 私有 bucket。
5. 后端保存照片元数据到 PostgreSQL。
6. 后端能读取基础 EXIF 信息，缺失时不报错。
7. 用户可以手动选择分类：`life`、`travel`、`pet`。
8. 前端可以展示全部照片、分类照片和照片详情。
9. 未登录用户不能访问照片接口和图片访问地址。

## 阶段 0：项目骨架初始化

### 目标

建立 v0 所需的最小目录、配置文件和统一命令。

### 开发任务

1. 创建基础目录：
   - `frontend/`
   - `backend/`
   - `deploy/caddy/`
   - `deploy/minio/`
   - `scripts/`
   - `data/`
2. 创建根目录文件：
   - `README.md`
   - `.env.example`
   - `.gitignore`
   - `.gitattributes`
   - `docker-compose.infra.yml`
   - `justfile`
3. 在 `.gitignore` 中排除：
   - `.env`
   - `data/`
   - `frontend/node_modules/`
   - `frontend/.nuxt/`
   - `frontend/.output/`
   - `backend/.venv/`
   - `backend/__pycache__/`
   - `backend/.pytest_cache/`
4. 在 `.env.example` 中先提供 v0 必需变量：
   - `APP_ENV`
   - `APP_SECRET_KEY`
   - `DATABASE_URL`
   - `REDIS_URL`
   - `MINIO_ENDPOINT`
   - `MINIO_ACCESS_KEY`
   - `MINIO_SECRET_KEY`
   - `MINIO_BUCKET`
   - `MAX_UPLOAD_SIZE_MB`
   - `ALLOWED_IMAGE_TYPES`
   - `SESSION_COOKIE_NAME`
   - `SESSION_EXPIRE_DAYS`
5. 在 `justfile` 中提供最小命令：
   - `just infra`
   - `just infra-down`
   - `just backend`
   - `just frontend`
   - `just dev`
   - `just test-backend`

## 阶段 1：Docker 虚拟环境准备

### 目标

在 Docker 环境中先安装并验证 v0 所需的大部分依赖、第三方库和工具，避免后续开发频繁补环境。

### 开发任务

1. 编写 `docker-compose.infra.yml`，包含：
   - PostgreSQL 16
   - Redis 7
   - MinIO
   - Caddy，可先作为本地反向代理预留
2. 准备 `backend/Dockerfile` 或后端依赖说明，覆盖：
   - Python
   - uv
   - FastAPI
   - Uvicorn
   - Pydantic
   - SQLAlchemy
   - Alembic
   - PostgreSQL 驱动
   - Redis 客户端
   - MinIO/S3 客户端
   - Pillow 或等价图片处理库
   - ExifTool 调用依赖
   - pytest
3. 准备 `frontend/Dockerfile` 或前端依赖说明，覆盖：
   - Node.js
   - Corepack
   - pnpm
   - Nuxt 3
   - Vue
   - TypeScript
   - Tailwind CSS
4. 安装并验证系统工具：
   - `exiftool`
   - `curl`
   - `bash`
   - `ca-certificates`
   - 基础图片处理依赖
5. 编写 `scripts/check-docker-env.sh`：
   - 检查 PostgreSQL、Redis、MinIO 容器状态。
   - 检查后端容器或环境中 Python、uv、ExifTool 是否可执行。
   - 检查关键 Python 包是否可导入。
   - 检查前端环境中 Node、pnpm 是否可执行。

## 阶段 2：后端基础服务

### 目标

建立 FastAPI 后端骨架，连接数据库、Redis 和 MinIO，并提供健康检查。

### 开发任务

1. 初始化 `backend/`：
   - `pyproject.toml`
   - `uv.lock`
   - `alembic.ini`
   - `app/main.py`
   - `app/core/config.py`
   - `app/core/database.py`
   - `app/core/security.py`
   - `app/api/`
   - `app/models/`
   - `app/schemas/`
   - `app/services/`
   - `tests/`
2. 实现配置读取：
   - 从 `.env` 读取数据库、Redis、MinIO、上传限制和 Session 配置。
3. 实现数据库连接：
   - SQLAlchemy engine/session。
   - Alembic 迁移配置。
4. 实现健康检查接口：
   - `GET /api/health`
   - 返回数据库、Redis、MinIO 连接状态。
5. 初始化测试框架：
   - pytest 可运行。
   - 添加健康检查测试。

## 阶段 3：账号登录与权限控制

### 目标

完成 v0 私有系统的最小账号体系：管理员和成员都必须登录后才能使用照片功能。

### 开发任务

1. 设计 `users` 表：
   - `id`
   - `username`
   - `display_name`
   - `password_hash`
   - `role`
   - `is_active`
   - `created_at`
   - `last_login_at`
2. 实现密码哈希：
   - 使用 Argon2 或 bcrypt。
3. 实现 Session Cookie：
   - `HttpOnly`
   - `SameSite=Lax`
   - 开发环境可先不启用 `Secure`
4. 实现认证 API：
   - `POST /api/auth/login`
   - `POST /api/auth/logout`
   - `GET /api/auth/me`
5. 实现最小管理员能力：
   - 初始化管理员账号脚本。
   - `GET /api/admin/users`
   - `POST /api/admin/users`
6. 实现权限依赖：
   - 未登录返回 401。
   - 非管理员访问管理接口返回 403。

## 阶段 4：照片上传、MinIO 存储与 EXIF

### 目标

完成不依赖 AI 的照片入库流程：上传、保存原图、写数据库、解析 EXIF、手动分类。

### 开发任务

1. 设计 `photos` 表：
   - `id`
   - `owner_id`
   - `category`
   - `user_message`
   - `final_caption`
   - `bucket`
   - `object_key_original`
   - `object_key_thumbnail`
   - `mime_type`
   - `file_size`
   - `sha256`
   - `width`
   - `height`
   - `taken_at`
   - `uploaded_at`
   - `gps_lat`
   - `gps_lng`
   - `camera_make`
   - `camera_model`
   - `exif_json`
   - `status`
   - `created_at`
   - `updated_at`
2. 实现 MinIO 服务层：
   - 创建 bucket。
   - 上传原图。
   - 上传缩略图。
   - 生成短期 presigned URL。
   - 删除对象。
3. 实现上传 API：
   - `POST /api/photos/upload`
   - 限制文件大小。
   - 限制 MIME 类型。
   - 计算 `sha256`。
   - 重复图片返回明确提示。
4. 实现 EXIF 解析：
   - 拍摄时间。
   - GPS 经纬度。
   - 设备品牌和型号。
   - 图片宽高。
   - 原始 EXIF JSON。
   - 缺失 EXIF 时使用上传时间兜底。
5. 实现缩略图：
   - v0 只要求生成列表页可用的 thumbnail。
   - HEIC/HEIF 可暂缓到 v1，但接口要给出“不支持或处理失败”的明确错误。
6. 实现照片 API：
   - `GET /api/photos`
   - `GET /api/photos/{photo_id}`
   - `PATCH /api/photos/{photo_id}`
   - `DELETE /api/photos/{photo_id}`
   - `GET /api/photos/{photo_id}/thumbnail-url`
   - `GET /api/photos/{photo_id}/original-url`
7. 实现权限规则：
   - 成员可以查看所有照片。
   - 成员只能修改自己上传照片的分类和留言。
   - 管理员可以修改和删除所有照片。

## 阶段 5：前端最小可用界面

### 目标

让家庭成员可以通过网页完成登录、上传、浏览和查看详情。

### 开发任务

1. 初始化 `frontend/`：
   - Nuxt 3
   - Vue
   - TypeScript
   - Tailwind CSS
   - pnpm
2. 建立最小页面路由：
   - `/login`
   - `/gallery`
   - `/gallery/life`
   - `/gallery/travel`
   - `/gallery/pet`
   - `/photo/:id`
   - `/upload`
   - `/admin/users`
3. 实现 API 客户端：
   - 自动携带 Cookie。
   - 401 自动跳转登录页。
   - 统一错误提示。
4. 实现登录页：
   - 用户名输入。
   - 密码输入。
   - 登录失败提示。
5. 实现上传页：
   - 选择图片。
   - 选择分类。
   - 填写留言。
   - 展示上传成功或失败。
6. 实现相册页：
   - 展示所有照片。
   - 展示缩略图。
   - 支持按 `life`、`travel`、`pet` 分类查看。
7. 实现照片详情页：
   - 展示大图或原图访问链接。
   - 展示留言、分类、拍摄时间、设备信息。
   - 用户可编辑自己的分类和留言。
8. 实现最小用户管理页：
   - 管理员查看用户列表。
   - 管理员创建成员账号。

## 阶段 6：本地联调与 v0 验收

### 目标

把后端、前端、Docker 基础设施串起来，确认 v0 核心流程能完整跑通。

### 开发任务

1. 本地启动流程验证：
   - `just infra`
   - `just backend`
   - `just frontend`
2. 创建管理员账号。
3. 管理员登录并创建成员账号。
4. 成员登录并上传照片。
5. 检查 MinIO 中是否存在原图和缩略图。
6. 检查 PostgreSQL 中是否存在照片记录和用户记录。
7. 检查相册列表是否显示缩略图。
8. 检查详情页是否显示照片信息和 EXIF 信息。
9. 检查权限：
   - 未登录不能访问照片接口。
   - 普通成员不能创建用户。
   - 普通成员不能删除他人照片。
10. 添加 v0 后端测试：
   - 登录成功和失败。
   - 权限拒绝。
   - 上传文件类型限制。
   - EXIF 缺失不失败。
   - MinIO presigned URL 需要登录。
11. 更新 README：
   - v0 启动命令。
   - v0 功能范围。
   - 常见问题。

## v0 验收标准

1. `just infra` 能启动 PostgreSQL、Redis、MinIO。
2. `just backend` 能启动 FastAPI。
3. `just frontend` 能启动 Nuxt 前端。
4. 管理员可以创建成员账号。
5. 成员可以登录、上传照片、选择分类和填写留言。
6. 上传后的照片原图保存在 MinIO。
7. 上传后的照片元数据保存在 PostgreSQL。
8. 相册页能展示全部照片和三类分类照片。
9. 详情页能展示照片、留言、分类、拍摄时间和设备信息。
10. 未登录用户不能访问照片接口或图片 URL。
11. v0 后端关键测试通过。

## v0 之后再做的内容

1. 异步 Worker 和任务状态。
2. HEIC/HEIF 完整支持。
3. Ollama 视觉识别。
4. DeepSeek 自动描述。
5. Chatbot 入库确认。
6. Caddy + Cloudflare Tunnel 外网访问。
7. backup/restore 脚本和恢复演练。
8. Windows + WSL2 迁移验证。
9. 首页视觉、时间线、年度回忆和更完整的艺术化展示。
