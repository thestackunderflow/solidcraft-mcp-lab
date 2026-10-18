#!/bin/bash
# One recorded Agent chat session, inside the beginner image. Host side:
#   docker run --rm --shm-size 1g --env-file .env -v "$PWD:/work" -e RUN_DIR=run-x -e STEPS=session/steps-x.json \
#     solidcraft-beginner:0.1 bash /work/session/run-session.sh
# Writes /work/out/$RUN_DIR: screen.mp4, acp.jsonl (every ACP message), mcp.jsonl (every MCP message),
# timeline.jsonl, chat-final.json, app.log, design files. Refuses an existing RUN_DIR (runs are never overwritten).
set -u
: "${RUN_DIR:?set RUN_DIR}" "${STEPS:?set STEPS}"
OUT=/work/out/$RUN_DIR
[ -e "$OUT" ] && { echo "refusing: $OUT exists"; exit 1; }
mkdir -p "$OUT/png" /root/designs/exports
mkdir -p /opt/shim && cp /work/shim/acp_tee.py /opt/shim/claude-agent-acp && chmod +x /opt/shim/claude-agent-acp
export PATH=/opt/shim:$PATH ACP_LOG=$OUT/acp.jsonl
export MCP_PROXY="[\"python3\", \"/work/proxy/mcp_log_proxy.py\", \"--log\", \"$OUT/mcp.jsonl\", \"--png-dir\", \"$OUT/png\", \"--\"]"
export XDG_RUNTIME_DIR=/tmp/xdg; mkdir -p -m 700 $XDG_RUNTIME_DIR
Xvfb :99 -screen 0 1600x1000x24 >/dev/null 2>&1 & export DISPLAY=:99; sleep 2
solidcraft --control 7878 > "$OUT/app.log" 2>&1 & sleep 15
C="python3 /work/spike/ctl.py"
$C ui.prefs '{"theme":"light"}' >/dev/null
$C ui.agent_chat '{"open":true,"refresh":true}' >/dev/null; sleep 6
xdotool mousemove 1595 995; sleep 1
ffmpeg -loglevel error -y -f x11grab -framerate 15 -video_size 1600x1000 -i :99 -c:v libx264 -preset veryfast -pix_fmt yuv420p "$OUT/screen.mp4" &
REC=$!; sleep 2
python3 /work/session/session.py "/work/$STEPS" "$OUT"
sleep 3; kill -INT $REC; wait $REC 2>/dev/null
cp -r /root/designs "$OUT/designs" 2>/dev/null
python3 - "$OUT" <<'EOF'
import json, sys
cost = 0
for l in open(sys.argv[1] + '/acp.jsonl'):
    u = json.loads(l)['msg'].get('params', {}).get('update', {})
    if u.get("sessionUpdate") == "usage_update" and "cost" in u: print("  cost update:", u["cost"]["amount"]); cost = u["cost"]["amount"]
print(f'last cost value: ${cost:.3f}')
EOF
