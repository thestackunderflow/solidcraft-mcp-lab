#!/bin/bash
# Spike 3: the ACP tee shim ahead of the real adapter; one read-only question; what does the log hold?
set -u
OUT=/work/spike/out; C="python3 /work/spike/ctl.py"
mkdir -p /opt/shim && cp /work/shim/acp_tee.py /opt/shim/claude-agent-acp && chmod +x /opt/shim/claude-agent-acp
export PATH=/opt/shim:$PATH ACP_LOG=$OUT/acp3.jsonl; rm -f $ACP_LOG
export XDG_RUNTIME_DIR=/tmp/xdg; mkdir -p -m 700 $XDG_RUNTIME_DIR
Xvfb :99 -screen 0 1600x1000x24 >/dev/null 2>&1 & export DISPLAY=:99; sleep 2
solidcraft --control 7878 > $OUT/app3.log 2>&1 & sleep 15
$C ui.prefs '{"theme":"light"}' >/dev/null
$C ui.agent_chat '{"open":true,"refresh":true}' >/dev/null; sleep 8
$C ui.agent_chat '{}' | python3 -c "import json,sys;print(json.load(sys.stdin)['result']['detection']['found'])"
$C ui.agent_chat '{"send":"What is in my design right now?"}' > /dev/null
for i in $(seq 1 30); do sleep 4; S=$($C ui.agent_chat '{}' | python3 -c "import json,sys;print(json.load(sys.stdin)['result'].get('state'))"); [ "$S" = ready ] && [ $i -gt 2 ] && break; done
$C ui.agent_chat '{}' > $OUT/chat-3.json
ffmpeg -loglevel error -y -f x11grab -video_size 1600x1000 -i :99 -frames:v 1 $OUT/window3.png
wc -l $ACP_LOG
