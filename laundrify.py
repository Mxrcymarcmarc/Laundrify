"""
Laundrify - Application Entry Point

This module serves as the bootstrap script for the Laundrify desktop application.
It handles database initialization, splash screen presentation, Windows application
grouping ID configuration, resource path resolution, and initial window management
to embed and start the Tkinter frontend GUI.
"""

import tkinter as tk
from tkinter import ttk
import os
import db
import ctypes
import sys

# Styling theme configuration constants
PRIMARY = "#F0EDE5"      # Light beige background
SECONDARY = "#4A6FA5"    # Slate blue primary color
ACCENT = "#B8C5D6"       # Steel gray accent color
HDR_TEXT = ("Cooper Black", 24)
REG_TEXT = ("Arial", 12)

def get_asset_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller.
    
    Args:
        relative_path (str): The relative path to the asset file.
        
    Returns:
        str: Absolute path to the asset resource.
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def show_splash(root):
    """Create and display an indeterminate splash screen.
    
    Creates a borderless TopLevel Tkinter window centered on the screen,
    with a progress bar, logo, and title, to run while the main app starts.
    
    Args:
        root (tk.Tk): The parent Tkinter root window instance.
        
    Returns:
        tk.Toplevel: The created splash screen window instance.
    """
    splash = tk.Toplevel()
    splash.overrideredirect(True) # Remove standard window decorations
    splash.configure(bg=PRIMARY)
    splash.attributes('-topmost', True) # Keep on top of other windows
    splash.lift()

    # Outer border content frame
    content = tk.Frame(splash, bg=PRIMARY, bd=2, relief='ridge')
    content.pack(expand=True, fill='both', padx=10, pady=10)

    # Header section container
    header_frame = tk.Frame(content, bg=PRIMARY)
    header_frame.pack(pady=(20, 10))

    # Optional logo loading
    try:
        splash.logo_scaled = tk.PhotoImage(file=get_asset_path("Laundrify logo rounded.png"))
        logo_label = tk.Label(header_frame, image=splash.logo_scaled, bg=PRIMARY)
        logo_label.pack(side='left', padx=(0, 10))
    except Exception:
        pass

    # Title and subtitle labels
    title_label = tk.Label(header_frame, text="Laundrify", font=("Cooper Black", 36), bg=PRIMARY, fg=SECONDARY)
    title_label.pack(side='left')

    subtitle_label = tk.Label(content, text="Preparing your experience...", font=("Arial", 14), bg=PRIMARY, fg=SECONDARY)
    subtitle_label.pack(pady=(0, 18))

    # Animated progress bar
    progress = ttk.Progressbar(content, mode='indeterminate', length=320)
    progress.pack(pady=(0, 18))
    progress.start(12)

    # Center the splash screen on the monitor
    width, height = 460, 220
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    splash.geometry(f"{width}x{height}+{x}+{y}")
    splash.update_idletasks()
    splash.focus_force()

    return splash


def main():
    """Application entry point function.
    
    Initializes the database schema, configures OS grouping layout rules,
    configures window properties and icons, displays the splash screen,
    and initializes the main application layout/views.
    """
    import sys
    import os

    # 1. Force Windows to assign a fresh process grouping layout identity
    # This ensures taskbar grouping and window icons display correctly on Windows OS
    try:
        myappid = 'laundrify.system.v2'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    # Helper function to find the logo asset inside the compiled .exe environment
    def get_runtime_asset(relative_path):
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    # Initialize database
    db.init_db()
    
    root = tk.Tk()
    root.title('Laundrify')

    # 2. Bind the extracted asset to the active window runtime instance
    try:
        # Use the helper path tracker to locate the extracted logo resource
        logo_path = get_runtime_asset("Laundrify logo rounded.png")
        
        if os.path.exists(logo_path):
            root.logo_icon = tk.PhotoImage(file=logo_path)
            # Setting this to True ensures the window icon is inherited by the taskbar!
            root.iconphoto(True, root.logo_icon)
    except Exception:
        pass
        
    root.geometry('1500x750')
    root.resizable(False, False)
    root.configure(bg=PRIMARY)
    
    # Hide root window while splash is shown
    root.withdraw()

    splash = show_splash(root)

    def start_app():
        """Destroy the splash screen, unhide the root window, and initialize page views."""
        splash.destroy()
        root.deiconify()

        root.columnconfigure(0, weight=1)
        root.columnconfigure(1, weight=1)
        
        page_title = "New Order"
        
        # Header bar setup
        header_frame = tk.Frame(root, bg=SECONDARY)
        header_frame.grid(row=0, column=0, columnspan=2, sticky='ew')
        header_frame.columnconfigure(0, weight=1)

        label_header = tk.Label(header_frame, text=f"Laundrify - {page_title}", font=HDR_TEXT, bg=SECONDARY, fg="white")
        label_header.grid(row=0, column=0, sticky='ew', pady=18)
        label_header.configure(anchor='center')

        # Embed the frontend App into the existing root
        import frontend

        root.rowconfigure(0, weight=0)
        root.rowconfigure(1, weight=0)
        root.rowconfigure(2, weight=1)

        def set_title(t):
            """Callback function to dynamically update header text when pages change."""
            label_header.config(text=t)

        app = frontend.App(root, show_header=False, title_callback=set_title)
        app.grid(row=2, column=0, columnspan=2, sticky='nsew')
        app.configure(bg=PRIMARY)

    # Delay the start of the app by 1200ms to show splash screen transitions
    root.after(1200, start_app)
    root.mainloop()
    
if __name__ == '__main__':
    main()