import tkinter as tk

class QuizApp:
    def __init__(self, root, questions):
        self.root = root
        self.root.title("Quiz App")
        self.root.geometry("500x300")

        self.container = tk.Frame(root)
        self.container.pack(fill="both", expand=True)

        self.questions = questions
        self.frames = {}
        self.user_answers = {}

        # Create a frame for each question
        for index, question in enumerate(self.questions):
            frame = QuestionFrame(self.container, question, index, self)
            self.frames[index] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(0)  # Show first question

    def show_frame(self, index):
        """Switch to a specific question frame."""
        if index < len(self.questions):
            frame = self.frames[index]
            frame.tkraise()

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

        tk.Label(self, text=f"Q{index + 1}: {question['text']}", font=("Arial", 14)).pack(pady=10)

        if question["type"] == "multiple_choice":
            # Display multiple-choice options
            for option in question["options"]:
                tk.Radiobutton(self, text=option, variable=self.answer_var, value=option).pack(anchor="w")
        elif question["type"] == "free_response":
            # Free-response text box
            self.entry = tk.Entry(self, textvariable=self.answer_var, width=40)
            self.entry.pack(pady=10)

        # Next button
        next_button = tk.Button(self, text="Next", command=self.next_question)
        next_button.pack(pady=10)

    def next_question(self):
        """Save the answer and move to the next question."""
        answer = self.answer_var.get()
        self.controller.save_answer(self.index, answer)
        self.controller.show_frame(self.index + 1)

# Sample questions (mix of multiple-choice and free-response)
questions = [
    {"text": "What is the capital of France?", "type": "multiple_choice", "options": ["Paris", "London", "Berlin", "Madrid"]},
    {"text": "Who developed the theory of relativity?", "type": "multiple_choice", "options": ["Newton", "Einstein", "Tesla", "Galileo"]},
    {"text": "What is your favorite programming language?", "type": "free_response"}
]

# Run the Quiz App
root = tk.Tk()
app = QuizApp(root, questions)
root.mainloop()
