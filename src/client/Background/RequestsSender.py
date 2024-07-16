# Author : Mathias Amato
# Date : 16.04.2024
# Project name : Foxync
# Project URL : https://gitlab.ictge.ch/mathias-amt/foxync
# Description : File synchronization tool using Bittorrent

import requests
import urllib.parse
import json
import platform

from pathlib import Path
import sys

import logging
from Logs import Logs

from apscheduler.schedulers.background import BackgroundScheduler

# Setting the parent directory to be able to import modules from it
parent_directory = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(parent_directory))

from inc.server_info_inc import Servers_Info

class RequestsSender:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RequestsSender, cls).__new__(cls)

        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True

            requests.packages.urllib3.disable_warnings() 

            self.cert_path = "src/client/ssl/school/cert.pem"
            
            from Parameters import Parameters
            self.parameters = Parameters()

            from GUI.Main import Main
            self.main_gui = Main()
            
            self.scheduler_ping = BackgroundScheduler()

            Logs().write_new_log(logging.INFO, "INITIALIZED CLIENT REQUESTSSENDER")

            print("CLIENT REQUESTSSENDER INITIALIZED")

    def set_scheduler_for_ping(self):
        """Set the scheduler to send a ping message to the server every 3 seconds"""

        Logs().write_new_log(logging.INFO, "SETTING SCHEDULER FOR REGULAR PINGS")
        
        if self.scheduler_ping.running:
            self.scheduler_ping.shutdown(wait=False)
        
        self.scheduler_ping = BackgroundScheduler()

        if self.scheduler_ping.get_job("scheduler_ping"):
            self.scheduler_ping.remove_job("scheduler_ping")

        from Background.BackgroundProcess import BackgroundProcess
        self.background_process = BackgroundProcess()

        self.scheduler_ping.add_job(self.send_ping, 'interval', seconds=3, id="scheduler_ping")
        
        self.scheduler_ping.start()

    def send_post_request(self, url, data, success_message, error_message, auth = True, refresh = False):
        """Helper function to send a POST request and log the result."""
        try:
            if auth:
                if refresh:
                    Logs().write_new_log(logging.INFO, "REFRESHING ACCESS TOKEN")
                    headers = {"Authorization": f"Bearer {self.parameters.refresh_token_server}"}
                        
                else:
                    headers = {"Authorization": f"Bearer {self.parameters.access_token_server}"}
                    
                response = requests.post(url, json=data, headers=headers,  verify=False)
            else:
                response = requests.post(url, json=data, verify=False)

            if response.status_code == 401:
                self.refresh_access_token()

            return response

        except requests.exceptions.RequestException as e:
            print(f"{error_message}: {str(e)}")

            return 400
    
    def send_get_request(self, url, success_message, error_message, auth = True):
        """Helper function to send a GET request and log the result."""
        try:
            if auth:
                headers = {"Authorization": f"Bearer {self.parameters.access_token_server}"}
                response = requests.get(url, headers=headers, verify=False)

            else:
                response = requests.get(url, verify=False)

            if response.status_code == 200:
                response_content = response.json()

                return response_content
            
            if response.status_code == 401:
                self.refresh_access_token()

            else:
                print(f"{error_message}: {response.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"{error_message}: {str(e)}")
            return False

    def refresh_access_token(self):
        """Refresh the access token"""
        try:
            print("Refreshing access token...")
            response = self.send_post_request(
                f'https://{Servers_Info.SERVER_IP.value}:{Servers_Info.SERVER_PORT.value}/refresh_token', 
                {}, 
                "Successfully refreshed server token", 
                "Error while refreshing token", 
                auth=True, 
                refresh=True
            )

            if response is not None:
                self.parameters.access_token_server = response.json()["access_token_server"]

        except Exception as e:
            print(f"Unexpected error while refreshing token: {str(e)}")

    def send_ping(self):
        """Send a ping message to the server"""
        return_code = 0
        
        try:
            response = self.send_post_request(f'https://{Servers_Info.SERVER_IP.value}:{Servers_Info.SERVER_PORT.value}/ping', {"client_id": self.parameters.current_client.client_id}, "Successfully sent ping to server", "Error while calling ping")

            if response is not None:
                return_code = response.status_code
            else:
                return_code = 400

        except Exception as e:
            print(f"Error while calling ping: {str(e)}")
            return_code = 400

        finally:
            if return_code != 200 and return_code != 401:
                self.parameters.current_client.is_online = 0
                self.main_gui.set_device_state_text()

            if return_code == 200 and self.parameters.current_client.is_online == 0:
                self.parameters.current_client.is_online = 1
                self.main_gui.set_device_state_text()
                self.background_process.show_popup_if_number_of_connected_clients_is_more_than_zero()

    def get_authenticated_clients_of_user(self, user_id, client_id):
        """Query the database to get all clients that are not offline"""

        return self.send_get_request(f"https://{Servers_Info.SERVER_IP.value}:{Servers_Info.SERVER_PORT.value}/get_authenticated_clients_of_user?user_id={user_id}&client_id={client_id}",  
                                     "Successfully retrieved authenticated clients", 
                                     "Error while retrieving authenticated clients")

    def get_current_user(self, user_id):
        """Get the current user"""

        return self.send_get_request(f'https://{Servers_Info.SERVER_IP.value}:{Servers_Info.SERVER_PORT.value}/get_current_user?user_id={user_id}', 
                                     "Successfully received current user data from server", 
                                     "Error while calling get_current_user", False)

    def get_current_client_or_insert_if_not_found(self, user_id, mac_address, torrent_directory = None):
        """Get the current client or insert it if it doesn't exist"""

        data = {'user_id': user_id, 'name': platform.node(), 'ip_address': 0, 'mac_address': mac_address}

        if torrent_directory is not None:
            data['torrent_directory'] = torrent_directory

        response = self.send_post_request(f'https://{Servers_Info.SERVER_IP.value}:{Servers_Info.SERVER_PORT.value}/get_current_client_or_insert_if_not_found', data, 
                               "Successfully sent data to /get_current_client_or_insert_if_not_found endpoint of server", 
                               "Error while calling /get_current_client_or_insert_if_not_found", False)

        response_content = response.json()
        
        return response_content

    def get_tokens(self, client_id, user_id):
        """Get the access and refresh tokens from the server"""

        response = self.send_get_request(f'https://{Servers_Info.SERVER_IP.value}:{Servers_Info.SERVER_PORT.value}/get_tokens?client_id={client_id}&user_id={user_id}', 
                                     "Successfully retrieved tokens from server", 
                                     "Error while retrieving tokens", False)

        return response

    def set_client_status(self, name, client_id, is_online, is_away, user_id):
        """Update the current client's status"""

        data = {'client_id': client_id, 'is_online': is_online, 'is_away': is_away}

        self.send_post_request(f'https://{Servers_Info.SERVER_IP.value}:{Servers_Info.SERVER_PORT.value}/set_client_status', data, 
                               "Successfully sent data to /set_client_status endpoint of server", 
                               "Error while calling /set_client_status")

    def set_user_is_authenticated(self, is_authenticated):
        """Update the current user's authentication status"""
        
        data = {'client_id': self.parameters.current_client.client_id, 'is_authenticated': is_authenticated}

        self.send_post_request(f'https://{Servers_Info.SERVER_IP.value}:{Servers_Info.SERVER_PORT.value}/set_user_is_authenticated', data, 
                               "Successfully sent data to /set_user_is_authenticated endpoint of server", 
                               "Error while calling /set_user_is_authenticated")

    def update_last_synchronization_date(self, readable_date, client_id):
        """Update the current client's last synchronization date"""

        data = {'readable_date': readable_date, 'client_id': client_id}

        self.send_post_request(f'https://{Servers_Info.SERVER_IP.value}:{Servers_Info.SERVER_PORT.value}/update_last_synchronization_date', data, 
                               "Successfully sent data to /update_last_synchronization_date endpoint of server", 
                               "Error while calling /update_last_synchronization_date")

    def update_options(self, table, id_name, id_value, new_values):
        """Update the options of the current client or user"""

        data = {'table': table, 'id_name': id_name, 'id_value': id_value, 'new_values': new_values}

        self.send_post_request(f'https://{Servers_Info.SERVER_IP.value}:{Servers_Info.SERVER_PORT.value}/update_options', data,
                               "Successfully sent data to /update_options endpoint of server",
                               "Error while calling /update_options")

    def update_client_ip_address(self, client_id, ip_address):
        """Update the current client's IP address"""

        data = {'client_id': client_id, 'ip_address': ip_address}

        self.send_post_request(f'https://{Servers_Info.SERVER_IP.value}:{Servers_Info.SERVER_PORT.value}/update_client_ip_address', data, 
                               "Successfully sent data to /update_client_ip_address endpoint of server", 
                               "Error while calling /update_client_ip_address")

    def get_usernames_authenticated_to_current_client(self, mac_address):
        """Get the users authenticated to the current client"""
        response_content = self.send_get_request(f'https://{Servers_Info.SERVER_IP.value}:{Servers_Info.SERVER_PORT.value}/get_usernames_authenticated_to_current_client?mac_address={mac_address}', 
                               "Successfully sent data to /get_usernames_authenticated_to_current_client endpoint of server", 
                               "Error while calling /get_usernames_authenticated_to_current_client", False)

        return response_content

    def get_number_of_connected_clients(self, user_id):
        """Get the number of clients connected to the server"""
        number_of_clients = self.send_get_request(f'https://{Servers_Info.SERVER_IP.value}:{Servers_Info.SERVER_PORT.value}/get_number_of_connected_clients?user_id={user_id}', 
                                     "Successfully sent data to /get_number_of_connected_clients endpoint of server", 
                                     "Error while calling /get_number_of_connected_clients")
        
        number_of_clients = number_of_clients.get('COUNT(name)')

        return number_of_clients

    def send_to_server_magnet_link_with_patches(self, info_type, magnet_link):
        """Send a generated magnet link referencing a torrent with patches to the server"""

        current_client_json = self.parameters.current_client.dict_to_json()

        data = {'info_type': info_type, 'magnet_link': magnet_link, 'client_sender': current_client_json}

        self.send_post_request(f'https://{Servers_Info.SERVER_IP.value}:{Servers_Info.SERVER_PORT.value}/relay_magnet_link', data, 
                               "Successfully sent data to /relay_magnet_link endpoint of server", 
                               "Error while calling /relay_magnet_link")

    def send_to_server_magnet_link_with_blocks(self, info_type, magnet_link, connecting_client):
        """Send a generated magnet link referencing a torrent with blocks to the server"""

        data = {'info_type': info_type, 'magnet_link': magnet_link, 'connecting_client': connecting_client}

        self.send_post_request(f'https://{Servers_Info.SERVER_IP.value}:{Servers_Info.SERVER_PORT.value}/relay_magnet_link', data, 
                               "Successfully sent data to /relay_magnet_link endpoint of server", 
                               "Error while calling /relay_magnet_link")

    def login(self, username, hashed_password, is_fast_login = False):
        """Send a list of files and their blocks to the server when client is starting"""

        data = {'username': username, 'hashed_password': hashed_password, 'fast_login': is_fast_login}
        
        response = self.send_post_request(f'https://{Servers_Info.SERVER_IP.value}:{Servers_Info.SERVER_PORT.value}/login', data, 
                               "Successfully sent data to /login endpoint of server", 
                               "Error while calling /login", False)

        response_content = response.json()

        return response_content

    def logout(self, mac_address, user_id):
        """Send a list of files and their blocks to the server when client is starting"""

        data = {'mac_address': mac_address, 'user_id': user_id}
        
        self.send_post_request(f'https://{Servers_Info.SERVER_IP.value}:{Servers_Info.SERVER_PORT.value}/logout', data, 
                               "Successfully sent data to /logout endpoint of server", 
                               "Error while calling /logout")

    def signup(self, username, hashed_password, mac_address):
        """Create new account"""

        data = {'username': username, 'hashed_password': hashed_password, 'mac_address': mac_address}
        
        response = self.send_post_request(f'https://{Servers_Info.SERVER_IP.value}:{Servers_Info.SERVER_PORT.value}/signup', data, 
                               "Successfully sent data to /signup endpoint of server", 
                               "Error while calling /signup", False)
        
        response_content = response.json()

        return response_content
    def send_to_server_blocks(self, files_blocks):
        """Send a list of files and their blocks to the server when client is starting"""

        current_client_json = self.parameters.current_client.dict_to_json()

        files_blocks_json = {}

        for key in files_blocks:
            files_blocks_json[key] = []
            for i in range(len(files_blocks[key])):
                files_blocks_json[key].append(files_blocks[key][i].to_json())

        data = {'files_blocks': files_blocks_json, 'client_sender': current_client_json}
        
        self.send_post_request(f'https://{Servers_Info.SERVER_IP.value}:{Servers_Info.SERVER_PORT.value}/relay_blocks', data, 
                               "Successfully sent data to /relay_blocks endpoint of server", 
                               "Error while calling /relay_blocks")

    def send_to_tracker_torrent_completion(self, info_hash):
        """Send a message to the tracker to tell that the downloading of the torrent was completed"""
        
        url_encoded_info_hash = urllib.parse.quote(str(info_hash))

        data = {'info_hash': url_encoded_info_hash}
        
        self.send_get_request(f'http://{Servers_Info.TRACKER_IP.value}:{Servers_Info.TRACKER_PORT.value}/complete?info_hash={url_encoded_info_hash}', 
                               "Successfully sent data to /complete endpoint of server", 
                               "Error while calling /complete")