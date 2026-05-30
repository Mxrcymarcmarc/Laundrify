import tkinter as tk
from tkinter import ttk, messagebox
import os
import db


class NewOrderFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.services = db.list_services()
        self.items = []
        self.build()

    def build(self):
        frm = ttk.LabelFrame(self, text='New Order')
        frm.pack(fill='both', expand=True, padx=10, pady=10)

        row = 0
        ttk.Label(frm, text='Customer name:').grid(row=row, column=0, sticky='w')
        self.name_entry = ttk.Entry(frm, width=40)
        self.name_entry.grid(row=row, column=1, sticky='w')
        row += 1

        ttk.Label(frm, text='Phone:').grid(row=row, column=0, sticky='w')
        self.phone_entry = ttk.Entry(frm, width=20)
        self.phone_entry.grid(row=row, column=1, sticky='w')
        row += 1

        ttk.Label(frm, text='Service:').grid(row=row, column=0, sticky='w')
        self.service_var = tk.StringVar()
        names = [s['name'] for s in self.services]
        self.service_cb = ttk.Combobox(frm, values=names, state='readonly')
        self.service_cb.grid(row=row, column=1, sticky='w')
        row += 1

        ttk.Label(frm, text='Quantity:').grid(row=row, column=0, sticky='w')
        self.qty_entry = ttk.Entry(frm, width=10)
        self.qty_entry.insert(0, '1')
        self.qty_entry.grid(row=row, column=1, sticky='w')
        row += 1

        ttk.Button(frm, text='Add Item', command=self.add_item).grid(row=row, column=1, sticky='w')
        row += 1

        self.items_tv = ttk.Treeview(frm, columns=('service','qty','price'), show='headings')
        self.items_tv.heading('service', text='Service')
        self.items_tv.heading('qty', text='Qty')
        self.items_tv.heading('price', text='Price')
        self.items_tv.grid(row=row, column=0, columnspan=2, sticky='nsew')
        row += 1

        ttk.Button(frm, text='Create Order', command=self.create_order).grid(row=row, column=1, sticky='e')

    def add_item(self):
        sel = self.service_cb.get()
        if not sel:
            messagebox.showwarning('Service', 'Please select a service')
            return
        qty = float(self.qty_entry.get() or 1)
        service = next((s for s in self.services if s['name']==sel), None)
        if not service:
            return
        self.items.append({'service_id': service['id'], 'service_name': service['name'], 'quantity': qty})
        self.items_tv.insert('', 'end', values=(service['name'], qty, service['unit_price'] * qty))

    def create_order(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning('Customer', 'Please enter customer name')
            return
        cid = db.create_customer(name, self.phone_entry.get().strip())
        order_items = [{'service_id': i['service_id'], 'quantity': i['quantity']} for i in self.items]
        order_id = db.create_order(cid, order_items)
        messagebox.showinfo('Created', f'Order {order_id} created')
        self.items = []
        for row in self.items_tv.get_children():
            self.items_tv.delete(row)
        self.name_entry.delete(0, 'end')
        self.phone_entry.delete(0, 'end')


class OrdersFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.build()

    def build(self):
        frm = ttk.Frame(self)
        frm.pack(fill='both', expand=True, padx=10, pady=10)
        self.tv = ttk.Treeview(frm, columns=('id','uuid','customer','status','received','total'), show='headings')
        for c in ('id','uuid','customer','status','received','total'):
            self.tv.heading(c, text=c.title())
        self.tv.pack(fill='both', expand=True)
        self.tv.bind('<<TreeviewSelect>>', self.on_select)

        btns = ttk.Frame(self)
        btns.pack(fill='x')
        ttk.Button(btns, text='Refresh', command=self.refresh).pack(side='left')
        ttk.Button(btns, text='Mark Ready', command=lambda: self.change_status('Ready')).pack(side='left')
        ttk.Button(btns, text='Release', command=lambda: self.change_status('Released')).pack(side='left')
        ttk.Button(btns, text='Record Payment', command=self.record_payment).pack(side='left')
        self.refresh()

    def refresh(self):
        for r in self.tv.get_children():
            self.tv.delete(r)
        for o in db.list_orders():
            self.tv.insert('', 'end', iid=o['id'], values=(o['id'], o['uuid'], o['customer_name'] or 'Walk-in', o['status'], o['received_at'], o['total']))

    def on_select(self, event):
        pass

    def change_status(self, new_status):
        sel = self.tv.selection()
        if not sel:
            messagebox.showwarning('Select', 'Select an order')
            return
        oid = int(sel[0])
        db.update_order_status(oid, new_status)
        self.refresh()

    def record_payment(self):
        sel = self.tv.selection()
        if not sel:
            messagebox.showwarning('Select', 'Select an order')
            return
        oid = int(sel[0])
        def do():
            try:
                amt = float(ent.get())
            except Exception:
                messagebox.showerror('Amount', 'Invalid amount')
                return
            db.record_payment(oid, amt)
            pw.destroy()
            messagebox.showinfo('Payment', 'Recorded')
        pw = tk.Toplevel(self)
        pw.title('Record Payment')
        ttk.Label(pw, text='Amount').pack(side='left')
        ent = ttk.Entry(pw)
        ent.pack(side='left')
        ttk.Button(pw, text='OK', command=do).pack(side='left')


class ReportsFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.build()

    def build(self):
        frm = ttk.Frame(self)
        frm.pack(fill='both', expand=True, padx=10, pady=10)
        ttk.Button(frm, text='In-progress Orders', command=self.show_in_progress).pack(fill='x')
        ttk.Button(frm, text='Ready Today', command=self.show_ready_today).pack(fill='x')
        ttk.Button(frm, text='Received Today', command=self.show_received_today).pack(fill='x')
        ttk.Button(frm, text='Revenue Today', command=self.show_revenue_today).pack(fill='x')
        ttk.Button(frm, text='Overdue', command=self.show_overdue).pack(fill='x')
        ttk.Button(frm, text='Top Services', command=self.show_top_services).pack(fill='x')
        self.out = tk.Text(frm, height=20)
        self.out.pack(fill='both', expand=True)

    def show_in_progress(self):
        rows = db.orders_in_progress()
        self.out.delete('1.0', 'end')
        for r in rows:
            self.out.insert('end', f"{r['id']} {r['uuid']} {r['status']}\n")

    def show_ready_today(self):
        rows = db.orders_ready_today()
        self.out.delete('1.0', 'end')
        for r in rows:
            self.out.insert('end', f"{r['id']} {r['uuid']} ready_at={r.get('ready_at')}\n")

    def show_received_today(self):
        rows = db.orders_received_today()
        self.out.delete('1.0', 'end')
        for r in rows:
            self.out.insert('end', f"{r['id']} {r['uuid']} received_at={r.get('received_at')}\n")

    def show_revenue_today(self):
        total = db.total_revenue_today()
        self.out.delete('1.0', 'end')
        self.out.insert('end', f"Revenue today: {total}\n")

    def show_overdue(self):
        rows = db.overdue_orders()
        self.out.delete('1.0', 'end')
        for r in rows:
            self.out.insert('end', f"{r['id']} {r['uuid']} ready_at={r.get('ready_at')}\n")

    def show_top_services(self):
        rows = db.most_frequent_services()
        self.out.delete('1.0', 'end')
        for r in rows:
            self.out.insert('end', f"{r['name']}: {r['cnt']}\n")
