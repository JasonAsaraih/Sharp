import tkinter as tk

class Quiz:
    def __init__(self, root, questions, time_per_question):
        self.root = root
        self.root.title("Quiz App with Timer")
        self.root.geometry("800x600+450+50")
        root.configure(bg="lightblue")

        self.container = tk.Frame(root)
        self.container.pack(fill="both", expand=True)

        self.questions = questions
        self.time_per_question = time_per_question
        self.frames = {}
        self.user_answers = {}

        # Create a frame for each question
        for index, question in enumerate(self.questions):
            frame = QuestionFrame(self.container, question, index, self)
            self.frames[index] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(0)  # Show the first question

    def show_frame(self, index):
        """Switch to a specific question frame."""
        if index < len(self.questions):
            frame = self.frames[index]
            frame.tkraise()
            frame.start_timer()

    def save_answer(self, index, answer):
        """Save the user's answer."""
        self.user_answers[index] = answer
        print(f"Saved Answer for Q{index + 1}: {answer}")

class QuestionFrame(tk.Frame):
    def __init__(self, parent, question, index, controller):
        super().__init__(parent)
        self.controller = controller
        self.index = index
        self.answer_var = tk.StringVar()
        self.time_remaining = controller.time_per_question
        self.timer_label = tk.Label(self, text=f"Time Left: {self.time_remaining} sec", font=("Arial", 12))
        
        tk.Label(self, text=f"Q{index + 1}: {question['text']}", font=("Arial", 14)).pack(pady=10)
        self.timer_label.pack()

        if question["type"] == "multiple_choice":
            for option in question["options"]:
                tk.Radiobutton(self, text=option, variable=self.answer_var, value=option).pack(anchor="w")
        elif question["type"] == "free_response":
            self.entry = tk.Entry(self, textvariable=self.answer_var, width=40)
            self.entry.pack(pady=10)

        self.next_button = tk.Button(self, text="Next", command=self.next_question)
        self.next_button.pack(pady=10)

    def start_timer(self):
        """Start the countdown timer."""
        self.time_remaining = self.controller.time_per_question
        self.update_timer()

    def update_timer(self):
        """Update the timer label every second."""
        if self.time_remaining > 0:
            self.timer_label.config(text=f"Time Left: {self.time_remaining} sec")
            self.time_remaining -= 1
            self.after(1000, self.update_timer)
        else:
            self.next_question()

    def next_question(self):
        """Save the answer and move to the next question."""
        answer = self.answer_var.get()
        self.controller.save_answer(self.index, answer)
        self.controller.show_frame(self.index + 1)