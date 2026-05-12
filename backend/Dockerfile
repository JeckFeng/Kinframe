FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    UV_LINK_MODE=copy \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

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
        libheif1 \
        libimage-exiftool-perl \
        libjpeg62-turbo \
        libpng16-16 \
        libwebp7 \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --default-index https://pypi.tuna.tsinghua.edu.cn/simple

COPY . .

CMD ["uv", "run", "python", "--version"]
