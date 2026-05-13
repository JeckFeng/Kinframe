v0.1版本存在的缺少的功能或存在的问题如下：
1.缺少反向地理编码（调用 Nominatim/高德 API 将 GPS 坐标转为地名），无法在前端展示图片的拍摄地点。
2.缺少鼠标操作功能：目前只能通过键盘进行操作。需要加入鼠标操作功能：在showcase页面，点击鼠标左键返回上一张图片的播放页面，点击鼠标右键进入下一张图片的播放页面。鼠标的左右键对应着键盘的左方向键和右方向键。
3.缺少鼠标操作功能：目前只能通过键盘进行操作。需要加入鼠标操作功能：在showcase页面，滑动鼠标滚轮，自动切换到不同类别的图片展示集。鼠标滚轮对应着键盘的上下方向键。



没有彻底解决的宿主机/Docker 权限问题;
.nuxt 权限错误;


  1. 容器以宿主机用户运行：docker run --user "$(id -u):$(id -g)" ...
  2. 构建产物不写回宿主机：给 .nuxt、.output、node_modules、.pnpm-store 使用 Docker volume，而不是写到 bind mount 目录。

  更稳妥的方案通常是二者结合：源码 bind mount，生成物和依赖目录走 Docker volume，必要时容器用宿主机 UID 运行。这样既保留 Docker 环境一致性，又不会污染宿主机权限。

  前端页面出现错误：
  在showcase页面的"生活"类展示页面中，为什么会出现两个纯色块图片？且两个纯色块页面中出现文字"batch-v0 acceptance upload 20260512224721"，这个文字和这个色块是哪里来的？这个文字的含义是什么？

  同时，在在showcase页面的"摄影"类展示页面中，第一张图片也是纯色块。

  请你定位这些问题出现的原因。

  这些纯色块图片是你在构建代码时加入的测试数据吗？如果是的话，记得在每一个阶段任务完成后，都要清理这些纯色块的测试数据。

  问题 1/5 — AI Job 流水线架构
  
  当前 Worker 流水线是：photo_ingest（EXIF → 缩略图 → preview → fallback slide design）→ 可选 reverse_geocode。

  Phase 5 需要新增两个 job type：vision_analyze（Ollama）和 slide_design_generate（DeepSeek）。

  我看到的两种可行架构：

  A) 后处理替换模式：ingest 完成后始终先用 fallback design 让照片进入 ready，然后依次 enqueue vision_analyze → slide_design_generate。AI design 校验通过后替换 fallback
  design（新版本 active，旧 fallback 降为 draft）。AI 任何环节失败，照片仍保持 ready + fallback design 可用。

  B) 阻塞等待模式：ingest 完成后不立即生成 fallback，先等 AI 流水线跑完。如果 AI 失败再退回到 fallback。这会延迟照片进入 ready 状态。

  我推荐 方案 A，因为：
  - 照片立即可播放（Phase 2/3 的 ready 不变性原则）
  - 与 geocoding 的后处理模式一致（geocoding 失败不阻断 ready）
  - AI 耗时可能很长（你设了 500s 超时），不应阻塞用户播放

  你同意用方案 A 吗？为什么？哪种方案更好？还是都不好？为什么？

  问题 4/5 — DeepSeek Slide Design 生成的 Prompt 结构与校验链
  
  这是 Phase 5 最核心的环节。DeepSeek 需要接收的上下文包括：

  - 用户留言（photo.user_message，优先级最高）
  - EXIF 元数据（时间、相机、GPS）
  - 地点信息（来自 geocoding）
  - AI 视觉分析结果（来自 Ollama，ai_analysis_json）
  - 可用模板能力（3 个模板的 allowedLayerTypes、paramSchema、defaultStyleTokens）
  - CSS 变量白名单（--kf-* 前缀）
  - Layer type 枚举（shape/image/text/timeline/background/mask）
  - 布局约束（zIndex 0-100, rect 0-1, text ≤ 200 chars, fontSize ≤ 120px）

  输出要求：
  - 纯 JSON，format: "json" 或等效强制
  - 必须符合 slide_design.schema.json + 前端 validator 的全部规则
  - 不允许解释文字

  我有几个设计决策需要确认：

  A) Prompt 组装位置：建议新建 backend/app/services/ai/slide_design_prompt.py 存放 prompt 模板构建逻辑，独立于 DeepSeek API 调用代码。

  B) 校验链：DeepSeek 返回 JSON 后，建议的校验顺序是：
  1. JSON parse（失败 → 标记无效 JSON，可能重试）
  2. JSON Schema 校验（用 slide_design.schema.json 做 structural check）
  3. 语义校验（templateId 是否合法、layer 组合是否合理、至少有一张 image layer 等）
  4. 校验通过 → 事务内原子替换 active design

  C) "校验失败重试一次"的重试策略：你说"最多重试一次，然后 fallback"。这个重试是否应该带着修正提示（"上一次输出缺少 image
  layer，请添加"）还是原样重试？我建议带错误反馈重试，提高成功率。

  D) DeepSeek API 调用方式：用 httpx 直接调 REST API（https://api.deepseek.com/v1/chat/completions），和现有 Nominatim/Amap provider 风格一致，不引入额外 SDK。

  你对此有什么修改意见？

  全局行为准则：
  1. 任何新写的脚本/命令，写完必须实际执行一次，不依赖脑内模拟，用实际运行结果说话。
  2. 区分"单元测试通过"和"端到端验收通过"，不混用这两个概念
  3. 遇到错误时，先诊断根因再修改，不试错式修复