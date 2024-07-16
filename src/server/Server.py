import socket
import json
import threading
import concurrent.futures
import time
import platform
from apscheduler.schedulers.background import BackgroundScheduler 

from database.MariaDB_Connection_Server import MariaDB_Connection_Server

class Server:

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Server, cls).__new__(cls)
        
        return cls._instance
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.conn = MariaDB_Connection_Server()
            
            print("SERVER INITIALIZED")

    def get_all_clients(self):
        """Query the database to get all clients"""
        
        try:
            cur = self.conn.read_query("SELECT * FROM t_clients")

            return cur.fetchall()

        except Exception as e:
            print(f"Failed to get all clients: {e}")
            return False

    def get_client_with_latest_synchronization(self, ip_address_of_sender):
        """Query the database to get the client with the most recent synchronization

        Arguments:
            ip_address_of_sender -- The IP address of the client connecting, to exclude it for the query
        """

        try:
            cur = self.conn.read_query(f"SELECT * FROM t_clients WHERE is_online != 0 AND ip_address != '{ip_address_of_sender}' ORDER BY last_synchronization DESC LIMIT 1;")
            
            return cur.fetchone()

        except Exception as e:
            print(f"Failed to get client with latest synchronization: {e}")
            return False
    
    def get_current_user(self, user_id):
        """Query the database to get the connected user

        Arguments:
            user_id -- The ID of the user
        """
        
        try:
            query = f"SELECT * FROM t_users WHERE user_id = '{user_id}'"
            cur = self.conn.read_query(query)

            user = cur.fetchone()
            if user is None:
                raise Exception("User not found")
            else:
                return user

        except Exception as e:
            print(f"Failed to get connected user: {e}")
            return False

    def insert_and_get_new_client(self, data):
        """Query the database to insert a new client"""

        try:
            print("TORRENT DIRECTORY: ")
            print(data['torrent_directory'])          
            new_client_id = self.conn.insert_query(f"INSERT INTO t_clients (user_id, name, ip_address, mac_address, torrent_directory) VALUES ({data['user_id']}, '{data['name']}', '{data['ip_address']}', '{data['mac_address']}', '{data['torrent_directory']}')")

            cur = self.conn.read_query(f"SELECT * FROM t_clients WHERE client_id = {new_client_id}")

            client = cur.fetchone()

            return client

        except Exception as e:
            print(f"Failed to insert new client: {e}")
            return False

    def get_current_client(self, user_id, mac_address):
        """Query the database to get the current client

        Arguments:
            mac_address -- The mac address of the client
            user_id -- The id of the user
        """

        try:
            cur = self.conn.read_query(f"SELECT * FROM t_clients WHERE mac_address = '{mac_address}' AND user_id = '{user_id}'")

            client = cur.fetchone()

            return client

        except Exception as e:
            print(f"Failed to get current client: {e}")
            return False

    def get_usernames_authenticated_to_current_client(self, mac_address):
        """Query the database to get all usernames that are authenticated to the current device

        Arguments:
            mac_address -- The mac_address of the client
        """

        try:
            cur = self.conn.read_query(f"""
                SELECT t_users.username
                FROM t_users 
                INNER JOIN t_clients ON t_users.user_id = t_clients.user_id 
                WHERE t_clients.mac_address = '{mac_address}' 
                AND t_clients.user_is_authenticated = 1
                """)

            response = cur.fetchall()
            
            return response

        except Exception as e:
            print(f"Failed to get usernames authenticated to current device: {e}")
            return False
 

    def get_online_and_not_away_clients(self):
        """Query the database to get all clients that are not offline"""

        try:

            cur = self.conn.read_query("SELECT * FROM t_clients WHERE is_online = 1 AND is_away = 0")

            return cur.fetchall()

        except mariadb.Error as e:
            print(f"Failed to get online and away clients: {e}")
            return []

    def get_online_clients(self):
        """Query the database to get all clients that are not offline"""

        try:
            cur = self.conn.read_query("SELECT * FROM t_clients WHERE is_online = 1")
            
            return cur.fetchall()

        except Exception as e:
            print(f"Failed to get online clients: {e}")
            return False

    def get_authenticated_clients_of_user(self, user_id):
        """Query the database to get all clients that are not offline"""

        try:
            cur = self.conn.read_query(f"SELECT * FROM t_clients WHERE user_is_authenticated = 1 AND user_id = {user_id}")

            return cur.fetchall()

        except Exception as e:
            print(f"Failed to get authenticated clients: {e}")
            return False

    def update_last_synchronization_date(self, readable_date, client_id):
        """Query the database to update the last synchronization date of the current client

        Arguments:
            readable_date -- The date in readable format
            mac_address -- The mac address of the client
        """

        try:
            self.conn.update_query(f"UPDATE t_clients SET last_synchronization = '{readable_date}' WHERE client_id = '{client_id}'")
            
            return "200"

        except Exception as e:
            print(f"Failed to update last synchronization date: {e}")
            return False

    def update_client_ip_address(self, client_id, ip_address):
        """Query the database to update the ip address of the current client

        Arguments:
            client_id -- The id of the client
            ip_address -- The ip address of the client
        """

        try:
            self.conn.update_query(f"UPDATE t_clients SET ip_address = '{ip_address}' WHERE client_id = '{client_id}'")
            
            return "200"

        except Exception as e:
            print(f"Failed to update ip address: {e}")

    def set_user_is_authenticated(self, client_id, is_authenticated):
        """Query the database to set the user on the client as authenticated"""
        
        try:
            self.conn.update_query(f"UPDATE t_clients SET user_is_authenticated = {is_authenticated} WHERE client_id = '{client_id}'")
            
            return "200"

        except Exception as e:
            print(f"Failed to update authentication status: {e}")
            return False

    def set_client_status(self, data):
        """Query the database to set the client as online"""

        try:
            self.conn.update_query(f"UPDATE t_clients SET is_online = {data['is_online']}, is_away = {data['is_away']} WHERE client_id = {data['client_id']};")
            
            return "200"

        except Exception as e:
            print(f"Failed to update client status: {e}")
            return False

    def get_number_of_connected_clients(self, user_id):
        """Query the database to get the number of connected clients"""

        try:
            cur = self.conn.read_query(f"SELECT COUNT(name) FROM t_clients WHERE is_online = 1 AND is_away = 0 AND user_id = {user_id}")

            number_of_clients = cur.fetchone()

            return number_of_clients

        except Exception as e:
            print(f"Failed to get number of connected clients: {e}")
            return False

    def login(self, data):
        """Query the database to get the user with the given username and hashed password"

        Arguments:
            data -- The username and hashed password of the user, and if the user used fast login
        """

        try:
            if data["fast_login"]:
                cur = self.conn.read_query(f"SELECT * FROM t_users WHERE BINARY username = '{data['username']}'")
            else:
                cur = self.conn.read_query(f"SELECT * FROM t_users WHERE BINARY username = '{data['username']}' AND password = '{data['hashed_password']}'")

            user = cur.fetchone()
            
            if user is None:
                return 404
            else:
                return user

        except Exception as e:
            print(f"Failed to login: {e}")
            return False

    def logout(self, data):
        """Logout the user from the client"

        Arguments:
            user_id -- The id of the user
        """

        try:
            self.conn.update_query(f"UPDATE t_clients SET user_is_authenticated = 0 WHERE mac_address = '{data['mac_address']}' AND user_id = '{data['user_id']}'")
            
            return "200"

        except Exception as e:
            print(f"Failed to logout: {e}")
            return False

    def signup(self, data):
        """Query the database to get the user with the given username and hashed password"

        Arguments:
            username -- The username of the user
            hashed_password -- The hashed password of the user
        """

        try:
            new_user_id = self.conn.insert_query(f"INSERT INTO t_users (username, password) VALUES ('{data['username']}', '{data['hashed_password']}')")

            cur = self.conn.read_query(f"SELECT * FROM t_users WHERE user_id = {new_user_id}")

            user = cur.fetchone()
            
            if user is None:
                return 404
            else:
                return user

        except Exception as e:
            print(f"Failed to signup: {e}")
            return False

    def update_options(self, data):
        """Query the database to update the options of the current client"""

        try:
            columns = ', '.join([f"{key} = ?" for key in data["new_values"].keys()])
            query = f"UPDATE {data['table']} SET {columns} WHERE {data['id_name']} = ?"
            values = list(data["new_values"].values())
            item_id = data["id_value"]
            values.append(item_id)

            self.conn.update_query(query, values)
            
            return "200"

        except Exception as e:
            print(f"Failed to update options: {e}")
            return False


    def create_thread_for_sending_information_to_single_client(self, ip_of_recipient, data_to_relay):
        """Create new thread for sending data to a single client

        Arguments:
            ip_of_recipient -- The IP address of the client to relay the data to
            data_to_relay -- The data to relay to that client
        """
        thread = threading.Thread(target=self.send_information_to_client, args=(ip_of_recipient, 3125, data_to_relay))
        thread.start()
        thread.join()

    def create_threads_for_sending_information_to_clients(self, clients, ip_of_sender, data_to_relay):
        """Create new threads for sending data to all connected clients
        
        Arguments:
            clients -- The clients to relay the data to
            ip_of_sender -- The IP address of the client that send the data to relay
            data_to_relay -- The data to relay to the other clients
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = []

            for client in clients:
                if client["ip_address"] == ip_of_sender:
                    continue

                future = executor.submit(self.send_information_to_client, client["ip_address"], 3125, data_to_relay)
                futures.append(future)

            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()  # Will raise any exceptions caught by the thread
                except Exception as e:
                    print(f"Exception in thread: {e}")

    def send_information_to_client(self, ip, port, data_to_relay):
        """Send data to clients

        Arguments:
            ip -- The IP address of the client to relay the data to
            port -- The port of the client to relay the data to
            data_to_relay -- The data to relay to that client
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((ip, port))
                s.sendall(json.dumps(data_to_relay).encode('utf-8'))
                print(f"Data sent to {ip}")

        except (socket.error, json.JSONDecodeError) as e:
            print(f"Error sending data to {ip}: {e}")

