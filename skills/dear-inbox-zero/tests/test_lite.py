"""Lite mode (mail only, no Python): the guides stay consistent, small and inside the safety rules."""
import json, os, re, shutil, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(SKILL))
sys.path.insert(0, os.path.join(SKILL, "engine"))
from diz import doctor as D, CATEGORY  # noqa: E402


def read(rel):
    with open(os.path.join(SKILL, rel), encoding="utf-8") as fh:
        return fh.read()


LITE_FILES = ("lite/run.md", "lite/setup.md")
OP = re.compile(r"`((?:me|ask|schedule|run_python)|(?:mail|cal|teams|store)\.[a-z_]+)`")


class LiteGuides(unittest.TestCase):
    def test_lite_files_are_required(self):
        for f in LITE_FILES:
            self.assertIn(f, D.REQUIRED_FILES)
            self.assertTrue(os.path.exists(os.path.join(SKILL, f)), f)

    def test_lite_uses_only_lite_operations(self):
        allowed = set(D.LITE_OPS) | {"schedule"}
        for f in LITE_FILES:
            used = set(OP.findall(read(f)))
            self.assertTrue(used, f)
            self.assertEqual(used - allowed, set(), f"{f} uses non-lite operations")
            self.assertFalse(used & set(D.FORBIDDEN_OPS), f)

    def test_lite_needs_only_mail_scopes(self):
        text = read("lite/run.md")
        perms = text.split("## Permissions", 1)[1].split("\n## ", 1)[0]
        needed = perms.split("Lite never needs", 1)[0]
        scopes = set(re.findall(r"`([A-Z][A-Za-z]+\.[A-Za-z.*]+)`", needed))
        self.assertEqual(scopes, {"User.Read", "Mail.ReadWrite", "Files.ReadWrite"})
        never = perms.split("Lite never needs", 1)[1]
        for scope in ("Mail.Send", "Calendars.", "Chat.", "ChannelMessage.", "MailboxSettings."):
            self.assertIn(scope, never)

    def test_lite_lists_every_lite_operation(self):
        text = read("lite/run.md").split("## Memory", 1)[0]
        for op in D.LITE_OPS:
            self.assertIn(f"`{op}`", text, op)

    def test_memory_example_is_valid_and_fictional(self):
        text = read("lite/run.md")
        block = re.search(r"```json\n(.*?)```", text, re.S).group(1)
        mem = json.loads(block)
        self.assertEqual(mem["format"], "dear-inbox-zero/lite@1")
        for key in ("version", "account", "tz", "preset", "stage", "checkpoint", "rules", "proposals",
                    "paused", "vip", "personal", "voice", "last_run"):
            self.assertIn(key, mem)
        self.assertLess(len(block.encode()), 8 * 1024)
        for r in mem["rules"]:
            self.assertIn(r["scope"], ("series", "sender", "domain"))
            self.assertIn(r["bucket"], tuple(CATEGORY))
        for addr in re.findall(r"[\w.+-]+@([\w-]+\.[\w.-]+)", block) + mem["own_domains"] + mem["personal"]:
            self.assertRegex(addr, r"(^|\.)example\.(com|org|net)$")

    def test_lite_presets_exist_in_policy(self):
        buckets = read("policy/buckets.md")
        for preset in ("Low", "Medium"):
            self.assertIn(preset, buckets)
        self.assertIn("lite has no High", read("lite/run.md"))

    def test_lite_run_fits_the_budget(self):
        res = D.run(SKILL)
        self.assertTrue(res["ok"], res["errors"])
        self.assertLessEqual(res["info"]["lite_run_guides_bytes"], D.BUDGET["lite_run_guides"])


class Routing(unittest.TestCase):
    def test_skill_routes_to_lite_without_asking(self):
        text = read("SKILL.md")
        self.assertIn("lite/run.md", text)
        self.assertIn("lite/setup.md", text)
        self.assertIn("detect, don't ask", text)
        self.assertIn("run_python", text)

    def test_host_config_mode(self):
        cfg = json.loads(read("config/host.json"))
        self.assertIn(cfg.get("mode"), D.MODES)

    def test_manifest_describes_both_modes(self):
        with open(os.path.join(ROOT, "install.json"), encoding="utf-8") as fh:
            sk = json.load(fh)["skills"][0]
        self.assertEqual(sk["modes"]["lite"]["graph_scopes"], ["User.Read", "Mail.ReadWrite"])
        self.assertFalse(sk["modes"]["lite"]["python"])
        for g in sk["modes"]["lite"]["guides"]:
            self.assertTrue(os.path.exists(os.path.join(SKILL, g)), g)


class LiteAdapterDoctor(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir)

    def lite_adapter(self, drop_mail=False):
        rows = []
        for op in D.REQUIRED_OPS:
            tool = f"Tool{op.replace('.', '_')}" if op in D.LITE_OPS else ""
            if drop_mail and op == "mail.list":
                tool = ""
            rows.append(f"| `{op}` | {tool} | |")
        path = os.path.join(self.dir, "lite-host.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("# Adapter: lite host\n\n<!-- adapter-mode: lite -->\n\n<!-- adapter-ops:begin -->\n"
                     "| Operation | Tool | Notes |\n|---|---|---|\n" + "\n".join(rows) + "\n<!-- adapter-ops:end -->\n")
        return path

    def test_lite_adapter_may_leave_pro_operations_empty(self):
        self.assertEqual(D.check_adapter(self.lite_adapter()), [])

    def test_lite_adapter_must_map_mail(self):
        errs = D.check_adapter(self.lite_adapter(drop_mail=True))
        self.assertTrue(any("mail.list" in e for e in errs), errs)

    def test_full_adapter_still_needs_every_operation(self):
        path = self.lite_adapter()
        with open(path, encoding="utf-8") as fh:
            text = fh.read().replace("<!-- adapter-mode: lite -->", "")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        self.assertTrue(any("cal.view" in e for e in D.check_adapter(path)))

    def test_doctor_warns_about_lite_only_adapters(self):
        skill = os.path.join(self.dir, "skill")
        shutil.copytree(SKILL, skill, ignore=shutil.ignore_patterns("__pycache__", "tests"))
        shutil.copy(self.lite_adapter(), os.path.join(skill, "hosts", "lite-host.md"))
        res = D.run(skill)
        self.assertTrue(res["ok"], res["errors"])
        self.assertTrue(any("lite-only" in w for w in res["warnings"]))

    def test_bad_mode_is_an_error(self):
        skill = os.path.join(self.dir, "skill")
        shutil.copytree(SKILL, skill, ignore=shutil.ignore_patterns("__pycache__", "tests"))
        with open(os.path.join(skill, "config", "host.json"), "w", encoding="utf-8") as fh:
            json.dump({"host": "generic", "adapter": "hosts/graph-mcp.md", "mode": "turbo"}, fh)
        self.assertFalse(D.run(skill)["ok"])


if __name__ == "__main__":
    unittest.main()
