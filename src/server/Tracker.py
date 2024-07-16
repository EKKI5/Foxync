import urllib.parse
import binascii
import requests
import sys
from pathlib import Path

from database.MariaDB_Connection_Server import MariaDB_Connection_Server

parent_directory = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_directory))

from inc.server_info_inc import Servers_Info

class Tracker:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Tracker, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            print("TRACKER INITIALIZED")


    def check_if_allowed_to_connect(self, client_id, ip_address):
        """Check if the client is allowed to connect to the tracker"""
        self.conn = MariaDB_Connection_Server()

        cur = self.conn.read_query(f"SELECT client_id, ip_address FROM t_clients WHERE client_id = {client_id}")

        client_id = cur.fetchone()

        if client_id is None:
            return False

        return True

    def decode_info_hash_to_utf8(self, info_hash):
        """
        Decode URL encoded hash to UTF-8.

        Arguments:
            info_hash -- The hash to decode

        Returns:
            Decoded info hash as a UTF-8 string.
        """

        # Decode to binary
        url_decoded_info_hash_bytes = urllib.parse.unquote_to_bytes(info_hash)
        # Convert bytes to a hexadecimal string for readable format
        return binascii.hexlify(url_decoded_info_hash_bytes).decode('utf-8')

    def add_peer_to_list_of_peers_and_create_info_hash_key_if_not_exist(self, info_hash, peers, client_id, ip, port, is_seeding):
        """
        Add a peer to the list of peers and create info_hash key if it does not exist.

        Arguments:
            info_hash -- The info hash of the torrent
            peers -- The dictionary of peers
            client_id -- The peer ID of the client
            ip -- The IP address of the client
            port -- The port number of the client
            is_seeding -- Whether the client is seeding

        Returns:
            The newly added peer.
        """

        if info_hash not in peers:
            # Create new info_hash key if it does not exist
            peers[info_hash] = []

        # Create a peer dictionary
        peer = {'client_id': client_id, 'ip': ip, 'port': port, 'is_seeding': is_seeding}

        # Add the client to the peers list
        peers[info_hash].append(peer)

        return peer, peers

    def update_peer_is_seeding(self, peers, ip, info_hash):
        """
        Update the seeding status of a peer.

        Arguments:
            peers -- The dictionary of peers
            ip -- The IP address of the client
            info_hash -- The info hash of the torrent
        """
        if info_hash in peers:
            # Find the peer with the specified IP address
            for peer in peers[info_hash]:
                print("888888888888888888888")
                print(peer['ip'])
                print(ip)
                print("888888888888888888888")
                if peer['ip'] == ip:
                    # Update the seeding status
                    peer['is_seeding'] = 1
                    return
            print("No peer found with the specified IP.")
        else:
            print("No such info_hash found in peers.")

    def delete_info_hash_if_empty_and_return_complete_seeding(self, peers, ip, info_hash):
        """
        Check if all peers are seeding and if so, return True.

        Arguments:
            peers -- The dictionary of peers
            ip -- The IP address of the client
            info_hash -- The info hash of the torrent

        Returns:
            True if all peers are seeding, False otherwise.
        """
        
        if info_hash not in peers:
            print("No such info_hash found in peers.")
            return False

        # Check if all peers are seeding
        for peer in peers[info_hash]:
            if not peer['is_seeding']:
                return False

        return True

    def send_stop_seeding_to_server_relay(self):
        """
        Send a request to the server relay to stop seeding.
        """
        try:
            print("Sending stop seeding request to server relay...")
            # Send POST request to the server relay endpoint
            requests.post(f'https://{Servers_Info.SERVER_IP.value}:{Servers_Info.SERVER_PORT.value}/complete_seeding', json={'info_type': "complete_seeding"}, verify=False)
        except requests.exceptions.RequestException as e:
            # Print error message if request fails
            print(f"Error while calling /complete_seeding of server: {str(e)}")
