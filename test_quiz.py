import json
import inspect
import tempfile
import unittest
from pathlib import Path

from quiz import EquationEditor, QuizStore, SharpQuiz, answers_match, format_math_text


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

    def test_edit_question_preserves_math_choices_and_explanation(self):
        question = self.store.add_question("Old", "1")
        updated = self.store.update_question(
            question["id"], prompt=r"Solve $x^2=4$", answer=r"$x=\pm2$",
            options=[r"$x=2$", r"$x=\pm2$"], explanation=r"Because $\sqrt{4}=2$.", image="",
        )
        self.assertEqual(updated["options"], [r"$x=2$", r"$x=\pm2$"])
        self.assertIn(r"\sqrt", QuizStore(self.path).data["questions"][-1]["explanation"])


class FreeResponseTests(unittest.TestCase):
    def test_ignores_whitespace_case_and_punctuation(self):
        self.assertTrue(answers_match("  Albert   Einstein! ", "albert einstein"))

    def test_accepts_explicit_alternatives(self):
        self.assertTrue(answers_match("NYC", "New York City || NYC"))
        self.assertFalse(answers_match("York", "New York City || NYC"))

    def test_accepts_equivalent_numbers_and_expressions(self):
        self.assertTrue(answers_match("0.5", "1 / 2"))
        self.assertTrue(answers_match("50%", "0.5"))
        self.assertTrue(answers_match("2 + 2", "4"))

    def test_does_not_execute_arbitrary_python(self):
        self.assertFalse(answers_match("open('/tmp/file')", "4"))

    def test_formats_inline_math(self):
        rendered = format_math_text(r"Area is $A = \pi r^2$ and $x_1 \le x_2$.")
        self.assertEqual(rendered, "Area is A = π r² and x₁ ≤ x₂.")

    def test_text_outside_math_is_unchanged(self):
        self.assertEqual(format_math_text("Price is $5"), "Price is $5")

    def test_formats_display_math_nested_structures_and_functions(self):
        rendered = format_math_text(r"Before $$\sum_{i=1}^{n} \frac{\sqrt{x_i}}{2}$$ after")
        self.assertNotIn("$", rendered)
        self.assertNotIn(r"\frac", rendered)
        self.assertIn("∑", rendered)
        self.assertIn("√", rendered)

    def test_formats_standard_matrix_latex(self):
        rendered = format_math_text(
            r"$$\begin{bmatrix}a & b \\ c & d\end{bmatrix}$$"
        )
        self.assertEqual(rendered.strip(), "⎡ a  b ⎤\n⎡ c  d ⎤")


class EditorRegressionTests(unittest.TestCase):
    def test_editor_accepts_a_question_for_editing(self):
        parameter = inspect.signature(SharpQuiz.show_editor).parameters["question"]
        self.assertIsNone(parameter.default)

    def test_question_editor_has_persistent_save_action(self):
        source = inspect.getsource(SharpQuiz.show_editor)
        self.assertIn('ttk.Button(header, text="Save question"', source)
        self.assertIn('ttk.Button(bottom, text="Save question"', source)
        self.assertIn('self.root.bind("<Control-s>"', source)

    def test_equation_toolbar_includes_special_characters(self):
        equation_labels = {label for label, _latex in EquationEditor.BUTTONS}
        symbol_labels = {label for label, _latex in EquationEditor.SPECIAL}
        self.assertTrue({"a⁄b", "√", "xⁿ", "Σ", "∫", "π"} <= equation_labels)
        self.assertTrue({"∞", "≠", "≈", "→", "°", "∂", "∇", "∈"} <= symbol_labels)


if __name__ == "__main__":
    unittest.main()
