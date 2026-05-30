import sqlite3
import os
import uuid
import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "laundrify.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript("""
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    unit_price REAL NOT NULL,
    pricing_type TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT NOT NULL UNIQUE,
    customer_id INTEGER,
    status TEXT NOT NULL,
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ready_at TIMESTAMP,
    released_at TIMESTAMP,
    notes TEXT,
    FOREIGN KEY(customer_id) REFERENCES customers(id)
);
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    service_id INTEGER,
    quantity REAL,
    unit_price REAL,
    subtotal REAL,
    FOREIGN KEY(order_id) REFERENCES orders(id),
    FOREIGN KEY(service_id) REFERENCES services(id)
);
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    amount REAL,
    paid_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    method TEXT,
    FOREIGN KEY(order_id) REFERENCES orders(id)
);
""")
    conn.commit()

    cur.execute("SELECT COUNT(*) as c FROM services")
    row = cur.fetchone()
    if row is None or row[0] == 0:
        services = [
            ("Wash", 3.0, "per_kg"),
            ("Dry", 2.5, "per_kg"),
            ("Fold", 1.0, "per_item"),
            ("Ironing", 1.5, "per_item"),
            ("Dry Clean", 8.0, "per_item"),
            ("Express", 5.0, "flat")
        ]
        cur.executemany("INSERT INTO services (name, unit_price, pricing_type) VALUES (?, ?, ?)", services)
        conn.commit()
    conn.close()


def create_customer(name, phone=None, email=None, address=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO customers (name, phone, email, address) VALUES (?,?,?,?)", (name, phone, email, address))
    conn.commit()
    cid = cur.lastrowid
    conn.close()
    return cid


def create_order(customer_id, items, notes=None):
    conn = get_conn()
    cur = conn.cursor()
    uuid_str = uuid.uuid4().hex[:12]
    cur.execute("INSERT INTO orders (uuid, customer_id, status, notes) VALUES (?,?,?,?)", (uuid_str, customer_id, "Received", notes))
    order_id = cur.lastrowid
    for it in items:
        service_id = it['service_id']
        quantity = float(it.get('quantity', 1))
        cur.execute("SELECT unit_price FROM services WHERE id=?", (service_id,))
        r = cur.fetchone()
        unit_price = r['unit_price'] if r else 0
        subtotal = unit_price * quantity
        cur.execute("INSERT INTO order_items (order_id, service_id, quantity, unit_price, subtotal) VALUES (?,?,?,?,?)",
                    (order_id, service_id, quantity, unit_price, subtotal))
    conn.commit()
    conn.close()
    return order_id


def list_services():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM services")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_orders():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
SELECT o.id, o.uuid, o.status, o.received_at, c.name as customer_name,
    (SELECT COALESCE(SUM(subtotal),0) FROM order_items WHERE order_id=o.id) as total
FROM orders o
LEFT JOIN customers c ON c.id=o.customer_id
ORDER BY o.received_at DESC
""")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_order_items(order_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
SELECT oi.*, s.name as service_name FROM order_items oi
LEFT JOIN services s ON s.id = oi.service_id
WHERE oi.order_id=?
""", (order_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def order_total(order_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(SUM(subtotal),0) as total FROM order_items WHERE order_id=?", (order_id,))
    r = cur.fetchone(); conn.close()
    return r['total'] if r else 0


def update_order_status(order_id, new_status):
    conn = get_conn(); cur = conn.cursor()
    now = datetime.datetime.now().isoformat(sep=' ', timespec='seconds')
    if new_status == "Ready":
        cur.execute("UPDATE orders SET status=?, ready_at=? WHERE id=?", (new_status, now, order_id))
    elif new_status == "Released":
        cur.execute("UPDATE orders SET status=?, released_at=? WHERE id=?", (new_status, now, order_id))
    else:
        cur.execute("UPDATE orders SET status=? WHERE id=?", (new_status, order_id))
    conn.commit(); conn.close()


def record_payment(order_id, amount, method="Cash"):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("INSERT INTO payments (order_id, amount, method) VALUES (?,?,?)", (order_id, amount, method))
    conn.commit(); conn.close()


def payments_total(order_id):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT COALESCE(SUM(amount),0) as paid FROM payments WHERE order_id=?", (order_id,))
    r = cur.fetchone(); conn.close()
    return r['paid'] if r else 0


def orders_in_progress():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM orders WHERE status IN ('Received','Washing','Drying') ORDER BY received_at DESC")
    rows = cur.fetchall(); conn.close()
    return [dict(r) for r in rows]


def orders_ready_today():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT o.* FROM orders o WHERE o.status='Ready' AND date(o.ready_at)=date('now','localtime')")
    rows = cur.fetchall(); conn.close()
    return [dict(r) for r in rows]


def orders_received_today():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT o.* FROM orders o WHERE date(o.received_at)=date('now','localtime')")
    rows = cur.fetchall(); conn.close()
    return [dict(r) for r in rows]


def total_revenue_today():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT COALESCE(SUM(amount),0) as total FROM payments WHERE date(paid_at)=date('now','localtime')")
    r = cur.fetchone(); conn.close()
    return r['total'] if r else 0


def overdue_orders():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM orders WHERE status='Ready' AND released_at IS NULL AND date(ready_at) < date('now','localtime')")
    rows = cur.fetchall(); conn.close()
    return [dict(r) for r in rows]


def most_frequent_services(limit=10):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
SELECT s.name, COUNT(oi.service_id) as cnt
FROM order_items oi JOIN services s ON oi.service_id=s.id
GROUP BY oi.service_id ORDER BY cnt DESC LIMIT ?
""", (limit,))
    rows = cur.fetchall(); conn.close()
    return [dict(r) for r in rows]


if __name__ == '__main__':
    init_db()
    print('DB initialized at', DB_PATH)
