# Sharp

Sharp is a calm, local-first desktop app for building a personal question bank and turning anything you learn into a quick practice session.

## Features

- Create unlimited multiple-choice or written-answer questions from the GUI.
- Check written answers intelligently: capitalization, whitespace, and presentation
  punctuation do not matter, and equivalent arithmetic such as `1/2`, `0.5`, and
  `50%` is accepted.
- Add alternate correct responses with `||` (for example,
  `New York City || NYC`).
- Write standard LaTeX inline with `$...$` or as a display equation with
  `$$...$$`. The shared renderer handles fractions, roots, scripts, sums,
  integrals, functions, Greek letters, inequalities, and matrix environments
  in questions, choices, answers, explanations, previews, and review feedback.
- Build LaTeX without memorizing commands by using the equation toolbar in the
  question editor and free-response answer box. Selecting text before choosing
  a tool wraps that text in the requested structure.
- Edit existing questions, including one-choice-per-line multiple-choice
  answers and an optional rendered answer explanation.
- Attach PNG, GIF, PPM, or PGM pictures to visual questions.
- Switch between relaxed practice and an optional per-question timer.
- Enable Zen mode to hide progress and scores while answering.
- Track accuracy, app opens, practice sessions, longest correct streak, and best correct answers per minute.
- Keep everything private in a human-readable JSON file at `~/.sharp_quiz.json`.

## Run

Sharp only needs Python 3 and Tkinter:

```bash
python main.py
```

Use **New question** to grow your collection, then choose **Start practice**. Settings are saved automatically.

## Test

```bash
python -m unittest -v
```

Set `SHARP_DATA_FILE` to use a custom data location, which is useful for portable installations or development.
