from socket import *
from p2p_meetings.server_messages import * 
from p2p_meetings.constants import * 
import threading
import json
from p2p_meetings.p2p_nodes import *

######################################################
######################################################
##                                                  ##
##  This file includes all of the functions needed  ##
##  for a client to connect to the central server   ##
##  and join/create a meeting. This is the code     ##
##  that the client runs to start the program.      ##
##                                                  ##
######################################################
######################################################
                                                     

class Client:

    def __init__(self):
        # connect to central server
        self.connect_with_server()
    
    def star_create(self):
        send_socket_message(self.client_socket, CreateStarRequest())

    def mesh_create(self):
        send_socket_message(self.client_socket, CreateMeshRequest())

    def join(self, n, user_str):
        send_socket_message(self.client_socket, JoinRequest(n, user_str))

    def list(self):
        send_socket_message(self.client_socket, ListRequest())

    def connect_with_server(self):
        """
        Establish new TCP connection with central server
        and create new thread for listening for server responses.
        """
        self.client_socket = socket(AF_INET, SOCK_STREAM)

        try:
            # try connecting to central server 
            self.client_socket.connect((SERVER_IP, SERVER_PORT))
        except Exception as e:
            print("Failed to connect with central server:", e, SERVER_IP, SERVER_PORT)
            return

        print("Connected successfully with central server.")

        # listen for messages from server 
        # in a separate thread
        self.server_response_thread = \
            ListenThread(ServerResponse, \
                            self.client_socket,  \
                            self.handle_response, \
                            lambda: print("Disconnected from central server."))

        self.server_response_thread.start()

    def disconnect_from_server(self):
        """
        Close socket with server and stop listening thread.
        """
        self.client_socket.close()

        self.server_response_thread.stop()

    def handle_response(self, response_obj):
        """
        Handle response from server 

        response_obj - valid ServerResponse object
        """
        if response_obj.type == JOIN:


            if response_obj.success:
                host_addr, host_port = response_obj.data.host
                username = response_obj.data.username 

                # Join a star-shaped meeting, so just connect
                # with the host. 
                if response_obj.data.meetingType == STAR:
                    self.node = StarAudienceNode(username, host_addr, host_port)

                # Join a full-mesh meeting, new tcp 
                # connections will be created between the 
                # joining user and all other nodes in the mesh network. 
                elif response_obj.data.meetingType == MESH:
                    # server should have assigned us a unique p2p port
                    p2p_port = response_obj.data.p2p_port
                    self.node = MeshAudienceNode(username, host_addr, host_port, p2p_port)

            else:
                print("Join request failed: ", response_obj.message)


        # Create a new meeting. The underlying network initially 
        # contains just the host node. As other users 
        # request to join, a p2p network will be built up 
        if response_obj.type == CREATE:
            if response_obj.success:
                meeting_port = response_obj.data.p2p_port

                # create a meeting with star-shaped network topology
                if response_obj.data.meetingType == STAR:
                    self.node = StarHostNode(HOST_USERNAME, response_obj.data.meetingID, meeting_port)

                # create a meeting with full-mesh network topology
                if response_obj.data.meetingType == MESH:
                    self.node = MeshHostNode(HOST_USERNAME, response_obj.data.meetingID, meeting_port)

            else:
                print("Create request failed: ", response_obj.message)

        if response_obj.type == LIST:
            if response_obj.success:
                print("Available meetings (ID/type) : ", response_obj.data)
            else:
                print("List request failed: ", response_obj.message)

