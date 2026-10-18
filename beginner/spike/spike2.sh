#!/bin/bash
# Spike 2: light theme; does Agent chat find claude-agent-acp, start Claude Code with only CLAUDE_CODE_OAUTH_TOKEN,
# and answer one read-only question through SolidCraft's tools?
set -u
OUT=/work/spike/out; C="python3 /work/spike/ctl.py"
export XDG_RUNTIME_DIR=/tmp/xdg; mkdir -p -m 700 $XDG_RUNTIME_DIR
Xvfb :99 -screen 0 1920x1080x24 >/dev/null 2>&1 & export DISPLAY=:99; sleep 2
solidcraft --control 7878 > $OUT/app2.log 2>&1 & sleep 15
$C ui.prefs '{"theme":"light"}' | head -c 300; echo
$C ui.agent_chat '{"open":true,"refresh":true}' > $OUT/chat-0.json; sleep 8
$C ui.agent_chat '{}' > $OUT/chat-1.json
python3 -c "import json;r=json.load(open('$OUT/chat-1.json'))['result'];print('state',r.get('state'),'agents',[(a.get('id'),a.get('name'),a.get('signedIn',a.get('signed_in'))) for a in r.get('agents',[])])"
$C ui.agent_chat '{"send":"What is in my design right now?"}' > /dev/null
for i in $(seq 1 30); do sleep 4; S=$($C ui.agent_chat '{}' | python3 -c "import json,sys;print(json.load(sys.stdin)['result'].get('state'))"); echo "t=$((i*4)) $S"; [ "$S" = ready ] && [ $i -gt 2 ] && break; done
$C ui.agent_chat '{}' > $OUT/chat-2.json
ffmpeg -loglevel error -y -f x11grab -video_size 1920x1080 -i :99 -frames:v 1 $OUT/window2.png
