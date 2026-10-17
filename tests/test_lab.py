"""SolidCraft v0.14.0 over MCP (stdio): what the server really does, tested.

The tests share one server session and run in order (0 -> 7), like one agent session:
build the enclosure, fail a batch, change a parameter, export, undo, look at it.
Every reply is saved to tests/out/ so the video quotes files, never memory.
"""

import json
import math
import os
import subprocess

import pytest

from mcp_client import SERVER_CMD, McpClient, OUT, save, save_png

CLI = "solidcraft-cli"
ALLOWED = "/lab/out"
FORBIDDEN = "/lab/forbidden"
STEPS_FILE = os.path.join(os.path.dirname(__file__), "enclosure_steps.json")

# The tools docs/mcp.md (v0.14.0) documents. Checked as a subset, not a count.
DOCUMENTED_TOOLS = {
    "list_commands", "execute", "batch", "inspect_design", "measure", "body_topology",
    "set_parameter", "screenshot", "export", "undo", "redo", "crash_reports",
    "new_design", "open", "save",
}
READ_ONLY_TOOLS = {"list_commands", "inspect_design", "measure", "body_topology", "crash_reports"}
FILE_TOOLS = {"execute", "batch", "open", "save", "export", "screenshot"}

# Analytic volume of the shelled, rounded box (outer W x D x H, corner radius R, wall T, open top):
# rounded rectangle area = w*d - (4 - pi) * r^2; the inner pocket is offset by T (radius R - T), depth H - T.
def shelled_volume(w, d, h, r=6.0, t=2.0):
    outer = (w * d - (4 - math.pi) * r * r) * h
    ri = r - t
    inner = ((w - 2 * t) * (d - 2 * t) - (4 - math.pi) * ri * ri) * (h - t)
    return outer - inner


def size(m):
    """[dx, dy, dz] of a `measure` reply. Observed in v0.14.0: `total` has volume, area and counts
    but no bbox; each body has `bbox: {min, max}`. So: the union of the bodies' boxes."""
    lo = [min(b["bbox"]["min"][i] for b in m["bodies"]) for i in range(3)]
    hi = [max(b["bbox"]["max"][i] for b in m["bodies"]) for i in range(3)]
    return [round(hi[i] - lo[i], 6) for i in range(3)]


@pytest.fixture(scope="module")
def mcp():
    c = McpClient(SERVER_CMD)
    c.start()
    yield c
    c.close()


def state(mcp):
    """What must not change when a batch fails: volume, bbox, timeline, undo depth, parameters."""
    d = mcp.tool_json("inspect_design", {"measure": True, "sketches": False})
    m = mcp.tool_json("measure", {})
    return {
        "volume_mm3": round(m["total"]["volume_mm3"], 6),
        "bbox_size": size(m),
        "timeline": [(f.get("name"), f.get("type")) for f in d["timeline"]],
        "undo": d["undo"],
        "params": {p["name"]: p["value"] for p in d["params"]},
    }


# 0 ------------------------------------------------------------------------------------------
def test_0_version_and_renderer(mcp):
    version = subprocess.run([CLI, "--version"], capture_output=True, text=True, check=True).stdout.strip()
    gpu = subprocess.run([CLI, "gpu"], capture_output=True, text=True, check=True)
    info = json.loads(gpu.stdout)
    save("00_version_renderer", {
        "cli_version": version,
        "server_info": mcp.init_result.get("serverInfo"),
        "protocol_version": mcp.init_result.get("protocolVersion"),
        "gpu": info,
        "gpu_stderr": gpu.stderr.strip(),
        "server_stderr_startup": mcp.stderr_text(),
    })
    assert version == "solidcraft-cli 0.14.0"
    assert mcp.init_result["serverInfo"]["version"] == "0.14.0"
    # No GPU in a container: the software Vulkan device (llvmpipe) or the CPU rasterizer.
    assert info["renderer"] in ("gpu-software", "cpu")


# 1 ------------------------------------------------------------------------------------------
def test_1_tools_list_has_the_documented_tools(mcp):
    r = mcp.request("tools/list", {})
    save("01_tools_list", r)
    tools = {t["name"]: t for t in r["tools"]}
    assert DOCUMENTED_TOOLS <= set(tools), DOCUMENTED_TOOLS - set(tools)
    for name in READ_ONLY_TOOLS:
        assert tools[name].get("annotations", {}).get("readOnlyHint") is True, name
    for name in FILE_TOOLS:
        a = tools[name].get("annotations", {})
        assert a.get("readOnlyHint") is not True, name
        assert a.get("destructiveHint") is True, name


# 2 ------------------------------------------------------------------------------------------
def enclosure_commands():
    """The project's demo (examples/demo/enclosure_steps.json), up to and including the shell:
    parameters -> sketch -> dimensions bound to width/depth -> extrude by height -> fillet -> shell."""
    steps = json.load(open(STEPS_FILE))["steps"]
    cmds = []
    for s in steps:
        cmds.append({"command": s["command"], "params": s["params"]})
        if s["command"] == "solid.shell":
            break
    return cmds


def test_2_one_batch_builds_the_enclosure(mcp):
    cmds = enclosure_commands()
    assert [c["command"] for c in cmds][-3:] == ["solid.extrude", "solid.fillet", "solid.shell"]
    raw = mcp.call_tool("batch", {"commands": cmds})
    body = mcp.text_json(raw)
    save("02_build_batch_request", {"commands": cmds})
    save("02_build_batch_reply", raw)
    assert raw.get("isError") is not True, body
    assert body["ok"] is True and body["completed"] == len(cmds)

    m = mcp.tool_json("measure", {})
    d = mcp.tool_json("inspect_design", {"measure": False, "sketches": True})
    save("02_measure_after_build", m)
    save("02_inspect_after_build", d)
    params = {p["name"]: p["value"] for p in d["params"]}
    assert params == {**params, "width": 80, "depth": 60, "height": 30, "wall": 2}
    assert m["body_count"] == 1
    assert size(m) == pytest.approx([80, 60, 30], abs=1e-6)
    assert m["total"]["volume_mm3"] == pytest.approx(shelled_volume(80, 60, 30), rel=1e-3)
    types = [f["type"] for f in d["timeline"]]
    assert len(types) >= 4  # sketch, extrude, fillet, shell (names as the engine reports them)
    save_png(mcp, "02_iso_after_build", {"view": "iso"})


# 3 ------------------------------------------------------------------------------------------
def failing_batch():
    """Step 4 of 4 fails: a USB-port sketch, then a fillet far larger than the 2 mm wall allows."""
    return [
        {"command": "sketch.create", "params": {"plane": {"origin": [0, 0, 0], "x_dir": [0, 1, 0], "y_dir": [0, 0, 1]}, "name": "USB port"}},
        {"command": "sketch.rectangle.center", "params": {"center": [0, 12], "corner": [6, 15.5]}},
        {"command": "sketch.finish", "params": {}},
        {"command": "solid.fillet", "params": {"edges": [[40, 0, 30]], "radius": 25}},
    ]


def test_3_failing_batch_rolls_back(mcp):
    before = state(mcp)
    raw = mcp.call_tool("batch", {"commands": failing_batch()})
    body = mcp.text_json(raw)
    after = state(mcp)
    save("03_failing_batch_request", {"commands": failing_batch()})
    save("03_failing_batch_reply", raw)
    save("03_state_before_after", {"before": before, "after": after})
    assert raw.get("isError") is True
    assert body["ok"] is False
    assert body["failed"]["index"] == 3
    assert body["failed"]["command"] == "solid.fillet"
    assert isinstance(body["failed"]["error"], str) and body["failed"]["error"]
    assert body["rolled_back"] is True
    assert body["completed"] == 3 and len(body["results"]) == 3
    assert after == before
    save_png(mcp, "03_iso_after_failed_batch", {"view": "iso"})


# 4 ------------------------------------------------------------------------------------------
def test_4_set_parameter_width_100(mcp):
    before = mcp.tool_json("measure", {})
    r = mcp.tool_json("set_parameter", {"name": "width", "value": "100 mm"})
    after = mcp.tool_json("measure", {})
    save("04_set_parameter_reply", r)
    save("04_measure_after_width_100", after)
    d = mcp.tool_json("inspect_design", {"measure": False, "sketches": False})
    timeline = [{k: f.get(k) for k in ("id", "name", "type", "error", "warning", "ms")} for f in d["timeline"]]
    save("04_timeline_after_width_100", timeline)
    # Observed in v0.14.0: `recomputed` is a COUNT of rebuilt features, not a list of names.
    # Every feature here depends on width (sketch -> extrude -> fillet -> shell), so it equals
    # the timeline length; the names come from inspect_design's timeline.
    assert isinstance(r["recomputed"], int) and r["recomputed"] > 0, r
    assert r["recomputed"] == len(timeline), (r, timeline)
    assert all(f["error"] is None for f in timeline), timeline
    assert r["errors"] == [], r
    sb, sa = size(before), size(after)
    save("04_bbox_before_after", {"before": sb, "after": sa,
                                  "volume_before": before["total"]["volume_mm3"],
                                  "volume_after": after["total"]["volume_mm3"]})
    assert sb[0] == pytest.approx(80) and sa[0] == pytest.approx(100)
    assert sa[1:] == pytest.approx(sb[1:])
    assert after["total"]["volume_mm3"] == pytest.approx(shelled_volume(100, 60, 30), rel=1e-3)
    save_png(mcp, "04_iso_after_width_100", {"view": "iso"})


# 5 ------------------------------------------------------------------------------------------
def test_5_export_inside_allowed_folder_only(mcp):
    replies = {}
    for fmt in ("step", "stl"):
        p = f"{ALLOWED}/enclosure.{fmt}"
        raw = mcp.call_tool("export", {"path": p, "format": fmt})
        replies[p] = raw
        assert raw.get("isError") is not True, raw
        assert os.path.getsize(p) > 0
    with open(f"{ALLOWED}/enclosure.step", encoding="utf-8", errors="replace") as f:
        assert f.read(64).startswith("ISO-10303-21")

    refused = {}
    for p in (f"{FORBIDDEN}/enclosure.step", f"{ALLOWED}/../forbidden/enclosure.step"):
        raw = mcp.call_tool("export", {"path": p, "format": "step"})
        refused[p] = raw
        assert raw.get("isError") is True, raw
        assert "outside the folders this agent may use" in mcp.text(raw)
    save("05_export_replies", {"allowed": replies, "refused": refused,
                               "allowed_listing": sorted(os.listdir(ALLOWED)),
                               "forbidden_listing": sorted(os.listdir(FORBIDDEN))})
    assert os.listdir(FORBIDDEN) == []


# 6 ------------------------------------------------------------------------------------------
def test_6_undo_brings_width_back_to_80(mcp):
    raw = mcp.call_tool("undo", {})
    d = mcp.tool_json("inspect_design", {"measure": False, "sketches": False})
    m = mcp.tool_json("measure", {})
    save("06_undo_reply", raw)
    save("06_after_undo", {"params": d["params"], "bbox_size": size(m),
                           "volume_mm3": m["total"]["volume_mm3"]})
    assert raw.get("isError") is not True, raw
    params = {p["name"]: p["value"] for p in d["params"]}
    assert params["width"] == 80
    assert size(m) == pytest.approx([80, 60, 30], abs=1e-6)


# 7 ------------------------------------------------------------------------------------------
def test_7_screenshot_returns_png_and_renderer(mcp):
    info = save_png(mcp, "07_top_after_undo", {"view": "top"})
    save("07_screenshot_info", info)
    assert info["renderer"] in ("gpu-software", "cpu")
    for name in ("02_iso_after_build", "03_iso_after_failed_batch", "04_iso_after_width_100", "07_top_after_undo"):
        with open(os.path.join(OUT, name + ".png"), "rb") as f:
            assert f.read(8) == b"\x89PNG\r\n\x1a\n", name
