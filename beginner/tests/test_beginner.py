"""SolidCraft 0.15.0, the desktop app with its window, driven over MCP bridged to it (`solidcraft-cli mcp --connect`, the
way Agent chat starts the server). Each test is one claim the beginner video makes. No AI in the loop: a small test
client sends the calls. Run inside the beginner image:  bash /work/tests/run-tests.sh
Every reply is saved to tests/out/ so the video quotes files, never memory."""
import json, os, subprocess, sys, time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'spike'))
from ctl import call
from mcp_client import SERVER_CMD, McpClient, save

HOME = os.path.expanduser('~')
DESIGNS = os.path.join(HOME, 'designs')          # a normal folder inside the home folder, as a viewer would make
EXPORTS = os.path.join(DESIGNS, 'exports')

# A box whose width is a named parameter that drives the sketch, and a named parameter that drives nothing.
BOX = [
    {'command': 'parameters.change', 'params': {'name': 'width', 'expression': '80 mm'}},
    {'command': 'parameters.change', 'params': {'name': 'depth', 'expression': '60 mm'}},
    {'command': 'parameters.change', 'params': {'name': 'phone_thickness', 'expression': '12 mm'}},   # named, not used
    {'command': 'sketch.create', 'params': {'plane': 'XY', 'name': 'Base'}},
    {'command': 'sketch.rectangle.center', 'params': {'center': [0, 0], 'corner': [40, 30]}},
    {'command': 'sketch.constraint.coincident', 'params': {'a': 'p5', 'b': 'origin'}},
    {'command': 'sketch.dimension', 'params': {'entities': ['l1'], 'value': 'width'}},
    {'command': 'sketch.dimension', 'params': {'entities': ['l2'], 'value': 'depth'}},
    {'command': 'sketch.finish', 'params': {}},
    {'command': 'solid.extrude', 'params': {'distance': '10 mm', 'body_name': 'Base'}},
]

def size(m):
    lo = [min(b['bbox']['min'][i] for b in m['bodies']) for i in range(3)]
    hi = [max(b['bbox']['max'][i] for b in m['bodies']) for i in range(3)]
    return [round(hi[i] - lo[i], 6) for i in range(3)]


@pytest.fixture(scope='module')
def app():
    """The real app with its window (Xvfb, software Vulkan) and its control channel on 7878."""
    os.makedirs(EXPORTS, exist_ok=True)
    env = dict(os.environ, DISPLAY=':98', XDG_RUNTIME_DIR='/tmp/xdg-t')
    os.makedirs('/tmp/xdg-t', mode=0o700, exist_ok=True)
    xvfb = subprocess.Popen(['Xvfb', ':98', '-screen', '0', '1600x1000x24'], stderr=subprocess.DEVNULL)
    time.sleep(2)
    sc = subprocess.Popen(['solidcraft', '--control', '7878'], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    for _ in range(60):
        try:
            if call('ui.inspect', {}).get('ok'): break
        except (OSError, FileNotFoundError): pass
        time.sleep(1)
    yield sc
    sc.terminate(); xvfb.terminate()


@pytest.fixture(scope='module')
def mcp(app):
    c = McpClient(SERVER_CMD); c.start()
    yield c
    c.close()


def test_1_the_bridged_server_lists_the_tools_agent_chat_uses(mcp):
    names = {t['name'] for t in mcp.request('tools/list', {})['tools']}
    save('b1_tools', sorted(names))
    assert {'inspect_design', 'batch', 'measure', 'set_parameter', 'export', 'save', 'undo'} <= names


def test_2_a_new_design_is_empty(mcp):
    d = mcp.tool_json('inspect_design', {})
    save('b2_inspect_empty', d)
    assert d['bodies'] == [] and d['timeline'] == [] and d['path'] is None


def test_3_a_named_size_that_drives_the_sketch_rebuilds_the_part(mcp):
    r = mcp.tool_json('batch', {'commands': BOX})
    save('b3_box_batch', r)
    before = size(mcp.tool_json('measure', {}))
    r = mcp.tool_json('set_parameter', {'name': 'width', 'value': '100 mm'})
    save('b3_set_width_100', r)
    after = size(mcp.tool_json('measure', {}))
    save('b3_sizes', {'before': before, 'after': after})
    assert before[:2] == [80, 60] and after[:2] == [100, 60]


def test_4_a_named_size_that_drives_nothing_changes_nothing(mcp):
    # The spike-4 session: Claude named phone_thickness, but the slot was a fixed number, so changing it did nothing.
    before = mcp.tool_json('measure', {})
    r = mcp.tool_json('set_parameter', {'name': 'phone_thickness', 'value': '9 mm'})
    save('b4_set_unbound', r)
    after = mcp.tool_json('measure', {})
    save('b4_measure_before_after', {'before': before['total'], 'after': after['total']})
    assert size(before) == size(after) and round(before['total']['volume_mm3'], 3) == round(after['total']['volume_mm3'], 3)


def test_5_export_of_an_unsaved_design_into_home_is_refused(mcp):
    r = mcp.call_tool('export', {'path': os.path.join(EXPORTS, 'stand-unsaved.stl')})
    save('b5_export_unsaved', r)
    assert r.get('isError') and not os.path.exists(os.path.join(EXPORTS, 'stand-unsaved.stl'))


def test_6_after_saving_in_a_home_folder_export_into_its_subfolder_works(mcp):
    # The video's step: the viewer saves the design themselves first (here over the control channel, as File > Save does).
    r = call('engine.execute', {'command': 'file.save_as', 'params': {'path': os.path.join(DESIGNS, 'stand.solidcraft')}})
    save('b6_save_as', r)
    assert r.get('ok'), r
    out = os.path.join(EXPORTS, 'stand.stl')
    r = mcp.call_tool('export', {'path': out})
    save('b6_export_after_save', r)
    assert not r.get('isError'), mcp.text(r)
    assert os.path.getsize(out) > 84


def test_7_export_outside_the_designs_folder_is_still_refused(mcp):
    r = mcp.call_tool('export', {'path': '/opt/stand.stl'})
    save('b7_export_outside', r)
    assert r.get('isError') and not os.path.exists('/opt/stand.stl')


def test_8_the_stl_is_a_closed_mesh(mcp):
    # A slicer needs a closed (watertight) mesh: every edge shared by exactly two triangles. Not a strength claim.
    import struct
    data = open(os.path.join(EXPORTS, 'stand.stl'), 'rb').read()
    if data[:5] == b'solid' and b'facet' in data[:400]:
        tris = [tuple(tuple(round(float(v), 4) for v in l.split()[1:4]) for l in f.split('\n') if l.strip().startswith('vertex'))
                for f in data.decode().split('endfacet')[:-1]]
    else:
        n = struct.unpack('<I', data[80:84])[0]
        tris = [tuple(tuple(round(v, 4) for v in struct.unpack('<3f', data[84 + 50 * i + 12 + 12 * k:84 + 50 * i + 24 + 12 * k]))
                      for k in range(3)) for i in range(n)]
    edges = {}
    for t in tris:
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            k = (min(a, b), max(a, b)); edges[k] = edges.get(k, 0) + 1
    bad = sum(1 for c in edges.values() if c != 2)
    save('b8_stl_check', {'triangles': len(tris), 'edges': len(edges), 'edges_not_shared_by_two': bad})
    assert tris and bad == 0
