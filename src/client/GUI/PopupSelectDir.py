# Author : Mathias Amato
# Date : 24.05.2024
# Project name : Foxync
# Project URL : https://gitlab.ictge.ch/mathias-amt/foxync
# Description : File synchronization tool using Bittorrent

import sys
import os

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import logging
from Logs import Logs

class PopupSelectDir:
    def __init__(self, new_client_id):

        self.new_client_id = new_client_id

        self.popup_select_dir_window = QDialog()

        from ui.pyqt.Ui_popup_select_dir_window import Ui_popup_select_dir_window
        self.ui_popup_select_dir = Ui_popup_select_dir_window() #Get the python ui file, then run its setup
        
        self.ui_popup_select_dir.setupUi(self.popup_select_dir_window)

        self.popup_select_dir_window.setModal(True)  # Make the dialog modal

        self.popup_select_dir_window.closeEvent = self.close_event #Override the close event of Pyqt5

        self.ui_popup_select_dir.button_save.clicked.connect(self.save_synchronized_directory)
        self.ui_popup_select_dir.button_select.clicked.connect(self.open_file_dialog)

        self.ui_popup_select_dir.textbox_synchronized_directory.textChanged.connect(lambda: self.ui_popup_select_dir.label_wrong.setVisible(False))

        self.can_be_closed = False #Prevents the user from closing the pop-up without choosing a way of synchronization

        self.ui_popup_select_dir.label_wrong.setVisible(False)

        self.popup_select_dir_window.exec_()

        Logs().write_new_log(logging.INFO, "DISPLAYED CLIENT POPUP SELECT DIR")

        print("CLIENT POPUP SELECT DIR INITIALIZED")

    def open_file_dialog(self):
        """Open a file dialog to select a directory"""
        Logs().write_new_log(logging.INFO, "OPENING FILE DIALOG FOR SELECTING USER DIRECTORY")

        folderpath = QFileDialog.getExistingDirectory(self.popup_select_dir_window, 'Select Folder', '/home')

        if folderpath != '':
            self.ui_popup_select_dir.textbox_synchronized_directory.setText(folderpath)     

    def save_synchronized_directory(self):
        """Saves the selected directory"""

        textbox_synchronized_directory = self.ui_popup_select_dir.textbox_synchronized_directory.text()

        if not os.path.isdir(textbox_synchronized_directory):
            self.ui_popup_select_dir.label_wrong.setText("Selected directory is invalid")
            self.ui_popup_select_dir.label_wrong.setVisible(True)
            Logs().write_new_log(logging.INFO, "INVALID USER DIRECTORY IN CLIENT POPUP SELECT DIR")
            return
        else:
            self.can_be_closed = True
            self.popup_select_dir_window.close()

            from Parameters import Parameters
            self.parameters = Parameters()
            
            from Background.RequestsSender import RequestsSender
            self.requests_sender = RequestsSender()
            self.requests_sender.update_options('t_clients', 'client_id', self.new_client_id, {'user_directory': textbox_synchronized_directory})

            self.parameters.current_client = self.parameters.get_current_client_obj(logging_in = True)  # Connected client

            Logs().write_new_log(logging.INFO, "SAVED USER DIRECTORY IN CLIENT POPUP SELECT DIR")

    def close_event(self, event):
        """Overrides the closing event of Pyqt5
            
            Arguments:
            event -- Closing event
        """

        if self.can_be_closed:
            Logs().write_new_log(logging.INFO, "CLOSED CLIENT POPUP SELECT DIR")
            pass
        else:
            Logs().write_new_log(logging.INFO, "CLIENT POPUP SELECT DIR NOT CLOSED")
            event.ignore()