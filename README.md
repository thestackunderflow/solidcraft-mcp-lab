# What SolidCraft's MCP server really does: a test-first lab

**Lab snapshot: 16–17 Oct 2026. SolidCraft v0.14.0** (`solidcraft-0.14.0-linux-x86_64.tar.gz`, checked against the
release's `SHA256SUMS.txt`), Ubuntu 24.04, MCP over stdio (the server negotiates protocol `2025-06-18`).
SolidCraft is a young project that releases almost daily: every number here was measured in v0.14.0.

[SolidCraft](https://github.com/tangency-labs/solidcraft) is open-source parametric CAD. Its MCP server lets an AI
agent drive the same engine commands as the toolbar. This lab proves, with tests, what that means in practice: an
agent builds an electronics enclosure from parameters, a failing step rolls the whole batch back, changing one
parameter rebuilds the part, files can only be written where you allow, and the server can show the part without a GPU.
Then one real, logged Claude Code run does the same job from an English request.

## What's in it

| Path | What it is |
|---|---|
| `Dockerfile` | `ubuntu:24.04` + the pinned release asset (SHA-256 checked, no Rust compile) + `mesa-vulkan-drivers` (llvmpipe, a software Vulkan device for screenshots) + Python 3 / pytest. The binary itself needs only glibc. |
| `compose.yaml` | `tests`: runs the 8 tests. `server`: the bare MCP server on stdin/stdout. |
| `tests/mcp_client.py` | A ~150-line MCP client: starts `solidcraft-cli mcp --allow-path /lab/out` as a child process and speaks JSON-RPC 2.0, one message per line, over its stdin/stdout. No SDK. |
| `tests/test_lab.py` | Tests 0–7, one shared server session, run in order like one agent session. |
| `tests/enclosure_steps.json` | The project's own demo (`examples/demo/enclosure_steps.json` at v0.14.0, MIT OR Apache-2.0), unchanged. |
| `tests/out/` | Every reply, saved by the tests (`NN_*.json`), the PNGs, the exported files (`lab-out/`), the red and green runs (`red-phase.log`, `green-phase.log`). Committed: the video quotes these files, never memory. |
| `proxy/mcp_log_proxy.py` | A stdio logging proxy: forwards every byte unchanged and writes every JSON-RPC line, both ways, with a timestamp, to a JSONL file. |
| `claude-run/` | `run-claude.sh` (the headless Claude Code run), `summarize.py`, the generated `mcp-config.json`. Results in `tests/out/claude-run/`. |

Folders inside the container: `/lab/out` is the one folder the agent may use (`--allow-path /lab/out`, mounted to
`tests/out/lab-out/`); `/lab/forbidden` is an empty folder that must stay empty.

## Run it

Everything runs in Docker; nothing is installed on the host.

```bash
docker compose build
docker compose run --rm tests                       # the 8 tests; writes tests/out/
bash claude-run/run-claude.sh                       # optional: one real Claude Code run (needs `claude` logged in; costs ~$0.20)
docker run --rm -v "$PWD:/work" -w /work solidcraft-mcp-lab:0.14.0 python3 claude-run/summarize.py
```

To use the lab's server from any MCP client: `docker compose run --rm -T server` speaks MCP on stdin/stdout.

## The tests

Written first and run red (`tests/out/red-phase.log`: 8 errors, the client was a stub), then green
(`tests/out/green-phase.log`: **8 passed**).

0. `solidcraft-cli --version` is `solidcraft-cli 0.14.0`; `initialize` reports server `0.14.0`; `solidcraft-cli gpu` (renderer info) saved.
1. `tools/list` contains the 15 documented tools (checked as a subset, not a count); the read-only ones carry `readOnlyHint: true`, the six that can touch files carry `destructiveHint: true`.
2. **One `batch`** builds the enclosure from the project's demo: parameters `width/depth/height/wall` = 80/60/30/2 mm, sketch on XY, centre rectangle, the two sketch dimensions bound to `width` and `depth`, extrude by `height`, fillet the four vertical edges (6 mm), shell open at the top with thickness `wall`. Measured size 80 × 60 × 30 mm; volume equals the analytic value within 0.1 %.
3. **A batch whose step 4 fails** (a USB-port sketch, then a 25 mm fillet on the 2 mm wall): `ok: false`, `failed.index` 3, `failed.command` `solid.fillet`, `failed.error` text, `rolled_back: true`; volume, size, timeline, undo depth and parameters identical before and after.
4. `set_parameter width "100 mm"`: `errors` empty, features rebuilt, size X 80 → 100, Y and Z unchanged, volume equals the analytic value.
5. `export` STEP and STL into `/lab/out` works; to `/lab/forbidden` and to `/lab/out/../forbidden` it is refused with "outside the folders this agent may use"; `/lab/forbidden` stays empty. The exported STEP, re-read by a separate `solidcraft-cli eval`, is 100 × 60 × 30 with no parameters and no history.
6. `undo` brings width back to 80 (size 80 × 60 × 30).
7. `screenshot` returns a PNG and the renderer it used (`gpu-software`).

PNGs (960 × 600, the server's default size): `tests/out/02_iso_after_build.png`, `03_iso_after_failed_batch.png`,
`04_iso_after_width_100.png`, `07_top_after_undo.png`.

## Findings (16–17 Oct 2026, v0.14.0; exact values in `tests/out/`)

**Version and renderer** (`00_version_renderer.json`). `solidcraft-cli 0.14.0`; server `{"name": "solidcraft", "title":
"SolidCraft", "version": "0.14.0"}`. No GPU in the container: with `mesa-vulkan-drivers` the server renders on
llvmpipe (`llvmpipe (LLVM 20.1.2, 256 bits)`, Mesa 25.2.8, Vulkan) and reports **`renderer: "gpu-software"`**. Without
those packages (first try of the image) it falls back to its own CPU rasterizer, `renderer: "cpu"`, with the warning
"drawn by the CPU rasterizer (no GPU adapter qualified, or SOLIDCRAFT_GPU=cpu): surface analysis colours, highlights
and legends are not drawn". So the video's "works without a GPU" is true either way.

**Tools** (`01_tools_list.json`). Exactly the 15 documented tools: `list_commands, execute, batch, inspect_design,
measure, body_topology, set_parameter, screenshot, export, crash_reports, undo, redo, new_design, open, save`.
Read-only (`readOnlyHint: true`): `list_commands, inspect_design, measure, body_topology, crash_reports`.
`destructiveHint: true`: `execute, batch, screenshot, export, new_design, open, save`. `set_parameter`, `undo`,
`redo`: neither read-only nor destructive. These are hints for the client, not enforcement.

**Build** (`02_*.json`). The demo's 13 commands (and its sketch ids `p5`, `l1`, `l2`) work unchanged as **one batch**;
no fallback to separate `execute` calls was needed. Result: `ok: true, completed: 13`. One body "Enclosure":
bbox X −40…40, Y −30…30, Z 0…30 → **80 × 60 × 30 mm**; **volume 24 289.40 mm³** (analytic for a 6 mm corner radius,
2 mm wall, open top, `shelled_volume` in `tests/test_lab.py`: 24 289.49, so 0.0004 % apart); area 24 828.80 mm²; 19 faces (8 cylindrical, 11 planar), 48 edges, 32 vertices.
Timeline: `Outline` (Sketch), `Extrude1`, `Fillet1`, `Shell1`. Undo depth 11. The sketch dimensions report
`"expression": "width", "measured": 80.0` and `"expression": "depth", "measured": 60.0`, and the sketch ends at 0 DOF.

**Failing batch** (`03_*.json`). Reply, exactly:
`ok: false`, `completed: 3`, `failed: {index: 3, command: "solid.fillet", error: "not supported yet: the blend is
larger than a corner radius; the largest radius that fits is 2 mm"}`, `rolled_back: true`, `undone: 3`, plus the
results of the three steps that had run (the "USB port" sketch). `isError: true`. Before and after: volume
24 289.39602, size [80, 60, 30], the same 4 timeline features, undo depth 11 → 11, same parameters. The iso PNG after
the failure is **byte-identical** to the one after the build (same MD5). Note the wording: the engine calls this
"not supported yet", and tells the agent the largest radius that would fit, which is what lets a model correct itself.

**Width 80 → 100** (`04_*.json`). `set_parameter` reply: `{"value": 100.0, "expression": "100 mm", "recomputed": 4,
"restored": 0, "errors": []}`. Size **[80, 60, 30] → [100, 60, 30]**; volume **24 289.40 → 28 929.40 mm³** (analytic
28 929.49, 0.0003 % apart). All four features have `error: null`.

**Export and the folder limit** (`05_*.json`). `/lab/out/enclosure.step`: 27 825 bytes, `"format": "Step"`, starts
`ISO-10303-21`. `/lab/out/enclosure.stl`: 115 884 bytes, `"format": "StlBinary"`. Refused, `isError: true`, exact text:

```
/lab/forbidden/enclosure.step: /lab/forbidden/enclosure.step: outside the folders this agent may use (/root/.local/share/solidcraft/recovery, /tmp/solidcraft-mcp-7-2af3b364, /lab/out); allow another folder with `--allow-path DIR`
```

and the same for `/lab/out/../forbidden/enclosure.step` (the `..` is resolved first, then refused). `/lab/forbidden`
stayed empty. The STEP file re-read by a separate process: 100 × 60 × 30, volume 28 929.29 mm³ (0.0004 % below the
in-session value), **no parameters, one `BaseFeature`**: STEP carries exact geometry, not the design's history.

**Undo** (`06_*.json`). Reply `{"undone": "Change Parameters"}`; width back to 80, size 80 × 60 × 30.

**Screenshot** (`07_*.json`). `{"renderer": "gpu-software", "source": "model", "width": 960, "height": 600, "bytes": 42841}`
for the top view. Renders are deterministic: two full runs gave identical PNG bytes.

### Where reality differed from the plan (tests adjusted to the observed truth, not fudged)

1. **`recomputed` is a count, not a list.** PLAN.html says "recomputed features listed". v0.14.0 returns
   `"recomputed": 4`. The names come from `inspect_design`'s timeline (`Outline, Extrude1, Fillet1, Shell1`, all of
   which depend on width). Test 4 asserts `recomputed` is an integer equal to the timeline length. On screen: "4
   features rebuilt", with the names from the timeline.
2. **`measure.total` has no bounding box.** The docs say bbox "per body, with totals"; the total has volume, area,
   mass and counts, the bbox is per body only. The tests take the union of the body boxes.
3. **The refusal text has more than the plan quotes.** The path is printed twice, then the allowed folders, including
   the server's scratch folder, whose name changes every run (`/tmp/solidcraft-mcp-7-<random>`). Quote the stable part:
   "outside the folders this agent may use … allow another folder with `--allow-path DIR`".
4. **The failing step's error says "not supported yet"** rather than "impossible": the 25 mm fillet is refused as a
   blend larger than the corner radius, with the largest radius that fits (2 mm).
5. **Not tested here:** PLAN chapter 5's "the screw bosses don't move" (the lab builds up to the shell; no bosses),
   and chapter 3's "the local control port isn't an MCP endpoint" (documented, not tested, as the plan says).

## The Claude Code run (17 Oct 2026, 02:58 UTC)

One headless run, owner-approved, first attempt, no retries (`claude-run/run-claude.sh`):

```
claude -p "<prompt>" --mcp-config claude-run/mcp-config.json --strict-mcp-config --tools "" \
  --allowedTools "mcp__solidcraft__*" --permission-mode dontAsk --max-budget-usd 4 \
  --no-session-persistence --output-format json
```

Claude Code 2.1.302, default model (`claude-opus-5-5`). Only the solidcraft tools were available (no built-in tools, no
other MCP servers). This CLI has no `--max-turns`, so cost was capped with `--max-budget-usd` and time with
`timeout 600`. The MCP server was `docker run -i --rm … solidcraft-mcp-lab:0.14.0` with the logging proxy running in
the same container in front of `solidcraft-cli mcp --allow-path /lab/out` (so only `docker` and `claude` ran on the
host); `/lab/out` was mounted to `tests/out/claude-run/`. The owner's global CLAUDE.md and memory were loaded as usual
(`--bare` would have needed an API key instead of the login); with no built-in tools they could not change anything.

The prompt: "Use the solidcraft MCP tools to build a simple electronics enclosure: parameters width 80 mm, depth 60 mm,
height 30 mm, wall 2 mm, with the sketch dimensions tied to those parameters; round the four vertical edges, then shell
it open at the top. Measure it and report the bounding box. Then change width to 100 mm, measure again, and report
which features were recomputed. Export a STEP file to /lab/out/claude-enclosure.step. Report any step that failed."

**Result** (`tests/out/claude-run/claude-output.json`, `summary.json`, `transcript.jsonl`): success, 14 turns, 35.5 s,
$0.196, **13 tool calls, none failed, no permission denials**:

| # | Tool | What |
|---|---|---|
| 1–2 | `list_commands` | looked up `shell` and `sketch.dimension` parameter docs |
| 3–6 | `set_parameter` ×4 | width 80, depth 60, height 30, wall 2 (mm) |
| 7 | `batch` (`rollback: false`) | `sketch.create` XY, `sketch.rectangle.two_point` (0,0)–(80,60) |
| 8 | `batch` | `sketch.dimension` l1 = `width`, l2 = `depth`, `sketch.finish`, `solid.extrude` by `height` |
| 9 | `batch` | `solid.fillet` four vertical edges, **5 mm** (its own choice), `solid.shell` top face, thickness `wall`, inside |
| 10 | `measure` | 80 × 60 × 30 (min 0,0,0), volume 24 404.4 mm³ |
| 11 | `set_parameter` | width "100 mm" → `recomputed: 4`, `errors: []` |
| 12 | `inspect_design` | 100 × 60 × 30, timeline names |
| 13 | `export` | `/lab/out/claude-enclosure.step`, 28 210 bytes |

What it reported: bbox (0,0,0)–(80,60,30), then (0,0,0)–(100,60,30); "Recomputed: 4 features, the whole timeline:
Sketch1, Extrude1, Fillet1 and Shell1"; no step failed. All true against the transcript; it read the names from
`inspect_design` because `recomputed` is only a count. Differences from the lab's build: the rectangle sits in the
first quadrant instead of on the origin, and it picked a 5 mm corner radius (the prompt gave none; the demo uses 6 mm),
hence a different volume. Its exported file, re-read with `solidcraft-cli eval`
(`claude-enclosure.step.eval.json`): 100 × 60 × 30, volume 29 044.36 mm³. One wrong guess: its last line said the file
is probably "inside the container and not on your Windows filesystem"; with the mount, it landed in
`tests/out/claude-run/`. It took no screenshot.

Protocol details visible in the log: Claude Code first probes `server/discover` (protocol `2026-07-28`); SolidCraft
answers `-32601 method not found`; Claude Code then sends `initialize` asking for `2025-11-25` and the server answers
with `2025-06-18`, which the client accepts. Screenshot data would be shortened in the log only (size + SHA-256, PNG
saved beside it); this run took none.

## Licence

Lab code: Apache License 2.0 (`LICENSE`). SolidCraft is "MIT OR Apache-2.0"; `tests/enclosure_steps.json` is copied
unchanged from its repository under that licence. The Docker image downloads SolidCraft's official release; it is
not redistributed here.
