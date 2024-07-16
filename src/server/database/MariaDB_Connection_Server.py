import mariadb
from pathlib import Path
import sys

from database.db_connection_info_inc import DB_Connection_Info
class MariaDB_Connection_Server():
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MariaDB_Connection_Server, cls).__new__(cls)
        
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            
            self.conn = mariadb.connect(
                user=DB_Connection_Info.USERNAME.value,
                password=DB_Connection_Info.PASSWORD.value,
                host=DB_Connection_Info.HOST.value,
                port=DB_Connection_Info.PORT.value,
                database=DB_Connection_Info.DATABASE.value
            )

    def read_query(self, query):
        """ Execute the query and return the cursor """

        cur = self.conn.cursor(dictionary=True)
        cur.execute(query)
        self.conn.commit()

        return cur

    def update_query(self, query, values=None):
        cur = self.conn.cursor(dictionary=True)

        if values:
            cur.execute(query, values)
        else:
            cur.execute(query)

        self.conn.commit()

    def insert_query(self, query):
        cur = self.conn.cursor(dictionary=True)
        cur.execute(query)
        self.conn.commit()

        return cur.lastrowid