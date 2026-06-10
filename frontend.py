import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont

from db import get_received_report_data, get_revenue_report_data, get_ready_report_data, get_overdue_report_data, get_top_services_report_data, get_next_customer_id

PRIMARY = "#F0EDE5"
SECONDARY = "#4A6FA5"
ACCENT = "#B8C5D6"
HDR_TEXT = ("Cooper Black", 24)
HDR2_TEXT = ("Arial Black", 15)
TTL_TEXT = ("Arial", 11, "bold")
REG_TEXT = ("Arial", 11)

def reload_services_for_page(page):
    """Populate page.service_map from DB and refresh the service combobox values."""
    import db
    # base defaults
    page.service_map = {
        "Wash, Dry & Fold": ("weight", 70),
        "Wash & Dry": ("weight", 50),
        "Dry Cleaning": ("size", {"small": 110, "large": 150}),
        "Ironing": ("size", {"small": 20, "large": 30})
    }
    try:
        services = db.get_services()
        if not services:
            db.restore_default_services()
            services = db.get_services()
        for s in services:
            name = s['Service_Type']
            price = s['Service_Unit_Price'] or 0
            try:
                unit = (s['Service_Unit'] or 'pcs').lower()
            except Exception:
                unit = 'pcs'
            if unit == 'kg':
                page.service_map[name] = ('weight', price)
            else:
                # for pcs show size radios by default (small/large)
                page.service_map[name] = ('size', {'small': price, 'large': price})
    except Exception:
        pass
    # update combobox values if combobox exists
    try:
        page.service_combo['values'] = list(page.service_map.keys())
    except Exception:
        pass

class App(tk.Frame):
    def __init__(self, parent, show_header=True, backend=None, title_callback=None):
        super().__init__(parent)
        self.backend = backend
        self.title_callback = title_callback or (lambda t: None)
        self.configure(bg=PRIMARY)

        # decide where to place content rows depending on header
        content_row = 2 if show_header else 0

        if show_header:
            header = tk.Label(self, text="Laundrify - {New Order}", font=("Helvetica", 24), bg=SECONDARY, fg="white")
            header.grid(row=0, column=0, sticky="ew", padx=0, pady=(15))

            separator = tk.Frame(self, height=4, bg=SECONDARY)
            separator.grid(row=1, column=0, sticky="ew", padx=0, pady=(0,4))
            separator.grid_propagate(False)

        # layout: content + nav
        self.columnconfigure(0, weight=1)
        self.rowconfigure(content_row, weight=1)
        self.rowconfigure(content_row+1, weight=0)

        # container for pages
        container = tk.Frame(self)
        container.grid(row=content_row, column=0, sticky="ew", padx=8, pady=(8, 0))
        container.rowconfigure(0, weight=0)
        container.columnconfigure(0, weight=1)

        # create pages
        self.pages = {}
        for Page in (NewOrderPage, ViewOrderPage, ReportsPage):
            page = Page(container, self)
            page.grid(row=0, column=0, sticky="nsew")
            self.pages[Page.__name__] = page

        # bottom navigation
        nav = tk.Frame(self, bg=PRIMARY)
        nav.grid(row=content_row+1, column=0, sticky="ew", padx=8, pady=15)
        nav.columnconfigure((0,1,2), weight=1)

        self.nav_buttons = {}
        self.current_page = "NewOrderPage"
        
        btn_new = tk.Button(nav, text="New Order", font=TTL_TEXT, command=lambda: self.show("NewOrderPage"), 
                            height=2, cursor="hand2")
        btn_view = tk.Button(nav, text="View Order", font=TTL_TEXT, command=lambda: self.show("ViewOrderPage"), 
                            height=2, cursor="hand2")
        btn_reports = tk.Button(nav, text="Reports", font=TTL_TEXT, command=lambda: self.show("ReportsPage"), 
                            height=2, cursor="hand2")

        self.nav_buttons["NewOrderPage"] = btn_new
        self.nav_buttons["ViewOrderPage"] = btn_view
        self.nav_buttons["ReportsPage"] = btn_reports

        btn_new.grid(row=0, column=0, padx=12, sticky="ew")
        btn_view.grid(row=0, column=1, padx=12, sticky="ew")
        btn_reports.grid(row=0, column=2, padx=12, sticky="ew")

        self.show("NewOrderPage")

    def show(self, name):
        titles = {
            "NewOrderPage": "Laundrify - New Order",
            "ViewOrderPage": "Laundrify - View Order",
            "ReportsPage": "Laundrify - Reports",
        }
        # Update button styles
        self.current_page = name
        for page_name, btn in self.nav_buttons.items():
            if page_name == name:
                btn.config(bg=SECONDARY, fg="white", activebackground=SECONDARY, activeforeground="white", relief="sunken", bd=2)
            else:
                btn.config(bg=ACCENT, fg=SECONDARY, activebackground=ACCENT, activeforeground=SECONDARY, relief="raised", bd=1)
        
        # update outer header if provided
        self.title_callback(titles.get(name, "Laundrify"))
        # auto-refresh view page when shown
        try:
            if name == 'ViewOrderPage':
                self.pages[name].refresh_all()
        except Exception:
            pass
        self.pages[name].tkraise()


class NewOrderPage(tk.Frame):           
    def __init__(self, parent, controller):
        super().__init__(parent, bd=0, relief="solid")
        # two-column main area like mockup
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(0, weight=1)
        self.configure(bg=PRIMARY)

        left = tk.Frame(self, bd=1, padx=12, pady=12, bg=PRIMARY)
        left.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        right = tk.Frame(self, bd=1, padx=12, pady=12, bg=PRIMARY)
        right.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)

        # left form using grid only
        left.columnconfigure(0, minsize=80)
        left.columnconfigure(1, weight=1)
        for i in range(2):
            left.rowconfigure(i, pad=5)
        for i in range(2, 10):
            left.rowconfigure(i, pad=5)

        cust_num = get_next_customer_id()
        tk.Label(left, text=f"Customer Number: {cust_num}", font=HDR2_TEXT, bg=PRIMARY).grid(row=0, column=0, columnspan=2, sticky="w")
        
        tk.Label(left, text="First Name:", font=TTL_TEXT, bg=PRIMARY).grid(row=1, column=0, sticky="w")
        self.first_name_entry = tk.Entry(left, font=REG_TEXT, highlightthickness=2, highlightcolor=SECONDARY)
        self.first_name_entry.grid(row=1, column=1, sticky="ew", ipady=3)

        tk.Label(left, text="Last Name:", font=TTL_TEXT, bg=PRIMARY).grid(row=2, column=0, sticky="w")
        self.last_name_entry = tk.Entry(left, font=REG_TEXT, highlightthickness=2, highlightcolor=SECONDARY)
        self.last_name_entry.grid(row=2, column=1, sticky="ew", ipady=3)

        tk.Label(left, text="Address:", font=TTL_TEXT, bg=PRIMARY).grid(row=3, column=0, sticky="w")
        self.address_entry = tk.Entry(left, font=REG_TEXT, highlightthickness=2, highlightcolor=SECONDARY)
        self.address_entry.grid(row=3, column=1, sticky="ew", ipady=3)

        tk.Label(left, text="Email:", font=TTL_TEXT, bg=PRIMARY).grid(row=4, column=0, sticky="w")
        self.email_entry = tk.Entry(left, font=REG_TEXT, highlightthickness=2, highlightcolor=SECONDARY)
        self.email_entry.grid(row=4, column=1, sticky="ew", ipady=3)

        tk.Label(left, text="Phone:", font=TTL_TEXT, bg=PRIMARY).grid(row=5, column=0, sticky="w")
        self.phone_entry = tk.Entry(left, font=REG_TEXT, highlightthickness=2, highlightcolor=SECONDARY)
        self.phone_entry.grid(row=5, column=1, sticky="ew", ipady=3)
        # Register phone validation - only numbers
        vcmd_phone = left.register(self.validate_phone)
        self.phone_entry.config(validate='key', validatecommand=(vcmd_phone, '%P'))

        tk.Label(left, text="Service:", font=TTL_TEXT, bg=PRIMARY).grid(row=6, column=0, sticky="w")
        # default in-code service map (used for UI behavior). Prices will be updated from DB if available.
        self.service_map = {
            "Wash, Dry & Fold": ("weight", 70),
            "Wash & Dry": ("weight", 50),
            "Dry Cleaning": ("size", {"small": 110, "large": 150}),
            "Ironing": ("size", {"small": 20, "large": 30})
        }
        # Load services from DB and refresh combobox
        reload_services_for_page(self)

        self.service_combo = ttk.Combobox(left, values=list(self.service_map.keys()), state="readonly", font=REG_TEXT)
        self.service_combo.grid(row=6, column=1, sticky="ew", ipady=3)
        self.service_combo.bind("<<ComboboxSelected>>", self.on_service_selected)

        # Dynamic field frame (weight or size selection)
        self.dynamic_frame = tk.Frame(left, bg=PRIMARY)
        self.dynamic_frame.grid(row=7, column=0, columnspan=2, sticky="ew", pady=6)
        self.dynamic_frame.columnconfigure(0, minsize=80)
        self.dynamic_frame.columnconfigure(1, weight=1)
        # unit price display (updated on service selection)
        self.unit_price_var = tk.StringVar()
        unit_price_label = tk.Label(self.dynamic_frame, textvariable=self.unit_price_var, fg=SECONDARY)
        unit_price_label.grid(row=2, column=0, columnspan=2, sticky='w')

        tk.Label(left, text="Additional\nNotes:", font=TTL_TEXT, bg=PRIMARY).grid(row=8, column=0, sticky="nw")
        self.notes_text = tk.Text(left, height=3, width=30, font=REG_TEXT, highlightthickness=2, highlightcolor=SECONDARY)
        self.notes_text.grid(row=8, column=1, sticky="ew", ipady=3)

        add_btn = tk.Button(left, text="Add Item", font=TTL_TEXT, bg=SECONDARY, fg=PRIMARY, command=self.add_item, width=20)
        add_btn.grid(row=9, column=0, columnspan=2, pady=10)

        # right - instructions and order items area
        # header with Instruction label and gear button on same row
        header_frame = tk.Frame(right, bg=PRIMARY)
        header_frame.grid(row=0, column=0, sticky="ew")
        header_frame.columnconfigure(0, weight=1)
        header_frame.columnconfigure(1, weight=0)
        tk.Label(header_frame, text="Instruction", font=TTL_TEXT, bg=PRIMARY).grid(row=0, column=0, sticky="w")
        gear_btn = tk.Button(header_frame, text='⚙', font=("Arial", 12), bg=SECONDARY, fg=PRIMARY, width=3, command=self.open_services_window)
        gear_btn.grid(row=0, column=1, sticky='ne', padx=(6,0), )

        instr_text = (
            "To create an order: fill customer details, select a service, then enter weight or size, then press 'Add Item'.\n"
            "Items will appear below. Select an item and press 'Remove Item' to delete it.\n"
            "When ready, press 'Create Order' to save."
        )
        instr_frame = tk.Frame(right, bg=PRIMARY)
        instr_frame.grid(row=1, column=0, sticky="ew", pady=6)
        instr_frame.columnconfigure(0, weight=1)
        instr = tk.Label(instr_frame, text=instr_text, font=REG_TEXT, bg=PRIMARY, anchor="nw", justify="left", wraplength=800)
        instr.grid(row=0, column=0, sticky="w")

        # order items table
        right.rowconfigure(2, weight=1)
        columns = ("service", "quantity", "price")
        self.order_tree = ttk.Treeview(right, columns=columns, show="headings")
        for col in columns:
            self.order_tree.heading(col, text=col.capitalize())
            self.order_tree.column(col, anchor="w")
        self.order_tree.grid(row=2, column=0, sticky="nsew", pady=6)

        # buttons under the table
        btn_frame = tk.Frame(right, bg=PRIMARY)
        btn_frame.grid(row=3, column=0, sticky="ew", pady=(8,0))
        btn_frame.columnconfigure((0,1,2,3), weight=1)
        remove_btn = tk.Button(btn_frame, text="Remove Item", font=TTL_TEXT, bg=PRIMARY, fg=SECONDARY, command=self.remove_item, width=5)
        remove_btn.grid(row=0, column=0, sticky="ew")
        clear_btn = tk.Button(btn_frame, text="Remove All Items", font=TTL_TEXT, bg=PRIMARY, fg=SECONDARY, command=self.remove_all_items, width=10)
        clear_btn.grid(row=0, column=1, padx=8, sticky="ew")
        create_btn = tk.Button(btn_frame, text="Create Order", font=TTL_TEXT, bg=SECONDARY, fg=PRIMARY, highlightcolor=SECONDARY, command=self.create_order)
        create_btn.grid(row=0, column=3, padx=(0, 0), sticky="ew")

        self.weight_var = None
        self.size_var = None

    def on_service_selected(self, event=None):
        # Clear previous widgets in dynamic frame
        for widget in self.dynamic_frame.winfo_children():
            widget.destroy()

        service = self.service_combo.get()
        if not service:
            return

        service_type, pricing = self.service_map[service]

        if service_type == "weight":
            # Show weight entry field
            tk.Label(self.dynamic_frame, text="Weight (kg):", font=TTL_TEXT, bg=PRIMARY).grid(row=0, column=0, sticky="w")
            self.weight_var = tk.Entry(self.dynamic_frame, font=REG_TEXT, highlightthickness=2, highlightcolor=SECONDARY)
            self.weight_var.grid(row=0, column=1, sticky="ew", ipady=3)
            self.size_var = None
            self.qty_var = None
            # show unit price for weight service
            try:
                self.unit_price_var.set(f"Unit price: ₱{float(pricing):.2f}")
            except Exception:
                self.unit_price_var.set("")

        else:
            # size-based or per-item
            if service_type == 'size':
                # Show radio buttons for small/large
                tk.Label(self.dynamic_frame, text="Size:", font=TTL_TEXT, bg=PRIMARY).grid(row=0, column=0, sticky="w")
                self.size_var = tk.StringVar(value="small")
                rb_frame = tk.Frame(self.dynamic_frame, bg=PRIMARY)
                rb_frame.grid(row=0, column=1, sticky="ew")
                tk.Radiobutton(rb_frame, text="Small", font=REG_TEXT, bg=PRIMARY, variable=self.size_var, value="small").pack(side="left", padx=5)
                tk.Radiobutton(rb_frame, text="Large", font=REG_TEXT, bg=PRIMARY, variable=self.size_var, value="large").pack(side="left", padx=5)
                
                # Show quantity entry field
                tk.Label(self.dynamic_frame, text="Quantity:", font=TTL_TEXT, bg=PRIMARY).grid(row=1, column=0, sticky="w")
                self.qty_var = tk.Entry(self.dynamic_frame, font=REG_TEXT, highlightthickness=2, highlightcolor=SECONDARY)
                # Register quantity validation - only numbers
                vcmd_qty = self.dynamic_frame.register(self.validate_quantity)
                self.qty_var.config(validate='key', validatecommand=(vcmd_qty, '%P'))
                self.qty_var.grid(row=1, column=1, sticky="ew", ipady=3)
                self.weight_var = None
                # show price breakdown for sizes
                try:
                    small_p = pricing.get('small')
                    large_p = pricing.get('large')
                    self.unit_price_var.set(f"Prices: Small ₱{float(small_p):.2f} / Large ₱{float(large_p):.2f}")
                except Exception:
                    self.unit_price_var.set("")
            else:
                # per-item service: single quantity entry
                tk.Label(self.dynamic_frame, text="Quantity:", font=TTL_TEXT, bg=PRIMARY).grid(row=0, column=0, sticky="w")
                self.qty_var = tk.Entry(self.dynamic_frame, font=REG_TEXT, highlightthickness=2, highlightcolor=SECONDARY)
                vcmd_qty = self.dynamic_frame.register(self.validate_quantity)
                self.qty_var.config(validate='key', validatecommand=(vcmd_qty, '%P'))
                self.qty_var.grid(row=0, column=1, sticky="ew", ipady=3)
                self.weight_var = None
                self.size_var = None
                # show unit price
                try:
                    self.unit_price_var.set(f"Unit price: ₱{float(pricing):.2f}")
                except Exception:
                    self.unit_price_var.set("")
    
    def validate_phone(self, value):
        """Allow only numeric characters for phone"""
        if value == "":
            return True
        return value.isdigit()
    
    def validate_quantity(self, value):
        """Allow only numeric characters for quantity"""
        if value == "":
            return True
        return value.isdigit()

    def open_services_window(self):
        import db
        from tkinter import messagebox
        svc_win = tk.Toplevel(self)
        svc_win.title('Manage Services')
        svc_win.geometry('480x400')
        svc_win.resizable(False, False)
        svc_win.grab_set()

        container = tk.Frame(svc_win, padx=12, pady=12)
        container.pack(fill='both', expand=True)
        container.columnconfigure(0, weight=1)

        cols = ('Service', 'Price', 'Unit')
        tree = ttk.Treeview(container, columns=cols, show='headings')
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, anchor='w', width=160 if c=='Service' else 80)
        tree.grid(row=0, column=0, sticky='nsew')

        scrollbar = ttk.Scrollbar(container, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky='ns')

        # form for add/edit
        form = tk.Frame(container)
        form.grid(row=1, column=0, columnspan=2, sticky='ew', pady=8)
        form.columnconfigure(1, weight=1)
        tk.Label(form, text='Service Type:').grid(row=0, column=0, sticky='w')
        svc_entry = tk.Entry(form)
        svc_entry.grid(row=0, column=1, sticky='ew')
        tk.Label(form, text='Unit Price (₱):').grid(row=1, column=0, sticky='w')
        price_entry = tk.Entry(form)
        price_entry.grid(row=1, column=1, sticky='ew')
        tk.Label(form, text='Unit:').grid(row=2, column=0, sticky='w')
        unit_combo = ttk.Combobox(form, values=['pcs','kg'], state='readonly', width=6)
        unit_combo.grid(row=2, column=1, sticky='w')

        def load_services():
            for i in tree.get_children():
                tree.delete(i)
            for s in db.get_services():
                tree.insert('', 'end', iid=s['ServiceID'], values=(s['Service_Type'], f"{s['Service_Unit_Price']}", s['Service_Unit']))
        load_services()

        def on_select(evt):
            sel = tree.selection()
            if not sel:
                return
            sid = sel[0]
            vals = tree.item(sid, 'values')
            svc_entry.delete(0, tk.END); svc_entry.insert(0, vals[0])
            price_entry.delete(0, tk.END); price_entry.insert(0, vals[1])
            try:
                unit_combo.set(vals[2])
            except Exception:
                unit_combo.set('pcs')
        tree.bind('<<TreeviewSelect>>', on_select)

        def save():
            name = svc_entry.get().strip()
            price = price_entry.get().strip()
            unit = unit_combo.get() or 'pcs'
            if not name or not price:
                messagebox.showwarning('Missing', 'Please enter service name and price', parent=svc_win)
                return
            try:
                price_val = int(float(price))
            except Exception:
                messagebox.showerror('Invalid', 'Price must be a number', parent=svc_win)
                return
            sel = tree.selection()
            if sel:
                db.update_service(int(sel[0]), name, price_val, unit)
            else:
                db.add_service(name, price_val, unit)
            load_services()
            try:
                # refresh New Order service combobox
                reload_services_for_page(self)
            except Exception:
                pass
            messagebox.showinfo('Saved', 'Service saved', parent=svc_win)

        def restore_defaults():
            if messagebox.askyesno('Restore', 'Restore default services and prices?', parent=svc_win):
                db.restore_default_services()
                load_services()
                try:
                    reload_services_for_page(self)
                except Exception:
                    pass

        btn_frame = tk.Frame(container)
        btn_frame.grid(row=2, column=0, columnspan=2, sticky='ew', pady=10)
        btn_frame.columnconfigure((0,1,2), weight=1)
        tk.Button(btn_frame, text='Close', command=svc_win.destroy).grid(row=0, column=0, sticky='ew', padx=6)
        tk.Button(btn_frame, text='Save', command=save, bg='#3498db', fg='white').grid(row=0, column=1, sticky='ew', padx=6)
        tk.Button(btn_frame, text='Restore Defaults', command=restore_defaults, bg='#95a5a6', fg='white').grid(row=0, column=2, sticky='ew', padx=6)
        
    def add_item(self):
        from tkinter import messagebox
        
        service = self.service_combo.get()
        if not service:
            messagebox.showerror("Missing Service", "Please select a service before adding an item")
            return

        service_type, pricing = self.service_map[service]
        quantity = None
        price = None

        if service_type == "weight":
            if not self.weight_var:
                messagebox.showerror("Missing Field", f"Weight (kg) field is required for {service}")
                return
            weight_str = self.weight_var.get().strip()
            if not weight_str:
                messagebox.showerror("Missing Field", f"Please enter a weight (kg) for {service}")
                return
            try:
                weight = float(weight_str)
                quantity = f"{weight} kg"
                # pricing may be a string or number
                try:
                    unit_price = float(pricing)
                except Exception:
                    unit_price = float(pricing.get('price', 0)) if isinstance(pricing, dict) else 0.0
                price = weight * unit_price
            except ValueError:
                messagebox.showerror("Invalid Input", "Weight must be a valid number")
                return
        else:  # size-based or per-item
            if service_type == 'size' or service_type == 'item':
                # size-based: size_var and qty_var; item-based: treat as qty entry
                if service_type == 'size':
                    if not self.size_var or not self.qty_var:
                        messagebox.showerror("Missing Field", f"Size and Quantity fields are required for {service}")
                        return
                    size = self.size_var.get()
                    if not size:
                        messagebox.showerror("Missing Field", f"Please select a size (Small/Large) for {service}")
                        return
                    qty_str = self.qty_var.get().strip()
                    if not qty_str:
                        messagebox.showerror("Missing Field", f"Please enter a quantity for {service}")
                        return
                    try:
                        qty = int(qty_str)
                        if qty <= 0:
                            messagebox.showerror("Invalid Input", "Quantity must be greater than 0")
                            return
                    except ValueError:
                        messagebox.showerror("Invalid Input", "Quantity must be a valid number")
                        return
                    # pricing might be dict or single value
                    if isinstance(pricing, dict):
                        price_per_item = float(pricing.get(size, 0))
                    else:
                        price_per_item = float(pricing)
                    quantity = f"{qty}x {size.capitalize()}"
                    price = price_per_item * qty
                else:
                    # per-item service: use qty entry (reuse qty_var if present or weight_var)
                    qty_str = self.qty_var.get().strip() if getattr(self, 'qty_var', None) else ''
                    if not qty_str:
                        messagebox.showerror("Missing Field", f"Please enter a quantity for {service}")
                        return
                    try:
                        qty = int(qty_str)
                        if qty <= 0:
                            messagebox.showerror("Invalid Input", "Quantity must be greater than 0")
                            return
                    except ValueError:
                        messagebox.showerror("Invalid Input", "Quantity must be a valid number")
                        return
                    price_per_item = float(pricing)
                    quantity = f"{qty} pcs"
                    price = price_per_item * qty
            else:
                messagebox.showerror("Configuration Error", "Unknown service type")
                return

        self.order_tree.insert("", "end", values=(service, quantity, f"₱ {price:.2f}"))
        # lock customer fields once first item is added
        try:
            self.first_name_entry.config(state='disabled')
            self.last_name_entry.config(state='disabled')
            self.address_entry.config(state='disabled')
            self.email_entry.config(state='disabled')
            self.phone_entry.config(state='disabled')
        except Exception:
            pass

    def remove_item(self):
        sel = self.order_tree.selection()
        for iid in sel:
            self.order_tree.delete(iid)
        # if no more items, unlock customer fields
        if not self.order_tree.get_children():
            try:
                self.first_name_entry.config(state='normal')
                self.last_name_entry.config(state='normal')
                self.address_entry.config(state='normal')
                self.email_entry.config(state='normal')
                self.phone_entry.config(state='normal')
            except Exception:
                pass
            
    def remove_all_items(self):
        all_iids = self.order_tree.get_children()

        for iid in all_iids:
            self.order_tree.delete(iid)
    
        try:
            self.first_name_entry.config(state='normal')
            self.last_name_entry.config(state='normal')
            self.address_entry.config(state='normal')
            self.email_entry.config(state='normal')
            self.phone_entry.config(state='normal')
        except Exception:
            pass

    def create_order(self):
        from tkinter import messagebox
        import db
        
        # Validate customer info
        first_name = self.first_name_entry.get().strip()
        last_name = self.last_name_entry.get().strip()
        phone = self.phone_entry.get().strip()
        address = self.address_entry.get().strip()
        email = self.email_entry.get().strip()
        notes = self.notes_text.get("1.0", "end-1c").strip()
        
        # Required field validation
        required_errors = []
        if not first_name:
            required_errors.append("First name is required")
        if not phone:
            required_errors.append("Phone is required")
        if not address:
            required_errors.append("Address is required")
        
        if required_errors:
            messagebox.showerror("Validation Error", "Please fill in all required fields:\n• " + "\n• ".join(required_errors))
            return
        
        # Validate phone is numeric
        if not phone.isdigit():
            messagebox.showerror("Validation Error", "Phone number must contain only digits")
            return
        
        # Check if there are items in the order
        items = self.order_tree.get_children()
        if not items:
            messagebox.showerror("No Items", "Please add at least one item to the order.\n\nSteps:\n1. Select a service from the dropdown\n2. Enter weight or select size and quantity\n3. Click 'Add Item'")
            return
        
        try:
            # Use first and last name entries directly
            first = first_name
            last = last_name
            # Create or get customer
            customer_id = db.create_or_get_customer(first, last, phone, email, address)
            
            # Calculate total and prepare items
            total_price = 0
            order_items = []
            
            for item_id in items:
                values = self.order_tree.item(item_id, 'values')
                service = values[0]
                quantity_str = values[1]
                price_str = values[2].replace("₱ ", "").strip()
                price = float(price_str)
                
                total_price += price
                order_items.append({
                    'service': service,
                    'quantity': quantity_str,
                    'subtotal': price
                })
            
            # Create order in database
            order_id = db.create_order(customer_id, total_price, order_items, notes)
            
            messagebox.showinfo("Success", f"Order created successfully!\nOrder ID: {order_id}\nTotal: ₱{total_price:.2f}")
            
            # Clear the form and unlock customer fields
            try:
                self.first_name_entry.config(state='normal')
                self.last_name_entry.config(state='normal')
                self.address_entry.config(state='normal')
                self.email_entry.config(state='normal')
                self.phone_entry.config(state='normal')
            except Exception:
                pass
            self.first_name_entry.delete(0, tk.END)
            self.last_name_entry.delete(0, tk.END)
            self.address_entry.delete(0, tk.END)
            self.email_entry.delete(0, tk.END)
            self.phone_entry.delete(0, tk.END)
            self.service_combo.set("")
            self.notes_text.delete("1.0", tk.END)
            for widget in self.dynamic_frame.winfo_children():
                widget.destroy()
            
            # Clear order items
            for item_id in self.order_tree.get_children():
                self.order_tree.delete(item_id)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create order: {str(e)}")

class ViewOrderPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.configure(bg=SECONDARY)

        import db
        # per-cell overlay widgets for Action column
        self.action_overlays = {}

        # Main border frame
        main_frame = tk.Frame(self, bd=1, relief="solid", bg=PRIMARY)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        # reserve notebook row for content
        main_frame.rowconfigure(3, weight=1)
        main_frame.columnconfigure(0, weight=1)

        # Top section with title and buttons
        top_frame = tk.Frame(main_frame)
        top_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=10)
        top_frame.columnconfigure(0, weight=1)

        self.subheading_label = tk.Label(top_frame, text="View Orders", font=("Arial", 12, "bold"))
        self.subheading_label.grid(row=0, column=0, sticky="w")

        # Action buttons on right
        button_frame = tk.Frame(top_frame, bg=PRIMARY)
        button_frame.grid(row=0, column=1, sticky="e", padx=5, pady=5)

        tk.Button(button_frame, text="Update Status", font=TTL_TEXT, bg=SECONDARY, fg=PRIMARY, command=self.open_update_status_window, width=15, height=1).pack(side="left", padx=5)
        tk.Button(button_frame, text="Process Payment", font=TTL_TEXT, bg=SECONDARY, fg=PRIMARY, command=self.open_payment_window, width=15, height=1).pack(side="left", padx=5)

        # thin separator under heading (inside top_frame so filter_frame stays at previous row)
        sep1 = ttk.Separator(top_frame, orient='horizontal')
        sep1.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(8,0))

        # Filter section (return to previous position)
        filter_frame = tk.Frame(main_frame, bg=PRIMARY)
        filter_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=10)
        filter_frame.columnconfigure(1, weight=0)
        filter_frame.columnconfigure(3, weight=0)
        filter_frame.columnconfigure(5, weight=0)
        filter_frame.columnconfigure(7, weight=0)

        tk.Label(filter_frame, text="Search ID:", font=TTL_TEXT, bg=PRIMARY).grid(row=0, column=0, padx=5)
        self.search_entry = tk.Entry(filter_frame, width=15, font=REG_TEXT, highlightthickness=2, highlightcolor=SECONDARY)
        self.search_entry.grid(row=0, column=1, padx=5, ipady=2)

        search_btn = tk.Button(filter_frame, text="Search", font=TTL_TEXT, bg=SECONDARY, fg=PRIMARY, command=self.search_orders, width=8)
        search_btn.grid(row=0, column=2, padx=(5,15))

        tk.Label(filter_frame, text="Date From:", font=TTL_TEXT, bg=PRIMARY).grid(row=0, column=3, padx=(8,5))
        self.date_from = tk.Entry(filter_frame, font=REG_TEXT, highlightthickness=2, highlightcolor=SECONDARY, width=12)
        self.date_from.insert(0, "mm/dd/yyyy")
        self.date_from.grid(row=0, column=4, padx=(5,10), ipady=2)

        tk.Label(filter_frame, text="To:", font=TTL_TEXT, bg=PRIMARY).grid(row=0, column=5, padx=5)
        self.date_to = tk.Entry(filter_frame, font=REG_TEXT, highlightthickness=2, highlightcolor=SECONDARY, width=12)
        self.date_to.insert(0, "mm/dd/yyyy")
        self.date_to.grid(row=0, column=6, padx=(5,12), ipady=2)

        # improve date entry UX: clear placeholder on focus, restore if empty
        def _clear_placeholder(event):
            w = event.widget
            if w.get() in ("mm/dd/yyyy", ""):
                w.delete(0, tk.END)
        def _restore_placeholder(event):
            w = event.widget
            if not w.get():
                w.insert(0, "mm/dd/yyyy")
        self.date_from.bind('<FocusIn>', _clear_placeholder)
        self.date_from.bind('<FocusOut>', _restore_placeholder)
        self.date_to.bind('<FocusIn>', _clear_placeholder)
        self.date_to.bind('<FocusOut>', _restore_placeholder)

        # Quick-fill functions
        def _fill_today():
            from datetime import date
            s = date.today().strftime('%m/%d/%Y')
            self.date_from.delete(0, tk.END); self.date_to.delete(0, tk.END)
            self.date_from.insert(0, s); self.date_to.insert(0, s)
        def _fill_week():
            from datetime import date, timedelta
            today = date.today()
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
            self.date_from.delete(0, tk.END); self.date_to.delete(0, tk.END)
            self.date_from.insert(0, start.strftime('%m/%d/%Y'))
            self.date_to.insert(0, end.strftime('%m/%d/%Y'))
        def _fill_month():
            from datetime import date
            import calendar
            today = date.today()
            start = today.replace(day=1)
            last_day = calendar.monthrange(today.year, today.month)[1]
            end = today.replace(day=last_day)
            self.date_from.delete(0, tk.END); self.date_to.delete(0, tk.END)
            self.date_from.insert(0, start.strftime('%m/%d/%Y'))
            self.date_to.insert(0, end.strftime('%m/%d/%Y'))
        def _clear_dates():
            self.date_from.delete(0, tk.END); self.date_to.delete(0, tk.END)
            self.date_from.insert(0, 'mm/dd/yyyy'); self.date_to.insert(0, 'mm/dd/yyyy')

        # Quick-fill buttons inline on same row (buttons assigned to variables for responsive behavior)
        date_btn_frame = tk.Frame(filter_frame, bg=PRIMARY)
        date_btn_frame.grid(row=0, column=7, padx=(2,0))
        btn_today = tk.Button(date_btn_frame, text='Today', font=TTL_TEXT, bg=ACCENT, fg=SECONDARY, width=8, command=_fill_today)
        btn_today.pack(side='left', padx=2)
        btn_week = tk.Button(date_btn_frame, text='This Week', font=TTL_TEXT, bg=ACCENT, fg=SECONDARY, width=10, command=_fill_week)
        btn_week.pack(side='left', padx=2)
        btn_month = tk.Button(date_btn_frame, text='This Month', font=TTL_TEXT, bg=ACCENT, fg=SECONDARY, width=10, command=_fill_month)
        btn_month.pack(side='left', padx=2)
        btn_clear = tk.Button(date_btn_frame, text='Clear', font=TTL_TEXT, bg=PRIMARY, fg=SECONDARY, width=6, command=_clear_dates)
        btn_clear.pack(side='left', padx=2)
        search_btn_inline = tk.Button(date_btn_frame, text='Search by Date', font=TTL_TEXT, bg=SECONDARY, fg=PRIMARY, width=12, command=self.search_by_date)
        search_btn_inline.pack(side='left', padx=4)
        # make space to right so layout doesn't look cramped — keep buttons near date fields
        filter_frame.columnconfigure(7, weight=0)
        filter_frame.columnconfigure(8, weight=1)
        # keep legacy variable name for compatibility
        search_date_btn = search_btn_inline
        
        # Notebook tabs for Unpaid / Paid / Archived
        style = ttk.Style()
        try:
            style.configure('TNotebook.Tab', font=('Segoe UI', 11, 'bold'), padding=[12, 8])
        except Exception:
            pass

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=3, column=0, sticky="nsew", padx=15, pady=10)
        self.notebook.rowconfigure(0, weight=1)
        self.notebook.columnconfigure(0, weight=1)
        self.notebook.bind('<<NotebookTabChanged>>', self.on_tab_changed)

        # thin separator above notebook
        sep2 = ttk.Separator(main_frame, orient='horizontal')
        sep2.grid(row=2, column=0, sticky='ew', padx=8)

        # create three tab frames
        self.unpaid_frame = tk.Frame(self.notebook)
        self.paid_frame = tk.Frame(self.notebook)
        self.archived_frame = tk.Frame(self.notebook)
        self.notebook.add(self.unpaid_frame, text="Unpaid Orders")
        self.notebook.add(self.paid_frame, text="Paid Orders")
        self.notebook.add(self.archived_frame, text="Archived")

        # Common columns (archived omits Action)
        all_columns = ("OrderID", "Date Received", "Customer", "Service", "Qty/Wt", "Status", "Total", "Paid")

        # helper to create tree (optionally include Action column)
        def make_tree(parent, include_action=True):
            cols = list(all_columns)
            if include_action:
                cols.append('Action')
            frame = tk.Frame(parent)
            frame.pack(fill='both', expand=True)
            scrollbar = ttk.Scrollbar(frame)
            scrollbar.pack(side='right', fill='y')
            tree = ttk.Treeview(frame, columns=cols, show="headings", yscrollcommand=scrollbar.set)
            # keep a reference to scrollbar so we can bind its events later
            tree._scrollbar = scrollbar
            scrollbar.config(command=tree.yview)
            for col in cols:
                tree.heading(col, text=col)
                tree.column(col, width=120 if col not in ('Action', 'Qty/Wt') else 80, anchor='w')

            tree.pack(fill='both', expand=True)
            return tree

        self.unpaid_tree = make_tree(self.unpaid_frame, include_action=True)
        self.paid_tree = make_tree(self.paid_frame, include_action=True)
        self.archived_tree = make_tree(self.archived_frame, include_action=False)

        # bind click & reposition handlers to trees that have Action column
        for t in (self.unpaid_tree, self.paid_tree):
            t.bind('<ButtonRelease-1>', self.on_tree_click)
            t.bind('<Motion>', self.on_tree_motion)
            # reposition overlays on configure, mouse actions and after scroll (add handlers so original click binding isn't replaced)
            t.bind('<Configure>', lambda e: self._reposition_action_overlays(e), add='+')
            t.bind('<ButtonRelease-1>', lambda e: self._reposition_action_overlays(e), add='+')
            t.bind('<MouseWheel>', lambda e: self._reposition_action_overlays(e), add='+')
            try:
                # scrollbar exists as attribute _scrollbar
                t._scrollbar.bind('<ButtonRelease-1>', lambda e: self._reposition_action_overlays(e), add='+')
                t._scrollbar.bind('<B1-Motion>', lambda e: self._reposition_action_overlays(e), add='+')
            except Exception:
                pass

        # Legend/Filter at bottom (moved below the notebook)
        legend_frame = tk.Frame(main_frame, bg=PRIMARY)
        legend_frame.grid(row=4, column=0, sticky="ew", padx=15, pady=10)

        legend_label = tk.Label(legend_frame, text="Filter By Status:", font=TTL_TEXT, bg=PRIMARY)
        legend_label.pack(side="left", padx=5)
        
        for status in ["All", "Received", "In-Progress", "Ready", "Released"]:
            tk.Button(legend_frame, text=status, font=TTL_TEXT, bg=PRIMARY, fg=SECONDARY, width=12, command=lambda s=status: self.sort_by_status(s)).pack(side="left", padx=3)

        # Load initial data
        self.refresh_all()

    def refresh_all(self):
        self.refresh_unpaid()
        self.refresh_paid()
        self.refresh_archived()
        # update heading
        try:
            self.on_tab_changed()
        except Exception:
            pass

    def on_tab_changed(self, event=None):
        # update subheading to show tab text and record count
        try:
            tab_text = self.notebook.tab(self.notebook.select(), option='text')
        except Exception:
            tab_text = 'View Orders'
        tree = self.get_tree_for_current_tab()
        count = len(tree.get_children()) if tree is not None else 0
        self.subheading_label.config(text=f"{tab_text} - {count} records")

    def get_tree_for_current_tab(self):
        idx = self.notebook.index(self.notebook.select())
        if idx == 0:
            return self.unpaid_tree
        elif idx == 1:
            return self.paid_tree
        else:
            return self.archived_tree

    # --- Action overlay helpers (show blue underlined 'Edit' only over Action cell) ---
    def _clear_action_overlays(self, tree=None):
        # clear overlays for a specific tree or all
        if tree is None:
            for treemap in list(self.action_overlays.values()):
                for w in list(treemap.values()):
                    try:
                        w.destroy()
                    except Exception:
                        pass
            self.action_overlays = {}
            return
        treemap = self.action_overlays.get(tree, {})
        for w in list(treemap.values()):
            try:
                w.destroy()
            except Exception:
                pass
        self.action_overlays[tree] = {}

    def _create_action_overlays(self, tree):
        # create Label widgets positioned over the Action column cells (per-tree)
        self._clear_action_overlays(tree)
        cols = list(tree['columns'])
        if 'Action' not in cols:
            return
        action_col_index = cols.index('Action') + 1
        treemap = {}
        for iid in tree.get_children():
            try:
                bbox = tree.bbox(iid, f"#{action_col_index}")
                if not bbox:
                    continue
                x, y, w, h = bbox
                # create a visible blue-underlined label (link style)
                try:
                    link_font = tkfont.Font(family="Segoe UI", size=9, underline=1)
                except Exception:
                    try:
                        link_font = tkfont.Font(underline=1)
                    except Exception:
                        link_font = None
                lbl = tk.Label(tree, text='Edit', fg='#0563c1', cursor='hand2', bg='white', bd=0)
                if link_font:
                    try:
                        lbl.config(font=link_font)
                    except Exception:
                        pass
                # bind before placing to capture iid
                lbl.bind('<Button-1>', lambda e, id=iid: self.open_edit_window(int(id)))
                lbl.place(x=x+2, y=y+1, width=w-4, height=h-2)
                lbl.lift()
                treemap[iid] = lbl
            except Exception:
                continue
        self.action_overlays[tree] = treemap

    def _reposition_action_overlays(self, event=None):
        # reposition existing overlays (call on configure/scroll)
        for tree in (self.unpaid_tree, self.paid_tree):
            treemap = self.action_overlays.get(tree, {})
            cols = list(tree['columns'])
            if 'Action' not in cols:
                continue
            action_col_index = cols.index('Action') + 1
            for iid, lbl in list(treemap.items()):
                if iid not in tree.get_children():
                    try:
                        lbl.destroy()
                    except Exception:
                        pass
                    del treemap[iid]
                    continue
                bbox = tree.bbox(iid, f"#{action_col_index}")
                if not bbox:
                    try:
                        lbl.place_forget()
                    except Exception:
                        pass
                else:
                    x, y, w, h = bbox
                    try:
                        lbl.place(x=x+2, y=y+1, width=w-4, height=h-2)
                        lbl.lift()
                    except Exception:
                        pass
        # cleanup empty maps
        for tree in list(self.action_overlays.keys()):
            if not self.action_overlays.get(tree):
                del self.action_overlays[tree]

    def refresh_unpaid(self):
        import db
        tree = self.unpaid_tree
        for item in tree.get_children():
            tree.delete(item)
        try:
            orders = db.get_unpaid_orders()
            for order in orders:
                service_display = db.get_order_services(order['OrderID'])
                qty_display = db.get_order_qty_display(order['OrderID'])
                tree.insert("", "end", iid=order['OrderID'], values=(
                    order['OrderID'],
                    order['Order_Received_At'],
                    f"{order['First_Name']} {order['Last_Name']}",
                    service_display,
                    qty_display,
                    order['Order_Status'],
                    f"₱{order['Order_Total_Price']}",
                    "Yes" if order['Order_Payed_At'] else "No",
                    ""
                ))
            # create overlays for action column
            try:
                self._create_action_overlays(tree)
            except Exception:
                pass
        except Exception as e:
            print(f"Error loading unpaid orders: {e}")

    def refresh_paid(self):
        import db
        tree = self.paid_tree
        for item in tree.get_children():
            tree.delete(item)
        try:
            orders = db.get_paid_orders()
            for order in orders:
                service_display = db.get_order_services(order['OrderID'])
                qty_display = db.get_order_qty_display(order['OrderID'])
                tree.insert("", "end", iid=order['OrderID'], values=(
                    order['OrderID'],
                    order['Order_Received_At'],
                    f"{order['First_Name']} {order['Last_Name']}",
                    service_display,
                    qty_display,
                    order['Order_Status'],
                    f"₱{order['Order_Total_Price']}",
                    "Yes",
                    ""
                ))
            # create overlays for action column
            try:
                self._create_action_overlays(tree)
            except Exception:
                pass
        except Exception as e:
            print(f"Error loading paid orders: {e}")

    def refresh_archived(self):
        import db
        tree = self.archived_tree
        for item in tree.get_children():
            tree.delete(item)
        try:
            orders = db.get_archived_orders()
            for order in orders:
                service_display = db.get_order_services(order['OrderID'])
                qty_display = db.get_order_qty_display(order['OrderID'])
                tree.insert("", "end", iid=order['OrderID'], values=(
                    order['OrderID'],
                    order['Order_Received_At'],
                    f"{order['First_Name']} {order['Last_Name']}",
                    service_display,
                    qty_display,
                    order['Order_Status'],
                    f"₱{order['Order_Total_Price']}",
                    "Yes"
                ))
        except Exception as e:
            print(f"Error loading archived orders: {e}")

    def search_orders(self):
        
        term = self.search_entry.get().strip()
        if not term:
            self.refresh_all()
            return
        import db
        # search within the currently selected tab
        idx = self.notebook.index(self.notebook.select())
        if idx == 0:
            orders = db.get_unpaid_orders()
            tree = self.unpaid_tree
        elif idx == 1:
            orders = db.get_paid_orders()
            tree = self.paid_tree
        else:
            orders = db.get_archived_orders()
            tree = self.archived_tree

        for item in tree.get_children():
            tree.delete(item)

        found = False
        for order in orders:
            if str(order['OrderID']).startswith(term):
                service_display = db.get_order_services(order['OrderID'])
                qty_display = db.get_order_qty_display(order['OrderID'])
                vals = [order['OrderID'], order['Order_Received_At'], f"{order['First_Name']} {order['Last_Name']}", service_display, qty_display, order['Order_Status'], f"₱{order['Order_Total_Price']}", "Yes" if order['Order_Payed_At'] else "No"]
                if idx in (0,1):
                    vals.append('')
                    tree.insert("", "end", iid=order['OrderID'], values=tuple(vals))
                else:
                    tree.insert("", "end", iid=order['OrderID'], values=tuple(vals))
                found = True
        # create overlays for action column on search results
        try:
            if idx in (0,1):
                self._create_action_overlays(tree)
        except Exception:
            pass
        if not found:
            from tkinter import messagebox
            messagebox.showinfo("Search", f"No orders found with ID starting with '{term}'")

    def search_by_date(self):
        import db
        from tkinter import messagebox
        start_raw = self.date_from.get().strip()
        end_raw = self.date_to.get().strip()
        if not start_raw or not end_raw or start_raw in ("mm/dd/yyyy","") or end_raw in ("mm/dd/yyyy",""):
            messagebox.showwarning('Date Search', 'Please enter both From and To dates in mm/dd/yyyy format')
            return
        # try parsing either mm/dd/yyyy or yyyy-mm-dd
        from datetime import datetime
        def parse_date(s):
            for fmt in ('%m/%d/%Y','%Y-%m-%d'):
                try:
                    return datetime.strptime(s, fmt).date()
                except Exception:
                    continue
            raise ValueError('Invalid date format')
        try:
            start_dt = parse_date(start_raw)
            end_dt = parse_date(end_raw)
        except Exception:
            messagebox.showerror('Date Search', 'Invalid date format. Use mm/dd/yyyy or yyyy-mm-dd')
            return
        if start_dt > end_dt:
            messagebox.showwarning('Date Search', 'Start date must be before or equal to End date')
            return
        start_iso = start_dt.strftime('%Y-%m-%d')
        end_iso = end_dt.strftime('%Y-%m-%d')
        idx = self.notebook.index(self.notebook.select())
        try:
            if idx == 0:
                orders = db.get_unpaid_orders_by_date(start_iso, end_iso)
                tree = self.unpaid_tree
            elif idx == 1:
                orders = db.get_paid_orders_by_date(start_iso, end_iso)
                tree = self.paid_tree
            else:
                orders = db.get_archived_orders_by_date(start_iso, end_iso)
                tree = self.archived_tree
        except Exception as e:
            messagebox.showerror('Date Search', f'Database error: {e}')
            return
        # populate tree
        for item in tree.get_children():
            tree.delete(item)
        for order in orders:
            service_display = db.get_order_services(order['OrderID'])
            qty_display = db.get_order_qty_display(order['OrderID'])
            vals = [order['OrderID'], order['Order_Received_At'], f"{order['First_Name']} {order['Last_Name']}", service_display, qty_display, order['Order_Status'], f"₱{order['Order_Total_Price']}", 'Yes' if order['Order_Payed_At'] else 'No']
            if idx in (0,1):
                vals.append('')
                tree.insert('', 'end', iid=order['OrderID'], values=tuple(vals))
            else:
                tree.insert('', 'end', iid=order['OrderID'], values=tuple(vals))
        try:
            if idx in (0,1):
                self._create_action_overlays(tree)
        except Exception:
            pass

    def sort_by_status(self, status):
        # find current tab and filter that tree
        idx = self.notebook.index(self.notebook.select())
        import db
        if idx == 0:
            tree = self.unpaid_tree
            orders = db.get_unpaid_orders()
        elif idx == 1:
            tree = self.paid_tree
            orders = db.get_paid_orders()
        else:
            tree = self.archived_tree
            orders = db.get_archived_orders()

        # clear
        for item in tree.get_children():
            tree.delete(item)

        if status == 'All':
            # refresh this tab
            if idx == 0:
                self.refresh_unpaid()
            elif idx == 1:
                self.refresh_paid()
            else:
                self.refresh_archived()
            return

        try:
            orders = [o for o in orders if o['Order_Status'] == status]
            for order in orders:
                service_display = db.get_order_services(order['OrderID'])
                qty_display = db.get_order_qty_display(order['OrderID'])
                vals = (order['OrderID'], order['Order_Received_At'], f"{order['First_Name']} {order['Last_Name']}", service_display, qty_display, order['Order_Status'], f"₱{order['Order_Total_Price']}", "Yes" if order['Order_Payed_At'] else "No")
                if idx in (0,1):
                    vals = tuple(list(vals) + [''])
                    tree.insert("", "end", iid=order['OrderID'], values=vals)
                else:
                    tree.insert("", "end", iid=order['OrderID'], values=vals)
            # after populating sorted list, create overlays
            try:
                if idx in (0,1):
                    self._create_action_overlays(tree)
            except Exception:
                pass
        except Exception as e:
            print(f"Error sorting orders: {e}")

    def open_update_status_window(self):
        import db
        from tkinter import messagebox

        status_win = tk.Toplevel(self)
        status_win.title("Update Order Status")
        status_win.geometry("500x350")
        status_win.resizable(False, False)
        status_win.grab_set()

        container = tk.Frame(status_win, bd=2, relief="solid", bg="white")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        header = tk.Frame(container, bg="#2c3e50", height=60)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="Update Order Status", font=("Arial", 16, "bold"), bg="#2c3e50", fg="white").pack(pady=15)

        form_frame = tk.Frame(container, bg="white")
        form_frame.pack(fill="both", expand=True, padx=30, pady=30)
        form_frame.columnconfigure(1, weight=1)

        # Order selection: use a freeform search entry (supports order ID or customer name search)
        tk.Label(form_frame, text="Order ID / Customer:", font=("Arial", 11), bg="white").grid(row=0, column=0, sticky="w", pady=15)
        order_entry_var = tk.StringVar()
        order_entry = tk.Entry(form_frame, textvariable=order_entry_var, width=30, font=("Arial", 10))
        order_entry.grid(row=0, column=1, sticky="ew", pady=15, padx=10)
        def _choose_from_matches(matches):
            # matches: list of (OrderID, display)
            pick_win = tk.Toplevel(status_win)
            pick_win.title('Select Order')
            pick_win.geometry('400x300')
            lb = tk.Listbox(pick_win)
            for oid, disp in matches:
                lb.insert('end', f"{oid} - {disp}")
            lb.pack(fill='both', expand=True, padx=8, pady=8)
            def _select():
                sel = lb.curselection()
                if not sel:
                    return
                text = lb.get(sel[0])
                oid = text.split(' - ', 1)[0]
                order_entry_var.set(oid)
                pick_win.destroy()
            btnf = tk.Button(pick_win, text='Select', command=_select)
            btnf.pack(pady=6)
        def _find_order():
            q = order_entry_var.get().strip()
            if not q:
                messagebox.showwarning('Find Order', 'Enter Order ID or Customer name', parent=status_win)
                return
            # if numeric, try fetch by ID
            if q.isdigit():
                o = db.get_order_details(int(q))
                if not o:
                    messagebox.showinfo('Find Order', f'Order {q} not found', parent=status_win)
                    return
                # show brief info
                order_entry_var.set(str(o['OrderID']))
                messagebox.showinfo('Find Order', f"Found Order {o['OrderID']} for {o['First_Name']} {o['Last_Name']}", parent=status_win)
                return
            # otherwise search by name (simple filter)
            all_orders = db.get_orders()
            qlow = q.lower()
            matches = []
            for o in all_orders:
                name = f"{o['First_Name']} {o['Last_Name']}".lower()
                if qlow in name:
                    matches.append((o['OrderID'], f"{o['First_Name']} {o['Last_Name']} - {o['Order_Received_At']}"))
            if not matches:
                messagebox.showinfo('Find Order', 'No matching orders found', parent=status_win)
                return
            if len(matches) == 1:
                order_entry_var.set(str(matches[0][0]))
                messagebox.showinfo('Find Order', f"Found Order {matches[0][0]} for {matches[0][1]}", parent=status_win)
                return
            # multiple matches - let user pick
            _choose_from_matches(matches)

        tk.Button(form_frame, text='Find', command=_find_order).grid(row=0, column=2, padx=6)

        tk.Label(form_frame, text="New Status:", font=("Arial", 11), bg="white").grid(row=1, column=0, sticky="w", pady=15)
        status_combo = ttk.Combobox(form_frame, values=["Received", "In-Progress", "Ready", "Released"], width=30, state="readonly", font=("Arial", 10))
        status_combo.grid(row=1, column=1, sticky="ew", pady=15, padx=10)

        def update_and_close():
            order_id = order_entry_var.get().strip()
            new_status = status_combo.get()
            if not order_id or not new_status:
                messagebox.showwarning("Error", "Please select an order and status", parent=status_win)
                return
            try:
                db.update_order(int(order_id), new_status, None)
                messagebox.showinfo("Success", f"Order {order_id} status updated to {new_status}", parent=status_win)
                self.refresh_all()
                status_win.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Database error: {str(e)}", parent=status_win)

        btn_frame = tk.Frame(container, bg="white")
        btn_frame.pack(fill="x", padx=30, pady=20)
        btn_frame.columnconfigure((0, 1), weight=1)
        tk.Button(btn_frame, text="Update Status", command=update_and_close, font=("Arial", 11, "bold"), bg="#27ae60", fg="white", height=2, cursor="hand2").grid(row=0, column=0, sticky="ew", padx=5)
        tk.Button(btn_frame, text="Cancel", command=status_win.destroy, font=("Arial", 11), bg="#95a5a6", fg="white", height=2, cursor="hand2").grid(row=0, column=1, sticky="ew", padx=5)

    def open_payment_window(self):
        import db
        from tkinter import messagebox

        payment_win = tk.Toplevel(self)
        payment_win.title("Process Payment")
        payment_win.geometry("520x450")
        payment_win.resizable(False, False)
        payment_win.grab_set()

        container = tk.Frame(payment_win, bd=2, relief="solid", bg="white")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        header = tk.Frame(container, bg="#2c3e50", height=60)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="Process Payment", font=("Arial", 16, "bold"), bg="#2c3e50", fg="white").pack(pady=15)

        form_frame = tk.Frame(container, bg="white")
        form_frame.pack(fill="both", expand=True, padx=30, pady=30)
        form_frame.columnconfigure(1, weight=1)

        # Order selection via search entry for scalability
        tk.Label(form_frame, text="Order ID / Customer:", font=("Arial", 11), bg="white").grid(row=0, column=0, sticky="w", pady=12)
        order_entry_var = tk.StringVar()
        order_entry = tk.Entry(form_frame, textvariable=order_entry_var, width=30, font=("Arial", 10))
        order_entry.grid(row=0, column=1, sticky="ew", pady=12, padx=10)

        def _choose_from_matches_payment(matches):
            pick_win = tk.Toplevel(payment_win)
            pick_win.title('Select Order')
            pick_win.geometry('400x300')
            lb = tk.Listbox(pick_win)
            for oid, disp in matches:
                lb.insert('end', f"{oid} - {disp}")
            lb.pack(fill='both', expand=True, padx=8, pady=8)
            def _select():
                sel = lb.curselection()
                if not sel:
                    return
                text = lb.get(sel[0])
                oid = text.split(' - ', 1)[0]
                order_entry_var.set(oid)
                # update amount display
                try:
                    o = db.get_order_details(int(oid))
                    if o:
                        amount_due_display.config(text=f"₱{o['Order_Total_Price']:.2f}")
                except:
                    pass
                pick_win.destroy()
            btnf = tk.Button(pick_win, text='Select', command=_select)
            btnf.pack(pady=6)

        def _find_order_payment():
            q = order_entry_var.get().strip()
            if not q:
                messagebox.showwarning('Find Order', 'Enter Order ID or Customer name', parent=payment_win)
                return
            if q.isdigit():
                o = db.get_order_details(int(q))
                if not o:
                    messagebox.showinfo('Find Order', f'Order {q} not found', parent=payment_win)
                    return
                order_entry_var.set(str(o['OrderID']))
                amount_due_display.config(text=f"₱{o['Order_Total_Price']:.2f}")
                cash_entry.delete(0, tk.END)
                return
            # search by name
            all_orders = db.get_orders()
            qlow = q.lower()
            matches = []
            for o in all_orders:
                name = f"{o['First_Name']} {o['Last_Name']}".lower()
                if qlow in name:
                    matches.append((o['OrderID'], f"{o['First_Name']} {o['Last_Name']} - {o['Order_Received_At']}"))
            if not matches:
                messagebox.showinfo('Find Order', 'No matching orders found', parent=payment_win)
                return
            if len(matches) == 1:
                order_entry_var.set(str(matches[0][0]))
                o = db.get_order_details(int(matches[0][0]))
                if o:
                    amount_due_display.config(text=f"₱{o['Order_Total_Price']:.2f}")
                return
            _choose_from_matches_payment(matches)

        tk.Button(form_frame, text='Find', command=_find_order_payment).grid(row=0, column=2, padx=6)

        amount_due_display = tk.Label(form_frame, text="0.00", font=("Arial", 13, "bold"), bg="#ecf0f1", fg="#2c3e50", relief="sunken", width=35)
        amount_due_display.grid(row=1, column=1, sticky="ew", pady=12, padx=10)
        tk.Label(form_frame, text="Amount Due (₱):", font=("Arial", 11), bg="white").grid(row=1, column=0, sticky="w", pady=12)

        cash_entry = tk.Entry(form_frame, width=37, font=("Arial", 10), bd=1, relief="solid")
        cash_entry.grid(row=2, column=1, sticky="ew", pady=12, padx=10)
        tk.Label(form_frame, text="Cash Received (₱):", font=("Arial", 11), bg="white").grid(row=2, column=0, sticky="w", pady=12)

        def process_payment():
            order_id = order_entry_var.get()
            cash_str = cash_entry.get()
            if not order_id or not cash_str:
                messagebox.showwarning("Error", "Please select an order and enter cash amount", parent=payment_win)
                return
            try:
                cash = float(cash_str)
                result = db.process_payment(int(order_id), cash)
                if not result['success']:
                    messagebox.showerror("Payment Error", result['message'], parent=payment_win)
                    return

                # show summary and close
                messagebox.showinfo("Success", "Payment processed successfully!", parent=payment_win)
                self.refresh_all()
                payment_win.destroy()
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid numeric amount", parent=payment_win)
            except Exception as e:
                messagebox.showerror("Error", f"Database error: {str(e)}", parent=payment_win)

        btn_frame = tk.Frame(container, bg="white")
        btn_frame.pack(fill="x", padx=30, pady=20)
        btn_frame.columnconfigure((0, 1), weight=1)
        tk.Button(btn_frame, text="Process Payment", command=process_payment, font=("Arial", 11, "bold"), bg="#3498db", fg="white", height=2, cursor="hand2").grid(row=0, column=0, sticky="ew", padx=5)
        tk.Button(btn_frame, text="Cancel", command=payment_win.destroy, font=("Arial", 11), bg="#95a5a6", fg="white", height=2, cursor="hand2").grid(row=0, column=1, sticky="ew", padx=5)

    def on_tree_motion(self, event):
        widget = event.widget
        col = widget.identify_column(event.x)
        # change cursor to hand when over Action column
        if col == f"#{len(widget['columns'])}":
            widget.configure(cursor='hand2')
        else:
            widget.configure(cursor='')

    def on_tree_click(self, event):
        """Detect clicks on the 'Action' column and open edit window"""
        widget = event.widget
        # which column was clicked
        col = widget.identify_column(event.x)
        # last column is Action - find its index
        # identify_column returns like '#1', '#2' ...
        if col == f"#{len(widget['columns'])}":
            row_id = widget.identify_row(event.y)
            if not row_id:
                return
            try:
                order_id = int(row_id)
            except ValueError:
                return
            self.open_edit_window(order_id)

    def open_edit_window(self, order_id):
        import db
        from tkinter import messagebox
        order = db.get_order_details(int(order_id))
        if not order:
            messagebox.showerror("Not found", "Order not found")
            return
        # normalize sqlite3.Row to dict so .get() works
        try:
            order = dict(order)
        except Exception:
            pass

        edit_win = tk.Toplevel(self)
        edit_win.title(f"Edit Order {order_id}")
        edit_win.geometry("520x420")
        edit_win.resizable(False, False)
        edit_win.grab_set()

        form = tk.Frame(edit_win, padx=12, pady=12)
        form.pack(fill='both', expand=True)
        form.columnconfigure(1, weight=1)

        # First and Last Name fields
        tk.Label(form, text="First Name:").grid(row=0, column=0, sticky='w')
        first_name = tk.Entry(form)
        first_name.grid(row=0, column=1, sticky='ew')
        first_name.insert(0, order.get('First_Name',''))

        tk.Label(form, text="Last Name:").grid(row=1, column=0, sticky='w')
        last_name = tk.Entry(form)
        last_name.grid(row=1, column=1, sticky='ew')
        last_name.insert(0, order.get('Last_Name',''))

        tk.Label(form, text="Email:").grid(row=2, column=0, sticky='w')
        email = tk.Entry(form)
        email.grid(row=2, column=1, sticky='ew')
        email.insert(0, order.get('Email',''))

        tk.Label(form, text="Phone:").grid(row=3, column=0, sticky='w')
        ph = tk.Entry(form)
        ph.grid(row=3, column=1, sticky='ew')
        ph.insert(0, order.get('Phone_Number',''))

        tk.Label(form, text="Status:").grid(row=4, column=0, sticky='w')
        status = ttk.Combobox(form, values=["Received","In-Progress","Ready","Released"], state='readonly')
        status.grid(row=4, column=1, sticky='ew')
        status.set(order['Order_Status'])

        tk.Label(form, text="Notes:").grid(row=5, column=0, sticky='nw')
        notes = tk.Text(form, height=6)
        notes.grid(row=5, column=1, sticky='ew')
        notes.insert('1.0', order.get('Order_Notes') or '')

        def save_changes():
            try:
                # read first and last name fields
                first = first_name.get().strip()
                last = last_name.get().strip()
                # update customer (CustomerID, First, Last, Phone, Email, Address)
                db.update_customer(order['CustomerID'], first, last, ph.get().strip(), email.get().strip(), '')
                # update order
                db.update_order(order_id, status.get(), notes.get('1.0', 'end-1c').strip())
                messagebox.showinfo('Saved', 'Order updated')
                edit_win.destroy()
                self.refresh_all()
            except Exception as e:
                messagebox.showerror('Error', str(e))

        btn_frame = tk.Frame(form, bg='white')
        btn_frame.grid(row=6, column=0, columnspan=2, pady=12, sticky='ew')
        btn_frame.columnconfigure((0,1), weight=1)
        tk.Button(btn_frame, text='Confirm', command=save_changes, font=("Arial", 11, "bold"), bg="#3498db", fg="white", height=2, cursor="hand2").grid(row=0, column=0, sticky='ew', padx=5)
        tk.Button(btn_frame, text='Cancel', command=edit_win.destroy, font=("Arial", 11), bg="#95a5a6", fg="white", height=2, cursor="hand2").grid(row=0, column=1, sticky='ew', padx=5)

class ReportsPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        
        # Tab buttons
        tab_frame = tk.Frame(self, bd=1, relief="solid")
        tab_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        tab_frame.columnconfigure((0,1,2,3,4), weight=1)
        
        self.current_tab = "revenue"
        tabs = {
            "revenue": "Revenue Today",
            "received": "Received Today",
            "ready": "Ready Today",
            "overdue": "Overdue",
            "services": "Top Services"
        }
        self.tab_buttons = {}
        for key, label in tabs.items():
            btn = tk.Button(tab_frame, text=label, command=lambda k=key: self.show_report(k))
            btn.grid(row=0, column=list(tabs.keys()).index(key), sticky="ew", padx=4, pady=4)
            self.tab_buttons[key] = btn
        
        # Chart canvas area
        self.chart_frame = tk.Frame(self, bd=1, relief="groove")
        self.chart_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        self.chart_frame.columnconfigure(0, weight=1)
        self.chart_frame.rowconfigure(0, weight=1)
        
        self.canvas = None
        self.show_report("revenue")
    
    def show_report(self, report_type):
        # Clear previous chart
        if self.canvas:
            self.canvas.get_tk_widget().destroy()
        
        self.current_tab = report_type
        
        # Create matplotlib figure
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        
        fig, ax = plt.subplots(figsize=(10, 5))
        
        if report_type == "revenue":
            # Revenue Today - Line chart
            days, revenue = get_revenue_report_data()
            
            ax.plot(days, revenue, marker='o', linewidth=2, markersize=8, color='#2ecc71')
            ax.fill_between(range(len(days)), revenue, alpha=0.3, color='#2ecc71')
            ax.set_title("Revenue Today", fontsize=14, fontweight='bold')
            ax.set_ylabel("Amount ($)")
            ax.grid(True, alpha=0.3)
        
        elif report_type == "received":
            # Received Today - Bar chart
            hours, received = get_received_report_data()
            ax.bar(hours, received, color='#3498db', alpha=0.7)
            ax.set_title("Received Today", fontsize=14, fontweight='bold')
            ax.set_ylabel("Orders")
            ax.grid(True, alpha=0.3, axis='y')
        
        elif report_type == "ready":
            # Ready Today - Bar chart
            hours, ready = get_ready_report_data()  
            ax.bar(hours, ready, color='#f39c12', alpha=0.7)
            ax.set_title("Ready Today", fontsize=14, fontweight='bold')
            ax.set_ylabel("Orders")
            ax.grid(True, alpha=0.3, axis='y')
        
        elif report_type == "overdue":
            services, overdue_count = get_overdue_report_data()
            
            if not services:
                ax.text(0.5, 0.5, "All caught up!\nNo overdue orders.", 
                        horizontalalignment='center', verticalalignment='center', 
                        fontsize=12, fontweight='bold', color='#2ed573')
                ax.set_title("Overdue Orders by Service", fontsize=14, fontweight='bold')
                ax.axis('off')
            else:
                ax.pie(overdue_count, labels=services, autopct='%1.1f%%', startangle=90,
                    colors=['#e74c3c', '#e67e22', '#f1c40f', '#3498db'])
                ax.set_title("Overdue Orders by Service", fontsize=14, fontweight='bold')

        elif report_type == "services":
            services, count = get_top_services_report_data()
    
            if not services:
                ax.text(0.5, 0.5, "No orders recorded yet to calculate top services.", 
                        horizontalalignment='center', verticalalignment='center', fontsize=12)
                ax.set_title("Top Services", fontsize=14, fontweight='bold')
                ax.axis('off')
            else:
                ax.barh(services, count, color='#e74c3c', alpha=0.7, height=0.5)
                ax.set_title("Top Services", fontsize=14, fontweight='bold')
                ax.set_xlabel("Orders")
                ax.grid(True, alpha=0.3, axis='x') 
        
        fig.tight_layout()
        
        # Embed in tkinter
        self.canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")



if __name__ == "__main__":
    root = tk.Tk()
    root.title("Laundrify - Frontend")
    root.geometry("1000x650")
    app = App(root)
    app.grid(row=0, column=0, sticky='nsew')
    root.rowconfigure(0, weight=1)
    root.columnconfigure(0, weight=1)
    root.mainloop()
