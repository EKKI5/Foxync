# Author : Mathias Amato
# Date : 16.04.2024
# Project name : Foxync
# Project URL : https://gitlab.ictge.ch/mathias-amt/foxync
# Description : File synchronization tool using Bittorrent

import sys
import os
import time
from pathlib import Path
import threading
from datetime import datetime, timezone

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from apscheduler.schedulers.background import BackgroundScheduler

import logging
from Logs import Logs

parent_directory = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_directory))

from ui.pyqt.Ui_main_window import Ui_main_window
from Parameters import Parameters
from Logs import Logs

class Main:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Main, cls).__new__(cls)

        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.parameters = Parameters()            

    def initialize_ui(self):
        """Initialize the UI components and set up connections"""

        from Background.SocketHandler import SocketHandler
        self.socket_handler = SocketHandler()

        from Background.BackgroundProcess import BackgroundProcess
        self.background_process = BackgroundProcess()

        from Background.RequestsSender import RequestsSender
        self.requests_sender = RequestsSender()

        self.requests_sender.set_client_status(self.parameters.current_client.name, self.parameters.current_client.client_id, 1, self.parameters.current_client.is_away, self.parameters.current_client.user_id)

        self.parameters.current_client.is_online = 1

        self.window_foxync = QMainWindow()
        self.ui = Ui_main_window()  # Get the python UI file, then run its setup
        self.ui.setupUi(self.window_foxync)

        self.window_foxync.closeEvent = self.close_event

        self.update_list_devices()

        self.ui.list_devices.itemSelectionChanged.connect(self.show_infos_of_selected_client)  # Display the information of the selected client
        self.ui.list_devices.setCurrentRow(0)  # Select the first client in the list by default

        self.ui.buttonicon_options.clicked.connect(self.open_options)  # Open options at button click
        self.ui.buttonicon_about.clicked.connect(self.open_about)  # Open about page at button click
        self.ui.buttonicon_logout.clicked.connect(self.disconnect)  # Open about page at button click
        self.ui.buttonicon_switch_account.clicked.connect(self.switch_account)
        self.ui.buttonicon_refresh.clicked.connect(self.update_list_devices)
        
        self.ui.label_current_name.setText(f"Connected as <span style='font-weight:600'>{self.parameters.current_user.username}</span> on <span style='font-weight:600'>{self.parameters.current_client.name}</span>")

        last_sync = self.parameters.current_client.last_synchronization

        if last_sync is not None:
            last_sync = last_sync.replace("GMT", "")

        self.ui.label_last_sync.setText(f"Last synchronization : <span style='font-weight:600'>{last_sync}</span>")

        self.set_device_state_text()

        self.window_foxync.show()

        Logs().write_new_log(logging.INFO, "INITIALIZED UI")

        print("CLIENT GUI INITIALIZED")

    def update_list_devices(self):
        """Update the list of devices"""
        self.ui.list_devices.clear()

        item = None

        self.parameters.clients = self.parameters.get_authenticated_clients_of_user_obj(self.parameters.current_user.user_id)

        for client in self.parameters.clients:  # Display each client of the user in a list widget
            item = QListWidgetItem(client.name)
            item.setData(Qt.UserRole, client.client_id)

            self.ui.list_devices.addItem(item)

        self.ui.list_devices.setCurrentRow(0)

        self.show_infos_of_selected_client()

        Logs().write_new_log(logging.INFO, "REFRESHED LIST OF DEVICES")

    def stop_threads(self):
        """Stop all the threads"""
        self.background_process.scheduler_changes.shutdown(wait=False)

        self.requests_sender.scheduler_ping.shutdown(wait=False)

        self.socket_handler.stop_listen_for_information_thread()

        Logs().write_new_log(logging.INFO, "STOPPED THREADS AND SCHEDULERS")

    def close_event(self, event):
        """Overrides the closing event of Pyqt5
        
            Arguments:
            event -- Closing event
        """
        if hasattr(self, 'options') and hasattr(self.options, 'window_foxync_options'):
            self.options.window_foxync_options.close()
            Logs().write_new_log(logging.INFO, "CLOSED OPTIONS PAGE")

        if hasattr(self, 'about') and hasattr(self.about, 'window_foxync_about'):
            self.about.window_foxync_about.close()
            Logs().write_new_log(logging.INFO, "CLOSED ABOUT PAGE")

        self.stop_threads()

        self.requests_sender.set_client_status(self.parameters.current_client.name, self.parameters.current_client.client_id, 0, self.parameters.current_client.is_away, self.parameters.current_client.user_id)

        Logs().write_new_log(logging.INFO, "CLOSED APPLICATION")

        event.accept()
    
    def open_options(self):
        """Initialize the options window"""
        from GUI.Options import Options
        self.options = Options()

    def open_about(self):
        """Initialize the about window"""
        from GUI.About import About
        self.about = About()

    def set_device_state_text(self):
        """Set the text of the device state label"""
        device_status_name = self.get_corresponding_state_name_from_value(self.parameters.current_client)

        # Set the text color depending on the status
        color_dict = {"Offline": "red", "Online": "#71B340", "Away": "#2191FB"}
        text_color = color_dict.get(device_status_name)

        self.ui.label_state_device.setText(f"<span style='font-weight:600; color: {text_color};'>{device_status_name}</span>")

        Logs().write_new_log(logging.INFO, f"DEVICE STATE SET TO: {device_status_name.upper()}")

    def get_corresponding_state_name_from_value(self, client):
        """Get the corresponding state name from the device status value"""
        if client.is_away:
            return "Away"

        if not client.is_online:
            return "Offline"

        return "Online"

    def show_infos_of_selected_client(self):
        """Show the right data corresponding to the selected client"""
        item = self.ui.list_devices.currentItem()

        client = next((client for client in self.parameters.clients if client.client_id == item.data(Qt.UserRole)), None)

        if client is not None:
            device_status = self.get_corresponding_state_name_from_value(client)

            last_sync = client.last_synchronization
            if last_sync is not None:
                last_sync = last_sync.replace("GMT", "")    
            
            device_info = (
                f'<span style=" font-size:14pt; font-weight:600;">Name : </span><br><span style=" font-size:14pt;">{client.name}</span><br><br>'
                f'<span style=" font-size:14pt; font-weight:600;">MAC : </span><br><span style=" font-size:14pt;">{client.mac_address}</span><br><br>'
                f'<span style=" font-size:14pt; font-weight:600;">IP : </span><br><span style=" font-size:14pt;">{client.ip_address}</span><br><br>'
                f'<span style=" font-size:14pt; font-weight:600;">Status : </span><br><span style=" font-size:14pt;">{device_status}</span><br><br>'
                f'<span style=" font-size:14pt; font-weight:600;">Last synchronization date : </span><br><span style=" font-size:14pt;">{last_sync}</span><br><br>'
            )

            self.ui.label_device_infos.setText(device_info)
        else:
            Logs().write_new_log(logging.ERROR, "CLIENT NOT FOUND")
            self.ui.label_device_infos.setText("Client not found.")

    def update_last_synchronization_date(self):
        """Update the date of the last synchronization of the current client"""
        readable_date = self.parameters.python_timestamp_to_sql_datetime(time.time())

        self.requests_sender.update_last_synchronization_date(readable_date, self.parameters.current_client.client_id)
        self.ui.label_last_sync.setText(f"Last synchronization : <span style='font-weight:600'>{readable_date}</span>")

        self.parameters.current_client.last_synchronization = readable_date
        self.parameters.clients = self.parameters.get_authenticated_clients_of_user_obj(self.parameters.current_user.user_id)  # Update clients list

        Logs().write_new_log(logging.INFO, "LAST SYNCHRONIZATION DATE UPDATED")
    def switch_account(self):
        """Switch the current account"""

        Logs().write_new_log(logging.INFO, "SWITCHING ACCOUNT")

        self.socket_handler.stop_listen_for_information_thread()

        from GUI.Login import Login
        self.login_window = Login()

    def disconnect(self):
        """Disconnect the current client"""
        self.requests_sender.logout(self.parameters.current_client.mac_address, self.parameters.current_user.user_id)
        
        self.socket_handler.stop_listen_for_information_thread()
        
        self.window_foxync.close()

        from GUI.Login import Login
        self.login_window = Login()

        Logs().write_new_log(logging.INFO, "DISCONNECTED")