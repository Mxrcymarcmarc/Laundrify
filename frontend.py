import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
import re

from db import get_received_report_data, get_revenue_report_data, get_ready_report_data, get_overdue_report_data, get_top_services_report_data, get_top_customers_by_orders, get_top_customers_by_revenue, get_next_customer_id

PRIMARY = "#F0EDE5"
SECONDARY = "#4A6FA5"
ACCENT = "#B8C5D6"
HDR_TEXT = ("Cooper Black", 24)
HDR2_TEXT = ("Arial Black", 15)
TTL_TEXT = ("Arial", 11, "bold")
REG_TEXT = ("Arial", 11)

def format_db_date(date_str):
    """Converts a raw database timestamp into a beautiful, readable format."""
    if not date_str:
        return ""
    try:
        from datetime import datetime
        # Parse the raw format SQLite uses
        dt = datetime.strptime(date_str.strip(), "%Y-%m-%d %H:%M:%S")
        # %B = Full Month name, %d = Day, %Y = 4-digit Year, %I:%M %p = 12-hour time with AM/PM
        return dt.strftime("%m/%d/%Y | %I:%M %p")
    except Exception:
        # Fallback if the date string is formatted slightly differently (e.g., date only)
        try:
            from datetime import datetime
            dt = datetime.strptime(date_str.strip(), "%Y-%m-%d")
            return dt.strftime("%B %d, %Y")
        except Exception:
            return date_str # Return original string if parsing fails entirely

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
                l_price = s['Large_Unit_Price']
                if l_price is None: l_price = price
            except Exception:
                l_price = price
            try:
                unit = (s['Service_Unit'] or 'pcs').lower()
            except Exception:
                unit = 'pcs'
            if unit == 'kg':
                page.service_map[name] = ('weight', price)
            else:
                # for pcs show size radios by default (small/large)
                page.service_map[name] = ('size', {'small': price, 'large': l_price})
    except Exception:
        pass
    # update combobox values if combobox exists
    try:
        page.service_combo['values'] = list(page.service_map.keys())
    except Exception:
        pass

class ScrollableGridTable(tk.Frame):
    def __init__(self, parent, columns, include_action=True, edit_callback=None, delete_callback=None, double_click_callback=None):
        super().__init__(parent, bg="white")
        self.columns = columns
        self.include_action = include_action
        self.edit_callback = edit_callback
        self.delete_callback = delete_callback
        self.double_click_callback = double_click_callback
        
        self.alignments = {}
        self.widths = {}
        for c in columns:
            if c in ("Qty/Wt", "Total", "OrderID", "ID", "Total Revenue", "Quantity", "Price"):
                self.alignments[c] = "e"
                self.widths[c] = 12
            elif c in ("Action", "Rank", "Total Orders"):
                self.alignments[c] = "center"
                self.widths[c] = 15
            elif c in ("Status", "Paid", "Date Received"):
                self.alignments[c] = "w"
                self.widths[c] = 15
            elif c == "Service":
                self.alignments[c] = "w"
                self.widths[c] = 20
            else:
                self.alignments[c] = "w"
                self.widths[c] = 20

        self.canvas = tk.Canvas(self, bg="white", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        
        # Grid frame container with dark background for 1px gridlines
        self.grid_frame = tk.Frame(self.canvas, bg="#cccccc") 
        self.canvas_window = self.canvas.create_window((0, 0), window=self.grid_frame, anchor="nw")
        
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        self.grid_frame.bind('<Configure>', self._on_frame_configure)
        
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        self.rows = {} # iid -> dict
        self.row_order = [] # list of iids in order
        self.current_row_idx = 1
        
        self.selected_iids = []
        
        self._build_headers()

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)
        
    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _build_headers(self):
        for col_idx, col_name in enumerate(self.columns):
            anchor = "w"
            lbl = tk.Label(self.grid_frame, text=col_name, font=("Arial", 11, "bold"), fg="#4A6FA5", bg="#ffffff", anchor=anchor, padx=12, pady=6, width=self.widths.get(col_name, 15))
            lbl.grid(row=0, column=col_idx, sticky="nsew", padx=1, pady=1)
            if col_name in ("Customer", "Service", "First Name", "Last Name", "Address", "Email"):
                self.grid_frame.columnconfigure(col_idx, weight=1)

    def get_children(self, parent=''):
        if not parent:
            return [iid for iid, r in self.rows.items() if not r.get('parent_iid')]
        else:
            return [iid for iid, r in self.rows.items() if r.get('parent_iid') == parent]

    def delete(self, iid):
        if iid in self.rows:
            children = self.get_children(iid)
            for c in children:
                self.delete(c)
            
            row_data = self.rows.pop(iid)
            for w in row_data['widgets']:
                w.destroy()
            if iid in self.row_order:
                self.row_order.remove(iid)
            if iid in self.selected_iids:
                self.selected_iids.remove(iid)

    def clear_all(self):
        for iid in list(self.rows.keys()):
            self.delete(iid)
        self.current_row_idx = 1
        self.selected_iids = []
        self.row_order = []
        try:
            self.canvas.yview_moveto(0)
        except Exception:
            pass

    def insert(self, parent, index, iid=None, text='', values=(), tags=(), open=False):
        if iid is None:
            import uuid
            iid = str(uuid.uuid4())
        row_idx = self.current_row_idx
        self.current_row_idx += 1
        
        bg_color = "#ffffff"
        text_color = "#2c3e50"
        font_config = ("Arial", 11)
        
        if 'evenrow' in tags:
            bg_color = "#f8f9fa"
            
        if 'child_service' in tags:
            bg_color = "#edf5fc" # distinct light-blue background highlight across entire child row
            
        if 'top1' in tags:
            bg_color = "#ffeaa7"
            font_config = ("Arial", 11, "bold")
        elif 'top2' in tags:
            bg_color = "#dfe6e9"
            font_config = ("Arial", 11, "bold")
        elif 'top3' in tags:
            bg_color = "#fab1a0"
            font_config = ("Arial", 11, "bold")
            
        row_data = {
            'iid': iid,
            'parent_iid': parent if parent else None,
            'widgets': [],
            'open': open,
            'bg_color': bg_color,
            'tags': tags,
            'text': text,
            'values': values
        }
        
        for col_idx, col_name in enumerate(self.columns):
            cell_frame = tk.Frame(self.grid_frame, bg=bg_color)
            cell_frame.grid(row=row_idx, column=col_idx, sticky="nsew", padx=1, pady=1)
            row_data['widgets'].append(cell_frame)
            
            cell_frame.bind("<Button-1>", lambda e, i=iid: self._on_row_click(i))
            
            if col_name == "Action":
                has_children = 'parent_mixed' in tags
                
                if self.delete_callback:
                    btn_del = tk.Button(cell_frame, text='Delete', fg='#e74c3c', bg=bg_color, activebackground=bg_color, activeforeground='#c0392b', cursor='hand2', bd=0, command=lambda i=iid: self.delete_callback(i))
                    btn_del.pack(side='right', padx=(10, 40))
                
                if self.edit_callback and not has_children:
                    btn_edit = tk.Button(cell_frame, text='Edit', fg='#0563c1', bg=bg_color, activebackground=bg_color, activeforeground='#044280', cursor='hand2', bd=0, command=lambda i=iid: self.edit_callback(i))
                    if self.delete_callback:
                        separator = tk.Frame(cell_frame, width=1, bg="#cccccc", height=22)
                        separator.pack(side='right', padx=(0, 10), pady=6, fill='y')
                        btn_edit.pack(side='right', padx=(10, 15)) # Extra space between Edit and Delete
                    else:
                        btn_edit.pack(expand=True) # Center if only edit button is present
            else:
                if col_idx == 0:
                    val = text
                else:
                    v_idx = col_idx - 1
                    val = values[v_idx] if v_idx < len(values) else ""
                    
                anchor = self.alignments.get(col_name, "w")
                
                # Expand toggle in the first column for parent_mixed
                if col_name == self.columns[0] and 'parent_mixed' in tags:
                    # Create an inner frame to hold toggle + label
                    inner_frame = tk.Frame(cell_frame, bg=bg_color)
                    inner_frame.pack(side="left" if anchor == "w" else "right", fill="both", expand=True, padx=4, pady=8)
                    
                    btn_toggle = tk.Label(inner_frame, text="▼" if open else "▶", font=("Arial", 10), fg="#4A6FA5", bg=bg_color, cursor='hand2')
                    btn_toggle.pack(side="left", padx=(0, 4))
                    btn_toggle.bind("<Button-1>", lambda e, i=iid: self.toggle_expand(i))
                    row_data['toggle_btn'] = btn_toggle
                    
                    lbl = tk.Label(inner_frame, text=val, font=font_config, fg=text_color, bg=bg_color, anchor=anchor)
                    lbl.pack(side="left" if anchor == "w" else "right", fill="both", expand=True)
                    lbl.bind("<Button-1>", lambda e, i=iid: self._on_row_click(i))
                    if self.double_click_callback:
                        lbl.bind("<Double-1>", lambda e, i=iid: self.double_click_callback(i))
                        inner_frame.bind("<Double-1>", lambda e, i=iid: self.double_click_callback(i))
                        cell_frame.bind("<Double-1>", lambda e, i=iid: self.double_click_callback(i))
                else:
                    lbl = tk.Label(cell_frame, text=val, font=font_config, fg=text_color, bg=bg_color, anchor=anchor)
                    lbl.pack(side="left" if anchor == "w" else "right", fill="both", expand=True, padx=4, pady=8)
                    lbl.bind("<Button-1>", lambda e, i=iid: self._on_row_click(i))
                    if self.double_click_callback:
                        lbl.bind("<Double-1>", lambda e, i=iid: self.double_click_callback(i))
                        cell_frame.bind("<Double-1>", lambda e, i=iid: self.double_click_callback(i))

        self.rows[iid] = row_data
        self.row_order.append(iid)
        
        if parent:
            parent_data = self.rows.get(parent)
            if parent_data and not parent_data['open']:
                for w in row_data['widgets']:
                    w.grid_remove()
        return iid

    def toggle_expand(self, iid):
        row_data = self.rows.get(iid)
        if not row_data: return
        is_open = not row_data['open']
        row_data['open'] = is_open
        if 'toggle_btn' in row_data:
            row_data['toggle_btn'].config(text="▼" if is_open else "▶")
            
        children = self.get_children(iid)
        for child_iid in children:
            child_data = self.rows[child_iid]
            if is_open:
                for w in child_data['widgets']:
                    w.grid()
            else:
                for w in child_data['widgets']:
                    w.grid_remove()

    def item(self, iid, option=None, **kwargs):
        row_data = self.rows.get(iid)
        if not row_data: return {}
        
        if option == 'values':
            return (row_data.get('text', ''),) + tuple(row_data.get('values', ()))
            
        open_val = kwargs.get('open', option if isinstance(option, bool) else None)
        if open_val is not None and row_data['open'] != open_val:
            self.toggle_expand(iid)
            
        return {'open': row_data['open'], 'values': (row_data.get('text', ''),) + tuple(row_data.get('values', ()))}

    def _on_row_click(self, iid):
        self.selection_set([iid])

    def selection(self):
        return self.selected_iids

    def selection_set(self, iids):
        for old_iid in self.selected_iids:
            if old_iid in self.rows:
                row_data = self.rows[old_iid]
                for w in row_data['widgets']:
                    w.config(bg=row_data['bg_color'])
                    for child in w.winfo_children():
                        child.config(bg=row_data['bg_color'])
                        
        self.selected_iids = list(iids)
        
        sel_bg = "#ACC8E5"
        for new_iid in self.selected_iids:
            if new_iid in self.rows:
                row_data = self.rows[new_iid]
                for w in row_data['widgets']:
                    w.config(bg=sel_bg)
                    for child in w.winfo_children():
                        child.config(bg=sel_bg)

    def see(self, iid):
        if iid in self.rows:
            row_data = self.rows[iid]
            w = row_data['widgets'][0]
            y = w.winfo_y()
            # Simple scroll
            try:
                self.canvas.yview_moveto(y / self.grid_frame.winfo_height())
            except Exception:
                pass


class App(tk.Frame):
    def __init__(self, parent, show_header=True, backend=None, title_callback=None):
        super().__init__(parent)
        self.backend = backend
        self.title_callback = title_callback or (lambda t: None)
        self.configure(bg=PRIMARY)

        # Global Treeview Style
        style = ttk.Style()
        style.configure("Fun.Treeview", 
                        background="#ffffff",
                        foreground="#2c3e50",
                        rowheight=35,
                        fieldbackground="#ffffff",
                        font=("Arial", 11),
                        borderwidth=0)
        style.configure("Fun.Treeview.Heading", 
                        font=("Arial", 11, "bold"), 
                        foreground="#4A6FA5",
                        borderwidth=1,
                        relief="flat")
        style.map("Fun.Treeview", background=[('selected', ACCENT)], foreground=[('selected', 'black')])

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
        container.grid(row=content_row, column=0, sticky="nsew", padx=8, pady=(8, 0))
        container.rowconfigure(0, weight=1)
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
        # auto-refresh view/customers page when shown
        try:
            if name == 'ViewOrderPage':
                self.pages[name].refresh_all()
            elif name == 'CustomersPage':
                self.pages[name].refresh_customers()
            elif name == 'NewOrderPage':
                if not self.pages[name].first_name_entry.get().strip() and not self.pages[name].last_name_entry.get().strip():
                    self.pages[name].update_customer_number()
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
        left.columnconfigure(0, minsize=130)
        left.columnconfigure(1, weight=1)
        for i in range(2):
            left.rowconfigure(i, pad=5)
        for i in range(2, 10):
            left.rowconfigure(i, pad=5)

        self.cust_num = get_next_customer_id()
        self.customer_number_label = tk.Label(left, text=f"Customer Number: {self.cust_num}", font=HDR2_TEXT, bg=PRIMARY)
        self.customer_number_label.grid(row=0, column=0, columnspan=2, sticky="w")
        
        tk.Label(left, text="First Name* :", font=TTL_TEXT, bg=PRIMARY).grid(row=1, column=0, sticky="w")
        self.first_name_entry = tk.Entry(left, font=REG_TEXT, highlightthickness=2, highlightcolor=SECONDARY)
        self.first_name_entry.grid(row=1, column=1, sticky="ew", ipady=3)

        tk.Label(left, text="Last Name* :", font=TTL_TEXT, bg=PRIMARY).grid(row=2, column=0, sticky="w")
        self.last_name_entry = tk.Entry(left, font=REG_TEXT, highlightthickness=2, highlightcolor=SECONDARY)
        self.last_name_entry.grid(row=2, column=1, sticky="ew", ipady=3)

        tk.Label(left, text="Address* :", font=TTL_TEXT, bg=PRIMARY).grid(row=3, column=0, sticky="w")
        self.address_entry = tk.Entry(left, font=REG_TEXT, highlightthickness=2, highlightcolor=SECONDARY)
        self.address_entry.grid(row=3, column=1, sticky="ew", ipady=3)

        tk.Label(left, text="Email:", font=TTL_TEXT, bg=PRIMARY).grid(row=4, column=0, sticky="w")
        self.email_entry = tk.Entry(left, font=REG_TEXT, highlightthickness=2, highlightcolor=SECONDARY)
        self.email_entry.grid(row=4, column=1, sticky="ew", ipady=3)

        tk.Label(left, text="Phone* :", font=TTL_TEXT, bg=PRIMARY).grid(row=5, column=0, sticky="w")
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
        self.dynamic_frame.columnconfigure(0, minsize=130)
        self.dynamic_frame.columnconfigure(1, weight=1)
        # unit price display (updated on service selection)
        self.unit_price_var = tk.StringVar()
        unit_price_label = tk.Label(self.dynamic_frame, textvariable=self.unit_price_var, fg=SECONDARY)
        unit_price_label.grid(row=2, column=0, columnspan=2, sticky='w')

        tk.Label(left, text="Additional\nNotes:", font=TTL_TEXT, bg=PRIMARY).grid(row=8, column=0, sticky="nw")
        self.notes_text = tk.Text(left, height=3, width=30, font=REG_TEXT, highlightthickness=2, highlightcolor=SECONDARY)
        self.notes_text.grid(row=8, column=1, sticky="ew", ipady=3)

        add_btn = tk.Button(left, text="Add Item", font=TTL_TEXT, bg=SECONDARY, fg=PRIMARY, command=self.add_item, width=20)
        add_btn.grid(row=9, column=1, pady=10)

        # Lookup existing customer and autofill fields
        lookup_btn = tk.Button(left, text="Lookup Customer", font=TTL_TEXT, bg=ACCENT, fg=SECONDARY, command=self.lookup_customer, width=20)
        lookup_btn.grid(row=10, column=1, pady=(0,10))

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
        columns = ("Service", "Quantity", "Price")
        self.order_tree = ScrollableGridTable(right, columns=columns, include_action=False)
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
        # Only perform an automatic direct lookup by phone when other fields are empty
        if phone and not (self.first_name_entry.get().strip() or self.last_name_entry.get().strip() or self.address_entry.get().strip() or self.email_entry.get().strip()):
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
                        self.update_customer_number(rec.get('CustomerID'))
                        messagebox.showinfo('Found', f"Loaded customer {rec.get('First_Name','')} {rec.get('Last_Name','')}")
                        return
            except Exception:
                pass

        # Otherwise show a selection window with treeview to pick a customer
        sel_win = tk.Toplevel(self)
        sel_win.title('Select Customer')
        sel_win.geometry('1100x550')
        sel_win.configure(bg=PRIMARY)
        sel_win.grab_set()
        sel_win.rowconfigure(1, weight=1); sel_win.columnconfigure(0, weight=1)

        # search row
        top = tk.Frame(sel_win, padx=8, pady=6, bg=PRIMARY)
        top.grid(row=0, column=0, sticky='ew')
        top.columnconfigure((1,3), weight=1)
        tk.Label(top, text='First Name:', font=TTL_TEXT, bg=PRIMARY).grid(row=0, column=0, sticky='w')
        entry_first = tk.Entry(top, font=REG_TEXT)
        entry_first.grid(row=0, column=1, sticky='ew', padx=6)
        tk.Label(top, text='Last Name:', font=TTL_TEXT, bg=PRIMARY).grid(row=0, column=2, sticky='w', padx=(12,6))
        entry_last = tk.Entry(top, font=REG_TEXT)
        entry_last.grid(row=0, column=3, sticky='ew')
        tk.Button(top, text='Search', font=TTL_TEXT, bg=SECONDARY, fg=PRIMARY, command=lambda: populate_filtered()).grid(row=0, column=4, padx=8)

        def check_lookup_empty(event):
            if not entry_first.get().strip() and not entry_last.get().strip():
                populate()
            elif not event.widget.get().strip():
                populate_filtered()

        entry_first.bind('<KeyRelease>', check_lookup_empty)
        entry_last.bind('<KeyRelease>', check_lookup_empty)

        # container for tree
        container = tk.Frame(sel_win, padx=8, pady=6, bg=PRIMARY)
        container.grid(row=1, column=0, sticky='nsew')
        container.rowconfigure(0, weight=1); container.columnconfigure(0, weight=1)

        cols = ('ID','First Name','Last Name','Phone','Email','Address')
        
        def _on_double(iid):
            cid = int(iid)
            import db as _db
            rec = _db.get_customer_details(cid)
            if rec:
                rd = dict(rec)
                self.first_name_entry.delete(0, tk.END); self.first_name_entry.insert(0, rd.get('First_Name',''))
                self.last_name_entry.delete(0, tk.END); self.last_name_entry.insert(0, rd.get('Last_Name',''))
                self.address_entry.delete(0, tk.END); self.address_entry.insert(0, rd.get('Address','') or '')
                self.email_entry.delete(0, tk.END); self.email_entry.insert(0, rd.get('Email','') or '')
                self.phone_entry.delete(0, tk.END); self.phone_entry.insert(0, rd.get('Phone_Number','') or '')
                self.update_customer_number(rd.get('CustomerID'))
                # Inform the user immediately when a customer is selected
                messagebox.showinfo('Found', f"Loaded customer {rd.get('First_Name','')} {rd.get('Last_Name','')}")
            sel_win.destroy()
            
        tree = ScrollableGridTable(container, cols, include_action=False, double_click_callback=_on_double)
        tree.grid(row=0, column=0, sticky='nsew')

        def populate(customers=None):
            tree.clear_all()
            import db as _db
            try:
                rows = customers if customers is not None else _db.get_customers()
            except Exception:
                rows = []
            for r in rows:
                rr = dict(r)
                tag = "evenrow" if len(tree.get_children()) % 2 == 0 else "oddrow"
                vals = (rr.get('First_Name',''), rr.get('Last_Name',''), rr.get('Phone_Number',''), rr.get('Email',''), rr.get('Address',''))
                tree.insert('', 'end', iid=str(rr.get('CustomerID')), text=str(rr.get('CustomerID')), values=vals, tags=(tag,))

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
                cc = dict(c)
                fn = (cc.get('First_Name','') or '').lower()
                ln = (cc.get('Last_Name','') or '').lower()
                if f and f not in fn: continue
                if l and l not in ln: continue
                res.append(c)
            populate(res)

        # _on_double is already defined above and passed to ScrollableGridTable

        def _select():
            sel = tree.selected_iids
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
                self.update_customer_number(rd.get('CustomerID'))
                # Inform the user immediately when a customer is selected
                messagebox.showinfo('Found', f"Loaded customer {rd.get('First_Name','')} {rd.get('Last_Name','')}")
            sel_win.destroy()

        btnf = tk.Frame(sel_win, bg=PRIMARY)
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
            tk.Label(self.dynamic_frame, text="Weight (kg):", font=TTL_TEXT, bg=PRIMARY).grid(row=0, column=0, sticky="w", pady=(8,0))
            self.weight_var = tk.Entry(self.dynamic_frame, font=REG_TEXT, highlightthickness=2, highlightcolor=SECONDARY)
            vcmd_weight = self.dynamic_frame.register(self.validate_weight)
            self.weight_var.config(validate='key', validatecommand=(vcmd_weight, '%P'))
            self.weight_var.grid(row=0, column=1, sticky="ew", ipady=3, pady=(8,0))
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
                tk.Label(self.dynamic_frame, text="Size:", font=TTL_TEXT, bg=PRIMARY).grid(row=0, column=0, sticky="w", pady=(8,0))
                self.size_var = tk.StringVar(value="small")
                rb_frame = tk.Frame(self.dynamic_frame, bg=PRIMARY)
                rb_frame.grid(row=0, column=1, sticky="ew", pady=(8,0))
                tk.Radiobutton(rb_frame, text="Small", font=REG_TEXT, bg=PRIMARY, activebackground=PRIMARY, selectcolor="white", cursor="hand2", variable=self.size_var, value="small").pack(side="left", padx=(0, 15))
                tk.Radiobutton(rb_frame, text="Large", font=REG_TEXT, bg=PRIMARY, activebackground=PRIMARY, selectcolor="white", cursor="hand2", variable=self.size_var, value="large").pack(side="left", padx=15)
                
                # Show quantity entry field
                tk.Label(self.dynamic_frame, text="Quantity:", font=TTL_TEXT, bg=PRIMARY).grid(row=1, column=0, sticky="w", pady=(8,0))
                self.qty_var = tk.Entry(self.dynamic_frame, font=REG_TEXT, highlightthickness=2, highlightcolor=SECONDARY)
                # Register quantity validation - only numbers
                vcmd_qty = self.dynamic_frame.register(self.validate_quantity)
                self.qty_var.config(validate='key', validatecommand=(vcmd_qty, '%P'))
                self.qty_var.grid(row=1, column=1, sticky="ew", ipady=3, pady=(8,0))
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
                tk.Label(self.dynamic_frame, text="Quantity:", font=TTL_TEXT, bg=PRIMARY).grid(row=0, column=0, sticky="w", pady=(8,0))
                self.qty_var = tk.Entry(self.dynamic_frame, font=REG_TEXT, highlightthickness=2, highlightcolor=SECONDARY)
                vcmd_qty = self.dynamic_frame.register(self.validate_quantity)
                self.qty_var.config(validate='key', validatecommand=(vcmd_qty, '%P'))
                self.qty_var.grid(row=0, column=1, sticky="ew", ipady=3, pady=(8,0))
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

    def validate_weight(self, value):
        """Allow only numeric characters (digits) for weight"""
        if value == "":
            return True
        return value.isdigit()

    def validate_customer_info(self):
        from tkinter import messagebox
        first_name = self.first_name_entry.get().strip()
        last_name = self.last_name_entry.get().strip()
        phone = self.phone_entry.get().strip()
        address = self.address_entry.get().strip()
        
        required_errors = []
        if not first_name:
            required_errors.append("First Name")
        if not last_name:
            required_errors.append("Last Name")
        if not address:
            required_errors.append("Address")
        if not phone:
            required_errors.append("Phone")
            
        if required_errors:
            messagebox.showerror("Validation Error", "Please fill in all required fields:\n• " + "\n• ".join(required_errors))
            return False
            
        if not phone.isdigit():
            messagebox.showerror("Validation Error", "Phone number must contain only digits")
            return False
            
        return True

    def update_customer_number(self, cust_id=None):
        import db
        if cust_id is None:
            self.cust_num = db.get_next_customer_id()
        else:
            self.cust_num = cust_id
        self.customer_number_label.config(text=f"Customer Number: {self.cust_num}")

    def open_services_window(self):
        import db
        from tkinter import messagebox
        svc_win = tk.Toplevel(self)
        svc_win.title('Manage Services')
        svc_win.geometry('520x460')
        svc_win.resizable(False, False)
        svc_win.configure(bg=PRIMARY)
        svc_win.grab_set()

        container = tk.Frame(svc_win, padx=16, pady=16, bg=PRIMARY)
        container.pack(fill='both', expand=True)
        container.columnconfigure(0, weight=1)

        # Title
        tk.Label(container, text="Configure Services", font=HDR2_TEXT, bg=PRIMARY, fg=SECONDARY).grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 10))

        # Treeview inside a bordered frame
        tree_border = tk.Frame(container, bg="white", bd=1, relief="solid", highlightbackground=SECONDARY, highlightthickness=1)
        tree_border.grid(row=1, column=0, columnspan=2, sticky='nsew')
        tree_border.columnconfigure(0, weight=1)
        tree_border.rowconfigure(0, weight=1)

        cols = ('Service', 'Price', 'Unit', 'LargePrice')
        tree = ttk.Treeview(tree_border, columns=cols, displaycolumns=('Service', 'Price', 'Unit'), show='headings', style="Fun.Treeview", height=5)
        tree.tag_configure("evenrow", background="#f8f9fa")
        tree.tag_configure("oddrow", background="#ffffff")
        for c in ('Service', 'Price', 'Unit'):
            tree.heading(c, text=c)
            tree.column(c, anchor='w', width=200 if c == 'Service' else 90)
        tree.grid(row=0, column=0, sticky='nsew')

        scrollbar = ttk.Scrollbar(tree_border, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky='ns')

        # Separator
        ttk.Separator(container, orient='horizontal').grid(row=2, column=0, columnspan=2, sticky='ew', pady=10)

        # Form for add/edit
        form = tk.Frame(container, bg=PRIMARY)
        form.grid(row=3, column=0, columnspan=2, sticky='ew')
        form.columnconfigure(1, weight=1)

        tk.Label(form, text='Service Type:', font=TTL_TEXT, bg=PRIMARY).grid(row=0, column=0, sticky='w', pady=3)
        svc_entry = tk.Entry(form, font=REG_TEXT, highlightthickness=2, highlightcolor=SECONDARY)
        svc_entry.grid(row=0, column=1, sticky='ew', pady=3, ipady=2)

        tk.Label(form, text='Unit:', font=TTL_TEXT, bg=PRIMARY).grid(row=1, column=0, sticky='w', pady=3)
        unit_combo = ttk.Combobox(form, values=['pcs', 'kg'], state='readonly', width=8, font=REG_TEXT)
        unit_combo.grid(row=1, column=1, sticky='w', pady=3)

        price_lbl = tk.Label(form, text='Small Price (₱):', font=TTL_TEXT, bg=PRIMARY)
        price_lbl.grid(row=2, column=0, sticky='w', pady=3)
        price_entry = tk.Entry(form, font=REG_TEXT, highlightthickness=2, highlightcolor=SECONDARY)
        price_entry.grid(row=2, column=1, sticky='ew', pady=3, ipady=2)

        large_lbl = tk.Label(form, text='Large Price (₱):', font=TTL_TEXT, bg=PRIMARY)
        large_lbl.grid(row=2, column=0, sticky='w', pady=3)
        large_entry = tk.Entry(form, font=REG_TEXT, highlightthickness=2, highlightcolor=SECONDARY)

        # Track the selected service name for the delete button label
        delete_btn_text = tk.StringVar(value='Delete')

        def on_unit_change(event=None):
            if unit_combo.get() == 'pcs':
                price_lbl.config(text='Small Price (₱):')
                large_lbl.grid(row=3, column=0, sticky='w', pady=3)
                large_entry.grid(row=3, column=1, sticky='ew', pady=3, ipady=2)
            else:
                price_lbl.config(text='Unit Price (₱):')
                large_lbl.grid_forget()
                large_entry.grid_forget()

        unit_combo.bind('<<ComboboxSelected>>', on_unit_change)

        def load_services():
            for i in tree.get_children():
                tree.delete(i)
            for s in db.get_services():
                tag = "evenrow" if len(tree.get_children()) % 2 == 0 else "oddrow"
                lp = s['Large_Unit_Price']
                p = s['Service_Unit_Price']
                if lp is None:
                    lp = p
                tree.insert('', 'end', iid=s['ServiceID'], values=(s['Service_Type'], f"{p}", s['Service_Unit'], f"{lp}"), tags=(tag,))
        load_services()

        def on_select(evt):
            sel = tree.selection()
            if not sel:
                return
            sid = sel[0]
            vals = tree.item(sid, 'values')
            svc_entry.delete(0, tk.END); svc_entry.insert(0, vals[0])
            price_entry.delete(0, tk.END); price_entry.insert(0, vals[1])
            large_entry.delete(0, tk.END); large_entry.insert(0, vals[3])
            try:
                unit_combo.set(vals[2])
            except Exception:
                unit_combo.set('pcs')
            on_unit_change()
            # Update delete button label
            delete_btn_text.set(f'Delete "{vals[0]}"')
        tree.bind('<<TreeviewSelect>>', on_select)

        def clear_form():
            """Clear form fields and deselect treeview."""
            svc_entry.delete(0, tk.END)
            price_entry.delete(0, tk.END)
            large_entry.delete(0, tk.END)
            unit_combo.set('')
            large_lbl.grid_forget()
            large_entry.grid_forget()
            price_lbl.config(text='Small Price (₱):')
            for sel in tree.selection():
                tree.selection_remove(sel)
            delete_btn_text.set('Delete')

        def save():
            name = svc_entry.get().strip()
            price = price_entry.get().strip()
            unit = unit_combo.get() or 'pcs'
            large_price = large_entry.get().strip() if unit == 'pcs' else price
            if not name or not price:
                messagebox.showwarning('Missing', 'Please enter service name and price', parent=svc_win)
                return
            try:
                price_val = int(float(price))
                l_price_val = int(float(large_price)) if large_price else price_val
            except Exception:
                messagebox.showerror('Invalid', 'Price must be a number', parent=svc_win)
                return
            sel = tree.selection()
            if sel:
                db.update_service(int(sel[0]), name, price_val, unit, l_price_val)
            else:
                db.add_service(name, price_val, unit, l_price_val)
            load_services()
            clear_form()
            try:
                reload_services_for_page(self)
            except Exception:
                pass
            messagebox.showinfo('Saved', 'Service saved', parent=svc_win)

        def delete_selected():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning('No Selection', 'Please select a service to delete.', parent=svc_win)
                return
            sid = sel[0]
            svc_name = tree.item(sid, 'values')[0]
            if not messagebox.askyesno('Delete Service', f'Are you sure you want to delete "{svc_name}"?', parent=svc_win):
                return
            db.delete_service(int(sid))
            load_services()
            clear_form()
            try:
                reload_services_for_page(self)
            except Exception:
                pass

        def restore_defaults():
            if messagebox.askyesno('Restore', 'Restore default services and prices?', parent=svc_win):
                db.restore_default_services()
                load_services()
                clear_form()
                try:
                    reload_services_for_page(self)
                except Exception:
                    pass

        # Buttons
        btn_frame = tk.Frame(container, bg=PRIMARY)
        btn_frame.grid(row=4, column=0, columnspan=2, sticky='ew', pady=(12, 0))
        btn_frame.columnconfigure((0, 1, 2, 3), weight=1)

        tk.Button(btn_frame, text='Cancel', font=TTL_TEXT, bg=ACCENT, fg='#333333', relief='flat', cursor='hand2',
                  command=svc_win.destroy).grid(row=0, column=0, sticky='ew', padx=4, ipady=4)
        tk.Button(btn_frame, text='Confirm', font=TTL_TEXT, bg=SECONDARY, fg='white', relief='flat', cursor='hand2',
                  command=save).grid(row=0, column=1, sticky='ew', padx=4, ipady=4)
        delete_btn = tk.Button(btn_frame, textvariable=delete_btn_text, font=TTL_TEXT, bg='#e74c3c', fg='white', relief='flat', cursor='hand2',
                               command=delete_selected)
        delete_btn.grid(row=0, column=2, sticky='ew', padx=4, ipady=4)
        tk.Button(btn_frame, text='Restore Defaults', font=TTL_TEXT, bg='#95a5a6', fg='white', relief='flat', cursor='hand2',
                  command=restore_defaults).grid(row=0, column=3, sticky='ew', padx=4, ipady=4)
        
    def add_item(self):
        from tkinter import messagebox
        
        if not self.validate_customer_info():
            return
            
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
        tag = "evenrow" if len(self.order_tree.get_children()) % 2 == 0 else "oddrow"
        self.order_tree.insert("", "end", text=service, values=(quantity, f"₱ {price:.2f}", item_notes), tags=(tag,))
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
        
        if not self.validate_customer_info():
            return
            
        first_name = self.first_name_entry.get().strip()
        last_name = self.last_name_entry.get().strip()
        phone = self.phone_entry.get().strip()
        address = self.address_entry.get().strip()
        email = self.email_entry.get().strip()
        notes = self.notes_text.get("1.0", "end-1c").strip()
        
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
            
            self.update_customer_number()
            
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
        main_frame = tk.Frame(self, bd=0, relief="solid", bg=PRIMARY)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        # reserve notebook row for content
        main_frame.rowconfigure(3, weight=1)
        main_frame.columnconfigure(0, weight=1)

        # Top section with title and buttons
        top_frame = tk.Frame(main_frame, bg=PRIMARY)
        top_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=10)
        top_frame.columnconfigure(0, weight=1)

        self.subheading_label = tk.Label(top_frame, text="View Orders", font=("Arial", 12, "bold"), bg=PRIMARY)
        self.subheading_label.grid(row=0, column=0, sticky="w")
        self.order_sort_desc = True
        self.order_sort_field = 'Order_Received_At'

        # Action buttons on right
        button_frame = tk.Frame(top_frame, bg=PRIMARY)
        button_frame.grid(row=0, column=1, sticky="e", padx=5, pady=5)
        
        # Gear Button to the left side
        tk.Button(
            button_frame, 
            text="⚙", 
            font=TTL_TEXT, 
            bg=SECONDARY, 
            fg=PRIMARY, 
            command=self.open_overdue_config_window, 
            width=3,  # Compact square width for the icon
            height=1
        ).pack(side="left", padx=5)

        #Process Payment button placed next to it
        tk.Button(
            button_frame, 
            text="Process Payment", 
            font=TTL_TEXT, 
            bg=SECONDARY, 
            fg=PRIMARY, 
            command=self.open_payment_window, 
            width=15, 
            height=1
        ).pack(side="left", padx=5)

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
        filter_frame.columnconfigure(8, weight=0)
        filter_frame.columnconfigure(9, weight=1)

        tk.Label(filter_frame, text="Search ID:", font=TTL_TEXT, bg=PRIMARY).grid(row=0, column=0, padx=5, sticky='w')
        self.search_entry = tk.Entry(filter_frame, width=15, font=REG_TEXT, highlightthickness=2, highlightcolor=SECONDARY)
        self.search_entry.grid(row=0, column=1, padx=5, ipady=2, sticky='w')

        search_btn = tk.Button(filter_frame, text="Search", font=TTL_TEXT, bg=SECONDARY, fg=PRIMARY, command=self.search_orders, width=8)
        search_btn.grid(row=0, column=2, padx=(5,15), sticky='w')

        tk.Label(filter_frame, text="Date From:", font=TTL_TEXT, bg=PRIMARY).grid(row=0, column=3, padx=(0,5), sticky='w')
        self.date_from = tk.Entry(filter_frame, font=REG_TEXT, highlightthickness=2, highlightcolor=SECONDARY, width=12)
        self.date_from.insert(0, "mm/dd/yyyy")
        self.date_from.grid(row=0, column=4, padx=(5,10), ipady=2, sticky='w')

        tk.Label(filter_frame, text="To:", font=TTL_TEXT, bg=PRIMARY).grid(row=0, column=5, padx=5, sticky='w')
        self.date_to = tk.Entry(filter_frame, font=REG_TEXT, highlightthickness=2, highlightcolor=SECONDARY, width=12)
        self.date_to.insert(0, "mm/dd/yyyy")
        self.date_to.grid(row=0, column=6, padx=(5,12), ipady=2, sticky='w')


        # Quick-fill helper functions
        def _fill_today():
            from datetime import date
            s = date.today().strftime('%m/%d/%Y')
            self.date_from.delete(0, tk.END)
            self.date_to.delete(0, tk.END)
            self.date_from.insert(0, s)
            self.date_to.insert(0, s)
        def _fill_week():
            from datetime import date, timedelta
            today = date.today()
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
            self.date_from.delete(0, tk.END)
            self.date_to.delete(0, tk.END)
            self.date_from.insert(0, start.strftime('%m/%d/%Y'))
            self.date_to.insert(0, end.strftime('%m/%d/%Y'))
        def _fill_month():
            from datetime import date
            import calendar
            today = date.today()
            start = today.replace(day=1)
            last_day = calendar.monthrange(today.year, today.month)[1]
            end = today.replace(day=last_day)
            self.date_from.delete(0, tk.END)
            self.date_to.delete(0, tk.END)
            self.date_from.insert(0, start.strftime('%m/%d/%Y'))
            self.date_to.insert(0, end.strftime('%m/%d/%Y'))
        def _clear_dates():
            self.date_from.delete(0, tk.END)
            self.date_to.delete(0, tk.END)
            self.date_from.insert(0, 'mm/dd/yyyy')
            self.date_to.insert(0, 'mm/dd/yyyy')

        # Quick-fill buttons sit on the same row as the date search controls
        date_btn_frame = tk.Frame(filter_frame, bg=PRIMARY)
        date_btn_frame.grid(row=0, column=7, padx=(10, 0), sticky='w')
        btn_today = tk.Button(date_btn_frame, text='Today', font=TTL_TEXT, bg=ACCENT, fg=SECONDARY, width=8, command=_fill_today)
        btn_today.pack(side='left', padx=2)
        btn_week = tk.Button(date_btn_frame, text='This Week', font=TTL_TEXT, bg=ACCENT, fg=SECONDARY, width=10, command=_fill_week)
        btn_week.pack(side='left', padx=2)
        btn_month = tk.Button(date_btn_frame, text='This Month', font=TTL_TEXT, bg=ACCENT, fg=SECONDARY, width=10, command=_fill_month)
        btn_month.pack(side='left', padx=2)
        btn_clear = tk.Button(date_btn_frame, text='Clear', font=TTL_TEXT, bg=PRIMARY, fg=SECONDARY, width=6, command=_clear_dates)
        btn_clear.pack(side='left', padx=2)

        search_btn_inline = tk.Button(filter_frame, text='Search by Date', font=TTL_TEXT, bg=SECONDARY, fg=PRIMARY, width=14, command=self.search_by_date)
        search_btn_inline.grid(row=0, column=8, padx=6, sticky='w')
        
        # make space to the right so layout doesn't look cramped
        filter_frame.columnconfigure(9, weight=1)

        # keep legacy variable name for compatibility
        search_date_btn = search_btn_inline

        def check_orders_search_empty(event):
            if not self.search_entry.get().strip():
                self.refresh_all()
        self.search_entry.bind('<KeyRelease>', check_orders_search_empty)

        # Notebook tabs for Unpaid / Paid / Archived
        style = ttk.Style()
        try:
            style.configure('TNotebook', background=PRIMARY, borderwidth=0)
            style.configure('TNotebook.Tab', font=("Arial", 12, "bold"), padding=[20, 10], relief="flat", borderwidth=2, background="#f0f0f0", foreground="black")
            style.map("TNotebook.Tab", background=[("selected", "white")], foreground=[("selected", SECONDARY)])
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
            
            tree = ScrollableGridTable(parent, cols, include_action=include_action, edit_callback=self.open_edit_window, delete_callback=self.confirm_delete_order)
            tree.pack(fill='both', expand=True)
            return tree

        self.unpaid_tree = make_tree(self.unpaid_frame, include_action=True)
        self.paid_tree = make_tree(self.paid_frame, include_action=True)
        self.archived_tree = make_tree(self.archived_frame, include_action=False)

        # Legend/Filter at bottom (moved below the notebook)
        legend_frame = tk.Frame(main_frame, bg=PRIMARY)
        legend_frame.grid(row=4, column=0, sticky="ew", padx=15, pady=10)
        legend_frame.columnconfigure(0, weight=0)
        legend_frame.columnconfigure(1, weight=1)
        legend_frame.columnconfigure(2, weight=0)

        legend_label = tk.Label(legend_frame, text="Filter By Status:", font=TTL_TEXT, bg=PRIMARY)
        legend_label.grid(row=0, column=0, sticky='w', padx=5)
        
        status_button_frame = tk.Frame(legend_frame, bg=PRIMARY)
        status_button_frame.grid(row=0, column=1, sticky='w', padx=(10,0))
        for status in ["All", "Received", "In-Progress", "Ready", "Released"]:
            tk.Button(status_button_frame, text=status, font=TTL_TEXT, bg=PRIMARY, fg=SECONDARY, width=12, command=lambda s=status: self.sort_by_status(s)).pack(side="left", padx=3)

        sort_frame = tk.Frame(legend_frame, bg=PRIMARY)
        sort_frame.grid(row=0, column=2, sticky='e')
        self.order_sort_label = tk.Label(sort_frame, text='Sorting by received date:', font=TTL_TEXT, bg=PRIMARY)
        self.order_sort_label.grid(row=0, column=0, sticky='e', padx=13)
        self.order_sort_newest_btn = tk.Button(sort_frame, text='Newest first', font=TTL_TEXT, bg=ACCENT, fg=SECONDARY, activebackground=ACCENT, activeforeground=SECONDARY, relief='raised', bd=1, command=lambda: self.set_order_sort(True), width=12)
        self.order_sort_newest_btn.grid(row=0, column=1, padx=(0, 4))
        self.order_sort_oldest_btn = tk.Button(sort_frame, text='Oldest first', font=TTL_TEXT, bg=ACCENT, fg=SECONDARY, activebackground=ACCENT, activeforeground=SECONDARY, relief='raised', bd=1, command=lambda: self.set_order_sort(False), width=12)
        self.order_sort_oldest_btn.grid(row=0, column=2, padx=(0, 12))

        # Initialize visual sort state so the buttons reflect the current mode from startup
        self.set_order_sort(self.order_sort_desc, refresh=False)

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

    def sort_orders(self, orders):
        from datetime import datetime
        def parse_date(value):
            if not value:
                return datetime.min
            if isinstance(value, str):
                for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%m/%d/%Y', '%m/%d/%Y %H:%M:%S'):
                    try:
                        return datetime.strptime(value, fmt)
                    except Exception:
                        continue
            return datetime.min

        def get_field_value(order, field):
            if hasattr(order, 'get'):
                return order.get(field)
            try:
                return order[field]
            except Exception:
                return None

        try:
            return sorted(orders, key=lambda o: parse_date(get_field_value(o, self.order_sort_field)), reverse=self.order_sort_desc)
        except Exception:
            return list(orders)

    def set_order_sort(self, newest_first, refresh=True):
        self.order_sort_desc = bool(newest_first)
        

        if self.order_sort_desc:
            self.order_sort_newest_btn.config(bg=SECONDARY, fg='white', activebackground=SECONDARY, activeforeground='white', relief='sunken', bd=2)
            self.order_sort_oldest_btn.config(bg=ACCENT, fg=SECONDARY, activebackground=ACCENT, activeforeground=SECONDARY, relief='raised', bd=1)
            self.order_sort_label.config(text='Sorting by received date:')
        else:
            self.order_sort_newest_btn.config(bg=ACCENT, fg=SECONDARY, activebackground=ACCENT, activeforeground=SECONDARY, relief='raised', bd=1)
            self.order_sort_oldest_btn.config(bg=SECONDARY, fg='white', activebackground=SECONDARY, activeforeground='white', relief='sunken', bd=2)
            self.order_sort_label.config(text='Sorting by received date:')
        if refresh:
            self.refresh_all()

    # --- Action overlays (REMOVED: Now handled by CustomGridTable directly) ---
    def _clear_action_overlays(self, tree=None):
        pass

    def _order_id_from_iid(self, iid):
        """Extract numeric order_id from an iid that may be '42', '42-1', or '42-total'."""
        try:
            return int(str(iid).split('-')[0])
        except Exception:
            return None

    def confirm_delete_order(self, iid):
        import db
        from tkinter import messagebox
        is_child = '-' in str(iid)
        if is_child:
            try:
                oid = int(str(iid).split('-')[0])
            except Exception:
                return
            if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete this service line from Order {oid}?"):
                try:
                    success, parent_deleted = db.delete_service_row(iid)
                    if parent_deleted:
                        messagebox.showinfo("Deleted", f"Service line deleted. The entire Order {oid} has been deleted since no services remain.")
                    else:
                        messagebox.showinfo("Deleted", f"Service line deleted from Order {oid}.")
                    self.refresh_all()
                except Exception as e:
                    messagebox.showerror("Error", str(e))
        else:
            try:
                oid = int(iid)
            except Exception:
                return
            if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete Order {oid}?\nThis will permanently delete the order and all its items."):
                try:
                    db.delete_order(oid)
                    messagebox.showinfo("Deleted", f"Order {oid} has been deleted.")
                    self.refresh_all()
                except Exception as e:
                    messagebox.showerror("Error", str(e))

    def _create_action_overlays(self, tree):
        pass

    def _reposition_action_overlays(self, event=None):
        pass

    def _insert_order_rows(self, tree, order, include_action=True):
        import db
        
        # Pull details safely out of row dictionary records
        oid = order['OrderID']
        raw_date_str = order['Order_Received_At']
        
        # --- HERE IS THE FIX: FORMAT THE DISPLAY DATE ---
        date_str = format_db_date(raw_date_str)
        
        customer = f"{order['First_Name']} {order['Last_Name']}"
        status = order['Order_Status']
        total = order['Order_Total_Price']
        paid = "Yes" if order['Order_Paid_At'] else "No"

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
            tag = "evenrow" if len(tree.get_children()) % 2 == 0 else "oddrow"
            tree.insert('', 'end', iid=parent_iid, text=str(oid), values=tuple(vals), tags=(tag,))
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
            tag = "evenrow" if len(tree.get_children()) % 2 == 0 else "oddrow"
            tree.insert('', 'end', iid=parent_iid, text=str(oid), values=tuple(vals), tags=(tag,))
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
                
            tag = "evenrow" if len(tree.get_children()) % 2 == 0 else "oddrow"
            tree.insert('', 'end', iid=parent_iid, text=str(oid), values=tuple(parent_vals), tags=(tag, 'parent_mixed'))
            
            # Populate underlying layout item details inside the folder dropdown rows
            for srow in svc_rows:
                child_iid = srow['order_detail_id']
                child_vals = [
                    "", # Intentionally blank to keep alignment clean under parent timestamp
                    "",
                    srow['service_name'],
                    srow['qty_display'],
                    srow['status'],
                    f"₱{srow['subtotal']}",
                    srow['paid'],
                ]
                if include_action:
                    child_vals.append('')
                tree.insert(parent_iid, 'end', iid=child_iid, text=child_iid, values=tuple(child_vals), tags=('child_service',))
                
    def refresh_unpaid(self):
        import db
        tree = self.unpaid_tree
        tree.clear_all()
        try:
            orders = self.sort_orders(db.get_unpaid_orders())
            for order in orders:
                self._insert_order_rows(tree, order, include_action=True)
        except Exception as e:
            print(f"Error loading unpaid orders: {e}")

    def refresh_paid(self):
        import db
        tree = self.paid_tree
        tree.clear_all()
        try:
            orders = self.sort_orders(db.get_paid_orders())
            for order in orders:
                self._insert_order_rows(tree, order, include_action=True)
        except Exception as e:
            print(f"Error loading paid orders: {e}")

    def refresh_archived(self):
        import db
        tree = self.archived_tree
        tree.clear_all()
        try:
            orders = self.sort_orders(db.get_archived_orders())
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
            orders = self.sort_orders(db.get_unpaid_orders())
            tree = self.unpaid_tree
        elif idx == 1:
            orders = self.sort_orders(db.get_paid_orders())
            tree = self.paid_tree
        else:
            orders = self.sort_orders(db.get_archived_orders())
            tree = self.archived_tree

        tree.clear_all()

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

            # 1. Match by parent OrderID (strict: must be exact integer match)
            if str(oid) == term:
                order_matched = True

            # 2. Match by customer name
            if term.lower() in customer_name.lower():
                order_matched = True

            # 3. Match by child service ID (exact: e.g. "1-2") or by parent ID prefix (e.g. "1" matches "1-1", "1-2")
            for srow in svc_rows:
                child_iid = srow['order_detail_id']
                # Exact child ID match (e.g. search "1-2") OR parent ID search (e.g. search "1" matches "1-N")
                if term == child_iid or (term == str(oid)):
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
                orders = self.sort_orders(db.get_unpaid_orders_by_date(start_iso, end_iso))
                tree = self.unpaid_tree
            elif idx == 1:
                orders = self.sort_orders(db.get_paid_orders_by_date(start_iso, end_iso))
                tree = self.paid_tree
            else:
                orders = self.sort_orders(db.get_archived_orders_by_date(start_iso, end_iso))
                tree = self.archived_tree
        except Exception as e:
            messagebox.showerror('Date Search', f'Database error: {e}')
            return
        tree.clear_all()
        include_action = (idx in (0, 1))
        for order in orders:
            self._insert_order_rows(tree, order, include_action=include_action)

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

        tree.clear_all()

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
            orders = self.sort_orders(orders)
            include_action = (idx in (0, 1))
            for order in orders:
                self._insert_order_rows(tree, order, include_action=include_action)
        except Exception as e:
            print(f"Error sorting orders: {e}")
            
    def open_overdue_config_window(self):
        """Opens a top-level modal window to change the active overdue threshold configuration."""
        import db
        
        config_win = tk.Toplevel(self)
        config_win.title("Overdue Rules Config")
        config_win.geometry("340x180")
        config_win.configure(bg=PRIMARY)
        config_win.grab_set()  # Lock window focus
        config_win.resizable(False, False)
        
        # Center modal window relative to display screen
        config_win.update_idletasks()
        w, h = config_win.winfo_width(), config_win.winfo_height()
        x = (config_win.winfo_screenwidth() // 2) - (w // 2)
        y = (config_win.winfo_screenheight() // 2) - (h // 2)
        config_win.geometry(f'{w}x{h}+{x}+{y}')
        
        tk.Label(
            config_win, 
            text="Set Days Before 'Ready' Order is Overdue:", 
            font=TTL_TEXT, 
            bg=PRIMARY, 
            fg=SECONDARY
        ).pack(pady=(25, 10))
        
        # Form field capturing threshold integer entry bound to backend variable
        days_var = tk.StringVar(value=str(db.OrderConfig.OVERDUE_DAYS))
        days_entry = tk.Entry(config_win, textvariable=days_var, font=REG_TEXT, justify="center", width=12)
        days_entry.pack(pady=5)
        days_entry.focus()
        
        def save_config_action():
            try:
                val = int(days_var.get().strip())
                if val < 0:
                    raise ValueError
                
                # Permanently save the configuration value to config.txt instead of changing DB tables
                db.update_overdue_days_config(val)
                
                config_win.destroy()
                self.refresh_all()  # Instantly update current view table rows
                
                # Force the ReportsPage to dynamically rebuild the donut chart right now
                if hasattr(self, 'controller') and "ReportsPage" in self.controller.pages:
                    self.controller.pages["ReportsPage"].show_report("overdue")
                elif hasattr(self.master, 'pages') and "ReportsPage" in self.master.pages:
                    self.master.pages["ReportsPage"].show_report("overdue")
                    
            except ValueError:
                from tkinter import messagebox
                messagebox.showerror("Validation Error", "Please enter a valid positive integer number of days.")

        tk.Button(
            config_win, 
            text="Save Settings", 
            font=TTL_TEXT, 
            bg=SECONDARY, 
            fg=PRIMARY, 
            command=save_config_action
        ).pack(pady=15)

    def open_payment_window(self):
        
        import db
        from tkinter import messagebox

        payment_win = tk.Toplevel(self)
        payment_win.title("Process Payment")
        payment_win.geometry("520x450")
        payment_win.configure(bg=PRIMARY)
        payment_win.resizable(False, False)
        payment_win.grab_set()

        container = tk.Frame(payment_win, bd=2, relief="solid", bg=PRIMARY)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        header = tk.Frame(container, bg=SECONDARY, height=60)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="Process Payment", font=HDR_TEXT, bg=SECONDARY, fg=PRIMARY).pack(pady=10)

        form_frame = tk.Frame(container, bg=PRIMARY)
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
        order_entry = tk.Entry(form_frame, textvariable=order_entry_var, width=30, font=REG_TEXT, highlightthickness=1, highlightbackground=ACCENT, highlightcolor=SECONDARY)
        order_entry.grid(row=0, column=1, sticky="ew", pady=12, padx=10)

        tk.Label(form_frame, text="Order ID / Customer:", font=TTL_TEXT, bg=PRIMARY, fg=SECONDARY).grid(row=0, column=0, sticky="w", pady=12)

        def _choose_from_matches_payment(matches):
            pick_win = tk.Toplevel(payment_win)
            pick_win.title('Select Order')
            pick_win.geometry('400x300')
            pick_win.configure(bg=PRIMARY)
            
            lb = tk.Listbox(pick_win, font=REG_TEXT, selectbackground=SECONDARY, selectforeground=PRIMARY)
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
                # update amount display from unpaid child subtotal
                try:
                    due_amount = db.get_order_amount_due(int(oid))
                    amount_due_display.config(text=f"₱{due_amount:.2f}")
                except:
                    pass
                pick_win.destroy()
                
            btnf = tk.Button(pick_win, text='Select', font=TTL_TEXT, bg=SECONDARY, fg=PRIMARY, command=_select, cursor="hand2")
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
                    svc_rows = db.get_order_service_rows(oid_clean)
                    target_svc = next((sr for sr in svc_rows if sr['order_detail_id'] == q), None)
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
                due_amount = db.get_order_amount_due(int(q))
                amount_due_display.config(text=f"₱{due_amount:.2f}")
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
                due_amount = db.get_order_amount_due(int(matches[0][0]))
                amount_due_display.config(text=f"₱{due_amount:.2f}")
                return
            _choose_from_matches_payment(matches)

        # Set initial amount due if pre-populated
        initial_amount = "0.00"
        if selected_order_id:
            try:
                oid_clean = selected_order_id.split('-')[0]
                if '-' in selected_order_id:
                    svc_rows = db.get_order_service_rows(int(oid_clean))
                    target_svc = next((sr for sr in svc_rows if sr['order_detail_id'] == selected_order_id), None)
                    if target_svc:
                        initial_amount = f"₱{target_svc['subtotal']:.2f}"
                else:
                    o = db.get_order_details(int(oid_clean))
                    if o:
                        due_amount = db.get_order_amount_due(int(oid_clean))
                        initial_amount = f"₱{due_amount:.2f}"
            except Exception:
                pass

        amount_due_display = tk.Label(form_frame, text=initial_amount, font=HDR2_TEXT, bg=PRIMARY, fg=SECONDARY, relief="sunken", width=35, bd=1)
        amount_due_display.grid(row=1, column=1, sticky="ew", pady=12, padx=10)
        tk.Label(form_frame, text="Amount Due (₱):", font=TTL_TEXT, bg=PRIMARY, fg=SECONDARY).grid(row=1, column=0, sticky="w", pady=12)

        cash_entry = tk.Entry(form_frame, width=37, font=REG_TEXT, bd=1, relief="solid", highlightthickness=1, highlightbackground=ACCENT, highlightcolor=SECONDARY)
        cash_entry.grid(row=2, column=1, sticky="ew", pady=12, padx=10)
        tk.Label(form_frame, text="Cash Received (₱):", font=TTL_TEXT, bg=PRIMARY, fg=SECONDARY).grid(row=2, column=0, sticky="w", pady=12)

        change_var = tk.StringVar(value="₱0.00")
        change_display = tk.Label(form_frame, textvariable=change_var, font=("Arial", 16, "bold"), bg=PRIMARY, fg="#27ae60") 
        change_display.grid(row=3, column=1, sticky="w", pady=12, padx=10)
        tk.Label(form_frame, text="Change (₱):", font=TTL_TEXT, bg=PRIMARY, fg=SECONDARY).grid(row=3, column=0, sticky="w", pady=12)

        def calculate_change(event=None):
            try:
                # Strip out the peso sign and commas to get the raw float
                due_str = amount_due_display.cget("text").replace("₱", "").replace(",", "").strip()
                due = float(due_str) if due_str else 0.0
                
                cash_str = cash_entry.get().strip()
                cash = float(cash_str) if cash_str else 0.0
                
                # If they empty the box, reset
                if cash_str == "":
                    change_var.set("₱0.00")
                    change_display.config(fg="#27ae60")
                    return

                change = cash - due
                if change >= 0:
                    change_var.set(f"₱{change:,.2f}")
                    change_display.config(fg="#27ae60") # Green for good to go
                else:
                    change_var.set("Insufficient")
                    change_display.config(fg="#e74c3c") # Red for not enough cash
            except ValueError:
                change_var.set("₱0.00")

        # Bind the calculation to happen every time a key is released in the cash entry box
        cash_entry.bind("<KeyRelease>", calculate_change)

        def process_payment():
            order_id = order_entry_var.get().strip()
            cash_str = cash_entry.get().strip()
            if not order_id or not cash_str:
                messagebox.showwarning("Error", "Please select an order and enter cash amount", parent=payment_win)
                return
            try:
                cash = float(cash_str)
                if '-' in order_id:
                    result = db.process_service_payment(order_id, cash)
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

        btn_frame = tk.Frame(container, bg=PRIMARY)
        btn_frame.pack(fill="x", padx=30, pady=20)
        btn_frame.columnconfigure((0, 1), weight=1)
        
        tk.Button(btn_frame, text="Process Payment", command=process_payment, font=TTL_TEXT, bg=SECONDARY, fg=PRIMARY, height=2, cursor="hand2", bd=1, relief="raised").grid(row=0, column=0, sticky="ew", padx=5)
        tk.Button(btn_frame, text="Cancel", command=payment_win.destroy, font=REG_TEXT, bg=ACCENT, fg=SECONDARY, height=2, cursor="hand2", bd=1, relief="raised").grid(row=0, column=1, sticky="ew", padx=5)

    def on_tree_motion(self, event):
        pass

    def on_tree_click(self, event):
        pass

    #FOR VIEW ORDER PAGE
    def open_edit_window(self, target_id):
        import db
        from tkinter import messagebox
        import sqlite3

        # Parse target ID
        is_child = '-' in str(target_id)
        if is_child:
            oid = int(str(target_id).split('-')[0])
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

        # Retrieve the service row we are editing
        svc_rows = db.get_order_service_rows(oid)
        if is_child:
            target_svc = next((sr for sr in svc_rows if sr['order_detail_id'] == target_id), None)
        else:
            target_svc = svc_rows[0] if svc_rows else None

        if not target_svc:
            messagebox.showerror("Not found", "Service details not found")
            return

        edit_win = tk.Toplevel(self)
        edit_win.title(f"Edit Order {target_id}" if not is_child else f"Edit Service {target_id}")
        edit_win.geometry("500x450")
        edit_win.resizable(False, False)
        edit_win.grab_set()

        form = tk.Frame(edit_win, padx=20, pady=20, bg=PRIMARY)
        form.pack(fill='both', expand=True)
        form.columnconfigure(1, weight=1)

        # Helper to parse number from Qty/Wt string
        def parse_qty_value(raw_str):
            s = raw_str.strip().lower()
            m = re.search(r"([0-9]+(?:\.[0-9]+)?)", s)
            if m:
                return float(m.group(1))
            return 0.0

        # Calculate unit price
        unit_price = 0.0
        try:
            qty_val = parse_qty_value(target_svc['qty_display'])
            if qty_val > 0:
                unit_price = target_svc['subtotal'] / qty_val
        except Exception:
            pass
        
        if unit_price == 0.0:
            try:
                with sqlite3.connect("Laundrify.db") as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT Service_Unit_Price FROM SERVICES WHERE Service_Type = ?", (target_svc['service_name'],))
                    srow = cur.fetchone()
                    if srow:
                        unit_price = float(srow[0])
            except Exception:
                pass

        # Header Labels (pre-established font style)
        title_lbl = tk.Label(form, text=f"Order {oid}'s {target_svc['service_name']} Service", font=("Cooper Black", 14), bg=PRIMARY, fg=SECONDARY, anchor='w')
        title_lbl.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 2))
        
        cust_lbl = tk.Label(form, text=f"From {order['First_Name']} {order['Last_Name']}", font=("Arial", 11, "bold"), bg=PRIMARY, fg="#555555", anchor='w')
        cust_lbl.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(0, 20))

        # Qty/Wt:
        tk.Label(form, text="Qty/Wt:", font=TTL_TEXT, bg=PRIMARY).grid(row=2, column=0, sticky='w', pady=8)
        qty_entry = tk.Entry(form, font=REG_TEXT, highlightthickness=1, highlightcolor=SECONDARY)
        qty_entry.grid(row=2, column=1, sticky='ew', pady=8, ipady=3)
        qty_entry.insert(0, str(target_svc['qty_display']))

        # Subtotal (P):
        tk.Label(form, text="Subtotal (P):", font=TTL_TEXT, bg=PRIMARY).grid(row=3, column=0, sticky='w', pady=8)
        subtotal_entry = tk.Entry(form, font=REG_TEXT, highlightthickness=1, highlightcolor=SECONDARY)
        subtotal_entry.grid(row=3, column=1, sticky='ew', pady=8, ipady=3)
        
        def set_subtotal_display(val):
            subtotal_entry.config(state='normal')
            subtotal_entry.delete(0, tk.END)
            subtotal_entry.insert(0, f"{val:.2f}")
            subtotal_entry.config(state='readonly')
            
        set_subtotal_display(target_svc['subtotal'])

        # Recalculate subtotal on key release in Qty/Wt entry
        def recalculate_price(event=None):
            try:
                qty_val = parse_qty_value(qty_entry.get())
                new_subtotal = qty_val * unit_price
                set_subtotal_display(new_subtotal)
            except Exception:
                pass

        qty_entry.bind('<KeyRelease>', recalculate_price)

        # Status:
        tk.Label(form, text="Status:", font=TTL_TEXT, bg=PRIMARY).grid(row=4, column=0, sticky='w', pady=8)
        status_combo = ttk.Combobox(form, values=["Received","In-Progress","Ready","Released"], state='readonly', font=REG_TEXT)
        status_combo.grid(row=4, column=1, sticky='ew', pady=8, ipady=3)
        status_combo.set(target_svc['status'])

        # Paid:
        tk.Label(form, text="Paid:", font=TTL_TEXT, bg=PRIMARY).grid(row=5, column=0, sticky='w', pady=8)
        paid_combo = ttk.Combobox(form, values=["Yes", "No"], state='readonly', font=REG_TEXT)
        paid_combo.grid(row=5, column=1, sticky='ew', pady=8, ipady=3)
        paid_combo.set(target_svc['paid'])

        # Notes:
        tk.Label(form, text="Notes:", font=TTL_TEXT, bg=PRIMARY).grid(row=6, column=0, sticky='nw', pady=8)
        notes_text = tk.Text(form, height=4, width=30, font=REG_TEXT, highlightthickness=1, highlightcolor=SECONDARY)
        notes_text.grid(row=6, column=1, sticky='ew', pady=8)
        notes_text.insert('1.0', target_svc.get('notes','') or '')

        def save_changes():
            try:
                qty_val = qty_entry.get().strip()
                subtotal = float(subtotal_entry.get().strip())
                status = status_combo.get()
                paid_val = paid_combo.get() == "Yes"
                notes = notes_text.get("1.0", "end-1c").strip()
                db.update_service_details(target_svc['order_detail_id'], qty_val, subtotal, status, paid_val, notes)
                messagebox.showinfo('Saved', 'Service details updated')
                edit_win.destroy()
                self.refresh_all()
            except ValueError:
                messagebox.showerror('Error', 'Subtotal must be a valid number')
            except Exception as e:
                messagebox.showerror('Error', str(e))

        # Bottom Button Frame (Cancel, Confirm) side-by-side
        btn_frame = tk.Frame(form, bg=PRIMARY)
        btn_frame.grid(row=7, column=0, columnspan=2, pady=(20, 10), sticky='ew')
        btn_frame.columnconfigure((0, 1), weight=1)
        
        tk.Button(btn_frame, text='Cancel', command=edit_win.destroy, font=TTL_TEXT, bg=ACCENT, fg=SECONDARY, height=2, cursor="hand2").grid(row=0, column=0, sticky='ew', padx=5)
        tk.Button(btn_frame, text='Confirm', command=save_changes, font=TTL_TEXT, bg=SECONDARY, fg=PRIMARY, height=2, cursor="hand2").grid(row=0, column=1, sticky='ew', padx=5)

class CustomersPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.configure(bg=SECONDARY)
        self.controller = controller
        self.action_overlays = {}

        main_frame = tk.Frame(self, bd=0, relief="solid", bg=PRIMARY)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)

        # Header and count
        header_frame = tk.Frame(main_frame, bg=PRIMARY)
        header_frame.grid(row=0, column=0, sticky='ew', padx=12, pady=(8,4))
        header_frame.columnconfigure(0, weight=1)
        tk.Label(header_frame, text='There are {0} Customer Records'.format('0'), font=TTL_TEXT, bg=PRIMARY).grid(row=0, column=0, sticky='w')
        self.count_label = header_frame.grid_slaves(row=0, column=0)[0]
        self.customer_sort_key = 'id'
        self.customer_sort_desc = False

        # Search area
        search_frame = tk.Frame(main_frame, bg=PRIMARY)
        search_frame.grid(row=1, column=0, sticky='ew', padx=12, pady=6)
        # left: ID search
        tk.Label(search_frame, text='Search ID:', font=TTL_TEXT, bg=PRIMARY).grid(row=0, column=0, sticky='w')
        self.search_id_entry = tk.Entry(search_frame, width=12, font=REG_TEXT, highlightthickness=2, highlightcolor=SECONDARY)
        self.search_id_entry.grid(row=0, column=1, padx=6, ipady=3)
        tk.Button(search_frame, text='Search by ID', font=TTL_TEXT, bg=SECONDARY, fg=PRIMARY, command=self.search_by_id).grid(row=0, column=2, padx=6)

        # right: name search
        tk.Label(search_frame, text='First Name:', font=TTL_TEXT, bg=PRIMARY).grid(row=0, column=3, padx=(30,6))
        self.search_first = tk.Entry(search_frame, width=15, font=REG_TEXT, highlightthickness=2, highlightcolor=SECONDARY)
        self.search_first.grid(row=0, column=4, ipady=3)
        tk.Label(search_frame, text='Last Name:', font=TTL_TEXT, bg=PRIMARY).grid(row=0, column=5, padx=(12,6))
        self.search_last = tk.Entry(search_frame, width=15, font=REG_TEXT, highlightthickness=2, highlightcolor=SECONDARY)
        self.search_last.grid(row=0, column=6, ipady=3)
        tk.Button(search_frame, text='Search by Name', font=TTL_TEXT, bg=SECONDARY, fg=PRIMARY, command=self.search_by_name).grid(row=0, column=7, padx=8)

        def check_id_empty(event):
            if not self.search_id_entry.get().strip():
                self.refresh_customers()

        def check_names_empty(event):
            if not self.search_first.get().strip() and not self.search_last.get().strip():
                self.refresh_customers()

        self.search_id_entry.bind('<KeyRelease>', check_id_empty)
        self.search_first.bind('<KeyRelease>', check_names_empty)
        self.search_last.bind('<KeyRelease>', check_names_empty)

        sep = ttk.Separator(main_frame, orient='horizontal')
        sep.grid(row=2, column=0, sticky='ew', padx=8, pady=(4,8))

        # Table area
        table_frame = tk.Frame(main_frame, bg=PRIMARY)
        table_frame.grid(row=3, column=0, sticky="nsew", padx=12, pady=6)
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        cols = ("ID", "First Name", "Last Name", "Phone", "Email", "Address", "Action")
        self.customer_tree = ScrollableGridTable(table_frame, cols, include_action=True, edit_callback=self.open_edit_window, delete_callback=None)
        self.customer_tree.grid(row=0, column=0, sticky='nsew')

        # Sort buttons at bottom
        sort_frame = tk.Frame(main_frame, bg=PRIMARY)
        sort_frame.grid(row=4, column=0, sticky='ew', padx=12, pady=(8,6))
        sort_frame.columnconfigure(0, weight=1)
        sort_frame.columnconfigure(1, weight=0)

        left_sort_frame = tk.Frame(sort_frame, bg=PRIMARY)
        left_sort_frame.grid(row=0, column=0, sticky='w')
        tk.Label(left_sort_frame, width=12, text='Sort By:', font=TTL_TEXT, bg=PRIMARY).grid(row=0, column=0, sticky='w')
        tk.Button(left_sort_frame, width=12, text='ID', font=TTL_TEXT, bg=PRIMARY, fg=SECONDARY, command=lambda: self.set_customer_sort('id')).grid(row=0, column=1, padx=8)
        tk.Button(left_sort_frame, width=12, text='First Name', font=TTL_TEXT, bg=PRIMARY, fg=SECONDARY, command=lambda: self.set_customer_sort('first')).grid(row=0, column=2, padx=8)
        tk.Button(left_sort_frame, width=12, text='Last Name', font=TTL_TEXT, bg=PRIMARY, fg=SECONDARY, command=lambda: self.set_customer_sort('last')).grid(row=0, column=3, padx=8)

        right_sort_frame = tk.Frame(sort_frame, bg=PRIMARY)
        right_sort_frame.grid(row=0, column=1, sticky='e')
        self.customer_sort_label = tk.Label(right_sort_frame, text='Current:', font=TTL_TEXT, bg=PRIMARY)
        self.customer_sort_label.grid(row=0, column=0, padx=(12,13), sticky='e')
        self.customer_sort_asc_btn = tk.Button(right_sort_frame, width=12, text='Ascending', font=TTL_TEXT, bg=ACCENT, fg=SECONDARY, activebackground=ACCENT, activeforeground=SECONDARY, relief='raised', bd=1, command=lambda: self.set_customer_sort(self.customer_sort_key, ascending=True))
        self.customer_sort_asc_btn.grid(row=0, column=1, padx=(0, 4))
        self.customer_sort_desc_btn = tk.Button(right_sort_frame, width=12, text='Descending', font=TTL_TEXT, bg=ACCENT, fg=SECONDARY, activebackground=ACCENT, activeforeground=SECONDARY, relief='raised', bd=1, command=lambda: self.set_customer_sort(self.customer_sort_key, ascending=False))
        self.customer_sort_desc_btn.grid(row=0, column=2, padx=(0, 12))

        self.refresh_customers()

    def refresh_customers(self, customers_list=None):
        import db
        self.customer_tree.clear_all()
        try:
            customers = customers_list if customers_list is not None else db.get_customers()
        except Exception:
            customers = []
        for c in customers:
            cid = c['CustomerID']
            vals = (c['First_Name'], c['Last_Name'], c['Phone_Number'], c['Email'] or '', c['Address'] or '', '')
            tag = "evenrow" if len(self.customer_tree.get_children()) % 2 == 0 else "oddrow"
            self.customer_tree.insert('', 'end', iid=str(cid), text=str(cid), values=vals, tags=(tag,))
        # update count label
        try:
            cnt = len(customers)
            self.count_label.config(text=f'There are {cnt} Customer Records')
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
                cc = dict(c)
                fn = (cc.get('First_Name','') or '').lower()
                ln = (cc.get('Last_Name','') or '').lower()
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

    def set_customer_sort(self, key=None, ascending=None):
        import db
        try:
            if key is not None and key != self.customer_sort_key:
                self.customer_sort_key = key
            if ascending is not None:
                self.customer_sort_desc = not ascending

            customers = list(db.get_customers())
            if self.customer_sort_key == 'id':
                customers.sort(key=lambda c: int(c['CustomerID']), reverse=self.customer_sort_desc)
            elif self.customer_sort_key == 'first':
                customers.sort(key=lambda c: (dict(c).get('First_Name') or '').lower(), reverse=self.customer_sort_desc)
            elif self.customer_sort_key == 'last':
                customers.sort(key=lambda c: (dict(c).get('Last_Name') or '').lower(), reverse=self.customer_sort_desc)
            self.update_customer_sort_buttons()
            self.refresh_customers(customers)
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror('Sort Error', str(e))

    def update_customer_sort_buttons(self):
        if self.customer_sort_desc:
            self.customer_sort_asc_btn.config(bg=ACCENT, fg=SECONDARY, activebackground=ACCENT, activeforeground=SECONDARY, relief='raised', bd=1)
            self.customer_sort_desc_btn.config(bg=SECONDARY, fg='white', activebackground=SECONDARY, activeforeground='white', relief='sunken', bd=2)
        else:
            self.customer_sort_asc_btn.config(bg=SECONDARY, fg='white', activebackground=SECONDARY, activeforeground='white', relief='sunken', bd=2)
            self.customer_sort_desc_btn.config(bg=ACCENT, fg=SECONDARY, activebackground=ACCENT, activeforeground=SECONDARY, relief='raised', bd=1)

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
        pass

    def _create_action_overlays(self):
        pass

    def _reposition_action_overlays(self, event=None):
        pass
    
    #FOR CUSTOMER PAGE
    def open_edit_window(self, iid):
        import db
        from tkinter import messagebox
        cid = int(iid)
        rec = db.get_customer_details(cid)
        if not rec:
            messagebox.showerror('Error', 'Customer not found')
            return
        rec = dict(rec)
        edit_win = tk.Toplevel(self)
        edit_win.title(f"Edit Customer {cid}")
        edit_win.geometry("460x420")
        edit_win.resizable(False, False)
        edit_win.grab_set()
        edit_win.configure(bg=PRIMARY)
        edit_win.rowconfigure(0, weight=1); edit_win.columnconfigure(0, weight=1)

        form = tk.Frame(edit_win, padx=16, pady=12, bg=PRIMARY)
        form.grid(row=0, column=0, sticky='nsew')
        form.columnconfigure(1, weight=1)

        # Title and subtitle
        title_lbl = tk.Label(form, text='Edit Details', font=HDR2_TEXT, bg=PRIMARY, fg=SECONDARY, anchor='w')
        title_lbl.grid(row=0, column=0, columnspan=2, sticky='w', pady=(0,4))
        subtitle = f"For Customer {rec.get('First_Name','')} {rec.get('Last_Name','')}"
        sub_lbl = tk.Label(form, text=subtitle, font=(REG_TEXT,11,"bold"), bg=PRIMARY, fg="#555555", anchor='w')
        sub_lbl.grid(row=1, column=0, columnspan=2, sticky='w', pady=(0,10))

        tk.Label(form, text='First Name:', font=TTL_TEXT, bg=PRIMARY, fg=SECONDARY).grid(row=2, column=0, sticky='w', pady=(6,6))
        e_first = tk.Entry(form, font=REG_TEXT, highlightthickness=2, highlightbackground=ACCENT, highlightcolor=SECONDARY)
        e_first.grid(row=2, column=1, sticky='ew', ipady=3, pady=(6,6)); e_first.insert(0, rec['First_Name'])

        tk.Label(form, text='Last Name:', font=TTL_TEXT, bg=PRIMARY, fg=SECONDARY).grid(row=3, column=0, sticky='w', pady=(6,6))
        e_last = tk.Entry(form, font=REG_TEXT, highlightthickness=2, highlightbackground=ACCENT, highlightcolor=SECONDARY)
        e_last.grid(row=3, column=1, sticky='ew', ipady=3, pady=(6,6)); e_last.insert(0, rec['Last_Name'])

        tk.Label(form, text='Phone:', font=TTL_TEXT, bg=PRIMARY, fg=SECONDARY).grid(row=4, column=0, sticky='w', pady=(6,6))
        e_phone = tk.Entry(form, font=REG_TEXT, highlightthickness=2, highlightbackground=ACCENT, highlightcolor=SECONDARY)
        e_phone.grid(row=4, column=1, sticky='ew', ipady=3, pady=(6,6)); e_phone.insert(0, rec['Phone_Number'])

        tk.Label(form, text='Email:', font=TTL_TEXT, bg=PRIMARY, fg=SECONDARY).grid(row=5, column=0, sticky='w', pady=(6,6))
        e_email = tk.Entry(form, font=REG_TEXT, highlightthickness=2, highlightbackground=ACCENT, highlightcolor=SECONDARY)
        e_email.grid(row=5, column=1, sticky='ew', ipady=3, pady=(6,6)); e_email.insert(0, rec.get('Email','') or '')

        tk.Label(form, text='Address:', font=TTL_TEXT, bg=PRIMARY, fg=SECONDARY).grid(row=6, column=0, sticky='nw', pady=(6,6))
        e_addr = tk.Text(form, height=4, font=REG_TEXT, highlightthickness=2, highlightbackground=ACCENT, highlightcolor=SECONDARY)
        e_addr.grid(row=6, column=1, sticky='ew', pady=(6,6)); e_addr.insert('1.0', rec.get('Address','') or '')

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

        btnf = tk.Frame(form, bg=PRIMARY); btnf.grid(row=7, column=0, columnspan=2, pady=(12,0), sticky='ew'); btnf.columnconfigure((0,1), weight=1)
        tk.Button(btnf, text='Save', command=save_changes, font=TTL_TEXT, bg=SECONDARY, fg='white', cursor='hand2').grid(row=0, column=0, sticky='ew', padx=6)
        tk.Button(btnf, text='Delete', command=do_delete, font=TTL_TEXT, bg=ACCENT, fg=SECONDARY, cursor='hand2').grid(row=0, column=1, sticky='ew', padx=6)

class ReportsPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        self.configure(bg=PRIMARY)
        
        # Tab buttons
        tab_frame = tk.Frame(self, relief="solid", bg=PRIMARY)
        tab_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        tab_frame.columnconfigure((0,1,2,3,4,5), weight=1)
        
        self.current_tab = "revenue"
        tabs = {
            "revenue": "Revenue This Week",
            "received": "Received Today",
            "ready": "Ready Today",
            "overdue": "Overdue",
            "services": "Top Services",
            "customers": "Top Customers"
        }
        self.tab_buttons = {}
        for key, label in tabs.items():
            btn = tk.Button(
                tab_frame,
                text=label,
                command=lambda k=key: self.show_report(k),
                font=TTL_TEXT,
                bg=ACCENT,
                fg=SECONDARY,
                activebackground=ACCENT,
                activeforeground=SECONDARY,
                relief='raised',
                bd=1
            )
            btn.grid(row=0, column=list(tabs.keys()).index(key), sticky="ew", padx=4, pady=4)
            self.tab_buttons[key] = btn
        
        # Chart canvas area
        self.chart_frame = tk.Frame(self, bd=1, relief="groove")
        self.chart_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        self.chart_frame.columnconfigure(0, weight=1)
        self.chart_frame.rowconfigure(0, weight=1)
        
        self.canvas = None
        self.show_report("revenue")
        
    def refresh(self):
        self.show_report(self.current_tab)

    def update_report_tab_buttons(self):
        for key, btn in self.tab_buttons.items():
            if key == self.current_tab:
                btn.config(bg=SECONDARY, fg='white', activebackground=SECONDARY, activeforeground='white', relief='sunken', bd=2)
            else:
                btn.config(bg=ACCENT, fg=SECONDARY, activebackground=ACCENT, activeforeground=SECONDARY, relief='raised', bd=1)
    
    def show_report(self, report_type):
        import matplotlib.pyplot as plt
        
        # --- FIX: Close and clear all previous figures from memory before building the next one ---
        plt.close('all')
        
        # Clear previous canvas widget if it exists
        if hasattr(self, 'canvas') and self.canvas:
            self.canvas.get_tk_widget().destroy()
            
        # ... the rest of your original show_report code continues below exactly as it is ...
        
        # Clear previous chart
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
        self.canvas = None
        
        # Default configuration: KPI/Title in row 0 (no expand), Content in row 1 (expand)
        self.chart_frame.rowconfigure(0, weight=0)
        self.chart_frame.rowconfigure(1, weight=1)
        
        self.current_tab = report_type
        self.update_report_tab_buttons()

        kpi_frame = tk.Frame(self.chart_frame, bg="white")
        
        if report_type == "customers":
            self.chart_frame.rowconfigure(0, weight=1)
            self.chart_frame.rowconfigure(1, weight=0)
            data_orders = get_top_customers_by_orders()
            data_revenue = get_top_customers_by_revenue()
            
            # Main container for the sub-tab area
            customers_container = tk.Frame(self.chart_frame, bg="white")
            customers_container.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
            customers_container.rowconfigure(1, weight=1)
            customers_container.columnconfigure(0, weight=1)
            
            # Sub-tabs frame (the grey bar)
            subtab_frame = tk.Frame(customers_container, bg="#f0f0f0")
            subtab_frame.grid(row=0, column=0, sticky="ew")
            
            # Treeview container
            tree_container = tk.Frame(customers_container, bg="white", highlightbackground="#cccccc", highlightthickness=1)
            tree_container.grid(row=1, column=0, sticky="nsew")
            tree_container.columnconfigure(0, weight=1)
            tree_container.rowconfigure(0, weight=1)
            
            # Styles have been moved to App.__init__ globally
            
            def build_tree(parent, data):
                columns = ("rank", "name", "orders", "revenue")
                tree = ttk.Treeview(parent, columns=columns, show="headings", height=10, style="Fun.Treeview")
                tree.heading("rank", text="  Rank", anchor="w")
                tree.heading("name", text="  Customer Name", anchor="w")
                tree.heading("orders", text="  Total Orders", anchor="w")
                tree.heading("revenue", text="  Total Revenue", anchor="w")
                
                tree.column("rank", width=80, anchor="center")
                tree.column("name", width=250, anchor="w")
                tree.column("orders", width=120, anchor="e")
                tree.column("revenue", width=150, anchor="e")
                
                tree.tag_configure("evenrow", background="#f8f9fa")
                tree.tag_configure("oddrow", background="#ffffff")
                tree.tag_configure("top1", background="#ffeaa7", font=("Arial", 11, "bold")) 
                tree.tag_configure("top2", background="#dfe6e9", font=("Arial", 11, "bold")) 
                tree.tag_configure("top3", background="#fab1a0", font=("Arial", 11, "bold")) 
                
                for i, row in enumerate(data):
                    if i == 0:
                        rank_str, tag = "1st", "top1"
                    elif i == 1:
                        rank_str, tag = "2nd", "top2"
                    elif i == 2:
                        rank_str, tag = "3rd", "top3"
                    else:
                        r = i + 1
                        if 11 <= (r % 100) <= 13:
                            suf = 'th'
                        else:
                            suf = {1: 'st', 2: 'nd', 3: 'rd'}.get(r % 10, 'th')
                        rank_str, tag = f"{r}{suf}", ("evenrow" if i % 2 == 0 else "oddrow")
                        
                    tree.insert("", "end", values=(rank_str, row[0], row[1], f"₱ {row[2]:,.2f}"), tags=(tag,))
                return tree

            tree_orders = build_tree(tree_container, data_orders)
            tree_revenue = build_tree(tree_container, data_revenue)
            
            # Toggling logic
            def show_subtab(tab_name):
                btn_freq.config(bg="white" if tab_name == "freq" else "#f0f0f0", fg=SECONDARY if tab_name == "freq" else "black", font=("Arial", 12, "bold"))
                btn_spend.config(bg="white" if tab_name == "spend" else "#f0f0f0", fg=SECONDARY if tab_name == "spend" else "black", font=("Arial", 12, "bold"))
                
                if tab_name == "freq":
                    tree_revenue.grid_forget()
                    tree_orders.grid(row=0, column=0, sticky="nsew")
                else:
                    tree_orders.grid_forget()
                    tree_revenue.grid(row=0, column=0, sticky="nsew")

            btn_freq = tk.Button(subtab_frame, text="Most Frequent", relief="flat", bd=0, padx=20, pady=10, fg="black", command=lambda: show_subtab("freq"))
            btn_freq.pack(side="left")
            
            btn_spend = tk.Button(subtab_frame, text="Top Spenders", relief="flat", bd=0, padx=20, pady=10, fg="black", command=lambda: show_subtab("spend"))
            btn_spend.pack(side="left")
            
            # Default
            show_subtab("freq")
            
            return
        
        self.update_report_tab_buttons()

        
        if report_type == "services":
            from db import get_top_services_report_data
            services, count = get_top_services_report_data()
            total_services = sum(count) if count else 0
            
            kpi_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
            card = tk.Frame(kpi_frame, bg="#f9e7f9", bd=1, relief="solid", highlightbackground="#9b59b6", highlightthickness=1)
            card.pack(fill="x", pady=5, padx=20)
            tk.Label(card, text="Total Services Rendered", font=("Arial", 10, "bold"), bg="#f9e7f9", fg="#8e44ad").pack(pady=(10, 0))
            tk.Label(card, text=f"{total_services} Services", font=("Arial", 18, "bold"), bg="#f9e7f9", fg="#8e44ad").pack(pady=(0, 10))
            
        elif report_type == "overdue":
            from db import get_overdue_report_data
            overdue_data = get_overdue_report_data()
            
            # Safely unpack depending on what backend returns
            if isinstance(overdue_data, tuple):
                overdue_count, normal_ready_count = overdue_data
            else:
                overdue_count = overdue_data
                
            total_overdue = overdue_count
            
            if total_overdue == 0:
                msg = tk.Label(self.chart_frame, text="0 Overdue!\nAll caught up.", font=("Arial", 32, "bold"), bg="white", fg="#2ed573")
                msg.grid(row=0, column=0, sticky="nsew", pady=100)
                return
                
            # --- SOFTENED CONTEMPORARY KPI BANNER ---
            kpi_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
            
            # Removed bd=1 and relief="solid" line; added smooth visual styling properties
            kpi_card = tk.Frame(kpi_frame, bg="#fff5f5", bd=1, relief="solid", highlightbackground="#e74c3c", highlightthickness=1)
            kpi_card.pack(fill="x", pady=5, padx=20)
            
            tk.Label(kpi_card, text="Urgent Action Center", font=("Arial", 10, "bold"), bg="#fff5f5", fg="#e74c3c").pack(pady=(12, 2))
            tk.Label(kpi_card, text=f"{total_overdue} Orders Overdue", font=("Arial", 16, "bold"), bg="#fff5f5", fg="#c0392b").pack(pady=(0, 12))
        
        elif report_type == "revenue":
            from db import get_revenue_report_data
            days, revenue = get_revenue_report_data()
            total_rev = sum(revenue) if revenue else 0
            peak_rev = max(revenue) if revenue else 0
            
            kpi_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
            kpi_frame.columnconfigure((0, 1), weight=1)
            
            card1 = tk.Frame(kpi_frame, bg="#f0f8ff", bd=1, relief="solid", highlightbackground="#cce4ff", highlightthickness=1)
            card1.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
            tk.Label(card1, text="Total Weekly Revenue", font=("Arial", 10, "bold"), bg="#f0f8ff", fg="#3498db").pack(pady=(10, 0))
            tk.Label(card1, text=f"₱{total_rev:,.2f}", font=("Arial", 18, "bold"), bg="#f0f8ff", fg="#2980b9").pack(pady=(0, 10))
            
            card2 = tk.Frame(kpi_frame, bg="#f0f8ff", bd=1, relief="solid", highlightbackground="#cce4ff", highlightthickness=1)
            card2.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
            tk.Label(card2, text="Peak Day Revenue", font=("Arial", 10, "bold"), bg="#f0f8ff", fg="#3498db").pack(pady=(10, 0))
            tk.Label(card2, text=f"₱{peak_rev:,.2f}", font=("Arial", 18, "bold"), bg="#f0f8ff", fg="#2980b9").pack(pady=(0, 10))
            
        elif report_type in ["received", "ready"]:
            kpi_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
            if report_type == "received":
                from db import get_received_report_data
                hours, data = get_received_report_data()
                title, color, bg_color, fg_color = "Total Received", "#e67e22", "#fff3e8", "#d35400"
            else:
                from db import get_ready_report_data
                hours, data = get_ready_report_data()
                title, color, bg_color, fg_color = "Total Ready", "#2ecc71", "#e8f8f0", "#27ae60"
                
            total_orders = sum(data) if data else 0
            
            card = tk.Frame(kpi_frame, bg=bg_color, bd=1, relief="solid", highlightbackground=color, highlightthickness=1)
            card.pack(fill="x", pady=5, padx=20)
            tk.Label(card, text=title, font=("Arial", 10, "bold"), bg=bg_color, fg=fg_color).pack(pady=(10, 0))
            tk.Label(card, text=f"{total_orders} Orders", font=("Arial", 18, "bold"), bg=bg_color, fg=fg_color).pack(pady=(0, 10))

        # Create matplotlib figure for remaining reports
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.ticker import MaxNLocator
        
        fig, ax = plt.subplots(figsize=(10, 4))
        
        if report_type == "revenue":
            ax.plot(days, revenue, marker='o', linewidth=2, markersize=8, color='#3498db')
            ax.fill_between(range(len(days)), revenue, alpha=0.3, color='#3498db')
            ax.set_title("Revenue Trend", fontsize=14, fontweight='bold')
            ax.set_ylabel("Amount (₱)")
            ax.grid(True, alpha=0.3)
            
            if revenue and max(revenue) > 0:
                peak_idx = revenue.index(max(revenue))
                ax.annotate(f"Peak: ₱{max(revenue):,.2f}", xy=(peak_idx, max(revenue)), xytext=(0, 10), textcoords='offset points', ha='center', fontweight='bold', color='#2c3e50', bbox=dict(boxstyle='round,pad=0.3', fc='#f1c40f', alpha=1.0, ec='none'))
                
        elif report_type == "received":
            from matplotlib.ticker import MaxNLocator
            import db
            
            hours, counts = db.get_received_report_data()
            max_count = max(counts) if counts else 0
            
            # --- PROFESSIONAL ZERO-DATA GRAPH SCREEN ---
            if max_count == 0:
                ax.text(0.5, 0.5, "No orders received today.", 
                        ha='center', va='center', fontsize=12, fontweight='bold', color='black')
                ax.set_title("Orders Received Today (Hourly Breakdown)", fontsize=14, fontweight='bold', pad=20)
                ax.axis('off')  # Drops the grid and axes lines entirely
            else:
                # 1. Plot the bar chart with your exact color
                bars = ax.bar(hours, counts, color='#e67e22', alpha=0.8)
                
                # Only show numerical labels if the count is greater than 0
                for bar in bars:
                    height = bar.get_height()
                    if height > 0:  # Hides the unanchored "0" labels entirely
                        ax.annotate(
                            f'{int(height)}',
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 3),  # 3 points vertical offset
                            textcoords="offset points",
                            ha='center', va='bottom',
                            fontweight='bold', color='#2c3e50'
                        )
                
                # Set titles and labels
                ax.set_title("Orders Received Today", fontsize=14, fontweight='bold', pad=20)
                ax.set_xlabel("Time of Day")
                ax.set_ylabel("Number of Orders")
                
                # Map your hour time labels back to the X-axis positions
                ax.set_xticks(range(len(hours)))
                ax.set_xticklabels(hours, ha='center', fontsize=9)
                
                # Force Y-Axis to use integers only
                ax.yaxis.set_major_locator(MaxNLocator(integer=True))
                ax.set_ylim(0, max_count + 1)
                ax.grid(True, alpha=0.3, axis='y')
            
        elif report_type == "ready":
            from matplotlib.ticker import MaxNLocator
            import db
            
            hours, counts = db.get_ready_report_data()
            max_count = max(counts) if counts else 0
            
            # --- PROFESSIONAL ZERO-DATA GRAPH SCREEN ---
            if max_count == 0:
                ax.text(0.5, 0.5, "No orders ready for pickup today.", 
                        ha='center', va='center', fontsize=12, fontweight='bold', color="black")
                ax.set_title("Orders Made Ready Today", fontsize=14, fontweight='bold', pad=20)
                ax.axis('off')  # Drops the grid and axes lines entirely
            else:
                # 1. Plot the bar chart (using your ready report's original color)
                bars = ax.bar(hours, counts, color='#2ecc71', alpha=0.8)
                
                # Only show numerical labels if the count is greater than 0
                for bar in bars:
                    height = bar.get_height()
                    if height > 0:  # Hides the unanchored "0" labels entirely
                        ax.annotate(
                            f'{int(height)}',
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 3),
                            textcoords="offset points",
                            ha='center', va='bottom',
                            fontweight='bold', color='#2c3e50'
                        )
                
                # Set titles and labels
                ax.set_title("Orders Made Ready Today", fontsize=14, fontweight='bold', pad=20)
                ax.set_xlabel("Time of Day")
                ax.set_ylabel("Number of Orders")
                
                # Map your hour time labels back to the X-axis positions
                ax.set_xticks(range(len(hours)))
                ax.set_xticklabels(hours, ha='center', fontsize=9)
                
                # Force Y-Axis to use integers only and establish a clean range
                ax.yaxis.set_major_locator(MaxNLocator(integer=True))
                ax.set_ylim(0, max_count + 1)
                ax.grid(True, alpha=0.3, axis='y')
            
        elif report_type == "overdue":
            import db # Ensures access to the updated module namespace

            # 1. Fetch breakdown numbers directly from db
            overdue_data = db.get_overdue_report_data()
            
            # Safe parsing check
            if isinstance(overdue_data, tuple):
                overdue_count, normal_ready_count = overdue_data
            else:
                overdue_count = overdue_data
                normal_ready_count = 0
                
            total_ready = overdue_count + normal_ready_count
            
            # Wipes out any previous drawings on this specific axis
            ax.clear() 
            
            if total_ready == 0:
                # Gray placeholder ring when there is no data at all
                ax.pie([1], colors=['#bdc3c7'], radius=1, wedgeprops=dict(width=0.4, edgecolor='w'))
                ax.text(0, 0, "0", ha='center', va='center', fontsize=20, fontweight='bold', color='#7f8c8d')
                ax.text(0, -0.2, "TOTAL READY", ha='center', va='center', fontsize=8, fontweight='bold', color="black")
                ax.set_title("Ready Order Status Breakdown", fontsize=14, fontweight='bold', pad=30)
            else:
                slices = [overdue_count, normal_ready_count]
                slice_colors = ['#e74c3c', '#2ecc71']  # Red for Overdue, Green for On-Time Ready
                
                # Combine category and custom calculated percentage into a clean, uniform string literal
                # This bypasses the default font artifact that shrinks the % symbol
                pct_overdue = (overdue_count / total_ready) * 100
                pct_ontime = (normal_ready_count / total_ready) * 100
                
                labels = [
                    f"Overdue\n{pct_overdue:.1f}%",
                    f"On-Time\n{pct_ontime:.1f}%"
                ]
                
                legend_labels = [
                    f'Overdue ({overdue_count} orders) — Passed pickup threshold',
                    f'On-Time ({normal_ready_count} orders) — Safely within pickup window'
                ]
                
                # Plotting the donut chart (Set autopct=None to avoid the native styling artifact)
                wedges, texts = ax.pie(
                    slices, 
                    labels=labels,                     
                    colors=slice_colors, 
                    radius=1, 
                    labeldistance=1.30,                 # Slightly increased breathing room outside the donut
                    wedgeprops=dict(width=0.4, edgecolor='w')
                )
                
                # FIX 1 & 3: Clean text contrast, sizing, and optical alignment adjustments
                for i, text in enumerate(texts):
                    text.set_color('#1a252f')          # Sharp charcoal text color
                    text.set_fontsize(10.5)
                    text.set_fontweight('bold')
                    
                    # Nudge the bottom label ("On-Time") slightly to the left to perfectly balance the alignment
                    if i == 1: 
                        x_pos, y_pos = text.get_position()
                        text.set_position((x_pos + 0.25, y_pos - 0.10))  # Precise horizontal nudge
                        text.set_horizontalalignment('center')    # Force precise bounding center anchor
                
                # FIX 2: Concentric centering fix inside the donut hole.
                # Setting both lines to explicitly share a center anchor point prevents minor font-width offsets.
                ax.text(0, 0.05, str(total_ready), ha='center', va='center', fontsize=28, fontweight='bold', color='#2c3e50')
                ax.text(0, -0.18, "TOTAL READY", ha='center', va='center', fontsize=8, fontweight='bold', color='#7f8c8d')
                
                # Descriptive legend without a border box layout outline
                ax.legend(
                    wedges, 
                    legend_labels, 
                    loc="upper center", 
                    bbox_to_anchor=(0.5, -0.18), 
                    ncol=1, 
                    frameon=False,
                    fontsize=9
                )
                
                # Title layout
                ax.set_title("Ready Order Status Breakdown", fontsize=14, fontweight='bold', pad=30)
            
        elif report_type == "services":
            import db
            from matplotlib.ticker import MaxNLocator
            # 1. Clear any residual graphics layers
            ax.clear()
            
            # Unpack exactly using your native layout logic structure from line 2720
            services, count = db.get_top_services_report_data()
            
            if not services or len(services) == 0:
                ax.text(0.5, 0.5, "No orders recorded yet to calculate top services.", 
                        horizontalalignment='center', verticalalignment='center', fontsize=12, fontweight='bold', color='black')
                ax.set_title("Top Services", fontsize=14, fontweight='bold', pad=20)
                ax.axis('off')
            else:
                ax.axis('on')
                
                # 2. Pair them together for dynamic volume sorting
                paired_data = list(zip(services, count))
                sorted_pairs = sorted(paired_data, key=lambda x: int(x[1]))
                
                sorted_services = [item[0] for item in sorted_pairs]
                sorted_count = [item[1] for item in sorted_pairs]
                
                # 3. Plot clean horizontal bars matching your original color specifications
                bars = ax.barh(sorted_services, sorted_count, color='#9b59b6', alpha=0.8)
                ax.bar_label(bars, fmt='%d', padding=3, color='#2c3e50', fontweight='bold')
                
                ax.set_title("Top Services", fontsize=14, fontweight='bold', pad=20)
                ax.set_xlabel("Services Rendered")
                ax.xaxis.set_major_locator(MaxNLocator(integer=True))
                ax.grid(True, alpha=0.3, axis='x')

        fig.tight_layout()
        
        self.canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew")

        if report_type == "revenue" and revenue:
            hover_annot = ax.annotate(
                "", xy=(0, 0), xytext=(0, 10), textcoords='offset points',
                ha='center', fontweight='bold', color='#2c3e50',
                bbox=dict(boxstyle='round,pad=0.3', fc='#c2e0f4', alpha=1.0, ec='none'),
                visible=False, zorder=5
            )
            x_coords = list(range(len(days)))

            def on_hover(event):
                if event.inaxes != ax:
                    hover_annot.set_visible(False)
                    self.canvas.draw_idle()
                    return
                found = False
                for i, (xc, yc) in enumerate(zip(x_coords, revenue)):
                    # transform data coords to display coords for distance check
                    disp = ax.transData.transform((xc, yc))
                    dist = ((event.x - disp[0])**2 + (event.y - disp[1])**2) ** 0.5
                    if dist < 18:
                        hover_annot.xy = (xc, yc)
                        hover_annot.set_text(f"{days[i]}\n₱{yc:,.2f}")
                        hover_annot.set_visible(True)
                        found = True
                        break
                if not found:
                    hover_annot.set_visible(False)
                self.canvas.draw_idle()

            self.canvas.mpl_connect('motion_notify_event', on_hover)



if __name__ == "__main__":
    root = tk.Tk()
    root.title("Laundrify - Frontend")
    root.geometry("1000x650")
    app = App(root)
    app.grid(row=0, column=0, sticky='nsew')
    root.rowconfigure(0, weight=1)
    root.columnconfigure(0, weight=1)
    root.mainloop()
