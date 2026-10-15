from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import captions  # noqa: E402

OPTIONS = dict(captions.DEFAULTS)


def cue(index, start, end, *lines):
    return {"index": index, "start": start, "end": end, "lines": list(lines)}


def rules(found):
    return sorted({f["rule"] for f in found})


class CheckTests(unittest.TestCase):
    def test_clean_cue_passes(self) -> None:
        self.assertEqual(captions.check([cue(1, 0.0, 2.5, "Сегодня мы превратим", "идею в ролик.")], OPTIONS), [])

    def test_each_rule_has_a_positive_case(self) -> None:
        cases = {
            "CAP001": [cue(1, 0, 6, "one", "two", "three")],
            "CAP002": [cue(1, 0, 6, "x" * 50)],
            "CAP003": [cue(1, 0, 1, "Эта строка слишком длинная для одной секунды")],
            "CAP004": [cue(1, 0, 0.5, "Да.")],
            "CAP005": [cue(1, 0, 2, "first"), cue(2, 1.5, 3, "second")],
            "CAP006": [cue(1, 0, 2, "first"), cue(2, 2.03, 4, "second")],
            "CAP009": [cue(1, 0, 2, "Работаем в Сlaude")],
            "CAP010": [cue(1, 0, 2, "")],
            "CAP011": [cue(1, 0, 4, "Мы соберём ролик в", "три простых шага")],
        }
        for rule, items in cases.items():
            with self.subTest(rule):
                self.assertIn(rule, rules(captions.check(items, OPTIONS)))

    def test_past_the_end_of_the_video(self) -> None:
        found = captions.check([cue(1, 8, 10, "late")], OPTIONS, duration=9.0)
        self.assertIn("CAP007", rules(found))
        self.assertNotIn("CAP007", rules(captions.check([cue(1, 1, 3, "early")], OPTIONS, duration=9.0)))

    def test_glossary(self) -> None:
        found = captions.check([cue(1, 0, 3, "Открываем Hyperframes и Remotoin")], OPTIONS,
                               glossary=["HyperFrames", "Remotion"])
        messages = " ".join(f["message"] for f in found if f["rule"] == "CAP008")
        self.assertIn("Hyperframes", messages)
        self.assertIn("Remotoin", messages)
        self.assertEqual(captions.check([cue(1, 0, 3, "Открываем HyperFrames")], OPTIONS, glossary=["HyperFrames"]), [])

    def test_negative_cases(self) -> None:
        # One alphabet per word, a line ending in a full word, a zero gap: none of these is a finding.
        items = [cue(1, 0, 2.5, "Работаем в Claude Code"), cue(2, 2.5, 5.5, "Соберём ролик,", "потом проверим.")]
        self.assertEqual(captions.check(items, OPTIONS), [])

    def test_markup_is_not_counted(self) -> None:
        self.assertEqual(captions.check([cue(1, 0, 3, "<i>" + "x" * 40 + "</i>")], OPTIONS), [])


class ParseTests(unittest.TestCase):
    def test_parse_reports_broken_blocks(self) -> None:
        text = "1\n00:00:01,000 --> 00:00:02,000\nok\n\n2\nno timing here\n\n3\n00:00:03 --> x\nbad\n"
        cues, errors = captions.parse_srt(text)
        self.assertEqual(len(cues), 1)
        self.assertEqual(len(errors), 2)

    def test_round_trip(self) -> None:
        items = [cue(1, 1.0, 2.5, "a", "b")]
        parsed, errors = captions.parse_srt(captions.write_srt(items))
        self.assertEqual(errors, [])
        self.assertEqual((parsed[0]["start"], parsed[0]["end"], parsed[0]["lines"]), (1.0, 2.5, ["a", "b"]))


class BuildTests(unittest.TestCase):
    def words(self, text: str, start: float = 0.0, step: float = 0.35, pauses: dict | None = None) -> list[dict]:
        result, time = [], start
        for index, word in enumerate(text.split()):
            time += (pauses or {}).get(index, 0)
            result.append({"word": word, "start": round(time, 3), "end": round(time + step - 0.05, 3)})
            time += step
        return result

    def test_breaks_at_sentences_and_pauses(self) -> None:
        words = self.words("Сегодня мы превратим идею в ролик. Сначала соберём три сцены затем голос",
                           pauses={10: 1.0})
        built = captions.build(words, dict(OPTIONS))
        texts = [" ".join(c["lines"]) for c in built]
        self.assertEqual(texts[0], "Сегодня мы превратим идею в ролик.")
        self.assertTrue(texts[-1].endswith("затем голос"))
        self.assertEqual(captions.check([dict(c, index=i) for i, c in enumerate(built, 1)],
                                        dict(OPTIONS, max_cps=30)), [])

    def test_lines_fit_and_avoid_weak_endings(self) -> None:
        words = self.words("Мы соберём короткий ролик из трёх сцен и добавим голос в конце работы", step=0.4)
        for item in captions.build(words, dict(OPTIONS)):
            for line in item["lines"]:
                self.assertLessEqual(len(line), OPTIONS["max_chars"])
            if len(item["lines"]) > 1:
                self.assertNotIn(item["lines"][0].split()[-1].lower(), captions.WEAK_ENDINGS)

    def test_a_cue_never_spans_a_cut(self) -> None:
        words = [{"word": "А", "start": 3.3, "end": 3.5, "clip": "c02"},
                 {"word": "этот", "start": 3.55, "end": 3.8, "clip": "c02"},
                 {"word": "И", "start": 3.9, "end": 4.0, "clip": "c03"},
                 {"word": "финал.", "start": 4.05, "end": 4.5, "clip": "c03"}]
        built = captions.build(words, dict(OPTIONS))
        self.assertEqual([" ".join(c["lines"]) for c in built], ["А этот", "И финал."])

    def test_gap_and_minimum_duration(self) -> None:
        words = [{"word": "Да.", "start": 0.0, "end": 0.2}, {"word": "Нет.", "start": 0.25, "end": 0.45}]
        built = captions.build(words, dict(OPTIONS, pause=0.01))
        self.assertGreaterEqual(built[1]["start"] - built[0]["end"], OPTIONS["min_gap"] - 1e-9)


if __name__ == "__main__":
    unittest.main()
