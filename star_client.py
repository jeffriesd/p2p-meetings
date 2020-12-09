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



# TODO in this file (12/04): 
#
#   - convert host/audience messaging to SocketMesage
#
#   - convert question threads to ListenThread
#       - TODO THIS 
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

class HostNode:
    """
    Host nodes accept new peer connections and 
    and broadcast messages to the network as the
    central node in a star topology. 

    Host nodes can also remove close connections 
    with peers to kick a user out of the meeting. 

    Meeting attendees (peers) can ask questions to 
    the host. If the question doesn't contain any
    'bad words', then the question is broadcast
    to the entire class. Otherwise, the 
    user receives a warning. After three warnings, 
    the user is removed from the meeting.
    """

    def __init__(self, name, p2p_port):
        self.room_name = name

        # maintain dictionary of tcp connections 
        # (socket objects) keyed on ip addr
        self.connections = {}

        # maintain usernames for each peer
        # (maps ip addr to username)
        self.usernames = {}

        self.p2p_port = p2p_port

        # number of warnings (default to 0)
        # given to each user 
        # (maps ip addr to integer)
        self.user_warnings = {}

        # wait for connections in a separate thread
        self.connection_thread = threading.Thread(target=self.wait_for_connections)
        self.connection_thread.start()


        # listen to questions from users in 
        # independent threads
        # (maps ip addr to thread object)
        self.question_threads = {}

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

            # assign default username 
            self.register_username(addr_port, DEFAULT_USERNAME)

            # set number of warnings to 0 
            self.user_warnings[addr_port] = 0

            # add this connection to the list
            self.connections[addr_port] = connection_socket
            
            # start thread to listen for questions from this client
            question_thread = self.make_listen_thread(connection_socket, addr_port)
            self.question_threads[addr_port] = question_thread
            question_thread.start()

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
            # regular text from AudienceNode to HostNode is 
            # viewed as a "question"
            self.handle_question(addr_port, message_obj.message)

        elif message_obj.type == P2P_USERNAME:
            self.register_username(addr_port, message_obj.data.username)

        else:
            print("Unknown message type: ", message_obj.type)

    def register_username(self, addr_port, user_str):
        """
        Add an entry in self.usernames to associate 
        the address of a meeting attendee with a username. 
        If the username is already taken, we add an underscore.
        """
        # get unique username 
        while user_str in set(self.usernames.values()):
            user_str = user_str + "_"

        # associate user_str with addr 
        self.usernames[addr_port] = user_str


    def handle_question(self, addr_port, question_str):
        """
        Listen for messages (questions) from meeting attendees
        and possibly broadcast them to the entire meeting. 
        If a message contains 'bad words', then the 
        user receives a warning. Three warnings will result 
        in removal from the meeting. 
        """

        print("New question from client %s: '%s'" % (self.usernames[addr_port], question_str))

        if all([bw not in question_str for bw in BAD_WORDS]):
            # broadcast message to entire meeting
            self.broadcast_message("Question from %s: '%s'" % (self.usernames[addr_port], question_str))
        else:
            # give user a warning and possibly remove them 
            self.user_warnings[addr_port] += 1
            self.direct_message(addr_port, "This is warning number %s." % self.user_warnings[addr_port])

            if self.user_warnings[addr_port] == MAX_WARNINGS:
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

        if addr_port in self.question_threads:
            # this causes the thread to stop executing
            self.question_threads[addr_port].stop()
            del self.question_threads[addr_port] 

        if addr_port in self.connections:
            self.connections[addr_port].close()
            print("Closed connection with", addr_port)

            # delete entry in dict
            del self.connections[addr_port]

        # delete username, user warnings count
        if addr_port in self.usernames:
            del self.usernames[addr_port]

        if addr_port in self.user_warnings:
            del self.user_warnings[addr_port] 

    def remove_all_users(self):
        """
        Close all connections and kill 
        thread that's listening for new tcp connections.
        Also clear all entries in self.connections dictionary.
        """
        # stop thread
        self.connection_thread.join()

        for addr_port in self.connections:
            self.remove_user(addr_port)

        # clear connections dictionary 
        self.connections = {}


    def direct_message(self, addr_port, msg_str):
        """
        Create a P2PMessage object and send it
        over a socket. 
        """
        p2p_msg = P2PText(msg_str)
        if p2p_msg.is_valid():
            send_socket_message(self.connections[addr_port], p2p_msg)
        else:
            print("Invalid argument to P2PText: ", msg_str)

    def broadcast_message(self, msg_str):
        """
        Given a message as a string, send it to every peer. 
        """
        for peer_addr_port in self.connections:
            # send message to a single peer
            self.direct_message(peer_addr_port, msg_str)


class AudienceNode:
    """ 
    Audience nodes make a single connection
    from themselves to the host node. 
    """

    def __init__(self, name, host_addr, host_port):
        """
        Connect to host and save reference to the socket object.
        """

        # self.host_addr = host_addr
        # self.host_port = host_port
        #
        # dont really need these?
    

        # create new tcp connection with hosting peer
        self.client_socket = socket(AF_INET, SOCK_STREAM)

        try:
            self.client_socket.connect((host_addr, host_port))
            print("Connected successfully")
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




