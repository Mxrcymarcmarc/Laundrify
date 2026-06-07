import sqlite3

def init_db():
    tables = [
        #Table initialization for Customer Information
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
        #Table initialization for Services Information
        """
        CREATE TABLE IF NOT EXISTS SERVICES (
            ServiceID INTEGER PRIMARY KEY AUTOINCREMENT,
            Service_Type TEXT NOT NULL,
            Service_Unit_Price INTEGER NOT NULL
        )
        """,
        #Table initialization for Orders Basic Information
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
        """,
        #Table initialization for Orders Information
        """
        CREATE TABLE IF NOT EXISTS ORDER_DETAILS (
            OrderDetailID INTEGER PRIMARY KEY AUTOINCREMENT,
            OrderID INTEGER NOT NULL,
            ServiceID INTEGER NOT NULL,
            Order_Subtotal INTEGER NOT NULL,
            Item_Weight INTEGER NOT NULL,
   
            FOREIGN KEY (OrderID) REFERENCES ORDERS(OrderID),
            FOREIGN KEY (ServiceID) REFERENCES SERVICES(ServiceID)
         
        """,
        #Table initialization for Payment Information
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
            # Loop and execute each one
            for table_query in tables:
                cursor.execute(table_query)
            conn.commit()
        