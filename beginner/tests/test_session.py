"""The session driver waits for Claude from the ACP log (a prompt is finished when its reply has a stopReason),
not from the app's busy/ready state, which said "ready" while a turn was still running (run-a, 18 Oct)."""
import json, os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'session'))
import session

def line(d, msg): return json.dumps({'t': 0, 'dir': d, 'msg': msg})

class PromptsDone(unittest.TestCase):
    def test_counts_prompts_sent_and_answered(self):
        lines = [line('app->agent', {'id': 5, 'method': 'session/prompt', 'params': {}}),
                 line('agent->app', {'method': 'session/update', 'params': {}}),
                 line('app->agent', {'id': 9, 'method': 'session/prompt', 'params': {}}),
                 line('agent->app', {'id': 5, 'result': {'stopReason': 'end_turn'}})]
        self.assertEqual(session.prompts_done(lines), (2, 1))

    def test_a_permission_answer_is_not_a_finished_prompt(self):
        lines = [line('app->agent', {'id': 5, 'method': 'session/prompt', 'params': {}}),
                 line('app->agent', {'id': 0, 'result': {'outcome': {'optionId': 'allow-once'}}})]
        self.assertEqual(session.prompts_done(lines), (1, 0))

if __name__ == '__main__': unittest.main()


class FakeChat:
    """The chat state over time: a list of states returned one per poll; records what the driver sent."""
    def __init__(self, states): self.states, self.sent = list(states), []
    def __call__(self, params=None):
        if params: self.sent.append(params)
        return self.states.pop(0) if len(self.states) > 1 else self.states[0]

class CardPolicy(unittest.TestCase):
    # run-b, 18 Oct: an unexpected Allow card (an undo from before the message) stopped the turn; the driver moved on.
    def test_an_unexpected_card_in_a_message_is_denied_and_the_turn_awaited(self):
        chat = FakeChat([{'waiting': 1}, {'waiting': 0}, {'waiting': 0}])
        logs = iter([(1, 0), (1, 1)])
        st, denied = session.await_turn(chat, lambda: next(logs), on_card='deny', min_wait=0, poll=0)
        self.assertEqual(chat.sent, [{'approve': False}])
        self.assertEqual(denied, 1)

    def test_a_card_we_expect_is_left_for_the_approve_step(self):
        chat = FakeChat([{'waiting': 1}])
        st, denied = session.await_turn(chat, lambda: (1, 0), on_card='return', min_wait=0, poll=0)
        self.assertEqual((chat.sent, denied, st['waiting']), ([], 0, 1))
