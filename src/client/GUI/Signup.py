# Author : Mathias Amato
# Date : 22.05.2024
# Project name : Foxync
# Project URL : https://gitlab.ictge.ch/mathias-amt/foxync
# Description : File synchronization tool using Bittorrent

import sys
import hashlib
import platform
import os

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import logging
from Logs import Logs

class Signup:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Signup, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            
            self.signup_window = QDialog()

            from ui.pyqt.Ui_signup_window import Ui_signup_window
            self.ui_signup = Ui_signup_window() #Get the python ui file, then run its setup
            
            self.ui_signup.setupUi(self.signup_window)

            self.signup_window.setStyle(QStyleFactory.create("Fusion"))

            self.signup_window.setModal(True)  # Make the dialog modal

            self.signup_window.closeEvent = self.close_event #Override the close event of Pyqt5

            self.ui_signup.button_create.clicked.connect(self.check_credentials)
            self.ui_signup.button_login.clicked.connect(self.open_login_window)

            self.ui_signup.textbox_username.textChanged.connect(lambda: self.ui_signup.label_wrong.setVisible(False))
            self.ui_signup.textbox_password.textChanged.connect(lambda: self.ui_signup.label_wrong.setVisible(False))
            self.ui_signup.textbox_confirm_password.textChanged.connect(lambda: self.ui_signup.label_wrong.setVisible(False))

            self.ui_signup.label_wrong.setVisible(False)

            self.is_authenticated = False

            self.signup_window.show()

            print("CLIENT SIGNUP INITIALIZED")

        else:
            self.signup_window.show()

    def close_event(self, event):
        """Overrides the closing event of Pyqt5"""
        if not self.is_authenticated:
            exit(0)
    
    def open_login_window(self):
        """Open the login window"""
        from GUI.Login import Login
        Login()

        self.signup_window.hide()

    def open_file_dialog(self):
        """Open the file dialog"""
        folderpath = QFileDialog.getExistingDirectory(self.signup_window, 'Select Folder', '/home')

        if folderpath != '':
            self.ui_signup.textbox_synchronized_directory.setText(folderpath)

    def check_credentials(self):
        """Check if the credentials are correct"""
        username = self.ui_signup.textbox_username.text()

        if len(username) < 1:
            self.ui_signup.label_wrong.setText("Username is invalid")
            self.ui_signup.label_wrong.setVisible(True)
            return

        password = self.ui_signup.textbox_password.text()

        if len(password) < 6:
            self.ui_signup.label_wrong.setText("Password must have at least 6 characters")
            self.ui_signup.label_wrong.setVisible(True)
            return
        
        confirm_password = self.ui_signup.textbox_confirm_password.text()

        if password != confirm_password:
            self.ui_signup.label_wrong.setText("Passwords do not match")
            self.ui_signup.label_wrong.setVisible(True)
            return 

        hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()

        from Background.RequestsSender import RequestsSender
        self.requests_sender = RequestsSender()

        from Parameters import Parameters
        self.parameters = Parameters()

        user = self.requests_sender.signup(username, hashed_password, self.parameters.mac_address)

        self.is_authenticated = True

        self.signup_window.close()

        if self.is_authenticated:
            
            self.parameters.init_parameters(user)

            self.requests_sender.set_user_is_authenticated(1)

            from GUI.Main import Main
            self.main_gui = Main()

            self.main_gui.initialize_ui()

            from Background.BackgroundProcess import BackgroundProcess

            self.background_process = BackgroundProcess()

            self.background_process.recreate_scheduler()
            self.requests_sender.set_scheduler_for_ping()
            self.background_process.show_popup_if_number_of_connected_clients_is_more_than_zero(True)