# Author : Mathias Amato
# Date : 22.05.2024
# Project name : Foxync
# Project URL : https://gitlab.ictge.ch/mathias-amt/foxync
# Description : File synchronization tool using Bittorrent

import sys
import hashlib
import platform
import time
import logging
from Logs import Logs

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from Parameters import Parameters
from Background.RequestsSender import RequestsSender
from Background.BackgroundProcess import BackgroundProcess

class Login:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Login, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True

            self.login_window = QDialog()

            from ui.pyqt.Ui_login_window import Ui_login_window
            self.ui_login = Ui_login_window() #Get the python ui file, then run its setup
            
            self.ui_login.setupUi(self.login_window)

            self.login_window.setStyle(QStyleFactory.create("Fusion"))

            self.login_window.setModal(True)  # Make the dialog modal

            self.login_window.closeEvent = self.close_event #Override the close event of Pyqt5

            self.init_login()

            print("CLIENT LOGIN INITIALIZED")

        else:
            self.set_list_of_users()

            self.ui_login.textbox_username.clear()
            self.ui_login.textbox_password.clear()
            self.ui_login.button_fast_login.setEnabled(False)

            self.login_window.show()

    def init_login(self):

        self.parameters = Parameters()
        
        self.requests_sender = RequestsSender()

        self.ui_login.list_users.itemDoubleClicked.connect(self.fast_login)
        
        self.set_list_of_users()

        self.ui_login.button_login.clicked.connect(lambda: self.check_credentials(is_fast_login=False))

        self.ui_login.button_create.clicked.connect(self.open_signup_window)

        self.ui_login.button_fast_login.clicked.connect(self.fast_login)
        self.ui_login.button_fast_login.setEnabled(False)

        self.ui_login.list_users.itemSelectionChanged.connect(self.select_user)

        self.ui_login.textbox_username.textChanged.connect(lambda: self.ui_login.label_wrong.setVisible(False))
        self.ui_login.textbox_password.textChanged.connect(lambda: self.ui_login.label_wrong.setVisible(False))

        self.ui_login.label_wrong.setVisible(False)

        self.is_authenticated = False

        self.login_window.show()

        Logs().write_new_log(logging.INFO, "CLIENT LOGIN INITIALIZED")

    def set_list_of_users(self):
        self.ui_login.list_users.clear()

        usernames = self.requests_sender.get_usernames_authenticated_to_current_client(self.parameters.mac_address)

        for username in usernames:
            self.ui_login.list_users.addItem(username.get("username"))
        pass

    def fast_login(self):
        Logs().write_new_log(logging.INFO, "FAST LOGIN")
        self.check_credentials(is_fast_login=True)

    def select_user(self):
        """Select the user from the list"""

        if self.ui_login.list_users.count() > 0:
            self.ui_login.textbox_username.setText(self.ui_login.list_users.currentItem().text())
            self.ui_login.button_fast_login.setEnabled(True)

    def open_signup_window(self):
        """Open the signup window"""

        from GUI.Signup import Signup
        Signup()
        
        self.login_window.hide()

        Logs().write_new_log(logging.INFO, "OPENED SIGNUP WINDOW")

    def close_event(self, event):
        """Overrides the closing event of Pyqt5"""
        Logs().write_new_log(logging.INFO, "CLOSED LOGIN WINDOW")
        
        if not self.is_authenticated:
            event.accept()
            exit(0)

    
    def check_credentials(self, is_fast_login = False):
        """Check if the credentials are correct"""

        username = self.ui_login.textbox_username.text()
        password = self.ui_login.textbox_password.text()
    
        hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()

        user = self.requests_sender.login(username, hashed_password, is_fast_login)

        if is_fast_login or user != 404:

            self.is_authenticated = True

            Logs().write_new_log(logging.INFO, "RIGHT CREDENTIALS, LOGGING IN")

            self.ui_login.textbox_username.clear()
            self.ui_login.textbox_password.clear()
            self.ui_login.button_fast_login.setEnabled(False)

            self.login_window.close()

            from Init import Init
            self.init = Init()

            self.parameters.init_parameters(user)

            if not is_fast_login:
                self.requests_sender.set_user_is_authenticated(1)

            self.init.init_main()

            self.init.init_background()

        else:
            self.ui_login.label_wrong.setVisible(True)
            Logs().write_new_log(logging.INFO, "WRONG CREDENTIALS")