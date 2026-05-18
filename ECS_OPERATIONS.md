# KinFrame ECS Remote Operations

这份文档整理了当前 KinFrame 在阿里云 ECS 上的常用远程运维命令。

当前约定：

- ECS 公网 IP：`47.99.132.33`
- SSH 用户：`root`
- 本地私钥：`/mnt/data_nvme/code/KinFrame/KinFrame.pem`
- 远端项目目录：`/srv/kinframe`

注意：

- `rsync` 只会同步源码，不会自动更新正在运行的容器。
- 如果你改了代码，要让修改生效，必须重新构建镜像、上传镜像，并重启远端应用容器。

## 1. 登录服务器

```bash
rtk bash -lc 'tmpkey=$(mktemp /tmp/kinframe-ecs-key-XXXXXX.pem); cp /mnt/data_nvme/code/KinFrame/KinFrame.pem "$tmpkey"; chmod 600 "$tmpkey"; ssh -i "$tmpkey" -o StrictHostKeyChecking=accept-new root@47.99.132.33; rm -f "$tmpkey"'
```

## 2. 启动服务器上已有的前后端与基础设施容器

适用场景：

- 服务器重启后
- 你只是想把现有容器重新拉起来
- 不涉及代码更新

```bash
rtk bash -lc 'tmpkey=$(mktemp /tmp/kinframe-ecs-key-XXXXXX.pem); cp /mnt/data_nvme/code/KinFrame/KinFrame.pem "$tmpkey"; chmod 600 "$tmpkey"; ssh -i "$tmpkey" -o StrictHostKeyChecking=accept-new root@47.99.132.33 "for c in kinframe-postgres kinframe-redis kinframe-minio kinframe-backend kinframe-worker kinframe-frontend kinframe-caddy; do docker start \"\$c\" >/dev/null 2>&1 || true; done; docker ps -a --format \"table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Ports}}\""; rm -f "$tmpkey"'
```

## 3. 同步本地代码到远程服务器

```bash
rtk bash -lc 'tmpkey=$(mktemp /tmp/kinframe-ecs-key-XXXXXX.pem); cp /mnt/data_nvme/code/KinFrame/KinFrame.pem "$tmpkey"; chmod 600 "$tmpkey"; rsync -avz --delete -e "ssh -i $tmpkey -o StrictHostKeyChecking=accept-new" --exclude ".git" --exclude ".env" --exclude "data" --exclude "backend/.venv" --exclude "frontend/node_modules" --exclude "frontend/.nuxt" --exclude "frontend/.output" --exclude "KinFrame.pem" /mnt/data_nvme/code/KinFrame/ root@47.99.132.33:/srv/kinframe/; rm -f "$tmpkey"'
```

## 4. 同步代码后，让修改真正生效

### 4.1 本地重新构建镜像

```bash
rtk docker build -t kinframe-backend-env:stage5 ./backend
```

```bash
rtk docker build -t kinframe-frontend-env:stage5 ./frontend
```

### 4.2 把本地镜像传到 ECS

```bash
rtk bash -lc 'tmpkey=$(mktemp /tmp/kinframe-ecs-key-XXXXXX.pem); cp /mnt/data_nvme/code/KinFrame/KinFrame.pem "$tmpkey"; chmod 600 "$tmpkey"; rtk docker save kinframe-backend-env:stage5 kinframe-frontend-env:stage5 | gzip -1 | ssh -i "$tmpkey" -o StrictHostKeyChecking=accept-new root@47.99.132.33 "gunzip | docker load"; rm -f "$tmpkey"'
```

### 4.3 重建并重启远程应用容器

```bash
rtk bash -lc 'tmpkey=$(mktemp /tmp/kinframe-ecs-key-XXXXXX.pem); cp /mnt/data_nvme/code/KinFrame/KinFrame.pem "$tmpkey"; chmod 600 "$tmpkey"; ssh -i "$tmpkey" -o StrictHostKeyChecking=accept-new root@47.99.132.33 "docker rm -f kinframe-backend kinframe-worker kinframe-frontend kinframe-caddy >/dev/null 2>&1 || true; docker run -d --name kinframe-backend --restart unless-stopped --network host --env-file /srv/kinframe/.env kinframe-backend-env:stage5 bash -lc \"cd /app && uv run alembic upgrade head && exec uv run uvicorn app.main:app --host 0.0.0.0 --port 18000\"; docker run -d --name kinframe-worker --restart unless-stopped --network host --env-file /srv/kinframe/.env kinframe-backend-env:stage5 bash -lc \"cd /app && uv run alembic upgrade head && exec uv run python -m app.workers.photo_processor --poll-interval 2\"; docker run -d --name kinframe-frontend --restart unless-stopped --network host --env-file /srv/kinframe/.env -e HOST=0.0.0.0 -e PORT=3000 -e NITRO_HOST=0.0.0.0 -e NITRO_PORT=3000 -e NODE_ENV=production kinframe-frontend-env:stage5 bash -lc \"cd /app && pnpm build && exec node .output/server/index.mjs\"; docker run -d --name kinframe-caddy --restart unless-stopped --network host -v /srv/kinframe/deploy/caddy/Caddyfile:/etc/caddy/Caddyfile:ro -v /srv/kinframe/data/caddy:/data caddy:latest; docker ps -a --format \"table {{.Names}}\t{{.Status}}\t{{.Image}}\""; rm -f "$tmpkey"'
```

## 5. 查看日志

### 查看全部容器状态

```bash
rtk bash -lc 'tmpkey=$(mktemp /tmp/kinframe-ecs-key-XXXXXX.pem); cp /mnt/data_nvme/code/KinFrame/KinFrame.pem "$tmpkey"; chmod 600 "$tmpkey"; ssh -i "$tmpkey" -o StrictHostKeyChecking=accept-new root@47.99.132.33 "docker ps -a --format \"table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Ports}}\""; rm -f "$tmpkey"'
```

### 查看 backend 日志

```bash
rtk bash -lc 'tmpkey=$(mktemp /tmp/kinframe-ecs-key-XXXXXX.pem); cp /mnt/data_nvme/code/KinFrame/KinFrame.pem "$tmpkey"; chmod 600 "$tmpkey"; ssh -i "$tmpkey" -o StrictHostKeyChecking=accept-new root@47.99.132.33 "docker logs --tail 200 -f kinframe-backend"; rm -f "$tmpkey"'
```

### 查看 frontend 日志

```bash
rtk bash -lc 'tmpkey=$(mktemp /tmp/kinframe-ecs-key-XXXXXX.pem); cp /mnt/data_nvme/code/KinFrame/KinFrame.pem "$tmpkey"; chmod 600 "$tmpkey"; ssh -i "$tmpkey" -o StrictHostKeyChecking=accept-new root@47.99.132.33 "docker logs --tail 200 -f kinframe-frontend"; rm -f "$tmpkey"'
```

### 查看 worker 日志

```bash
rtk bash -lc 'tmpkey=$(mktemp /tmp/kinframe-ecs-key-XXXXXX.pem); cp /mnt/data_nvme/code/KinFrame/KinFrame.pem "$tmpkey"; chmod 600 "$tmpkey"; ssh -i "$tmpkey" -o StrictHostKeyChecking=accept-new root@47.99.132.33 "docker logs --tail 200 -f kinframe-worker"; rm -f "$tmpkey"'
```

### 查看 caddy 日志

```bash
rtk bash -lc 'tmpkey=$(mktemp /tmp/kinframe-ecs-key-XXXXXX.pem); cp /mnt/data_nvme/code/KinFrame/KinFrame.pem "$tmpkey"; chmod 600 "$tmpkey"; ssh -i "$tmpkey" -o StrictHostKeyChecking=accept-new root@47.99.132.33 "docker logs --tail 200 -f kinframe-caddy"; rm -f "$tmpkey"'
```

## 6. 查看健康状态

```bash
rtk bash -lc 'tmpkey=$(mktemp /tmp/kinframe-ecs-key-XXXXXX.pem); cp /mnt/data_nvme/code/KinFrame/KinFrame.pem "$tmpkey"; chmod 600 "$tmpkey"; ssh -i "$tmpkey" -o StrictHostKeyChecking=accept-new root@47.99.132.33 "curl -fsS http://127.0.0.1:18000/api/health && echo && curl -I --max-time 10 http://127.0.0.1/"; rm -f "$tmpkey"'
```

## 7. 建议的日常操作顺序

如果你改了代码，建议按这个顺序操作：

1. 同步代码到 ECS
2. 本地重新构建镜像
3. 把镜像传到 ECS
4. 重启远程应用容器
5. 查看日志与健康检查

也就是依次执行：

- 第 3 节
- 第 4.1 节
- 第 4.2 节
- 第 4.3 节
- 第 5 节 / 第 6 节
