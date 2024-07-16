import time
import os
import socket
import hashlib
import json
import bsdiff4
import glob
from pathlib import Path

from Parameters import Parameters

from Block import Block
from File import File

import sys
from pathlib import Path
parent_directory = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(parent_directory))

import logging
from Logs import Logs

class BlockLevelProcess:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BlockLevelProcess, cls).__new__(cls)

        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True

            # Initialize parameters and classes
            self.parameters = Parameters()

            from Background.TorrentHandler import TorrentHandler
            self.torrent_handler = TorrentHandler()
            
            print("CLIENT BLOCKLEVELPROCESS INITIALIZED")

    def init_blocks(self):
        """Call generate_blocks() at startup and return it"""
        return self.generate_blocks()

    def generate_blocks(self):
        """Generate a list of blocks for each file in the user directory"""
        files_blocks = {}
        full_path_to_user_dir = self.parameters.current_client.user_directory  # Path to the user directory

        # Get all files in the user directory, including hidden files

        files = Path(full_path_to_user_dir).rglob('*')
        
        for file in files:
            #current_file_path = full_path_to_user_dir / file  # Full path to file
            current_file_path = file

            # Skip if path is invalid or inaccessible
            if not current_file_path.exists():
                continue

            current_file_size = current_file_path.stat().st_size  # Get the size of the file
            relative_path = str(current_file_path.relative_to(full_path_to_user_dir))  # Get the relative path
            files_blocks[relative_path] = []  # Create an empty list for the file inside the dictionary

            if current_file_path.is_dir():  # If it's a directory                
                files_blocks[relative_path].append(Block(
                    is_dir=1,
                    file_rel_path=relative_path,
                    block_number=0,
                ))

                continue

            if current_file_size == 0:  # Handle empty files
                files_blocks[relative_path].append(Block(
                    file_rel_path=relative_path,
                    block_number=0,
                    hash_var=hashlib.sha256(b'').hexdigest(),
                ))

                continue

            with open(current_file_path, "rb") as f:  # Open the file in binary mode
                size_limit = self.parameters.current_user.block_size_in_bytes
                bytes_count = 0
                block_number = 0

                while bytes_count < current_file_size:  # While it has not reached the end of the file
                    read_file = f.read(size_limit)  # Read from the pointer to the end of the block
                    block_size = len(read_file)  # Get the size of the block
                    hashed_block = hashlib.sha256(read_file).hexdigest()  # Get the hash of the block

                    files_blocks[relative_path].append(Block(
                        file_rel_path=relative_path,
                        block_number=block_number,
                        hash_var=hashed_block,
                        starting_byte=bytes_count,
                        block_size=block_size
                    ))

                    bytes_count += block_size
                    block_number += 1

        Logs().write_new_log(logging.INFO, "DETERMINED FILES AND THEIR BLOCKS")

        return files_blocks

    def compare_files_blocks(self, received_files_blocks, connecting_client):
        """Compare the blocks received via socket with the current client's own blocks
        
        Parameters:
        received_files_blocks -- List of blocks of files received by another client via socket
        connecting_client -- The client that sent the blocks
        """

        Logs().write_new_log(logging.INFO, "COMPARING LOCAL BLOCKS WITH RECEIVED BLOCKS")
                
        files_blocks = self.generate_blocks()  # Get the files blocks

        # Dictionary of differences that will be serialized to JSON and sent via torrent
        difference_blocks = {
            'added': [],
            'deleted': [],
            'modified': []
        }

        # Get the files that need to be added or deleted
        to_add = set(files_blocks).difference(received_files_blocks)
        to_delete = set(received_files_blocks).difference(files_blocks)

        # Add files to be deleted
        for file in to_delete:
            difference_blocks['deleted'].append(file)

        for file in files_blocks:
            if file in to_add:  # If the file needs to be added
                current_file_full_path = self.parameters.current_client.user_directory / file

                file_obj = None

                if not current_file_full_path.is_dir():  # If the file is not a directory, open it
                    with open(current_file_full_path, "rb") as file_open:
                        file_content_bytes = file_open.read()

                    file_obj = File(                        
                        file_rel_path=file,
                        content_bytes=str(file_content_bytes)
                    ).to_json()

                else:
                    file_obj = File(
                        is_dir=1,
                        file_rel_path=file,
                    ).to_json()

                difference_blocks['added'].append(file_obj)

            else:
                current_file_path = self.parameters.current_client.user_directory / file

                if current_file_path.is_dir():
                    continue

                with open(current_file_path, "rb") as file_open:
                    for index, block in enumerate(files_blocks[file]):  # For each block of the file

                        if index >= len(received_files_blocks[file]):  # If the block is not in the list of received blocks
                            file_open.seek(block.starting_byte)
                            block_content_bytes = file_open.read()

                        elif block.hash != received_files_blocks[file][index]['hash']:  # If the hashes of the two lists are not the same
                            file_open.seek(block.starting_byte)
                            block_content_bytes = file_open.read(block.block_size)

                        else:
                            continue

                        difference_blocks['modified'].append(Block(
                            is_dir=0,
                            file_rel_path=file,
                            content_bytes=str(block_content_bytes),
                            block_number=block.block_number,
                            hash_var=block.hash,
                            starting_byte=block.starting_byte,
                            block_size=block.block_size
                        ).to_json())

        # Generate and send the data for the differences found
        self.torrent_handler.generate_data_to_send_and_torrent(difference_blocks, "block", connecting_client)