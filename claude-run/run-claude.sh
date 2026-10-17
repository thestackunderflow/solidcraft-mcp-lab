#!/usr/bin/env bash
# One logged, headless Claude Code run against the lab's SolidCraft MCP server.
# Host needs only `docker` and `claude`; the proxy and the server run in the lab container.
#   Claude Code --stdio--> docker run -i ... [mcp_log_proxy.py --stdio--> solidcraft-cli mcp --allow-path /lab/out]
set -euo pipefail
cd "$(dirname "$0")/.."
LAB="$(pwd -W 2>/dev/null || pwd)"          # C:/... on Git Bash, /... elsewhere
OUT=tests/out/claude-run
mkdir -p "$OUT"
rm -f "$OUT/transcript.jsonl"

cat > claude-run/mcp-config.json <<JSON
{
  "mcpServers": {
    "solidcraft": {
      "command": "docker",
      "args": ["run", "-i", "--rm",
               "-v", "$LAB/proxy:/proxy:ro",
               "-v", "$LAB/$OUT:/lab/out",
               "solidcraft-mcp-lab:0.14.0",
               "python3", "/proxy/mcp_log_proxy.py", "--log", "/lab/out/transcript.jsonl", "--png-dir", "/lab/out",
               "--", "solidcraft-cli", "mcp", "--allow-path", "/lab/out"]
    }
  }
}
JSON

PROMPT='Use the solidcraft MCP tools to build a simple electronics enclosure: parameters width 80 mm, depth 60 mm, height 30 mm, wall 2 mm, with the sketch dimensions tied to those parameters; round the four vertical edges, then shell it open at the top. Measure it and report the bounding box. Then change width to 100 mm, measure again, and report which features were recomputed. Export a STEP file to /lab/out/claude-enclosure.step. Report any step that failed.'

# Only the solidcraft tools: no built-in tools (--tools ""), no other MCP servers, nothing else allowed.
# This CLI (2.1.302) has no --max-turns; cost is capped with --max-budget-usd and time with timeout.
CLAUDE="${CLAUDE:-claude}"
MSYS_NO_PATHCONV=1 timeout 600 "$CLAUDE" -p "$PROMPT" \
  --mcp-config claude-run/mcp-config.json --strict-mcp-config \
  --tools "" --allowedTools "mcp__solidcraft__*" --permission-mode dontAsk \
  --max-budget-usd 4 --no-session-persistence \
  --output-format json < /dev/null > "$OUT/claude-output.json"
echo "exit $?"
