"""Packaging: the lite and pro zips, the short description and one version everywhere."""
import hashlib, importlib.util, json, os, re, shutil, sys, tempfile, unittest, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(SKILL))
sys.path.insert(0, os.path.join(SKILL, "engine"))
from diz import doctor as D, __version__  # noqa: E402

BUILD = os.path.join(ROOT, "scripts", "build_release.py")
FOLDER = "dear-inbox-zero/"
PATH_REF = re.compile(r"`((?:lite|policy|hosts|setup|channels|learn|engine|config)/[\w./-]+\.(?:md|json|py))`")


def read(rel, base=SKILL):
    with open(os.path.join(base, rel), encoding="utf-8") as fh:
        return fh.read()


def load_builder():
    spec = importlib.util.spec_from_file_location("build_release", BUILD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@unittest.skipUnless(os.path.exists(BUILD), "repo checkout only")
class Zips(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.out = load_builder().build_all(cls.tmp)
        cls.zips = {z["edition"]: z for z in cls.out["zips"]}
        cls.names = {e: zipfile.ZipFile(z["zip"]).namelist() for e, z in cls.zips.items()}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def extract(self, edition):
        dest = tempfile.mkdtemp(dir=self.tmp)
        zipfile.ZipFile(self.zips[edition]["zip"]).extractall(dest)
        return os.path.join(dest, "dear-inbox-zero")

    def host(self, edition):
        return json.loads(zipfile.ZipFile(self.zips[edition]["zip"]).read(FOLDER + "config/host.json"))

    def test_two_editions_named_by_version(self):
        self.assertEqual(set(self.zips), {"lite", "pro"})
        for e, z in self.zips.items():
            self.assertEqual(os.path.basename(z["zip"]), f"dear-inbox-zero-{e}-v{__version__}.zip")

    def test_one_folder_with_skill_md_at_its_top(self):
        for e, names in self.names.items():
            self.assertTrue(all(n.startswith(FOLDER) for n in names), e)
            self.assertIn(FOLDER + "SKILL.md", names, e)
            self.assertIn(FOLDER + "SHA256SUMS", names, e)

    def test_no_tests_or_build_leftovers(self):
        for e, names in self.names.items():
            for n in names:
                self.assertNotIn("/tests/", n, e)
                self.assertNotIn("__pycache__", n, e)
                self.assertFalse(n.endswith(".pyc"), n)

    def test_lite_has_no_engine_and_says_lite(self):
        names = self.names["lite"]
        self.assertFalse([n for n in names if n.startswith(FOLDER + "engine/")])
        for pro_only in ("channels/calendar.md", "channels/teams.md", "setup/first-install.md", "learn/learning-loop.md"):
            self.assertNotIn(FOLDER + pro_only, names)
        self.assertEqual(self.host("lite"), {"host": "cowork", "adapter": "hosts/cowork.md", "mode": "lite"})

    def test_lite_has_every_file_its_guides_name(self):
        names = set(self.names["lite"])
        guides = ["SKILL.md", "lite/run.md", "lite/setup.md", "setup/install.md"]
        for g in guides:
            self.assertIn(FOLDER + g, names)
        for g in ("lite/run.md", "lite/setup.md"):
            for ref in PATH_REF.findall(read(g)):
                self.assertIn(FOLDER + ref, names, f"{g} names {ref}")
        for f in D.LITE_RUN_FILES + [self.host("lite")["adapter"]]:
            self.assertIn(FOLDER + f, names)

    def test_pro_is_the_whole_skill_and_passes_doctor(self):
        self.assertIn(FOLDER + "engine/dear_engine.py", self.names["pro"])
        self.assertEqual(self.host("pro"), {"host": "cowork", "adapter": "hosts/cowork.md", "mode": "auto"})
        res = D.run(self.extract("pro"))
        self.assertTrue(res["ok"], res["errors"])

    def test_sha256sums_match_every_file(self):
        for e, z in self.zips.items():
            zf = zipfile.ZipFile(z["zip"])
            sums = dict(reversed(line.split("  ", 1)) for line in zf.read(FOLDER + "SHA256SUMS").decode().splitlines())
            files = [n for n in zf.namelist() if n != FOLDER + "SHA256SUMS"]
            self.assertEqual(set(sums), set(files), e)
            for n in files:
                self.assertEqual(sums[n], hashlib.sha256(zf.read(n)).hexdigest(), n)

    def test_reproducible(self):
        again = load_builder().build_all(tempfile.mkdtemp(dir=self.tmp))
        self.assertEqual([z["sha256"] for z in again["zips"]], [z["sha256"] for z in self.out["zips"]])


class Description(unittest.TestCase):
    def test_short_and_honest(self):
        desc = D.skill_description(read("SKILL.md").split("---")[1])
        self.assertLessEqual(len(desc), 300)
        self.assertTrue(desc.startswith("Inbox-zero"), desc)
        self.assertIn('"dear-inbox-zero"', desc)
        self.assertIn("off by default", desc)

    def test_doctor_fails_a_long_description_or_a_version_mismatch(self):
        tmp = tempfile.mkdtemp()
        try:
            skill = os.path.join(tmp, "dear-inbox-zero")
            shutil.copytree(SKILL, skill, ignore=shutil.ignore_patterns("tests", "__pycache__"))
            path = os.path.join(skill, "SKILL.md")
            text = read("SKILL.md")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text.replace("Inbox-zero for", "Inbox-zero " + "very " * 60 + "for").replace(
                    f'version: "{__version__}"', 'version: "9.9.9"'))
            errs = D.run(skill)["errors"]
            self.assertTrue(any("description is" in e for e in errs), errs)
            self.assertTrue(any("9.9.9" in e for e in errs), errs)
        finally:
            shutil.rmtree(tmp)

    def test_folded_and_plain_descriptions_parse(self):
        self.assertEqual(D.skill_description("name: x\ndescription: >-\n  One two\n  three.\nlicense: y\n"), "One two three.")
        self.assertEqual(D.skill_description("name: x\ndescription: One line.\nlicense: y\n"), "One line.")


@unittest.skipUnless(os.path.exists(os.path.join(ROOT, "install.json")), "repo checkout only")
class OneVersion(unittest.TestCase):
    def test_skill_engine_manifest_and_changelog_agree(self):
        v = re.search(r'version:\s*"([^"]+)"', read("SKILL.md")).group(1)
        self.assertEqual(v, __version__)
        with open(os.path.join(ROOT, "install.json"), encoding="utf-8") as fh:
            skill = [s for s in json.load(fh)["skills"] if s["name"] == "dear-inbox-zero"][0]
        self.assertEqual(skill["version"], v)
        self.assertIn(f"v{v}", skill["status"])
        first = re.search(r"^## (\S+)", read("CHANGELOG.md"), re.M).group(1)
        self.assertEqual(first, v)

    def test_readme_before_and_after_is_fictional(self):
        readme = read("README.md", ROOT)
        section = readme.split("## Before and after", 1)[1].split("\n## ", 1)[0]
        self.assertIn("fictional", section)
        for domain in re.findall(r"[\w.-]+\.(?:com|org|net|nl|io)\b", section):
            self.assertRegex(domain, r"(^|\.)example\.(com|org|net)$")
        self.assertIn("Nothing was sent", section)


if __name__ == "__main__":
    unittest.main()
