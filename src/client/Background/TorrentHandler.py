# Author : Mathias Amato
# Date : 02.04.2024
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
import sys

from Parameters import Parameters

import logging
from Logs import Logs

import sys
from pathlib import Path
parent_directory = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(parent_directory))

from inc.server_info_inc import Servers_Info

class TorrentHandler:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TorrentHandler, cls).__new__(cls)

        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            # Initialize parameters and classes
            self.parameters = Parameters()
              
            from GUI.Main import Main
            self.main_gui = Main()

            from Background.RequestsSender import RequestsSender
            self.requests_sender = RequestsSender()

            from Background.DiffApplier import DiffApplier
            self.diff_applier = DiffApplier()

            Logs().write_new_log(logging.INFO, "INITIALIZED CLIENT TORRENT HANDLER")

            print("CLIENT TORRENTHANDLER INITIALIZED")

    def set_session_settings(self):
        """Set the session settings for libtorrent."""

        self.session_settings = {
            'listen_interfaces': f"{self.parameters.current_client.ip_address}:6881",
            'request_timeout': 5,
            'peer_timeout': 15, 
            'min_reconnect_time': 5,
            'min_announce_interval': 15,
            'local_upload_rate_limit': self.parameters.current_client.upload_limit,
            'local_download_rate_limit': self.parameters.current_client.download_limit,
        }

        if self.parameters.current_client.upload_limit != 0:
            self.session_settings['local_upload_rate_limit'] = self.parameters.current_client.upload_limit

        if self.parameters.current_client.download_limit != 0:
            self.session_settings['local_download_rate_limit'] = self.parameters.current_client.download_limit

        Logs().write_new_log(logging.INFO, "SESSION SETTINGS SET")

    def generate_data_to_send_and_torrent(self, changes, changes_type, connecting_client=0):
        """Generate the JSON that will be seeded and downloaded. Also generate the torrent metadata and the magnet link.
        
        Parameters:
            changes -- The changes to be applied.
            changes_type -- The type of changes to be applied later (block or patch).
            connecting_client -- The ID of the client that is connecting for the block-level synchronization"""
        self.main_gui.ui.label_sync_state.setText("Generating a new torrent...")

        # Create the JSON object containing changes
        file_to_send_via_torrent = {
            'changes_type': changes_type,
            'changes': changes,
            'creation_timestamp': time.time(),
        }

        Logs().write_new_log(logging.INFO, "CREATING TORRENTED JSON FILE")
        # Write the JSON to a file
        json_path = self.parameters.current_client.torrent_directory / "foxync-torrent.json"
        with open(json_path, "w") as file:
            json.dump(file_to_send_via_torrent, file, indent=4)

        # Generate the torrent metadata and the magnet link
        magnet_link, torrent_info = self.create_torrent_info_and_magnet_link(json_path)
        Logs().write_new_log(logging.INFO, "GENERATED TORRENT METADATA AND MAGNET LINK")

        # Send the magnet link to the server based on the change type
        if changes_type == "patch":
            self.requests_sender.send_to_server_magnet_link_with_patches(changes_type, magnet_link)
        elif changes_type == "block":
            self.requests_sender.send_to_server_magnet_link_with_blocks(changes_type, magnet_link, connecting_client)

        # Seed the torrent for clients
        self.seed_from_torrent_info(torrent_info)

    def create_torrent_info_and_magnet_link(self, json_path):
        """Generate the torrent metadata and the magnet link."""
        fs = lt.file_storage()

        # Get file size and construct the relative path
        size = json_path.stat().st_size
        parent_directory = os.path.basename(self.parameters.current_client.torrent_directory)
        relative_path = os.path.join(parent_directory, os.path.relpath(json_path, self.parameters.current_client.torrent_directory))
        fs.add_file(relative_path, size)

        # Create the torrent
        torrent = lt.create_torrent(fs, flags=lt.create_torrent.v2_only) # Creating the torrent using only the Bittorrent v2 protocol
        torrent.set_creator(self.parameters.current_client.name) # Creator of the torrent
        tracker_url = f"http://{Servers_Info.TRACKER_IP.value}:{Servers_Info.TRACKER_PORT.value}/announce?client_id={self.parameters.current_client.client_id}" # Tracker that will organize the torrenting
        torrent.add_tracker(tracker_url)
        lt.set_piece_hashes(torrent, str(self.parameters.current_client.torrent_directory.parent)) # Set the piece hashes of the torrent
        torrent_data = torrent.generate()
        torrent_info = lt.torrent_info(torrent_data)

        # Log the creation of the magnet link

        return lt.make_magnet_uri(torrent_info), torrent_info # Return the generated magnet link and torrent metadata

    def download_from_magnet_link(self, magnet_link=None):
        """Download the torrent from the magnet link.

        Parameters:
            magnet_link (str): The magnet link to download the torrent from.
        """
        Logs().write_new_log(logging.INFO, "STARTING DOWNLOAD FROM MAGNET LINK")

        if not magnet_link or not magnet_link.startswith("magnet:"):
            print("Invalid magnet link")
            return

        self.set_session_settings()

        # Initialize libtorrent session
        self.ses = lt.session(self.session_settings)

        # Parse the magnet link
        torrent_params = lt.parse_magnet_uri(magnet_link)
        torrent_params.save_path = str(self.parameters.current_client.torrent_directory)
        handle = self.ses.add_torrent(torrent_params)

        # Start downloading the torrent
        self.operate_torrent(handle)

        # Apply the changes from the downloaded torrent
        self.parameters.current_client.torrent_directory = Path(self.parameters.current_client.torrent_directory)
        self.parameters.current_client.user_directory = Path(self.parameters.current_client.user_directory)

        json_path = self.parameters.current_client.torrent_directory / "foxync-torrent.json"

        self.diff_applier.apply_downloaded_torrent(json_path)

    def seed_from_torrent_info(self, torrent_info=None):
        """Seed the torrent metadata for clients receiving the magnet link.

        Parameters:
            torrent_info (libtorrent.torrent_info): The torrent metadata to seed.
        """

        Logs().write_new_log(logging.INFO, "STARTING SEED FROM TORRENT INFO")

        if not torrent_info:
            print("No torrent metadata")
            Logs().write_new_log(logging.ERROR, "NO TORRENT METADATA TO SEED")
            return

        self.set_session_settings()

        # Initialize libtorrent session
        self.ses = lt.session(self.session_settings)

        # Add metadata and start seeding
        handle = self.ses.add_torrent({'ti': torrent_info, 'save_path': str(self.parameters.current_client.torrent_directory)})
        self.operate_torrent(handle)

        # Notify the user and clean up
        self.main_gui.ui.label_sync_state.setText("Synchronized")
        json_path = self.parameters.current_client.torrent_directory / "foxync-torrent.json"
        os.remove(json_path)

    def operate_torrent(self, handle):
        """Interact with the torrent by downloading or seeding it.
        
        Parameters:
            handle (libtorrent.torrent_handle): The handle of the torrent to operate on.
        """

        self.parameters.keep_seeding = True
        sent_completion = False

        states_list = ['queued', 'checking', 'downloading metadata', 'downloading', 'finished', 'seeding', 'allocating', 'checking fastresume']
        
        while self.parameters.keep_seeding:
            # Get and display the torrent status
            status = handle.status()
            progress_in_percentage = status.progress * 100

            time.sleep(0.1) # Add a bit of time between update of progress_in_percentage and its use in the progress bar

            # Update the progress bar
            self.main_gui.ui.progressbar_sync.setValue(int(progress_in_percentage))

            if status.progress < 1:
                # Display download progress
                output = '%s\r%.2f%% complete (Download: %.1f kb/s, Upload: %.1f kB/s)' % (
                    states_list[status.state].capitalize(), progress_in_percentage, status.download_rate / 1000, status.upload_rate / 1000)
                self.main_gui.ui.label_sync_state.setText(output)

            else:
                # Display seeding status
                if not sent_completion:
                    Logs().write_new_log(logging.INFO, "DONE DOWNLOADING, STARTING SEEDING")
                    self.main_gui.ui.label_sync_state.setText("Seeding")
                    sent_completion = True
                    self.requests_sender.send_to_tracker_torrent_completion(handle.info_hash())

        Logs().write_new_log(logging.INFO, "DONE SEEDING")
        self.main_gui.update_last_synchronization_date()