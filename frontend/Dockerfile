FROM node:22-slim

ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0 \
    COREPACK_NPM_REGISTRY=https://registry.npmmirror.com \
    NPM_CONFIG_REGISTRY=https://registry.npmmirror.com \
    npm_config_registry=https://registry.npmmirror.com \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

RUN sed -i \
        -e 's|http://deb.debian.org/debian-security|http://mirrors.aliyun.com/debian-security|g' \
        -e 's|http://deb.debian.org/debian|http://mirrors.aliyun.com/debian|g' \
        /etc/apt/sources.list.d/debian.sources

RUN apt-get update -o Acquire::Retries=3 -o Acquire::ForceIPv4=true \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        curl \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY package.json pnpm-lock.yaml ./
RUN corepack enable \
    && corepack prepare pnpm@9.15.4 --activate \
    && pnpm config set registry https://registry.npmmirror.com \
    && pnpm install --frozen-lockfile

COPY . .

CMD ["pnpm", "--version"]
