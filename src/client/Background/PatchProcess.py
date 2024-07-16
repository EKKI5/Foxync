# Author : Mathias Amato
# Date : 02.04.2024
# Project name : Foxync
# Project URL : https://gitlab.ictge.ch/mathias-amt/foxync
# Description : File synchronization tool using Bittorrent

import time
import os
import socket
import hashlib
import json
import bsdiff4
import glob

from Parameters import Parameters
from Patch import Patch

import sys
from pathlib import Path
parent_directory = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(parent_directory))

import logging
from Logs import Logs

class PatchProcess:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PatchProcess, cls).__new__(cls)

        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.parameters = Parameters()
            
            from Background.TorrentHandler import TorrentHandler
            self.torrent_handler = TorrentHandler()

            from GUI.Main import Main
            self.main_gui = Main()

            # Initialize previous file hashes list
            self.parameters.files_hashes_list_previous = self.parameters.get_list_of_files()

            self.backup_files_can_be_applied = False

            Logs().write_new_log(logging.INFO, "INITIALIZED CLIENT PATCHPROCESS")

            print("CLIENT PATCHPROCESS INITIALIZED")

    def send_changes_if_any(self):
        """Look for modifications inside the user directory. If any, generate the torrent and send it to the server"""
        
        changes = self.determine_changes()  # Get the changes in the user directory

        has_changes = any(changes[key] for key in changes)

        if has_changes:
            Logs().write_new_log(logging.INFO, "CHANGES IN SYNCHRONIZED FILES DETECTED")
            self.torrent_handler.generate_data_to_send_and_torrent(changes, "patch")  # Generate the torrent and send it to the server
            self.parameters.files_hashes_list_previous = self.parameters.get_list_of_files()
        else:
            self.main_gui.ui.label_sync_state.setText("Synchronized")

    def determine_changes(self):
        """Determine the changes and patches inside the user directory, and save them to a dictionary"""

        Logs().write_new_log(logging.INFO, "DETERMINING CHANGES IN SYNCHRONIZED DIRECTORY")

        changes = {
            'added': [],
            'deleted': [],
            'modified': []
        }

        files_hashes_list = self.parameters.get_list_of_files()  # Get the current hashes of the files

        # Calculate added and deleted files
        previous_files = {file.file_rel_path: file for file in self.parameters.files_hashes_list_previous}
        current_files = {file.file_rel_path: file for file in files_hashes_list}

        added_files_rel_path = set(current_files).difference(previous_files)
        deleted_files_rel_path = set(previous_files).difference(current_files)

        changes['deleted'].extend(deleted_files_rel_path)

        for file_rel_path in added_files_rel_path:  # Added file(s)
            file = current_files[file_rel_path]
            file.content_bytes = str(file.content_bytes)
            changes['added'].append(file.to_json())

        for file_rel_path, current_file in current_files.items():  # Modified file(s)
            if file_rel_path not in added_files_rel_path:
                previous_file = previous_files.get(file_rel_path)
                if previous_file and current_file.content_bytes != previous_file.content_bytes and not current_file.is_dir:
                    # Determine the delta between the two states of the file
                    delta_between_the_two_files = bsdiff4.diff(previous_file.content_bytes, current_file.content_bytes)
                    current_file.patch = str(delta_between_the_two_files)  # Convert to string to be able to serialize it to JSON
                    current_file.content_bytes = 0
                    changes['modified'].append(current_file.to_json())

        return changes

    def reapply_backup_after_blocks(self, backup_current_files):
        """Reapply the files that were backed up before the block-level synchronization was performed
        
        Parameters:
            backup_current_files -- The list of files that were backed up before the block-level synchronization was performed
        """

        self.parameters.files_hashes_list_previous = self.parameters.get_list_of_files()  # Get current hashes after receiving blocks but before applying backed up changes

        # Files that need to be deleted
        current_files_set = set(file.file_rel_path for file in self.parameters.files_hashes_list_previous)
        backup_files_set = set(file.file_rel_path for file in backup_current_files)
        deleted_files_rel_path = current_files_set.difference(backup_files_set)

        for file_rel_path in deleted_files_rel_path:
            os.remove(f"{self.parameters.current_client.user_directory}/{file_rel_path}")

        for file in backup_current_files:
            file_path = f"{self.parameters.current_client.user_directory}/{file.file_rel_path}"
            with open(file_path, "wb") as file_open:
                file_open.write(file.content_bytes)