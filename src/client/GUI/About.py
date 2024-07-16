# Author : Mathias Amato
# Date : 16.04.2024
# Project name : Foxync
# Project URL : https://gitlab.ictge.ch/mathias-amt/foxync
# Description : File synchronization tool using Bittorrent

import sys
import git
import logging
from Logs import Logs
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
class About:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(About, cls).__new__(cls)

        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True

            self.window_foxync_about = QDialog()
            
            from ui.pyqt.Ui_about_window import Ui_about_window
            self.ui_about = Ui_about_window() #Get the python ui file, then run its setup
            
            self.ui_about.setupUi(self.window_foxync_about)

            repo = git.Repo(search_parent_directories=True)
            commit_id = repo.head.object.hexsha

            self.ui_about.label_commit.setText(f"Latest commit : {commit_id}")
            self.ui_about.label_version.setText(f"Version 0.3.1")

            self.window_foxync_about.show()
            Logs().write_new_log(logging.INFO, "OPENED ABOUT PAGE")
        else:
            repo = git.Repo(search_parent_directories=True)
            commit_id = repo.head.object.hexsha

            self.ui_about.label_commit.setText(f"Latest commit : {commit_id}")
            self.ui_about.label_version.setText(f"Version 0.3.1")

            self.window_foxync_about.show()
            Logs().write_new_log(logging.INFO, "OPENED ABOUT PAGE")