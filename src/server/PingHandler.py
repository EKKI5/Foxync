import socket
import json
import time
from apscheduler.schedulers.background import BackgroundScheduler 

from database.MariaDB_Connection_Server import MariaDB_Connection_Server
from Server import Server

class PingHandler:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PingHandler, cls).__new__(cls)
        return cls._instance
        
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.conn = MariaDB_Connection_Server()

            self.server = Server()

            online_clients_in_db = {}

            online_clients_in_db = self.server.get_online_clients() #Get online clients from database, useful if the server is restarted

            self.online_clients = {}
            
            for client in online_clients_in_db:
                self.online_clients[client['client_id']] = time.time()

            self.scheduler = BackgroundScheduler() #Check ping every 3 seconds
            self.scheduler.add_job(self.check_pings_time, 'interval', seconds=3)
            self.scheduler.start()
            
            print("PINGHANDLER INITIALIZED")

    def update_ping_time_of_client(self, client_id):
        """Update the ping time of the client and set it online in the database if it was offline"""

        print(f"self.online_clients: {self.online_clients}")

        if client_id not in self.online_clients:
            self.conn.update_query(f"UPDATE t_clients SET is_online = 1 WHERE client_id = '{client_id}'")
        self.online_clients[client_id] = time.time()

    def check_pings_time(self):
        clients_to_remove_from_online_clients = []
        current_time = time.time()

        for client_id, ping_time in self.online_clients.items(): #For each client
            if current_time - ping_time > 9: #If no ping was sent from client for 9 seconds or more, set it offline
                clients_to_remove_from_online_clients.append(client_id)

        if len(clients_to_remove_from_online_clients) > 0:
            self.timeout_ping(clients_to_remove_from_online_clients)

    def timeout_ping(self, clients_to_remove_from_online_clients):
        for client_id in clients_to_remove_from_online_clients:
            self.conn.update_query(f"UPDATE t_clients SET is_online = 0 WHERE client_id = '{client_id}'")
            del self.online_clients[client_id]



