"""Stub (red phase): the tests exist before the client does."""
import os
OUT = os.path.join(os.path.dirname(__file__), "out")
SERVER_CMD = ["solidcraft-cli", "mcp", "--allow-path", "/lab/out"]
class McpClient:
    def __init__(self, cmd): self.cmd = cmd
    def start(self): raise NotImplementedError("McpClient.start")
    def close(self): pass
def save(name, obj): raise NotImplementedError("save")
def save_png(mcp, name, args): raise NotImplementedError("save_png")
