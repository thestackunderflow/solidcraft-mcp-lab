# Beginner lab: the logged sessions (18 Oct 2026)

SolidCraft 0.15.0 desktop app (Xvfb, light theme) · Agent chat · claude-agent-acp 0.93.0 (default model claude-sonnet-5-5)
· the ACP tee (`shim/acp_tee.py`) + MCP logging proxy on the MCP server that SolidCraft hands Claude Code.
Each run is a fresh container (fresh home folder: no CLAUDE.md, memory or skills). Lab steps (the Undo button, the slip,
File > Save, pressing Allow) are sent by the driver (`session/session.py`) and logged as such in `timeline.jsonl`.

| Run | Cost | Outcome |
|---|---|---|
| spike-4 | $0.30 | question, cube, Undo button, stand: built; `phone_thickness` named but NOT connected (Claude said so) |
| run-a | $0.62 | full story up to the export; the driver moved on too early (fixed: wait on the ACP log); the export turn answered "unsaved" without a tool call, and no Allow card came |
| run-b | $0.13 | Claude tried to undo its cube itself (an undo from before the message: SolidCraft asked); the driver left the card and queued the next messages; Claude stopped: "the design isn't in the state I left it" (fixed: unexpected cards are denied) |
| **run-c** | **$0.67** | **complete: the video's session** |

Total spent: about $1.72 (budget $6).

## run-c, the video's session (out/run-c: screen.mp4, acp.jsonl, mcp.jsonl, timeline.jsonl, chat-final.json, designs/)
1. "What's in my design right now?" → `inspect_design` → empty.
2. "Make a 40 mm cube." → `batch` (a Box feature) + `measure`: 64,000 mm³. Then the **Undo these changes** button (lab step).
3. Phone stand → 20 MCP tool calls (seq 20–58 in mcp.jsonl: list_commands ×6, batch ×9 of which 3 failed and rolled back, measure ×2, body_topology, inspect_design, screenshot), about 1 min 40 s: 80 × 60 × 30 mm,
   a 13 mm slot at 70°, named sizes incl. `phone_thickness` 12 + `slot_clearance` 1. The panel counted **26 changes** for this
   message, above the documented 24-per-message default; not explained yet (does a batch in flight finish?). Don't claim "24" in the video unverified.
4. "Connect phone_thickness…" → already connected; it tested 12 → 14 → 12 and measured 13.000 / 15.000 / 13.000 mm.
   At 14 mm the 3 mm fillet failed ("largest radius that fits is 2.87 mm"); it said so and restored 12.
5. **The slip (lab step: phone_thickness = 6 mm, `recomputed: 3`).** "Check the slot… use measure" → found
   "`phone_thickness` was 6 mm, not 12. Something outside my edits had changed it. The slot was only 7 mm wide", fixed it,
   and found a second real problem (the floor under the slot was about 3.5 mm, not 8) and re-anchored it. Walls 13.000 mm apart.
6. "My new phone is 9 mm" → `batch` (parameters.change) → slot 10 mm; it said it read the width from the sketch dimension
   and "didn't measure the faces this time".
7. File > Save (lab step) → "Export the stand as an STL…" → it answered **without checking** that the design was unsaved
   (only a ToolSearch call) → follow-up "I saved the design…" → `inspect_design` → `export` → SolidCraft's approval card
   "file.export: /root/designs/exports/PhoneStand.stl" → Allow (lab step) → 227,484-byte binary STL: 4,548 triangles, every edge shared by exactly two (closed; out/run-c/stl-check.json).

## Findings that repeat across runs (one model, three runs: say "in our runs", not "always")
- **The cube:** after the Undo button removed the cube, Claude said in the stand message that "a failed batch step rolled it
  back" (spike-4, run-a, run-c). The panel shows the cube's changes as "(undone)" before the stand prompt was sent (spike-4: 3 changes; run-c: 1, a Box feature).
  In run-b it tried to undo the cube itself. The agent isn't told about the user's Undo button press.
- **Saved or not:** asked to export right after File > Save, it said the design was unsaved without calling a tool (run-a, run-c).
- **Named ≠ connected:** spike-4 left `phone_thickness` unconnected and said so; run-a and run-c connected it.
  Lab test b4: a named size that drives nothing replies `recomputed: 0` and changes nothing.
- Every SolidCraft tool call shows in the panel as a card titled `mcp__solidcraft__<tool>`; "Auto-allowed … (SolidCraft checks its
  own tools itself)" under each. `session/new` shows SolidCraft starting `solidcraft-cli mcp --connect 127.0.0.1:<port>` and
  disallowing Claude Code's Bash, Read, Write, Edit, MultiEdit, NotebookEdit, Glob, Grep, WebFetch, WebSearch, Task, BashOutput, KillShell.
- "Not logged in" shows in the panel with only CLAUDE_CODE_OAUTH_TOKEN (it works anyway): film sign-in on Windows.
