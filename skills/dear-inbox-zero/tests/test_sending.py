"""What can reach other people: invite accepts are opt-in and off by default, and the docs say so."""
import json, os, re, shutil, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(SKILL))
ENGINE = os.path.join(SKILL, "engine", "dear_engine.py")


def read(rel, base=SKILL):
    with open(os.path.join(base, rel), encoding="utf-8") as fh:
        return fh.read()


def run(*args):
    r = subprocess.run([sys.executable, ENGINE, *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError(r.stderr or r.stdout)
    return r.stdout


class InviteAcceptSwitch(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.state = os.path.join(self.d, "state.json")
        store = os.path.join(self.d, "store")
        run("store-init", "--store", store, "--account", "work", "--now", "2026-03-02T08:00:00Z")
        run("store-load", "--store", store, "--out", self.state)

    def tearDown(self):
        shutil.rmtree(self.d)

    def profile(self):
        with open(self.state, encoding="utf-8") as fh:
            return json.load(fh)["head"]["profile"]

    def test_go_live_leaves_accepts_off_at_every_preset(self):
        for preset in ("low", "medium", "high"):
            out = json.loads(run("go-live", "--state", self.state, "--preset", preset))
            self.assertFalse(out["automation"]["invite_accept"], preset)
            self.assertFalse(self.profile()["invite_accept"], preset)

    def test_switch_on_and_off(self):
        run("go-live", "--state", self.state, "--invite-accept", "on")
        self.assertTrue(self.profile()["invite_accept"])
        out = json.loads(run("automation", "--state", self.state, "--preset", "high"))
        self.assertTrue(out["invite_accept"], "changing the preset keeps the user's choice")
        out = json.loads(run("automation", "--state", self.state, "--invite-accept", "off"))
        self.assertFalse(out["invite_accept"])
        self.assertIn("nothing is sent", out["notes"])


class HonestWording(unittest.TestCase):
    def description(self):
        front = read("SKILL.md").split("---")[1]
        return " ".join(front.split("description:", 1)[1].split("license:", 1)[0].split())

    def test_description_names_the_one_exception(self):
        d = self.description()
        self.assertIn("off by default", d)
        self.assertIn("sends the organiser an acceptance", d)
        self.assertNotRegex(d, r"Never sends,")  # "never sends" without saying what does go out

    def test_hard_rules_and_safety_say_what_reaches_people(self):
        self.assertIn("The one action that reaches another person is an invite accept", read("SKILL.md"))
        safety = read("policy/safety.md")
        self.assertIn("## What can reach other people", safety)
        self.assertIn("off by default", safety)
        self.assertNotIn("accept only under confirmed rules", safety)

    def test_no_doc_promises_accepts_from_day_one_without_the_switch(self):
        for rel, base in [("policy/buckets.md", SKILL), ("README.md", ROOT)]:
            for line in read(rel, base).splitlines():
                if re.search(r"accepts? invites under confirmed rules from day one", line):
                    self.fail(f"{rel}: {line}")

    def test_adapters_flag_that_accept_sends_a_response(self):
        for name in ("graph-mcp.md", "cowork.md"):
            row = [l for l in read(os.path.join("hosts", name)).splitlines() if l.startswith("| `cal.accept`")][0]
            self.assertIn("sends the organiser a response", row, name)


if __name__ == "__main__":
    unittest.main()
