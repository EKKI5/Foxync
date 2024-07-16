# Author : Mathias Amato
# Date : 27.03.2024
# Project name : Foxync
# Project URL : https://gitlab.ictge.ch/mathias-amt/foxync
# Description : File synchronization tool using Bittorrent

from flask import Flask, request, jsonify, Response
from flask_jwt_extended import (
    JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity, decode_token
)
import secrets
from datetime import datetime, timedelta
import sys
from pathlib import Path
import urllib.parse
import bencodepy

parent_directory = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_directory))

from database.MariaDB_Connection_Server import MariaDB_Connection_Server
from Tracker import Tracker
from PingHandler import PingHandler

from server_info_inc import Servers_Info

app = Flask(__name__)

tracker = Tracker()

pinghandler = PingHandler()

peers = {}

@app.route('/')
def hello_world():
    return "<h1>Hello world! Tracker is working!</h1>"

@app.route('/announce', methods=['GET'])
def announce(): #TODO Finish securizing
    client_id = request.args.get('client_id')
    info_hash = request.args.get('info_hash')
    ip = request.remote_addr
    port = int(request.args.get('port', '6881'))
    is_seeding = request.args.get('left') == "0"

    if not client_id or not info_hash:
        return Response("Missing client_id or info_hash", status=400)

    is_allowed = False

    is_allowed = tracker.check_if_allowed_to_connect(int(client_id), ip)

    if not is_allowed:
        return Response("Unauthorized", status=401)

    url_decoded_info_hash_string = tracker.decode_info_hash_to_utf8(info_hash)
    peer = tracker.add_peer_to_list_of_peers_and_create_info_hash_key_if_not_exist(
        url_decoded_info_hash_string, peers, client_id, ip, port, is_seeding)

    bencoded_response = bencodepy.encode(peer)
    return Response(bencoded_response, content_type='application/x-bittorrent', status=200)

@app.route('/complete', methods=['GET'])
def complete():
    info_hash = request.args.get('info_hash')
    ip = request.remote_addr

    if not ip or not info_hash:
        print("Missing info_hash or IP")
        return Response("Missing info_hash or IP", status=400)

    url_decoded_info_hash_string = urllib.parse.unquote(info_hash)
    tracker.update_peer_is_seeding(peers, ip, url_decoded_info_hash_string)
    complete_seeding = tracker.delete_info_hash_if_empty_and_return_complete_seeding(peers, ip, url_decoded_info_hash_string)

    if complete_seeding:
        tracker.send_stop_seeding_to_server_relay()

    return "200"

if __name__ == '__main__':
    app.run(debug=False, host=Servers_Info.TRACKER_IP.value, port=Servers_Info.TRACKER_PORT.value)