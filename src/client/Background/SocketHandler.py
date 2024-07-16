from PyQt5.QtCore import QObject, pyqtSignal
import time
import os
import socket
import threading
import hashlib
import json
import bsdiff4
import glob
import sched

from Parameters import Parameters

import sys
from pathlib import Path
parent_directory = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(parent_directory))

import logging
from Logs import Logs

class SocketHandler():
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SocketHandler, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True

            self.parameters = Parameters()  # Initialize Parameters singleton

            # Import and initialize TorrentHandler
            from Background.TorrentHandler import TorrentHandler
            self.torrent_handler = TorrentHandler()

            # Import and initialize BlockLevelProcess
            from Background.BlockLevelProcess import BlockLevelProcess
            self.block_level_process = BlockLevelProcess()

            # Import and initialize the main GUI
            from GUI.Main import Main
            self.main_gui = Main()

            # Create a separate thread for listening for information from the server
            self.listen_for_information_stop_event = threading.Event()
            self.listen_for_information_thread = threading.Thread(target=self.listen_for_information)
            self.listen_for_information_thread.start()

            Logs().write_new_log(logging.INFO, "INITIALIZED CLIENT SOCKET HANDLER")

            print("CLIENT SOCKETHANDLER INITIALIZED")

    def stop_listen_for_information_thread(self):
        """Stop the thread listening for information from the server"""
        self.listen_for_information_stop_event.set()
        self.listen_for_information_thread.join()
        
    def handle_data_received_via_socket(self, socket_connection):
        """Handle the data received via socket connection
        
        Parameters:
            socket_connection -- The socket connection
        """
        try:
            Logs().write_new_log(logging.INFO, "HANDLING RECEIVED DATA VIA SOCKET")
            received_data = []
            while True:
                part_of_data = socket_connection.recv(4096)
                if not part_of_data:
                    break
                received_data.append(part_of_data.decode())

            received_data_json = json.loads(''.join(received_data))

            # Handle the received data based on its content
            info_type = received_data_json.get('info_type')

            if info_type == "block_dict":
                Logs().write_new_log(logging.INFO, "RECEIVED BLOCKS LIST")
                # Compare file blocks received from another client
                self.block_level_process.compare_files_blocks(
                    received_data_json['files_blocks'], received_data_json['client_sender'])

            elif info_type == "complete_seeding":
                Logs().write_new_log(logging.INFO, "RECEIVED COMPLETE SEEDING")
                # Stop seeding torrents
                self.parameters.keep_seeding = False

            elif info_type in {"block", "patch"}:
                Logs().write_new_log(logging.INFO, "RECEIVED MAGNET LINK")
                # Download from magnet link received
                self.torrent_handler.download_from_magnet_link(received_data_json['magnet_link'])

        except Exception as e:
            print(f"Error handling data: {e}")
        finally:
            socket_connection.close()

    def listen_for_information(self):
        """Listen for incoming socket connections and handle the data"""

        Logs().write_new_log(logging.INFO, "RECEIVED DATA VIA SOCKET")

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('0.0.0.0', 3125))
            s.listen(1)
            while not self.listen_for_information_stop_event.is_set():
                s.settimeout(0.2)  # Set a timeout to break out of the loop periodically

                try:
                    socket_connection, addr = s.accept()  # Accept a new connection
                    
                    # Start a new thread to handle the client
                    threading.Thread(target=self.handle_data_received_via_socket, args=(socket_connection,)).start()
                
                except socket.timeout:
                    continue  # Continue listening for connections

                except Exception as e:
                    print(f"Error accepting connection: {e}")
                    break