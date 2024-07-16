# Author : Mathias Amato
# Date : 10.05.2024
# Project name : Foxync
# Project URL : https://gitlab.ictge.ch/mathias-amt/foxync
# Description : File synchronization tool using Bittorrent

import time
from apscheduler.schedulers.background import BackgroundScheduler

from Parameters import Parameters

import sys
from pathlib import Path
parent_directory = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(parent_directory))

import logging
from Logs import Logs

class BackgroundProcess:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BackgroundProcess, cls).__new__(cls)

        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True

            self.parameters = Parameters()

            from Background.BlockLevelProcess import BlockLevelProcess
            self.block_level_process = BlockLevelProcess()

            from Background.PatchProcess import PatchProcess
            self.patch_process = PatchProcess()

            from Background.RequestsSender import RequestsSender
            self.requests_sender = RequestsSender()

            from GUI.Popup import Popup
            self.popup = Popup()

            self.files_blocks = self.block_level_process.init_blocks()

            self.scheduler_changes = BackgroundScheduler()

            # If client is in away mode
            if self.parameters.current_client.is_away:
                return

            Logs().write_new_log(logging.INFO, "INITIALIZED CLIENT BACKGROUNDPROCESS")

            print("CLIENT BACKGROUNDPROCESS INITIALIZED")

    def show_popup_if_number_of_connected_clients_is_more_than_zero(self, is_new_connection = False):
        """Show popup only if there is one other device connected
        
        Parameters:
            is_new_connection -- Indicates if the user is logging in or not"""
            
         # Get number of other connected clients that are not away

        number_of_clients = self.requests_sender.get_number_of_connected_clients(self.parameters.current_user.user_id)

        if number_of_clients < 2:  # If there are no other connected clients
            Logs().write_new_log(logging.INFO, "NO OTHER CONNECTED CLIENT")
            self.recreate_scheduler()
            return

        self.construct_popup_at_connection()

    def recreate_scheduler(self):
        """Create or recreate the scheduler to check if there are changes in the user directory"""

        if self.scheduler_changes.running:
            self.scheduler_changes.shutdown(wait=False)

        self.scheduler_changes = BackgroundScheduler()

        if self.scheduler_changes.get_job("scheduler_changes"):
            self.scheduler_changes.remove_job("scheduler_changes")
            Logs().write_new_log(logging.INFO, "RECREATED SCHEDULER TO CHECK CHANGES")

        self.scheduler_changes.add_job(self.patch_process.send_changes_if_any, 'interval', seconds=self.parameters.current_client.interval_in_seconds_check, id="scheduler_changes")
        self.scheduler_changes.start()

        Logs().write_new_log(logging.INFO, "STARTED SCHEDULER TO CHECK CHANGES")

    def construct_popup_at_connection(self):
        """Construct a popup that asks the user if he wants to transfer the local changes or overwrite them"""

        self.popup.can_be_closed = False

        # Connect buttons to their respective functions
        self.popup.ui_popup.button1.clicked.connect(self.transfer_changes)
        self.popup.ui_popup.button2.clicked.connect(self.overwrite_local_files)

        # Display popup with choices
        self.popup.display_popup_with_two_choices(
            "There is at least 1 other device connected. Would you like to transfer\nthe local changes to the other devices or overwrite the local changes?",
            "Local changes", "Transfer changes", "Overwrite"
        )
    
    def stop_interval_check_for_changes(self):
        self.scheduler_changes.shutdown(wait=False)
        Logs().write_new_log(logging.INFO, "STOPPED SCHEDULER TO CHECK CHANGES")

    def overwrite_local_files(self):
        """Synchronize the current client with all other clients of the synchronization"""

        Logs().write_new_log(logging.INFO, "OVERWRITING LOCAL FILES WITH FILES FROM CLIENT WITH LATEST SYNCHRONIZATION")

        self.requests_sender.send_to_server_blocks(self.files_blocks)  # Block-level synchronization
        self.close_popup_and_start_interval()

    def transfer_changes(self):
        """Synchronize all other clients with differences of the current client"""

        Logs().write_new_log(logging.INFO, "SENDING LOCAL FILES TO OTHER CLIENTS")
        
        # Backup of files before block-level synchronization
        backup_current_files = self.parameters.get_list_of_files()

        self.requests_sender.send_to_server_blocks(self.files_blocks)

        # Wait until the end of block-level synchronization
        while not self.patch_process.backup_files_can_be_applied:
            time.sleep(0.2)

        # Reapply backup
        self.patch_process.reapply_backup_after_blocks(backup_current_files)
        self.close_popup_and_start_interval()

    def close_popup_and_start_interval(self):
        """Close the synchronization popup and start checking files at interval"""
        self.popup.can_be_closed = True
        self.popup.popup_window.close()

        self.recreate_scheduler()