import tkinter as tk
from tkinter import ttk
import os
import db

PRIMARY = "#F0EDE5"
SECONDARY = "#4A6FA5"
ACCENT = "#B8C5D6"
HDR_TEXT = ("Cooper Black", 24)
REG_TEXT = ("Arial", 12)


def show_splash(root):
    splash = tk.Toplevel()
    splash.overrideredirect(True)
    splash.configure(bg=PRIMARY)
    splash.attributes('-topmost', True)
    splash.lift()

    content = tk.Frame(splash, bg=PRIMARY, bd=2, relief='ridge')
    content.pack(expand=True, fill='both', padx=10, pady=10)

    header_frame = tk.Frame(content, bg=PRIMARY)
    header_frame.pack(pady=(20, 10))

    try:
        splash.logo_scaled = tk.PhotoImage(file="Laundrify logo rounded.png")
        logo_label = tk.Label(header_frame, image=splash.logo_scaled, bg=PRIMARY)
        logo_label.pack(side='left', padx=(0, 10))
    except Exception:
        pass

    title_label = tk.Label(header_frame, text="Laundrify", font=("Cooper Black", 36), bg=PRIMARY, fg=SECONDARY)
    title_label.pack(side='left')

    subtitle_label = tk.Label(content, text="Preparing your experience...", font=("Arial", 14), bg=PRIMARY, fg=SECONDARY)
    subtitle_label.pack(pady=(0, 18))

    progress = ttk.Progressbar(content, mode='indeterminate', length=320)
    progress.pack(pady=(0, 18))
    progress.start(12)

    width, height = 460, 240
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    splash.geometry(f"{width}x{height}+{x}+{y}")
    splash.update_idletasks()
    splash.focus_force()

    return splash


def main():
    # Initialize database
    db.init_db()
    
    root = tk.Tk()
    root.title('Laundrify')
    try:
        root.logo_icon = tk.PhotoImage(file="Laundrify logo rounded.png")
        root.iconphoto(False, root.logo_icon)
    except Exception:
        pass
    root.geometry('1500x750')
    root.resizable(False, False)
    root.configure(bg=PRIMARY)
    
    root.withdraw()

    splash = show_splash(root)

    def start_app():
        splash.destroy()
        root.deiconify()

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
        root.rowconfigure(2, weight=1)

        def set_title(t):
            label_header.config(text=t)

        app = frontend.App(root, show_header=False, title_callback=set_title)
        app.grid(row=2, column=0, columnspan=2, sticky='nsew')
        app.configure(bg=PRIMARY)

    root.after(1200, start_app)
    root.mainloop()
    
if __name__ == '__main__':
    main()