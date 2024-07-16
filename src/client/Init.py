# Author : Mathias Amato
# Date : 02.04.2024
# Project name : Foxync
# Project URL : https://gitlab.ictge.ch/mathias-amt/foxync
# Description : File synchronization tool using Bittorrent

from PyQt5.QtWidgets import QApplication
import sys
import logging
from Logs import Logs

app = None

class Init:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Init, cls).__new__(cls)

        return cls._instance

    def __init__(self):
        """
        Initialize the Init instance if it hasn't been initialized yet. Set up logging and print an initialization message.
        """
        if not hasattr(self, '_initialized'):
            self._initialized = True

            self.logs = Logs()
            print("INIT INITIALIZED")

    def init_login(self):
        """
        Initialize the login GUI.
        """
        from GUI.Login import Login

        Login()

    def init_main(self):
        """
        Initialize the main GUI and set up its user interface.
        """
        from GUI.Main import Main

        self.main_gui = Main()
        self.main_gui.initialize_ui()

    def init_background(self):
        """
        Initialize background processes such as request sending, parameter handling, and background tasks.
        """
        from Parameters import Parameters
        from Background.RequestsSender import RequestsSender
        from Background.BackgroundProcess import BackgroundProcess

        self.background_process = BackgroundProcess()

        self.requests_sender = RequestsSender()

        self.parameters = Parameters()

        self.background_process.recreate_scheduler() #Set the scheduler that checks if there are changes

        self.requests_sender.set_scheduler_for_ping() #Set the scheduler to send a ping message to the server every few seconds

        self.background_process.show_popup_if_number_of_connected_clients_is_more_than_zero(True)

        self.parameters.files_hashes_list_previous = self.parameters.get_list_of_files()

if __name__ == "__main__":
    app = QApplication(sys.argv)  # Init PyQt application

    Logs().write_new_log(logging.INFO, "APPLICATION STARTED")
    
    init = Init()

    init.init_login()

    sys.exit(app.exec_())