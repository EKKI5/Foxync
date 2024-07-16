# Author : Mathias Amato
# Date : 16.04.2024
# Project name : Foxync
# Project URL : https://gitlab.ictge.ch/mathias-amt/foxync
# Description : File synchronization tool using Bittorrent

import sys
import subprocess

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from ui.pyqt.Ui_parameters_window import Ui_parameters_window

from Parameters import Parameters

import re
import os
from pathlib import Path
import hashlib

import logging
from Logs import Logs

class Options:
    # Singleton instance variable
    _instance = None

    # Override __new__ to ensure a single instance (Singleton)
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Options, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # Ensure the instance is initialized only once
        if not hasattr(self, 'initialized'):
            self.initialized = True

            self.parameters = Parameters()
            
            # Import and initialize needed classes

            from Background.BackgroundProcess import BackgroundProcess
            self.background_process = BackgroundProcess()

            from GUI.Main import Main
            self.main_gui = Main()

            from Background.BlockLevelProcess import BlockLevelProcess
            self.block_level_process = BlockLevelProcess()

            self.values_to_edit = {}

            # Initialize the options dialog window
            self.window_foxync_options = QDialog()
            self.ui_options = Ui_parameters_window()  # Load the UI
            self.ui_options.setupUi(self.window_foxync_options)

            # Set the current client data to the options window
            self.set_current_client_data_to_options()
            
            self.setup_events()

            # Mapping UI components to their corresponding keys
            self.key_to_component = {
                "ip_address": self.ui_options.textbox_ip_address,
                "auto_update_ip_address": self.ui_options.checkbox_auto_update_ip_address,
                "name": self.ui_options.textbox_name,
                "user_directory": self.ui_options.textbox_synchronized_directory,
                "is_away": self.ui_options.checkbox_is_away,
                "upload_limit": self.ui_options.spinbox_upload_speed_limit,
                "download_limit": self.ui_options.spinbox_download_speed_limit,
                "interval_in_seconds_check": self.ui_options.spinbox_interval,
                "block_size_in_bytes": self.ui_options.spinbox_block_size,
                "username": self.ui_options.textbox_username,
                "current_password": self.ui_options.textbox_current_password,
                "password": self.ui_options.textbox_new_password,
            }

            self.ui_options.label_wrong.setVisible(False)

            # Show the options dialog window
            self.window_foxync_options.show()
            Logs().write_new_log(logging.INFO, "OPENED OPTIONS PAGE")
        else:
            # If already initialized, only update the client data
            self.set_current_client_data_to_options()
            self.window_foxync_options.show()
            self.values_to_edit = {}
            Logs().write_new_log(logging.INFO, "OPENED OPTIONS PAGE")

    def set_current_client_data_to_options(self):
        """Set the current client data to the options window"""
        current_client = self.parameters.current_client

        current_user = self.parameters.current_user

        # Populate the UI components with current client data
        self.ui_options.textbox_name.setText(current_client.name)
        self.ui_options.textbox_ip_address.setText(current_client.ip_address)
        self.ui_options.textbox_synchronized_directory.setText(str(current_client.user_directory))
        self.ui_options.checkbox_is_away.setChecked(current_client.is_away)
        self.ui_options.checkbox_auto_update_ip_address.setChecked(current_client.auto_update_ip_address)
        self.ui_options.spinbox_upload_speed_limit.setValue(int(current_client.upload_limit / 1000))
        self.ui_options.spinbox_download_speed_limit.setValue(int(current_client.download_limit / 1000))
        self.ui_options.spinbox_interval.setValue(current_client.interval_in_seconds_check)
        self.ui_options.spinbox_block_size.setValue(int(current_user.block_size_in_bytes / 1000))
        self.ui_options.textbox_username.setText(current_user.username)

    def setup_events(self):
        """Setup event listeners for the UI components"""
        self.ui_options.textbox_name.textChanged.connect(lambda: self.change_value('name', self.ui_options.textbox_name.text()))
        self.ui_options.textbox_ip_address.textChanged.connect(lambda: self.change_value('ip_address', self.ui_options.textbox_ip_address.text()))
        self.ui_options.textbox_synchronized_directory.textChanged.connect(lambda: self.change_value('user_directory', self.ui_options.textbox_synchronized_directory.text()))
        self.ui_options.checkbox_is_away.stateChanged.connect(lambda: self.change_value('is_away', self.ui_options.checkbox_is_away.isChecked()))
        self.ui_options.checkbox_auto_update_ip_address.stateChanged.connect(lambda: self.change_value('auto_update_ip_address', self.ui_options.checkbox_auto_update_ip_address.isChecked()))
        self.ui_options.spinbox_upload_speed_limit.valueChanged.connect(lambda: self.change_value('upload_limit', self.ui_options.spinbox_upload_speed_limit.value()))
        self.ui_options.spinbox_download_speed_limit.valueChanged.connect(lambda: self.change_value('download_limit', self.ui_options.spinbox_download_speed_limit.value()))
        self.ui_options.spinbox_interval.valueChanged.connect(lambda: self.change_value('interval_in_seconds_check', self.ui_options.spinbox_interval.value()))
        self.ui_options.spinbox_block_size.valueChanged.connect(lambda: self.change_value('block_size_in_bytes', self.ui_options.spinbox_block_size.value() * 1000))
        self.ui_options.textbox_username.textChanged.connect(lambda: self.change_value('username', self.ui_options.textbox_username.text()))
        self.ui_options.textbox_new_password.textChanged.connect(lambda: self.change_value('password', self.ui_options.textbox_new_password.text()))
        self.ui_options.textbox_current_password.textChanged.connect(lambda: self.change_value('current_password', self.ui_options.textbox_current_password.text()))
        # Connect buttons to their respective handlers
        self.ui_options.button_open_logs.clicked.connect(self.open_logs_folder)
        self.ui_options.button_clear_logs.clicked.connect(self.clear_logs)
        self.ui_options.button_save_changes.clicked.connect(self.save_changes)
        self.ui_options.button_cancel_changes.clicked.connect(self.window_foxync_options.close)
        self.ui_options.button_select.clicked.connect(self.open_file_dialog)
        self.ui_options.buttonicon_update_ip_address.clicked.connect(self.update_ip_address_to_field)

    def open_logs_folder(self):
        """Open the logs folder in the file explorer"""
        Logs().write_new_log(logging.INFO, "OPENED LOGS FOLDER")
        logs_folder_rel_path = "src/logs"
        logs_folder_full_path = os.path.abspath(logs_folder_rel_path)

        # Ensure the folder exists
        if os.path.isdir(logs_folder_rel_path):
            try:
                # Open the folder using the default file explorer
                subprocess.run(['xdg-open', logs_folder_full_path])
                print(f"Opened file explorer at '{logs_folder_full_path}'.")
            except Exception as e:
                print(f"An error occurred: {e}")
        else:
            print(f"The folder '{logs_folder_full_path}' does not exist.")

    def clear_logs(self):
        """Clear the logs"""
        from Logs import Logs

        self.logs = Logs()

        self.logs.clear_logs_files()
        Logs().write_new_log(logging.INFO, "CLEARED LOGS")

    def update_ip_address_to_field(self):
        """Update the IP address field"""
        ip_address = self.parameters.get_ip_address()
        self.ui_options.textbox_ip_address.setText(ip_address)

        Logs().write_new_log(logging.INFO, "IP ADDRESS AUTOMATICALLY SET")

    def open_file_dialog(self):
        """Open the file dialog"""
        Logs().write_new_log(logging.INFO, "OPENED FILE DIALOG FOR CHANGING USER DIRECTORY")
        
        folderpath = QFileDialog.getExistingDirectory(self.window_foxync_options, 'Select Folder', '/home')

        if folderpath != '':
            self.ui_options.textbox_synchronized_directory.setText(folderpath)


    def change_value(self, key, value):
        """Handle changes in UI components and validate inputs"""

        if key == "password" or key == "current_password":
            if self.ui_options.label_wrong.isVisible():
                self.ui_options.label_wrong.setVisible(False)

        if key == "ip_address":
            is_valid = self.check_if_ip_address_is_valid(key, value)
            if not is_valid:
                self.ui_options.textbox_ip_address.setStyleSheet("QLineEdit {border: 1px solid #A31621; border-radius: 5px;}")
                self.ui_options.button_save_changes.setEnabled(False)
                return
            else:
                self.ui_options.textbox_ip_address.setStyleSheet("QLineEdit:focus {border: 1px solid #3daee9; border-radius: 5px;}")
                self.ui_options.button_save_changes.setEnabled(True)

        if key == "user_directory":
            if os.path.isdir(value):
                self.values_to_edit[key] = value
                self.ui_options.textbox_synchronized_directory.setStyleSheet("QLineEdit:focus {border: 1px solid #3daee9; border-radius: 5px;}")
                self.ui_options.button_save_changes.setEnabled(True)
                return
            else:
                self.ui_options.textbox_synchronized_directory.setStyleSheet("QLineEdit {border: 1px solid #A31621; border-radius: 5px;}")
                self.ui_options.button_save_changes.setEnabled(False)
                return

        if isinstance(value, str) and len(value) < 1 and not "password" and not "current_password":
            self.ui_options.button_save_changes.setEnabled(False)
            component = self.key_to_component[key]
            component.setStyleSheet("QLineEdit {border: 1px solid #A31621; border-radius: 5px;}")
        else:
            self.values_to_edit[key] = value
            self.ui_options.button_save_changes.setEnabled(True)
            # Apply the style to the component if the value is valid
            if key in self.key_to_component:
                component = self.key_to_component[key]
                if isinstance(value, str):
                    component.setStyleSheet("QLineEdit:focus {border: 1px solid #3daee9; border-radius: 5px;}")

    def check_if_ip_address_is_valid(self, key, ip_address):
        """Validate IP address format"""
        if re.match(r"^((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\b){4}$", ip_address):
            self.values_to_edit[key] = ip_address

            if not self.ui_options.button_save_changes.isEnabled():
                self.ui_options.button_save_changes.setEnabled(True)
                self.ui_options.textbox_ip_address.setStyleSheet("QLineEdit:focus {border: 1px solid #3daee9; border-radius: 5px;}")

            return True
        else:
            self.ui_options.textbox_ip_address.setStyleSheet("QLineEdit {border: 1px solid #A31621; border-radius: 5px;}")
            self.ui_options.button_save_changes.setEnabled(False)
            return False

    def save_changes(self):
        """Update the modified values in the database"""
        Logs().write_new_log(logging.INFO, "CONFIRMING CHANGES")
        # Define mappings for keys to corresponding tables
        client_keys = {'name', 'ip_address', 'user_directory', 'auto_update_ip_address', 'is_away', 'interval_in_seconds_check', 'upload_limit', 'download_limit'}
        user_keys = {'username', 'password', 'block_size_in_bytes'}

        # Separate values into client and user dictionaries
        client_values = {key: value for key, value in self.values_to_edit.items() if key in client_keys}
        user_values = {key: value for key, value in self.values_to_edit.items() if key in user_keys}

        # If no changes, return
        if not client_values and not user_values:
            return

        from Background.RequestsSender import RequestsSender
        self.requests_sender = RequestsSender()

        # Update t_clients table if needed
        if client_values:
            if "upload_limit" in client_values:
                Logs().write_new_log(logging.INFO, "CHANGED UPLOAD LIMIT")
                client_values["upload_limit"] = client_values["upload_limit"] * 1000

            if "download_limit" in client_values:
                Logs().write_new_log(logging.INFO, "CHANGED DOWNLOAD LIMIT")
                client_values["download_limit"] = client_values["download_limit"] * 1000

               # Recreate scheduler if interval was changed
            if "interval_in_seconds_check" in client_values:
                Logs().write_new_log(logging.INFO, "CHANGED INTERVAL IN SECONDS CHECK")
                self.background_process.recreate_scheduler()

            self.requests_sender.update_options('t_clients', 'client_id', self.parameters.current_client.client_id, client_values)

            self.parameters.current_client = self.parameters.get_current_client_obj()

        # Update t_users table if needed
        if user_values:

            new_password = ""

            if "password" in user_values:
                if len(self.key_to_component["current_password"].text()) < 6:
                    self.ui_options.label_wrong.setText("Please enter your current password")
                    self.ui_options.label_wrong.setVisible(True)
                    self.values_to_edit = {}
                    Logs().write_new_log(logging.INFO, "CURRENT PASSWORD EMPTY")
                    return
                
                if hashlib.sha256(self.key_to_component["current_password"].text().encode()).hexdigest() != self.parameters.current_user.hashed_password:
                    self.ui_options.label_wrong.setText("Your current password is incorrect")
                    self.ui_options.label_wrong.setVisible(True)
                    self.values_to_edit = {}
                    Logs().write_new_log(logging.INFO, "CURRENT PASSWORD INVALID")
                    return

                if len(self.key_to_component["password"].text()) < 6:
                    self.ui_options.label_wrong.setText("New password must have at least 6 characters")
                    self.ui_options.label_wrong.setVisible(True)
                    self.values_to_edit = {}
                    Logs().write_new_log(logging.INFO, "INVALID NEW PASSWORD")
                    return

                new_password = hashlib.sha256(self.key_to_component["password"].text().encode()).hexdigest()

                user_values["password"] = new_password

            self.requests_sender.update_options('t_users', 'user_id', self.parameters.current_user.user_id, user_values)

            self.parameters.current_user = self.parameters.get_current_user_obj(self.parameters.current_user.user_id)

        # Refresh client and user data
        self.parameters.clients = self.parameters.get_authenticated_clients_of_user_obj(self.parameters.current_user.user_id)

        # Reinitialize blocks if user directory was changed
        if "user_directory" in client_values:
            Logs().write_new_log(logging.INFO, "CHANGED USER DIRECTORY")
            self.background_process.files_blocks = self.block_level_process.init_blocks()
            self.background_process.scheduler_changes.shutdown(wait=False)
            self.background_process.show_popup_if_number_of_connected_clients_is_more_than_zero()

        self.parameters.current_client.user_directory = Path(self.parameters.current_client.user_directory)
        self.parameters.current_client.torrent_directory = Path(self.parameters.current_client.torrent_directory)

        if "username" in user_values or "password" in user_values:
            Logs().write_new_log(logging.INFO, "CHANGED USERNAME OR PASSWORD")
            self.main_gui.disconnect()
        
        if "is_away" in client_values and client_values["is_away"] == False:
            Logs().write_new_log(logging.INFO, "CHANGED IS AWAY")
            self.background_process.show_popup_if_number_of_connected_clients_is_more_than_zero()

        self.main_gui.update_list_devices()
        self.main_gui.ui.label_current_name.setText(f"Connected as <span style='font-weight:600'>{self.parameters.current_user.username}</span> on <span style='font-weight:600'>{self.parameters.current_client.name}</span>")

        # Update the main GUI and close options window
        self.main_gui.set_device_state_text()
        self.window_foxync_options.close()