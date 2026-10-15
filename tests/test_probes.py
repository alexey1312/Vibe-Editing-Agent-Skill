from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
HAVE_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


class ExpectationTests(unittest.TestCase):
    def test_every_probe_has_an_expectation_and_a_measured_section(self) -> None:
        expectations = json.loads((ROOT / "scripts/probes/expectations.json").read_text(encoding="utf-8"))
        source = (ROOT / "scripts/probes/ffmpeg_probes.py").read_text(encoding="utf-8")
        probes = set(re.findall(r'"(M\d+)": probe_', source))
        self.assertEqual(probes, set(expectations))
        measured = (ROOT / "references/measured-behavior.md").read_text(encoding="utf-8")
        for name in probes:
            with self.subTest(name):
                self.assertRegex(measured, rf"(?m)^## {name}\b")


@unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not installed")
class ProbeRunTests(unittest.TestCase):
    def test_probes_still_behave_as_recorded(self) -> None:
        result = subprocess.run([sys.executable, str(ROOT / "scripts/probes/ffmpeg_probes.py"), "--check"],
                                capture_output=True, text=True, timeout=600)
        self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr[-2000:])


if __name__ == "__main__":
    unittest.main()
