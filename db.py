import sqlite3
import os

class OrderConfig:
    OVERDUE_DAYS = 7  # Simple backend variable configuration (default 7 days)

from datetime import datetime


def load_overdue_days_config():
    """Reads the saved number from config.txt if it exists."""
    try:
        if os.path.exists("config.txt"):
            with open("config.txt", "r") as f: # standard read mode 'r'
                content = f.read().strip()
                if content.isdigit():
                    OrderConfig.OVERDUE_DAYS = int(content)
    except Exception:
        OrderConfig.OVERDUE_DAYS = 7  # Safe fallback if something goes wrong

def update_overdue_days_config(days):
    """Writes the new selection into config.txt so it's remembered."""
    try:
        with open("config.txt", "w") as f: # standard write mode 'w'
            f.write(str(days))
        OrderConfig.OVERDUE_DAYS = int(days)
    except Exception as e:
        print(f"Error saving configuration file: {e}")

# Call the loader function right here so it executes the second the program starts!
load_overdue_days_config()

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
            Large_Unit_Price INTEGER DEFAULT NULL,
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
            Order_Paid_At TEXT NULL,
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
            Service_Paid_At TEXT DEFAULT NULL,
            Additional_Notes,
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
        """
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
        # Ensure ORDER_DETAILS has Service_Paid_At column
        try:
            cursor.execute("ALTER TABLE ORDER_DETAILS ADD COLUMN Service_Paid_At TEXT DEFAULT NULL")
        except Exception:
            pass
        # Ensure ORDER_DETAILS has Additional_Notes column (migrated from ORDERS.Order_Notes)
        try:
            cursor.execute("ALTER TABLE ORDER_DETAILS ADD COLUMN Additional_Notes TEXT NULL")
        except Exception:
            pass
        # Ensure SERVICES has Large_Unit_Price column for pcs services
        try:
            cursor.execute("ALTER TABLE SERVICES ADD COLUMN Large_Unit_Price INTEGER DEFAULT NULL")
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

    # Backfill Service_Status and Service_Paid_At for existing order details from ORDERS table
    try:
        with sqlite3.connect("Laundrify.db") as cconn:
            cc = cconn.cursor()
            # If Service_Status is 'Received' (default), backfill with parent order's status
            cc.execute("""
                UPDATE ORDER_DETAILS
                SET Service_Status = (SELECT Order_Status FROM ORDERS WHERE ORDERS.OrderID = ORDER_DETAILS.OrderID)
                WHERE Service_Status = 'Received' AND EXISTS (SELECT 1 FROM ORDERS WHERE ORDERS.OrderID = ORDER_DETAILS.OrderID)
            """)
            # If Service_Paid_At is NULL, backfill with parent order's payment timestamp
            cc.execute("""
                UPDATE ORDER_DETAILS
                SET Service_Paid_At = (SELECT Order_Paid_At FROM ORDERS WHERE ORDERS.OrderID = ORDER_DETAILS.OrderID)
                WHERE Service_Paid_At IS NULL AND EXISTS (SELECT 1 FROM ORDERS WHERE ORDERS.OrderID = ORDER_DETAILS.OrderID AND ORDERS.Order_Paid_At IS NOT NULL)
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

def check_and_apply_overdue_logic(rows):
    """
    Takes database rows containing Order_Status and Order_Ready_At,
    dynamically checks if a 'Ready' order has exceeded the configured threshold,
    and updates its display status to 'Overdue' on the fly.
    """
    updated_rows = []
    now = datetime.now()
    
    for row in rows:
        # turn row into a mutable dictionary if row_factory is sqlite3.Row
        r = dict(row)
        if r.get('Order_Status') == 'Ready' and r.get('Order_Ready_At'):
            try:
                ready_date = datetime.strptime(r['Order_Ready_At'], '%Y-%m-%d %H:%M:%S')
                days_elapsed = (now - ready_date).days
                if days_elapsed >= OrderConfig.OVERDUE_DAYS:
                    r['Order_Status'] = 'Overdue'
            except Exception:
                pass
        updated_rows.append(r)
    return updated_rows

def get_orders():
    """Fetch all orders with their details"""
    with sqlite3.connect("Laundrify.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT o.OrderID, o.CustomerID, o.Order_Status, o.Order_Total_Price, o.Order_Received_At, o.Order_Ready_At, o.Order_Released_At, o.Order_Paid_At, c.First_Name, c.Last_Name
            FROM ORDERS o
            JOIN CUSTOMERS c ON o.CustomerID = c.CustomerID
            ORDER BY o.Order_Received_At DESC
        """)
        # --- APPLY AUTOMATIC OVERDUE LOGIC HERE ---
        return check_and_apply_overdue_logic(cursor.fetchall())

def get_unpaid_orders():
    """Fetch orders that have not been paid yet"""
    with sqlite3.connect("Laundrify.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT o.OrderID, o.CustomerID, o.Order_Status, o.Order_Total_Price, o.Order_Received_At, o.Order_Ready_At, o.Order_Released_At, o.Order_Paid_At, c.First_Name, c.Last_Name
            FROM ORDERS o
            JOIN CUSTOMERS c ON o.CustomerID = c.CustomerID
            WHERE o.Order_Paid_At IS NULL
            ORDER BY o.Order_Received_At DESC
        """)
        # --- APPLY AUTOMATIC OVERDUE LOGIC HERE ---
        return check_and_apply_overdue_logic(cursor.fetchall())

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
        cursor.execute("SELECT Order_Paid_At FROM ORDERS WHERE OrderID = ?", (order_id,))
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
        try:
            cursor.execute("SELECT ServiceID, Service_Type, Service_Unit_Price, IFNULL(Large_Unit_Price, Service_Unit_Price) as Large_Unit_Price, IFNULL(Service_Unit,'pcs') as Service_Unit FROM SERVICES ORDER BY Service_Type")
        except Exception:
            cursor.execute("SELECT ServiceID, Service_Type, Service_Unit_Price, Service_Unit_Price as Large_Unit_Price, IFNULL(Service_Unit,'pcs') as Service_Unit FROM SERVICES ORDER BY Service_Type")
        return cursor.fetchall()

def get_next_service_id():
    """Return the lowest unused ServiceID, filling any gaps left by deletions."""
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT ServiceID FROM SERVICES ORDER BY ServiceID")
        existing = {row[0] for row in cursor.fetchall()}
    candidate = 1
    while candidate in existing:
        candidate += 1
    return candidate


def add_service(service_type, unit_price, unit='pcs', large_price=None):
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        l_price = int(large_price) if large_price is not None else int(unit_price)
        new_id = get_next_service_id()
        cursor.execute("INSERT INTO SERVICES (ServiceID, Service_Type, Service_Unit_Price, Service_Unit, Large_Unit_Price) VALUES (?, ?, ?, ?, ?)", (new_id, service_type, int(unit_price), unit, l_price))
        conn.commit()
        return new_id

def update_service(service_id, service_type, unit_price, unit='pcs', large_price=None):
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        l_price = int(large_price) if large_price is not None else int(unit_price)
        cursor.execute("UPDATE SERVICES SET Service_Type = ?, Service_Unit_Price = ?, Service_Unit = ?, Large_Unit_Price = ? WHERE ServiceID = ?", (service_type, int(unit_price), unit, l_price, service_id))
        conn.commit()
        return True

def delete_service(service_id):
    """Delete a service by its ID and resequence remaining ServiceIDs to maintain
    a continuous numerical sequence. All foreign key references are updated."""
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM SERVICES WHERE ServiceID = ?", (service_id,))
        if cursor.rowcount == 0:
            conn.commit()
            return False
        # Resequence: shift all ServiceIDs above the deleted one down by 1
        cursor.execute("SELECT ServiceID FROM SERVICES WHERE ServiceID > ? ORDER BY ServiceID", (service_id,))
        ids_to_shift = [row[0] for row in cursor.fetchall()]
        for old_id in ids_to_shift:
            new_id = old_id - 1
            cursor.execute("UPDATE SERVICES SET ServiceID = ? WHERE ServiceID = ?", (new_id, old_id))
            cursor.execute("UPDATE ORDER_DETAILS SET ServiceID = ? WHERE ServiceID = ?", (new_id, old_id))
            try:
                cursor.execute("UPDATE ORDERS SET Composite_ServiceID = ? WHERE Composite_ServiceID = ?", (new_id, old_id))
            except Exception:
                pass
        # Reset the autoincrement counter so it follows the new max
        cursor.execute("SELECT MAX(ServiceID) FROM SERVICES")
        max_row = cursor.fetchone()
        max_id = max_row[0] if max_row and max_row[0] else 0
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='SERVICES'")
        if max_id > 0:
            cursor.execute("INSERT INTO sqlite_sequence (name, seq) VALUES ('SERVICES', ?)", (max_id,))
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
                cursor.execute("UPDATE SERVICES SET Service_Unit_Price = ?, Service_Unit = ?, Large_Unit_Price = ? WHERE ServiceID = ?", (int(price), unit, int(price), row[0]))
            else:
                new_sid = get_next_service_id()
                cursor.execute("INSERT INTO SERVICES (ServiceID, Service_Type, Service_Unit_Price, Large_Unit_Price, Service_Unit) VALUES (?, ?, ?, ?, ?)", (new_sid, name, int(price), int(price), unit))
        conn.commit()
    return True


def get_or_create_combined_service(component_service_ids, cursor=None):
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
    
    def _find_or_create_combo(cur):
        cur.execute("SELECT ServiceID FROM SERVICES WHERE Combo_Key = ?", (combo_key,))
        row = cur.fetchone()
        if row and row[0]:
            return row[0]
        placeholders = ','.join(['?'] * len(ids))
        cur.execute(f"SELECT ServiceID, Service_Type FROM SERVICES WHERE ServiceID IN ({placeholders})", tuple(ids))
        rows = cur.fetchall()
        id_to_name = {r[0]: r[1] for r in rows}
        names = [id_to_name.get(i, f"SVC#{i}") for i in ids]
        combo_name = ' + '.join(names)
        
        cur.execute("SELECT ServiceID FROM SERVICES ORDER BY ServiceID")
        existing = {r[0] for r in cur.fetchall()}
        candidate = 1
        while candidate in existing:
            candidate += 1
        new_combo_id = candidate
        
        cur.execute("INSERT INTO SERVICES (ServiceID, Service_Type, Service_Unit_Price, Service_Unit, Combo_Key) VALUES (?, ?, ?, ?, ?)", (new_combo_id, combo_name, 0, 'mixed', combo_key))
        return new_combo_id

    if cursor is not None:
        return _find_or_create_combo(cursor)
    else:
        with sqlite3.connect("Laundrify.db") as conn:
            cur = conn.cursor()
            res = _find_or_create_combo(cur)
            conn.commit()
            return res




def process_payment(order_id, amount_paid):
    """Process payment for an order
    
    Returns: dict with keys 'success', 'total_amount', 'change', 'message'
    """
    from datetime import datetime
    
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT OrderID FROM ORDERS WHERE OrderID = ?", (order_id,))
        if not cursor.fetchone():
            return {
                'success': False,
                'message': 'Order not found'
            }

        cursor.execute(
            "SELECT SUM(Order_Subtotal) FROM ORDER_DETAILS WHERE OrderID = ? AND Service_Paid_At IS NULL",
            (order_id,)
        )
        due_row = cursor.fetchone()
        due_amount = float(due_row[0]) if due_row and due_row[0] is not None else 0.0

        if due_amount <= 0:
            return {
                'success': False,
                'message': 'Order is already fully paid.'
            }

        if amount_paid < due_amount:
            return {
                'success': False,
                'total_amount': due_amount,
                'paid_amount': amount_paid,
                'short_amount': due_amount - amount_paid,
                'message': f'Insufficient payment. Short by ₱{due_amount - amount_paid:.2f}'
            }

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute(
            "INSERT INTO PAYMENTS (OrderID, Amount_Paid, Payment_Date) VALUES (?, ?, ?)",
            (order_id, amount_paid, timestamp)
        )

        cursor.execute(
            "UPDATE ORDER_DETAILS SET Service_Paid_At = ? WHERE OrderID = ? AND Service_Paid_At IS NULL",
            (timestamp, order_id)
        )

        cursor.execute("SELECT COUNT(*) FROM ORDER_DETAILS WHERE OrderID = ? AND Service_Paid_At IS NULL", (order_id,))
        unpaid_count = cursor.fetchone()[0]
        if unpaid_count == 0:
            cursor.execute("UPDATE ORDERS SET Order_Paid_At = ? WHERE OrderID = ?", (timestamp, order_id))

        conn.commit()

        change = amount_paid - due_amount
        return {
            'success': True,
            'total_amount': due_amount,
            'paid_amount': amount_paid,
            'change': change,
            'message': 'Payment processed successfully'
        }


def get_order_amount_due(order_id):
    """Return the remaining unpaid subtotal for an order."""
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT SUM(Order_Subtotal) FROM ORDER_DETAILS WHERE OrderID = ? AND Service_Paid_At IS NULL",
            (order_id,)
        )
        row = cursor.fetchone()
        return float(row[0]) if row and row[0] is not None else 0.0


def get_next_customer_id():
    """Return the lowest unused CustomerID, filling any gaps left by deletions."""
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT CustomerID FROM CUSTOMERS ORDER BY CustomerID")
        existing = {row[0] for row in cursor.fetchall()}
    candidate = 1
    while candidate in existing:
        candidate += 1
    return candidate


def get_next_order_id():
    """Return the lowest unused OrderID, filling any gaps left by deletions."""
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT OrderID FROM ORDERS ORDER BY OrderID")
        existing = {row[0] for row in cursor.fetchall()}
    candidate = 1
    while candidate in existing:
        candidate += 1
    return candidate


def create_or_get_customer(first_name, last_name, phone_number, email="", address=""):
    """Create or find an existing customer.

    Matching logic:
    1. If phone is provided, reuse an existing customer only when phone and identity match.
    2. Otherwise try exact match on first_name + last_name + address (trimmed).
    3. If no match is found, create a new customer record.
    """
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()

        phone = (phone_number or "").strip()
        fn = (first_name or "").strip()
        ln = (last_name or "").strip()
        addr = (address or "").strip()

        if phone:
            cursor.execute(
                "SELECT CustomerID, First_Name, Last_Name, Address FROM CUSTOMERS WHERE Phone_Number = ?",
                (phone,)
            )
            rows = cursor.fetchall()
            for row in rows:
                existing_id, existing_fn, existing_ln, existing_addr = row
                if (existing_fn or "").strip() == fn and (existing_ln or "").strip() == ln and (existing_addr or "").strip() == addr:
                    return existing_id

        # Try matching by exact name + address when phone not provided or phone did not resolve to the same identity
        if fn or ln or addr:
            cursor.execute(
                "SELECT CustomerID FROM CUSTOMERS WHERE TRIM(First_Name)=? AND TRIM(Last_Name)=? AND TRIM(Address)=?",
                (fn, ln, addr)
            )
            res = cursor.fetchone()
            if res:
                return res[0]

        # create new customer record, reusing the lowest available CustomerID
        new_id = get_next_customer_id()
        cursor.execute(
            "INSERT INTO CUSTOMERS (CustomerID, First_Name, Last_Name, Phone_Number, Email, Address) VALUES (?, ?, ?, ?, ?, ?)",
            (new_id, first_name, last_name, phone, email, address)
        )
        conn.commit()
        return new_id

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
        
        # Insert parent order, reusing the lowest available OrderID (gap-filling)
        new_order_id = get_next_order_id()
        cursor.execute(
            """INSERT INTO ORDERS (OrderID, CustomerID, Order_Status, Order_Total_Price, 
               Order_Received_At) 
               VALUES (?, ?, ?, ?, ?)""",
            (new_order_id, customer_id, "Received", total_price, timestamp)
        )
        order_id = new_order_id
        
        service_ids = []
        for item in items:
            cursor.execute("SELECT ServiceID FROM SERVICES WHERE Service_Type = ?", (item['service'],))
            service_result = cursor.fetchone()
            
            if service_result:
                service_id = service_result[0]
            else:
                new_svc_id = get_next_service_id()
                cursor.execute(
                    "INSERT INTO SERVICES (ServiceID, Service_Type, Service_Unit_Price) VALUES (?, ?, ?)",
                    (new_svc_id, item['service'], 0)
                )
                service_id = new_svc_id
            
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
            service_ids.append(service_id)
            
        if service_ids:
            combo_id = get_or_create_combined_service(service_ids, cursor=cursor)
            if combo_id is not None:
                cursor.execute("UPDATE ORDERS SET Composite_ServiceID = ? WHERE OrderID = ?", (combo_id, order_id))
        
        conn.commit()
        return order_id


def get_paid_orders():
    with sqlite3.connect("Laundrify.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT o.OrderID, o.CustomerID, o.Order_Status, o.Order_Total_Price, 
                   o.Order_Received_At, o.Order_Ready_At, o.Order_Released_At, o.Order_Paid_At,
                   c.First_Name, c.Last_Name
            FROM ORDERS o
            JOIN CUSTOMERS c ON o.CustomerID = c.CustomerID
            WHERE o.Order_Paid_At IS NOT NULL AND o.Order_Released_At IS NULL
            ORDER BY o.Order_Received_At DESC
        """)
        return cursor.fetchall()


def get_archived_orders():
    with sqlite3.connect("Laundrify.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT o.OrderID, o.CustomerID, o.Order_Status, o.Order_Total_Price, 
                   o.Order_Received_At, o.Order_Ready_At, o.Order_Released_At, o.Order_Paid_At,
                   c.First_Name, c.Last_Name
            FROM ORDERS o
            JOIN CUSTOMERS c ON o.CustomerID = c.CustomerID
            WHERE o.Order_Paid_At IS NOT NULL AND o.Order_Released_At IS NOT NULL
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
                   o.Order_Received_At, o.Order_Ready_At, o.Order_Released_At, o.Order_Paid_At,
                   c.First_Name, c.Last_Name, c.Email
            FROM ORDERS o
            JOIN CUSTOMERS c ON o.CustomerID = c.CustomerID
            WHERE o.Order_Paid_At IS NULL
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
                   o.Order_Received_At, o.Order_Ready_At, o.Order_Released_At, o.Order_Paid_At,
                   c.First_Name, c.Last_Name, c.Email
            FROM ORDERS o
            JOIN CUSTOMERS c ON o.CustomerID = c.CustomerID
            WHERE o.Order_Paid_At IS NOT NULL AND o.Order_Released_At IS NULL
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
                   o.Order_Received_At, o.Order_Ready_At, o.Order_Released_At, o.Order_Paid_At,
                   c.First_Name, c.Last_Name, c.Email
            FROM ORDERS o
            JOIN CUSTOMERS c ON o.CustomerID = c.CustomerID
            WHERE o.Order_Paid_At IS NOT NULL AND o.Order_Released_At IS NOT NULL
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


def get_customers():
    """Return list of all customers as sqlite3.Row objects"""
    with sqlite3.connect("Laundrify.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT CustomerID, First_Name, Last_Name, Phone_Number, Email, Address FROM CUSTOMERS ORDER BY First_Name, Last_Name")
        return cursor.fetchall()


def get_customer_details(customer_id):
    with sqlite3.connect("Laundrify.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT CustomerID, First_Name, Last_Name, Phone_Number, Email, Address FROM CUSTOMERS WHERE CustomerID = ?", (customer_id,))
        return cursor.fetchone()


def delete_customer(customer_id):
    """Delete a customer and resequence remaining CustomerIDs to maintain
    a continuous numerical sequence. Foreign key references are updated."""
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM CUSTOMERS WHERE CustomerID = ?", (customer_id,))
        if cursor.rowcount == 0:
            conn.commit()
            return True
        # Resequence: shift all CustomerIDs above the deleted one down by 1
        cursor.execute("SELECT CustomerID FROM CUSTOMERS WHERE CustomerID > ? ORDER BY CustomerID", (customer_id,))
        ids_to_shift = [row[0] for row in cursor.fetchall()]
        for old_id in ids_to_shift:
            new_id = old_id - 1
            cursor.execute("UPDATE CUSTOMERS SET CustomerID = ? WHERE CustomerID = ?", (new_id, old_id))
            cursor.execute("UPDATE ORDERS SET CustomerID = ? WHERE CustomerID = ?", (new_id, old_id))
        # Reset the autoincrement counter
        cursor.execute("SELECT MAX(CustomerID) FROM CUSTOMERS")
        max_row = cursor.fetchone()
        max_id = max_row[0] if max_row and max_row[0] else 0
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='CUSTOMERS'")
        if max_id > 0:
            cursor.execute("INSERT INTO sqlite_sequence (name, seq) VALUES ('CUSTOMERS', ?)", (max_id,))
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
            strftime('%w', o.Order_Paid_At) as day_num,
            SUM(o.Order_Total_Price) as total_revenue
        FROM ORDERS o
        WHERE o.Order_Paid_At IS NOT NULL
          AND date(o.Order_Paid_At) >= date('now', '-6 days')
        GROUP BY day_num
    """
    
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        raw_data = cursor.fetchall()
        
    for day_num, total in raw_data:
        day_name = day_mapping.get(str(day_num))
        if day_name:
            results_dict[day_name] = float(total or 0)
            
    ordered_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    ordered_revenue = [results_dict[day] for day in ordered_days]
    
    return ordered_days, ordered_revenue

def get_received_report_data():
    target_hours = ["06", "09", "12", "15", "18", "21"]
    results_dict = {hr: 0 for hr in target_hours}
    
    today_str = datetime.now().strftime("%Y-%m-%d")
         
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT strftime('%H', Order_Received_At), COUNT(*) 
            FROM ORDERS 
            WHERE Order_Received_At LIKE ?
            GROUP BY strftime('%H', Order_Received_At)
        """, (f"{today_str}%",))
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
    """
    Counts how many orders are dynamically overdue based on the current threshold
    and returns a tuple of (overdue_count, normal_ready_count).
    """
    days_limit = OrderConfig.OVERDUE_DAYS
    
    # Ready orders that crossed the threshold
    query_overdue = """
        SELECT COUNT(*) FROM ORDERS 
        WHERE Order_Status = 'Ready' 
          AND Order_Ready_At <= datetime('now', ?)
    """
    
    # Ready orders still safe within the time window
    query_normal_ready = """
        SELECT COUNT(*) FROM ORDERS 
        WHERE Order_Status = 'Ready' 
          AND Order_Ready_At > datetime('now', ?)
    """
    
    param_string = f"-{days_limit} days"
    
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        
        cursor.execute(query_overdue, (param_string,))
        overdue_count = cursor.fetchone()[0]
        
        cursor.execute(query_normal_ready, (param_string,))
        normal_ready_count = cursor.fetchone()[0]
        
    return overdue_count, normal_ready_count

def get_top_services_report_data():
    import sqlite3
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        
        # Query the Service_Name and count how many times it shows up in order details
        cursor.execute("""
            SELECT Service_Name, COUNT(*) as order_count
            FROM ORDER_DETAILS
            WHERE Service_Name IS NOT NULL AND Service_Name != ''
            GROUP BY Service_Name
            ORDER BY order_count ASC
        """)
        
        rows = cursor.fetchall()
        
        # Break them back out into the two synchronized arrays your frontend needs
        services_list = [str(r[0]) for r in rows]
        counts_list = [int(r[1]) for r in rows]
        
        return services_list, counts_list

def get_top_customers_by_orders():
    query = """
        SELECT 
            C.First_Name || ' ' || C.Last_Name as customer_name,
            COUNT(O.OrderID) as total_orders,
            SUM(O.Order_Total_Price) as total_spent
        FROM ORDERS O
        JOIN CUSTOMERS C ON O.CustomerID = C.CustomerID
        WHERE O.Order_Paid_At IS NOT NULL
        GROUP BY C.CustomerID
        ORDER BY total_orders DESC, total_spent DESC
        LIMIT 10
    """
    
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()

def get_top_customers_by_revenue():
    query = """
        SELECT 
            C.First_Name || ' ' || C.Last_Name as customer_name,
            COUNT(O.OrderID) as total_orders,
            SUM(O.Order_Total_Price) as total_spent
        FROM ORDERS O
        JOIN CUSTOMERS C ON O.CustomerID = C.CustomerID
        WHERE O.Order_Paid_At IS NOT NULL
        GROUP BY C.CustomerID
        ORDER BY total_spent DESC, total_orders DESC
        LIMIT 10
    """
    
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()

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
                      od.Service_Paid_At,
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
            'paid': 'Yes' if row['Service_Paid_At'] else 'No',
            'notes': row['Additional_Notes'] if 'Additional_Notes' in row.keys() else ''
        })
    return result


def is_service_paid(order_id, service_id):
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT Service_Paid_At FROM ORDER_DETAILS WHERE OrderID = ? AND ServiceID = ?", (order_id, service_id))
        res = cursor.fetchone()
        return res and res[0] is not None




def process_service_payment(order_id, service_id, amount_paid):
    from datetime import datetime
    
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT OrderDetailID, Order_Subtotal, IFNULL(Service_Paid_At, '') FROM ORDER_DETAILS WHERE OrderID = ? AND ServiceID = ?", (order_id, service_id))
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
        cursor.execute("UPDATE ORDER_DETAILS SET Service_Paid_At = ? WHERE OrderDetailID = ?", (timestamp, odid))
        
        # Record payment in PAYMENTS table
        cursor.execute(
            "INSERT INTO PAYMENTS (OrderID, Amount_Paid, Payment_Date) VALUES (?, ?, ?)",
            (order_id, amount_paid, timestamp)
        )
        
        # Check if all services for this order are paid now:
        cursor.execute("SELECT COUNT(*) FROM ORDER_DETAILS WHERE OrderID = ? AND Service_Paid_At IS NULL", (order_id,))
        unpaid_count = cursor.fetchone()[0]
        
        if unpaid_count == 0:
            # Mark parent order as paid
            cursor.execute("UPDATE ORDERS SET Order_Paid_At = ? WHERE OrderID = ?", (timestamp, order_id))
            
        conn.commit()
        
        change = amount_paid - subtotal
        return {
            'success': True,
            'total_amount': subtotal,
            'paid_amount': amount_paid,
            'change': change,
            'message': 'Payment processed successfully'
        }


def delete_order(order_id):
    """Delete an order and resequence remaining OrderIDs to maintain
    a continuous numerical sequence. Foreign key references are updated.
    Orphaned customers are also deleted (with their own resequencing)."""
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT CustomerID FROM ORDERS WHERE OrderID = ?", (order_id,))
        row = cursor.fetchone()
        customer_id = row[0] if row else None

        cursor.execute("DELETE FROM ORDERS WHERE OrderID = ?", (order_id,))
        cursor.execute("DELETE FROM ORDER_DETAILS WHERE OrderID = ?", (order_id,))
        cursor.execute("DELETE FROM PAYMENTS WHERE OrderID = ?", (order_id,))

        # Resequence: shift all OrderIDs above the deleted one down by 1
        cursor.execute("SELECT OrderID FROM ORDERS WHERE OrderID > ? ORDER BY OrderID", (order_id,))
        ids_to_shift = [r[0] for r in cursor.fetchall()]
        for old_id in ids_to_shift:
            new_id = old_id - 1
            cursor.execute("UPDATE ORDERS SET OrderID = ? WHERE OrderID = ?", (new_id, old_id))
            cursor.execute("UPDATE ORDER_DETAILS SET OrderID = ? WHERE OrderID = ?", (new_id, old_id))
            cursor.execute("UPDATE PAYMENTS SET OrderID = ? WHERE OrderID = ?", (new_id, old_id))
        # Reset the autoincrement counter
        cursor.execute("SELECT MAX(OrderID) FROM ORDERS")
        max_row = cursor.fetchone()
        max_id = max_row[0] if max_row and max_row[0] else 0
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='ORDERS'")
        if max_id > 0:
            cursor.execute("INSERT INTO sqlite_sequence (name, seq) VALUES ('ORDERS', ?)", (max_id,))

        conn.commit()

    # Delete orphaned customer (with its own resequencing) outside the order connection
    if customer_id:
        with sqlite3.connect("Laundrify.db") as conn2:
            c2 = conn2.cursor()
            c2.execute("SELECT COUNT(*) FROM ORDERS WHERE CustomerID = ?", (customer_id,))
            orders_left = c2.fetchone()[0]
        if orders_left == 0:
            delete_customer(customer_id)

    return True


def delete_service_row(order_id, service_id):
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT CustomerID FROM ORDERS WHERE OrderID = ?", (order_id,))
        row = cursor.fetchone()
        customer_id = row[0] if row else None

        cursor.execute("DELETE FROM ORDER_DETAILS WHERE OrderID = ? AND ServiceID = ?", (order_id, service_id))
        
        # Check if any services remain for this order
        cursor.execute("SELECT COUNT(*), SUM(Order_Subtotal) FROM ORDER_DETAILS WHERE OrderID = ?", (order_id,))
        count, new_total = cursor.fetchone()
        
        if count == 0:
            # Delete order entirely (with resequencing handled by delete_order)
            conn.commit()
            delete_order(order_id)
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
        
        from datetime import datetime
        if agg_status == 'Ready':
            cursor.execute("UPDATE ORDERS SET Order_Ready_At = ? WHERE OrderID = ? AND Order_Ready_At IS NULL", (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), order_id))
        elif agg_status == 'Released':
            cursor.execute("UPDATE ORDERS SET Order_Released_At = ? WHERE OrderID = ? AND Order_Released_At IS NULL", (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), order_id))
        
        # Recalculate payment status
        cursor.execute("SELECT COUNT(*) FROM ORDER_DETAILS WHERE OrderID = ? AND Service_Paid_At IS NULL", (order_id,))
        unpaid_count = cursor.fetchone()[0]
        if unpaid_count == 0:
            cursor.execute("SELECT Order_Paid_At FROM ORDERS WHERE OrderID = ?", (order_id,))
            p_at = cursor.fetchone()
            if not p_at or not p_at[0]:
                from datetime import datetime
                cursor.execute("UPDATE ORDERS SET Order_Paid_At = ? WHERE OrderID = ?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), order_id))
        else:
            cursor.execute("UPDATE ORDERS SET Order_Paid_At = NULL WHERE OrderID = ?", (order_id,))
            
        conn.commit()
        return True, False  # success, parent order NOT deleted


def update_service_details(order_id, service_id, weight, subtotal, status, paid_val, notes=""):
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
            cursor.execute("SELECT Service_Paid_At FROM ORDER_DETAILS WHERE OrderID = ? AND ServiceID = ?", (order_id, service_id))
            curr_paid = cursor.fetchone()
            if curr_paid and curr_paid[0]:
                paid_at = curr_paid[0]
            else:
                paid_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else:
            paid_at = None
            
        cursor.execute("""
            UPDATE ORDER_DETAILS
            SET Item_Weight = ?, Item_Unit = ?, Order_Subtotal = ?, Service_Status = ?, Service_Paid_At = ?, Additional_Notes = ?
            WHERE OrderID = ? AND ServiceID = ?
        """, (qty_value, unit, subtotal, status, paid_at, notes, order_id, service_id))
        
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
        
        if agg_status == 'Ready':
            cursor.execute("UPDATE ORDERS SET Order_Ready_At = ? WHERE OrderID = ? AND Order_Ready_At IS NULL", (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), order_id))
        elif agg_status == 'Released':
            cursor.execute("UPDATE ORDERS SET Order_Released_At = ? WHERE OrderID = ? AND Order_Released_At IS NULL", (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), order_id))
        
        # Recalculate parent order payment status
        cursor.execute("SELECT COUNT(*) FROM ORDER_DETAILS WHERE OrderID = ? AND Service_Paid_At IS NULL", (order_id,))
        unpaid_count = cursor.fetchone()[0]
        if unpaid_count == 0:
            cursor.execute("SELECT Order_Paid_At FROM ORDERS WHERE OrderID = ?", (order_id,))
            p_at = cursor.fetchone()
            if not p_at or not p_at[0]:
                cursor.execute("UPDATE ORDERS SET Order_Paid_At = ? WHERE OrderID = ?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), order_id))
        else:
            cursor.execute("UPDATE ORDERS SET Order_Paid_At = NULL WHERE OrderID = ?", (order_id,))
            
        conn.commit()
        return True
