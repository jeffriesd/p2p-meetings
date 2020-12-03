from socket import *
import threading
from constants import * 

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

    def __init__(self, name):
        self.room_name = name

        # maintain dictionary of tcp connections 
        # (socket objects) keyed on ip addr
        self.connections = {}

        # maintain usernames for each peer
        # (maps ip addr to username)
        self.usernames = {}

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
        self.question_threads_keep_alive = {}

    def wait_for_connections(self):
        """
        Wait for incoming tcp connection requests, 
        then send some test data when they connect.
        """
        server_socket = socket(AF_INET, SOCK_STREAM)
        server_socket.bind(('', P2P_PORT))
        server_socket.listen(MAX_QUEUED_REQUESTS)

        # TODO REMOVE THIS
        # FOR DEBUGGING
        server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

        # TODO put a limit on the number of simultaneous connections 

        while True:
            connection_socket, addr = server_socket.accept()
            print("Got a new connection")

            connection_msg = "You are connected to host %s!" % self.room_name
            connection_socket.send(connection_msg.encode())

            
            # TODO check if username already exists
            #
            # TODO perform error handling (what if bytes are malformed, etc)
        
            # first message sent is the new client's username
            username_bytes = connection_socket.recv(1024)
            # add username to list 
            self.usernames[addr] = username_bytes.decode()

            # set number of warnings to 0 
            self.user_warnings[addr] = 0

            # add this connection to the list
            self.connections[addr] = connection_socket
            
            # start thread to listen for questions from this client
            question_thread = threading.Thread(target=self.listen_for_question, args=(addr,))
            self.question_threads[addr] = question_thread
            self.question_threads_keep_alive[addr] = True
            question_thread.start()

    def listen_for_question(self, addr): 
        """
        Listen for messages (questions) from meeting attendees
        and possibly broadcast them to the entire meeting. 
        If a message contains 'bad words', then the 
        user receives a warning. Three warnings will result 
        in removal from the meeting. 
        """
        while self.question_threads_keep_alive[addr]:
            response = self.connections[addr].recv(1024)

            # TODO add error handling in case connection
            # is closed by host 
            if not response:
                continue

            response_str = response.decode()
            print("New question from client %s: '%s'" % (self.usernames[addr], response_str))

            if all([bw not in response_str for bw in BAD_WORDS]):
                # broadcast message to entire meeting
                self.broadcast_message("Question from %s: '%s'" % (self.usernames[addr], response_str))
            else:
                # give user a warning and possibly remove them 
                self.user_warnings[addr] += 1
                self.direct_message(addr, "This is warning number %s." % self.user_warnings[addr])
                if self.user_warnings[addr] == 3:
                    self.direct_message(addr, "\nGoodbye.")
                    self.close_connection(addr)
        print("thread finished for ", addr)

    def close_connection(self, addr):
        """
        Close a connection with the given address. 
        Kill the thread that was listening to it. 
        Also remove username and reset user warnings
        associated with this address. 
        """

        if addr in self.question_threads:
            # this causes the thread to stop looping
            self.question_threads_keep_alive[addr] = False

            # TODO debug thread join
            #
            # if self.question_threads[addr].is_alive():
            #     threading.Thread.join(self.question_threads[addr])
                # self.question_threads[addr].join()
             #print(self.question_threads[addr])
            # self.question_threads[addr].join()
            # del self.question_threads[addr]

        if addr in self.connections:
            self.connections[addr].close()
            print("Closed connection with", addr)

            # delete entry in dict
            del self.connections[addr]

        # delete username, user warnings count
        if addr in self.usernames:
            del self.usernames[addr]

        self.user_warnings[addr] = 0

    def close_all_connections(self):
        """
        Close all connections and kill 
        thread that's listening for new tcp connections.
        Also clear all entries in self.connections dictionary.
        """
        # stop thread
        self.connection_thread.join()

        for addr in self.connections:
            self.close_connection(addr)

        self.connections = {}


    def direct_message(self, addr, msg_str):
        """
        Send a message to one peer.
        """
        self.connections[addr].send(msg_str.encode())

    def broadcast_message(self, msg_str):
        """
        Given a message as a string, send it to every peer. 
        """
        for peer_addr in self.connections:
            # send message to a single peer
            self.direct_message(peer_addr, msg_str)


class AudienceNode:
    """ 
    Audience nodes make a single connection
    from themselves to the host node. 
    """

    def __init__(self, name, host_addr):
        """
        Connect to host and save reference to the socket object.
        """
        self.username = name 

        self.host_addr = host_addr
        # create new tcp connection with hosting peer
        self.client_socket = socket(AF_INET, SOCK_STREAM)

        try:
            self.client_socket.connect((host_addr, P2P_PORT))
            print("Connected successfully")

            # tell the host our username 
            self.client_socket.send(self.username.encode())
        except:
            self.client_socket.close()
            print("Connection failed")
            return

            
        # listen for messages from host 
        self.connection_thread = threading.Thread(target=self.listen_to_host)
        self.connection_thread.start()

        
    def listen_to_host(self):
        """
        Listen for incoming messages from host.
        """
        # listen for data on tcp connection 
        while True:
            response = self.client_socket.recv(1024)

            # TODO add error handling in case connection
            # is closed by host 
            if not response:
                break
            print("Client %s: New message: %s" % (self.username, response.decode()))
    

    def ask_question(self, msg_str):
        """
        Send a message to the host, which will 
        potentially be broadcast to the entire meeting
        after review. 
        """
        # TODO error handling, wrap sending receiving 
        # in another method 
        # try:
        self.client_socket.send(msg_str.encode())
