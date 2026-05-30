import tkinter as tk
from tkinter import ttk
import os
import db
import ui


def main():
    db.init_db()
    root = tk.Tk()
    root.title('Laundrify')
    root.geometry('1000x700')

    nav = ttk.Frame(root)
    nav.pack(fill='x')
    ttk.Label(nav, text='Laundrify', font=('Segoe UI', 18, 'bold')).pack(side='left', padx=10)

    container = ttk.Frame(root)
    container.pack(fill='both', expand=True)

    frames = {}
    for F in (ui.NewOrderFrame, ui.OrdersFrame, ui.ReportsFrame):
        frame = F(container, root)
        frame.grid(row=0, column=0, sticky='nsew')
        frames[F.__name__] = frame

    # simple toolbar
    tb = ttk.Frame(root)
    tb.pack(fill='x')
    def show(name):
        for f in frames.values():
            f.grid_remove()
        frames[name].grid()

    ttk.Button(tb, text='New Order', command=lambda: show('NewOrderFrame')).pack(side='left')
    ttk.Button(tb, text='Orders', command=lambda: show('OrdersFrame')).pack(side='left')
    ttk.Button(tb, text='Reports', command=lambda: show('ReportsFrame')).pack(side='left')

    show('OrdersFrame')
    root.mainloop()


if __name__ == '__main__':
    main()
