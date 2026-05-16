# KinFrame 内网穿透技术方案

## 一、推荐方案：Cloudflare Tunnel

**一句话**：在你的机器上跑一个 `cloudflared` 容器，Cloudflare 的全球边缘网络替你把流量从公网安全转发到本地，无需碰路由器、无需公网 IP。

### 技术架构

```
公网用户 ──HTTPS──▶ Cloudflare Edge ──QUIC长连接──▶ 你的机器(cloudflared)
                    (DDoS防护/WAF)                   │
                                                     ├─ Caddy :18080
                                                     ├─ Nuxt :3000
                                                     └─ FastAPI :18000
```

### 技术栈

| 组件 | 选型 | 用途 |
|------|------|------|
| 隧道 | `cloudflared` (Cloudflare Tunnel) | 出站 QUIC 长连接，穿透 NAT |
| 域名 | 任意 `.com`/`.top`/免费域名 | 绑定到 Cloudflare DNS |
| HTTPS | Cloudflare Edge 自动签发 | 公网侧 TLS 终结 |
| 防护 | Cloudflare WAF / Rate Limiting | 防扫描、防撞库 |
| 反代 | 现有 Caddy | 保持不变，处理内网侧路由 |

### 费用

| 项目 | 费用 |
|------|------|
| 域名 | `.top` 首年 ¥3，续费约 ¥30/年 |
| Cloudflare DNS + Tunnel | **完全免费** |
| Cloudflare WAF | **免费**（托管规则集 5 条额度，够用） |
| Cloudflare Rate Limiting | 免费套餐有基础速率限制规则 |

**总成本：首年约 ¥3，之后每年约 ¥30。**

---

## 二、基础设施改造评估

### 需要改的部分

#### 1. 新增一个 Docker 容器（改动量：小）

```yaml
# docker-compose.infra.yml 新增
cloudflared:
  image: cloudflare/cloudflared:latest
  command: tunnel run
  environment:
    - TUNNEL_TOKEN=${CF_TUNNEL_TOKEN}
  network_mode: host  # 与其他服务一致
  restart: unless-stopped
```

就是加一个容器，一行命令的事。

#### 2. Caddy 需要知道真实客户端 IP（改动量：小）

Cloudflare Tunnel 在 HTTP 头里传 `CF-Connecting-IP`。当前 Caddy 配置需要加信任代理：

```Caddyfile
# 原来
reverse_proxy backend:18000

# 改为
(tunnel_trust) {
    trusted_proxies 127.0.0.1 ::1
    # cloudflared 在本地，所以信任 localhost
}
```

改动不超过 5 行。

#### 3. 后端审计日志需要读取真实 IP（改动量：小）

当前 `backend/app/api/deps.py` 里记录 IP 的方式需要检查 `X-Forwarded-For` 头。FastAPI 如果配置好 `--proxy-headers`，会自动取最外层 IP。改一行启动参数即可。

### 不需要改的部分

| 模块 | 理由 |
|------|------|
| Nuxt 前端 | 完全不变，对外域名统一通过 Caddy/Caddyfile 路由 |
| FastAPI 路由 | 不变，API 路径不变 |
| 数据库/Redis/MinIO | 不变，内网内部通信 |
| 认证逻辑 | 不变，cookie 机制照常工作 |
| Docker 网络架构 | 不变，`--network host` 保持不变 |
| 照片处理 worker | 不变 |
| justfile 命令 | 几乎不变，最多加一个 `just tunnel-logs` |

**总结：基础设施不需要大改，主要是加一个容器 + 改几行配置。**

---

## 三、最困难的点（按难度排序）

### 困难 1：HTTPS -> 内网 HTTP 的安全断层

Cloudflare Edge 到用户是 HTTPS，但 cloudflared 到 Caddy 是本地 HTTP（localhost）。技术上讲，这段链路在你自己机器上，不会被窃听。**但如果你的机器被其他进程监听 18080 端口，它是明文的。**

这不是 Cloudflare Tunnel 的问题，是所有反向代理隧道方案的共性问题。严肃方案会在内网侧也加一层 TLS，但这需要自签证书 + Caddy 配 TLS，复杂度上一个台阶。

**建议的处理方式**：先用本地 HTTP，因为攻击者已经需要在你机器上跑进程才能嗅探，这个威胁模型对家庭照片库来说可以接受。

### 困难 2：Cookie 安全问题

当前 cookie 设置（推断的，需确认）：

```
Set-Cookie: kinframe_session=xxx; HttpOnly; SameSite=Lax; Path=/
```

暴露公网后需要加 `Secure` flag（只通过 HTTPS 发送）。但因为 Cloudflare Edge 做 TLS 终结，你的后端收到的请求是 HTTP（来自 cloudflared），所以后端不会自动设置 `Secure` flag。

**需要做**：后端判断 `X-Forwarded-Proto: https` 头来动态设置 `Secure`。FastAPI 的 session 中间件需要显式配置 `secure=True`。这是一个容易漏掉但后果严重的点 —— 如果漏了，cookie 可能在某些场景下通过 HTTP 明文传输。

### 困难 3：登录接口无保护

当前 `/api/auth/login` 没有速率限制。暴露公网后，最基础的攻击就是跑用户名/密码字典。Shodan 扫描到开放服务后，会在几分钟内开始撞。

Cloudflare 免费版有 Rate Limiting 规则（需手动配置），但更可靠的做法是**应用层也加一层**：

```python
# 需要实现或引入
@login_rate_limit(max_attempts=5, window_seconds=300)
```

这不是复杂代码，但需要测试、需要决定用 Redis 还是内存存储。Redis 更可靠但需要多写几行。

### 困难 4：MinIO 预签名 URL 的内网地址泄漏

当前架构中，照片预览 URL 是 MinIO 生成的预签名 URL，格式是 `http://localhost:19000/bucket/...`。这在浏览器端直接请求，内网没问题，但公网用户访问 `localhost:19000` 当然访问不到。

**需要改造**：

- 方案 A：MinIO 预签名 URL 使用公网可访问的域名（需要 MinIO 感知 Caddy 反代的外部地址）
- 方案 B：图片不走预签名直链，改为通过后端 API 流式代理（增加后端负载，但更安全 —— 可以做访问控制）
- 方案 C：Caddy 再加一个路由，把 `/minio/` 路径反向代理到 MinIO，预签名 URL 改为使用 Caddy 的公网地址

方案 A 和 C 改动小但需要仔细配置。方案 B 安全但性能开销大。

**这是整个穿透方案里最需要仔细设计的部分。**

### 困难 5：备份文件暴露风险

当前 `scripts/backup` 把 PostgreSQL dump 和 MinIO 全量数据写到 `data/backups/`。如果 Caddy 被错误配置或路径遍历漏洞，备份文件可能通过 Web 被下载。数据库 dump 里包含密码哈希和 session 信息。

**需要注意**：确保 Caddy 的 file_server 不暴露 `data/` 目录，或者在备份后加 `.htpasswd` 保护。

---

## 四、实施路线建议

### Phase 1：最小可用公网访问（2-3 小时）

1. 注册域名，绑定 Cloudflare DNS
2. 添加 `cloudflared` 容器
3. Caddy 改信任代理
4. Cookie 加 `Secure` flag
5. 登录接口加 Redis 速率限制（5 次/5分钟）

**目标**：能通过 `https://你的域名` 访问，基本防撞库。

### Phase 2：图片访问修复（1-2 小时）

6. 解决 MinIO 预签名 URL 的公网可达性（方案 A 或 C）
7. 验证所有页面的图片加载

### Phase 3：加固（1 小时）

8. Cloudflare WAF 规则（阻止已知恶意 IP 规则集）
9. 验证备份路径不可通过 Web 访问
10. 完整验收

---

**总工期估算：4-6 小时**，核心改造量不大，真正耗时间的是验证和测试，不是写代码。

最核心的风险点在 **困难 2**（Cookie Secure flag）和 **困难 4**（MinIO URL），这两个必须搞对。
