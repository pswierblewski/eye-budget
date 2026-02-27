from abc import ABC
import os

import psycopg2


class EyeBudgetDbContext(ABC):
    def __init__(self):
        self.conn = None
        self.connect_db()
        
    def connect_db(self):
        try:
            self.conn = psycopg2.connect(
                host=os.getenv("POSTGRESQL_HOST"),
                port=os.getenv("POSTGRESQL_PORT"),
                dbname=os.getenv("POSTGRESQL_DB"),
                user=os.getenv("POSTGRESQL_USER"),
                password=os.getenv("POSTGRESQL_PASSWORD")
            )
            print("Database connection established.")
            return self.conn
        except Exception as e:
            print("Failed to connect to database:", e)
    
    def dispose(self):
        if self.conn:
            self.conn.close()
            print("Database connection closed.")
        else:
            print("No database connection to close.")