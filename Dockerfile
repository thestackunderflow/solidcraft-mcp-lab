# SolidCraft v0.14.0 MCP lab: the pinned Linux release asset, checked against the release's
# SHA256SUMS.txt. No Rust compile. Lab snapshot 16-17 Oct 2026.
FROM ubuntu:24.04
ARG SC_ASSET=solidcraft-0.14.0-linux-x86_64.tar.gz
ARG SC_BASE=https://github.com/tangency-labs/solidcraft/releases/download/v0.14.0
ENV DEBIAN_FRONTEND=noninteractive
# mesa-vulkan-drivers + libvulkan1: llvmpipe, a software Vulkan device, so headless screenshots use
# the viewport's own pipelines ("gpu-software"). Without them SolidCraft falls back to its CPU
# rasterizer ("cpu", no analysis colours). The binary itself needs only glibc (ldd: libc, libm, libgcc_s).
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl \
      mesa-vulkan-drivers libvulkan1 python3 python3-pytest \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /tmp/dl
RUN curl -fsSLO "$SC_BASE/$SC_ASSET" \
 && curl -fsSLO "$SC_BASE/SHA256SUMS.txt" \
 && grep " $SC_ASSET\$" SHA256SUMS.txt > check.txt \
 && test "$(wc -l < check.txt)" = 1 \
 && sha256sum -c check.txt \
 && mkdir -p /opt/solidcraft \
 && tar -xzf "$SC_ASSET" -C /opt/solidcraft --strip-components=1 \
 && cp SHA256SUMS.txt check.txt /opt/solidcraft/ \
 && cd / && rm -rf /tmp/dl
ENV PATH=/opt/solidcraft/bin:$PATH
# /lab/out: the one folder the agent may write to (--allow-path). /lab/forbidden: must stay empty.
RUN mkdir -p /lab/out /lab/forbidden
WORKDIR /work
