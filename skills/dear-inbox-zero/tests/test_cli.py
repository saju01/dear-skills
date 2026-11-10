"""End-to-end run through the command line, synthetic data only."""
import json, os, shutil, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(os.path.dirname(HERE), "engine", "dear_engine.py")


def dump(obj, fh):
    with fh:
        json.dump(obj, fh)


def run(*args):
    r = subprocess.run([sys.executable, ENGINE, *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError(r.stderr or r.stdout)
    return r.stdout


class CliRun(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.s = os.path.join(self.d, "store")
        self.p = lambda n: os.path.join(self.d, n)

    def tearDown(self):
        shutil.rmtree(self.d)

    def test_setup_then_two_daily_runs(self):
        t0 = "2026-03-02T08:00:00Z"
        run("store-init", "--store", self.s, "--account", "work", "--channels", "mail,calendar,teams", "--now", t0)
        run("store-load", "--store", self.s, "--out", self.p("state.json"))
        dump([{"scope": "domain", "key": "newsletter.example.org", "bucket": "noise", "answer": "rule"}], open(self.p("ans.json"), "w"))
        run("add-facts", "--state", self.p("state.json"), "--answers", self.p("ans.json"), "--stage", "s3_done", "--now", t0)
        sent = [{"id": f"s{i}", "conversation_id": f"c{i}", "sent_at": "2026-02-1%dT09:00:00Z" % i,
                 "to": ["pat@example.com"], "in_reply_to_sender": "pat@example.com"} for i in range(4)]
        dump(sent, open(self.p("sent.json"), "w"))
        dump({"s1": "Hi Pat,\n\nThanks, will do.\n\nThanks, Alex"}, open(self.p("bodies.json"), "w"))
        out = json.loads(run("sent-study", "--state", self.p("state.json"), "--sent", self.p("sent.json"),
                             "--bodies", self.p("bodies.json"), "--now", t0))
        self.assertTrue(out["voice"])
        run("go-live", "--state", self.p("state.json"), "--now", t0)
        run("store-publish", "--store", self.s, "--state", self.p("state.json"), "--now", t0)
        # run 1
        run("store-load", "--store", self.s, "--out", self.p("state.json"))
        dump([], open(self.p("sig.json"), "w"))
        run("observe", "--state", self.p("state.json"), "--signals", self.p("sig.json"))
        shutil.copy(os.path.join(HERE, "fixtures", "alex_mail.json"), self.p("items.json"))
        run("classify", "--state", self.p("state.json"), "--items", self.p("items.json"), "--out", self.p("dec.json"))
        dump({"mail": "2026-03-02T08:00:00Z"}, open(self.p("cp.json"), "w"))
        run("learn", "--state", self.p("state.json"), "--decisions", self.p("dec.json"), "--checkpoints", self.p("cp.json"), "--now", t0)
        out = json.loads(run("store-publish", "--store", self.s, "--state", self.p("state.json"), "--now", t0))
        self.assertIn("index.json", out["files"])
        md = run("report", "--state", self.p("state.json"), "--decisions", self.p("dec.json"), "--now", t0)
        self.assertIn("Needs you", md)
        # run 2: the user replied to the newsletter twice -> proposal
        t1 = "2026-03-03T08:00:00Z"
        run("store-load", "--store", self.s, "--out", self.p("state.json"))
        dump([{"id": "m01", "signal": "replied"}, {"id": "m01", "signal": "flag_added"}], open(self.p("sig.json"), "w"))
        run("observe", "--state", self.p("state.json"), "--signals", self.p("sig.json"), "--now", t1)
        dump([], open(self.p("items.json"), "w"))
        run("classify", "--state", self.p("state.json"), "--items", self.p("items.json"), "--out", self.p("dec.json"))
        res = json.loads(run("learn", "--state", self.p("state.json"), "--decisions", self.p("dec.json"), "--now", t1))
        # a domain rule can still learn a narrower sender exception, asked once
        self.assertEqual(len(res["proposals"]), 1)
        with open(self.p("state.json")) as fh:
            st = json.load(fh)
        p = [x for x in st["head"]["proposals"] if x["state"] == "open"][0]
        self.assertEqual((p["scope"], p["key"], p["bucket"]), ("sender", "news@newsletter.example.org", "reply"))
        out = run("doctor", "--store", self.s)
        self.assertIn('"ok": true', out)


if __name__ == "__main__":
    unittest.main()
