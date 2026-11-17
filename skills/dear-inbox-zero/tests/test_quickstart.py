"""`quickstart`: one command, a throwaway store, a dry run over fictional demo data, a sample report."""
import json, os, re, shutil, subprocess, sys, tempfile, time, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(SKILL))
ENGINE = os.path.join(SKILL, "engine", "dear_engine.py")
ADDR = re.compile(r"[\w.+-]+@([\w-]+\.[\w.-]+)")


def quickstart(*args):
    return subprocess.run([sys.executable, ENGINE, "quickstart", *args], capture_output=True, text=True)


class Quickstart(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.d)

    def test_one_command_gives_a_report_and_a_healthy_store(self):
        t = time.monotonic()
        r = quickstart("--dir", self.d)
        self.assertLess(time.monotonic() - t, 30)
        self.assertEqual(r.returncode, 0, r.stderr)
        for heading in ("dry run: nothing changed", "## Decide today", "## Needs you", "## FYI", "## I noticed",
                        "## New senders", "Nothing was read, changed or sent", "Store check: ok", "dear-inbox-zero setup"):
            self.assertIn(heading, r.stdout)
        self.assertTrue(os.listdir(os.path.join(self.d, "store", "head")))
        with open(os.path.join(self.d, "report.md"), encoding="utf-8") as fh:
            self.assertIn("## Needs you", fh.read())

    def test_dry_run_plans_no_action(self):
        self.assertEqual(quickstart("--dir", self.d).returncode, 0)
        with open(os.path.join(self.d, "decisions.json"), encoding="utf-8") as fh:
            dec = json.load(fh)
        self.assertTrue(dec["dry_run"])
        self.assertTrue(dec["decisions"])
        for d in dec["decisions"]:
            self.assertEqual(d.get("actions"), [], d["id"])

    def test_invite_accepts_stay_off(self):
        out = quickstart("--dir", self.d, "--preset", "high").stdout
        self.assertIn("accepting for you is off", out)
        self.assertNotIn("Accepted under your rule", out)

    def test_never_writes_over_a_store(self):
        self.assertEqual(quickstart("--dir", self.d).returncode, 0)
        r = quickstart("--dir", self.d)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not empty", r.stderr)

    def test_default_folder_is_new(self):
        r = quickstart()
        self.assertEqual(r.returncode, 0, r.stderr)
        store = re.search(r"Sample store: (.+)", r.stdout).group(1).strip()
        try:
            self.assertTrue(os.path.isdir(store))
            self.assertFalse(store.startswith(SKILL), "the demo store must not land inside the skill")
        finally:
            shutil.rmtree(os.path.dirname(store))

    def test_example_report_is_the_quickstart_report(self):
        self.assertEqual(quickstart("--dir", self.d).returncode, 0)
        with open(os.path.join(self.d, "report.md"), encoding="utf-8") as a, \
                open(os.path.join(ROOT, "examples", "persona-alex", "report.md"), encoding="utf-8") as b:
            self.assertEqual(a.read(), b.read(), "regenerate examples/persona-alex/report.md with quickstart")


class DemoData(unittest.TestCase):
    def test_demo_is_fictional(self):
        demo = os.path.join(SKILL, "demo")
        for name in sorted(os.listdir(demo)):
            with open(os.path.join(demo, name), encoding="utf-8") as fh:
                for domain in ADDR.findall(fh.read()):
                    self.assertRegex(domain, r"(^|\.)example\.(com|org|net)$", name)


if __name__ == "__main__":
    unittest.main()
