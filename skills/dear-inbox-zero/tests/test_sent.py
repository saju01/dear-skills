"""Sent-box study and daily signals, synthetic data only."""
import os, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "engine"))
from diz import sent as S  # noqa: E402

BODY_EN = "Hi Pat,\n\nThanks for the update. I will review the deck and send comments tomorrow.\n\nThanks, Alex\n\nOn Mon, Pat wrote:\n> can you review?"
BODY_NL = "Hoi Sam,\n\nDank je voor het bericht. Ik kijk er graag naar en stuur het voor vrijdag.\n\nGroet, Alex\n\nVan: Sam\nVerzonden: maandag"


class SentStudy(unittest.TestCase):
    def test_strip_reply_keeps_only_own_text(self):
        own = S.strip_reply(BODY_EN)
        self.assertNotIn("can you review", own)
        self.assertTrue(own.endswith("Thanks, Alex"))

    def test_features_template_the_recipient_not_the_user(self):
        f = S.features(BODY_EN, ["Pat"])
        self.assertEqual(f["greeting"], "Hi {first_name},")
        self.assertEqual(f["sign_off"], "Thanks, Alex")
        self.assertEqual(f["language"], "en")
        self.assertEqual(S.features(BODY_NL, ["Sam"])["language"], "nl")

    def test_study_learns_reply_vip_language_hours(self):
        sent = []
        for i in range(10):
            sent.append({"id": f"s{i}", "conversation_id": f"c{i}", "sent_at": f"2026-02-{10 + i:02d}T09:30:00Z",
                         "to": ["pat@example.com"], "in_reply_to_sender": "pat@example.com",
                         "in_reply_to_received_at": f"2026-02-{10 + i:02d}T08:30:00Z", "recipient_names": ["Pat"]})
        for i in range(3):
            sent.append({"id": f"n{i}", "conversation_id": f"d{i}", "sent_at": f"2026-02-{10 + i:02d}T14:00:00Z",
                         "to": ["sam@example.org"], "in_reply_to_sender": "sam@example.org", "recipient_names": ["Sam"]})
        res = S.study(sent, bodies={"s1": BODY_EN, "s2": BODY_EN, "n1": BODY_NL})
        kinds = {(o["kind"], o["key"]) for o in res["observations"]}
        self.assertIn(("replied_to", "pat@example.com"), kinds)
        self.assertIn(("vip_hint", "pat@example.com"), kinds)
        self.assertIn(("replied_to", "sam@example.org"), kinds)
        pat = next(p for p in res["people"] if p["key"] == "pat@example.com")
        self.assertEqual(pat["median_reply_hours"], 1.0)
        self.assertEqual(next(p for p in res["people"] if p["key"] == "sam@example.org")["language"], "nl")
        self.assertEqual(res["voice"]["greeting"], "Hi {first_name},")
        self.assertEqual(res["profile_hints"]["working_hours"], [9, 15])
        self.assertNotIn("deck", str(res))  # no body text reaches memory

    def test_daily_signals(self):
        last = [{"id": "m1", "bucket": "reply", "thread_id": "c1", "received_at": "2026-03-02T08:00:00Z"},
                {"id": "m2", "bucket": "fyi", "thread_id": "c2", "received_at": "2026-03-02T08:00:00Z"},
                {"id": "m3", "bucket": "noise", "thread_id": "c3", "received_at": "2026-03-02T08:00:00Z"}]
        sent = [{"id": "x1", "conversation_id": "c1", "sent_at": "2026-03-02T10:00:00Z"},
                {"id": "x2", "conversation_id": "c2", "sent_at": "2026-03-02T10:00:00Z"},
                {"id": "x3", "conversation_id": "c3", "sent_at": "2026-03-01T10:00:00Z"},
                {"id": "x4", "conversation_id": "c1", "sent_at": "2026-03-02T11:00:00Z", "is_meeting_response": True}]
        drafts = [{"draft_id": "d1", "item_id": "m1", "thread_id": "c1", "state": "open"}]
        res = S.daily_signals(sent, last, drafts, {"x1": "Totally different words here now sent"}, {"d1": "Hi Pat, thanks, I will review it"})
        sig = {(s["id"], s["signal"]) for s in res["signals"]}
        self.assertIn(("m1", "replied"), sig)
        self.assertIn(("m2", "replied_not_proposed"), sig)
        self.assertNotIn(("m3", "replied_not_proposed"), sig)  # sent before the item arrived
        self.assertIn(("m1", "draft_edited_heavily"), sig)
        self.assertEqual(res["drafts"][0]["state"], "sent")

    def test_voice_update_only_on_drift(self):
        cur = [{"kind": "voice", "greeting": "Hi {first_name},", "sign_off": "Thanks, Alex", "median_words": 20}]
        same = [S.features(BODY_EN, ["Pat"])] * 5
        self.assertIsNone(S.update_voice(cur, same))
        drift = [S.features(BODY_NL, ["Sam"])] * 5
        self.assertEqual(S.update_voice(cur, drift)["greeting"], "Hoi {first_name},")


if __name__ == "__main__":
    unittest.main()
