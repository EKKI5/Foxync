# Author : Mathias Amato
# Date : 29.03.2024
# Project name : Foxync
# Project URL : https://gitlab.ictge.ch/mathias-amt/foxync
# Description : File synchronization tool using Bittorrent

import logging
import os
import datetime
import importlib
from pathlib import Path
from datetime import datetime

class Logs:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logs, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            
            self.create_new_log_file()

    def create_new_log_file(self):
        """Create a new log file"""
        datetime_string = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

        # Ensure the logs directory exists
        logs_folder_rel_path = "src/logs"

        log_filename = f"{logs_folder_rel_path}/Foxync-{datetime_string}.log"

        # Reset the logging configuration
        logging.shutdown()
        importlib.reload(logging)

        # Configure the logging system
        logging.basicConfig(
            filename=log_filename,  # Log file with timestamp in the name
            format='%(asctime)s %(levelname)s %(message)s',  # Log message format
            filemode='w'  # Write mode for the log file
        )
        
        self.log_object = logging.getLogger()  # Get a logger instance
        self.log_object.setLevel(logging.DEBUG)  # Set the log level, this is the minimum level that will be logged

    def write_new_log(self, level, message):
        """Write a new log in the log file
        
        Parameters:
            level -- The level of the log
            message -- The message to write"""
        self.log_object.log(level, message)  # Log the message with the specified level

    def clear_logs_files(self):
        """Clear the logs"""
        logs_folder_rel_path = "src/logs"
        logs_folder_full_path = os.path.abspath(logs_folder_rel_path)

        log_files = Path(logs_folder_full_path).rglob('*.log')  # Get all the .log files

        for log_file in log_files:
            log_file.unlink()  # Delete all the .log files

        self.create_new_log_file()