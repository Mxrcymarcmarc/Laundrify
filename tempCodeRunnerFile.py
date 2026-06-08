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
            Service_Unit_Price INTEGER NOT NULL
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
            Item_Weight INTEGER NOT NULL,
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
            SELECT o.*, c.First_Name, c.Last_Name, c.Phone_Number
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
    """Create a new customer or get existing customer by phone number"""
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT CustomerID FROM CUSTOMERS WHERE Phone_Number = ?", (phone_number,))
        result = cursor.fetchone()
        
        if result:
            return result[0]
        
        cursor.execute(
            "INSERT INTO CUSTOMERS (First_Name, Last_Name, Phone_Number, Email, Address) VALUES (?, ?, ?, ?, ?)",
            (first_name, last_name, phone_number, email, address)
        )
        conn.commit()
        return cursor.lastrowid

def create_order(customer_id, total_price, items, notes=""):
    """Create a new order with items
    
    items: list of dicts with keys 'service', 'quantity', 'subtotal'
    Returns: order_id
    """
    from datetime import datetime
    
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
            
            cursor.execute(
                """INSERT INTO ORDER_DETAILS (OrderID, ServiceID, Order_Subtotal, Item_Weight) 
                   VALUES (?, ?, ?, ?)""",
                (order_id, service_id, item['subtotal'], item.get('quantity', 0))
            )
        
        conn.commit()
        return order_id

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
    # 1. Define your standard time intervals to match the chart
    hours = ["6AM", "9AM", "12PM", "3PM", "6PM", "9PM"]
    # Initialize counts for each time slot to 0
    ready_counts = [0, 0, 0, 0, 0, 0]
    
    query = """
    SELECT strftime('%H', Order_Ready_At) AS hour_digit, COUNT(OrderID)
    FROM ORDERS
    WHERE Status = 'Ready' AND date(Order_Ready_At) = date('now')
    GROUP BY hour_digit
    """
    
    with sqlite3.connect("Laundrify.db") as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()  
        
        for row in rows:
            db_hour = int(row[0])
            count = row[1]
            
            if db_hour < 9: ready_counts[0] += count     
            elif db_hour < 12: ready_counts[1] += count  
            elif db_hour < 15: ready_counts[2] += count  
            elif db_hour < 18: ready_counts[3] += count  
            elif db_hour < 21: ready_counts[4] += count  
            else: ready_counts[5] += count               
            
    return hours, ready_counts

