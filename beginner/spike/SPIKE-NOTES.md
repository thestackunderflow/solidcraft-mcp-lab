# Beginner lab spike (18 Oct 2026, SolidCraft 0.15.0, claude-agent-acp 0.93.0)

## Spike 1: the desktop app under Xvfb: PASS
- `solidcraft --control 7878` opens a 1600x1000 window on a 1920x1080 Xvfb display; "SolidCraft graphics: Vulkan, MSAA 4x"
  (llvmpipe). Control server on 127.0.0.1:7878, token file written. `out/window.png`.
- It warns that XDG_RUNTIME_DIR is not set; setting it to a 0700 folder silences that.
- To do: match the window and display sizes (1600x1000 window, or resize it with xdotool) so the recording has no black border.

## Spike 2: Agent chat with Claude Code, token only: PASS (one cosmetic gap)
- `ui.prefs {"theme":"light"}` switches to the light theme, so the white-visuals rule holds.
- Detection found `claude-agent-acp` 0.93.0 on PATH. `login: signed_out` and "Not logged in" show in the panel even though
  `CLAUDE_CODE_OAUTH_TOKEN` worked: SolidCraft only looks for the credentials file (as the docs say).
  On a real sign-in (Windows recording) this should read as signed in. Don't film the Docker panel header as proof of sign-in.
- `ui.agent_chat {"send": "What is in my design right now?"}`: busy, then ready in about 8 s. Cards:
  `ToolSearch` (Claude Code loading deferred tools), then `mcp__solidcraft__inspect_design` with its JSON reply (empty design).
  Notice: "Auto-allowed: mcp__solidcraft__inspect_design (SolidCraft checks its own tools itself)". Answer: "Your design is empty…".
- **The MCP name is on screen in the product**: `mcp__solidcraft__inspect_design` is the card title. This is the chapter-2 shot.
- `ui.agent_chat {}` returns the whole conversation (`items`: user, tool cards with output, notices, agent text), so the
  session log can be read from the app itself, without a proxy, as a first evidence layer.
- Evidence: `out/chat-2.json`, `out/window2.png`, `out/app2.log`. Cost: one short Claude turn.

## Next
- Spike 3: the ACP tee shim (exact JSON-RPC both ways) and capturing the MCP server launch from `session/new`.
- Spike 4: the phone-stand prompt and the 24-changes limit; `parameters.change` over the control channel for the slip.
