from socket import *
from server_requests import * 
from constants import * 
import threading
import json
from star_client import *

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
                                                     
                                                     
# also implement CLI -- reading user commands one line at a time
#
# once meeting is joined, entering a line just sends it as a message
# type !exit to leave or something. 



## def listen_thread(conn_socket, handle_message, on_close):
##     """
##     Return a thread that will listen to a socket 
##     and process incoming messages. 
## 
##     conn_socket - socket object to listen to 
##     handle_message - function to be called when a message 
##                 is received and parsed. Takes a message
##                 in dictionary form as its single argument. 
##     on_close - 0-ary function to be called when socket is closed.
##             This function might perform some cleanup, such as removing
##             the socket from a list of active connections 
##     """
##     listen_func = lambda: listen_and_do(conn_socket, handle_message, on_close)
##     return threading.Thread(target=listen_func)

class Client:

    def __init__(self):
        # connect to central server
        self.connect_with_server()
    
    def create(self):
        send_socket_message(self.client_socket, CreateStarRequest())

    def join(self, n):
        send_socket_message(self.client_socket, JoinStarRequest(n))

    def list(self):
        send_socket_message(self.client_socket, ListRequest())

    def connect_with_server(self):
        """
        Establish new TCP connection with central server
        and create new thread for listening for server responses.
        """
        self.client_socket = socket(AF_INET, SOCK_STREAM)

        try:
            # self.client_socket.connect((SERVER_IP, SERVER_PORT))
            self.client_socket.connect((convert_ip(SERVER_IP), SERVER_PORT))
        except Exception as e:
            # try: 
            #     # workaround for connectin from local machine 
            #     self.client_socket.connect(("localhost", SERVER_PORT))
            # except Exception as e:
            #
            print("Failed to connect with central server:", e)
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
                
                if response_obj.data.meetingType == STAR:
                    print("Client action: join with ", response_obj.data.host)
                    host_addr, host_port = response_obj.data.host

                    # TODO wrap this with try/except (meeting may have closed)
                    #
                    # aud = AudienceNode("new user", host_addr)
                    self.aud = AudienceNode("new_user123", host_addr, host_port)

                elif response_obj.data.meetingType == MESH:
                    pass

                # disconnect from central server
                self.disconnect_from_server()

            else:
                print("Join request failed: ", response_obj.message)

        if response_obj.type == CREATE:
            if response_obj.success:
                print("Client action: Create new room with meeting ID", response_obj.data.meetingID)
                # TODO establish new room 

                # what kind of room to create:

                if response_obj.data.meetingType == STAR:
                    room_name = "meeting-%s" % response_obj.data.meetingID
                    # host = HostNode(room_name)
                    self.host = HostNode(room_name, get_meeting_port(response_obj.data.meetingID))

                if response_obj.data.meetingType == MESH:
                    pass

                self.disconnect_from_server()
            else:
                print("Create request failed: ", response_obj.message)

        if response_obj.type == LIST:
            if response_obj.success:
                print("Client action: Got 'list' response from server:", response_obj.data)
            else:
                print("List request failed: ", response_obj.message)

