import sqlite3

def init_db():
    tables = [
        """
        CREATE TABLE IF NOT EXISTS CUSTOMERS (
            CustomerID INTEGER PRIMARY KEY AUTOINCREMENT, 
            First_Name TEXT NOT NULL,
            Last_Name TEXT NOT NULL,
            Phone_Number TEXT NOT NULL,
            Email TEXT NULL,
            Address TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS SERVICES (
            ServiceID INTEGER PRIMARY KEY AUTOINCREMENT,
            Service_Type TEXT NOT NULL,
            Service_Unit_Price INTEGER NOT NULL,
            Service_Unit TEXT NOT NULL DEFAULT 'pcs'
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS ORDERS (
            OrderID INTEGER PRIMARY KEY AUTOINCREMENT,
            CustomerID INTEGER NOT NULL,
            Order_Status TEXT NOT NULL,
            Order_Total_Price INTEGER NOT NULL,
            Order_Received_At TEXT NOT NULL,
            Order_Ready_At TEXT NULL,
            Order_Released_At TEXT NULL,
            Order_Payed_At TEXT NULL,
            Order_Notes TEXT NULL,
            FOREIGN KEY (CustomerID) REFERENCES CUSTOMERS(CustomerID)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS ORDER_DETAILS (
            OrderDetailID INTEGER PRIMARY KEY AUTOINCREMENT,
            OrderID INTEGER NOT NULL,
            ServiceID INTEGER NOT NULL,
            Order_Subtotal INTEGER NOT NULL,
            Item_Weight REAL NOT NULL,
            Item_Unit TEXT NOT NULL DEFAULT 'pcs',
            FOREIGN KEY (OrderID) REFERENCES ORDERS(OrderID),
            FOREIGN KEY (ServiceID) REFERENCES SERVICES(ServiceID)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS PAYMENTS (
            PaymentID INTEGER PRIMARY KEY AUTOINCREMENT,
            OrderID INTEGER NOT NULL,
            Amount_Paid INTEGER NOT NULL,
            Payment_Date TEXT NOT NULL,
            FOREIGN KEY (OrderID) REFERENCES ORDERS(OrderID)
        )
        """,
    ]

    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        for table_query in tables:
            cursor.execute(table_query)
        # Ensure ORDER_DETAILS has Item_Unit column (backfill if missing)
        try:
            cursor.execute("ALTER TABLE ORDER_DETAILS ADD COLUMN Item_Unit TEXT DEFAULT 'pcs'")
        except Exception:
            # column likely exists
            pass
        # Ensure SERVICES has Service_Unit column (kg or pcs)
        try:
            cursor.execute("ALTER TABLE SERVICES ADD COLUMN Service_Unit TEXT DEFAULT 'pcs'")
        except Exception:
            pass
        conn.commit()

def get_orders():
    """Fetch all orders with their details"""
    with sqlite3.connect("Laundrify.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT o.OrderID, o.CustomerID, o.Order_Status, o.Order_Total_Price, 
                   o.Order_Received_At, o.Order_Ready_At, o.Order_Released_At, o.Order_Payed_At,
                   c.First_Name, c.Last_Name
            FROM ORDERS o
            JOIN CUSTOMERS c ON o.CustomerID = c.CustomerID
            ORDER BY o.Order_Received_At DESC
        """)
        return cursor.fetchall()

def get_unpaid_orders():
    """Fetch orders that have not been paid yet"""
    with sqlite3.connect("Laundrify.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT o.OrderID, o.CustomerID, o.Order_Status, o.Order_Total_Price, 
                   o.Order_Received_At, o.Order_Ready_At, o.Order_Released_At, o.Order_Payed_At,
                   c.First_Name, c.Last_Name
            FROM ORDERS o
            JOIN CUSTOMERS c ON o.CustomerID = c.CustomerID
            WHERE o.Order_Payed_At IS NULL
            ORDER BY o.Order_Received_At DESC
        """)
        return cursor.fetchall()

def get_order_details(order_id):
    """Fetch detailed information about a specific order"""
    with sqlite3.connect("Laundrify.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT o.*, c.First_Name, c.Last_Name, c.Phone_Number, c.Email
            FROM ORDERS o
            JOIN CUSTOMERS c ON o.CustomerID = c.CustomerID
            WHERE o.OrderID = ?
        """, (order_id,))
        return cursor.fetchone()

def is_order_paid(order_id):
    """Check if an order has been paid"""
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT Order_Payed_At FROM ORDERS WHERE OrderID = ?", (order_id,))
        result = cursor.fetchone()
        return result and result[0] is not None

def get_order_services(order_id):
    """Get unique service names for an order
    
    Returns:
        str: Service name if single service, "Mixed Services" if multiple
    """
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT s.Service_Type
            FROM ORDER_DETAILS od
            JOIN SERVICES s ON od.ServiceID = s.ServiceID
            WHERE od.OrderID = ?
        """, (order_id,))
        services = cursor.fetchall()
        
        if len(services) == 1:
            return services[0][0]
        elif len(services) > 1:
            return "Mixed Services"
        else:
            return "Unknown"

def get_order_qty_display(order_id):
    """Return a human-readable qty/wt summary for an order, e.g. '3 kg' or '2 pcs' or '3 kg + 2 pcs'
    Robustly parses legacy and current ORDER_DETAILS entries where Item_Weight may contain textual quantities.
    """
    import re
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT Item_Weight, IFNULL(Item_Unit, '') FROM ORDER_DETAILS WHERE OrderID = ?", (order_id,))
        rows = cursor.fetchall()
        if not rows:
            return "-"
        totals = {}
        for r in rows:
            raw_weight = r[0]
            unit_hint = (r[1] or '').lower()
            weight = 0.0
            unit = 'pcs'

            # If explicit unit column exists and is meaningful
            if unit_hint in ('kg', 'pcs', 'pc'):
                unit = 'kg' if unit_hint == 'kg' else 'pcs'

            # Try numeric coercion first
            if isinstance(raw_weight, (int, float)):
                weight = float(raw_weight)
            else:
                # raw_weight might be bytes or str with units: '3 kg', '3x Small', '3 pcs'
                try:
                    s = str(raw_weight).strip().lower()
                except Exception:
                    s = ''

                if not s:
                    weight = 0.0
                else:
                    # match '3 kg' or '3.5 kg'
                    m = re.match(r"^([0-9]+(?:\.[0-9]+)?)\s*(kg|kilos)?$", s)
                    if m:
                        weight = float(m.group(1))
                        unit = 'kg'
                    else:
                        # match '3x small' or '3 x small' or '3 pcs' or '3pc'
                        m2 = re.match(r"^([0-9]+)\s*(?:x|pcs|pc)?(?:\s*.*)?$", s)
                        if m2:
                            weight = float(m2.group(1))
                            unit = 'pcs'
                        else:
                            # extract first numeric token as fallback
                            m3 = re.search(r"([0-9]+(?:\.[0-9]+)?)", s)
                            if m3:
                                if '.' in m3.group(1):
                                    weight = float(m3.group(1))
                                    unit = 'kg'
                                else:
                                    weight = float(m3.group(1))
                                    unit = 'pcs'
                            else:
                                weight = 0.0
                                unit = 'pcs'

            totals[unit] = totals.get(unit, 0.0) + weight

        parts = []
        for unit, val in totals.items():
            if unit == 'kg':
                parts.append(f"{val:g} kg")
            else:
                parts.append(f"{int(val)} pcs")
        return ' + '.join(parts)

def get_services():
    with sqlite3.connect("Laundrify.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT ServiceID, Service_Type, Service_Unit_Price, IFNULL(Service_Unit,'pcs') as Service_Unit FROM SERVICES ORDER BY Service_Type")
        return cursor.fetchall()

def add_service(service_type, unit_price, unit='pcs'):
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO SERVICES (Service_Type, Service_Unit_Price, Service_Unit) VALUES (?, ?, ?)", (service_type, int(unit_price), unit))
        conn.commit()
        return cursor.lastrowid

def update_service(service_id, service_type, unit_price, unit='pcs'):
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE SERVICES SET Service_Type = ?, Service_Unit_Price = ?, Service_Unit = ? WHERE ServiceID = ?", (service_type, int(unit_price), unit, service_id))
        conn.commit()
        return True

def restore_default_services():
    """Restore a curated default set of services and prices"""
    defaults = [
        ("Wash, Dry & Fold", 70, 'kg'),
        ("Wash & Dry", 50, 'kg'),
        ("Dry Cleaning", 150, 'pcs'),
        ("Ironing", 20, 'pcs')
    ]
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM SERVICES")
        cursor.executemany("INSERT INTO SERVICES (Service_Type, Service_Unit_Price, Service_Unit) VALUES (?, ?, ?)", defaults)
        conn.commit()
        return True


def update_order_status(order_id, new_status):
    """Update order status with business rule validation
    
    Statuses allowed: Received, In-Progress, Ready, Released
    Rule: Cannot mark as Released if order has not been paid
    """
    from datetime import datetime
    
    if new_status == "Released" and not is_order_paid(order_id):
        raise ValueError("Cannot mark order as Released. Order must be paid first.")
    
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute(
            "UPDATE ORDERS SET Order_Status = ? WHERE OrderID = ?",
            (new_status, order_id)
        )
        
        if new_status == "Ready":
            cursor.execute(
                "UPDATE ORDERS SET Order_Ready_At = ? WHERE OrderID = ?",
                (timestamp, order_id)
            )
        
        if new_status == "Released":
            cursor.execute(
                "UPDATE ORDERS SET Order_Released_At = ? WHERE OrderID = ?",
                (timestamp, order_id)
            )
        
        conn.commit()
        return True

def process_payment(order_id, amount_paid):
    """Process payment for an order
    
    Returns: dict with keys 'success', 'total_amount', 'change', 'message'
    """
    from datetime import datetime
    
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT Order_Total_Price FROM ORDERS WHERE OrderID = ?", (order_id,))
        result = cursor.fetchone()
        
        if not result:
            return {
                'success': False,
                'message': 'Order not found'
            }
        
        total_amount = result[0]
        
        if amount_paid < total_amount:
            return {
                'success': False,
                'total_amount': total_amount,
                'paid_amount': amount_paid,
                'short_amount': total_amount - amount_paid,
                'message': f'Insufficient payment. Short by ₱{total_amount - amount_paid:.2f}'
            }
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute(
            "INSERT INTO PAYMENTS (OrderID, Amount_Paid, Payment_Date) VALUES (?, ?, ?)",
            (order_id, amount_paid, timestamp)
        )
        
        cursor.execute(
            "UPDATE ORDERS SET Order_Payed_At = ? WHERE OrderID = ?",
            (timestamp, order_id)
        )
        
        conn.commit()
        
        change = amount_paid - total_amount
        return {
            'success': True,
            'total_amount': total_amount,
            'paid_amount': amount_paid,
            'change': change,
            'message': 'Payment processed successfully'
        }

def create_or_get_customer(first_name, last_name, phone_number, email="", address=""):
    """Create a new customer or get existing customer by phone number.

    If phone_number is empty, always create a new customer (avoid treating empty phone as unique key).
    """
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()

        phone = (phone_number or "").strip()
        if phone:
            cursor.execute("SELECT CustomerID FROM CUSTOMERS WHERE Phone_Number = ?", (phone,))
            result = cursor.fetchone()
            if result:
                return result[0]

        # fallback: create a new customer record
        cursor.execute(
            "INSERT INTO CUSTOMERS (First_Name, Last_Name, Phone_Number, Email, Address) VALUES (?, ?, ?, ?, ?)",
            (first_name, last_name, phone, email, address)
        )
        conn.commit()
        return cursor.lastrowid

def create_order(customer_id, total_price, items, notes=""):
    """Create a new order with items
    
    items: list of dicts with keys 'service', 'quantity', 'subtotal'
    Returns: order_id
    """
    from datetime import datetime
    import re
    
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute(
            """INSERT INTO ORDERS (CustomerID, Order_Status, Order_Total_Price, 
               Order_Received_At, Order_Notes) 
               VALUES (?, ?, ?, ?, ?)""",
            (customer_id, "Received", total_price, timestamp, notes)
        )
        order_id = cursor.lastrowid
        
        for item in items:
            cursor.execute("SELECT ServiceID FROM SERVICES WHERE Service_Type = ?", (item['service'],))
            service_result = cursor.fetchone()
            
            if service_result:
                service_id = service_result[0]
            else:
                cursor.execute(
                    "INSERT INTO SERVICES (Service_Type, Service_Unit_Price) VALUES (?, ?)",
                    (item['service'], 0)
                )
                service_id = cursor.lastrowid
            
            # parse quantity string to numeric value and unit
            qty_raw = item.get('quantity', '')
            qty_value = 0
            unit = 'pcs'
            if isinstance(qty_raw, (int, float)):
                qty_value = qty_raw
            elif isinstance(qty_raw, str):
                s = qty_raw.strip().lower()
                # match patterns like '3 kg' or '3.5 kg'
                m = re.match(r"([0-9]+(?:\.[0-9]+)?)\s*kg", s)
                if m:
                    qty_value = float(m.group(1))
                    unit = 'kg'
                else:
                    # match patterns like '3x' or '3 x' or '3 pcs'
                    m2 = re.match(r"([0-9]+)\s*(?:x|pcs|pc)?", s)
                    if m2:
                        qty_value = int(m2.group(1))
                        unit = 'pcs'
                    else:
                        # fallback: try to extract number
                        m3 = re.search(r"([0-9]+(?:\.[0-9]+)?)", s)
                        if m3:
                            if '.' in m3.group(1):
                                qty_value = float(m3.group(1))
                                unit = 'kg'
                            else:
                                qty_value = int(m3.group(1))
                                unit = 'pcs'
                        else:
                            qty_value = 0
                            unit = 'pcs'

            cursor.execute(
                """INSERT INTO ORDER_DETAILS (OrderID, ServiceID, Order_Subtotal, Item_Weight, Item_Unit) 
                   VALUES (?, ?, ?, ?, ?)""",
                (order_id, service_id, item['subtotal'], qty_value, unit)
            )
        
        conn.commit()
        return order_id


def get_paid_orders():
    with sqlite3.connect("Laundrify.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT o.OrderID, o.CustomerID, o.Order_Status, o.Order_Total_Price, 
                   o.Order_Received_At, o.Order_Ready_At, o.Order_Released_At, o.Order_Payed_At,
                   c.First_Name, c.Last_Name
            FROM ORDERS o
            JOIN CUSTOMERS c ON o.CustomerID = c.CustomerID
            WHERE o.Order_Payed_At IS NOT NULL AND o.Order_Released_At IS NULL
            ORDER BY o.Order_Received_At DESC
        """)
        return cursor.fetchall()


def get_archived_orders():
    with sqlite3.connect("Laundrify.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT o.OrderID, o.CustomerID, o.Order_Status, o.Order_Total_Price, 
                   o.Order_Received_At, o.Order_Ready_At, o.Order_Released_At, o.Order_Payed_At,
                   c.First_Name, c.Last_Name
            FROM ORDERS o
            JOIN CUSTOMERS c ON o.CustomerID = c.CustomerID
            WHERE o.Order_Payed_At IS NOT NULL AND o.Order_Released_At IS NOT NULL
            ORDER BY o.Order_Received_At DESC
        """)
        return cursor.fetchall()

# Date-range queries for search-by-date
def get_unpaid_orders_by_date(start_date, end_date):
    with sqlite3.connect("Laundrify.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT o.OrderID, o.CustomerID, o.Order_Status, o.Order_Total_Price, 
                   o.Order_Received_At, o.Order_Ready_At, o.Order_Released_At, o.Order_Payed_At,
                   c.First_Name, c.Last_Name, c.Email
            FROM ORDERS o
            JOIN CUSTOMERS c ON o.CustomerID = c.CustomerID
            WHERE o.Order_Payed_At IS NULL
            AND date(o.Order_Received_At) BETWEEN date(?) AND date(?)
            ORDER BY o.Order_Received_At DESC
        """, (start_date, end_date))
        return cursor.fetchall()

def get_paid_orders_by_date(start_date, end_date):
    with sqlite3.connect("Laundrify.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT o.OrderID, o.CustomerID, o.Order_Status, o.Order_Total_Price, 
                   o.Order_Received_At, o.Order_Ready_At, o.Order_Released_At, o.Order_Payed_At,
                   c.First_Name, c.Last_Name, c.Email
            FROM ORDERS o
            JOIN CUSTOMERS c ON o.CustomerID = c.CustomerID
            WHERE o.Order_Payed_At IS NOT NULL AND o.Order_Released_At IS NULL
            AND date(o.Order_Received_At) BETWEEN date(?) AND date(?)
            ORDER BY o.Order_Received_At DESC
        """, (start_date, end_date))
        return cursor.fetchall()

def get_archived_orders_by_date(start_date, end_date):
    with sqlite3.connect("Laundrify.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT o.OrderID, o.CustomerID, o.Order_Status, o.Order_Total_Price, 
                   o.Order_Received_At, o.Order_Ready_At, o.Order_Released_At, o.Order_Payed_At,
                   c.First_Name, c.Last_Name, c.Email
            FROM ORDERS o
            JOIN CUSTOMERS c ON o.CustomerID = c.CustomerID
            WHERE o.Order_Payed_At IS NOT NULL AND o.Order_Released_At IS NOT NULL
            AND date(o.Order_Received_At) BETWEEN date(?) AND date(?)
            ORDER BY o.Order_Received_At DESC
        """, (start_date, end_date))
        return cursor.fetchall()


def update_customer(customer_id, first_name, last_name, phone_number, email="", address=""):
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE CUSTOMERS SET First_Name = ?, Last_Name = ?, Phone_Number = ?, Email = ?, Address = ? WHERE CustomerID = ?",
            (first_name, last_name, phone_number, email, address, customer_id)
        )
        conn.commit()
        return True


def update_order(order_id, status=None, notes=None):
    from datetime import datetime
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        if status is not None:
            cursor.execute("UPDATE ORDERS SET Order_Status = ? WHERE OrderID = ?", (status, order_id))
            if status == 'Ready':
                cursor.execute("UPDATE ORDERS SET Order_Ready_At = ? WHERE OrderID = ?", (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), order_id))
            if status == 'Released':
                cursor.execute("UPDATE ORDERS SET Order_Released_At = ? WHERE OrderID = ?", (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), order_id))
        if notes is not None:
            cursor.execute("UPDATE ORDERS SET Order_Notes = ? WHERE OrderID = ?", (notes, order_id))
        conn.commit()
        return True

def get_revenue_report_data():
    day_mapping = {
        '1': 'Mon', '2': 'Tue', '3': 'Wed', '4': 'Thu', 
        '5': 'Fri', '6': 'Sat', '0': 'Sun'
    }
    
    results_dict = {day: 0 for day in day_mapping.values()}
    
    query = """
        SELECT 
            strftime('%w', Payment_Date) as day_num,
            SUM(Amount_Paid) as total_revenue
        FROM PAYMENTS
        WHERE Payment_Date >= date('now', 'weekday 0', '-7 days')
        GROUP BY day_num
    """
    
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        raw_data = cursor.fetchall()
        
    for day_num, total in raw_data:
        day_name = day_mapping.get(day_num)
        if day_name:
            results_dict[day_name] = total
            
    ordered_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    ordered_revenue = [results_dict[day] for day in ordered_days]
    
    return ordered_days, ordered_revenue

def get_received_report_data():
    target_hours = ["06", "09", "12", "15", "18", "21"]
    results_dict = {hr: 0 for hr in target_hours}
    
    query = """
        SELECT 
            strftime('%H', Order_Received_At) as order_hour,
            COUNT(OrderID) as order_count
        FROM ORDERS
        WHERE date(Order_Received_At) = date('now')
        GROUP BY order_hour
    """
    
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        raw_data = cursor.fetchall()
        
    for raw_hour, count in raw_data:
        hour_int = int(raw_hour)
        if hour_int < 9: bucket = "06"
        elif hour_int < 12: bucket = "09"
        elif hour_int < 15: bucket = "12"
        elif hour_int < 18: bucket = "15"
        elif hour_int < 21: bucket = "18"
        else: bucket = "21"
        
        results_dict[bucket] += count

    display_mapping = {"06": "6AM", "09": "9AM", "12": "12PM", "15": "3PM", "18": "6PM", "21": "9PM"}
    
    hours_labels = [display_mapping[hr] for hr in target_hours]
    order_counts = [results_dict[hr] for hr in target_hours]
    
    return hours_labels, order_counts

def get_ready_report_data():
    target_hours = ["06", "09", "12", "15", "18", "21"]
    results_dict = {hr: 0 for hr in target_hours}
    
    # Tailored to your exact schema columns: Order_Ready_At and Order_Status
    query = """
        SELECT 
            strftime('%H', Order_Ready_At) as ready_hour,
            COUNT(OrderID) as order_count
        FROM ORDERS
        WHERE Order_Status = 'Ready'
        AND date(Order_Ready_At) = date('now')
        GROUP BY ready_hour
    """
    
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        raw_data = cursor.fetchall()
        
    for raw_hour, count in raw_data:
        if raw_hour is None:
            continue
            
        hour_int = int(raw_hour)
        if hour_int < 9: bucket = "06"
        elif hour_int < 12: bucket = "09"
        elif hour_int < 15: bucket = "12"
        elif hour_int < 18: bucket = "15"
        elif hour_int < 21: bucket = "18"
        else: bucket = "21"
        
        results_dict[bucket] += count

    display_mapping = {"06": "6AM", "09": "9AM", "12": "12PM", "15": "3PM", "18": "6PM", "21": "9PM"}
    
    hours_labels = [display_mapping[hr] for hr in target_hours]
    order_counts = [results_dict[hr] for hr in target_hours]
    
    return hours_labels, order_counts

def get_overdue_report_data():
    # We hop through ORDER_DETAILS (OD) to bridge ORDERS (O) and SERVICES (S)
    query = """
        SELECT 
            S.Service_Type,
            COUNT(O.OrderID) as order_count
        FROM ORDERS O
        JOIN ORDER_DETAILS OD ON O.OrderID = OD.OrderID
        JOIN SERVICES S ON OD.ServiceID = S.ServiceID
        WHERE O.Order_Status = 'Overdue'
        GROUP BY S.Service_Type
    """
    
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        raw_data = cursor.fetchall()
        
    # Unpack into clean lists for your frontend pie chart
    services = [row[0] for row in raw_data]
    overdue_counts = [row[1] for row in raw_data]
    
    return services, overdue_counts

def get_top_services_report_data():
    # Counts occurrences of each service across all order details
    query = """
        SELECT 
            S.Service_Type,
            COUNT(OD.OrderDetailID) as order_count
        FROM ORDER_DETAILS OD
        JOIN SERVICES S ON OD.ServiceID = S.ServiceID
        GROUP BY S.Service_Type
        ORDER BY order_count ASC  -- ASC because ax.barh plots from bottom up
    """
    
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        raw_data = cursor.fetchall()
        
    # Unpack into clean arrays for Matplotlib
    services = [row[0] for row in raw_data]
    counts = [row[1] for row in raw_data]
    
    return services, counts
