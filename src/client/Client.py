import json
import logging
from Logs import Logs

class Client:
    def __init__(self, client):
        self.client_id = client["client_id"]
        self.name = client["name"]
        self.mac_address = client["mac_address"]
        self.ip_address = client["ip_address"]
        self.auto_update_ip_address = client["auto_update_ip_address"]
        self.user_directory = client["user_directory"]
        self.torrent_directory = client["torrent_directory"]
        self.is_online = client["is_online"]
        self.is_away = client["is_away"]
        self.last_synchronization = client["last_synchronization"]
        self.interval_in_seconds_check = client["interval_in_seconds_check"]
        self.upload_limit = client["upload_limit"]
        self.download_limit = client["download_limit"]
        self.user_is_authenticated = client["user_is_authenticated"]
        self.user_id = client["user_id"]

    def dict_to_json(self):
        """Convert a dictionary to json

        Returns:
            The dictionary as json
        """
        Logs().write_new_log(logging.INFO, "SERIALIZING CLIENT DICT TO JSON")

        client_dict = {
            "client_id": self.client_id,
            "name": self.name,
            "mac_address": self.mac_address,
            "ip_address": self.ip_address,
            "auto_update_ip_address": self.auto_update_ip_address,
            "user_directory": str(self.user_directory),
            "torrent_directory": str(self.torrent_directory),
            "is_online": self.is_online,
            "is_away": self.is_away,
            "last_synchronization": str(self.last_synchronization),
            "user_is_authenticated": self.user_is_authenticated,
            "interval_in_seconds_check": self.interval_in_seconds_check,
            "upload_limit": self.upload_limit,
            "download_limit": self.download_limit,
            "user_id": self.user_id
        }

        return json.dumps(client_dict)