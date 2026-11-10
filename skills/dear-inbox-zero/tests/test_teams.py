"""Teams filter and signal tests on synthetic chats only."""
import os, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "engine"))
from diz import learn as L, teams as T  # noqa: E402
from diz.util import parse_ts  # noqa: E402


class TeamsTests(unittest.TestCase):
    def setUp(self):
        self.profile = {"tz": "UTC", "working_hours": [9, 17], "teams_reply_hours": 4}
        self.now = parse_ts("2026-03-02T12:00:00Z")

    def test_filter_keeps_questions_mentions_and_aged_direct_chats(self):
        chats = [
            {"id": "direct-aged", "direct": True, "messages": [
                {"id": "m1", "sender_id": "pat", "sent_at": "2026-02-27T16:00:00Z"}]},
            {"id": "group-question", "messages": [
                {"id": "m2", "sender_id": "sam", "sent_at": "2026-03-02T11:30:00Z", "has_question": True}]},
            {"id": "channel-mention", "kind": "channel", "messages": [
                {"id": "m3", "sender_id": "lee", "sent_at": "2026-03-02T11:30:00Z", "mentions_me": True}]},
            {"id": "answered", "direct": True, "messages": [
                {"id": "m4", "sender_id": "pat", "sent_at": "2026-03-02T08:00:00Z", "has_question": True},
                {"id": "m5", "sender_id": "alex", "sent_at": "2026-03-02T11:00:00Z", "is_me": True}]},
            {"id": "recent", "direct": True, "messages": [
                {"id": "m6", "sender_id": "pat", "sent_at": "2026-03-02T11:00:00Z"}]},
            {"id": "outside-hours", "direct": True, "messages": [
                {"id": "m7", "sender_id": "pat", "sent_at": "2026-03-01T23:00:00Z"}]},
        ]
        result = T.needs_response(chats, self.profile, "alex", self.now)
        self.assertEqual({item["thread_id"] for item in result},
                         {"direct-aged", "group-question", "channel-mention"})

    def test_filter_uses_latest_message_and_truncates_preview(self):
        chat = {"id": "c1", "direct": True, "messages": [
            {"id": "old", "sender_id": "pat", "sent_at": "2026-03-02T08:00:00Z", "has_question": True},
            {"id": "new", "sender_id": "pat", "sent_at": "2026-03-02T12:30:00Z",
             "has_question": True, "text": "x" * 400},
        ]}
        result = T.needs_response([chat], self.profile, "alex", self.now)
        self.assertEqual(result[0]["id"], "new")
        self.assertEqual(len(result[0]["preview"]), 300)

    def test_signals_use_own_posts_and_report_unanswered_loops(self):
        state = {"head": {
            "last_run": {"decisions": [
                {"id": "m1", "channel": "teams", "thread_id": "chat-1", "received_at": "2026-02-27T09:00:00Z"}]},
            "ledger": [
                {"id": "m1", "channel": "teams", "thread_id": "chat-1", "received_at": "2026-02-27T09:00:00Z", "state": "open"},
                {"id": "m2", "channel": "teams", "thread_id": "chat-2", "received_at": "2026-02-26T09:00:00Z", "state": "open"},
                {"id": "m3", "channel": "teams", "thread_id": "chat-4", "received_at": "2026-02-26T09:00:00Z", "state": "open"},
            ],
        }}
        posts = [
            {"id": "p1", "thread_id": "chat-1", "sender_id": "alex", "sent_at": "2026-02-27T10:00:00Z"},
            {"id": "p2", "thread_id": "chat-3", "sender_id": "alex", "reply_to_sender": "pat@example.com",
             "sent_at": "2026-03-02T10:00:00Z"},
            {"id": "p3", "thread_id": "chat-2", "sender_id": "alex", "sent_at": "2026-03-02T10:00:00Z"},
        ]
        result = T.signals(posts, state, "alex", self.now)
        pairs = {(item["id"], item["signal"]) for item in result}
        self.assertIn(("m1", "replied"), pairs)
        self.assertIn(("m2", "replied"), pairs)
        self.assertIn(("p2", "replied_not_proposed"), pairs)
        self.assertIn(("m3", "ignored"), pairs)
        unproposed = next(item for item in result if item["signal"] == "replied_not_proposed")
        self.assertEqual(unproposed["sender"], "pat@example.com")
        observed = {"head": {"last_run": {"decisions": []}, "signals": []}}
        L.observe(observed, [unproposed], self.now)
        self.assertEqual(observed["head"]["signals"][0]["outcome"], "override")


if __name__ == "__main__":
    unittest.main()
