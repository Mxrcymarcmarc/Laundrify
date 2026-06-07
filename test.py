import tkinter as tk
from tkinter import ttk, messagebox


# ====================================
# WINDOW
# ====================================


root = tk.Tk()
root.title("Laundrify - Orders")
root.geometry("1200x700")


# ====================================
# TITLE
# ====================================


title = tk.Label(
    root,
    text="Laundrify - Orders",
    font=("Arial", 24, "bold")
)
title.pack(pady=10)


# ====================================
# MAIN FRAME
# ====================================


main_frame = tk.Frame(root)
main_frame.pack(fill="both", expand=True, padx=10, pady=10)


# ====================================
# NOTEBOOK (TABS)
# ====================================


notebook = ttk.Notebook(main_frame)
notebook.pack(fill="both", expand=True)


# ==================================================
# TAB 1 - VIEW ORDERS
# ==================================================


view_tab = tk.Frame(notebook)
notebook.add(view_tab, text="View Orders")


# ====================================
# FILTER SECTION
# ====================================


filter_frame = tk.Frame(view_tab)
filter_frame.pack(fill="x", padx=10, pady=10)


tk.Label(filter_frame, text="Search:").grid(row=0, column=0, padx=5)


search_entry = tk.Entry(filter_frame, width=15)
search_entry.grid(row=0, column=1)


tk.Label(filter_frame, text="Status:").grid(row=0, column=2, padx=5)


status_combo = ttk.Combobox(
    filter_frame,
    values=["All", "Received", "Washing", "Drying", "Ready", "Released"],
    width=12
)
status_combo.current(0)
status_combo.grid(row=0, column=3)


tk.Label(filter_frame, text="Date From:").grid(row=0, column=4, padx=5)


date_from = tk.Entry(filter_frame, width=12)
date_from.insert(0, "mm/dd/yyyy")
date_from.grid(row=0, column=5)


tk.Label(filter_frame, text="To:").grid(row=0, column=6, padx=5)


date_to = tk.Entry(filter_frame, width=12)
date_to.insert(0, "mm/dd/yyyy")
date_to.grid(row=0, column=7)


refresh_btn = tk.Button(
    filter_frame,
    text="Refresh",
    width=10
)
refresh_btn.grid(row=0, column=8, padx=10)


# ====================================
# TABLE
# ====================================


table_frame = tk.Frame(view_tab)
table_frame.pack(fill="both", expand=True, padx=10)


# Scrollbar
scrollbar = ttk.Scrollbar(table_frame)
scrollbar.pack(side="right", fill="y")


columns = (
    "Order ID",
    "Date Received",
    "Customer",
    "Service",
    "Qty/Wt",
    "Status",
    "Total",
    "Paid"
)


tree = ttk.Treeview(
    table_frame,
    columns=columns,
    show="headings",
    yscrollcommand=scrollbar.set
)


scrollbar.config(command=tree.yview)


for col in columns:
    tree.heading(col, text=col)
    tree.column(col, width=120)


tree.pack(fill="both", expand=True)


# Sample Data
tree.insert(
    "",
    "end",
    values=(
        1001,
        "06/01/2026",
        "Juan Dela Cruz",
        "Wash & Fold",
        "5kg",
        "Washing",
        "₱150",
        "No"
    )
)


tree.insert("", "end",
    values=(1002, "06/02/2026", "Maria Santos",
            "Dry Clean", "3 pcs", "Ready",
            "₱250", "Yes"))


tree.insert("", "end",
    values=(1003, "06/03/2026", "Pedro Cruz",
            "Ironing", "10 pcs", "Drying",
            "₱180", "No"))


tree.insert("", "end",
    values=(1004, "06/04/2026", "Ana Reyes",
            "Wash & Fold", "8 kg", "Received",
            "₱300", "No"))


def open_details(event):
    view_details()
   


tree.bind("<Double-1>", open_details)


# ====================================
# BOTTOM SECTION
# ====================================


bottom_frame = tk.Frame(view_tab)
bottom_frame.pack(fill="x", padx=10, pady=10)


legend_label = tk.Label(
    bottom_frame,
    text="Legend (Status):"
)
legend_label.pack(side="left")


statuses = [
    "Received",
    "Washing",
    "Drying",
    "Ready",
    "Released"
]


for status in statuses:
    tk.Button(
        bottom_frame,
        text=status,
        width=10
    ).pack(side="left", padx=3)


def view_details():


    selected = tree.selection()


    if not selected:
        messagebox.showwarning(
            "No Selection",
            "Please select an order first."
        )
        return


    item = tree.item(selected[0])


    data = item["values"]


    popup = tk.Toplevel(root)
    popup.title("Order Details")
    popup.geometry("450x450")


    tk.Label(
        popup,
        text="ORDER DETAILS",
        font=("Arial", 16, "bold")
    ).pack(pady=10)


    details_frame = tk.Frame(popup)
    details_frame.pack(padx=20, pady=10)


    labels = [
        "Order ID",
        "Date Received",
        "Customer",
        "Service",
        "Qty/Wt",
        "Status",
        "Total",
        "Paid"
    ]


    for i in range(len(labels)):
        tk.Label(
            details_frame,
            text=labels[i] + ":",
            font=("Arial", 11, "bold")
        ).grid(row=i, column=0, sticky="w", pady=5)


        tk.Label(
            details_frame,
            text=str(data[i]),
            font=("Arial", 11)
        ).grid(row=i, column=1, sticky="w", padx=15)


    tk.Button(
    popup,
    text="CLOSE ME",
    command=popup.destroy,
    width=20,
    height=2
    ).pack(pady=20)


def update_order_status():


    selected = tree.selection()


    if not selected:
        messagebox.showwarning(
            "No Selection",
            "Please select an order from View Orders first."
        )
        return


    status = new_status.get()


    if status == "":
        messagebox.showwarning(
            "No Status",
            "Please select a status."
        )
        return


    item = selected[0]


    values = list(tree.item(item, "values"))


    values[5] = status


    tree.item(item, values=values)


    messagebox.showinfo(
        "Success",
        f"Order status updated to {status}"
    )




view_details_btn = tk.Button(
    bottom_frame,
    text="View Details",
    width=15,
    command=view_details
)


view_details_btn.pack(side="right")        


# ==================================================
# TAB 2 - UPDATE STATUS
# ==================================================


status_tab = tk.Frame(notebook)
notebook.add(status_tab, text="Update Status")


tk.Label(
    status_tab,
    text="Update Laundry Status",
    font=("Arial", 16, "bold")
).pack(pady=20)


tk.Label(status_tab, text="Order ID").pack()


order_entry = tk.Entry(status_tab)
order_entry.pack(pady=5)


tk.Label(status_tab, text="Select New Status").pack()


new_status = ttk.Combobox(
    status_tab,
    values=[
        "Received",
        "Washing",
        "Drying",
        "Ready",
        "Released"
    ]
)
new_status.pack(pady=5)


tk.Button(
    status_tab,
    text="Update Status",
    width=20,
    command=update_order_status
).pack(pady=20)


# ==================================================
# TAB 3 - PROCESS PAYMENT
# ==================================================


payment_tab = tk.Frame(notebook)
notebook.add(payment_tab, text="Process Payment")


tk.Label(
    payment_tab,
    text="Process Payment",
    font=("Arial", 16, "bold")
).pack(pady=20)


tk.Label(payment_tab, text="Order ID").pack()


payment_order = tk.Entry(payment_tab)
payment_order.pack()


tk.Label(payment_tab, text="Amount Due").pack()


amount_due = tk.Entry(payment_tab)
amount_due.pack()


tk.Label(payment_tab, text="Cash Received").pack()


cash_received = tk.Entry(payment_tab)
cash_received.pack()


tk.Label(payment_tab, text="Change").pack()


change_entry = tk.Entry(payment_tab)
change_entry.pack()


tk.Button(
    payment_tab,
    text="Process Payment",
    width=20
).pack(pady=20)


# ====================================
# NAVIGATION BUTTONS
# ====================================


nav_frame = tk.Frame(root)
nav_frame.pack(pady=10)


tk.Button(
    nav_frame,
    text="New Order",
    width=15
).grid(row=0, column=0, padx=10)


tk.Button(
    nav_frame,
    text="View Order",
    width=15
).grid(row=0, column=1, padx=10)


tk.Button(
    nav_frame,
    text="Reports",
    width=15
).grid(row=0, column=2, padx=10)


# ====================================
root.mainloop()
	
