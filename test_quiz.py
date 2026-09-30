import json
import tempfile
import unittest
from pathlib import Path

from quiz import QuizStore


class QuizStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "data.json"
        self.store = QuizStore(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_add_and_reload_question(self):
        question = self.store.add_question("Two plus two?", "4", ["3", "4"], "/tmp/sum.png")
        loaded = QuizStore(self.path)
        self.assertEqual(loaded.data["questions"][-1], question)

    def test_blank_question_is_rejected(self):
        with self.assertRaises(ValueError):
            self.store.add_question("", "answer")

    def test_scoring_tracks_accuracy_and_streaks(self):
        for result in (True, True, False, True):
            self.store.record_answer(result)
        stats = self.store.data["stats"]
        self.assertEqual((stats["answered"], stats["correct"]), (4, 3))
        self.assertEqual(stats["longest_streak"], 2)
        self.assertEqual(stats["current_streak"], 1)

    def test_corrupt_file_recovers_with_defaults(self):
        self.path.write_text("not json", encoding="utf-8")
        self.assertGreater(len(QuizStore(self.path).data["questions"]), 0)

    def test_save_is_valid_json(self):
        self.store.save()
        self.assertIn("stats", json.loads(self.path.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
