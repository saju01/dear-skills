"""setup/permissions.md: every scope the adapters ask for is explained, lite needs no admin consent, nothing can send."""
import json, os, re, shutil, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(SKILL))
sys.path.insert(0, os.path.join(SKILL, "engine"))
from diz import doctor as D  # noqa: E402

SCOPE = re.compile(r"`([A-Z][A-Za-z-]+\.[A-Za-z.]+)`")


def read(rel, base=SKILL):
    with open(os.path.join(base, rel), encoding="utf-8") as fh:
        return fh.read()


def table():
    return D.scope_table(read("setup/permissions.md"))


def manifest_skill():
    with open(os.path.join(ROOT, "install.json"), encoding="utf-8") as fh:
        return json.load(fh)["skills"][0]


class Guide(unittest.TestCase):
    def test_required_and_clean(self):
        self.assertIn("setup/permissions.md", D.REQUIRED_FILES)
        self.assertEqual(D.check_permissions(os.path.join(SKILL, "setup", "permissions.md")), [])

    def test_lite_needs_no_admin_consent(self):
        lite = {s: r for s, r in table().items() if r["lite"] != "no"}
        self.assertEqual(set(lite), {"User.Read", "Mail.ReadWrite", "Files.ReadWrite"})
        for scope, r in lite.items():
            self.assertEqual(r["admin"], "No", scope)

    def test_only_channels_need_admin_consent(self):
        self.assertEqual({s for s, r in table().items() if r["admin"] == "Yes"}, {"ChannelMessage.Read.All"})
        self.assertEqual(table()["ChannelMessage.Read.All"]["pro"], "optional")

    def test_calendar_write_only_for_invite_accepts(self):
        self.assertIn("invite accepts", table()["Calendars.ReadWrite"]["pro"])
        self.assertEqual(table()["Calendars.Read"]["pro"], "yes")

    def test_every_operation_has_a_scope(self):
        text = read("setup/permissions.md").split("<!-- scopes:begin -->")[1].split("<!-- scopes:end -->")[0]
        for op in D.REQUIRED_OPS:
            if op.startswith(("mail.", "cal.", "teams.", "store.")) or op == "me":
                self.assertIn(f"`{op}`", text, op)

    def test_nothing_that_sends_is_needed(self):
        for scope in D.NEVER_GRANT:
            self.assertNotIn(scope, table())
        never = read("setup/permissions.md").split("<!-- never-grant:begin -->")[1]
        for scope in ("Mail.Send", "ChatMessage.Send", "ChannelMessage.Send"):
            self.assertIn(f"`{scope}`", never)


class Consistency(unittest.TestCase):
    def granted(self, line):
        """Scopes a sentence asks for, ignoring the ones it says not to grant."""
        return set(SCOPE.findall(re.split(r"\*\*Do not grant\*\*", line)[0]))

    def test_graph_adapter_asks_only_for_listed_scopes(self):
        line = [l for l in read("hosts/graph-mcp.md").splitlines() if l.startswith("Delegated scopes")][0]
        asked = self.granted(line)
        self.assertTrue(asked)
        self.assertEqual(asked - set(table()), set())
        self.assertIn("MailboxSettings.ReadWrite", asked, "me reads mailbox settings")

    def test_lite_guide_matches(self):
        perms = read("lite/run.md").split("## Permissions", 1)[1].split("Lite never needs", 1)[0]
        lite = {s for s, r in table().items() if r["lite"] != "no"}
        self.assertEqual(set(SCOPE.findall(perms)), lite)

    def test_manifest_matches(self):
        modes = manifest_skill()["modes"]
        t = table()
        self.assertEqual(set(modes["lite"]["graph_scopes"]), {s for s, r in t.items() if r["lite"] == "yes"})
        self.assertEqual(set(modes["lite"]["optional_graph_scopes"]), {s for s, r in t.items() if r["lite"] == "optional"})
        self.assertEqual(set(modes["pro"]["graph_scopes"]), {s for s, r in t.items() if r["pro"] == "yes"})
        self.assertEqual(set(modes["pro"]["optional_graph_scopes"]), {s for s, r in t.items() if r["pro"] not in ("yes", "no")})
        self.assertEqual(set(manifest_skill()["requires"]["forbidden_graph_scopes"]), set(D.NEVER_GRANT))

    def test_copilot_guide_lists_no_unknown_scope(self):
        text = read("docs/hosts/github-copilot.md", ROOT).split("## Permissions and safety", 1)[1].split("\n## ", 1)[0]
        asked = self.granted(text.split("Do not grant", 1)[0])
        self.assertEqual(asked - set(table()), set())


class DoctorCatchesRegressions(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.skill = os.path.join(self.dir, "skill")
        shutil.copytree(SKILL, self.skill, ignore=shutil.ignore_patterns("__pycache__", "tests"))
        self.path = os.path.join(self.skill, "setup", "permissions.md")

    def tearDown(self):
        shutil.rmtree(self.dir)

    def edit(self, old, new):
        with open(self.path, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn(old, text)
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write(text.replace(old, new))
        return D.run(self.skill)

    def test_lite_scope_needing_admin_fails(self):
        res = self.edit("| Teams channel threads and channel mentions | `teams.needs_response`, `teams.thread` | **Yes** | no |",
                        "| Teams channel threads and channel mentions | `teams.needs_response`, `teams.thread` | **Yes** | optional |")
        self.assertFalse(res["ok"])
        self.assertTrue(any("admin consent" in e for e in res["errors"]), res["errors"])

    def test_send_scope_listed_as_needed_fails(self):
        res = self.edit("<!-- scopes:end -->", "| `Mail.Send` | send | `mail.send` | No | no | yes |\n<!-- scopes:end -->")
        self.assertFalse(res["ok"])
        self.assertTrue(any("Mail.Send" in e for e in res["errors"]), res["errors"])

    def test_missing_table_fails(self):
        res = self.edit("<!-- scopes:begin -->", "")
        self.assertFalse(res["ok"])


if __name__ == "__main__":
    unittest.main()
