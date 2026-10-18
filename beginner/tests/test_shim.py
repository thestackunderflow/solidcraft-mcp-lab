"""The ACP tee's one change to traffic: SolidCraft's MCP server is started through our logging proxy."""
import importlib.util, json, os, unittest

spec = importlib.util.spec_from_file_location('acp_tee', os.path.join(os.path.dirname(__file__), '..', 'shim', 'acp_tee.py'))
tee = importlib.util.module_from_spec(spec); spec.loader.exec_module(tee)

NEW = {'jsonrpc': '2.0', 'id': 2, 'method': 'session/new', 'params': {'cwd': '/w', 'mcpServers': [
    {'name': 'solidcraft', 'command': '/opt/solidcraft/bin/solidcraft-cli', 'args': ['mcp', '--connect', '127.0.0.1:41309'], 'env': []}]}}
PROXY = ['python3', '/work/proxy/mcp_log_proxy.py', '--log', '/work/out/mcp.jsonl', '--']

class Wrap(unittest.TestCase):
    def test_session_new_starts_the_server_through_the_proxy(self):
        out = json.loads(tee.wrap_mcp(json.dumps(NEW).encode() + b'\n', PROXY))
        s = out['params']['mcpServers'][0]
        self.assertEqual(s['command'], 'python3')
        self.assertEqual(s['args'], PROXY[1:] + ['/opt/solidcraft/bin/solidcraft-cli', 'mcp', '--connect', '127.0.0.1:41309'])
        self.assertEqual((s['name'], s['env']), ('solidcraft', []))

    def test_every_other_line_passes_byte_for_byte(self):
        for line in [b'{"jsonrpc":"2.0","id":3,"method":"session/prompt","params":{}}\n', b'not json\n']:
            self.assertIs(tee.wrap_mcp(line, PROXY), line)

    def test_no_proxy_configured_changes_nothing(self):
        line = json.dumps(NEW).encode() + b'\n'
        self.assertIs(tee.wrap_mcp(line, None), line)

if __name__ == '__main__': unittest.main()
