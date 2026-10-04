"""A friendly, local-first quiz builder and practice application."""

from __future__ import annotations

import json
import ast
import math
import os
import re
import time
import tkinter as tk
import unicodedata
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from uuid import uuid4


SAMPLE_QUESTIONS = [
    {
        "id": "welcome-capital",
        "prompt": "What is the capital of France?",
        "answer": "Paris",
        "options": ["Paris", "London", "Berlin", "Madrid"],
        "image": "",
    },
    {
        "id": "welcome-relativity",
        "prompt": "Who developed the theory of relativity?",
        "answer": "Albert Einstein",
        "options": [],
        "image": "",
    },
]


_MATH_SYMBOLS = {
    r"\times": "×", r"\cdot": "·", r"\div": "÷", r"\pm": "±",
    r"\le": "≤", r"\ge": "≥", r"\ne": "≠", r"\approx": "≈",
    r"\infty": "∞", r"\sum": "∑", r"\sqrt": "√", r"\pi": "π",
    r"\theta": "θ", r"\alpha": "α", r"\beta": "β", r"\gamma": "γ",
    r"\Delta": "Δ", r"\rightarrow": "→", r"\degree": "°", r"\int": "∫",
    r"\prod": "∏", r"\partial": "∂", r"\nabla": "∇", r"\in": "∈",
    r"\notin": "∉", r"\subset": "⊂", r"\subseteq": "⊆", r"\forall": "∀",
    r"\exists": "∃", r"\lambda": "λ", r"\mu": "μ", r"\sigma": "σ",
    r"\omega": "ω", r"\phi": "φ", r"\rho": "ρ", r"\epsilon": "ε",
    r"\Delta": "Δ", r"\rightarrow": "→", r"\degree": "°",
}
_SUPERSCRIPT = str.maketrans("0123456789+-=()n", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ")
_SUBSCRIPT = str.maketrans("0123456789+-=()", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎")


def format_math_text(text: str) -> str:
    """Turn approachable, LaTeX-like text between ``$`` markers into Unicode math.

    This deliberately stays dependency-free so saved quizzes remain portable. For
    example, ``$x^2 = \\frac{1}{2}\\pi r^2$`` becomes ``x² = ½π r²``.
    """
    def render(expression: str) -> str:
        # Resolve nested structural commands from the inside out.
        structural = [
            (r"\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}", lambda m: f"({m[1]})⁄({m[2]})"),
            (r"\\sqrt(?:\[([^]]+)\])?\s*\{([^{}]*)\}",
             lambda m: f"√{('[' + m[1] + ']') if m[1] else ''}({m[2]})"),
            (r"\\(?:text|mathrm|mathbf|mathit)\s*\{([^{}]*)\}", lambda m: m[1]),
            (r"\\(?:left|right)", lambda _m: ""),
        ]
        for _ in range(12):
            previous = expression
            for pattern, replacement in structural:
                expression = re.sub(pattern, replacement, expression)
            if expression == previous:
                break
        def matrix(match):
            rows = [[cell.strip() for cell in row.split("&")]
                    for row in re.split(r"\\\\", match.group(2))]
            width = max((len(row) for row in rows), default=0)
            rows = [row + [""] * (width - len(row)) for row in rows]
            body = "\n".join("  ".join(row) for row in rows)
            brackets = ("|", "|") if "vmatrix" in match.group(1) else ("⎡", "⎤")
            return "\n".join(f"{brackets[0]} {row} {brackets[1]}" for row in body.splitlines())
        expression = re.sub(r"\\begin\{(bmatrix|pmatrix|matrix|vmatrix)\}(.+?)\\end\{\1\}",
                            matrix, expression, flags=re.DOTALL)
        for command, symbol in sorted(_MATH_SYMBOLS.items(), key=lambda item: -len(item[0])):
            expression = expression.replace(command, symbol)
        expression = re.sub(r"\\(sin|cos|tan|log|ln|exp|lim)\b", r"\1", expression)
        expression = re.sub(
            r"\\frac\s*\{([^{}]+)\}\s*\{([^{}]+)\}",
            lambda match: f"({match.group(1)})⁄({match.group(2)})",
            expression,
        )
        for command, symbol in sorted(_MATH_SYMBOLS.items(), key=lambda item: -len(item[0])):
            expression = expression.replace(command, symbol)
        expression = re.sub(
            r"\^\{([^{}]+)\}|\^([0-9+\-=()n]+)",
            lambda match: (match.group(1) or match.group(2)).translate(_SUPERSCRIPT),
            expression,
        )
        expression = re.sub(
            r"_\{([^{}]+)\}|_([0-9+\-=()]+)",
            lambda match: (match.group(1) or match.group(2)).translate(_SUBSCRIPT),
            expression,
        )
        return expression.replace("{", "").replace("}", "")

    text = re.sub(r"\$\$(.+?)\$\$", lambda match: "\n" + render(match.group(1).strip()) + "\n",
                  text, flags=re.DOTALL)
    return re.sub(r"\$([^$\n]+)\$", lambda match: render(match.group(1)), text)


def _canonical_answer(value: str) -> str:
    value = unicodedata.normalize("NFKC", format_math_text(value)).casefold()
    value = value.translate(str.maketrans({"−": "-", "×": "*", "·": "*", "÷": "/", "⁄": "/"}))
    # Ignore spacing and presentation punctuation, but retain mathematical operators.
    return "".join(char for char in value if not char.isspace() and
                   (char.isalnum() or char in ".+-*/^=()%"))


def _numeric_value(value: str) -> float | None:
    """Safely evaluate a small arithmetic answer, without names or function calls."""
    value = _canonical_answer(value).replace("^", "**")
    if value.endswith("%"):
        value = f"({value[:-1]})/100"
    if "=" in value:
        value = value.rsplit("=", 1)[-1]
    try:
        tree = ast.parse(value, mode="eval")
    except (SyntaxError, ValueError):
        return None
    allowed = (ast.Expression, ast.Constant, ast.UnaryOp, ast.BinOp, ast.Add, ast.Sub,
               ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.UAdd, ast.USub)
    if any(not isinstance(node, allowed) or
           (isinstance(node, ast.Constant) and
            (not isinstance(node.value, (int, float)) or abs(node.value) > 1e12)) or
           (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow) and
            (not isinstance(node.right, ast.Constant) or abs(node.right.value) > 100))
           for node in ast.walk(tree)):
        return None
    try:
        result = eval(compile(tree, "<answer>", "eval"), {"__builtins__": {}}, {})
        return float(result) if math.isfinite(float(result)) else None
    except (ArithmeticError, OverflowError, TypeError, ValueError):
        return None


def answers_match(given: str, expected: str) -> bool:
    """Compare free responses flexibly; ``||`` separates accepted alternatives."""
    for alternative in expected.split("||"):
        if _canonical_answer(given) == _canonical_answer(alternative):
            return True
        given_number, expected_number = _numeric_value(given), _numeric_value(alternative)
        if given_number is not None and expected_number is not None:
            if math.isclose(given_number, expected_number, rel_tol=1e-9, abs_tol=1e-12):
                return True
    return False


class QuizStore:
    """JSON persistence and scoring, kept independent from Tk for easy testing."""

    def __init__(self, path: str | Path | None = None):
        default = Path.home() / ".sharp_quiz.json"
        self.path = Path(path or os.environ.get("SHARP_DATA_FILE", default))
        self.data = self._load()

    @staticmethod
    def defaults() -> dict:
        return {
            "questions": [dict(question) for question in SAMPLE_QUESTIONS],
            "settings": {"timer": True, "seconds": 30, "zen": False},
            "stats": {
                "logins": 0,
                "sessions": 0,
                "answered": 0,
                "correct": 0,
                "current_streak": 0,
                "longest_streak": 0,
                "best_per_minute": 0,
            },
        }

    def _load(self) -> dict:
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            base = self.defaults()
            base["questions"] = loaded.get("questions", base["questions"])
            base["settings"].update(loaded.get("settings", {}))
            base["stats"].update(loaded.get("stats", {}))
            return base
        except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError):
            return self.defaults()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    def add_question(self, prompt: str, answer: str, options=None, image="", explanation="") -> dict:
        question = {
            "id": uuid4().hex,
            "prompt": prompt.strip(),
            "answer": answer.strip(),
            "options": [item.strip() for item in (options or []) if item.strip()],
            "image": image,
            "explanation": explanation.strip(),
        }
        if not question["prompt"] or not question["answer"]:
            raise ValueError("A question and answer are required.")
        self.data["questions"].append(question)
        self.save()
        return question

    def update_question(self, question_id: str, **values) -> dict:
        for question in self.data["questions"]:
            if question["id"] == question_id:
                prompt, answer = values.get("prompt", "").strip(), values.get("answer", "").strip()
                if not prompt or not answer:
                    raise ValueError("A question and answer are required.")
                question.update(prompt=prompt, answer=answer,
                                options=[item.strip() for item in values.get("options", []) if item.strip()],
                                image=values.get("image", ""),
                                explanation=values.get("explanation", "").strip())
                self.save()
                return question
        raise ValueError("Question could not be found.")

    def delete_question(self, question_id: str) -> None:
        self.data["questions"] = [q for q in self.data["questions"] if q["id"] != question_id]
        self.save()

    def record_answer(self, correct: bool) -> None:
        stats = self.data["stats"]
        stats["answered"] += 1
        if correct:
            stats["correct"] += 1
            stats["current_streak"] += 1
            stats["longest_streak"] = max(stats["longest_streak"], stats["current_streak"])
        else:
            stats["current_streak"] = 0
        self.save()


class EquationEditor(tk.Frame):
    """Keyboard-friendly text editor with an unobtrusive standard-LaTeX toolbar."""

    BUTTONS = (
        ("a⁄b", r"\frac{{{}}}{{}}"), ("√", r"\sqrt{{{}}}"), ("xⁿ", "{}^{{}}"),
        ("xₙ", "{}_{{}}"), ("( )", r"\left({}\right)"), ("[ ]", r"\left[{}\right]"),
        ("×", r" \times "), ("÷", r" \div "), ("±", r" \pm "), ("=", " = "),
        ("<", " < "), (">", " > "), ("≤", r" \le "), ("≥", r" \ge "),
        ("|x|", r"\left|{}\right|"),
        ("Σ", r"\sum_{{{}}}^{{}} "), ("∫", r"\int_{{{}}}^{{}} "),
        ("sin", r"\sin({})"), ("cos", r"\cos({})"), ("tan", r"\tan({})"),
        ("log", r"\log({})"), ("ln", r"\ln({})"), ("π", r"\pi"),
    )
    GREEK = ("α", r"\alpha"), ("β", r"\beta"), ("γ", r"\gamma"), ("θ", r"\theta"), \
            ("λ", r"\lambda"), ("μ", r"\mu"), ("π", r"\pi"), ("σ", r"\sigma"), ("ω", r"\omega")
    SPECIAL = (("∞", r"\infty"), ("≠", r"\ne"), ("≈", r"\approx"),
               ("→", r"\rightarrow"), ("°", r"\degree"), ("∂", r"\partial"),
               ("∇", r"\nabla"), ("∈", r"\in"), ("∉", r"\notin"))

    def __init__(self, parent, *, height=3, on_change=None, toolbar=True, **kwargs):
        super().__init__(parent, bg="#FFFFFF")
        self.text = tk.Text(self, height=height, wrap="word", undo=True, relief="solid",
                            borderwidth=1, padx=8, pady=7, fg="#111111", bg="#FFFFFF",
                            insertbackground="#111111", **kwargs)
        self.text.pack(fill="x")
        self.text.bind("<<Modified>>", self._changed)
        self.text.bind("<Control-b>", lambda _e: self.insert_latex(r"\mathbf{{{}}}"))
        self.on_change = on_change
        if toolbar:
            tools = tk.Frame(self, bg="#F2F2F2", padx=3, pady=3)
            tools.pack(fill="x", pady=(3, 0))
            tk.Label(tools, text="Equation tools", bg="#F2F2F2", fg="#444444",
                     font=("TkDefaultFont", 8, "bold")).grid(row=0, column=0, columnspan=10, sticky="w", padx=3)
            for index, (label, latex) in enumerate(self.BUTTONS):
                row = 1 + index // 10
                tk.Button(tools, text=label, command=lambda value=latex: self.insert_latex(value),
                          bg="#FFFFFF", fg="#111111", activebackground="#D8D8D8",
                          relief="flat", padx=6, pady=2, takefocus=True).grid(row=row, column=index % 10, padx=1, pady=1)
            greek = tk.Menubutton(tools, text="Greek ▾", bg="#FFFFFF", relief="flat", padx=6)
            menu = tk.Menu(greek, tearoff=False)
            for label, latex in self.GREEK:
                menu.add_command(label=label, command=lambda value=latex: self.insert_latex(value))
            greek.configure(menu=menu)
            menu_row, menu_column = 1 + len(self.BUTTONS) // 10, len(self.BUTTONS) % 10
            greek.grid(row=menu_row, column=menu_column, padx=1, pady=1)
            special = tk.Menubutton(tools, text="Symbols ▾", bg="#FFFFFF", relief="flat", padx=6)
            special_menu = tk.Menu(special, tearoff=False)
            for label, latex in self.SPECIAL:
                special_menu.add_command(label=label,
                                         command=lambda value=latex: self.insert_latex(value))
            special.configure(menu=special_menu)
            special.grid(row=menu_row, column=menu_column + 1, padx=1, pady=1)

    def _changed(self, _event=None):
        if self.text.edit_modified():
            self.text.edit_modified(False)
            if self.on_change:
                self.on_change()

    def get(self):
        return self.text.get("1.0", "end-1c")

    def set(self, value):
        self.text.delete("1.0", "end")
        self.text.insert("1.0", value)
        self.text.edit_modified(False)

    def insert_latex(self, template):
        """Wrap the selection (or create a placeholder) and keep focus in the editor."""
        try:
            selected = self.text.get("sel.first", "sel.last")
            self.text.delete("sel.first", "sel.last")
        except tk.TclError:
            selected = ""
        latex = template.format(selected)
        # Toolbar output is always a complete math region unless the cursor is already in one.
        before = self.text.get("1.0", "insert")
        state, index = None, 0
        while index < len(before):
            if before.startswith("$$", index):
                state = None if state == "display" else "display"
                index += 2
            elif before[index] == "$" and state != "display":
                state = None if state == "inline" else "inline"
                index += 1
            else:
                index += 1
        if state is None:
            latex = f"${latex}$"
        start = self.text.index("insert")
        self.text.insert("insert", latex)
        empty = latex.find("{}")
        if empty >= 0:
            self.text.mark_set("insert", f"{start}+{empty + 1}c")
        self.text.focus_set()
        if self.on_change:
            self.on_change()


class SharpQuiz:
    BG = "#F2F2F2"
    PANEL = "#FFFFFF"
    INK = "#111111"
    MUTED = "#666666"
    GREEN = "#202020"
    PALE = "#E5E5E5"
    GOLD = "#555555"

    def __init__(self, root: tk.Tk, store: QuizStore | None = None, *_legacy):
        self.root, self.store = root, store or QuizStore()
        self.store.data["stats"]["logins"] += 1
        self.store.save()
        self.root.title("Sharp — learn a little every day")
        self.root.geometry("1040x700")
        self.root.minsize(820, 600)
        self.root.configure(bg=self.BG)
        self._timer_job = None
        self._photo = None
        self._configure_style()
        self.shell = tk.Frame(root, bg=self.BG)
        self.shell.pack(fill="both", expand=True)
        self.show_home()

    def _configure_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", font=("TkDefaultFont", 11, "bold"), padding=(18, 10),
                        background=self.GREEN, foreground="white", borderwidth=0)
        style.map("TButton", background=[("active", "#000000")])
        style.configure("Quiet.TButton", background=self.PALE, foreground=self.INK)
        style.configure("TEntry", padding=8)

    def _clear(self):
        self.root.unbind("<Control-s>")
        if self._timer_job:
            self.root.after_cancel(self._timer_job)
            self._timer_job = None
        for child in self.shell.winfo_children():
            child.destroy()

    def _header(self, title, subtitle=""):
        bar = tk.Frame(self.shell, bg=self.INK, height=92)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        tk.Label(bar, text="SHARP", bg=self.INK, fg="#FFFFFF", font=("TkDefaultFont", 12, "bold")).pack(
            side="left", padx=(36, 22))
        tk.Label(bar, text=title, bg=self.INK, fg="white", font=("TkDefaultFont", 22, "bold")).pack(side="left")
        if subtitle:
            tk.Label(bar, text=subtitle, bg=self.INK, fg="#C8C8C8", font=("TkDefaultFont", 10)).pack(
                side="left", padx=18)
        return bar

    def show_home(self):
        self._clear()
        header = self._header("Your learning space", "Build it. Practice it. Know it.")
        ttk.Button(header, text="＋ New question", command=self.show_editor).pack(side="right", padx=32, pady=22)
        body = tk.Frame(self.shell, bg=self.BG)
        body.pack(fill="both", expand=True, padx=36, pady=28)
        stats = self.store.data["stats"]
        answered = stats["answered"]
        accuracy = round(stats["correct"] * 100 / answered) if answered else 0
        cards = [
            ("QUESTIONS", len(self.store.data["questions"]), "in your collection"),
            ("ACCURACY", f"{accuracy}%", f"{stats['correct']} correct answers"),
            ("BEST STREAK", stats["longest_streak"], "answers in a row"),
            ("BEST MINUTE", stats["best_per_minute"], "correct answers"),
        ]
        row = tk.Frame(body, bg=self.BG)
        row.pack(fill="x")
        for label, value, note in cards:
            card = tk.Frame(row, bg=self.PANEL, padx=20, pady=18, highlightthickness=1,
                            highlightbackground="#E2DED5")
            card.pack(side="left", fill="x", expand=True, padx=(0, 12))
            tk.Label(card, text=label, bg=self.PANEL, fg=self.MUTED, font=("TkDefaultFont", 9, "bold")).pack(anchor="w")
            tk.Label(card, text=value, bg=self.PANEL, fg=self.INK, font=("TkDefaultFont", 25, "bold")).pack(anchor="w", pady=4)
            tk.Label(card, text=note, bg=self.PANEL, fg=self.MUTED).pack(anchor="w")
        action = tk.Frame(body, bg=self.PANEL, padx=28, pady=24, highlightthickness=1, highlightbackground="#E2DED5")
        action.pack(fill="x", pady=26)
        tk.Label(action, text="Ready for a quick practice?", bg=self.PANEL, fg=self.INK,
                 font=("TkDefaultFont", 17, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(action, text="Timer is optional. Zen mode hides scores and distractions while you learn.",
                 bg=self.PANEL, fg=self.MUTED).grid(row=1, column=0, sticky="w", pady=(5, 0))
        ttk.Button(action, text="Start practice  →", command=self.start_session).grid(row=0, column=2, rowspan=2, padx=12)
        action.columnconfigure(0, weight=1)
        settings = self.store.data["settings"]
        timer = tk.BooleanVar(value=settings["timer"])
        zen = tk.BooleanVar(value=settings["zen"])
        seconds = tk.IntVar(value=settings["seconds"])
        controls = tk.Frame(body, bg=self.BG)
        controls.pack(fill="x")
        tk.Checkbutton(controls, text="Timed questions", variable=timer, bg=self.BG, fg=self.INK,
                       activebackground=self.BG, command=lambda: self._setting("timer", timer.get())).pack(side="left")
        tk.Spinbox(controls, from_=5, to=300, increment=5, textvariable=seconds, width=5,
                   command=lambda: self._setting("seconds", seconds.get())).pack(side="left", padx=(8, 24))
        tk.Checkbutton(controls, text="Zen mode", variable=zen, bg=self.BG, fg=self.INK,
                       activebackground=self.BG, command=lambda: self._setting("zen", zen.get())).pack(side="left")
        ttk.Button(controls, text="Manage questions", style="Quiet.TButton", command=self.show_library).pack(side="right")
        tk.Label(body, text=f"Opened {stats['logins']} times  •  {stats['sessions']} practice sessions",
                 bg=self.BG, fg=self.MUTED).pack(anchor="w", side="bottom")

    def _setting(self, key, value):
        self.store.data["settings"][key] = value
        self.store.save()

    def show_library(self):
        self._clear(); header = self._header("Question library")
        ttk.Button(header, text="＋ Add", command=self.show_editor).pack(side="right", padx=(8, 32))
        ttk.Button(header, text="← Home", style="Quiet.TButton", command=self.show_home).pack(side="right")
        body = tk.Frame(self.shell, bg=self.BG); body.pack(fill="both", expand=True, padx=36, pady=25)
        for number, question in enumerate(self.store.data["questions"], 1):
            row = tk.Frame(body, bg=self.PANEL, padx=18, pady=12, highlightthickness=1, highlightbackground="#E2DED5")
            row.pack(fill="x", pady=5)
            tk.Label(row, text=f"{number:02}", bg=self.PANEL, fg=self.GREEN, font=("TkDefaultFont", 11, "bold")).pack(side="left")
            tk.Label(row, text=format_math_text(question["prompt"]), bg=self.PANEL, fg=self.INK,
                     font=("TkDefaultFont", 11)).pack(side="left", padx=18)
            ttk.Button(row, text="Delete", style="Quiet.TButton",
                       command=lambda q=question: self._delete(q)).pack(side="right")
            ttk.Button(row, text="Edit", style="Quiet.TButton",
                       command=lambda q=question: self.show_editor(q)).pack(side="right", padx=5)

    def _delete(self, question):
        if messagebox.askyesno("Delete question", f"Remove “{question['prompt']}”?"):
            self.store.delete_question(question["id"]); self.show_library()

    def show_editor(self, question=None):
        self._clear()
        title = "Edit question" if question else "Create a question"
        header = self._header(title, "Standard LaTeX works anywhere you see the equation toolbar.")
        ttk.Button(header, text="← Cancel", style="Quiet.TButton", command=self.show_library).pack(side="right", padx=32)
        holder = tk.Frame(self.shell, bg=self.BG)
        holder.pack(fill="both", expand=True, padx=40, pady=18)
        canvas = tk.Canvas(holder, bg=self.PANEL, highlightthickness=1,
                           highlightbackground="#CCCCCC")
        scrollbar = ttk.Scrollbar(holder, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        form = tk.Frame(canvas, bg=self.PANEL, padx=28, pady=16)
        # Create the save-action container up front. Keeping this initialization
        # next to the form prevents callbacks/build paths from ever referencing
        # an undefined ``bottom`` widget (including on Windows Tk builds).
        bottom = tk.Frame(form, bg=self.PANEL)
        form_window = canvas.create_window((0, 0), window=form, anchor="nw")
        form.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(form_window, width=event.width))
        scroll = lambda event: canvas.yview_scroll(-event.delta // 120, "units")
        canvas.bind("<Enter>", lambda _e: canvas.bind_all("<MouseWheel>", scroll))
        canvas.bind("<Leave>", lambda _e: canvas.unbind_all("<MouseWheel>"))
        image_path = tk.StringVar(value=(question or {}).get("image", ""))

        def label(text, hint=""):
            tk.Label(form, text=text, bg=self.PANEL, fg=self.INK,
                     font=("TkDefaultFont", 9, "bold")).pack(anchor="w", pady=(7, 2))
            if hint:
                tk.Label(form, text=hint, bg=self.PANEL, fg=self.MUTED,
                         font=("TkDefaultFont", 8)).pack(anchor="w")

        preview = tk.Label(form, text="Preview", bg="#F2F2F2", fg=self.INK, justify="left",
                           anchor="w", padx=12, pady=7, wraplength=820)
        editors = {}
        def update_preview():
            pieces = [format_math_text(prompt_editor.get()) or "Preview",
                      format_math_text(answer_editor.get())]
            if "choices" in editors:
                pieces.extend(f"• {format_math_text(choice)}"
                              for choice in choices_editor.get().splitlines() if choice.strip())
            if "explanation" in editors and explanation_editor.get().strip():
                pieces.append("Explanation: " + format_math_text(explanation_editor.get()))
            preview.configure(text="\n".join(piece for piece in pieces if piece))

        label("QUESTION", r"Type standard LaTeX inside $...$ (inline) or $$...$$ (display), or use the toolbar.")
        prompt_editor = EquationEditor(form, height=2, on_change=update_preview)
        prompt_editor.pack(fill="x")
        label("CORRECT ANSWER", "Use || between alternate correct answers.")
        answer_editor = EquationEditor(form, height=1, on_change=update_preview)
        answer_editor.pack(fill="x")
        preview.pack(fill="x", pady=(6, 0))
        label("ANSWER CHOICES (OPTIONAL)", "Put one choice per line. Each choice supports independent LaTeX.")
        choices_editor = EquationEditor(form, height=2, on_change=update_preview)
        editors["choices"] = choices_editor
        choices_editor.pack(fill="x")
        label("ANSWER EXPLANATION (OPTIONAL)", "Shown after answering; text and LaTeX are supported.")
        explanation_editor = EquationEditor(form, height=1, on_change=update_preview)
        editors["explanation"] = explanation_editor
        explanation_editor.pack(fill="x")

        if question:
            prompt_editor.set(question.get("prompt", ""))
            answer_editor.set(question.get("answer", ""))
            choices_editor.set("\n".join(question.get("options", [])))
            explanation_editor.set(question.get("explanation", ""))
        update_preview()

        tk.Label(form, text="PICTURE (OPTIONAL)", bg=self.PANEL, fg=self.INK, font=("TkDefaultFont", 10, "bold")).pack(anchor="w", pady=(18, 5))
        image_row = tk.Frame(form, bg=self.PANEL)
        image_row.pack(fill="x", pady=(8, 0))
        ttk.Entry(image_row, textvariable=image_path).pack(side="left", fill="x", expand=True)
        ttk.Button(image_row, text="Choose image", style="Quiet.TButton",
                   command=lambda: image_path.set(filedialog.askopenfilename(
                       filetypes=[("Images", "*.png *.gif *.ppm *.pgm"), ("All files", "*.*")]))).pack(side="left", padx=6)
        error = tk.Label(image_row, text="", bg=self.PANEL, fg="#333333")
        error.pack(side="left", padx=5)

        def save():
            raw_choices = choices_editor.get()
            options = raw_choices.splitlines() if "\n" in raw_choices else raw_choices.split(",")
            values = dict(prompt=prompt_editor.get(), answer=answer_editor.get(), options=options,
                          image=image_path.get(), explanation=explanation_editor.get())
            try:
                if question:
                    self.store.update_question(question["id"], **values)
                else:
                    self.store.add_question(**values)
                self.show_library()
            except ValueError as exc:
                error.configure(text=str(exc))
        # A second action at the end of the form is convenient for keyboard-free
        # workflows. ``bottom`` was initialized with the form above.
        bottom.pack(fill="x", pady=(10, 0))
        ttk.Button(bottom, text="Save question", command=save).pack(side="right")
        # The primary action lives in the fixed header, outside the scrolling form.
        ttk.Button(header, text="Save question", command=save).pack(side="right", padx=(8, 0), pady=22)
        self.root.bind("<Control-s>", lambda _event: (save(), "break")[1])

    def start_session(self):
        questions = self.store.data["questions"]
        if not questions:
            messagebox.showinfo("No questions yet", "Add your first question before practicing."); return
        self.store.data["stats"]["sessions"] += 1; self.store.save()
        self.session_questions = list(questions); self.session_index = 0; self.session_correct = 0
        self.session_started = time.monotonic(); self.show_question()

    def show_question(self):
        if self.session_index >= len(self.session_questions):
            self.finish_session(); return
        self._clear(); question = self.session_questions[self.session_index]
        settings = self.store.data["settings"]; zen = settings["zen"]
        header = self._header("Focus" if zen else "Practice",
                              "" if zen else f"Question {self.session_index + 1} of {len(self.session_questions)}")
        ttk.Button(header, text="End", style="Quiet.TButton", command=self.finish_session).pack(side="right", padx=32)
        body = tk.Frame(self.shell, bg=self.PANEL, padx=60, pady=35); body.pack(fill="both", expand=True, padx=90, pady=35)
        if question.get("image"):
            try:
                self._photo = tk.PhotoImage(file=question["image"])
                scale = max(1, max(self._photo.width() // 480, self._photo.height() // 210))
                shown = self._photo.subsample(scale, scale) if scale > 1 else self._photo
                self._display_photo = shown
                tk.Label(body, image=shown, bg=self.PANEL).pack(pady=(0, 18))
            except tk.TclError:
                tk.Label(body, text="Picture unavailable", bg=self.PANEL, fg=self.MUTED).pack()
        tk.Label(body, text=format_math_text(question["prompt"]), wraplength=720, justify="center", bg=self.PANEL,
                 fg=self.INK, font=("TkDefaultFont", 20, "bold")).pack(pady=(5, 24))
        if question["options"]:
            answer = tk.StringVar()
            for option in question["options"]:
                tk.Radiobutton(body, text=format_math_text(option), variable=answer, value=option, indicatoron=False,
                               bg=self.PALE, selectcolor="#BDBDBD", fg=self.INK, padx=18, pady=10).pack(fill="x", pady=4)
        else:
            answer = EquationEditor(body, height=2)
            answer.pack(fill="x", pady=10)
            answer.text.focus_set()
            answer.text.bind("<Control-Return>", lambda _e: submit())
        feedback = tk.Label(body, text="", bg=self.PANEL, fg=self.GREEN, font=("TkDefaultFont", 11, "bold")); feedback.pack(pady=10)
        def submit(timed_out=False):
            if getattr(self, "_answered", False): return
            self._answered = True
            correct = answers_match(answer.get(), question["answer"])
            self.store.record_answer(correct)
            self.session_correct += int(correct)
            shown_answer = format_math_text(question["answer"].split("||", 1)[0].strip())
            explanation = format_math_text(question.get("explanation", ""))
            message = "Nice work — that's right." if correct else f"Answer: {shown_answer}"
            if explanation:
                message += f"\n\n{explanation}"
            feedback.configure(text=message, wraplength=700, justify="center",
                               fg=self.GREEN if correct else "#333333")
            button.configure(text="Continue →", command=self._advance)
        self._answered = False
        button = ttk.Button(body, text="Check answer", command=submit); button.pack(pady=8)
        if settings["timer"]:
            remaining = [int(settings["seconds"])]
            timer_label = tk.Label(body, text="", bg=self.PANEL, fg=self.GOLD, font=("TkDefaultFont", 11, "bold"))
            timer_label.pack(side="bottom")
            def tick():
                timer_label.configure(text=f"{remaining[0]} seconds")
                if remaining[0] <= 0: submit(True)
                elif not self._answered:
                    remaining[0] -= 1; self._timer_job = self.root.after(1000, tick)
            tick()

    def _advance(self):
        self.session_index += 1; self.show_question()

    def finish_session(self):
        elapsed = max(time.monotonic() - getattr(self, "session_started", time.monotonic()), 1)
        per_minute = round(getattr(self, "session_correct", 0) * 60 / elapsed)
        stats = self.store.data["stats"]
        stats["best_per_minute"] = max(stats["best_per_minute"], per_minute); self.store.save()
        self._clear(); self._header("Session complete")
        body = tk.Frame(self.shell, bg=self.BG); body.pack(expand=True)
        tk.Label(body, text="Practice makes progress.", bg=self.BG, fg=self.INK,
                 font=("TkDefaultFont", 26, "bold")).pack(pady=8)
        tk.Label(body, text=f"{getattr(self, 'session_correct', 0)} correct  •  {per_minute} per minute",
                 bg=self.BG, fg=self.MUTED, font=("TkDefaultFont", 13)).pack(pady=6)
        ttk.Button(body, text="Back to dashboard", command=self.show_home).pack(pady=22)


# Backwards-compatible public name for existing imports.
Quiz = SharpQuiz
