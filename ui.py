import tkinter as tk
from tkinter import ttk, messagebox
import os
import db

class NewOrderFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.create_widgets()

    def create_widgets(self):
        ttk.LabelFrame(
            self, 
            text="New Order", 
            padding=10
        ).grid(row=0, column=0, columnspan=2, pady=10)
        # Add your form fields and buttons here
        
class OrdersFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.create_widgets()

    def create_widgets(self):
        ttk.LabelFrame(
            self, 
            text="Orders", 
            padding=10
        ).grid(row=0, column=0, columnspan=2, pady=10)
        #Add your orders list and buttons here 
        
class ReportsFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.create_widgets()

    def create_widgets(self):
        ttk.LabelFrame(
            self, 
            text="Reports", 
            padding=10
        ).grid(row=0, column=0, columnspan=2, pady=10)
        #Add your reports list and buttons here

    