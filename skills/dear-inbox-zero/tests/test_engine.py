"""Unit tests on synthetic data only (fictional persona Alex, example.com / example.org)."""
import json, os, shutil, sys, tempfile, unittest
from datetime import timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SKILL, "engine"))
from diz import store, classify as C, learn as L, ledger, report as R, doctor as D, FORBIDDEN_ACTIONS  # noqa: E402
from diz.util import parse_ts, iso, series_key  # noqa: E402

NOW = parse_ts("2026-03-02T08:00:00Z")  # a Monday


def fixture(name):
    with open(os.path.join(HERE, "fixtures", name), encoding="utf-8") as f:
        return json.load(f)


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        store.init(self.dir, "work", "Europe/Amsterdam", ["mail", "calendar", "teams"], NOW)
        self.st = store.load_state(self.dir)

    def tearDown(self):
        shutil.rmtree(self.dir)

    def rule(self, scope, key, bucket, origin="explicit", conf=1.0, **kw):
        L.apply_answers(self.st, [{"scope": scope, "key": key, "bucket": bucket, "answer": "rule", **kw}], NOW) if origin == "explicit" \
            else self.st["new_facts"].append({"kind": "rule", "scope": scope, "key": key, "bucket": bucket, "origin": origin, "confidence": conf})
        self.republish()

    def republish(self, now=NOW):
        store.publish(self.dir, self.st, now)
        self.st = store.load_state(self.dir)

    def live(self, **levels):
        L.go_live(self.st, NOW, "low")
        for b, l in levels.items():
            self.st["head"]["autonomy"][b]["level"] = l


class StoreTests(Base):
    def test_roundtrip_and_parent_chain(self):
        first = self.st["head_sha"]
        self.rule("sender", "news@example.org", "noise")
        self.assertNotEqual(first, self.st["head_sha"])
        self.assertEqual(self.st["head"]["parent"], first)
        self.assertEqual(len(self.st["facts"]), 1)

    def test_hash_mismatch_is_refused(self):
        hdir = os.path.join(self.dir, "head")
        name = os.listdir(hdir)[0]
        with open(os.path.join(hdir, name)) as fh:
            doc = json.load(fh)
        doc["payload"]["account"] = "tampered"
        with open(os.path.join(hdir, name), "w") as fh:
            json.dump(doc, fh)
        with self.assertRaises(store.StoreError):
            store.load_state(self.dir)

    def test_init_never_overwrites(self):
        with self.assertRaises(store.StoreError):
            store.init(self.dir, "work", "UTC", ["mail"], NOW)

    def test_stale_index_is_rebuilt(self):
        self.rule("sender", "news@example.org", "noise")
        os.remove(os.path.join(self.dir, "index.json"))
        st = store.load_state(self.dir)
        self.assertTrue(st["index_rebuilt"])
        self.assertEqual(len(st["facts"]), 1)

    def test_supersede_replaces_rule(self):
        self.rule("sender", "news@example.org", "noise")
        self.rule("sender", "news@example.org", "fyi")
        rules = [f for f in self.st["facts"] if f["kind"] == "rule"]
        self.assertEqual([r["bucket"] for r in rules], ["fyi"])


class ClassifyTests(Base):
    def test_fixture_buckets(self):
        self.rule("domain", "newsletter.example.org", "noise")
        self.rule("series", series_key("Weekly digest 12"), "fyi")
        self.rule("sender", "mum@example.net", "personal")
        L.apply_answers(self.st, [{"person": "boss@example.com", "vip": True}], NOW)
        self.live(noise=2, fyi=2, reply=2)
        out = C.classify(self.st, fixture("alex_mail.json"))
        got = {d["id"]: d["bucket"] for d in out["decisions"]}
        exp = fixture("alex_expected.json")
        self.assertEqual(got, exp)

    def test_vip_beats_noise_series_unless_beats_vip(self):
        self.rule("series", series_key("Team broadcast"), "noise")
        L.apply_answers(self.st, [{"person": "boss@example.com", "vip": True}], NOW)
        it = {"id": "1", "sender": "boss@example.com", "subject": "Team broadcast"}
        self.assertEqual(C.classify(self.st, [it])["decisions"][0]["bucket"], "reply")
        self.rule("series", series_key("Team broadcast"), "noise", beats_vip=True)
        self.assertEqual(C.classify(self.st, [it])["decisions"][0]["bucket"], "noise")

    def test_guard_lifts_noise(self):
        self.rule("domain", "alerts.example.org", "noise")
        it = {"id": "1", "sender": "it@alerts.example.org", "subject": "Unusual sign-in to your account"}
        self.assertEqual(C.classify(self.st, [it])["decisions"][0]["bucket"], "fyi")

    def test_inferred_threshold(self):
        self.rule("sender", "a@example.org", "noise", origin="inferred", conf=0.6)
        self.rule("sender", "b@example.org", "noise", origin="inferred", conf=0.8)
        d = C.classify(self.st, [{"id": "1", "sender": "a@example.org", "subject": "x"},
                                 {"id": "2", "sender": "b@example.org", "subject": "y"}])["decisions"]
        self.assertEqual([x["bucket"] for x in d], ["unknown", "noise"])

    def test_actions_respect_levels_and_safety(self):
        self.rule("sender", "news@example.org", "noise")
        self.rule("sender", "inferred@example.org", "noise", origin="inferred", conf=0.9)
        items = [{"id": "1", "sender": "news@example.org", "subject": "n"},
                 {"id": "2", "sender": "inferred@example.org", "subject": "m"},
                 {"id": "3", "sender": "colleague@example.com", "subject": "Can you review?", "to_me": True, "has_question": True}]
        self.live()  # level 1
        ops = {d["id"]: [a["op"] for a in d["actions"]] for d in C.classify(self.st, items)["decisions"]}
        self.assertEqual(ops, {"1": ["tag"], "2": ["tag"], "3": ["tag", "draft"]})
        self.live(noise=2, reply=2)
        ops = {d["id"]: [a["op"] for a in d["actions"]] for d in C.classify(self.st, items)["decisions"]}
        self.assertEqual(ops, {"1": ["tag", "mark_read"], "2": ["tag"], "3": ["tag", "draft", "flag"]})
        for d in C.classify(self.st, items)["decisions"]:
            for a in d["actions"]:
                self.assertNotIn(a["op"], FORBIDDEN_ACTIONS)

    def test_dry_run_plans_nothing(self):
        self.live(noise=2)
        self.rule("sender", "news@example.org", "noise")
        out = C.classify(self.st, [{"id": "1", "sender": "news@example.org", "subject": "n"}], dry_run=True)
        self.assertEqual(out["decisions"][0]["actions"], [])

    def test_teams_needs_response_gets_suggestion_only(self):
        self.live()
        d = C.classify(self.st, [{"id": "t1", "channel": "teams", "sender": "pat@example.com", "subject": "Project chat",
                                  "has_question": True}])["decisions"][0]
        self.assertEqual((d["bucket"], [a["op"] for a in d["actions"]]), ("reply", ["suggest_reply"]))


class CalendarTests(Base):
    CAL = [{"event_id": "e1", "subject": "Customer review", "start": "2026-03-03T09:00:00Z", "end": "2026-03-03T10:00:00Z",
            "my_response": "accepted", "external": True}]

    def inv(self, **kw):
        it = {"id": "i1", "channel": "invite", "event_id": "e9", "sender": "org@example.com", "subject": "Planning",
              "start": "2026-03-03T11:00:00Z", "end": "2026-03-03T12:00:00Z", "invitees": 6}
        it.update(kw)
        return C.classify(self.st, [it], self.CAL)["decisions"][0]

    def test_default_is_ask(self):
        self.live()
        self.assertEqual(self.inv()["recommendation"], "ask")

    def test_broadcast_is_fyi(self):
        self.live()
        self.assertEqual(self.inv(invitees=400)["recommendation"], "fyi")

    def test_clash_is_flagged_not_answered(self):
        self.live(calendar=3)
        self.rule("sender", "org@example.com", "accept")
        d = self.inv(start="2026-03-03T09:30:00Z", end="2026-03-03T10:30:00Z")
        self.assertEqual((d["recommendation"], [a["op"] for a in d["actions"]]), ("ask", ["flag"]))
        self.assertEqual(d["clashes"][0]["subject"], "Customer review")

    def test_accept_only_with_confirmed_rule_and_level3(self):
        self.live()
        self.rule("sender", "org@example.com", "accept")
        self.assertEqual(self.inv()["recommendation"], "ask")
        self.st["head"]["autonomy"]["calendar"]["level"] = 3
        d = self.inv()
        self.assertEqual(d["recommendation"], "accept")
        self.assertTrue(d["actions"][0]["occurrence_only"])


class LearnTests(Base):
    def run_once(self, items, signals, now):
        L.observe(self.st, signals, now)
        dec = C.classify(self.st, items)
        L.propose(self.st, now)
        L.expire(self.st, now)
        L.update_autonomy(self.st, now)
        ledger.update(self.st["head"], dec["decisions"], self.st["head"]["signals"], now)
        self.st["head"]["last_run"] = {"at": iso(now), "decisions": dec["decisions"]}
        return dec

    def test_two_overrides_create_proposal_then_confirm(self):
        self.live()
        self.rule("sender", "promo@example.org", "noise", origin="inferred", conf=0.9)
        items = [{"id": "m1", "sender": "promo@example.org", "subject": "Offer A"},
                 {"id": "m2", "sender": "promo@example.org", "subject": "Offer B"}]
        self.run_once(items, [], NOW)
        self.run_once([], [{"id": "m1", "signal": "replied"}, {"id": "m2", "signal": "flag_added"}], NOW + timedelta(days=1))
        props = [p for p in self.st["head"]["proposals"] if p["state"] == "open"]
        self.assertEqual(len(props), 1)
        self.assertEqual(props[0]["bucket"], "reply")
        L.apply_answers(self.st, [{"proposal_id": props[0]["id"], "answer": "confirm"}], NOW + timedelta(days=1))
        self.republish(NOW + timedelta(days=1))
        d = C.classify(self.st, [{"id": "m3", "sender": "promo@example.org", "subject": "Offer C"}])["decisions"][0]
        self.assertEqual(d["bucket"], "reply")

    def test_signals_without_direction_do_not_crash(self):
        self.live()
        self.st["head"]["last_run"] = {"decisions": [{"id": "x", "channel": "mail", "bucket": "fyi", "sender": "a@example.org", "series": "s"}]}
        L.observe(self.st, [{"id": "x", "signal": "draft_edited_heavily"}, {"id": "x", "signal": "something_new"}], NOW)
        self.assertEqual(L.propose(self.st, NOW)["created"], [])

    def test_mixed_directions_are_inconsistent(self):
        self.live()
        self.st["head"]["last_run"] = {"decisions": [
            {"id": "a", "channel": "mail", "bucket": "noise", "sender": "x@example.org", "series": "s1"},
            {"id": "b", "channel": "mail", "bucket": "noise", "sender": "x@example.org", "series": "s1"}]}
        L.observe(self.st, [{"id": "a", "signal": "replied"}, {"id": "b", "signal": "tag_removed"}], NOW)
        res = L.propose(self.st, NOW)
        self.assertEqual(res["created"], [])
        self.assertEqual(len(res["inconsistent"]), 1)

    def test_proposal_expires(self):
        self.live()
        self.st["head"]["last_run"] = {"decisions": [
            {"id": "a", "channel": "mail", "bucket": "noise", "sender": "x@example.org", "series": "s1"},
            {"id": "b", "channel": "mail", "bucket": "noise", "sender": "x@example.org", "series": "s1"}]}
        L.observe(self.st, [{"id": "a", "signal": "replied"}, {"id": "b", "signal": "replied"}], NOW)
        L.propose(self.st, NOW)
        self.republish()
        res = L.expire(self.st, NOW + timedelta(days=15))
        self.assertEqual(len(res["expired"]), 1)

    def test_rejected_proposal_is_blocked(self):
        self.live()
        dec = [{"id": "a", "channel": "mail", "bucket": "noise", "sender": "x@example.org", "series": "s1"},
               {"id": "b", "channel": "mail", "bucket": "noise", "sender": "x@example.org", "series": "s1"}]
        self.st["head"]["last_run"] = {"decisions": dec}
        L.observe(self.st, [{"id": "a", "signal": "replied"}, {"id": "b", "signal": "replied"}], NOW)
        p = L.propose(self.st, NOW)["created"][0]
        L.apply_answers(self.st, [{"proposal_id": p["id"], "answer": "reject"}], NOW)
        self.republish()
        self.st["head"]["signals"] = []
        self.st["head"]["last_run"] = {"decisions": dec}
        L.observe(self.st, [{"id": "a", "signal": "replied"}, {"id": "b", "signal": "replied"}], NOW)
        self.assertEqual(L.propose(self.st, NOW)["created"], [])

    def test_autonomy_promotion_and_demotion(self):
        self.live()
        self.st["head"]["profile"]["preset"] = "medium"  # ceiling 2 for noise
        a = self.st["head"]["autonomy"]["noise"]
        for i in range(5):
            self.st["head"]["_run_stats"] = {"noise": {"decisions": 8, "overrides": 0, "wrong": 0}}
            L.update_autonomy(self.st, NOW + timedelta(days=i))
        self.assertEqual(a["level"], 2)
        self.st["head"]["_run_stats"] = {"noise": {"decisions": 8, "overrides": 1, "wrong": 1}}
        L.update_autonomy(self.st, NOW + timedelta(days=6))
        self.assertEqual(a["level"], 1)

    def test_ledger_working_days(self):
        self.live()
        dec = C.classify(self.st, [{"id": "q", "sender": "pat@example.com", "subject": "Question", "to_me": True,
                                    "has_question": True, "received_at": "2026-02-26T09:00:00Z"}])
        ledger.update(self.st["head"], dec["decisions"], [], NOW)
        aged = ledger.aged(self.st["head"], NOW)
        self.assertEqual(aged[0]["working_days"], 2)


class PresetTests(Base):
    def test_medium_is_default_and_capped(self):
        self.st["head"]["profile"].pop("preset", None)
        levels = L.go_live(self.st, NOW)
        self.assertEqual(levels, {"noise": 2, "fyi": 2, "reply": 2, "calendar": 1})
        self.assertEqual(self.st["head"]["profile"]["preset"], "medium")
        a = self.st["head"]["autonomy"]["noise"]
        for i in range(6):
            self.st["head"]["_run_stats"] = {"noise": {"decisions": 8, "overrides": 0, "wrong": 0}}
            L.update_autonomy(self.st, NOW + timedelta(days=i))
        self.assertEqual(a["level"], 2)  # capped

    def test_low_and_high(self):
        self.assertEqual(L.go_live(self.st, NOW, "low"), {"noise": 1, "fyi": 1, "reply": 1, "calendar": 1})
        self.assertEqual(L.go_live(self.st, NOW, "high")["calendar"], 3)
        with self.assertRaises(ValueError):
            L.go_live(self.st, NOW, "max")

    def test_automation_plan_follows_working_hours(self):
        self.st["head"]["profile"]["working_hours"] = [8, 17]
        plan = L.automation_plan(self.st["head"]["profile"])
        self.assertEqual(plan["preset"], "medium")
        self.assertEqual(plan["jobs"][0]["cron"], "30 8 * * 1-5")
        self.assertEqual(plan["jobs"][1]["prompt"], "dear-inbox-zero learn")


class SetupTests(Base):
    def test_study_and_calibration(self):
        obs = [{"kind": "replied_to", "key": "pat@example.com", "count": 7},
               {"kind": "ignored", "scope": "domain", "key": "promo.example.org", "count": 12},
               {"kind": "accepted", "key": "org@example.com", "count": 4}]
        made = L.study(self.st, obs, NOW)
        self.assertEqual(len(made), 3)
        self.republish()
        qs = L.calibration_questions(self.st, [{"key": "new@example.org", "count": 30}])
        self.assertEqual(qs[0]["key"], "new@example.org")


class DoctorAndReportTests(Base):
    def test_doctor_passes_on_repo(self):
        res = D.run(SKILL, self.dir)
        self.assertTrue(res["ok"], res["errors"])

    def test_doctor_catches_forbidden_mapping(self):
        bad = os.path.join(self.dir, "bad.md")
        with open(os.path.join(SKILL, "hosts", "graph-mcp.md")) as fh:
            text = fh.read()
        text = text.replace("`PATCH /me/messages/{id}` `{isRead: true}`", "`ForwardMessage`")
        with open(bad, "w") as fh:
            fh.write(text)
        self.assertTrue(any("forbidden" in e for e in D.check_adapter(bad)))

    def test_report_renders(self):
        self.live()
        dec = C.classify(self.st, fixture("alex_mail.json"))
        md = R.render(self.st, dec, NOW)
        self.assertIn("dear-inbox-zero", md)
        self.assertNotIn("mum@example.net", md.split("Personal:")[0])


if __name__ == "__main__":
    unittest.main()
