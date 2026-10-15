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

import edl  # noqa: E402

HAVE_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def write(directory: Path, data: dict, name: str = "edl.json") -> Path:
    path = directory / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def plan(**overrides) -> dict:
    data = {"fps": 30, "sources": {"take": "take.mov", "screen": "screen.mov"}, "audio_fade_ms": 10, "clips": [
        {"id": "c01", "source": "take", "in": "00:00.50", "out": "00:02.00", "role": "hook", "reason": "first line"},
        {"id": "c02", "source": "take", "in": "00:03.20", "out": "00:05.50", "role": "body", "reason": "skip pause"},
        {"id": "c03", "source": "screen", "in": "1:02.0", "out": "1:04.0", "role": "proof", "reason": "the click"},
    ]}
    data.update(overrides)
    return data


class TimeTests(unittest.TestCase):
    def test_formats(self) -> None:
        self.assertEqual(edl.parse_time(12, 30), 12.0)
        self.assertEqual(edl.parse_time("12.5", 30), 12.5)
        self.assertEqual(edl.parse_time("01:02.5", 30), 62.5)
        self.assertEqual(edl.parse_time("1:00:02.5", 30), 3602.5)
        self.assertAlmostEqual(edl.parse_time("00:00:01:15", 30), 1.5)
        self.assertAlmostEqual(edl.parse_time("45f", 30), 1.5)

    def test_rejects_garbage(self) -> None:
        for value in ("abc", "1:2:3:4:5", True, None):
            with self.subTest(value=value), self.assertRaises(edl.EDLError):
                edl.parse_time(value, 30)

    def test_fmt(self) -> None:
        self.assertEqual(edl.fmt(62.5), "01:02.500")
        self.assertEqual(edl.fmt(3602.5), "1:00:02.500")


class LoadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.directory)

    def test_output_positions_follow_frames(self) -> None:
        loaded = edl.load(write(self.directory, plan()))
        self.assertEqual([c.out_start_frame for c in loaded.clips], [0, 45, 114])
        self.assertEqual(loaded.total_frames, 174)

    def test_off_frame_times_are_snapped_with_a_warning(self) -> None:
        data = plan()
        data["clips"][0]["in"] = 0.51
        loaded = edl.load(write(self.directory, data))
        self.assertEqual(loaded.clips[0].in_frame, 15)
        self.assertTrue(any("not on a frame" in w for w in loaded.warnings))

    def test_errors(self) -> None:
        cases = {
            "unknown source": plan(clips=[{"source": "nope", "in": 0, "out": 1}]),
            "out before in": plan(clips=[{"source": "take", "in": 2, "out": 1}]),
            "fps": plan(fps=0),
            "duplicate id": plan(clips=[{"id": "x", "source": "take", "in": 0, "out": 1},
                                        {"id": "x", "source": "take", "in": 2, "out": 3}]),
            "shorter than fades": plan(audio_fade_ms=600, clips=[{"source": "take", "in": 0, "out": 1}]),
        }
        for label, data in cases.items():
            with self.subTest(label), self.assertRaises(edl.EDLError):
                edl.load(write(self.directory, data))

    def test_missing_reason_warns(self) -> None:
        loaded = edl.load(write(self.directory, plan(clips=[{"source": "take", "in": 0, "out": 2}])))
        self.assertTrue(any("no `reason`" in w for w in loaded.warnings))

    def test_reorder_and_reuse_warn(self) -> None:
        data = plan(clips=[{"id": "b", "source": "take", "in": 5, "out": 7, "reason": "x"},
                           {"id": "a", "source": "take", "in": 1, "out": 6, "reason": "y"}])
        loaded = edl.load(write(self.directory, data))
        edl.check(loaded, probe=False)
        joined = " ".join(loaded.warnings)
        self.assertIn("out of its recorded order", joined)
        self.assertIn("reuse", joined)


class MappingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.directory)
        self.edl = edl.load(write(self.directory, plan()))

    def test_map_time(self) -> None:
        self.assertEqual(edl.map_time(self.edl, "take", 1.0), [0.5])
        self.assertEqual(edl.map_time(self.edl, "take", 3.0), [])
        self.assertAlmostEqual(edl.map_time(self.edl, "take", 5.0)[0], 3.3)
        self.assertAlmostEqual(edl.map_time(self.edl, "screen", 63.0)[0], 4.8)

    def test_removed_intervals(self) -> None:
        gaps = edl.removed_intervals(self.edl)
        self.assertEqual([(round(a, 3), round(b, 3)) for a, b in gaps["take"]], [(2.0, 3.2)])
        with_ends = edl.removed_intervals(self.edl, {"take": 10.0, "screen": 70.0})
        self.assertEqual([(round(a, 3), round(b, 3)) for a, b in with_ends["take"]],
                         [(0.0, 0.5), (2.0, 3.2), (5.5, 10.0)])

    def test_retime_words_drops_cut_words_and_shifts_the_rest(self) -> None:
        words = [{"word": "keep", "start": 1.0, "end": 1.3}, {"word": "gone", "start": 2.4, "end": 2.8},
                 {"word": "later", "start": 4.0, "end": 4.4}, {"word": "edge", "start": 1.9, "end": 2.05}]
        kept, dropped = edl.retime_words(self.edl, "take", sorted(words, key=lambda w: w["start"]))
        self.assertEqual([w["word"] for w in kept], ["keep", "edge", "later"])
        self.assertEqual([w["word"] for w in dropped], ["gone"])
        self.assertAlmostEqual(kept[0]["start"], 0.5)
        self.assertAlmostEqual(kept[2]["start"], 2.3)
        self.assertTrue(kept[1].get("clipped"))

    def test_retime_cues_flags_a_cue_across_a_cut(self) -> None:
        cues = [{"start": 0.6, "end": 1.5, "text": "inside"}, {"start": 1.8, "end": 3.5, "text": "across"},
                {"start": 2.2, "end": 3.0, "text": "cut"}]
        out, notes = edl.retime_cues(self.edl, "take", cues)
        self.assertEqual([c["text"] for c in out], ["inside", "across", "across"])
        self.assertTrue(any("crosses a cut" in n for n in notes))
        self.assertTrue(any("dropped" in n for n in notes))

    def test_srt_round_trip(self) -> None:
        cues = [{"start": 1.0, "end": 2.5, "text": "Привет"}, {"start": 3, "end": 4.25, "text": "мир"}]
        parsed = edl.parse_srt(edl.write_srt(cues))
        self.assertEqual([(c["start"], c["end"], c["text"]) for c in parsed],
                         [(1.0, 2.5, "Привет"), (3.0, 4.25, "мир")])


class TranscriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.directory)

    def load(self, data) -> list[dict]:
        path = self.directory / "words.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return edl.load_words(path)

    def test_formats(self) -> None:
        whisperx = {"segments": [{"words": [{"word": "a", "start": 0, "end": 0.2, "speaker": "S1"}]}]}
        eleven = {"words": [{"text": "a", "start": 0, "end": 0.2, "type": "word", "speaker_id": "speaker_0"},
                            {"text": " ", "start": 0.2, "end": 0.3, "type": "spacing"},
                            {"text": "(laughs)", "start": 0.3, "end": 0.9, "type": "audio_event"}]}
        plain = [{"word": "a", "start": 0, "end": 0.2}]
        for data in (whisperx, eleven, plain):
            with self.subTest(type(data).__name__):
                self.assertEqual([w["word"] for w in self.load(data)], ["a"])

    def test_candidates(self) -> None:
        words = [{"word": w, "start": s, "end": s + 0.2} for w, s in
                 [("we", 0.0), ("fixed", 0.3), ("we", 0.6), ("fixed", 0.9), ("this", 1.2), ("ну", 2.2), ("да", 2.5)]]
        found = edl.candidates(words, min_gap=0.5, language=None)
        kinds = {c["kind"] for c in found}
        self.assertEqual(kinds, {"pause", "repeat", "filler"})
        repeat = next(c for c in found if c["kind"] == "repeat")
        self.assertEqual((repeat["start"], repeat["end"]), (0.0, 0.6))

    def test_ambiguous_words_are_not_fillers(self) -> None:
        # "Ролик на треть короче." — the comparative, not the filler.
        words = [{"word": w, "start": i * 0.4, "end": i * 0.4 + 0.3} for i, w in
                 enumerate(["Ролик", "на", "треть", "короче."])]
        self.assertEqual([c for c in edl.candidates(words, 0.5, "ru") if c["kind"] == "filler"], [])


class RenderCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.directory)
        self.edl = edl.load(write(self.directory, plan(width=1080, height=1920)))

    def test_half_frame_video_bounds_and_exact_audio(self) -> None:
        command = edl.render_command(self.edl, self.directory / "out.mp4", 18, "medium")
        graph = command[command.index("-filter_complex") + 1]
        self.assertIn("trim=start=0.483333:end=1.983333", graph)
        self.assertIn("atrim=start=0.500000:end=2.000000", graph)
        self.assertIn("afade=t=out:st=1.490000:d=0.0100", graph)
        self.assertIn("pad=1080:1920", graph)
        self.assertIn("concat=n=3:v=1:a=1", graph)
        self.assertEqual(command.count("-i"), 2)

    def test_silent_source_gets_generated_silence(self) -> None:
        command = edl.render_command(self.edl, self.directory / "out.mp4", 18, "medium", {"take": True, "screen": False})
        graph = command[command.index("-filter_complex") + 1]
        self.assertIn("anullsrc", graph)

    def test_guard_output(self) -> None:
        source = self.directory / "take.mov"
        source.write_bytes(b"x")
        with self.assertRaises(edl.EDLError):
            edl.guard_output(source, force=True, sources=[source])
        with self.assertRaises(edl.EDLError):
            edl.guard_output(source, force=False)
        edl.guard_output(self.directory / "new.mp4", force=False)

    def test_snippets(self) -> None:
        html = edl.hyperframes_snippet(self.edl)
        self.assertIn('data-start="1.500" data-duration="2.300" data-media-start="3.200"', html)
        self.assertIn('data-has-audio="true"', html)
        older = edl.hyperframes_snippet(self.edl, separate_audio=True)
        self.assertIn("muted", older)
        self.assertIn("<audio", older)
        tsx = edl.remotion_snippet(self.edl)
        self.assertIn("from={45} durationInFrames={69}", tsx)
        self.assertIn("trimBefore={96}", tsx)


@unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not installed")
class CommandLineTests(unittest.TestCase):
    def test_check_with_probe_finds_out_past_end(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=160x90:rate=30:duration=2",
                            "-f", "lavfi", "-i", "sine=duration=2", "-shortest", "-pix_fmt", "yuv420p",
                            str(work / "take.mov")], check=True)
            path = write(work, {"fps": 30, "sources": {"take": "take.mov"},
                                "clips": [{"source": "take", "in": 0, "out": 3, "reason": "too long"}]})
            result = subprocess.run([sys.executable, str(ROOT / "scripts/edl.py"), "check", str(path), "--probe"],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("past the end", result.stdout)


if __name__ == "__main__":
    unittest.main()
