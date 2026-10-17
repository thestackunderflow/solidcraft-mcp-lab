"""Summarize tests/out/claude-run/transcript.jsonl + claude-output.json into summary.json."""
import collections, json, os, sys

d = sys.argv[1] if len(sys.argv) > 1 else "tests/out/claude-run"
lines = [json.loads(l) for l in open(os.path.join(d, "transcript.jsonl"), encoding="utf-8")]
out = json.load(open(os.path.join(d, "claude-output.json"), encoding="utf-8"))
calls, results = {}, {}
for e in lines:
    m = e["msg"]
    if not isinstance(m, dict):
        continue
    if e["dir"] == "client->server" and m.get("method") == "tools/call":
        calls[m["id"]] = {"t": e["t"], "tool": m["params"]["name"], "arguments": m["params"].get("arguments")}
    elif e["dir"] == "server->client" and m.get("id") in calls:
        r = m.get("result") or {}
        calls[m["id"]]["isError"] = bool(r.get("isError")) or "error" in m
        if calls[m["id"]]["isError"]:
            calls[m["id"]]["error_text"] = " ".join(c.get("text", "") for c in r.get("content", []) if c.get("type") == "text") or m.get("error")
seq = [calls[k] for k in sorted(calls)]
summary = {
    "tool_calls": len(seq),
    "by_tool": dict(collections.Counter(c["tool"] for c in seq)),
    "failed_calls": [c for c in seq if c.get("isError")],
    "batch_commands": [[s["command"] for s in c["arguments"]["commands"]] for c in seq if c["tool"] == "batch"],
    "sequence": [f'{c["t"][11:19]} {c["tool"]}' + (" (ERROR)" if c.get("isError") else "") for c in seq],
    "first_call": seq[0]["t"] if seq else None,
    "last_call": seq[-1]["t"] if seq else None,
    "claude": {k: out.get(k) for k in ("subtype", "is_error", "num_turns", "duration_ms", "duration_api_ms", "total_cost_usd", "terminal_reason", "permission_denials")},
    "model": list(out.get("modelUsage", {}).keys()),
}
json.dump(summary, open(os.path.join(d, "summary.json"), "w", encoding="utf-8"), indent=1)
print(json.dumps({k: summary[k] for k in ("tool_calls", "by_tool", "failed_calls", "claude", "model")}, indent=1))
