# Beginner lab: SolidCraft's Agent chat, recorded and logged

**Lab snapshot: 18 Oct 2026. SolidCraft v0.15.0** (`solidcraft-0.15.0-linux-x86_64.tar.gz`, checked against the
release's `SHA256SUMS.txt`), Agent chat with Claude Code through `@agentclientprotocol/claude-agent-acp` 0.93.0
(default model in our runs: claude-sonnet-5-5).

This folder is the evidence behind the beginner video. SolidCraft's real desktop window runs in Docker on a virtual
display (Xvfb, software Vulkan), ffmpeg records that display, and two loggers record every message:
- `shim/acp_tee.py`: between SolidCraft and the Claude Code adapter (ACP: prompts, replies, tool cards, approvals);
- `proxy/mcp_log_proxy.py`: between Claude Code and SolidCraft's MCP server (every tool call and its exact reply).

The video was recorded on Linux in Docker; on Windows or macOS the app and its Agent chat panel look the same.
What happened in each run, and the findings that repeat, are in `RUNS.md`.

## What's in it

| Path | What it is |
|---|---|
| `Dockerfile` | `node:22-bookworm-slim` + the pinned release (SHA-256 checked) + Xvfb, llvmpipe, ffmpeg, xdotool + the ACP adapter 0.93.0. |
| `spike/ctl.py` | A client for SolidCraft's control channel (`solidcraft --control 7878`, JSON lines, token from `~/.local/share/solidcraft/control/`). The driver uses it to type messages into Agent chat and to press the buttons a viewer would press. |
| `shim/acp_tee.py` | Placed first on `PATH` as `claude-agent-acp`: logs the ACP traffic and routes the MCP server SolidCraft hands Claude Code through the logging proxy. |
| `session/session.py` | The driver: reads a steps file (`session/steps-run-*.json`), waits for each Claude turn to finish in the ACP log, and logs every lab step (Undo button, our 6 mm slip, File > Save, Allow) to `timeline.jsonl`. |
| `session/run-session.sh` | One recorded session inside the image. |
| `tests/` | 15 tests: the shim (3), the driver (4) and 8 app tests that drive the bridged MCP server with no AI in the loop (`test_beginner.py`, replies saved in `tests/out/`). |
| `out/run-c/` | **The video's session**: `screen.mp4`, `acp.jsonl`, `mcp.jsonl`, `timeline.jsonl`, `chat-final.json`, the design and the exported STL, `stl-check.json`. `spike-4`, `run-a`, `run-b` are the earlier runs. |
| `video/` | The frames the video shows (cut from `out/run-c/screen.mp4`) and the sped-up opening. |

## Run it

Everything runs in Docker; nothing is installed on the host. From this folder:

```bash
docker build -t solidcraft-beginner:0.1 .
docker run --rm --shm-size 1g -v "$PWD:/work" solidcraft-beginner:0.1 bash /work/tests/run-tests.sh   # 15 tests, no AI, free
```

A recorded session uses Claude (run-c cost about $0.67 at API prices). Put `CLAUDE_CODE_OAUTH_TOKEN=...` (from
`claude setup-token`) in a `.env` file here (git-ignored), pick a new run name, then:

```bash
docker run --rm --shm-size 1g --env-file .env -v "$PWD:/work" -e RUN_DIR=run-x -e STEPS=session/steps-run-c.json \
  solidcraft-beginner:0.1 bash /work/session/run-session.sh
```

The script refuses an existing run folder, so earlier runs are never overwritten. AI answers vary from run to run:
compare yours with `out/run-c/`, don't expect the same words.
