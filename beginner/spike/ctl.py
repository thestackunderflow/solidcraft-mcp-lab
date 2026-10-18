"""Tiny SolidCraft control-channel client: python3 ctl.py METHOD '{json params}' [PORT]. Prints the reply line."""
import json, socket, sys
from pathlib import Path

def call(method, params, port=7878, timeout=120):
    token = (Path.home() / f'.local/share/solidcraft/control/{port}.token').read_text().strip()
    with socket.create_connection(('127.0.0.1', port), timeout=timeout) as s:
        s.sendall((json.dumps({'id': 1, 'method': method, 'params': params, 'token': token}) + '\n').encode())
        buf = b''
        while not buf.endswith(b'\n'):
            chunk = s.recv(1 << 20)
            if not chunk: break
            buf += chunk
    return json.loads(buf)

if __name__ == '__main__':
    print(json.dumps(call(sys.argv[1], json.loads(sys.argv[2]) if len(sys.argv) > 2 else {},
                          int(sys.argv[3]) if len(sys.argv) > 3 else 7878)))
