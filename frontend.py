import tkinter as tk
from tkinter import ttk

from db import get_received_report_data, get_revenue_report_data, get_ready_report_data, get_overdue_report_data, get_top_services_report_data

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

        self.nav_buttons = {}
        self.current_page = "NewOrderPage"
        
        btn_new = tk.Button(nav, text="New Order", command=lambda: self.show("NewOrderPage"), 
                            font=("Arial", 10), height=2, cursor="hand2")
        btn_view = tk.Button(nav, text="View Order", command=lambda: self.show("ViewOrderPage"), 
                            font=("Arial", 10), height=2, cursor="hand2")
        btn_reports = tk.Button(nav, text="Reports", command=lambda: self.show("ReportsPage"), 
                               font=("Arial", 10), height=2, cursor="hand2")

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
                btn.config(bg="#3498db", fg="white", activebackground="#2980b9", activeforeground="white", relief="sunken", bd=2)
            else:
                btn.config(bg="#95a5a6", fg="white", activebackground="#7f8c8d", activeforeground="white", relief="raised", bd=1)
        
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
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)

        # left form using grid only
        left.columnconfigure(0, minsize=80)
        left.columnconfigure(1, weight=1)
        for i in range(10):
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
        # Register phone validation - only numbers
        vcmd_phone = left.register(self.validate_phone)
        self.phone_entry.config(validate='key', validatecommand=(vcmd_phone, '%P'))

        tk.Label(left, text="Service:").grid(row=4, column=0, sticky="w")
        self.service_map = {
            "Wash, Dry & Fold": ("weight", 70),
            "Wash & Dry": ("weight", 50),
            "Dry Cleaning": ("size", {"small": 110, "large": 150}),
            "Ironing": ("size", {"small": 20, "large": 30})
        }
        self.service_combo = ttk.Combobox(left, values=list(self.service_map.keys()), state="readonly")
        self.service_combo.grid(row=4, column=1, sticky="ew")
        self.service_combo.bind("<<ComboboxSelected>>", self.on_service_selected)

        # Dynamic field frame (weight or size selection)
        self.dynamic_frame = tk.Frame(left)
        self.dynamic_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=6)
        self.dynamic_frame.columnconfigure(0, minsize=80)
        self.dynamic_frame.columnconfigure(1, weight=1)

        tk.Label(left, text="Additional\nNotes:").grid(row=6, column=0, sticky="nw")
        self.notes_text = tk.Text(left, height=3, width=30)
        self.notes_text.grid(row=6, column=1, sticky="ew")

        add_btn = tk.Button(left, text="Add Item", command=self.add_item)
        add_btn.grid(row=7, column=0, columnspan=2, pady=10)

        # right - instructions and order items area
        tk.Label(right, text="Instruction", font=("TkDefaultFont", 10, "bold")).grid(row=0, column=0, sticky="w")
        instr_text = (
            "To create an order: fill customer details, select a service, then enter weight or size, then press 'Add Item'.\n"
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
            tk.Label(self.dynamic_frame, text="Weight (kg):").grid(row=0, column=0, sticky="w")
            self.weight_var = tk.Entry(self.dynamic_frame)
            self.weight_var.grid(row=0, column=1, sticky="ew")
            self.size_var = None
            self.qty_var = None

        else:  # size-based
            # Show radio buttons for small/large
            tk.Label(self.dynamic_frame, text="Size:").grid(row=0, column=0, sticky="w")
            self.size_var = tk.StringVar(value="small")
            rb_frame = tk.Frame(self.dynamic_frame)
            rb_frame.grid(row=0, column=1, sticky="ew")
            tk.Radiobutton(rb_frame, text="Small", variable=self.size_var, value="small").pack(side="left", padx=5)
            tk.Radiobutton(rb_frame, text="Large", variable=self.size_var, value="large").pack(side="left", padx=5)
            
            # Show quantity entry field
            tk.Label(self.dynamic_frame, text="Quantity:").grid(row=1, column=0, sticky="w")
            self.qty_var = tk.Entry(self.dynamic_frame)
            # Register quantity validation - only numbers
            vcmd_qty = self.dynamic_frame.register(self.validate_quantity)
            self.qty_var.config(validate='key', validatecommand=(vcmd_qty, '%P'))
            self.qty_var.grid(row=1, column=1, sticky="ew")
            self.weight_var = None
    
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
                price = weight * pricing
            except ValueError:
                messagebox.showerror("Invalid Input", "Weight must be a valid number")
                return
        else:  # size-based
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
            
            price_per_item = pricing[size]
            quantity = f"{qty}x {size.capitalize()}"
            price = price_per_item * qty

        self.order_tree.insert("", "end", values=(service, quantity, f"₱ {price:.2f}"))

    def remove_item(self):
        sel = self.order_tree.selection()
        for iid in sel:
            self.order_tree.delete(iid)

    def create_order(self):
        from tkinter import messagebox
        import db
        
        # Validate customer info
        name = self.name_entry.get().strip()
        phone = self.phone_entry.get().strip()
        address = self.address_entry.get().strip()
        email = self.email_entry.get().strip()
        notes = self.notes_text.get("1.0", "end-1c").strip()
        
        # Required field validation
        required_errors = []
        if not name:
            required_errors.append("Name is required")
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
            # Parse name into first and last name
            name_parts = name.split(maxsplit=1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ""
            
            # Create or get customer
            customer_id = db.create_or_get_customer(first_name, last_name, phone, email, address)
            
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
            
            # Clear the form
            self.name_entry.delete(0, tk.END)
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
        
        # Main border frame
        main_frame = tk.Frame(self, bd=1, relief="solid")
        main_frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        main_frame.rowconfigure(2, weight=1)
        main_frame.columnconfigure(0, weight=1)
        
        # Top section with title and buttons
        top_frame = tk.Frame(main_frame)
        top_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=10)
        top_frame.columnconfigure(0, weight=1)
        
        # "Unpaid Orders" as subheading
        tk.Label(top_frame, text="Unpaid Orders", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w")
        
        # Action buttons on right
        button_frame = tk.Frame(top_frame)
        button_frame.grid(row=0, column=1, sticky="e", padx=5, pady=5)
        
        tk.Button(button_frame, text="Update Status", command=self.open_update_status_window, width=15, height=1).pack(side="left", padx=5)
        tk.Button(button_frame, text="Process Payment", command=self.open_payment_window, width=15, height=1).pack(side="left", padx=5)
        
        # Filter section
        filter_frame = tk.Frame(main_frame)
        filter_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=10)
        filter_frame.columnconfigure(1, weight=0)
        filter_frame.columnconfigure(3, weight=0)
        filter_frame.columnconfigure(5, weight=0)
        filter_frame.columnconfigure(7, weight=0)
        
        tk.Label(filter_frame, text="Search ID:").grid(row=0, column=0, padx=5)
        self.search_entry = tk.Entry(filter_frame, width=15)
        self.search_entry.grid(row=0, column=1, padx=5)
        
        search_btn = tk.Button(filter_frame, text="Search", command=self.search_orders, width=8)
        search_btn.grid(row=0, column=2, padx=5)
        
        tk.Label(filter_frame, text="Status:").grid(row=0, column=3, padx=5)
        self.status_combo = ttk.Combobox(filter_frame, values=["All", "Received", "In-Progress", "Ready", "Released"], width=12, state="readonly")
        self.status_combo.current(0)
        self.status_combo.grid(row=0, column=4, padx=5)
        
        tk.Label(filter_frame, text="Date From:").grid(row=0, column=5, padx=5)
        self.date_from = tk.Entry(filter_frame, width=12)
        self.date_from.insert(0, "mm/dd/yyyy")
        self.date_from.grid(row=0, column=6, padx=5)
        
        tk.Label(filter_frame, text="To:").grid(row=0, column=7, padx=5)
        self.date_to = tk.Entry(filter_frame, width=12)
        self.date_to.insert(0, "mm/dd/yyyy")
        self.date_to.grid(row=0, column=8, padx=5)
        
        refresh_btn = tk.Button(filter_frame, text="Refresh", command=self.refresh_table, width=10)
        refresh_btn.grid(row=0, column=9, padx=10)
        
        # Table
        table_frame = tk.Frame(main_frame)
        table_frame.grid(row=2, column=0, sticky="nsew", padx=15, pady=10)
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        
        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        columns = ("OrderID", "Date Received", "Customer", "Service", "Qty/Wt", "Status", "Total", "Paid", "Action")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", yscrollcommand=scrollbar.set, height=15)
        scrollbar.config(command=self.tree.yview)
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100 if col != "Action" else 80)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        
        # Legend/Filter at bottom
        legend_frame = tk.Frame(main_frame)
        legend_frame.grid(row=3, column=0, sticky="ew", padx=15, pady=10)
        
        legend_label = tk.Label(legend_frame, text="Filter By Status:")
        legend_label.pack(side="left", padx=5)
        
        for status in ["Received", "In-Progress", "Ready", "Released"]:
            tk.Button(legend_frame, text=status, width=12, command=lambda s=status: self.sort_by_status(s)).pack(side="left", padx=3)
        
        # Load initial data
        self.refresh_table()
    
    def refresh_table(self):
        """Refresh the treeview with current orders"""
        import db
        
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        try:
            orders = db.get_unpaid_orders()
            for order in orders:
                service_display = db.get_order_services(order['OrderID'])
                self.tree.insert("", "end", values=(
                    order['OrderID'],
                    order['Order_Received_At'],
                    f"{order['First_Name']} {order['Last_Name']}",
                    service_display,
                    "-",
                    order['Order_Status'],
                    f"₱{order['Order_Total_Price']}",
                    "Yes" if order['Order_Payed_At'] else "No",
                    ""
                ))
        except Exception as e:
            print(f"Error loading orders: {e}")
    
    def search_orders(self):
        """Search orders by order ID"""
        import db
        from tkinter import messagebox
        
        search_term = self.search_entry.get().strip()
        if not search_term:
            self.refresh_table()
            return
        
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        try:
            orders = db.get_unpaid_orders()
            found = False
            for order in orders:
                if str(order['OrderID']).startswith(search_term):
                    service_display = db.get_order_services(order['OrderID'])
                    self.tree.insert("", "end", values=(
                        order['OrderID'],
                        order['Order_Received_At'],
                        f"{order['First_Name']} {order['Last_Name']}",
                        service_display,
                        "-",
                        order['Order_Status'],
                        f"₱{order['Order_Total_Price']}",
                        "Yes" if order['Order_Payed_At'] else "No",
                        ""
                    ))
                    found = True
            
            if not found:
                messagebox.showinfo("Search", f"No orders found with ID starting with '{search_term}'")
        except Exception as e:
            messagebox.showerror("Error", f"Search error: {e}")
    
    def sort_by_status(self, status):
        """Sort the treeview by status"""
        import db
        
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        try:
            orders = db.get_unpaid_orders()
            
            if status != "All":
                orders = [o for o in orders if o['Order_Status'] == status]
            
            for order in orders:
                service_display = db.get_order_services(order['OrderID'])
                self.tree.insert("", "end", values=(
                    order['OrderID'],
                    order['Order_Received_At'],
                    f"{order['First_Name']} {order['Last_Name']}",
                    service_display,
                    "-",
                    order['Order_Status'],
                    f"₱{order['Order_Total_Price']}",
                    "Yes" if order['Order_Payed_At'] else "No",
                    ""
                ))
        except Exception as e:
            print(f"Error sorting orders: {e}")
    
    def open_update_status_window(self):
        """Open a new window for updating order status"""
        import db
        
        status_win = tk.Toplevel(self)
        status_win.title("Update Order Status")
        status_win.geometry("500x350")
        status_win.resizable(False, False)
        status_win.grab_set()
        
        # Main container with border
        container = tk.Frame(status_win, bd=2, relief="solid", bg="white")
        container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Header
        header = tk.Frame(container, bg="#2c3e50", height=60)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        tk.Label(header, text="Update Order Status", font=("Arial", 16, "bold"), bg="#2c3e50", fg="white").pack(pady=15)
        
        # Form content
        form_frame = tk.Frame(container, bg="white")
        form_frame.pack(fill="both", expand=True, padx=30, pady=30)
        form_frame.columnconfigure(1, weight=1)
        
        # Order ID field
        tk.Label(form_frame, text="Order ID:", font=("Arial", 11), bg="white").grid(row=0, column=0, sticky="w", pady=15)
        
        try:
            orders = db.get_unpaid_orders()
            order_ids = [str(order['OrderID']) for order in orders]
        except:
            order_ids = []
        
        order_combo = ttk.Combobox(form_frame, values=order_ids, width=30, state="readonly", font=("Arial", 10))
        order_combo.grid(row=0, column=1, sticky="ew", pady=15, padx=10)
        
        # New Status field
        tk.Label(form_frame, text="New Status:", font=("Arial", 11), bg="white").grid(row=1, column=0, sticky="w", pady=15)
        status_combo = ttk.Combobox(form_frame, values=["Received", "In-Progress", "Ready", "Released"], width=30, state="readonly", font=("Arial", 10))
        status_combo.grid(row=1, column=1, sticky="ew", pady=15, padx=10)
        
        # Button frame
        btn_frame = tk.Frame(container, bg="white")
        btn_frame.pack(fill="x", padx=30, pady=20)
        btn_frame.columnconfigure((0, 1), weight=1)
        
        def update_and_close():
            from tkinter import messagebox
            
            order_id = order_combo.get()
            new_status = status_combo.get()
            
            if not order_id or not new_status:
                messagebox.showwarning("Error", "Please select an order and status", parent=status_win)
                return
            
            try:
                db.update_order_status(int(order_id), new_status)
                messagebox.showinfo("Success", f"Order {order_id} status updated to {new_status}", parent=status_win)
                self.refresh_table()
                status_win.destroy()
            except ValueError as e:
                messagebox.showerror("Error", str(e), parent=status_win)
            except Exception as e:
                messagebox.showerror("Error", f"Database error: {str(e)}", parent=status_win)
        
        tk.Button(btn_frame, text="Update Status", command=update_and_close, font=("Arial", 11, "bold"), 
                 bg="#27ae60", fg="white", height=2, cursor="hand2").grid(row=0, column=0, sticky="ew", padx=5)
        tk.Button(btn_frame, text="Cancel", command=status_win.destroy, font=("Arial", 11), 
                 bg="#95a5a6", fg="white", height=2, cursor="hand2").grid(row=0, column=1, sticky="ew", padx=5)
    
    def open_payment_window(self):
        """Open a new window for processing payment"""
        import db
        
        payment_win = tk.Toplevel(self)
        payment_win.title("Process Payment")
        payment_win.geometry("520x450")
        payment_win.resizable(False, False)
        payment_win.grab_set()
        
        # Main container with border
        container = tk.Frame(payment_win, bd=2, relief="solid", bg="white")
        container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Header
        header = tk.Frame(container, bg="#2c3e50", height=60)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        tk.Label(header, text="Process Payment", font=("Arial", 16, "bold"), bg="#2c3e50", fg="white").pack(pady=15)
        
        # Form content
        form_frame = tk.Frame(container, bg="white")
        form_frame.pack(fill="both", expand=True, padx=30, pady=30)
        form_frame.columnconfigure(1, weight=1)
        
        # Order ID field
        tk.Label(form_frame, text="Order ID:", font=("Arial", 11), bg="white").grid(row=0, column=0, sticky="w", pady=12)
        
        try:
            orders = db.get_unpaid_orders()
            order_ids = [str(order['OrderID']) for order in orders]
        except:
            order_ids = []
        
        order_combo = ttk.Combobox(form_frame, values=order_ids, width=35, state="readonly", font=("Arial", 10))
        order_combo.grid(row=0, column=1, sticky="ew", pady=12, padx=10)
        
        # Amount Due display
        tk.Label(form_frame, text="Amount Due (₱):", font=("Arial", 11), bg="white").grid(row=1, column=0, sticky="w", pady=12)
        amount_due_display = tk.Label(form_frame, text="0.00", font=("Arial", 13, "bold"), bg="#ecf0f1", fg="#2c3e50", relief="sunken", width=35)
        amount_due_display.grid(row=1, column=1, sticky="ew", pady=12, padx=10)
        
        # Cash Received field
        tk.Label(form_frame, text="Cash Received (₱):", font=("Arial", 11), bg="white").grid(row=2, column=0, sticky="w", pady=12)
        cash_entry = tk.Entry(form_frame, width=37, font=("Arial", 10), bd=1, relief="solid")
        cash_entry.grid(row=2, column=1, sticky="ew", pady=12, padx=10)
        
        def on_order_selected(event=None):
            """Update amount due when order is selected"""
            order_id = order_combo.get()
            if order_id:
                try:
                    order = db.get_order_details(int(order_id))
                    if order:
                        amount_due_display.config(text=f"₱{order['Order_Total_Price']:.2f}")
                        cash_entry.delete(0, tk.END)
                except Exception as e:
                    print(f"Error fetching order: {e}")
        
        order_combo.bind("<<ComboboxSelected>>", on_order_selected)
        
        def process_payment():
            from tkinter import messagebox
            
            order_id = order_combo.get()
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
                
                # Create styled summary window
                summary_win = tk.Toplevel(payment_win)
                summary_win.title("Payment Summary")
                summary_win.geometry("450x500")
                summary_win.resizable(False, False)
                summary_win.grab_set()
                
                # Summary container
                sum_container = tk.Frame(summary_win, bd=2, relief="solid", bg="white")
                sum_container.pack(fill="both", expand=True, padx=10, pady=10)
                
                # Summary header
                sum_header = tk.Frame(sum_container, bg="#27ae60", height=60)
                sum_header.pack(fill="x")
                sum_header.pack_propagate(False)
                
                tk.Label(sum_header, text="PAYMENT SUMMARY", font=("Arial", 16, "bold"), bg="#27ae60", fg="white").pack(pady=15)
                
                # Summary details
                detail_frame = tk.Frame(sum_container, bg="white")
                detail_frame.pack(fill="both", expand=True, padx=30, pady=30)
                
                # Details with better styling
                tk.Label(detail_frame, text=f"Order ID: {order_id}", font=("Arial", 12), bg="white").pack(pady=10, anchor="w")
                tk.Label(detail_frame, text=f"Amount Due: ₱{result['total_amount']:.2f}", font=("Arial", 12), bg="white").pack(pady=10, anchor="w")
                tk.Label(detail_frame, text=f"Cash Received: ₱{result['paid_amount']:.2f}", font=("Arial", 12), bg="white").pack(pady=10, anchor="w")
                
                # Change display with styling
                change_frame = tk.Frame(detail_frame, bg="#d4edda", relief="solid", bd=1)
                change_frame.pack(fill="x", pady=15)
                tk.Label(change_frame, text=f"Change: ₱{result['change']:.2f}", font=("Arial", 14, "bold"), bg="#d4edda", fg="#155724").pack(pady=10)
                
                # Buttons
                btn_frame = tk.Frame(sum_container, bg="white")
                btn_frame.pack(fill="x", padx=30, pady=20)
                btn_frame.columnconfigure((0, 1), weight=1)
                
                def confirm_and_close():
                    messagebox.showinfo("Success", "Payment processed successfully!", parent=summary_win)
                    self.refresh_table()
                    summary_win.destroy()
                    payment_win.destroy()
                
                tk.Button(btn_frame, text="Confirm", command=confirm_and_close, font=("Arial", 11, "bold"), 
                         bg="#27ae60", fg="white", height=2, cursor="hand2").grid(row=0, column=0, sticky="ew", padx=5)
                tk.Button(btn_frame, text="Close", command=summary_win.destroy, font=("Arial", 11), 
                         bg="#95a5a6", fg="white", height=2, cursor="hand2").grid(row=0, column=1, sticky="ew", padx=5)
                
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid numeric amount", parent=payment_win)
            except Exception as e:
                messagebox.showerror("Error", f"Database error: {str(e)}", parent=payment_win)
        
        # Button frame
        btn_frame = tk.Frame(container, bg="white")
        btn_frame.pack(fill="x", padx=30, pady=20)
        btn_frame.columnconfigure((0, 1), weight=1)
        
        tk.Button(btn_frame, text="Calculate Change", command=process_payment, font=("Arial", 11, "bold"), 
                 bg="#3498db", fg="white", height=2, cursor="hand2").grid(row=0, column=0, sticky="ew", padx=5)
        tk.Button(btn_frame, text="Cancel", command=payment_win.destroy, font=("Arial", 11), 
                 bg="#95a5a6", fg="white", height=2, cursor="hand2").grid(row=0, column=1, sticky="ew", padx=5)



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
