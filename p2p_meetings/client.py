from socket import *
from p2p_meetings.message_types import * 
from p2p_meetings.constants import * 
import logging
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

        # this will be set when 
        # the client joins a p2p network 
        self.node = None

        # save messages from server for 
        # testing/debugging
        self.server_messages = []

        self.meeting_response_data = [] 
    
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
            logging.info("Failed to connect with central server: %s %s %s", str(e), str(SERVER_IP), str(SERVER_PORT))
            return

        logging.info("Connected successfully with central server.")

        # listen for messages from server 
        # in a separate thread
        self.server_response_thread = \
            ListenThread(ServerResponse, \
                            self.client_socket,  \
                            self.handle_response, \
                            lambda: logging.info("Disconnected from central server."))

        self.server_response_thread.start()

    def disconnect_from_server(self):
        """
        Safely close socket with server and stop listening thread.
        """
        safe_shutdown_close(self.client_socket)

        self.server_response_thread.stop()

    def handle_response(self, response_obj):
        """
        Handle response from server 

        response_obj - valid ServerResponse object
        """
        if response_obj.type == JOIN:
            # client attempts to join new p2p network 

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
                    listen_p2p_port = response_obj.data.listen_p2p_port
                    self.node = MeshAudienceNode(username, host_addr, host_port, listen_p2p_port)

            else:
                self.log_server_message("Join request failed: %s", str(response_obj.message))

        # Create a new meeting. The underlying network initially 
        # contains just the host node. As other users 
        # request to join, a p2p network will be built up 
        if response_obj.type == CREATE:
            if response_obj.success:
                listen_p2p_port = response_obj.data.listen_p2p_port

                # create a meeting with star-shaped network topology
                if response_obj.data.meetingType == STAR:
                    self.node = StarHostNode(HOST_USERNAME, response_obj.data.meetingID, listen_p2p_port)

                # create a meeting with full-mesh network topology
                if response_obj.data.meetingType == MESH:
                    self.node = MeshHostNode(HOST_USERNAME, response_obj.data.meetingID, listen_p2p_port)

            else:
                logging.info("Create request failed: %s", str(response_obj.message))

        if response_obj.type == LIST:
            if response_obj.success:
                self.log_server_message("Available meetings (ID/type): %s", response_obj.data)
                # save listing data for testing 
                self.meeting_response_data.append(response_obj.data)
            else:
                logging.info("List request failed: %s", str(response_obj.message))

    def log_server_message(self, fmt_str:str, *args):
        """
        Log a message and save it for testing and debugging. 
        Accept arguments in the same form as logging.info, 
        i.e., a formet string with 0 or more 
        """
        arg_tuple = tuple(map(str, args))
        text = fmt_str % arg_tuple
        logging.info(text)
        self.server_messages.append(text)


    def shutdown(self):
        """ 
        End connections and close sockets both with 
        server and with peers. Also stop listening thread"""
        self.disconnect_from_server()

        self.server_response_thread.stop()

        # close any p2p connections 
        if self.node:
            logging.debug("shutting down p2p node %s", self.node)
            self.node.shutdown()

