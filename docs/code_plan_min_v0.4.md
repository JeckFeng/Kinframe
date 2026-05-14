# KinFrame v0.4 开发计划方案

> 版本：v1.0
> 日期：2026-05-14
> 基于：`docs/Kinframe_PRD.md` v1.1 + `docs/Frontend_Rendering_Strategies.md`
> Issue 文件目录：`docs/issues_v0.4/`

---

## 1. v0.4 版本最终目标

v0.4 在 v0.3 完整的 P0+P1 功能基础上，实现两项 P2 增强功能：

1. **自动播放系统**：用户可通过 Space 键开启/暂停自动放映，在顶部菜单配置播放间隔（3s/5s/8s），系统按间隔自动切换同类照片。
2. **地图相册**：用户可在 `/map` 页面，在中国地图上查看已地理编码的照片标记（圆形缩略图），按分类筛选，点击标记查看照片信息并跳转详情。

两项功能独立、互不依赖，可并行开发。

---

## 2. v0.4 新增功能清单

| 编号 | 功能 | 对应 Issue | 类型 |
|------|------|-----------|------|
| F1 | Space 键自动播放开关（播放/暂停） | v0.4-01 | 前端 |
| F2 | 自动播放间隔配置（3s / 5s / 8s），顶部菜单按钮组 | v0.4-01 | 前端 |
| F3 | 自动播放状态指示器（底部进度条，鼠标静止2秒后自动隐藏） | v0.4-01 | 前端 |
| F4 | 手动导航自动停止播放（← → ↑ ↓ / 鼠标 / 滚轮 / 触摸手势） | v0.4-01 | 前端 |
| F5 | 地图相册后端 API：`GET /api/map/photos?category=` | v0.4-02 | 后端 |
| F6 | `/map` 页面：全视口中国地图 + Leaflet | v0.4-03 | 前端 |
| F7 | 照片 Marker：圆形缩略图，坐标定位 | v0.4-03 | 前端 |
| F8 | Marker 弹出窗口：缩略图 + caption + 地点 + 日期 + "查看照片"链接 | v0.4-03 | 前端 |
| F9 | 地图分类筛选栏（全部 / 生活 / 摄影 / 萌宠） | v0.4-03 | 前端 |
| F10 | 地图入口：顶部菜单 MapPin 图标 + 键盘 `M` 键 | v0.4-03 | 前端 |
| F11 | 后端单元测试（map API） | v0.4-02 | 测试 |
| F12 | 前端 Playwright E2E 测试（自动播放 + 地图） | v0.4-01/03 | 测试 |
| F13 | v0.4 验收脚本 `scripts/v0.4-acceptance.sh` | 集成 | 测试 |

---

## 3. 开发阶段总览

v0.4 开发分为 3 个阶段：

```
Phase 1: 后端基础                    Phase 2: 前端功能
┌─────────────────────┐              ┌──────────────────────────────┐
│ v0.4-02 Map Data API │              │ Track A: v0.4-01 Auto-play   │
│                      │              │ Track B: v0.4-03 Map Page    │
└────────┬─────────────┘              └─────────────┬────────────────┘
         │                                          │
         └──────────────┬───────────────────────────┘
                        ▼
              Phase 3: 集成验证 & 验收
              ┌──────────────────────────────┐
              │ v0.4-acceptance.sh           │
              │ E2E testing                  │
              │ justfile recipes             │
              │ README update                │
              └──────────────────────────────┘
```

| 阶段 | 名称 | 对应 Issue | 预估工时 |
|------|------|-----------|---------|
| Phase 1 | 后端基础 — 地图数据 API | v0.4-02 | 0.5 天 |
| Phase 2 | 前端功能 — 自动播放 + 地图相册 | v0.4-01, v0.4-03 | 2-3 天 |
| Phase 3 | 集成验证 & 验收脚本 | 全部 | 1 天 |

---

## 4. Phase 1：后端基础 — 地图数据 API

**对应 Issue**：[v0.4-02-map-api.md](issues_v0.4/v0.4-02-map-api.md)

### 4.1 阶段目标

提供 `GET /api/map/photos` 端点，返回可用于地图标记的照片地理数据（GPS 坐标 + 位置文本 + 预览 URL + 描述信息）。前端地图页面可在真实 API 就绪之前用 mock 数据并行开发。

### 4.2 任务拆解

#### 任务 1.1：定义 Pydantic Schema

**执行步骤**：
1. 在 `backend/app/schemas/photo.py` 中新增 `MapPhotoItem` 和 `MapPhotosResponse` 两个 Pydantic model
2. `MapPhotoItem` 字段：`photo_id`, `preview_url`, `thumbnail_url`, `category`, `gps_lat`, `gps_lng`, `location_name`, `location_city`, `location_region`, `location_country`, `location_district`, `final_caption`, `taken_at`
3. 添加 `model_config` 配置 `from_attributes=True`

**涉及文件**：`backend/app/schemas/photo.py`

#### 任务 1.2：实现 API 路由

**执行步骤**：
1. 在 `backend/app/api/photos.py`（或新建 `backend/app/api/map.py`）中新增 `GET /map/photos` 路由
2. 依赖注入：`DbSession`, `get_current_user`（鉴权）, `ObjectStorage`（生成 presigned URL）
3. 查询条件：`status == 'ready' AND gps_lat IS NOT NULL AND gps_lng IS NOT NULL AND geocoding_status == 'success'`
4. 支持 `?category=` 可选过滤参数
5. 按 `taken_at DESC` 排序
6. 遍历结果，为每条记录生成 `preview_url` 和 `thumbnail_url` 的 presigned URL
7. 构造 `MapPhotosResponse` 并返回

**涉及文件**：`backend/app/api/photos.py`（或新建 `backend/app/api/map.py` + 修改 `backend/app/main.py` 注册路由）

#### 任务 1.3：编写后端测试

**执行步骤**：
1. 创建 `backend/tests/test_map.py`
2. 测试用例：
   - 无 GPS 照片时返回空列表
   - 仅返回 `geocoding_status == 'success'` 的照片
   - `?category=life` 筛选正确
   - 排除 `status != 'ready'` 的照片
   - 排除无 GPS 坐标的照片
   - 未认证请求返回 401
   - 认证请求返回 200，验证 presigned URL 格式
3. 运行 `uv run pytest tests/test_map.py -x -q` 确保全部通过

**涉及文件**：`backend/tests/test_map.py`

### 4.3 阶段完成指标

- [ ] `MapPhotoItem` 和 `MapPhotosResponse` schema 定义完成且类型检查通过
- [ ] `GET /api/map/photos` 返回 200（有地理数据时）或 200 + 空列表（无地理数据时）
- [ ] `?category=life` 筛选功能正常
- [ ] 返回字段包含 GPS 坐标、位置文本、presigned URL
- [ ] 未登录请求返回 401
- [ ] pytest 测试不少于 6 个用例，全部通过
- [ ] 现有 182+ 后端测试不受影响

### 4.4 必须测试的功能

| 测试项 | 测试方法 | 测试文件 |
|--------|---------|---------|
| Map API 返回 geocoded 照片 | pytest | `tests/test_map.py` |
| category 筛选 | pytest | `tests/test_map.py` |
| 401 未认证拦截 | pytest | `tests/test_map.py` |
| 空数据集处理 | pytest | `tests/test_map.py` |
| 排除无 GPS / 非 ready 照片 | pytest | `tests/test_map.py` |
| 现有 182+ 测试无回归 | pytest | 全量 `uv run pytest` |

---

## 5. Phase 2：前端功能 — 自动播放 + 地图相册

**对应 Issue**：[v0.4-01-autoplay.md](issues_v0.4/v0.4-01-autoplay.md) + [v0.4-03-map-page.md](issues_v0.4/v0.4-03-map-page.md)

### 5.1 阶段目标

在 `/showcase` 页面集成自动播放系统（Space 键开关 + 间隔配置 + 进度指示器）；新建 `/map` 页面，使用 Leaflet 渲染中国地图，以圆形缩略图标记已地理编码的照片，支持分类筛选和弹出详情。

两个功能独立开发，互不阻塞。

---

### Track A：自动播放系统（v0.4-01）

#### 任务 2A.1：自动播放状态与定时器

**执行步骤**：
1. 在 `frontend/pages/showcase.vue` 的 `<script setup>` 中新增状态变量：
   - `isAutoPlaying: Ref<boolean>`（初始 `false`）
   - `autoPlayInterval: Ref<number>`（默认 `5000`，即 5s）
   - `autoPlayTimer: Ref<ReturnType<typeof setInterval> | null>`（初始 `null`）
2. 实现 `startAutoPlay()`：
   - 设置 `isAutoPlaying = true`
   - 启动 `setInterval`，每个 tick 调用 `nextPhoto()`
   - 将 timer handle 存入 `autoPlayTimer`
3. 实现 `stopAutoPlay()`：
   - 设置 `isAutoPlaying = false`
   - 清除 `clearInterval(autoPlayTimer.value)`
   - 将 `autoPlayTimer` 置 `null`
4. 实现 `toggleAutoPlay()`：根据 `isAutoPlaying` 状态调用 start/stop
5. 实现 `setAutoPlayInterval(ms: number)`：
   - 更新 `autoPlayInterval`
   - 如果当前正在播放，先 `stopAutoPlay()` 再 `startAutoPlay()`（用新间隔重启）
6. 在 `onUnmounted` 中 `clearInterval` 防止内存泄漏

**涉及文件**：`frontend/pages/showcase.vue`

#### 任务 2A.2：键盘 Space 处理

**执行步骤**：
1. 在现有 `onKeydown` 函数中添加 `Space` case
2. 调用 `e.preventDefault()` 阻止页面滚动
3. 调用 `toggleAutoPlay()`
4. 确保 `input` / `textarea` 内不触发（复用已有 `isTypingInput` 逻辑）

**涉及文件**：`frontend/pages/showcase.vue`

#### 任务 2A.3：手动导航停止自动播放

**执行步骤**：
1. 在以下函数/处理器开头添加 `stopAutoPlay()` 调用：
   - `nextPhoto()`
   - `previousPhoto()`
   - `moveCategory()`
   - 鼠标左键点击 handler
   - 鼠标右键/contextmenu handler
   - 鼠标滚轮 handler
   - 触摸滑动 handler

**涉及文件**：`frontend/pages/showcase.vue`

#### 任务 2A.4：顶部菜单 UI 控件

**执行步骤**：
1. 从 `lucide-vue-next` 导入 `Play` 和 `Pause` 图标组件
2. 在顶部菜单 `<div>` 的中间区域添加控件组：
   - **Play/Pause 按钮**：`h-9 w-9` 圆角按钮，`hover:bg-white/10`
   - **间隔选择器**：三个按钮 `3s` / `5s` / `8s`，当前选中高亮（`bg-white/15 text-white`），未选中半透明（`text-white/60`），`px-2 py-1 text-xs rounded-md`
3. 按钮用 `@click` 绑定对应函数
4. 按钮样式与现有菜单风格一致（半透明毛玻璃）

**涉及文件**：`frontend/pages/showcase.vue`

#### 任务 2A.5：播放状态指示器

**执行步骤**：
1. 在 slide 渲染区域底部添加进度条元素
2. 进度条结构：
   - 外层：`absolute bottom-24 left-1/2 -translate-x-1/2 w-32 h-0.5 bg-white/10 rounded-full overflow-hidden`
   - 内层：`h-full bg-white/40 rounded-full`，宽度定时递增模拟进度
3. 显示控制：`v-if="isAutoPlaying"`
4. `indicatorVisible` ref 管理可见性：
   - `pointermove` → 设置 visible = true，重置隐藏计时器
   - 2s 无鼠标移动 → visible = false
5. 可见性切换用 CSS `opacity` 过渡 `0.6s`

**涉及文件**：`frontend/pages/showcase.vue`

---

### Track B：地图相册页面（v0.4-03）

#### 任务 2B.1：安装依赖 + 类型定义

**执行步骤**：
1. 安装 Leaflet：`pnpm add leaflet @types/leaflet`
2. 在 `frontend/types/api.ts` 中新增 TypeScript 接口：
   - `MapPhotoItem`：包含 `photo_id`, `preview_url`, `thumbnail_url`, `category`, `gps_lat`, `gps_lng`, `location_name`, `location_city`, `location_region`, `location_country`, `location_district`, `final_caption`, `taken_at`
   - `MapPhotosResponse`：`{ photos: MapPhotoItem[] }`

**涉及文件**：`frontend/package.json`, `frontend/pnpm-lock.yaml`, `frontend/types/api.ts`

#### 任务 2B.2：创建 `/map` 页面

**执行步骤**：
1. 创建 `frontend/pages/map/index.vue`
2. 页面结构：
   - 顶层：`<div class="fixed inset-0 bg-neutral-950">`
   - "返回放映" 链接：`<NuxtLink to="/showcase">`，左上角绝对定位
   - 分类筛选栏：顶部绝对定位，水平 pill 按钮组
   - 地图容器：`<div ref="mapContainer" class="w-full h-full">`
   - 加载状态：`<div v-if="pending">` "加载中..."
   - 空状态：`<div v-else-if="photos.length === 0">` "暂无位置数据"
3. 认证检查：在 `onMounted` 中调用 `loadMe()`，未登录重定向到 `/login`
4. 数据获取：使用 `useApi` composable 调用 `GET /api/map/photos?category=`

**涉及文件**：`frontend/pages/map/index.vue`

#### 任务 2B.3：Leaflet 地图初始化

**执行步骤**：
1. 在 `onMounted` 中创建 Leaflet 地图实例：
   - `L.map(mapContainer, { center: [35.86, 104.19], zoom: 5 })`（中国中心坐标）
   - Tile layer：`https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png`
   - `L.layerGroup()` 管理 marker 图层
2. 在 `onUnmounted` 中调用 `mapInstance.remove()` 销毁地图
3. 监听 `photos` 和 `activeCategory` 变化，调用 `updateMarkers()`
4. 组件包裹 `<ClientOnly>` 避免 Nuxt SSR 时 `window is not defined` 错误

**涉及文件**：`frontend/pages/map/index.vue`

#### 任务 2B.4：Marker 渲染（圆形缩略图）

**执行步骤**：
1. 实现 `updateMarkers()` 函数：
   - 清除 `markersLayer` 现有内容
   - 遍历 `photos`，为每个 photo 创建 `L.divIcon`
2. `divIcon` HTML：`<div style="background-image: url(thumbnail_url); background-size: cover; background-position: center" class="w-10 h-10 rounded-full border-2 border-white/80 shadow-lg overflow-hidden">`
3. `iconSize: [40, 40]`, `iconAnchor: [20, 20]`
4. 创建 `L.marker([lat, lng], { icon })`，绑定 popup，添加到 `markersLayer`
5. 添加全局 CSS 覆盖 `.kf-map-marker` 去除 Leaflet 默认图标样式

**涉及文件**：`frontend/pages/map/index.vue`

#### 任务 2B.5：Marker Popup 弹出窗口

**执行步骤**：
1. 实现 `popupContent(photo: MapPhotoItem): string` 函数
2. Popup 内容：缩略图 + final_caption + 地点（📍）+ taken_at（中文日期格式）+ "查看照片 →"链接
3. 实现 `escapeHtml()` 辅助函数防止 XSS
4. Popup 配置：`maxWidth: 280, closeButton: true`

**涉及文件**：`frontend/pages/map/index.vue`

#### 任务 2B.6：分类筛选栏

**执行步骤**：
1. 复用 `usePhotoCategories` composable 获取分类列表
2. 筛选栏使用水平 pill 按钮组布局
3. "全部" 按钮（`activeCategory = null`）+ 各分类按钮
4. 选中态 `bg-white text-stone-900`，未选中 `bg-white/10 text-white/70`
5. 切换 `activeCategory`，触发 `watch` 重新拉取并更新 marker
6. 筛选栏背景：半透明毛玻璃 `bg-neutral-950/60 backdrop-blur-md`

**涉及文件**：`frontend/pages/map/index.vue`

#### 任务 2B.7：导航入口

**执行步骤**：
1. 在 `frontend/pages/showcase.vue` 顶部菜单添加"地图"入口：
   - 导入 `MapPin` from `lucide-vue-next`
   - `<NuxtLink to="/map" title="地图">` 与 Gallery、Upload 按钮同一组
2. 在 `onKeydown` 中添加 `M` 键处理：
   - `e.preventDefault()` + `navigateTo('/map')`

**涉及文件**：`frontend/pages/showcase.vue`

---

### 5.3 Track A 完成指标

- [ ] Space 键按下，自动播放开始（首次）/ 暂停（再次）
- [ ] 自动播放按配置间隔自动调用 `nextPhoto()`
- [ ] 修改间隔后实时生效（播放中重启定时器）
- [ ] 任何手动导航操作停止自动播放
- [ ] 顶部菜单显示 Play/Pause 按钮和间隔选择器按钮组
- [ ] 播放状态指示器在播放时可见，鼠标静止 2s 后渐隐
- [ ] Space 在 `input`/`textarea` 内不触发
- [ ] 组件卸载时 clearInterval 不泄漏

### 5.4 Track B 完成指标

- [ ] `/map` 页面正常加载，显示全视口地图
- [ ] 地图支持拖拽平移和滚轮缩放
- [ ] 有 GPS 数据的照片显示为圆形缩略图 marker
- [ ] 点击 marker 弹出详细信息窗口
- [ ] 分类筛选栏切换后 marker 更新
- [ ] "查看照片"链接导航到 `/photo/[id]`
- [ ] "返回放映"链接导航到 `/showcase`
- [ ] 无地理数据时显示空状态提示
- [ ] 未登录访问重定向到 `/login`
- [ ] 顶部菜单"地图"入口和键盘 `M` 键导航正常

### 5.5 必须测试的功能

| 测试项 | 测试方法 | 测试文件 | Track |
|--------|---------|---------|------|
| Space 键切换自动播放 | Playwright | `tests/e2e/showcase.spec.ts` | A |
| 自动播放间隔切换照片 | Playwright | `tests/e2e/showcase.spec.ts` | A |
| 间隔按钮切换 | Playwright | `tests/e2e/showcase.spec.ts` | A |
| 手动导航停止播放 | Playwright | `tests/e2e/showcase.spec.ts` | A |
| `/map` 页面加载 | Playwright | `tests/e2e/map.spec.ts` | B |
| 地图 marker 显示 | Playwright | `tests/e2e/map.spec.ts` | B |
| 分类筛选功能 | Playwright | `tests/e2e/map.spec.ts` | B |
| 地图入口导航（菜单 + M 键） | Playwright | `tests/e2e/map.spec.ts` | B |
| 地图空状态 | Playwright | `tests/e2e/map.spec.ts` | B |
| TypeScript 编译 | `vue-tsc --noEmit` | - | A+B |

---

## 6. Phase 3：集成验证 & 验收脚本

**对应 Issue**：全部（v0.4-01, v0.4-02, v0.4-03）

### 6.1 阶段目标

将所有 v0.4 功能串联验证，编写 E2E 测试、验收脚本和 justfile 配方，更新 README，确保 `just accept-v0-4` 全流程通过。

### 6.2 任务拆解

#### 任务 3.1：E2E 测试 — 自动播放

**执行步骤**：
1. 在 `frontend/tests/e2e/showcase.spec.ts` 中新增 `Auto-play` describe block
2. 测试用例：
   - Space 键触发自动播放
   - 自动播放启动后照片在间隔后自动切换
   - 再次按 Space 停止自动播放
   - 自动播放期间按 ArrowRight 停止播放
   - 菜单中点击间隔按钮切换间隔
3. 使用 `page.keyboard.press('Space')` 和 `page.waitForTimeout()` 验证

**涉及文件**：`frontend/tests/e2e/showcase.spec.ts`

#### 任务 3.2：E2E 测试 — 地图相册

**执行步骤**：
1. 新建 `frontend/tests/e2e/map.spec.ts`
2. 测试用例：
   - 从 `/showcase` 按 `M` 键导航到 `/map`
   - `/map` 页面地图容器可见
   - 分类筛选按钮全部显示
   - "返回放映"链接导航到 `/showcase`
   - 无 geocoded 数据时显示空状态
   - 顶部菜单"地图"图标点击导航到 `/map`

**涉及文件**：`frontend/tests/e2e/map.spec.ts`

#### 任务 3.3：v0.4 验收脚本

**执行步骤**：
1. 创建 `scripts/v0.4-acceptance.sh`
2. 脚本结构（在 v0.3 脚本基础上增量添加 v0.4 验证步骤）：

```
Step 1-8：复用 v0.3 基础设施/认证/上传/处理/Showcase/Admin/Schema 验证
Step 9：备份/恢复（复用 v0.3 步骤）
Step 10：自动播放验证
  - 检查 showcase.vue 包含 isAutoPlaying 状态变量
  - 检查 showcase.vue 包含 autoPlayInterval 默认值
  - 检查 showcase.vue 包含 Space 键处理
  - 检查 showcase.vue 包含 Play/Pause 图标引用
Step 11：地图相册验证
  - 检查 map API 返回 200
  - 检查 map API 返回数据包含 GPS 坐标字段
  - 检查 /map 页面文件存在
  - 检查 Leaflet 依赖已安装
  - 检查 showcase.vue 包含 MapPin 图标和 M 键处理
Step 12：Playwright E2E 测试（含新增测试）
Step 13：汇总 PASS/FAIL
```

3. 脚本遵循 v0.3 经验教训：
   - Python 代码块使用 `python3 -c "..."` 双引号
   - `cd "$ROOT_DIR"` 在 Playwright 测试后恢复工作目录
   - 上传 409 容错处理

**涉及文件**：`scripts/v0.4-acceptance.sh`

#### 任务 3.4：justfile 配方 + README 更新

**执行步骤**：
1. 在 `justfile` 中添加 `accept-v0-4` recipe
2. 在 `README.md` 中添加 v0.4 What's New 章节：
   - Auto-play (Space key, configurable intervals)
   - Map album page
   - New `/map` route
3. 更新 Navigation 表格：添加 Space (Toggle auto-play) 和 M (Map album)
4. 更新 Testing And Acceptance 章节：添加 `just accept-v0-4` 命令
5. 更新 Architecture 说明（新增 `/map` 路由）

**涉及文件**：`justfile`, `README.md`

#### 任务 3.5：全量回归测试

**执行步骤**：
1. 后端：`just test-backend` — 182+ 原有 + 新增 map 测试全部通过
2. 前端单元：`just test-frontend` — 120+ 测试全部通过
3. Playwright：`just test-e2e` — 原有 40+ + 新增全部通过
4. TypeScript：`pnpm exec vue-tsc --noEmit` 无错误
5. 完整验收：`just accept-v0-4` 全部 PASS

### 6.3 阶段完成指标

- [ ] 自动播放 E2E 测试不少于 4 个用例，全部通过
- [ ] 地图相册 E2E 测试不少于 5 个用例，全部通过
- [ ] `scripts/v0.4-acceptance.sh` 可执行，全部步骤 PASS
- [ ] `just accept-v0-4` 配方可用且全部通过
- [ ] README.md 已更新 v0.4 内容
- [ ] 后端 pytest 全量通过（无回归）
- [ ] 前端 vitest 全量通过（无回归）
- [ ] Playwright E2E 全量通过（无回归）

### 6.4 必须测试的功能

| 测试项 | 测试方法 | 阶段 |
|--------|---------|------|
| 后端全量回归 | `just test-backend` | Phase 3 |
| 前端全量回归 | `just test-frontend` | Phase 3 |
| Playwright 全量回归 | `just test-e2e` | Phase 3 |
| TypeScript 编译 | `pnpm exec vue-tsc --noEmit` | Phase 3 |
| 完整验收流程 | `just accept-v0-4` | Phase 3 |

---

## 7. v0.4 测试矩阵总表

### 7.1 功能测试

| 功能 | 测试方式 | 测试文件 | 阶段 |
|------|---------|---------|------|
| Map API 返回 200 + 正确数据 | pytest | `backend/tests/test_map.py` | Phase 1 |
| Map API 筛选 category | pytest | `backend/tests/test_map.py` | Phase 1 |
| Map API 401 未认证 | pytest | `backend/tests/test_map.py` | Phase 1 |
| Map API 空数据处理 | pytest | `backend/tests/test_map.py` | Phase 1 |
| Space 键切换自动播放 | Playwright | `tests/e2e/showcase.spec.ts` | Phase 3 |
| 自动播放间隔切换照片 | Playwright | `tests/e2e/showcase.spec.ts` | Phase 3 |
| 间隔按钮切换 | Playwright | `tests/e2e/showcase.spec.ts` | Phase 3 |
| 手动导航停止播放 | Playwright | `tests/e2e/showcase.spec.ts` | Phase 3 |
| `/map` 页面加载 | Playwright | `tests/e2e/map.spec.ts` | Phase 3 |
| 地图 marker 显示 | Playwright | `tests/e2e/map.spec.ts` | Phase 3 |
| 分类筛选功能 | Playwright | `tests/e2e/map.spec.ts` | Phase 3 |
| 地图入口导航 | Playwright | `tests/e2e/map.spec.ts` | Phase 3 |
| 地图空状态 | Playwright | `tests/e2e/map.spec.ts` | Phase 3 |
| 全量验收 | bash 脚本 | `scripts/v0.4-acceptance.sh` | Phase 3 |

### 7.2 兼容性测试

| 平台 | 测试方式 | 阶段 |
|------|---------|------|
| Linux + Chrome Desktop (1280×720) | Playwright desktop project | Phase 3 |
| Linux + Chrome Mobile (390×844) | Playwright mobile project | Phase 3 |
| 地图页面移动端响应式 | Playwright mobile project | Phase 3 |

---

## 8. 风险与注意事项

### 8.1 技术风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Leaflet 与 Nuxt 3 SSR 冲突 | `/map` 页面报错 `window is not defined` | 使用 `<ClientOnly>` 包裹地图组件；`import L from 'leaflet'` 仅在 `onMounted` 中执行 |
| Leaflet CSS 路径解析 | 地图控件样式丢失 | 在页面 `<style>` 中显式 `@import 'leaflet/dist/leaflet.css'` |
| 地理编码数据不足 | 地图页面无 marker 可显示 | E2E 测试用 seed 脚本插入测试 GPS 数据；验收脚本容错空数据 |
| 自动播放定时器内存泄漏 | 组件卸载后 timer 继续运行 | 在 `onUnmounted` 中 `clearInterval` |
| Docker 容器端口冲突 | `just accept-v0-4` 启动失败 | 遵循 CLAUDE.md 规范，验收前检查 `docker ps` 清理残留容器 |

### 8.2 注意事项

1. **Geocoding 数据准备**：Phase 1 测试需要照片有 GPS + geocoding 数据。如果测试数据库中没有此类数据，需通过 Admin API 手动注入或编写 seed fixture。
2. **地图 Tile 服务**：默认使用 OpenStreetMap 免费 tile，无需 API key。如需更好的中文地图标注，可切换到高德 tile（不强制）。
3. **自动播放间隔**：3s/5s/8s 三个选项硬编码在 showcase.vue 中。未来可扩展至用户设置页面持久化存储偏好。
4. **验收脚本顺序**：v0.4 验收脚本从 v0.3 复制改造。核心新增步骤在 Step 10（自动播放）和 Step 11（地图相册），其余步骤复用 v0.3。

---

## 9. 完成定义 (Definition of Done)

v0.4 版本被认为完成，当且仅当：

1. **代码**：Phase 1-2 所有任务完成，代码合入 main 分支
2. **测试**：后端 pytest 全量通过、前端 vitest 全量通过、Playwright E2E 全量通过
3. **验收**：`just accept-v0-4` 执行输出全部 PASS，0 FAILED
4. **文档**：README.md 包含 v0.4 What's New 和新增命令说明
5. **整洁**：无 `console.log`、debug 注释、未使用 import 残留

## 10. 全局行为规范准则：
  1. 任何新写的脚本/命令，写完必须实际执行一次，不依赖脑内模拟，用实际运行结果说话。
  2. 区分"单元测试通过"和"端到端验收通过"，不混用这两个概念
  3. 遇到错误时，先诊断根因再修改，不试错式修复
