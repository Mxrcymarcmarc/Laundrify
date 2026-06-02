import tkinter as tk
from tkinter import ttk

class App(tk.Frame):
    def __init__(self, parent, show_header=True, backend=None, title_callback=None):
        super().__init__(parent)
        self.backend = backend
        self.title_callback = title_callback or (lambda t: None)

        # decide where to place content rows depending on header
        content_row = 0 if not show_header else 1

        if show_header:
            header = tk.Label(self, text="Laundrify - {New Order}", font=("Helvetica", 24))
            header.grid(row=0, column=0, sticky="ew", padx=8, pady=8)

        # layout: content + nav
        self.rowconfigure(content_row, weight=1)
        self.columnconfigure(0, weight=1)

        # container for pages
        container = tk.Frame(self)
        container.grid(row=content_row, column=0, sticky="nsew", padx=8, pady=8)
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        # create pages
        self.pages = {}
        for Page in (NewOrderPage, ViewOrderPage, ReportsPage):
            page = Page(container, self)
            page.grid(row=0, column=0, sticky="nsew")
            self.pages[Page.__name__] = page

        # bottom navigation
        nav = tk.Frame(self)
        nav.grid(row=content_row+1, column=0, sticky="ew", padx=8, pady=8)
        nav.columnconfigure((0,1,2), weight=1)

        btn_new = ttk.Button(nav, text="New Order", command=lambda: self.show("NewOrderPage"))
        btn_view = ttk.Button(nav, text="View Order", command=lambda: self.show("ViewOrderPage"))
        btn_reports = ttk.Button(nav, text="Reports", command=lambda: self.show("ReportsPage"))

        btn_new.grid(row=0, column=0, padx=12, ipadx=10, sticky="ew")
        btn_view.grid(row=0, column=1, padx=12, ipadx=10, sticky="ew")
        btn_reports.grid(row=0, column=2, padx=12, ipadx=10, sticky="ew")

        self.show("NewOrderPage")

    def show(self, name):
        titles = {
            "NewOrderPage": "Laundrify - New Order",
            "ViewOrderPage": "Laundrify - View Order",
            "ReportsPage": "Laundrify - Reports",
        }
        # update outer header if provided
        self.title_callback(titles.get(name, "Laundrify"))
        self.pages[name].tkraise()


class NewOrderPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bd=1, relief="solid")
        # two-column main area like mockup
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(0, weight=1)

        left = tk.Frame(self, bd=1, relief="groove", padx=12, pady=12)
        left.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        right = tk.Frame(self, bd=1, relief="groove", padx=12, pady=12)
        right.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)

        # left form using grid only
        left.columnconfigure(1, weight=1)
        for i in range(8):
            left.rowconfigure(i, pad=6)

        tk.Label(left, text="Name:").grid(row=0, column=0, sticky="w")
        self.name_entry = tk.Entry(left)
        self.name_entry.grid(row=0, column=1, sticky="ew")

        tk.Label(left, text="Address:").grid(row=1, column=0, sticky="w")
        self.address_entry = tk.Entry(left)
        self.address_entry.grid(row=1, column=1, sticky="ew")

        tk.Label(left, text="Email:").grid(row=2, column=0, sticky="w")
        self.email_entry = tk.Entry(left)
        self.email_entry.grid(row=2, column=1, sticky="ew")

        tk.Label(left, text="Phone:").grid(row=3, column=0, sticky="w")
        self.phone_entry = tk.Entry(left)
        self.phone_entry.grid(row=3, column=1, sticky="ew")

        tk.Label(left, text="Quantity:").grid(row=4, column=0, sticky="w")
        self.qty_entry = tk.Entry(left)
        self.qty_entry.grid(row=4, column=1, sticky="ew")

        tk.Label(left, text="Service:").grid(row=5, column=0, sticky="nw")
        self.service_listbox = tk.Listbox(left, height=6, exportselection=False)
        services = ["Wash & Fold","Dry Clean","Press","Alteration","Pickup/Delivery"]
        for s in services:
            self.service_listbox.insert("end", s)
        self.service_listbox.grid(row=5, column=1, sticky="nsew")
        left.rowconfigure(5, weight=1)

        add_btn = tk.Button(left, text="Add Item", command=self.add_item)
        add_btn.grid(row=6, column=0, columnspan=2, pady=10)

        # right - instructions and order items area
        tk.Label(right, text="Instruction", font=("TkDefaultFont", 10, "bold")).grid(row=0, column=0, sticky="w")
        instr_text = (
            "To create an order: fill customer details, select a service and quantity, then press 'Add Item'.\n"
            "Items will appear below. Select an item and press 'Remove Item' to delete it.\n"
            "When ready, press 'Create Order' to save (not implemented)."
        )
        instr = tk.Label(right, text=instr_text, anchor="nw", justify="left", wraplength=420)
        instr.grid(row=1, column=0, sticky="ew", pady=6)

        # order items table
        right.rowconfigure(2, weight=1)
        columns = ("service", "quantity", "price")
        self.order_tree = ttk.Treeview(right, columns=columns, show="headings")
        for col in columns:
            self.order_tree.heading(col, text=col.capitalize())
            self.order_tree.column(col, anchor="w")
        self.order_tree.grid(row=2, column=0, sticky="nsew", pady=6)

        # buttons under the table
        btn_frame = tk.Frame(right)
        btn_frame.grid(row=3, column=0, sticky="ew", pady=(8,0))
        btn_frame.columnconfigure((0,1), weight=1)
        remove_btn = tk.Button(btn_frame, text="Remove Item", command=self.remove_item)
        create_btn = tk.Button(btn_frame, text="Create Order", command=self.create_order)
        remove_btn.grid(row=0, column=0, padx=8, sticky="ew")
        create_btn.grid(row=0, column=1, padx=8, sticky="ew")

        # simple price map
        self.price_map = {s: "00.00" for s in services}

    def add_item(self):
        sel = self.service_listbox.curselection()
        if not sel:
            return
        service = self.service_listbox.get(sel[0])
        qty = self.qty_entry.get().strip() or "1"
        # validate qty numeric
        try:
            int(qty)
        except ValueError:
            qty = "1"
        price = self.price_map.get(service, "00.00")
        self.order_tree.insert("", "end", values=(service, qty, price))

    def remove_item(self):
        sel = self.order_tree.selection()
        for iid in sel:
            self.order_tree.delete(iid)

    def create_order(self):
        # placeholder for saving to DB
        print("Create order pressed - not implemented")


class ViewOrderPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        tk.Label(self, text="View Orders", font=("Helvetica", 16)).grid(row=0, column=0, padx=8, pady=8)
        tree = ttk.Treeview(self, columns=("name","phone"), show="headings")
        tree.heading("name", text="Name"); tree.heading("phone", text="Phone")
        tree.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        self.rowconfigure(1, weight=1); self.columnconfigure(0, weight=1)


class ReportsPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        tk.Label(self, text="Reports", font=("Helvetica", 16)).grid(row=0, column=0, padx=8, pady=8)
        tk.Label(self, text="(Report content goes here)").grid(row=1, column=0, padx=8, pady=8)


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Laundrify - Frontend")
    root.geometry("1000x650")
    app = App(root)
    app.grid(row=0, column=0, sticky='nsew')
    root.rowconfigure(0, weight=1)
    root.columnconfigure(0, weight=1)
    root.mainloop()
