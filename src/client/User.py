import json
import hashlib

import logging
from Logs import Logs
class User:
    def __init__(self, user):
        """Initialize the user object

        Parameters:
            user -- The user dictionary
        """

        self.user_id = user["user_id"]
        self.username = user["username"]
        self.hashed_password = user["password"]
        self.block_size_in_bytes = user["block_size_in_bytes"]

    def dict_to_json(self):
        """Convert a dictionary to json
        
        Returns:
            The dictionary as json
        """
        Logs().write_new_log(logging.INFO, "SERIALIZING USER DICT TO JSON")
        
        user_dict = {
            "user_id": self.user_id,
            "username": self.username,
            "hashed_password": self.hashed_password,
            "block_size_in_bytes": self.block_size_in_bytes,
        }

        return json.dumps(user_dict)