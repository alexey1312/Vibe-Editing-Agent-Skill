from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SKILLS = sorted(path.name for path in (ROOT / "skills").iterdir() if path.is_dir())
# Skills of other projects that the descriptions and references route work to.
HYPERFRAMES_SKILLS = {
    "hyperframes", "product-launch-video", "faceless-explainer", "pr-to-video", "embedded-captions",
    "talking-head-recut", "motion-graphics", "music-to-video", "slideshow", "general-video",
    "remotion-to-hyperframes", "hyperframes-core", "hyperframes-animation", "hyperframes-keyframes",
    "hyperframes-creative", "media-use", "hyperframes-cli", "hyperframes-audio", "hyperframes-registry",
    "hyperframes-studio", "figma",
}
REMOTION_SKILLS = {
    "remotion-best-practices", "remotion-captions", "remotion-create", "remotion-docs", "remotion-interactivity",
    "remotion-maps", "remotion-markup", "remotion-multimedia", "remotion-render", "remotion-saas",
    "remotion-studio", "remotion-upgrade",
}
OTHER_SKILLS = {"video-use", "watch", "openscreen-demo"}
KNOWN_SKILLS = HYPERFRAMES_SKILLS | REMOTION_SKILLS | OTHER_SKILLS | set(SKILLS)
# A version that will rot: a tool name followed by a dotted release or a "22+" requirement.
VERSION = re.compile(
    r"\b(?:FFmpeg|ffmpeg|Node\.js|Node|Python|HyperFrames|Remotion|WhisperX|auto-editor|yt-dlp)\s+v?\d+(?:\.\d+)+\b"
    r"|\b(?:Node\.js|Node|Python)\s+\d+\+"
)
TEXT_SUFFIXES = {".md", ".py", ".json", ".yml", ".yaml", ".txt", ".sh", ".svg", ".srt"}
NOT_FILES = {"project.md"}


def frontmatter(skill: str) -> dict[str, str]:
    text = (ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert match, f"{skill}: missing frontmatter"
    fields: dict[str, str] = {}
    current = None
    for line in match.group(1).splitlines():
        if re.match(r"^[a-z_-]+:", line):
            key, _, value = line.partition(":")
            current = key.strip()
            fields[current] = value.strip()
        elif current:
            fields[current] = (fields[current] + " " + line.strip()).strip()
    if fields.get("description", "").startswith(">-"):
        fields["description"] = fields["description"][2:].strip()
    return fields


def body(skill: str) -> str:
    text = (ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
    return re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.S)


def tracked_text_files() -> list[Path]:
    result = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                            cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        paths = [path for path in ROOT.rglob("*") if ".git" not in path.parts]
    else:
        paths = [ROOT / line for line in result.stdout.splitlines()]
    return [path for path in paths if path.is_file() and path.suffix in TEXT_SUFFIXES]


class ManifestTests(unittest.TestCase):
    def test_json_manifests_parse(self) -> None:
        for relative in (".claude-plugin/plugin.json", ".claude-plugin/marketplace.json",
                         ".cursor-plugin/plugin.json", "package.json"):
            with self.subTest(relative):
                json.loads((ROOT / relative).read_text(encoding="utf-8"))

    def test_every_manifest_lists_every_skill(self) -> None:
        plugin = json.loads((ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
        cursor = json.loads((ROOT / ".cursor-plugin/plugin.json").read_text(encoding="utf-8"))
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        for name, paths in (("plugin.json", plugin["skills"]), ("cursor plugin.json", cursor["skills"]),
                            ("package.json", package["pi"]["skills"])):
            with self.subTest(name):
                self.assertEqual(sorted(Path(p).name for p in paths), SKILLS)
                for path in paths:
                    self.assertTrue((ROOT / path / "SKILL.md").is_file(), path)

    def test_versions_agree(self) -> None:
        plugin = json.loads((ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
        marketplace = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
        cursor = json.loads((ROOT / ".cursor-plugin/plugin.json").read_text(encoding="utf-8"))
        entry = next(p for p in marketplace["plugins"] if p["name"] == plugin["name"])
        self.assertEqual(marketplace["version"], plugin["version"])
        self.assertEqual(entry["version"], plugin["version"])
        self.assertEqual(cursor["version"], plugin["version"])
        openai = (ROOT / "agents/openai.yaml").read_text(encoding="utf-8")
        self.assertIn(f'version: "{plugin["version"]}"', openai)
        for skill in SKILLS:
            self.assertIn(f"  - {skill}\n", openai)


class SkillTests(unittest.TestCase):
    def test_frontmatter(self) -> None:
        for skill in SKILLS:
            with self.subTest(skill):
                fields = frontmatter(skill)
                self.assertEqual(set(fields), {"name", "description"})
                self.assertEqual(fields.get("name"), skill)
                description = fields.get("description", "")
                self.assertGreater(len(description), 200)
                self.assertLessEqual(len(description), 1024)
                self.assertTrue(description.startswith("Use this skill when"))
                self.assertIn("Not for", description)

    def test_skills_named_in_descriptions_exist(self) -> None:
        # The "Not for" clauses route work to other skills by name; a typo would route nowhere.
        for skill in SKILLS:
            description = frontmatter(skill)["description"]
            named = [name.strip() for group in re.findall(r"\(([a-z][a-z-]*(?:,\s*[a-z][a-z-]*)*)\)", description)
                     for name in group.split(",")]
            self.assertTrue(named, f"{skill} routes nothing by name")
            for name in named:
                with self.subTest(skill=skill, name=name):
                    self.assertIn(name, KNOWN_SKILLS)

    def test_referenced_files_exist(self) -> None:
        pattern = re.compile(r"`((?:references|scripts)/[\w./-]+\.(?:md|py|json))")
        for skill in SKILLS:
            directory = ROOT / "skills" / skill
            for document in [directory / "SKILL.md", *sorted((directory / "references").glob("*.md"))]:
                text = document.read_text(encoding="utf-8")
                for relative in set(pattern.findall(text)):
                    with self.subTest(file=str(document.relative_to(ROOT)), reference=relative):
                        in_skill = (directory / relative).is_file()
                        in_skill_references = (directory / "references" / Path(relative).name).is_file()
                        in_repository = (ROOT / relative).is_file()
                        self.assertTrue(in_skill or in_skill_references or in_repository, relative)

    def test_sibling_references_named_in_prose_exist(self) -> None:
        pattern = re.compile(r"`([a-z-]+\.md)`")
        for skill in SKILLS:
            references = ROOT / "skills" / skill / "references"
            names = {path.name for path in references.glob("*.md")}
            for document in [ROOT / "skills" / skill / "SKILL.md", *sorted(references.glob("*.md"))]:
                for name in set(pattern.findall(document.read_text(encoding="utf-8"))) - NOT_FILES:
                    with self.subTest(file=str(document.relative_to(ROOT)), reference=name):
                        self.assertTrue(name in names or (ROOT / name).is_file(), name)

    def test_skill_bodies_leave_version_numbers_to_versions_md(self) -> None:
        for skill in SKILLS:
            with self.subTest(skill):
                self.assertEqual(VERSION.findall(body(skill)), [])
                self.assertIn("versions.md", body(skill))

    def test_copies_in_sync(self) -> None:
        result = subprocess.run([sys.executable, str(ROOT / "scripts/sync_skill_copies.py"), "--check"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout)


class ChecksTests(unittest.TestCase):
    def test_every_rule_in_the_scripts_is_documented_and_back(self) -> None:
        checks = (ROOT / "CHECKS.md").read_text(encoding="utf-8")
        documented = set(re.findall(r"^\| `((?:MED|CAP|QA)\d{3})`", checks, re.M))
        used = set()
        for name in ("media_probe.py", "captions.py", "qa_scan.py"):
            used |= set(re.findall(r'"((?:MED|CAP|QA)\d{3})"', (ROOT / "scripts" / name).read_text(encoding="utf-8")))
        self.assertEqual(used, documented)

    def test_every_documented_rule_names_a_source(self) -> None:
        checks = (ROOT / "CHECKS.md").read_text(encoding="utf-8")
        for row in re.findall(r"^\| `(?:MED|CAP|QA)\d{3}`.*$", checks, re.M):
            with self.subTest(row[:20]):
                cells = [cell.strip() for cell in row.strip("|").split("|")]
                self.assertEqual(len(cells), 5)
                self.assertTrue(cells[3])


class SourceRuleTests(unittest.TestCase):
    def test_measured_claims_point_at_measured_sections(self) -> None:
        measured = (ROOT / "references" / "measured-behavior.md").read_text(encoding="utf-8")
        sections = {}
        for match in re.finditer(r"^## (M\d+)\b.*?(?=^## |\Z)", measured, re.S | re.M):
            sections[match.group(1)] = re.search(r"Status:\**\s*measured", match.group(0)) is not None
        claim = re.compile(r"\*Measured\* (M\d+)(?:, (M\d+))?(?:, (M\d+))?|measured-behavior\.md` (M\d+)")
        documents = [*(ROOT / "skills").rglob("*.md"), *(ROOT / "references").glob("*.md"), ROOT / "CHECKS.md",
                     ROOT / "README.md"]
        for path in documents:
            if not path.is_file() or path.name == "measured-behavior.md":
                continue
            for match in claim.findall(path.read_text(encoding="utf-8")):
                for section in filter(None, match):
                    with self.subTest(file=str(path.relative_to(ROOT)), section=section):
                        self.assertIn(section, sections)
                        self.assertTrue(sections[section], f"{section} is cited as measured but not marked measured")

    def test_versions_md_dates_every_row(self) -> None:
        text = (ROOT / "references" / "versions.md").read_text(encoding="utf-8")
        rows = [line for line in text.splitlines()
                if line.startswith("|") and not set(line) <= set("|- :") and "Checked |" not in line]
        self.assertTrue(rows)
        for row in rows:
            with self.subTest(row[:60]):
                self.assertRegex(row, r"20\d\d-\d\d-\d\d")

    def test_background_guide_is_not_a_citation(self) -> None:
        # The guide the work started from is not open-licensed: it appears only as background reading.
        sources = (ROOT / "references" / "sources.md").read_text(encoding="utf-8")
        before, _, after = sources.partition("## Background reading")
        self.assertNotIn("Точки над ИИ", before)
        self.assertIn("Точки над ИИ", after)


class PublicationTests(unittest.TestCase):
    def test_no_model_ids_local_paths_or_keys_in_files(self) -> None:
        model = re.compile(r"claude-(?:opus|sonnet|haiku|fable)|gpt-\d|gemini-\d", re.I)
        local = re.compile(r"/Users/[A-Za-z]|/home/runner/work/")
        key = re.compile(r"\b(?:sk-[A-Za-z0-9]{16,}|xi-api-key:\s*\w{8,}|AIza[0-9A-Za-z_-]{30,})")
        for path in tracked_text_files():
            if path.resolve() == Path(__file__).resolve():
                continue  # this file spells the patterns out
            text = path.read_text(encoding="utf-8", errors="replace")
            with self.subTest(str(path.relative_to(ROOT))):
                self.assertIsNone(model.search(text), "model id")
                self.assertIsNone(local.search(text), "local path")
                self.assertIsNone(key.search(text), "key")


class EvalTests(unittest.TestCase):
    def load(self, skill: str) -> dict:
        return json.loads((ROOT / "skills" / skill / "evals" / "evals.json").read_text(encoding="utf-8"))

    def test_every_skill_has_skill_creator_evals(self) -> None:
        for skill in SKILLS:
            with self.subTest(skill):
                evals = self.load(skill)
                self.assertEqual(evals["skill_name"], skill)
                ids = [item["id"] for item in evals["evals"]]
                names = [item["name"] for item in evals["evals"]]
                self.assertEqual(len(ids), len(set(ids)))
                self.assertEqual(len(names), len(set(names)))
                for item in evals["evals"]:
                    self.assertTrue(item["expectations"])
                    for relative in item["files"]:
                        self.assertTrue((ROOT / "skills" / skill / relative).exists(), relative)
                    if item.get("media"):
                        self.assertTrue((ROOT / "skills" / skill / item["media"]).is_file(), item["media"])

    def test_fixtures_hold_no_media(self) -> None:
        # Media is generated when a case is staged; committed media would bloat the repository.
        media = {".mp4", ".mov", ".mkv", ".webm", ".wav", ".mp3", ".m4a", ".aac", ".png", ".jpg"}
        for path in (ROOT / "skills").rglob("evals/files/**/*"):
            with self.subTest(str(path.relative_to(ROOT))):
                self.assertNotIn(path.suffix.lower(), media)

    def test_eval_expectations_carry_no_version_numbers(self) -> None:
        for skill in SKILLS:
            for item in self.load(skill)["evals"]:
                for expectation in item["expectations"]:
                    with self.subTest(skill=skill, case=item["name"]):
                        self.assertIsNone(VERSION.search(expectation), expectation)

    def test_trigger_evals_mix_positive_and_negative(self) -> None:
        for skill in SKILLS:
            with self.subTest(skill):
                items = json.loads((ROOT / "skills" / skill / "evals" / "trigger-evals.json").read_text(encoding="utf-8"))
                self.assertGreaterEqual(len(items), 16)
                positives = sum(item["should_trigger"] for item in items)
                self.assertGreaterEqual(positives, 6)
                self.assertGreaterEqual(len(items) - positives, 6)


if __name__ == "__main__":
    unittest.main()
