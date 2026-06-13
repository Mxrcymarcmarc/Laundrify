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
            -- Order notes are now stored per-service in ORDER_DETAILS.Additional_Notes
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
            Service_Name TEXT DEFAULT '',
            Service_Status TEXT DEFAULT 'Received',
            Service_Payed_At TEXT DEFAULT NULL,
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
        # Ensure ORDER_DETAILS has Service_Name column to persist service display even if SERVICES changes
        try:
            cursor.execute("ALTER TABLE ORDER_DETAILS ADD COLUMN Service_Name TEXT DEFAULT ''")
        except Exception:
            pass
        # Ensure ORDER_DETAILS has Service_Status column
        try:
            cursor.execute("ALTER TABLE ORDER_DETAILS ADD COLUMN Service_Status TEXT DEFAULT 'Received'")
        except Exception:
            pass
        # Ensure ORDER_DETAILS has Service_Payed_At column
        try:
            cursor.execute("ALTER TABLE ORDER_DETAILS ADD COLUMN Service_Payed_At TEXT DEFAULT NULL")
        except Exception:
            pass
        # Ensure ORDER_DETAILS has Additional_Notes column (migrated from ORDERS.Order_Notes)
        try:
            cursor.execute("ALTER TABLE ORDER_DETAILS ADD COLUMN Additional_Notes TEXT NULL")
        except Exception:
            pass
        # Ensure SERVICES has Service_Unit column (kg or pcs)
        try:
            cursor.execute("ALTER TABLE SERVICES ADD COLUMN Service_Unit TEXT DEFAULT 'pcs'")
        except Exception:
            pass
        # Ensure SERVICES has Combo_Key for composite/mixed services
        try:
            cursor.execute("ALTER TABLE SERVICES ADD COLUMN Combo_Key TEXT DEFAULT NULL")
        except Exception:
            pass
        # Ensure ORDERS has Composite_ServiceID to point to a combined service record when order contains multiple services
        try:
            cursor.execute("ALTER TABLE ORDERS ADD COLUMN Composite_ServiceID INTEGER NULL")
        except Exception:
            pass
        conn.commit()

    # Backfill Service_Status and Service_Payed_At for existing order details from ORDERS table
    try:
        with sqlite3.connect("Laundrify.db") as cconn:
            cc = cconn.cursor()
            # If Service_Status is 'Received' (default), backfill with parent order's status
            cc.execute("""
                UPDATE ORDER_DETAILS
                SET Service_Status = (SELECT Order_Status FROM ORDERS WHERE ORDERS.OrderID = ORDER_DETAILS.OrderID)
                WHERE Service_Status = 'Received' AND EXISTS (SELECT 1 FROM ORDERS WHERE ORDERS.OrderID = ORDER_DETAILS.OrderID)
            """)
            # If Service_Payed_At is NULL, backfill with parent order's payment timestamp
            cc.execute("""
                UPDATE ORDER_DETAILS
                SET Service_Payed_At = (SELECT Order_Payed_At FROM ORDERS WHERE ORDERS.OrderID = ORDER_DETAILS.OrderID)
                WHERE Service_Payed_At IS NULL AND EXISTS (SELECT 1 FROM ORDERS WHERE ORDERS.OrderID = ORDER_DETAILS.OrderID AND ORDERS.Order_Payed_At IS NOT NULL)
            """)
            cconn.commit()
            # If ORDERS still had Order_Notes, migrate them into ORDER_DETAILS.Additional_Notes
            try:
                cc.execute("""
                    UPDATE ORDER_DETAILS
                    SET Additional_Notes = (
                        SELECT Order_Notes FROM ORDERS WHERE ORDERS.OrderID = ORDER_DETAILS.OrderID
                    )
                    WHERE EXISTS (
                        SELECT 1 FROM ORDERS WHERE ORDERS.OrderID = ORDER_DETAILS.OrderID AND ORDERS.Order_Notes IS NOT NULL
                    )
                """)
                cconn.commit()
            except Exception:
                # If ORDERS.Order_Notes doesn't exist or migration fails, ignore
                pass
    except Exception:
        pass

    # Backfill Service_Name for existing order details so older orders show service labels
    try:
        with sqlite3.connect("Laundrify.db") as cconn:
            cc = cconn.cursor()
            # Update from SERVICES table where possible
            cc.execute("SELECT DISTINCT ServiceID FROM ORDER_DETAILS WHERE IFNULL(Service_Name,'') = ''")
            sids = [r[0] for r in cc.fetchall()]
            for sid in sids:
                cc.execute("SELECT Service_Type FROM SERVICES WHERE ServiceID = ?", (sid,))
                row = cc.fetchone()
                if row and row[0]:
                    cc.execute("UPDATE ORDER_DETAILS SET Service_Name = ? WHERE ServiceID = ? AND IFNULL(Service_Name,'') = ''", (row[0], sid))
            cconn.commit()
            # For remaining rows without Service_Name, attempt heuristic match by unit and per-item price
            cc.execute("SELECT OrderDetailID, OrderID, Order_Subtotal, Item_Weight, IFNULL(Item_Unit,'pcs') FROM ORDER_DETAILS WHERE IFNULL(Service_Name,'') = ''")
            remaining = cc.fetchall()
            if remaining:
                # load service candidates
                cc.execute("SELECT ServiceID, Service_Type, Service_Unit_Price, IFNULL(Service_Unit,'pcs') FROM SERVICES")
                services = cc.fetchall()
                import re
                for odid, oid, subtotal, iweight, iunit in remaining:
                    try:
                        qty = 0.0
                        # parse numeric quantity from iweight robustly (handles '12x Large', '3 kg', '3 pcs')
                        if isinstance(iweight, (int, float)):
                            qty = float(iweight)
                        else:
                            s = (str(iweight) or '').strip().lower()
                            m = re.search(r"([0-9]+(?:\.[0-9]+)?)", s)
                            if m:
                                try:
                                    qty = float(m.group(1))
                                except Exception:
                                    qty = 0.0
                            else:
                                qty = 0.0
                        if qty <= 0:
                            qty = 1.0
                        per_unit = None
                        if subtotal is not None:
                            try:
                                per_unit = float(subtotal) / qty if qty else float(subtotal)
                            except Exception:
                                per_unit = None
                        best = None
                        best_diff = None
                        for sid2, stype, sprice, sunit in services:
                            if (sunit or 'pcs').lower() != (iunit or 'pcs').lower():
                                continue
                            if per_unit is None:
                                continue
                            diff = abs((sprice or 0) - (per_unit or 0))
                            if best is None or diff < best_diff:
                                best = stype
                                best_diff = diff
                        if best is not None and best_diff is not None and best_diff <= 1.0:
                            cc.execute("UPDATE ORDER_DETAILS SET Service_Name = ? WHERE OrderDetailID = ?", (best, odid))
                    except Exception:
                        continue
                cconn.commit()
                # Additional mapping: for ServiceIDs that no longer exist, compute avg per-unit across their rows and pick closest service
                try:
                    cc.execute("SELECT DISTINCT ServiceID FROM ORDER_DETAILS WHERE IFNULL(Service_Name,'') = ''")
                    missing_sids = [r[0] for r in cc.fetchall()]
                    if missing_sids:
                        cc.execute("SELECT ServiceID, Service_Type, Service_Unit_Price, IFNULL(Service_Unit,'pcs') FROM SERVICES")
                        services_all = cc.fetchall()
                        import re
                        for msid in missing_sids:
                            try:
                                cc.execute("SELECT Order_Subtotal, Item_Weight, IFNULL(Item_Unit,'pcs') FROM ORDER_DETAILS WHERE ServiceID = ?", (msid,))
                                rows_m = cc.fetchall()
                                vals = []
                                unit_guess = None
                                for subtotal, iweight, iunit in rows_m:
                                    unit_guess = (iunit or 'pcs')
                                    qty = 0.0
                                    if isinstance(iweight, (int, float)):
                                        qty = float(iweight)
                                    else:
                                        s = (str(iweight) or '').strip().lower()
                                        m = re.search(r"([0-9]+(?:\.[0-9]+)?)", s)
                                        if m:
                                            try:
                                                qty = float(m.group(1))
                                            except Exception:
                                                qty = 0.0
                                        else:
                                            qty = 0.0
                                    if qty <= 0:
                                        qty = 1.0
                                    try:
                                        if subtotal is not None:
                                            vals.append(float(subtotal)/qty)
                                    except Exception:
                                        continue
                                if not vals:
                                    continue
                                avg = sum(vals)/len(vals)
                                best=None; best_diff=None
                                for sid2, stype, sprice, sunit in services_all:
                                    if (sunit or 'pcs').lower() != (unit_guess or 'pcs').lower():
                                        continue
                                    diff = abs((sprice or 0) - avg)
                                    if best is None or diff < best_diff:
                                        best = stype; best_diff=diff
                                if best is not None:
                                    cc.execute("UPDATE ORDER_DETAILS SET Service_Name=? WHERE ServiceID = ? AND IFNULL(Service_Name,'') = ''", (best, msid))
                            except Exception:
                                continue
                        cconn.commit()
                except Exception:
                    pass
    except Exception:
        pass

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
    """Get unique service names for an order.

    Prefer the persisted Service_Name in ORDER_DETAILS (added for robustness). If not present,
    try multiple fallbacks:
      1. JOIN SERVICES by ServiceID
      2. Heuristic match by unit and per-item price
    Returns a single service name, "Mixed Services", or "Unknown".
    """
    import math
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        # read order detail rows for this order
        cursor.execute("SELECT ServiceID, IFNULL(Service_Name,''), Order_Subtotal, Item_Weight, IFNULL(Item_Unit,'pcs') FROM ORDER_DETAILS WHERE OrderID = ?", (order_id,))
        rows = cursor.fetchall()

        persisted_names = []
        inferred_names = []

        for sid, sname, subtotal, item_weight, item_unit in rows:
            if sname and str(sname).strip():
                persisted_names.append(str(sname).strip())
                continue
            # try direct lookup by ServiceID
            cursor.execute("SELECT Service_Type FROM SERVICES WHERE ServiceID = ?", (sid,))
            r = cursor.fetchone()
            if r and r[0]:
                inferred_names.append(r[0])
                continue
            # heuristic: try to infer by unit and price-per-unit
            try:
                qty = 0.0
                if isinstance(item_weight, (int, float)):
                    qty = float(item_weight)
                else:
                    try:
                        qty = float(str(item_weight))
                    except Exception:
                        qty = 0.0
                if qty <= 0:
                    qty = 1.0
                price_per_unit = float(subtotal) / qty if subtotal is not None else None
                if price_per_unit is not None:
                    # look for exact price match first
                    cursor.execute("SELECT Service_Type FROM SERVICES WHERE Service_Unit = ? AND Service_Unit_Price = ?", (item_unit or 'pcs', int(round(price_per_unit))))
                    rr = cursor.fetchone()
                    if rr and rr[0]:
                        inferred_names.append(rr[0])
                        continue
                    # try approximate match within 1 peso
                    cursor.execute("SELECT Service_Type, Service_Unit_Price FROM SERVICES WHERE Service_Unit = ?", (item_unit or 'pcs',))
                    candidates = cursor.fetchall()
                    best = None
                    best_diff = None
                    for c in candidates:
                        c_name, c_price = c[0], c[1]
                        diff = abs((c_price or 0) - (price_per_unit or 0))
                        if best is None or diff < best_diff:
                            best = c_name
                            best_diff = diff
                    if best is not None and best_diff is not None and best_diff <= 1.0:
                        inferred_names.append(best)
            except Exception:
                pass

        combined = []
        for n in persisted_names + inferred_names:
            if n and n not in combined:
                combined.append(n)

        if len(combined) == 1:
            return combined[0]
        elif len(combined) > 1:
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
    """Restore a curated default set of services and prices.

    This function performs an upsert for defaults: if a service with the same Service_Type
    exists it will be updated (preserving ServiceID); otherwise the service will be inserted.
    """
    defaults = [
        ("Wash, Dry & Fold", 70, 'kg'),
        ("Wash & Dry", 50, 'kg'),
        ("Dry Cleaning", 150, 'pcs'),
        ("Ironing", 20, 'pcs')
    ]
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        for name, price, unit in defaults:
            cursor.execute("SELECT ServiceID FROM SERVICES WHERE Service_Type = ?", (name,))
            row = cursor.fetchone()
            if row and row[0]:
                cursor.execute("UPDATE SERVICES SET Service_Unit_Price = ?, Service_Unit = ? WHERE ServiceID = ?", (int(price), unit, row[0]))
            else:
                cursor.execute("INSERT INTO SERVICES (Service_Type, Service_Unit_Price, Service_Unit) VALUES (?, ?, ?)", (name, int(price), unit))
        conn.commit()
    return True


def get_or_create_combined_service(component_service_ids):
    """Return a deterministic combined ServiceID for the given component service IDs.

    The combination key is formed by sorting numeric ServiceIDs and joining them with '-'.
    If a SERVICES row with that Combo_Key exists its ServiceID is returned. Otherwise a new
    SERVICES row is inserted with Service_Type set to the joined service names and Combo_Key set.
    """
    ids = sorted({int(i) for i in component_service_ids if i is not None})
    if not ids:
        return None
    if len(ids) == 1:
        return ids[0]
    combo_key = 'combo:' + '-'.join(str(i) for i in ids)
    with sqlite3.connect("Laundrify.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT ServiceID FROM SERVICES WHERE Combo_Key = ?", (combo_key,))
        row = cur.fetchone()
        if row and row[0]:
            return row[0]
        # build a human-friendly name using the component service types (in the sorted id order)
        placeholders = ','.join(['?'] * len(ids))
        cur.execute(f"SELECT ServiceID, Service_Type FROM SERVICES WHERE ServiceID IN ({placeholders})", tuple(ids))
        rows = cur.fetchall()
        id_to_name = {r[0]: r[1] for r in rows}
        names = [id_to_name.get(i, f"SVC#{i}") for i in ids]
        combo_name = ' + '.join(names)
        cur.execute("INSERT INTO SERVICES (Service_Type, Service_Unit_Price, Service_Unit, Combo_Key) VALUES (?, ?, ?, ?)", (combo_name, 0, 'mixed', combo_key))
        conn.commit()
        return cur.lastrowid


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
        
        # Cascade to all child services
        cursor.execute(
            "UPDATE ORDER_DETAILS SET Service_Status = ? WHERE OrderID = ?",
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
        
        # Cascade payment status to all child services
        cursor.execute(
            "UPDATE ORDER_DETAILS SET Service_Payed_At = ? WHERE OrderID = ? AND Service_Payed_At IS NULL",
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
        
        # Insert parent order (notes are stored per-service in ORDER_DETAILS)
        cursor.execute(
            """INSERT INTO ORDERS (CustomerID, Order_Status, Order_Total_Price, 
               Order_Received_At) 
               VALUES (?, ?, ?, ?)""",
            (customer_id, "Received", total_price, timestamp)
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

            # Persist the service row and attach any per-item notes to the service line
            per_item_notes = item.get('notes', '') if isinstance(item, dict) else ''
            try:
                cursor.execute(
                    """INSERT INTO ORDER_DETAILS (OrderID, ServiceID, Order_Subtotal, Item_Weight, Item_Unit, Service_Name, Additional_Notes) 
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (order_id, service_id, item['subtotal'], qty_value, unit, item.get('service',''), per_item_notes)
                )
            except Exception:
                # Fallback if Additional_Notes column doesn't exist yet
                cursor.execute(
                    """INSERT INTO ORDER_DETAILS (OrderID, ServiceID, Order_Subtotal, Item_Weight, Item_Unit, Service_Name) 
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (order_id, service_id, item['subtotal'], qty_value, unit, item.get('service',''))
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
            # Cascade status to all child services
            cursor.execute("UPDATE ORDER_DETAILS SET Service_Status = ? WHERE OrderID = ?", (status, order_id))
            if status == 'Ready':
                cursor.execute("UPDATE ORDERS SET Order_Ready_At = ? WHERE OrderID = ?", (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), order_id))
            if status == 'Released':
                cursor.execute("UPDATE ORDERS SET Order_Released_At = ? WHERE OrderID = ?", (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), order_id))
        if notes is not None:
            # Store/update notes on child service rows (per-service notes). Also attempt to update legacy ORDERS.Order_Notes if present.
            try:
                cursor.execute("UPDATE ORDER_DETAILS SET Additional_Notes = ? WHERE OrderID = ?", (notes, order_id))
            except Exception:
                pass
            try:
                cursor.execute("UPDATE ORDERS SET Order_Notes = ? WHERE OrderID = ?", (notes, order_id))
            except Exception:
                # legacy column may not exist; ignore
                pass
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

def get_order_service_rows(order_id):
    """Return a list of service-line dicts for the given order.

    Each dict has:
        service_name  – human-readable service label
        qty_display   – formatted quantity string (e.g. '3 kg' or '2x Small')
        subtotal      – numeric subtotal for that line
        status        – service status ('Received', 'In-Progress', 'Ready', 'Released')
        paid          – payment status ('Yes' or 'No')

    Used by the Option-A parent-child treeview in ViewOrderPage._insert_order_rows.
    """
    import re
    with sqlite3.connect("Laundrify.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """SELECT od.OrderDetailID, od.ServiceID, od.Order_Subtotal,
                      od.Item_Weight, IFNULL(od.Item_Unit, 'pcs') as Item_Unit,
                      IFNULL(od.Service_Name, '') as Service_Name,
                      IFNULL(od.Service_Status, 'Received') as Service_Status,
                      od.Service_Payed_At,
                      IFNULL(od.Additional_Notes, '') as Additional_Notes
               FROM ORDER_DETAILS od
               WHERE od.OrderID = ?
               ORDER BY od.OrderDetailID""",
            (order_id,)
        )
        rows = cursor.fetchall()

    result = []
    for row in rows:
        # Resolve service name
        sname = (row['Service_Name'] or '').strip()
        if not sname:
            try:
                with sqlite3.connect("Laundrify.db") as c2:
                    c2r = c2.execute("SELECT Service_Type FROM SERVICES WHERE ServiceID = ?", (row['ServiceID'],))
                    sr = c2r.fetchone()
                    if sr:
                        sname = sr[0]
            except Exception:
                pass
        if not sname:
            sname = 'Unknown Service'

        # Build qty display
        raw_weight = row['Item_Weight']
        item_unit = (row['Item_Unit'] or 'pcs').lower()
        subtotal = row['Order_Subtotal'] or 0

        if isinstance(raw_weight, (int, float)):
            qty_val = float(raw_weight)
            if item_unit == 'kg':
                qty_display = f"{qty_val:g} kg"
            else:
                qty_display = f"{int(qty_val)} pcs"
        else:
            s = str(raw_weight or '').strip()
            # If it already looks like a formatted string (e.g. '3x Small', '2 kg') keep it
            if re.search(r'[a-zA-Z]', s):
                qty_display = s or '—'
            else:
                m = re.search(r'([0-9]+(?:\.[0-9]+)?)', s)
                if m:
                    qty_val = float(m.group(1))
                    if item_unit == 'kg':
                        qty_display = f"{qty_val:g} kg"
                    else:
                        qty_display = f"{int(qty_val)} pcs"
                else:
                    qty_display = s or '—'

        result.append({
            'service_id': row['ServiceID'],
            'service_name': sname,
            'qty_display': qty_display,
            'subtotal': float(subtotal),
            'status': row['Service_Status'] or 'Received',
            'paid': 'Yes' if row['Service_Payed_At'] else 'No',
            'notes': row['Additional_Notes'] if 'Additional_Notes' in row.keys() else ''
        })
    return result


def is_service_paid(order_id, service_id):
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT Service_Payed_At FROM ORDER_DETAILS WHERE OrderID = ? AND ServiceID = ?", (order_id, service_id))
        res = cursor.fetchone()
        return res and res[0] is not None


def update_service_status(order_id, service_id, new_status):
    from datetime import datetime
    
    # Cannot mark service as Released if it has not been paid
    if new_status == "Released" and not is_service_paid(order_id, service_id):
        raise ValueError("Cannot mark service as Released. This service must be paid first.")

    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE ORDER_DETAILS SET Service_Status = ? WHERE OrderID = ? AND ServiceID = ?", (new_status, order_id, service_id))
        
        # Recalculate parent order status
        cursor.execute("SELECT IFNULL(Service_Status, 'Received') FROM ORDER_DETAILS WHERE OrderID = ?", (order_id,))
        statuses = [r[0] for r in cursor.fetchall()]
        
        if all(s == 'Released' for s in statuses):
            agg_status = 'Released'
        elif all(s in ('Ready', 'Released') for s in statuses):
            agg_status = 'Ready'
        elif any(s in ('In-Progress', 'Ready', 'Released') for s in statuses):
            agg_status = 'In-Progress'
        else:
            agg_status = 'Received'
            
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("UPDATE ORDERS SET Order_Status = ? WHERE OrderID = ?", (agg_status, order_id))
        
        if agg_status == "Ready":
            cursor.execute("SELECT Order_Ready_At FROM ORDERS WHERE OrderID = ?", (order_id,))
            o_ready = cursor.fetchone()
            if not o_ready or not o_ready[0]:
                cursor.execute("UPDATE ORDERS SET Order_Ready_At = ? WHERE OrderID = ?", (timestamp, order_id))
                
        if agg_status == "Released":
            cursor.execute("SELECT Order_Released_At FROM ORDERS WHERE OrderID = ?", (order_id,))
            o_released = cursor.fetchone()
            if not o_released or not o_released[0]:
                cursor.execute("UPDATE ORDERS SET Order_Released_At = ? WHERE OrderID = ?", (timestamp, order_id))
                
        conn.commit()
        return True


def process_service_payment(order_id, service_id, amount_paid):
    from datetime import datetime
    
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT OrderDetailID, Order_Subtotal, IFNULL(Service_Payed_At, '') FROM ORDER_DETAILS WHERE OrderID = ? AND ServiceID = ?", (order_id, service_id))
        row = cursor.fetchone()
        if not row:
            return {
                'success': False,
                'message': 'Service not found'
            }
            
        odid = row[0]
        subtotal = row[1]
        already_paid = row[2] != ''
        
        if already_paid:
            return {
                'success': False,
                'message': 'This service has already been paid.'
            }
            
        if amount_paid < subtotal:
            return {
                'success': False,
                'total_amount': subtotal,
                'paid_amount': amount_paid,
                'short_amount': subtotal - amount_paid,
                'message': f'Insufficient payment. Short by ₱{subtotal - amount_paid:.2f}'
            }
            
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Update service payment status
        cursor.execute("UPDATE ORDER_DETAILS SET Service_Payed_At = ? WHERE OrderDetailID = ?", (timestamp, odid))
        
        # Record payment in PAYMENTS table
        cursor.execute(
            "INSERT INTO PAYMENTS (OrderID, Amount_Paid, Payment_Date) VALUES (?, ?, ?)",
            (order_id, amount_paid, timestamp)
        )
        
        # Check if all services for this order are paid now:
        cursor.execute("SELECT COUNT(*) FROM ORDER_DETAILS WHERE OrderID = ? AND Service_Payed_At IS NULL", (order_id,))
        unpaid_count = cursor.fetchone()[0]
        
        if unpaid_count == 0:
            # Mark parent order as paid
            cursor.execute("UPDATE ORDERS SET Order_Payed_At = ? WHERE OrderID = ?", (timestamp, order_id))
            
        conn.commit()
        
        change = amount_paid - subtotal
        return {
            'success': True,
            'total_amount': subtotal,
            'paid_amount': amount_paid,
            'change': change,
            'message': 'Payment processed successfully'
        }


def get_next_customer_id():
    """Fetches the highest CustomerID from the database and adds 1."""
    conn = sqlite3.connect("Laundrify.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT MAX(CustomerID) FROM CUSTOMERS")
    result = cursor.fetchone()[0]
    
    conn.close()
    
    return (result + 1) if result is not None else 1


def delete_order(order_id):
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ORDERS WHERE OrderID = ?", (order_id,))
        cursor.execute("DELETE FROM ORDER_DETAILS WHERE OrderID = ?", (order_id,))
        cursor.execute("DELETE FROM PAYMENTS WHERE OrderID = ?", (order_id,))
        conn.commit()
        return True


def delete_service_row(order_id, service_id):
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ORDER_DETAILS WHERE OrderID = ? AND ServiceID = ?", (order_id, service_id))
        
        # Check if any services remain for this order
        cursor.execute("SELECT COUNT(*), SUM(Order_Subtotal) FROM ORDER_DETAILS WHERE OrderID = ?", (order_id,))
        count, new_total = cursor.fetchone()
        
        if count == 0:
            # Delete order entirely
            cursor.execute("DELETE FROM ORDERS WHERE OrderID = ?", (order_id,))
            cursor.execute("DELETE FROM PAYMENTS WHERE OrderID = ?", (order_id,))
            conn.commit()
            return True, True  # success, parent order deleted
            
        # Update parent total price
        cursor.execute("UPDATE ORDERS SET Order_Total_Price = ? WHERE OrderID = ?", (new_total or 0, order_id))
        
        # Recalculate status
        cursor.execute("SELECT IFNULL(Service_Status, 'Received') FROM ORDER_DETAILS WHERE OrderID = ?", (order_id,))
        statuses = [r[0] for r in cursor.fetchall()]
        
        if all(s == 'Released' for s in statuses):
            agg_status = 'Released'
        elif all(s in ('Ready', 'Released') for s in statuses):
            agg_status = 'Ready'
        elif any(s in ('In-Progress', 'Ready', 'Released') for s in statuses):
            agg_status = 'In-Progress'
        else:
            agg_status = 'Received'
            
        cursor.execute("UPDATE ORDERS SET Order_Status = ? WHERE OrderID = ?", (agg_status, order_id))
        
        # Recalculate payment status
        cursor.execute("SELECT COUNT(*) FROM ORDER_DETAILS WHERE OrderID = ? AND Service_Payed_At IS NULL", (order_id,))
        unpaid_count = cursor.fetchone()[0]
        if unpaid_count == 0:
            cursor.execute("SELECT Order_Payed_At FROM ORDERS WHERE OrderID = ?", (order_id,))
            p_at = cursor.fetchone()
            if not p_at or not p_at[0]:
                from datetime import datetime
                cursor.execute("UPDATE ORDERS SET Order_Payed_At = ? WHERE OrderID = ?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), order_id))
        else:
            cursor.execute("UPDATE ORDERS SET Order_Payed_At = NULL WHERE OrderID = ?", (order_id,))
            
        conn.commit()
        return True, False  # success, parent order NOT deleted


def update_service_details(order_id, service_id, weight, subtotal, status, paid_val):
    from datetime import datetime
    import re
    
    if status == "Released" and not paid_val:
        raise ValueError("Cannot mark service as Released. This service must be paid first.")

    # Parse numeric weight value and unit from input string robustly
    qty_value = 0.0
    unit = 'pcs'
    if isinstance(weight, (int, float)):
        qty_value = float(weight)
    elif isinstance(weight, str):
        s = weight.strip().lower()
        m = re.match(r"^([0-9]+(?:\.[0-9]+)?)\s*kg", s)
        if m:
            qty_value = float(m.group(1))
            unit = 'kg'
        else:
            m2 = re.match(r"^([0-9]+)\s*(?:x|pcs|pc)?", s)
            if m2:
                qty_value = float(m2.group(1))
                unit = 'pcs'
            else:
                m3 = re.search(r"([0-9]+(?:\.[0-9]+)?)", s)
                if m3:
                    qty_value = float(m3.group(1))
                    unit = 'kg' if '.' in m3.group(1) else 'pcs'
                else:
                    qty_value = 0.0
                    unit = 'pcs'

    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        
        # Determine paid timestamp
        if paid_val:
            cursor.execute("SELECT Service_Payed_At FROM ORDER_DETAILS WHERE OrderID = ? AND ServiceID = ?", (order_id, service_id))
            curr_paid = cursor.fetchone()
            if curr_paid and curr_paid[0]:
                paid_at = curr_paid[0]
            else:
                paid_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else:
            paid_at = None
            
        cursor.execute("""
            UPDATE ORDER_DETAILS
            SET Item_Weight = ?, Item_Unit = ?, Order_Subtotal = ?, Service_Status = ?, Service_Payed_At = ?
            WHERE OrderID = ? AND ServiceID = ?
        """, (qty_value, unit, subtotal, status, paid_at, order_id, service_id))
        
        # Recalculate parent order price
        cursor.execute("SELECT SUM(Order_Subtotal) FROM ORDER_DETAILS WHERE OrderID = ?", (order_id,))
        new_total = cursor.fetchone()[0] or 0
        cursor.execute("UPDATE ORDERS SET Order_Total_Price = ? WHERE OrderID = ?", (new_total, order_id))
        
        # Recalculate parent order status
        cursor.execute("SELECT IFNULL(Service_Status, 'Received') FROM ORDER_DETAILS WHERE OrderID = ?", (order_id,))
        statuses = [r[0] for r in cursor.fetchall()]
        
        if all(s == 'Released' for s in statuses):
            agg_status = 'Released'
        elif all(s in ('Ready', 'Released') for s in statuses):
            agg_status = 'Ready'
        elif any(s in ('In-Progress', 'Ready', 'Released') for s in statuses):
            agg_status = 'In-Progress'
        else:
            agg_status = 'Received'
            
        cursor.execute("UPDATE ORDERS SET Order_Status = ? WHERE OrderID = ?", (agg_status, order_id))
        
        # Recalculate parent order payment status
        cursor.execute("SELECT COUNT(*) FROM ORDER_DETAILS WHERE OrderID = ? AND Service_Payed_At IS NULL", (order_id,))
        unpaid_count = cursor.fetchone()[0]
        if unpaid_count == 0:
            cursor.execute("SELECT Order_Payed_At FROM ORDERS WHERE OrderID = ?", (order_id,))
            p_at = cursor.fetchone()
            if not p_at or not p_at[0]:
                cursor.execute("UPDATE ORDERS SET Order_Payed_At = ? WHERE OrderID = ?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), order_id))
        else:
            cursor.execute("UPDATE ORDERS SET Order_Payed_At = NULL WHERE OrderID = ?", (order_id,))
            
        conn.commit()
        return True
