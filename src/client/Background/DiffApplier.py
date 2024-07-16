# Author : Mathias Amato
# Date : 17.05.2024
# Project name : Foxync
# Project URL : https://gitlab.ictge.ch/mathias-amt/foxync
# Description : File synchronization tool using Bittorrent

import libtorrent as lt
import time
import os
import shutil
import json
import bsdiff4
import codecs
from pathlib import Path

from Parameters import Parameters

from File import File
from Block import Block
from Patch import Patch

import sys
from pathlib import Path
parent_directory = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(parent_directory))

import logging
from Logs import Logs

class DiffApplier:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DiffApplier, cls).__new__(cls)

        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.parameters = Parameters()  # Initialize parameters
              # Initialize classes

            from Background.PatchProcess import PatchProcess
            self.patch_process = PatchProcess()

            from GUI.Main import Main
            self.main_gui = Main()

            Logs().write_new_log(logging.INFO, "INITIALIZED CLIENT DIFFAPPLIER")

            print("CLIENT DIFFAPPLIER INITIALIZED")

    def apply_downloaded_torrent(self, file_path):
        """Apply the changes in the downloaded torrent
        
        Parameters:
            file_path -- Path to the downloaded torrent"""
        self.main_gui.ui.label_sync_state.setText("Applying modifications...")  # Update GUI label

        Logs().write_new_log(logging.INFO, "APPLYING DOWNLOADED TORRENT")

        with open(file_path, 'rb') as f:
            torrent_content_dict = json.load(f)  # Load torrent content

        user_directory = self.parameters.current_client.user_directory  # Get user directory
        torrent_directory = self.parameters.current_client.torrent_directory  # Get torrent directory

        for item in torrent_content_dict['changes']['deleted']:

            self.main_gui.ui.label_sync_state.setText(f"Deleting {item}")  # Update GUI label
            file_full_path = f"{user_directory}/{item}"  # Get full path of the item

            if os.path.exists(file_full_path):
                if os.path.isdir(file_full_path):
                    shutil.rmtree(file_full_path)  # Remove directory
                    
                else:
                    os.remove(file_full_path)  # Remove file

            Logs().write_new_log(logging.INFO, "DELETED FILES")

        for file_dict in torrent_content_dict['changes']['added']:
            
            file = File.to_object(file_dict)

            self.main_gui.ui.label_sync_state.setText(f"Adding {file.file_rel_path}")  # Update GUI label
            file_full_path = f"{user_directory}/{file.file_rel_path}"  # Get full path of the item

            if file.is_dir:
                os.makedirs(file_full_path, exist_ok=True)  # Create directory
            else:
                with open(file_full_path, 'wb') as patched_file:
                    file_content_bytes = codecs.escape_decode(file.content_bytes[2:-1])[0]  # Decode content
                    patched_file.write(file_content_bytes)  # Write content to file

        Logs().write_new_log(logging.INFO, "ADDED FILES")

        if torrent_content_dict['changes_type'] == "patch":
            self.apply_patches(torrent_content_dict, user_directory)  # Apply patches

        elif torrent_content_dict['changes_type'] == "block":
            self.apply_blocks(torrent_content_dict, user_directory)  # Apply blocks

        os.remove(f"{torrent_directory}/foxync-torrent.json")  # Remove torrent JSON file

        self.parameters.files_hashes_list_previous = self.parameters.get_list_of_files()  # Update file hashes list

        self.main_gui.ui.label_sync_state.setText("Synchronized")  # Update GUI label

    def apply_patches(self, torrent_content_dict, user_directory):
        """Apply the patches in the downloaded torrent
        
        Parameters:
            torrent_content_dict -- The torrent content dictionary
            user_directory -- The user directory"""

        for patch_dict in torrent_content_dict['changes']['modified']:

            patch = Patch.to_object(patch_dict)

            self.main_gui.ui.label_sync_state.setText(f"Editing {patch.file_rel_path}")  # Update GUI label
            file_full_path = f"{user_directory}/{patch.file_rel_path}"  # Get full path of the patch
            
            if os.path.isfile(file_full_path):
                patch_data = codecs.escape_decode(patch.patch[2:-1])[0]  # Decode patch

                with open(file_full_path, 'rb') as original_file:
                    file_content_bytes = original_file.read()  # Read original file content

                patched_content = bsdiff4.patch(file_content_bytes, patch_data)  # Apply patch

                with open(file_full_path, 'wb') as patched_file:
                    patched_file.write(patched_content)  # Write patched content to file

        Logs().write_new_log(logging.INFO, "APPLIED PATCHES")

    def apply_blocks(self, torrent_content_dict, user_directory):
        """Apply the blocks in the downloaded torrent
        
        Parameters:
            torrent_content_dict -- The torrent content dictionary
            user_directory -- The user directory"""
            
        for block_dict in torrent_content_dict['changes']['modified']:

            block = Block.to_object(block_dict)

            self.main_gui.ui.label_sync_state.setText(f"Editing {block.file_rel_path}")  # Update GUI label
            file_full_path = Path(f"{user_directory}/{block.file_rel_path}")  # Get full path of the file containing the block

            if os.path.isfile(file_full_path):
                block_content = codecs.escape_decode(block.content_bytes[2:-1])[0]  # Decode block content

                with open(file_full_path, 'r+b') as file:
                    file.seek(block.starting_byte)  # Set cursor to the starting byte of the block
                    file.write(block_content)  # Write block content

                last_starting_byte = block.starting_byte + block.block_size # Calculate last starting byte

                if last_starting_byte < file_full_path.stat().st_size: #Delete everything after the last starting byte
                    with open(file_full_path, 'r+b') as file:
                        file.seek(last_starting_byte)  # Set cursor to last starting byte
                        file.truncate()  # Truncate file

        self.patch_process.backup_files_can_be_applied = True  # Allow backup files to be applied

        Logs().write_new_log(logging.INFO, "APPLIED BLOCKS")