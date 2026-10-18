# SolidCraft 0.15.0 beginner lab: the desktop app with its window on a virtual display (Xvfb, software
# Vulkan), Agent chat's Claude Code adapter, and ffmpeg to record the screen. Lab snapshot 18 Oct 2026.
FROM node:22-bookworm-slim
ARG SC_ASSET=solidcraft-0.15.0-linux-x86_64.tar.gz
ARG SC_BASE=https://github.com/tangency-labs/solidcraft/releases/download/v0.15.0
ENV DEBIAN_FRONTEND=noninteractive
# mesa-vulkan-drivers + libvulkan1: llvmpipe (the 0.14 lab picked it headless). The rest: the window (X11 via
# winit), the virtual display, the recorder and a fake click/keyboard (xdotool) for labelled lab steps.
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl \
      mesa-vulkan-drivers libvulkan1 libgl1 libegl1 \
      xvfb xauth x11-utils xdotool ffmpeg \
      libx11-6 libx11-xcb1 libxcursor1 libxrandr2 libxi6 libxkbcommon0 libxkbcommon-x11-0 libxcb1 \
      libwayland-client0 libdbus-1-3 libfontconfig1 fonts-dejavu-core \
      python3 python3-pytest \
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
# The ACP adapter Agent chat finds for Claude Code (docs/agent-chat.md); it bundles the Claude Agent SDK.
RUN npm install -g @agentclientprotocol/claude-agent-acp@0.93.0 && claude-agent-acp --version
WORKDIR /work
