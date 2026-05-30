Laundrify - Desktop Laundry POS (Tkinter + SQLite)

Quick start:

1. (Optional) Copy your logo to assets/logo.png
2. python -m pip install -r requirements.txt
3. python laundrify_app.py

Files added:

- db.py (SQLite schema and helpers)
- ui.py (Tkinter frames)
- laundrify_app.py (app runner)

Sample queries are implemented in db.py: orders_in_progress, orders_ready_today, orders_received_today, total_revenue_today, overdue_orders, most_frequent_services
