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
    
    #Header
    label_header = tk.Label(
        root, 
        text=f"Laundrify - {page_title}", 
        font=("Segoe UI", 24, "bold")
    ).grid(row=0, column=0, columnspan=2, pady=20)
    
    frames = {}

    for F in (ui.NewOrderFrame, ui.OrdersFrame):
        frame = F(root, root)
        frame.grid(row=1, column=0, columnspan=2, sticky='nsew')
        frames[F.__name__] = frame
    
    def show(name):
        for f in frames.values():
            f.grid_remove()
        frames[name].grid()
    
    
        
    
    

    root.mainloop()
    
if __name__ == '__main__':
    main()