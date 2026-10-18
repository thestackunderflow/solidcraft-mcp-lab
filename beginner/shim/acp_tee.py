#!/usr/bin/env python3
"""ACP tee: installed as `claude-agent-acp` ahead of the real one on PATH. Starts the real adapter and copies every
JSON-RPC line both ways to $ACP_LOG (one JSON object per line: t, dir, msg).

One change to the traffic, only when $MCP_PROXY is set (a JSON list, the proxy command ending in "--"): in
`session/new`, each MCP server SolidCraft hands the agent is started through that proxy, so every MCP message is
logged too. The log records the line as SolidCraft sent it, before that change. Everything else passes byte for byte."""
import json, os, subprocess, sys, threading, time

def wrap_mcp(line, proxy):
    """`line` with session/new's MCP servers started through `proxy` (argv ending in '--'); any other line unchanged."""
    if not proxy: return line
    try: msg = json.loads(line)
    except ValueError: return line
    if not isinstance(msg, dict) or msg.get('method') != 'session/new': return line
    for s in msg.get('params', {}).get('mcpServers', []):
        if 'command' in s:
            s['args'] = list(proxy[1:]) + [s['command']] + list(s.get('args', []))
            s['command'] = proxy[0]
    return json.dumps(msg).encode() + b'\n'

def main():
    real = os.environ.get('ACP_REAL', '/usr/local/bin/claude-agent-acp')
    p = subprocess.Popen([real] + sys.argv[1:], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    if sys.argv[1:] and sys.argv[1] in ('--version', '-v'):   # detection: pass the version through, log nothing
        out, _ = p.communicate(); sys.stdout.buffer.write(out); sys.exit(p.returncode)
    log_file = open(os.environ.get('ACP_LOG', '/work/out/acp.jsonl'), 'a', buffering=1)
    proxy = json.loads(os.environ['MCP_PROXY']) if os.environ.get('MCP_PROXY') else None
    lock = threading.Lock()

    def log(direction, line):
        try: msg = json.loads(line)
        except ValueError: msg = {'raw': line.decode('utf8', 'replace')}
        with lock: log_file.write(json.dumps({'t': round(time.time(), 3), 'dir': direction, 'msg': msg}) + '\n')

    def pump(src, dst, direction, change=lambda l: l):
        for line in iter(src.readline, b''):
            if line.strip(): log(direction, line)
            dst.write(change(line)); dst.flush()
        try: dst.close()
        except OSError: pass

    threading.Thread(target=pump, args=(sys.stdin.buffer, p.stdin, 'app->agent', lambda l: wrap_mcp(l, proxy)),
                     daemon=True).start()
    pump(p.stdout, sys.stdout.buffer, 'agent->app')
    sys.exit(p.wait())

if __name__ == '__main__':
    main()
