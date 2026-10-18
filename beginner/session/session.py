"""Drive one Agent chat session through SolidCraft's control channel, step by step, and log a timeline.

    python3 session.py STEPS.json OUT_DIR

STEPS.json is a list; each step is one of:
  {"send": "text", "card": "deny"|"return"}  a message, typed into Agent chat; waits until Claude has answered it.
                                           An Allow / Deny card meanwhile is denied (default: nobody asked for it,
                                           labelled DENIED in the timeline) or, with "return", left for the next step
  {"approve": true | false | "always", "else_send": "text"?}   answer the oldest Allow / Deny card (labelled in the
                                           timeline: a script did it); with no card waiting, send else_send first
  {"undo": true}                           "Undo these changes" for the last message
  {"control": METHOD, "params": {...}}     a lab step over the control channel (e.g. the slip), labelled LAB
  {"pause": seconds}                       a beat for the recording
Every step writes one line to OUT_DIR/timeline.jsonl with UTC time, the step and the chat's state after it."""
import json, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'spike'))
from ctl import call

def chat(params=None):
    r = call('ui.agent_chat', params or {})
    if not r.get('ok'): raise RuntimeError(f'ui.agent_chat {params}: {r.get("error")}')
    return r['result']

def prompts_done(lines):
    """(prompts sent, prompts answered) in ACP log lines: a prompt is answered when a reply with its id has a stopReason."""
    sent, answered = set(), set()
    for l in lines:
        r = json.loads(l); m = r['msg']
        if r['dir'] == 'app->agent' and m.get('method') == 'session/prompt': sent.add(m.get('id'))
        if r['dir'] == 'agent->app' and isinstance(m.get('result'), dict) and 'stopReason' in m['result']: answered.add(m.get('id'))
    return len(sent), len(sent & answered)

def await_turn(chat_fn, counts_fn, on_card='deny', min_wait=4, poll=3, limit=900):
    """Wait until every prompt sent so far is answered (counts_fn() -> (sent, answered)). An Allow / Deny card that
    appears meanwhile is denied (on_card='deny': nobody asked for it) or ends the wait (on_card='return': the next
    step answers it). Returns (last chat state, cards denied)."""
    t0, denied = time.time(), 0
    time.sleep(min_wait)
    while time.time() - t0 < limit:
        st = chat_fn()
        if st.get('waiting'):
            if on_card == 'return': return st, denied
            chat_fn({'approve': False}); denied += 1
        else:
            sent, answered = counts_fn()
            if sent and sent == answered and not st.get('pending'): return st, denied
        time.sleep(poll)
    return chat_fn(), denied

def acp_counts():
    return prompts_done(open(os.environ['ACP_LOG'], encoding='utf8').read().splitlines())

def wait_ready(on_card='deny', min_wait=4):
    st, denied = await_turn(chat, acp_counts, on_card=on_card, min_wait=min_wait)
    time.sleep(2)
    return dict(chat(), denied_cards=denied)

def main(steps_file, out):
    steps = json.load(open(steps_file, encoding='utf8'))
    tl = open(os.path.join(out, 'timeline.jsonl'), 'a', buffering=1)
    def note(**kw):
        tl.write(json.dumps({'t': time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime()) + f'.{int(time.time() * 1000) % 1000:03d}Z', **kw}) + '\n')
    for i, s in enumerate(steps, 1):
        note(step=i, start=s)
        if 'send' in s:
            chat({'send': s['send']}); st = wait_ready(on_card=s.get('card', 'deny'))
        elif 'approve' in s:
            if chat().get('waiting'):
                chat({'approve': s['approve']}); st = wait_ready(min_wait=3)
            elif 'else_send' in s:   # no Allow card: Claude answered without trying; send the follow-up, then approve
                note(step=i, no_card=True, sending=s['else_send'])
                chat({'send': s['else_send']}); st = wait_ready(on_card='return')
                if st.get('waiting'): chat({'approve': s['approve']}); st = wait_ready(min_wait=3)
            else:
                note(step=i, no_card=True); st = chat()
        elif 'undo' in s:
            chat({'undo': True}); time.sleep(2); st = chat()
        elif 'control' in s:
            r = call(s['control'], s.get('params', {})); note(step=i, who='LAB (not the AI)', reply=r); st = chat()
        elif 'pause' in s:
            time.sleep(s['pause']); continue
        note(step=i, done=True, state=st.get('state'), waiting=st.get('waiting'), turn=st.get('turn'),
             denied_cards=st.get('denied_cards', 0))
    json.dump(chat(), open(os.path.join(out, 'chat-final.json'), 'w'), indent=1)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
