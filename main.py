import tkinter as tk
from quiz import Quiz

# Sample questions
questions = [
    {"text": "What is the capital of France?", "type": "multiple_choice", "options": ["Paris", "London", "Berlin", "Madrid"]},
    {"text": "Who developed the theory of relativity?", "type": "multiple_choice", "options": ["Newton", "Einstein", "Tesla", "Galileo"]},
    {"text": "What is your favorite programming language?", "type": "free_response"}
]

# Time limit (in seconds) per question
time_per_question = 3 

# Run the Quiz App
root = tk.Tk()
app = Quiz(root, questions, time_per_question)
root.mainloop()