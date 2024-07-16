# Author : Mathias Amato
# Date : 16.04.2024
# Project name : Foxync
# Project URL : https://gitlab.ictge.ch/mathias-amt/foxync
# Description : File synchronization tool using Bittorrent

from Client import Client
from User import User
import glob
import os
import hashlib
from pathlib import Path
import platform
import sys
import datetime
import uuid
import re
import socket

from Background.RequestsSender import RequestsSender

from Patch import Patch     
from User import User

import logging
from Logs import Logs

import psutil

# Setting the parent directory to be able to import modules from it
parent_directory = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_directory))

class Parameters:
    """
    The Parameters class follows the Singleton design pattern to ensure only one instance exists.
    It handles the initialization and management of parameters used across the Foxync application.
    """

    _instance = None

    def __new__(cls):
        """Override the __new__ method to implement the Singleton pattern."""
        if cls._instance is None:
            cls._instance = super(Parameters, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """
        Initialize the Parameters instance if it hasn't been initialized yet.
        """
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.mac_address = self.get_mac_address()  # Get the MAC address of the current device

    def init_parameters(self, user):
        """Initialize the parameters used across the program"""
        if not hasattr(self, 'initialized_init_parameters'):
            self.initialized_init_parameters = True

            self.requests_sender = RequestsSender()  # Initialize the request sender

            if user is not None:
                self.current_user = self.get_current_user_obj(user['user_id'])  # Get the connected user object

            self.is_new_client = False
            
            self.current_client = self.get_current_client_obj(logging_in=True)  # Get the connected client object

            if self.is_new_client:
                return
            
            self.clients = self.get_authenticated_clients_of_user_obj(self.current_user.user_id)  # Get all clients of the connected user

            # Convert path strings to Path objects
            self.current_client.torrent_directory = Path(self.current_client.torrent_directory)
            self.current_client.user_directory = Path(self.current_client.user_directory)

            self.keep_seeding = True  # Indicates when a torrent should keep or stop seeding

            self.files_hashes_list_previous = self.get_list_of_files()  # Initialize previous file hashes list

            Logs().write_new_log(logging.INFO, "INITIALIZED PARAMETERS")
        else:
            self.current_user = self.get_current_user_obj(user['user_id'])  # Get the connected user object
            self.current_client = self.get_current_client_obj()  # Get the connected client object
            self.current_client.torrent_directory = Path(self.current_client.torrent_directory)
            self.current_client.user_directory = Path(self.current_client.user_directory)
        
    def get_current_user_obj(self, user_id):
        """Get the user that connected

        Parameters:
            user_id -- The ID of the user"""

        Logs().write_new_log(logging.INFO, "RETRIEVING CURRENT USER")
        user = self.requests_sender.get_current_user(user_id)
        return User(user)

    def get_mac_address(self):
        """Get the MAC address of the connected client"""
        Logs().write_new_log(logging.INFO, "RETRIEVING MAC ADDRESS")
        
        # List of common virtual network interface names to exclude
        virtual_interfaces = ["vboxnet", "vmnet", "veth", "docker", "lo", "virbr"]

        for interface, addrs in psutil.net_if_addrs().items():
            if any(virt in interface for virt in virtual_interfaces):
                continue
            
            for addr in addrs:
                if addr.family == psutil.AF_LINK:
                    mac_address = addr.address
                    if re.match(r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$', mac_address) and mac_address != "00:00:00:00:00:00":
                        return mac_address
        
        # Fallback to the original method if psutil does not find a valid MAC address
        mac_address = ':'.join(re.findall('..', '%012x' % getnode()))
        return mac_address

    def get_ip_address(self):
        """Get the IP address of the connected client"""
        Logs().write_new_log(logging.INFO, "RETRIEVING IP ADDRESS")
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("1.1.1.1", 80))
        ip_address = s.getsockname()[0]
        s.close()
        return ip_address

    def get_current_client_obj(self, logging_in=False):
        """Get the client that is currently used
        
        Parameters:
            logging_in -- Indicates if the user is logging in or not, for updating the ip"""
        Logs().write_new_log(logging.INFO, "RETRIEVING CURRENT CLIENT")

        self.mac_address = self.get_mac_address()

        torrent_directory_relative_path = "src/torrent-dir"
        torrent_directory_absolute_path = os.path.abspath(torrent_directory_relative_path)

        #Get current client of user
        response = self.requests_sender.get_current_client_or_insert_if_not_found(self.current_user.user_id, self.mac_address, torrent_directory_absolute_path)

        if response is None:
            Logs().write_new_log(logging.ERROR, "ERROR WHILE RETRIEVING CLIENT")
            return None

        client_db = response["client"]
        self.is_new_client = response["new_client"]

        tokens = self.requests_sender.get_tokens(client_db["client_id"], client_db["user_id"]) #Get access and refresh tokens

        self.access_token_server = tokens["access_token"]
        self.refresh_token_server = tokens["refresh_token"]

        if client_db is None:
            Logs().write_new_log(logging.ERROR, "ERROR WHILE RETRIEVING CLIENT")
            return None
     
        if self.is_new_client: #If the client has just been added (first time that the user connects to this user)
            from GUI.PopupSelectDir import PopupSelectDir

            popup = PopupSelectDir(client_db['client_id'])  # Create the popup window to set a user directory
            response = self.requests_sender.get_current_client_or_insert_if_not_found(self.current_user.user_id, self.mac_address, torrent_directory_absolute_path)
            client_db = response["client"]

            if client_db is None:
                Logs().write_new_log(logging.ERROR, "ERROR WHILE ADDING CLIENT TO DATABASE")
                return None

        ip_address = self.get_ip_address()

        # Update IP address if needed and user enabled the option
        if ip_address != client_db["ip_address"] and client_db["auto_update_ip_address"] and logging_in:
            Logs().write_new_log(logging.INFO, "AUTO UPDATING IP ADDRESS")
            self.requests_sender.update_client_ip_address(client_db["client_id"], ip_address)
            response = self.requests_sender.get_current_client_or_insert_if_not_found(self.current_user.user_id, self.mac_address, torrent_directory_absolute_path)
            client_db = response["client"]

        client_obj = Client(client_db)
        return client_obj

    def get_authenticated_clients_of_user_obj(self, user_id):
        """Get all connected clients
        
        Parameters:
            user_id -- The ID of the user"""
        Logs().write_new_log(logging.INFO, "RETRIEVING AUTHENTICATED CLIENTS OF CONNECTED USER")
        clients_db = self.requests_sender.get_authenticated_clients_of_user(user_id, self.current_client.client_id)
        return [Client(client_db) for client_db in clients_db]

    def get_list_of_files(self):
        """Get all the files inside the user directory of the client"""
        Logs().write_new_log(logging.INFO, "RETRIEVING LIST OF FILES")

        if self.current_client.user_directory.is_dir() == False:
            return []

        files_hashes_list = []

        # Traverse all files in the user directory
        files = Path(self.current_client.user_directory).rglob('*')
        for file_path in files:
            file_path = str(file_path)
            is_directory = os.path.isdir(file_path)

            if is_directory:  # If the file is a directory
                encoded_file = b''
            else:  # If the file is not a directory
                with open(file_path, 'rb') as file:
                    encoded_file = file.read()

            file_rel_path = os.path.relpath(file_path, self.current_client.user_directory)  # Relative path of the file

            is_directory = int(is_directory == True)  # Convert boolean to int

            # Add file hash information to the list
            files_hashes_list.append(Patch(
                is_dir=is_directory,
                file_rel_path=file_rel_path,
                content_bytes=encoded_file,
                hash_var=0
            ))

        return files_hashes_list

    def python_timestamp_to_sql_datetime(self, timestamp):
        """Convert Python timestamp to SQL datetime
        
        Parameters:
        timestamp (int): The timestamp to convert.
        
        Returns:
        str: The SQL datetime string.
        """
        Logs().write_new_log(logging.INFO, "CONVERTING TIMESTAMP TO DATETIME")
        datetime_string = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        return datetime_string
