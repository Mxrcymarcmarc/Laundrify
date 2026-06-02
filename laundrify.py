import tkinter as tk
from tkinter import ttk
import os
import db
import ui

def main():
    root = tk.Tk()
    root.title('Laundrify')
    root.geometry('1500x800')
    root.resizable(False, False)
    
    root.columnconfigure(0, weight=1)
    root.columnconfigure(1, weight=1)
    
    page_title = "New Order"
    
    # Header
    label_header = tk.Label(root, text=f"Laundrify - {page_title}", font=("Segoe UI", 24, "bold"))
    label_header.grid(row=0, column=0, columnspan=2, pady=20)
    
    # embed the frontend App into the existing root
    import frontend

    root.rowconfigure(1, weight=1)
    def set_title(t):
        label_header.config(text=t)

    app = frontend.App(root, show_header=False, title_callback=set_title)
    app.grid(row=1, column=0, columnspan=2, sticky='nsew')

    root.mainloop()
    
if __name__ == '__main__':
    main()