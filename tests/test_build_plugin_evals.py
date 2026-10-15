from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_plugin_evals as staging  # noqa: E402
import package_skills  # noqa: E402

HAVE_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


class StagingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.directory)
        self.out = self.directory / "stage"
        self.cases = staging.build(self.out)

    def test_every_case_is_staged(self) -> None:
        self.assertEqual(len(self.cases), len(staging.load_cases()))

    def test_no_answer_key_inside_the_skills(self) -> None:
        self.assertEqual(list((self.out / "skills").rglob("evals")), [])
        self.assertEqual(list((self.out / "skills").rglob("media")), [])

    def test_edit_cases_have_a_focus_for_every_expectation(self) -> None:
        for case in staging.load_cases():
            if staging.is_edit(case):
                with self.subTest(case["name"]):
                    self.assertEqual(len(staging.EDIT_FOCUS[case["name"]]), len(case["expectations"]))

    def test_media_script_stays_outside_the_fixture(self) -> None:
        for case_dir in (self.out / "evals").iterdir():
            fixture = case_dir / "fixture"
            if fixture.is_dir():
                with self.subTest(case_dir.name):
                    self.assertEqual(list(fixture.rglob("*.sh")), [])

    def test_prompts_point_into_the_workspace(self) -> None:
        for case_dir in (self.out / "evals").iterdir():
            definition = json.loads((case_dir / "case.yaml").read_text(encoding="utf-8"))
            with self.subTest(case_dir.name):
                self.assertNotIn("evals/files/", definition["execution"]["prompt"])

    def test_refuses_to_stage_inside_the_repository(self) -> None:
        self.assertEqual(staging.main([str(ROOT / "stage")]), 2)

    @unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not installed")
    def test_scaffold_makes_the_media(self) -> None:
        case_dir = self.out / "evals" / "review--review-before-publish"
        workspace = self.directory / "workspace"
        workspace.mkdir()
        subprocess.run(["bash", str(case_dir / "scaffold.sh")], cwd=workspace, check=True)
        self.assertTrue((workspace / "Promo/exports/final.mp4").is_file())
        self.assertTrue((workspace / "Promo/brief.md").is_file())
        self.assertFalse((workspace / "media.sh").exists())


class PackagingTests(unittest.TestCase):
    def test_archives_leave_evals_out(self) -> None:
        import zipfile
        with tempfile.TemporaryDirectory() as directory:
            result = package_skills.main(["--output", directory])
            self.assertEqual(result, 0)
            archives = sorted(Path(directory).glob("*.skill"))
            self.assertEqual(len(archives), len(list((ROOT / "skills").iterdir())))
            for archive in archives:
                names = zipfile.ZipFile(archive).namelist()
                with self.subTest(archive.name):
                    self.assertTrue(any(name.endswith("/SKILL.md") for name in names))
                    self.assertFalse(any("/evals/" in name for name in names))


if __name__ == "__main__":
    unittest.main()
