"""Sharp Quiz desktop application entry point."""

import tkinter as tk

from quiz import SharpQuiz


def main() -> None:
    root = tk.Tk()
    SharpQuiz(root)
    root.mainloop()


if __name__ == "__main__":
    main()
