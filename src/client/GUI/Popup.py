# Author : Mathias Amato
# Date : 09.05.2024
# Project name : Foxync
# Project URL : https://gitlab.ictge.ch/mathias-amt/foxync
# Description : File synchronization tool using Bittorrent

import sys

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import logging
from Logs import Logs

class Popup:
    def __init__(self):
        self.popup_window = QDialog()

        from ui.pyqt.Ui_popup_window import Ui_popup_window
        self.ui_popup = Ui_popup_window() #Get the python ui file, then run its setup
        
        self.ui_popup.setupUi(self.popup_window)

        self.popup_window.setModal(True)  # Make the dialog modal

        self.popup_window.closeEvent = self.close_event #Override the close event of Pyqt5

        self.can_be_closed = False #Prevents the user from closing the pop-up without choosing a way of synchronization

        print("CLIENT POPUP INITIALIZED")

    def display_popup_with_two_choices(self, message, title, button1, button2):
        """Display pop-up with a message and two choices
            
            Arguments:
            message -- Message to show
            title -- Title of the pop-up
            button1 -- Text of the first button
            button2 -- Text of the second button
        """

        Logs().write_new_log(logging.INFO, "DISPLAYING BLOCK-LEVEL SYNCHRONIZATION POPUP")

        self.popup_window.setWindowTitle(title)

        self.ui_popup.label.setText(message)

        self.ui_popup.button1.setText(button1)
        self.ui_popup.button2.setText(button2)

        self.popup_window.exec_()

    def close_event(self, event):
        """Overrides the closing event of Pyqt5
            
            Arguments:
            event -- Closing event
        """

        if self.can_be_closed:
            Logs().write_new_log(logging.INFO, "BLOCK-LEVEL SYNCHRONIZATION POPUP CLOSED")
            pass
        else:
            Logs().write_new_log(logging.INFO, "BLOCK-LEVEL SYNCHRONIZATION POPUP NOT CLOSED")
            event.ignore()