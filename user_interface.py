import tkinter as tk

# Create the main application window
root = tk.Tk()
root.title("Sharp")

root.state('zoomed')

# Create an Entry widget
entry = tk.Entry(root, width=30)
entry.pack(pady=10)

# Button to get text from the entry
def get_text():
    print("Entered Text:", entry.get())

btn = tk.Button(root, text="Print Text", command=get_text)
btn.pack(pady=5)

# Run the application
root.mainloop()
