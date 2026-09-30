"""A friendly, local-first quiz builder and practice application."""

from __future__ import annotations

import json
import os
import time
import tkinter as tk
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

    def add_question(self, prompt: str, answer: str, options=None, image="") -> dict:
        question = {
            "id": uuid4().hex,
            "prompt": prompt.strip(),
            "answer": answer.strip(),
            "options": [item.strip() for item in (options or []) if item.strip()],
            "image": image,
        }
        if not question["prompt"] or not question["answer"]:
            raise ValueError("A question and answer are required.")
        self.data["questions"].append(question)
        self.save()
        return question

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


class SharpQuiz:
    BG = "#F4F1EA"
    PANEL = "#FFFFFF"
    INK = "#20312B"
    MUTED = "#68756F"
    GREEN = "#317A5A"
    PALE = "#DDEBE3"
    GOLD = "#E7A84B"

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
        style.map("TButton", background=[("active", "#27664A")])
        style.configure("Quiet.TButton", background=self.PALE, foreground=self.INK)
        style.configure("TEntry", padding=8)

    def _clear(self):
        if self._timer_job:
            self.root.after_cancel(self._timer_job)
            self._timer_job = None
        for child in self.shell.winfo_children():
            child.destroy()

    def _header(self, title, subtitle=""):
        bar = tk.Frame(self.shell, bg=self.INK, height=92)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        tk.Label(bar, text="SHARP", bg=self.INK, fg="#A8D9BD", font=("TkDefaultFont", 12, "bold")).pack(
            side="left", padx=(36, 22))
        tk.Label(bar, text=title, bg=self.INK, fg="white", font=("TkDefaultFont", 22, "bold")).pack(side="left")
        if subtitle:
            tk.Label(bar, text=subtitle, bg=self.INK, fg="#BFC9C4", font=("TkDefaultFont", 10)).pack(
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
            tk.Label(row, text=question["prompt"], bg=self.PANEL, fg=self.INK, font=("TkDefaultFont", 11)).pack(side="left", padx=18)
            ttk.Button(row, text="Delete", style="Quiet.TButton",
                       command=lambda q=question: self._delete(q)).pack(side="right")

    def _delete(self, question):
        if messagebox.askyesno("Delete question", f"Remove “{question['prompt']}”?"):
            self.store.delete_question(question["id"]); self.show_library()

    def show_editor(self):
        self._clear(); header = self._header("Create a question", "Keep it focused and memorable.")
        ttk.Button(header, text="← Cancel", style="Quiet.TButton", command=self.show_home).pack(side="right", padx=32)
        form = tk.Frame(self.shell, bg=self.PANEL, padx=34, pady=28, highlightthickness=1, highlightbackground="#E2DED5")
        form.pack(fill="both", expand=True, padx=120, pady=28)
        prompt, answer, options, image_path = tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar()
        def field(label, variable, hint):
            tk.Label(form, text=label, bg=self.PANEL, fg=self.INK, font=("TkDefaultFont", 10, "bold")).pack(anchor="w", pady=(12, 5))
            ttk.Entry(form, textvariable=variable, font=("TkDefaultFont", 12)).pack(fill="x")
            tk.Label(form, text=hint, bg=self.PANEL, fg=self.MUTED).pack(anchor="w", pady=(4, 0))
        field("QUESTION", prompt, "Ask one clear thing at a time.")
        field("CORRECT ANSWER", answer, "Answers are checked without regard to capital letters.")
        field("ANSWER CHOICES (OPTIONAL)", options, "Separate choices with commas; leave blank for typed response.")
        tk.Label(form, text="PICTURE (OPTIONAL)", bg=self.PANEL, fg=self.INK, font=("TkDefaultFont", 10, "bold")).pack(anchor="w", pady=(18, 5))
        image_row = tk.Frame(form, bg=self.PANEL); image_row.pack(fill="x")
        ttk.Entry(image_row, textvariable=image_path).pack(side="left", fill="x", expand=True)
        ttk.Button(image_row, text="Choose image", style="Quiet.TButton",
                   command=lambda: image_path.set(filedialog.askopenfilename(filetypes=[("Images", "*.png *.gif *.ppm *.pgm"), ("All files", "*.*")]))).pack(side="left", padx=(10, 0))
        error = tk.Label(form, text="", bg=self.PANEL, fg="#A23B3B"); error.pack(anchor="w", pady=8)
        def save():
            try:
                self.store.add_question(prompt.get(), answer.get(), options.get().split(","), image_path.get())
                self.show_library()
            except ValueError as exc:
                error.configure(text=str(exc))
        ttk.Button(form, text="Save question", command=save).pack(anchor="e", pady=12)

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
        tk.Label(body, text=question["prompt"], wraplength=720, justify="center", bg=self.PANEL,
                 fg=self.INK, font=("TkDefaultFont", 20, "bold")).pack(pady=(5, 24))
        answer = tk.StringVar()
        if question["options"]:
            for option in question["options"]:
                tk.Radiobutton(body, text=option, variable=answer, value=option, indicatoron=False,
                               bg=self.PALE, selectcolor="#A8D9BD", fg=self.INK, padx=18, pady=10).pack(fill="x", pady=4)
        else:
            entry = ttk.Entry(body, textvariable=answer, font=("TkDefaultFont", 14), justify="center")
            entry.pack(fill="x", pady=10); entry.focus_set(); entry.bind("<Return>", lambda _e: submit())
        feedback = tk.Label(body, text="", bg=self.PANEL, fg=self.GREEN, font=("TkDefaultFont", 11, "bold")); feedback.pack(pady=10)
        def submit(timed_out=False):
            if getattr(self, "_answered", False): return
            self._answered = True
            correct = answer.get().strip().casefold() == question["answer"].strip().casefold()
            self.store.record_answer(correct)
            self.session_correct += int(correct)
            feedback.configure(text=("Nice work — that's right." if correct else f"Answer: {question['answer']}"),
                               fg=self.GREEN if correct else "#A23B3B")
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
