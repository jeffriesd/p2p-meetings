from socket import *
import threading
from constants import * 
from server_requests import * 
from socket_util import * 

# Author: Daniel Jeffries
#
# All code is my own, except for some small snippets 
# adapted from the textbook for creating new tcp connections. 
#
# This file implements the peer classes for the star-shaped 
# topology. There are two types of nodes in this topology, 
# the host (central) node and client nodes. 
# In this implementation the host can send messages 
# directly to a particular client, broadcast messages to 
# every client, and receive messages ("questions") from individuals. 

# Maintain a list of 'bad words' 
# that we will use to filter 
# questions from meeting attendees.
# If their question contains no 'bad words',
# then it will be broadcast to the entire meeting. 
#
# if a user uses 'bad words' three times, they are 
# kicked out of the meeting
BAD_WORDS = ["xxx", "yyy", "zzz"]


DEFAULT_USERNAME = "default_user"
MAX_WARNINGS     = 3




# TODO to implement MESH-shaped meeting
#
# what should operations be? 
#   - remove neighbor
#       - who should be able to remove? 
#           - should there be a host role that can get reassigned? 
#   - add neighbor
#   - broadcast to all
#   - direct message 
#
#   - some kind of vote/consensus? that would be cool
#
#
#   - how should usernames be managed? 
#
#   - what should happen when a node is dropped? 
#







###############################################################
## classes for messages between nodes in star-shaped network ##
###############################################################

P2P_MESSAGE_FIELDS = ["type", "message", "data"]
P2P_TEXT   = "p2p_text" # normal text message between nodes 
# P2P_BANNED = "p2p_banned" # user is banned from the meeting 
P2P_USERNAME = "p2p_username"
P2P_MESSAGE_TYPES = [P2P_TEXT, P2P_USERNAME]
#
# maybe have like special types of 'control' messages
# - RegisterUsername 
# - BannedMessage

class P2PMessage(SocketMessage):
    def __init__(self, request_dict={}):
        """
        Construct P2PMessage object from dictionary.
        """
        super().__init__(request_dict, P2P_MESSAGE_FIELDS)

        # initialize empty message
        if "message" not in request_dict:
            self.message = ""

    def is_valid(self):
        return self.type in P2P_MESSAGE_TYPES


class P2PText(P2PMessage):
    """
    Regular (non-control) text message between two p2p nodes. 
    """
    def __init__(self, message_str):
        super().__init__()
        self.message = message_str
        self.type = P2P_TEXT

    def is_valid(self):
        """
        Check that message between p2p nodes has appropriate
        fields and that the data have appropriate types. 
        """
        return self.type is P2P_TEXT \
            and (type(self.message) is str)

class RegisterUsername(P2PMessage):
    """
    Sent from AudienceNode to HostNode to 
    register their username for the meeting.
    The Host associates the username with the address
    of the AudienceNode. 
    """
    def __init__(self, username):
        super().__init__()

        self.type = P2P_USERNAME
        # pass username using data field
        self.data = { "username" : username }

    def is_valid(self):
        return super().is_valid() \
                and (type(self.data.username) is str)


###############################################################
###############################################################


# class UserData:
#     def __init__(self, name, 


# maybe need distinguished host meshnode? 
#  # # #class HostMeshNode


# TODO MESH NODE BEHAVIOR
#
# - how should usernames work? 
# - - should everyone just self-report their username to neighbors
# - - and only use this when printing at endpoints? 
# - - in other words, it should be irrelevant whether 
# - - a particular node gives different names for itself. 
# - - (not that we will exploit this; every user will report the same username to all neighbors) 
#
#
#
#


# TODO create a single abstraction
# for PeerInfo to record
# socket object, username, etc. 
# and then we can just maintain
# a _single_ mapping 
# of (addr,port) -> PeerInfo



class PeerInfo:
    """
    PeerInfo keeps track of 
    the socket object for a peer 
    along with all of its associated application data
    such as username, warnings, etc. 
    """

    def __init__(self, conn_socket, listen_thread, username=DEFAULT_USERNAME):
        self.conn_socket = conn_socket
        self.user_warnings = 0
        self.username = username

        self.listen_thread = listen_thread


class HostNode:
    """
    Mesh host nodes 
    have the privilege to remove users from the meeting. 

    """

    def __init__(self, name, p2p_port):
        self.room_name = name


        # maintain dictionary mapping
        # (addr,port) -> PeerInfo,
        # which contains socket object 
        # and other peer info 
        self.peers = {}

        self.p2p_port = p2p_port

        # wait for connections in a separate thread
        self.connection_thread = threading.Thread(target=self.wait_for_connections)
        self.connection_thread.start()

    def wait_for_connections(self):
        """
        Wait for incoming tcp connection requests, 
        then send some test data when they connect.
        """
        accept_socket = socket(AF_INET, SOCK_STREAM)
        # accept_socket.bind(('', P2P_PORT))
        accept_socket.bind(('', self.p2p_port))
        accept_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1) # FOR DEBUGGING
        accept_socket.listen(MAX_QUEUED_REQUESTS)

        while True:
            connection_socket, addr_port = accept_socket.accept()
            print("Host: received a new connection request")

            welcome_message = P2PText("You are connected to host %s!" % self.room_name)
            send_socket_message(connection_socket, welcome_message)


            # start thread to listen for questions from this peer
            listen_thread = self.make_listen_thread(connection_socket, addr_port)

            # assign default username 
            self.peers[addr_port] = PeerInfo(connection_socket, listen_thread, DEFAULT_USERNAME)

            self.peers[addr_port].listen_thread.start()

    def make_listen_thread(self, connection_socket, addr_port):
        """
        Need to define this as its own method since the lambdas 
        used as arguments to ListenThread need to capture some variables (addr_port). 

        The while loop in wait_for_connections makes inlining this 
        method impossible due to scoping/binding issues. 
        """
        return ListenThread(P2PMessage, connection_socket, \
                    # function to perform on incoming messages
                    lambda pm: self.handle_p2p_message(addr_port, pm), \
                    # cleanup to perform when client closes connection
                    lambda: self.remove_user(addr_port))
 

    def handle_p2p_message(self, addr_port, message_obj):
        """
        Handle a validated P2PMessage object, 
        split by cases on the type of the message. 

        addr_port - address of socket that produced this incoming message
        message_obj - P2PMessage object 
        """

        if message_obj.type == P2P_TEXT:
            # regular text from AudienceNode to HostNode
            self.handle_question(addr_port, message_obj.message)

        elif message_obj.type == P2P_USERNAME:
            # update username
            self.peers[addr_port].username = message_obj.data.username

        else:
            print("Unknown message type: ", message_obj.type)


    def unknown_peer_error(self, addr_port):
        return "Error: Unknown peer - %s" % (addr_port,)

    def set_username(self, addr_port, user_str):
        """ 
        Safely set username
        """
        if addr_port in self.peers:
            self.peers[addr_port].username = user_str
        else:
            print(self.unknown_peer_error(addr_port), "for set_username")
    
    def get_username(self, addr_port):
        """
        Safely get username by checking first if 
        peer is still connected
        """
        if addr_port in self.peers:
            return self.peers[addr_port].username

        return self.unknown_peer_error(addr_port)

    def give_warning(self, addr_port):
        """
        Safely update user warnings
        """
        if addr_port in self.peers:
            self.peers[addr_port].user_warnings += 1
        else:
            print(self.unknown_peer_error(addr_port), "for give_warning")

    def get_user_warnings(self, addr_port):
        """
        Safely get user warnings
        """
        if addr_port in self.peers:
            return self.peers[addr_port].user_warnings 

        print(self.unknown_peer_error(addr_port), "for get_user_warnings")
        return 0

    def handle_question(self, addr_port, question_str):
        """
        Listen for messages (questions) from meeting attendees
        and possibly broadcast them to the entire meeting. 
        If a message contains 'bad words', then the 
        user receives a warning. Three warnings will result 
        in removal from the meeting. 
        """

        print("New question from client %s: '%s'" % (self.get_username(addr_port), question_str))

        if all([bw not in question_str for bw in BAD_WORDS]):
            # broadcast message to entire meeting
            self.broadcast_message("Question from %s: '%s'" % (self.get_username(addr_port), question_str))
        else:
            # give user a warning and possibly remove them 
            self.give_warning(addr_port) 
            self.direct_message(addr_port, "This is warning number %s." % self.get_user_warnings(addr_port))

            if self.get_user_warnings(addr_port) == MAX_WARNINGS:
                self.direct_message(addr_port, "\nGoodbye.")
                # close connection and delete any information about client from 'addr_port'
                self.remove_user(addr_port)
     
    def remove_user(self, addr_port):
        """
        Close a connection with the given address 
        and remove any information associated with it. 
        The thread that was listening for messages from this
        address is stopped. 
        """

        if addr_port in self.peers:
            peer = self.peers[addr_port]
            # this causes the thread to stop executing
            peer.listen_thread.stop()

            # close socket connection
            peer.conn_socket.close()
            del self.peers[addr_port]
        else:
            print(self.unknown_peer_error(addr_port), "for remove_user")

    def remove_all_users(self):
        """
        Close all connections and kill 
        thread that's listening for new tcp connections.
        Also clear all entries in self.connections dictionary.
        """
        # stop thread
        self.connection_thread.join()

        for addr_port in self.peers:
            self.remove_user(addr_port)

        self.peers = {}


    def direct_message(self, addr_port, msg_str):
        """
        Create a P2PMessage object and send it
        over a socket. 
        """
        if addr_port in self.peers:
            p2p_msg = P2PText(msg_str)
            if p2p_msg.is_valid():
                send_socket_message(self.peers[addr_port].conn_socket, p2p_msg)
            else:
                print("Invalid argument to P2PText: ", msg_str)
        else:
            print(self.unknown_peer_error(addr_port), "for direct_message")

    def broadcast_message(self, msg_str):
        """
        Given a message as a string, send it to every peer. 
        """
        for addr_port in self.peers:
            # send message to a single peer
            self.direct_message(addr_port, msg_str)




class AudienceNode:
    """ 
    Audience nodes make a single connection
    from themselves to the host node. 
    """

    def __init__(self, name, host_addr, host_port):
        """
        Connect to host and save reference to the socket object.
        """

        self.host_addr = host_addr
        self.host_port = host_port
        # self.host_addr = host_addr
        # create new tcp connection with hosting peer
        self.client_socket = socket(AF_INET, SOCK_STREAM)

        try:
            self.client_socket.connect((host_addr, host_port))
            print("Connected successfully to host.")
        except:
            self.client_socket.close()
            print("Connection with meeting host failed. Host_addr = ", host_addr)
            return

        # tell the host our preferred username 
        send_socket_message(self.client_socket, RegisterUsername(name))

        # listen for messages from host 
        self.connection_thread = \
            ListenThread(P2PMessage, \
                        self.client_socket, \
                        lambda pm: print("New message from host:", pm.message), \

                        # TODO do something to reconnect with central server 
                        lambda: print("Connection with meeting host closed."))

        self.connection_thread.start()

    
    def ask_question(self, msg_str):
        """
        Send a message to the host, which will 
        potentially be broadcast to the entire meeting
        after review. 
        """
        send_socket_message(self.client_socket, P2PText(msg_str))


    # def send_text(self, peer_addr, msg_str):
    #     
    #     if peer_addr in self.connections:
    #         # TODO check that connection is still open ,
    #         # if it's closed then remove it from self.connections

    #         send_socket_message(self.connections[peer_addr], P2PText(msg_str))




