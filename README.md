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
  a tool wraps that text in the requested structure. The **Symbols** menu adds
  common special characters such as `∞`, `≠`, `≈`, `∂`, and `∇`.
- Edit existing questions, including one-choice-per-line multiple-choice
  answers and an optional rendered answer explanation. Save from the persistent
  header button, the button at the end of the form, or with **Ctrl+S**.
- Write clean inline equations with familiar `$...$` notation. Sharp supports
  exponents and subscripts (`$x^2 + y_1$`), fractions (`$\frac{1}{2}$`), and
  common symbols such as `$\pi$`, `$\times$`, `$\le$`, and `$\sqrt$`.
- Attach PNG, GIF, PPM, or PGM pictures to visual questions.
- Switch between relaxed practice and an optional per-question timer.
- Press **Enter** to check an answer, then press **Enter** again to continue.
  Questions are shuffled at the beginning of every practice session, incorrect
  feedback is highlighted in red, and stopping always shows accuracy and time.
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
