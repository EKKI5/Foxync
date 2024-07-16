# Author : Mathias Amato
# Date : 27.03.2024
# Project name : Foxync
# Project URL : https://gitlab.ictge.ch/mathias-amt/foxync
# Description : File synchronization tool using Bittorrent

from flask import Flask, request, jsonify
from flask_jwt_extended import (
    JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity, decode_token
)
import secrets
from datetime import datetime, timedelta
import sys
from pathlib import Path
import json

parent_directory = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_directory))

from Server import Server
from PingHandler import PingHandler

from server_info_inc import Servers_Info

app = Flask(__name__)

secure_key = secrets.token_urlsafe(32)
app.config['JWT_SECRET_KEY'] = secure_key
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=10)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)

jwt = JWTManager(app)

server = Server()

ping_handler = PingHandler()

connected_clients = []

@app.route('/')
def hello_world():
    return "<h1>Hello world! Server is working!</h1>"

@app.route('/login', methods=["POST"])
def login():
    data = request.json

    user = server.login(data)

    if user == 404:
        return "404"

    return user

@app.route('/logout', methods=["POST"])
def logout():
    data = request.json

    response = server.logout(data)

    return response

@app.route('/signup', methods=["POST"])
def signup():
    data = request.json

    response = server.signup(data)

    return response

@app.route('/get_tokens', methods=["GET"])
def get_tokens():
    client_id = request.args.get('client_id')
    user_id = request.args.get('user_id')

    access_token = create_access_token(identity={'user_id': user_id, 'client_id': client_id})
    refresh_token = create_refresh_token(identity={'user_id': user_id, 'client_id': client_id})

    return jsonify(access_token=access_token, refresh_token=refresh_token)

@app.route('/refresh_token', methods=["POST"])
@jwt_required(refresh=True)
def refresh_token():
    identity = get_jwt_identity()

    access_token = create_access_token(identity=identity)
    return jsonify(access_token_server=access_token)


@app.route('/ping', methods=["POST"])
@jwt_required()
def ping():
    client_data = request.json

    ping_handler.update_ping_time_of_client(client_data['client_id'])
    
    return "200"

@app.route('/relay_magnet_link', methods=["POST"])
@jwt_required()
def relay_magnet_link():
    data_to_relay = request.json

    if data_to_relay['info_type'] == "block":
        # When sending back a magnet link generated for the newly connected client
        connecting_client = json.loads(data_to_relay["connecting_client"])
        server.create_thread_for_sending_information_to_single_client(connecting_client['ip_address'], data_to_relay)

    else:
        # When sending a magnet link to all the connected clients for synchronization
        connected_clients = server.get_online_and_not_away_clients()
        ip_of_sender = request.remote_addr  # IP of the sending client, to not get its own magnet link
        server.create_threads_for_sending_information_to_clients(connected_clients, ip_of_sender, data_to_relay)

    return "200"

@app.route('/relay_blocks', methods=["POST"])
@jwt_required()
def relay_blocks():
    data_to_relay = request.json
    data_to_relay['info_type'] = "block_dict"

    ip_address_of_sender = request.remote_addr
    client_with_latest_synchronization = server.get_client_with_latest_synchronization(ip_address_of_sender)

    server.create_thread_for_sending_information_to_single_client(client_with_latest_synchronization["ip_address"], data_to_relay)

    return "200"

@app.route('/set_user_is_authenticated' , methods=["POST"])
@jwt_required()
def set_user_is_authenticated():
    data = request.json

    response = server.set_user_is_authenticated(data['client_id'], data['is_authenticated'])

    return response

@app.route('/get_number_of_connected_clients', methods=["GET"])
@jwt_required()
def get_number_of_connected_clients():
    user_id = request.args.get('user_id')

    number_of_clients = server.get_number_of_connected_clients(user_id)

    return number_of_clients

@app.route('/get_current_user', methods=["GET"])
def get_current_user():
    user_id = request.args.get('user_id')

    response = server.get_current_user(user_id)

    return response

@app.route('/get_current_client_or_insert_if_not_found', methods=["POST"])
def get_current_client_or_insert_if_not_found():
    data = request.json
    
    ip_address = request.remote_addr

    data['ip_address'] = ip_address

    new_client = False

    client = server.get_current_client(data['user_id'], data['mac_address'])

    if client is None:
        client = server.insert_and_get_new_client(data)

        new_client = True

    return jsonify(client=client, new_client=new_client)

@app.route('/get_usernames_authenticated_to_current_client', methods=["GET"])
def get_usernames_authenticated_to_current_client():
    mac_address = request.args.get('mac_address')

    response = server.get_usernames_authenticated_to_current_client(mac_address)

    return response

@app.route('/get_authenticated_clients_of_user', methods=["GET"])
@jwt_required()
def get_authenticated_clients_of_user():
    user_id = request.args.get('user_id')
    client_id = request.args.get('client_id')

    response = server.get_authenticated_clients_of_user(user_id)

    return response

@app.route ('/update_last_synchronization_date', methods=["POST"])
@jwt_required()
def update_last_synchronization_date():
    data = request.json

    response = server.update_last_synchronization_date(data['readable_date'], data['client_id'])

    return response

@app.route('/update_client_ip_address', methods=["POST"])
@jwt_required()
def update_client_ip_address():
    data = request.json

    server.update_client_ip_address(data['client_id'], data['ip_address'])

    return "200"

@app.route('/set_client_status', methods=["POST"])
@jwt_required()
def set_client_status():
    data = request.json

    server.set_client_status(data)

    if data['is_online'] == 1:
        ping_handler.update_ping_time_of_client(data['client_id'])

    return "200"

@app.route('/update_options', methods=["POST"])
@jwt_required()
def update_options():
    data = request.json

    server.update_options(data)

    return "200"

@app.route('/complete_seeding', methods=['POST'])
def complete_seeding():
    data_to_relay = {'info_type': "complete_seeding"}

    connected_clients = server.get_online_and_not_away_clients()

    server.create_threads_for_sending_information_to_clients(connected_clients, "0", data_to_relay)

    return "200"

if __name__ == '__main__':
    app.run(debug=False, host=Servers_Info.SERVER_IP.value, port=Servers_Info.SERVER_PORT.value, ssl_context=('src/server/ssl/school/cert.pem', 'src/server/ssl/school/key.pem'))