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
        for Page in (NewOrderPage, ViewOrderPage, CustomersPage, ReportsPage):
            page = Page(container, self)
            page.grid(row=0, column=0, sticky="nsew")
            self.pages[Page.__name__] = page

        # bottom navigation
        nav = tk.Frame(self, bg=PRIMARY)
        nav.grid(row=content_row+1, column=0, sticky="ew", padx=8, pady=15)
        nav.columnconfigure((0,1,2,3), weight=1)

        self.nav_buttons = {}
        self.current_page = "NewOrderPage"
        
        btn_new = tk.Button(nav, text="New Order", font=TTL_TEXT, command=lambda: self.show("NewOrderPage"),
                            height=2, cursor="hand2")
        btn_view = tk.Button(nav, text="View Order", font=TTL_TEXT, command=lambda: self.show("ViewOrderPage"),
                            height=2, cursor="hand2")
        btn_customers = tk.Button(nav, text="Customers", font=TTL_TEXT, command=lambda: self.show("CustomersPage"),
                            height=2, cursor="hand2")
        btn_reports = tk.Button(nav, text="Reports", font=TTL_TEXT, command=lambda: self.show("ReportsPage"),
                            height=2, cursor="hand2")

        self.nav_buttons["NewOrderPage"] = btn_new
        self.nav_buttons["ViewOrderPage"] = btn_view
        self.nav_buttons["CustomersPage"] = btn_customers
        self.nav_buttons["ReportsPage"] = btn_reports

        btn_new.grid(row=0, column=0, padx=12, sticky="ew")
        btn_view.grid(row=0, column=1, padx=12, sticky="ew")
        btn_customers.grid(row=0, column=2, padx=12, sticky="ew")
        btn_reports.grid(row=0, column=3, padx=12, sticky="ew")

        self.show("NewOrderPage")

    def show(self, name):
        titles = {
            "NewOrderPage": "Laundrify - New Order",
            "ViewOrderPage": "Laundrify - View Order",
            "CustomersPage": "Laundrify - Customers",
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

        # Lookup existing customer and autofill fields
        lookup_btn = tk.Button(left, text="Lookup Customer", font=TTL_TEXT, bg=ACCENT, fg=SECONDARY, command=self.lookup_customer, width=20)
        lookup_btn.grid(row=10, column=0, columnspan=2, pady=(0,10))

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
        columns = ("service", "quantity", "price", "notes")
        self.order_tree = ttk.Treeview(right, columns=columns, show="headings")
        for col in columns:
            self.order_tree.heading(col, text=col.capitalize())
            # keep the notes column hidden from view
            if col == 'notes':
                self.order_tree.column(col, anchor="w", width=0, stretch=False)
                self.order_tree.heading(col, text='')
            else:
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

    def lookup_customer(self):
        import db
        from tkinter import messagebox
        # If phone entry has value, try to find directly
        phone = self.phone_entry.get().strip()
        if phone:
            try:
                for c in db.get_customers():
                    if c['Phone_Number'] == phone:
                        rec = dict(c)
                        # populate fields
                        self.first_name_entry.delete(0, tk.END); self.first_name_entry.insert(0, rec.get('First_Name',''))
                        self.last_name_entry.delete(0, tk.END); self.last_name_entry.insert(0, rec.get('Last_Name',''))
                        self.address_entry.delete(0, tk.END); self.address_entry.insert(0, rec.get('Address','') or '')
                        self.email_entry.delete(0, tk.END); self.email_entry.insert(0, rec.get('Email','') or '')
                        self.phone_entry.delete(0, tk.END); self.phone_entry.insert(0, rec.get('Phone_Number','') or '')
                        messagebox.showinfo('Found', f"Loaded customer {rec.get('First_Name','')} {rec.get('Last_Name','')}")
                        return
            except Exception:
                pass

        # Otherwise show a selection window with treeview to pick a customer
        sel_win = tk.Toplevel(self)
        sel_win.title('Select Customer')
        sel_win.geometry('760x360')
        sel_win.grab_set()
        sel_win.rowconfigure(1, weight=1); sel_win.columnconfigure(0, weight=1)

        # search row
        top = tk.Frame(sel_win, padx=8, pady=6)
        top.grid(row=0, column=0, sticky='ew')
        top.columnconfigure((1,3), weight=1)
        tk.Label(top, text='First Name:', font=TTL_TEXT).grid(row=0, column=0, sticky='w')
        entry_first = tk.Entry(top, font=REG_TEXT)
        entry_first.grid(row=0, column=1, sticky='ew', padx=6)
        tk.Label(top, text='Last Name:', font=TTL_TEXT).grid(row=0, column=2, sticky='w', padx=(12,6))
        entry_last = tk.Entry(top, font=REG_TEXT)
        entry_last.grid(row=0, column=3, sticky='ew')
        tk.Button(top, text='Search', font=TTL_TEXT, bg=SECONDARY, fg=PRIMARY, command=lambda: populate_filtered()).grid(row=0, column=4, padx=8)

        # container for tree
        container = tk.Frame(sel_win, padx=8, pady=6)
        container.grid(row=1, column=0, sticky='nsew')
        container.rowconfigure(0, weight=1); container.columnconfigure(0, weight=1)

        cols = ('ID','First Name','Last Name','Phone','Email','Address')
        tree = ttk.Treeview(container, columns=cols, show='headings')
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=110 if c!='Address' else 220, anchor='w')
        tree.grid(row=0, column=0, sticky='nsew')
        scrollbar = ttk.Scrollbar(container, command=tree.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        tree.configure(yscrollcommand=scrollbar.set)

        def populate(customers=None):
            for i in tree.get_children():
                tree.delete(i)
            import db as _db
            try:
                rows = customers if customers is not None else _db.get_customers()
            except Exception:
                rows = []
            for r in rows:
                rr = dict(r)
                tree.insert('', 'end', iid=str(rr.get('CustomerID')), values=(rr.get('CustomerID'), rr.get('First_Name',''), rr.get('Last_Name',''), rr.get('Phone_Number',''), rr.get('Email',''), rr.get('Address','')))

        def populate_filtered():
            f = entry_first.get().strip().lower()
            l = entry_last.get().strip().lower()
            import db as _db
            try:
                allc = _db.get_customers()
            except Exception:
                allc = []
            res = []
            for c in allc:
                fn = (c.get('First_Name','') or '').lower()
                ln = (c.get('Last_Name','') or '').lower()
                if f and f not in fn: continue
                if l and l not in ln: continue
                res.append(c)
            populate(res)

        def _on_double(e):
            sel = tree.selection()
            if not sel: return
            cid = int(sel[0])
            import db as _db
            rec = _db.get_customer_details(cid)
            if rec:
                rd = dict(rec)
                self.first_name_entry.delete(0, tk.END); self.first_name_entry.insert(0, rd.get('First_Name',''))
                self.last_name_entry.delete(0, tk.END); self.last_name_entry.insert(0, rd.get('Last_Name',''))
                self.address_entry.delete(0, tk.END); self.address_entry.insert(0, rd.get('Address','') or '')
                self.email_entry.delete(0, tk.END); self.email_entry.insert(0, rd.get('Email','') or '')
                self.phone_entry.delete(0, tk.END); self.phone_entry.insert(0, rd.get('Phone_Number','') or '')
            sel_win.destroy()

        tree.bind('<Double-1>', _on_double)

        def _select():
            sel = tree.selection()
            if not sel: return
            cid = int(sel[0])
            import db as _db
            rec = _db.get_customer_details(cid)
            if rec:
                rd = dict(rec)
                self.first_name_entry.delete(0, tk.END); self.first_name_entry.insert(0, rd.get('First_Name',''))
                self.last_name_entry.delete(0, tk.END); self.last_name_entry.insert(0, rd.get('Last_Name',''))
                self.address_entry.delete(0, tk.END); self.address_entry.insert(0, rd.get('Address','') or '')
                self.email_entry.delete(0, tk.END); self.email_entry.insert(0, rd.get('Email','') or '')
                self.phone_entry.delete(0, tk.END); self.phone_entry.insert(0, rd.get('Phone_Number','') or '')
            sel_win.destroy()

        btnf = tk.Frame(sel_win)
        btnf.grid(row=2, column=0, pady=8, sticky='ew')
        btnf.columnconfigure((0,1,2), weight=1)
        tk.Button(btnf, text='Select', command=_select, bg=SECONDARY, fg='white').grid(row=0, column=0, sticky='ew', padx=6)
        tk.Button(btnf, text='Cancel', command=sel_win.destroy).grid(row=0, column=1, sticky='ew', padx=6)
        tk.Button(btnf, text='Refresh', command=lambda: populate(), bg=PRIMARY, fg=SECONDARY).grid(row=0, column=2, sticky='ew', padx=6)

        populate()

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

        # capture current additional notes for this item and store it in hidden column
        item_notes = self.notes_text.get("1.0", "end-1c").strip()
        self.order_tree.insert("", "end", values=(service, quantity, f"₱ {price:.2f}", item_notes))
        # clear notes box after adding the item so next item can have its own notes
        try:
            self.notes_text.delete('1.0', tk.END)
        except Exception:
            pass
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
                # preserve per-item notes stored in hidden column (index 3)
                item_note = values[3] if len(values) > 3 else ''
                order_items.append({
                    'service': service,
                    'quantity': quantity_str,
                    'subtotal': price,
                    'notes': item_note
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
            if 'OrderID' in cols:
                cols.remove('OrderID')
            if include_action:
                cols.append('Action')
            frame = tk.Frame(parent)
            frame.pack(fill='both', expand=True)
            scrollbar = ttk.Scrollbar(frame)
            scrollbar.pack(side='right', fill='y')
            tree = ttk.Treeview(frame, columns=cols, show="tree headings", yscrollcommand=scrollbar.set)
            # keep a reference to scrollbar so we can bind its events later
            tree._scrollbar = scrollbar
            scrollbar.config(command=tree.yview)
            
            # Configure #0 column as OrderID
            tree.heading('#0', text='OrderID')
            tree.column('#0', width=100, anchor='w')
            
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
            t.bind('<<TreeviewOpen>>', lambda e: self._reposition_action_overlays(e), add='+')
            t.bind('<<TreeviewClose>>', lambda e: self._reposition_action_overlays(e), add='+')
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

    def _order_id_from_iid(self, iid):
        """Extract numeric order_id from an iid that may be '42', '42-1', or '42-total'."""
        try:
            return int(str(iid).split('-')[0])
        except Exception:
            return None

    def _create_action_overlays(self, tree):
        # create Label widgets positioned over the Action column cells (per-tree).
        # Place Edit overlays on all parent and child rows representing an order or service.
        self._clear_action_overlays(tree)
        cols = list(tree['columns'])
        if 'Action' not in cols:
            return
        action_col_index = cols.index('Action') + 1
        treemap = {}

        def get_all_items(parent=''):
            items = []
            for item in tree.get_children(parent):
                items.append(item)
                items.extend(get_all_items(item))
            return items

        all_iids = get_all_items()

        for iid in all_iids:
            order_id = self._order_id_from_iid(iid)
            if order_id is None:
                continue
            try:
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
                lbl.bind('<Button-1>', lambda e, target_iid=iid: self.open_edit_window(target_iid))
                treemap[iid] = lbl

                bbox = tree.bbox(iid, f"#{action_col_index}")
                if bbox:
                    x, y, w, h = bbox
                    lbl.place(x=x+2, y=y+1, width=w-4, height=h-2)
                    lbl.lift()
                else:
                    lbl.place_forget()
            except Exception:
                continue
        self.action_overlays[tree] = treemap

    def _reposition_action_overlays(self, event=None):
        # reposition existing overlays (call on configure/scroll/expand/collapse)
        for tree in (self.unpaid_tree, self.paid_tree):
            treemap = self.action_overlays.get(tree, {})
            cols = list(tree['columns'])
            if 'Action' not in cols:
                continue
            action_col_index = cols.index('Action') + 1

            def get_all_items(parent=''):
                items = []
                for item in tree.get_children(parent):
                    items.append(item)
                    items.extend(get_all_items(item))
                return items

            all_iids = set(get_all_items())

            for iid, lbl in list(treemap.items()):
                if iid not in all_iids:
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

    def _insert_order_rows(self, tree, order, include_action=True):
        """Insert a collapsible parent row with individual service child rows for mixed orders.
        For single-service orders, insert a single flat row.
        """
        import db
        oid = order['OrderID']
        date_str = order['Order_Received_At']
        customer = f"{order['First_Name']} {order['Last_Name']}"
        status = order['Order_Status']
        paid = "Yes" if order['Order_Payed_At'] else "No"
        total = order['Order_Total_Price']

        try:
            svc_rows = db.get_order_service_rows(oid)
        except Exception:
            svc_rows = []

        parent_iid = str(oid)

        if not svc_rows:
            # Fallback: single generic row
            vals = [date_str, customer, "—", "—", status, f"₱{total}", paid]
            if include_action:
                vals.append('')
            tree.insert('', 'end', iid=parent_iid, text=str(oid), values=tuple(vals))
            return

        is_mixed = len(svc_rows) > 1

        if not is_mixed:
            # Single-service order: display as flat row
            srow = svc_rows[0]
            vals = [
                date_str,
                customer,
                srow['service_name'],
                srow['qty_display'],
                status,
                f"₱{total}",
                paid,
            ]
            if include_action:
                vals.append('')
            tree.insert('', 'end', iid=parent_iid, text=str(oid), values=tuple(vals))
        else:
            # Mixed-service order: parent row collapsed by default
            try:
                qty_sum = db.get_order_qty_display(oid)
            except Exception:
                qty_sum = "—"
            parent_vals = [
                date_str,
                customer,
                f"Mixed Services ({len(svc_rows)})",
                qty_sum,
                status,
                f"₱{total}",
                paid,
            ]
            if include_action:
                parent_vals.append('')
            tree.insert('', 'end', iid=parent_iid, text=str(oid), values=tuple(parent_vals), open=False, tags=('parent_mixed',))

            for srow in svc_rows:
                svc_iid = f"{oid}-{srow['service_id']}"
                child_vals = [
                    '',  # Date Received blank
                    '',  # Customer blank
                    srow['service_name'],
                    srow['qty_display'],
                    srow['status'],  # Service status
                    f"₱{srow['subtotal']:.0f}",
                    srow['paid'],  # Service paid
                ]
                if include_action:
                    child_vals.append('')
                tree.insert(parent_iid, 'end', iid=svc_iid, text=svc_iid, values=tuple(child_vals), tags=('child_service',))

    def refresh_unpaid(self):
        import db
        tree = self.unpaid_tree
        for item in tree.get_children():
            tree.delete(item)
        try:
            orders = db.get_unpaid_orders()
            for order in orders:
                self._insert_order_rows(tree, order, include_action=True)
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
                self._insert_order_rows(tree, order, include_action=True)
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
                self._insert_order_rows(tree, order, include_action=False)
        except Exception as e:
            print(f"Error loading archived orders: {e}")

    def search_orders(self):
        term = self.search_entry.get().strip()
        if not term:
            self.refresh_all()
            return
        import db
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
        matching_iids = []

        for order in orders:
            oid = order['OrderID']
            customer_name = f"{order['First_Name']} {order['Last_Name']}"
            try:
                svc_rows = db.get_order_service_rows(oid)
            except Exception:
                svc_rows = []

            order_matched = False
            matched_child_iids = []

            # 1. Match by parent OrderID
            if str(oid).startswith(term):
                order_matched = True

            # 2. Match by customer name
            if term.lower() in customer_name.lower():
                order_matched = True

            # 3. Match by child service ID or service name
            for srow in svc_rows:
                child_iid = f"{oid}-{srow['service_id']}"
                if child_iid.startswith(term) or term == child_iid:
                    order_matched = True
                    matched_child_iids.append(child_iid)
                elif term.lower() in srow['service_name'].lower():
                    order_matched = True
                    matched_child_iids.append(child_iid)

            if order_matched:
                include_action = (idx in (0, 1))
                self._insert_order_rows(tree, order, include_action=include_action)
                found = True

                if matched_child_iids:
                    # Expand parent row immediately so children are drawn and can be selected
                    tree.item(str(oid), open=True)
                    matching_iids.extend(matched_child_iids)

        try:
            if idx in (0, 1):
                self._create_action_overlays(tree)
        except Exception:
            pass

        # Select and scroll to the matched child items
        if matching_iids:
            try:
                tree.selection_set(matching_iids)
                tree.see(matching_iids[0])
            except Exception:
                pass

        if not found:
            from tkinter import messagebox
            messagebox.showinfo("Search", f"No orders found matching '{term}'")

    def search_by_date(self):
        import db
        from tkinter import messagebox
        start_raw = self.date_from.get().strip()
        end_raw = self.date_to.get().strip()
        if not start_raw or not end_raw or start_raw in ("mm/dd/yyyy","") or end_raw in ("mm/dd/yyyy",""):
            messagebox.showwarning('Date Search', 'Please enter both From and To dates in mm/dd/yyyy format')
            return
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
        for item in tree.get_children():
            tree.delete(item)
        include_action = (idx in (0, 1))
        for order in orders:
            self._insert_order_rows(tree, order, include_action=include_action)
        try:
            if idx in (0, 1):
                self._create_action_overlays(tree)
        except Exception:
            pass

    def sort_by_status(self, status):
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

        for item in tree.get_children():
            tree.delete(item)

        if status == 'All':
            if idx == 0:
                self.refresh_unpaid()
            elif idx == 1:
                self.refresh_paid()
            else:
                self.refresh_archived()
            return

        try:
            orders = [o for o in orders if o['Order_Status'] == status]
            include_action = (idx in (0, 1))
            for order in orders:
                self._insert_order_rows(tree, order, include_action=include_action)
            try:
                if idx in (0, 1):
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

        # Pre-populate and initialize if selected
        selected_order_id = ""
        tree = self.get_tree_for_current_tab()
        if tree:
            sel = tree.selection()
            if sel:
                selected_order_id = str(sel[0])

        order_entry_var = tk.StringVar(value=selected_order_id)
        order_entry = tk.Entry(form_frame, textvariable=order_entry_var, width=30, font=("Arial", 10))
        order_entry.grid(row=0, column=1, sticky="ew", pady=15, padx=10)

        # Order selection: use a freeform search entry (supports order ID or customer name search)
        tk.Label(form_frame, text="Order ID / Customer:", font=("Arial", 11), bg="white").grid(row=0, column=0, sticky="w", pady=15)

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
                try:
                    o = db.get_order_details(int(oid))
                    if o:
                        status_combo.set(o['Order_Status'])
                except:
                    pass
                pick_win.destroy()
            btnf = tk.Button(pick_win, text='Select', command=_select)
            btnf.pack(pady=6)

        def _find_order():
            q = order_entry_var.get().strip()
            if not q:
                messagebox.showwarning('Find Order', 'Enter Order ID or Customer name', parent=status_win)
                return
            
            # Support child IDs like "5-3" by parsing the parent OrderID and ServiceID
            if '-' in q:
                try:
                    parts = q.split('-')
                    oid_clean = int(parts[0])
                    svc_id = int(parts[1])
                    svc_rows = db.get_order_service_rows(oid_clean)
                    target_svc = next((sr for sr in svc_rows if sr['service_id'] == svc_id), None)
                    if target_svc:
                        status_combo.set(target_svc['status'])
                        o = db.get_order_details(oid_clean)
                        messagebox.showinfo('Find Order', f"Found Service {svc_id} ({target_svc['service_name']}) for Order {oid_clean} ({o['First_Name']} {o['Last_Name']})\nCurrent Status: {target_svc['status']}", parent=status_win)
                        return
                except Exception:
                    pass

            # if numeric, try fetch by ID
            if q.isdigit():
                o = db.get_order_details(int(q))
                if not o:
                    messagebox.showinfo('Find Order', f'Order {q} not found', parent=status_win)
                    return
                # show brief info and update status combo
                order_entry_var.set(str(o['OrderID']))
                status_combo.set(o['Order_Status'])
                messagebox.showinfo('Find Order', f"Found Order {o['OrderID']} for {o['First_Name']} {o['Last_Name']}\nCurrent Status: {o['Order_Status']}", parent=status_win)
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
                o = db.get_order_details(int(matches[0][0]))
                if o:
                    status_combo.set(o['Order_Status'])
                messagebox.showinfo('Find Order', f"Found Order {matches[0][0]} for {matches[0][1]}", parent=status_win)
                return
            # multiple matches - let user pick
            _choose_from_matches(matches)

        tk.Button(form_frame, text='Find', command=_find_order).grid(row=0, column=2, padx=6)

        tk.Label(form_frame, text="New Status:", font=("Arial", 11), bg="white").grid(row=1, column=0, sticky="w", pady=15)
        status_combo = ttk.Combobox(form_frame, values=["Received", "In-Progress", "Ready", "Released"], width=30, state="readonly", font=("Arial", 10))
        status_combo.grid(row=1, column=1, sticky="ew", pady=15, padx=10)

        # Initialize status if pre-populated
        if selected_order_id:
            try:
                oid_clean = selected_order_id.split('-')[0]
                if '-' in selected_order_id:
                    svc_id = int(selected_order_id.split('-')[1])
                    svc_rows = db.get_order_service_rows(int(oid_clean))
                    target_svc = next((sr for sr in svc_rows if sr['service_id'] == svc_id), None)
                    if target_svc:
                        status_combo.set(target_svc['status'])
                else:
                    o = db.get_order_details(int(oid_clean))
                    if o:
                        status_combo.set(o['Order_Status'])
            except Exception:
                pass

        def update_and_close():
            order_id = order_entry_var.get().strip()
            new_status = status_combo.get()
            if not order_id or not new_status:
                messagebox.showwarning("Error", "Please select an order and status", parent=status_win)
                return
            try:
                if '-' in order_id:
                    oid_clean = order_id.split('-')[0]
                    svc_id = int(order_id.split('-')[1])
                    db.update_service_status(int(oid_clean), svc_id, new_status)
                    messagebox.showinfo("Success", f"Service {order_id} status updated to {new_status}", parent=status_win)
                else:
                    db.update_order_status(int(order_id), new_status)
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

        # Pre-populate and initialize if selected
        selected_order_id = ""
        tree = self.get_tree_for_current_tab()
        if tree:
            sel = tree.selection()
            if sel:
                selected_order_id = str(sel[0])

        order_entry_var = tk.StringVar(value=selected_order_id)
        order_entry = tk.Entry(form_frame, textvariable=order_entry_var, width=30, font=("Arial", 10))
        order_entry.grid(row=0, column=1, sticky="ew", pady=12, padx=10)

        tk.Label(form_frame, text="Order ID / Customer:", font=("Arial", 11), bg="white").grid(row=0, column=0, sticky="w", pady=12)

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
            
            # Support child IDs like "5-3" by parsing the parent OrderID and ServiceID
            if '-' in q:
                try:
                    parts = q.split('-')
                    oid_clean = int(parts[0])
                    svc_id = int(parts[1])
                    svc_rows = db.get_order_service_rows(oid_clean)
                    target_svc = next((sr for sr in svc_rows if sr['service_id'] == svc_id), None)
                    if target_svc:
                        amount_due_display.config(text=f"₱{target_svc['subtotal']:.2f}")
                        cash_entry.delete(0, tk.END)
                        return
                except Exception:
                    pass

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

        # Set initial amount due if pre-populated
        initial_amount = "0.00"
        if selected_order_id:
            try:
                oid_clean = selected_order_id.split('-')[0]
                if '-' in selected_order_id:
                    svc_id = int(selected_order_id.split('-')[1])
                    svc_rows = db.get_order_service_rows(int(oid_clean))
                    target_svc = next((sr for sr in svc_rows if sr['service_id'] == svc_id), None)
                    if target_svc:
                        initial_amount = f"₱{target_svc['subtotal']:.2f}"
                else:
                    o = db.get_order_details(int(oid_clean))
                    if o:
                        initial_amount = f"₱{o['Order_Total_Price']:.2f}"
            except Exception:
                pass

        amount_due_display = tk.Label(form_frame, text=initial_amount, font=("Arial", 13, "bold"), bg="#ecf0f1", fg="#2c3e50", relief="sunken", width=35)
        amount_due_display.grid(row=1, column=1, sticky="ew", pady=12, padx=10)
        tk.Label(form_frame, text="Amount Due (₱):", font=("Arial", 11), bg="white").grid(row=1, column=0, sticky="w", pady=12)

        cash_entry = tk.Entry(form_frame, width=37, font=("Arial", 10), bd=1, relief="solid")
        cash_entry.grid(row=2, column=1, sticky="ew", pady=12, padx=10)
        tk.Label(form_frame, text="Cash Received (₱):", font=("Arial", 11), bg="white").grid(row=2, column=0, sticky="w", pady=12)

        def process_payment():
            order_id = order_entry_var.get().strip()
            cash_str = cash_entry.get().strip()
            if not order_id or not cash_str:
                messagebox.showwarning("Error", "Please select an order and enter cash amount", parent=payment_win)
                return
            try:
                cash = float(cash_str)
                if '-' in order_id:
                    oid_clean = order_id.split('-')[0]
                    svc_id = int(order_id.split('-')[1])
                    result = db.process_service_payment(int(oid_clean), svc_id, cash)
                else:
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
        col = widget.identify_column(event.x)
        if col == f"#{len(widget['columns'])}":
            row_id = widget.identify_row(event.y)
            if not row_id:
                return
            s = str(row_id)
            if s.endswith('-total') or s.endswith('-0'):
                return
            self.open_edit_window(row_id)

    def open_edit_window(self, target_id):
        import db
        from tkinter import messagebox
        import sqlite3

        # Parse target ID
        is_child = '-' in str(target_id)
        if is_child:
            oid = int(str(target_id).split('-')[0])
            svc_id = int(str(target_id).split('-')[1])
        else:
            oid = int(target_id)

        # Get parent order details for reference
        order = db.get_order_details(oid)
        if not order:
            messagebox.showerror("Not found", "Order not found")
            return
        
        try:
            order = dict(order)
        except Exception:
            pass

        edit_win = tk.Toplevel(self)
        edit_win.title(f"Edit Order {target_id}" if not is_child else f"Edit Service {target_id}")
        edit_win.geometry("520x420")
        edit_win.resizable(False, False)
        edit_win.grab_set()

        form = tk.Frame(edit_win, padx=12, pady=12)
        form.pack(fill='both', expand=True)
        form.columnconfigure(1, weight=1)

        if not is_child:
            # Edit Parent Order UI
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

            # tk.Label(form, text="Notes:").grid(row=5, column=0, sticky='nw')
            # notes = tk.Text(form, height=6)
            # notes.grid(row=5, column=1, sticky='ew')
            # notes.insert('1.0', order.get('Order_Notes') or '')

            def save_changes():
                try:
                    first = first_name.get().strip()
                    last = last_name.get().strip()
                    db.update_customer(order['CustomerID'], first, last, ph.get().strip(), email.get().strip(), '')
                    # db.update_order(oid, status.get(), notes.get('1.0', 'end-1c').strip())
                    messagebox.showinfo('Saved', 'Order updated')
                    edit_win.destroy()
                    self.refresh_all()
                except Exception as e:
                    messagebox.showerror('Error', str(e))

            def delete_target():
                if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete Order {oid}?\nThis will permanently delete the order and all its items."):
                    try:
                        db.delete_order(oid)
                        messagebox.showinfo("Deleted", f"Order {oid} has been deleted.")
                        edit_win.destroy()
                        self.refresh_all()
                    except Exception as e:
                        messagebox.showerror('Error', str(e))

        else:
            # Edit Child Service UI
            svc_rows = db.get_order_service_rows(oid)
            target_svc = next((sr for sr in svc_rows if sr['service_id'] == svc_id), None)
            if not target_svc:
                messagebox.showerror("Not found", f"Service details not found for service {svc_id}")
                edit_win.destroy()
                return

            tk.Label(form, text="Service Name:").grid(row=0, column=0, sticky='w', pady=8)
            tk.Label(form, text=target_svc['service_name'], font=("Arial", 11, "bold")).grid(row=0, column=1, sticky='w', pady=8)

            tk.Label(form, text="Qty/Wt:").grid(row=1, column=0, sticky='w', pady=8)
            qty_entry = tk.Entry(form)
            qty_entry.grid(row=1, column=1, sticky='ew', pady=8)
            qty_entry.insert(0, str(target_svc['qty_display']))

            tk.Label(form, text="Subtotal (₱):").grid(row=2, column=0, sticky='w', pady=8)
            subtotal_entry = tk.Entry(form)
            subtotal_entry.grid(row=2, column=1, sticky='ew', pady=8)
            subtotal_entry.insert(0, f"{target_svc['subtotal']:.2f}")

            tk.Label(form, text="Status:").grid(row=3, column=0, sticky='w', pady=8)
            status_combo = ttk.Combobox(form, values=["Received","In-Progress","Ready","Released"], state='readonly')
            status_combo.grid(row=3, column=1, sticky='ew', pady=8)
            status_combo.set(target_svc['status'])

            tk.Label(form, text="Paid:").grid(row=4, column=0, sticky='w', pady=8)
            paid_combo = ttk.Combobox(form, values=["Yes", "No"], state='readonly')
            paid_combo.grid(row=4, column=1, sticky='ew', pady=8)
            paid_combo.set(target_svc['paid'])

            # Read-only display for per-item notes
            tk.Label(form, text="Notes:").grid(row=5, column=0, sticky='nw', pady=8)
            notes_display = tk.Text(form, height=4, width=40, wrap='word', bg='white', relief='sunken')
            notes_display.grid(row=5, column=1, sticky='ew', pady=8)
            try:
                notes_display.insert('1.0', target_svc.get('notes','') or '')
                notes_display.config(state='disabled')
            except Exception:
                pass

            def save_changes():
                try:
                    qty_val = qty_entry.get().strip()
                    subtotal = float(subtotal_entry.get().strip())
                    status = status_combo.get()
                    paid_val = paid_combo.get() == "Yes"
                    
                    db.update_service_details(oid, svc_id, qty_val, subtotal, status, paid_val)
                    messagebox.showinfo('Saved', 'Service details updated')
                    edit_win.destroy()
                    self.refresh_all()
                except ValueError:
                    messagebox.showerror('Error', 'Subtotal must be a valid number')
                except Exception as e:
                    messagebox.showerror('Error', str(e))

            def delete_target():
                if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete service {target_svc['service_name']} ({target_id})?\nIf this is the only service in the order, the order itself will be deleted."):
                    try:
                        _, parent_deleted = db.delete_service_row(oid, svc_id)
                        if parent_deleted:
                            messagebox.showinfo("Deleted", f"Service deleted. Since it was the last service, Order {oid} has also been deleted.")
                        else:
                            messagebox.showinfo("Deleted", f"Service {target_svc['service_name']} has been deleted from Order {oid}.")
                        edit_win.destroy()
                        self.refresh_all()
                    except Exception as e:
                        messagebox.showerror('Error', str(e))

        # Bottom Button Frame (Confirm, Delete, Cancel)
        btn_frame = tk.Frame(form, bg='white')
        btn_frame.grid(row=6, column=0, columnspan=2, pady=15, sticky='ew')
        btn_frame.columnconfigure((0, 1, 2), weight=1)
        
        tk.Button(btn_frame, text='Confirm', command=save_changes, font=("Arial", 11, "bold"), bg="#3498db", fg="white", height=2, cursor="hand2").grid(row=0, column=0, sticky='ew', padx=5)
        tk.Button(btn_frame, text='Delete', command=delete_target, font=("Arial", 11, "bold"), bg="#e74c3c", fg="white", height=2, cursor="hand2").grid(row=0, column=1, sticky='ew', padx=5)
        tk.Button(btn_frame, text='Cancel', command=edit_win.destroy, font=("Arial", 11), bg="#95a5a6", fg="white", height=2, cursor="hand2").grid(row=0, column=2, sticky='ew', padx=5)

class CustomersPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.configure(bg=PRIMARY)
        self.controller = controller
        self.action_overlays = {}

        main_frame = tk.Frame(self, bd=1, relief="solid", bg=PRIMARY)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)

        # Header and count
        header_frame = tk.Frame(main_frame, bg=PRIMARY)
        header_frame.grid(row=0, column=0, sticky='ew', padx=12, pady=(8,4))
        header_frame.columnconfigure(0, weight=1)
        tk.Label(header_frame, text='There are {0} Customer Records'.format('0'), font=TTL_TEXT, bg=PRIMARY).grid(row=0, column=0, sticky='w')
        self.count_label = header_frame.grid_slaves(row=0, column=0)[0]

        # Search area
        search_frame = tk.Frame(main_frame, bg=PRIMARY)
        search_frame.grid(row=1, column=0, sticky='ew', padx=12, pady=6)
        # left: ID search
        tk.Label(search_frame, text='Search ID:', font=TTL_TEXT, bg=PRIMARY).grid(row=0, column=0, sticky='w')
        self.search_id_entry = tk.Entry(search_frame, width=12, font=REG_TEXT)
        self.search_id_entry.grid(row=0, column=1, padx=6)
        tk.Button(search_frame, text='Search by ID', font=TTL_TEXT, bg=SECONDARY, fg=PRIMARY, command=self.search_by_id).grid(row=0, column=2, padx=6)

        # right: name search
        tk.Label(search_frame, text='First Name:', font=TTL_TEXT, bg=PRIMARY).grid(row=0, column=3, padx=(30,6))
        self.search_first = tk.Entry(search_frame, width=15, font=REG_TEXT)
        self.search_first.grid(row=0, column=4)
        tk.Label(search_frame, text='Last Name:', font=TTL_TEXT, bg=PRIMARY).grid(row=0, column=5, padx=(12,6))
        self.search_last = tk.Entry(search_frame, width=15, font=REG_TEXT)
        self.search_last.grid(row=0, column=6)
        tk.Button(search_frame, text='Search by Name', font=TTL_TEXT, bg=SECONDARY, fg=PRIMARY, command=self.search_by_name).grid(row=0, column=7, padx=8)

        sep = ttk.Separator(main_frame, orient='horizontal')
        sep.grid(row=2, column=0, sticky='ew', padx=8, pady=(4,8))

        # Table area
        table_frame = tk.Frame(main_frame)
        table_frame.grid(row=3, column=0, sticky="nsew", padx=12, pady=6)
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.grid(row=0, column=1, sticky='ns')

        cols = ("First Name", "Last Name", "Phone", "Email", "Address", "Action")
        self.customer_tree = ttk.Treeview(table_frame, columns=cols, show="tree headings", yscrollcommand=scrollbar.set)
        self.customer_tree._scrollbar = scrollbar
        scrollbar.config(command=self.customer_tree.yview)

        self.customer_tree.heading('#0', text='ID')
        self.customer_tree.column('#0', width=80, anchor='w')
        for col in cols:
            self.customer_tree.heading(col, text=col)
            self.customer_tree.column(col, width=140 if col != 'Action' else 120, anchor='w')

        self.customer_tree.grid(row=0, column=0, sticky='nsew')

        # bind events
        self.customer_tree.bind('<Configure>', lambda e: self._reposition_action_overlays(e), add='+')
        self.customer_tree.bind('<ButtonRelease-1>', lambda e: self._reposition_action_overlays(e), add='+')
        self.customer_tree.bind('<Motion>', lambda e: self._reposition_action_overlays(e), add='+')
        try:
            self.customer_tree._scrollbar.bind('<ButtonRelease-1>', lambda e: self._reposition_action_overlays(e), add='+')
            self.customer_tree._scrollbar.bind('<B1-Motion>', lambda e: self._reposition_action_overlays(e), add='+')
        except Exception:
            pass

        # Sort buttons at bottom
        sort_frame = tk.Frame(main_frame, bg=PRIMARY)
        sort_frame.grid(row=4, column=0, sticky='ew', padx=12, pady=(8,6))
        tk.Label(sort_frame, width=12, text='Sort Rows By:', font=TTL_TEXT, bg=PRIMARY).grid(row=0, column=0, sticky='w')
        tk.Button(sort_frame, width=12, text='ID', font=TTL_TEXT, bg=PRIMARY, fg=SECONDARY, command=lambda: self.sort_by('id')).grid(row=0, column=1, padx=8)
        tk.Button(sort_frame, width=12, text='First Name', font=TTL_TEXT, bg=PRIMARY, fg=SECONDARY, command=lambda: self.sort_by('first')).grid(row=0, column=2, padx=8)
        tk.Button(sort_frame, width=12, text='Last Name', font=TTL_TEXT, bg=PRIMARY, fg=SECONDARY, command=lambda: self.sort_by('last')).grid(row=0, column=3, padx=8)

        self.refresh_customers()

    def refresh_customers(self, customers_list=None):
        import db
        # populate tree with provided list or all
        for item in self.customer_tree.get_children():
            self.customer_tree.delete(item)
        try:
            customers = customers_list if customers_list is not None else db.get_customers()
        except Exception:
            customers = []
        for c in customers:
            cid = c['CustomerID']
            vals = (c['First_Name'], c['Last_Name'], c['Phone_Number'], c['Email'] or '', c['Address'] or '', '')
            self.customer_tree.insert('', 'end', iid=str(cid), text=str(cid), values=vals)
        # update count label
        try:
            cnt = len(customers)
            self.count_label.config(text=f'There are {cnt} Customer Records')
        except Exception:
            pass
        try:
            self._create_action_overlays()
        except Exception:
            pass

    def search_by_id(self):
        import db
        from tkinter import messagebox
        q = self.search_id_entry.get().strip()
        if not q:
            self.refresh_customers(); return
        if not q.isdigit():
            messagebox.showwarning('Search', 'ID must be numeric')
            return
        try:
            rec = db.get_customer_details(int(q))
            if not rec:
                messagebox.showinfo('Search', f'No customer found with ID {q}')
                return
            self.refresh_customers([rec])
        except Exception as e:
            messagebox.showerror('Search Error', str(e))

    def search_by_name(self):
        import db
        from tkinter import messagebox
        first = self.search_first.get().strip()
        last = self.search_last.get().strip()
        if not first and not last:
            self.refresh_customers(); return
        try:
            customers = db.get_customers()
            results = []
            for c in customers:
                fn = (c.get('First_Name','') or '').lower()
                ln = (c.get('Last_Name','') or '').lower()
                if first and first.lower() not in fn:
                    continue
                if last and last.lower() not in ln:
                    continue
                results.append(c)
            if not results:
                messagebox.showinfo('Search', 'No matching customers found')
            self.refresh_customers(results)
        except Exception as e:
            messagebox.showerror('Search Error', str(e))

    def sort_by(self, key):
        import db
        try:
            customers = list(db.get_customers())
            if key == 'id':
                customers.sort(key=lambda c: int(c['CustomerID']))
            elif key == 'first':
                customers.sort(key=lambda c: (c.get('First_Name') or '').lower())
            elif key == 'last':
                customers.sort(key=lambda c: (c.get('Last_Name') or '').lower())
            self.refresh_customers(customers)
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror('Sort Error', str(e))

    def _confirm_delete(self, iid):
        import db
        from tkinter import messagebox
        try:
            cid = int(iid)
        except Exception:
            return
        if messagebox.askyesno('Confirm Delete', f'Delete customer {cid}?'):
            try:
                db.delete_customer(cid)
                self.refresh_customers()
            except Exception as e:
                messagebox.showerror('Error', str(e))

    def _clear_action_overlays(self):
        for w in list(self.action_overlays.values()):
            try:
                w.destroy()
            except Exception:
                pass
        self.action_overlays = {}

    def _create_action_overlays(self):
        self._clear_action_overlays()
        cols = list(self.customer_tree['columns'])
        if 'Action' not in cols:
            return
        action_col_index = cols.index('Action') + 1
        treemap = {}
        for iid in self.customer_tree.get_children():
            try:
                frame = tk.Frame(self.customer_tree, bg='white')
                # use grid inside the overlay frame
                btn_edit = tk.Button(frame, text='Edit', fg='#0563c1', cursor='hand2', bd=0, command=lambda cid=iid: self.open_edit_window(cid))
                btn_delete = tk.Button(frame, text='Delete', fg='#e74c3c', cursor='hand2', bd=0, command=lambda cid=iid: self._confirm_delete(cid))
                btn_edit.grid(row=0, column=0, padx=(2,4))
                btn_delete.grid(row=0, column=1, padx=(4,2))
                treemap[iid] = frame
                bbox = self.customer_tree.bbox(iid, f"#{action_col_index}")
                if bbox:
                    x, y, w, h = bbox
                    frame.place(x=x+2, y=y+1, width=w-4, height=h-2)
                    frame.lift()
                else:
                    frame.place_forget()
            except Exception:
                continue
        self.action_overlays = treemap

    def _reposition_action_overlays(self, event=None):
        cols = list(self.customer_tree['columns'])
        if 'Action' not in cols:
            return
        action_col_index = cols.index('Action') + 1
        all_iids = list(self.customer_tree.get_children())
        for iid, frame in list(self.action_overlays.items()):
            if iid not in all_iids:
                try:
                    frame.destroy()
                except Exception:
                    pass
                del self.action_overlays[iid]
                continue
            bbox = self.customer_tree.bbox(iid, f"#{action_col_index}")
            if not bbox:
                try:
                    frame.place_forget()
                except Exception:
                    pass
            else:
                x, y, w, h = bbox
                try:
                    frame.place(x=x+2, y=y+1, width=w-4, height=h-2)
                    frame.lift()
                except Exception:
                    pass

    def open_edit_window(self, iid):
        import db
        from tkinter import messagebox
        cid = int(iid)
        rec = db.get_customer_details(cid)
        if not rec:
            messagebox.showerror('Error', 'Customer not found')
            return
        edit_win = tk.Toplevel(self)
        edit_win.title(f"Edit Customer {cid}")
        edit_win.geometry("420x360")
        edit_win.grab_set()
        edit_win.rowconfigure(0, weight=1); edit_win.columnconfigure(0, weight=1)

        form = tk.Frame(edit_win, padx=12, pady=12)
        form.grid(row=0, column=0, sticky='nsew')
        form.columnconfigure(1, weight=1)

        tk.Label(form, text='First Name:').grid(row=0, column=0, sticky='w')
        e_first = tk.Entry(form); e_first.grid(row=0, column=1, sticky='ew'); e_first.insert(0, rec['First_Name'])
        tk.Label(form, text='Last Name:').grid(row=1, column=0, sticky='w')
        e_last = tk.Entry(form); e_last.grid(row=1, column=1, sticky='ew'); e_last.insert(0, rec['Last_Name'])
        tk.Label(form, text='Phone:').grid(row=2, column=0, sticky='w')
        e_phone = tk.Entry(form); e_phone.grid(row=2, column=1, sticky='ew'); e_phone.insert(0, rec['Phone_Number'])
        tk.Label(form, text='Email:').grid(row=3, column=0, sticky='w')
        e_email = tk.Entry(form); e_email.grid(row=3, column=1, sticky='ew'); e_email.insert(0, rec.get('Email','') or '')
        tk.Label(form, text='Address:').grid(row=4, column=0, sticky='nw')
        e_addr = tk.Text(form, height=4); e_addr.grid(row=4, column=1, sticky='ew'); e_addr.insert('1.0', rec.get('Address','') or '')

        def save_changes():
            try:
                db.update_customer(cid, e_first.get().strip(), e_last.get().strip(), e_phone.get().strip(), e_email.get().strip(), e_addr.get('1.0','end-1c').strip())
                messagebox.showinfo('Saved', 'Customer updated')
                edit_win.destroy()
                self.refresh_customers()
            except Exception as e:
                messagebox.showerror('Error', str(e))

        def do_delete():
            try:
                db.delete_customer(cid)
                messagebox.showinfo('Deleted', 'Customer deleted')
                edit_win.destroy()
                self.refresh_customers()
            except Exception as e:
                messagebox.showerror('Error', str(e))

        btnf = tk.Frame(form); btnf.grid(row=5, column=0, columnspan=2, pady=12); btnf.columnconfigure((0,1), weight=1)
        tk.Button(btnf, text='Save', command=save_changes, bg=SECONDARY, fg='white').grid(row=0, column=0, sticky='ew', padx=6)
        tk.Button(btnf, text='Delete', command=lambda: (messagebox.askyesno('Confirm','Delete customer?') and do_delete()), bg='#e74c3c', fg='white').grid(row=0, column=1, sticky='ew', padx=6)

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
