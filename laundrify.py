import tkinter as tk
from tkinter import ttk
import os
import db

PRIMARY = "#F0EDE5"
SECONDARY = "#4A6FA5"
ACCENT = "#B8C5D6"
HDR_TEXT = ("Cooper Black", 24)
REG_TEXT = ("Arial", 12)

def main():
    # Initialize database
    db.init_db()
    
    root = tk.Tk()
    root.title('Laundrify')
    root.geometry('1500x750')
    root.resizable(False, False)
    root.configure(bg=PRIMARY)
    
    root.columnconfigure(0, weight=1)
    root.columnconfigure(1, weight=1)
    
    page_title = "New Order"
    
    # Header bar
    header_frame = tk.Frame(root, bg=SECONDARY)
    header_frame.grid(row=0, column=0, columnspan=2, sticky='ew')
    header_frame.columnconfigure(0, weight=1)

    label_header = tk.Label(header_frame, text=f"Laundrify - {page_title}", font=HDR_TEXT, bg=SECONDARY, fg="white")
    label_header.grid(row=0, column=0, sticky='ew', pady=18)
    label_header.configure(anchor='center')

    # embed the frontend App into the existing root
    import frontend

    root.rowconfigure(0, weight=0)
    root.rowconfigure(1, weight=0)
    root.rowconfigure(2, weight=0)
    def set_title(t):
        label_header.config(text=t)

    app = frontend.App(root, show_header=False, title_callback=set_title)
    app.grid(row=2, column=0, columnspan=2, sticky='nsew')
    app.configure(bg=PRIMARY)

    root.mainloop()
    
if __name__ == '__main__':
    main()