from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import media_probe  # noqa: E402
import qa_scan  # noqa: E402
import toolchain_report  # noqa: E402

HAVE_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def info(path="take_01.mp4", **video) -> dict:
    base = {"codec": "h264", "coded_width": 1920, "coded_height": 1080, "rotation": 0, "display_width": 1920,
            "display_height": 1080, "r_frame_rate": "30/1", "avg_frame_rate": "30/1", "frame_rate": 30.0,
            "field_order": "progressive", "color_transfer": "bt709", "hdr": None, "duration": 10.0, "pix_fmt": "yuv420p",
            "scan": {"packets": 300, "irregular_share": 0.0, "max_keyframe_interval": 1.0}}
    base.update(video)
    return {"path": path, "duration": 10.0, "video": base,
            "audio": [{"codec": "aac", "sample_rate": 48000, "channels": 2, "duration": 10.0}]}


def rules(found) -> set[str]:
    return {f["rule"] for f in found}


class ProbeFindingTests(unittest.TestCase):
    def test_clean_file_has_no_findings(self) -> None:
        self.assertEqual(media_probe.file_findings(info()), [])

    def test_positive_cases(self) -> None:
        cases = {
            "MED001": info(scan={"packets": 300, "irregular_share": 0.2, "min_frame_interval": 0.016,
                                 "max_frame_interval": 0.033}),
            "MED002": info(rotation=-90, display_width=1080, display_height=1920),
            "MED006": info(scan={"packets": 300, "irregular_share": 0.0, "max_keyframe_interval": 4.0}),
            "MED009": info(field_order="tt"),
            "MED010": info(hdr="HLG", color_transfer="arib-std-b67"),
        }
        for rule, item in cases.items():
            with self.subTest(rule):
                self.assertIn(rule, rules(media_probe.file_findings(item)))

    def test_av_length_mismatch_and_missing_audio(self) -> None:
        item = info()
        item["audio"][0]["duration"] = 9.5
        self.assertIn("MED008", rules(media_probe.file_findings(item)))
        item["audio"] = []
        self.assertIn("MED003", rules(media_probe.file_findings(item)))

    def test_unstable_names(self) -> None:
        self.assertIn("MED007", rules(media_probe.file_findings(info("Запись экрана (2).mov"))))
        self.assertNotIn("MED007", rules(media_probe.file_findings(info("screen_02.mov"))))

    def test_cross_file_findings(self) -> None:
        a, b = info("a.mp4"), info("b.mp4", frame_rate=25.0)
        b["audio"][0]["sample_rate"] = 44100
        self.assertEqual(rules(media_probe.cross_findings([a, b])), {"MED004", "MED005"})
        self.assertEqual(media_probe.cross_findings([a, info("c.mp4")]), [])

    def test_rotation_sign(self) -> None:
        self.assertEqual(media_probe.rotation_of({"side_data_list": [{"rotation": -90}]}), -90)
        self.assertEqual(media_probe.rotation_of({"tags": {"rotate": "90"}}), -90)
        self.assertEqual(media_probe.rotation_of({}), 0)


class BoxOrderTests(unittest.TestCase):
    def test_reads_top_level_boxes(self) -> None:
        def box(kind: bytes, payload: bytes = b"") -> bytes:
            return (8 + len(payload)).to_bytes(4, "big") + kind + payload
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "a.mp4"
            path.write_bytes(box(b"ftyp", b"isom") + box(b"mdat", b"x" * 20) + box(b"moov", b"y" * 4))
            self.assertEqual(qa_scan.mp4_box_order(path), ["ftyp", "mdat", "moov"])


class ToolchainTests(unittest.TestCase):
    def test_only_allowed_commands_run(self) -> None:
        seen = []
        real = subprocess.run

        def spy(command, *args, **kwargs):
            seen.append(tuple([os.path.basename(command[0]), *command[1:]]))
            return real(command, *args, **kwargs)

        with mock.patch("subprocess.run", side_effect=spy):
            toolchain_report.report()
        for command in seen:
            with self.subTest(command=command):
                self.assertIn(command, toolchain_report.ALLOWED)

    def test_run_refuses_other_commands(self) -> None:
        with self.assertRaises(PermissionError):
            toolchain_report.run(["ffmpeg", "-i", "x.mp4", "y.mp4"])

    def test_secret_values_never_reach_the_report(self) -> None:
        with mock.patch.dict(os.environ, {"ELEVENLABS_API_KEY": "sk-very-secret"}):
            result = toolchain_report.report()
        self.assertIn("ELEVENLABS_API_KEY", result["secrets_present"])
        self.assertNotIn("sk-very-secret", json.dumps(result))
        self.assertNotIn("sk-very-secret", toolchain_report.markdown(result))


class ReadOnlyTests(unittest.TestCase):
    def test_read_only_scripts_never_open_files_for_writing(self) -> None:
        # media_probe and toolchain_report write nothing; qa_scan writes only evidence frames via ffmpeg.
        for name in ("media_probe.py", "toolchain_report.py", "qa_scan.py"):
            tree = ast.parse((ROOT / "scripts" / name).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and getattr(node.func, "attr", getattr(node.func, "id", "")) in {
                        "write_text", "write_bytes", "unlink", "rmtree", "remove", "rename"}:
                    self.fail(f"{name} line {node.lineno} writes or deletes a file")
                if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "open":
                    modes = [a.value for a in node.args[1:2] if isinstance(a, ast.Constant)]
                    self.assertFalse(any(set(m) & set("wax+") for m in modes), f"{name} line {node.lineno}")


@unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not installed")
class MediaIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.directory = Path(tempfile.mkdtemp())
        cls.video = cls.directory / "qa.mp4"
        subprocess.run([
            "ffmpeg", "-v", "error", "-y",
            "-f", "lavfi", "-i", "color=black:size=320x180:rate=30:duration=0.5",
            "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30:duration=3",
            "-f", "lavfi", "-i", "aevalsrc='0.3*sin(2*PI*220*t)*(1-between(t\\,1.5\\,3.2))':s=48000:d=3.5",
            "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0,format=yuv420p[v]",
            "-map", "[v]", "-map", "2:a", "-c:v", "libx264", "-c:a", "aac", "-shortest", str(cls.video)], check=True)

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.directory)

    def test_probe_reads_the_file(self) -> None:
        result = media_probe.report([str(self.directory)])
        self.assertEqual(len(result["files"]), 1)
        self.assertEqual(result["files"][0]["video"]["display_width"], 320)

    def test_scan_finds_black_start_silence_and_brief_mismatch(self) -> None:
        output = subprocess.run([sys.executable, str(ROOT / "scripts/qa_scan.py"), str(self.video), "--width", "1080",
                                 "--height", "1920", "--format", "json"], capture_output=True, text=True)
        result = json.loads(output.stdout)
        found = rules(result["findings"])
        self.assertTrue({"QA001", "QA002", "QA004"} <= found, found)
        self.assertEqual(output.returncode, 1)
        self.assertIsNotNone(result["loudness"]["integrated_lufs"])
        self.assertTrue(result["not_checked"])


if __name__ == "__main__":
    unittest.main()
