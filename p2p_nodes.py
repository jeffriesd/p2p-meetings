from socket import *
import threading
from constants import * 
from socket_util import * 
from server_messages import * 

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
#
#
# TODO complete description of Mesh meetings etc. 



###############################################################
###############################################################
class PeerInfo:
    """
    PeerInfo keeps track of 
    the socket object for a peer 
    along with all of its associated application data
    such as username, warnings, etc. 
    """

    def __init__(self, conn_socket, listen_thread, listening_port, username=DEFAULT_USERNAME):
        self.conn_socket = conn_socket
        self.user_warnings = 0
        self.username = username

        self.listen_thread = listen_thread

        self.listening_port = listening_port

        self.p2p_port = None

class HostNode:
    """
    host nodes 
    listen for new tcp connection requests, and then 
    create new sockets for each newly connected peer 

    this class specializes to both star-shaped and
    full-mesh host nodes. 
    """

    def __init__(self, username, meetingID, p2p_port):
        self.username = username
        self.meetingID = meetingID

        # maintain dictionary mapping
        # (addr,port) -> PeerInfo,
        # which contains socket object 
        # and other peer info 
        self.peers = {}

        # this is the port used for incoming traffic 
        # to this node 
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
        accept_socket.listen()

        while True:
            connection_socket, addr_port = accept_socket.accept()
            # DEBUG print("Host: received a new connection request from ", addr_port)

            # tell new peer our username
            send_socket_message(connection_socket, RegisterUsername(HOST_USERNAME))

            welcome_message = P2PText(self.welcome_message())
            send_socket_message(connection_socket, welcome_message)

            self.add_new_peer(connection_socket, addr_port)

    def welcome_message(self):
        return "You are connected to host of meeting %s." % self.meetingID

    def add_new_peer(self, connection_socket, addr_port, username=DEFAULT_USERNAME):
        """
        Create a new peer connection object and add
        it to self.peers. First check if this peer is already connected. 
        """
        if type(addr_port) is list:
            addr_port = tuple(addr_port)
            
        if addr_port in self.peers:
            print("Error: Already have peer connection with " , addr_port)
            traceback.print_stack()
            return

        # start thread to listen for questions from this peer
        listen_thread = self.make_listen_thread(connection_socket, addr_port)

        # assign default username 
        self.peers[addr_port] = PeerInfo(connection_socket, listen_thread, username)
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
 
    def unknown_peer_error(self, addr_port):
        """ 
        Formatted error message for when a peer
        with a particular (addr,port) doesn't have 
        a corresponding entry in self.peers 
        """
        return "Error: Unknown peer - %s" % (addr_port,)

    def set_p2p_port(self, addr_port, p2p_port):
        """
        Safely set p2p port for a peer. 
        """
        if addr_port in self.peers:
            self.peers[addr_port].p2p_port = p2p_port
        else:
            print(self.unknown_peer_error(addr_port), "for set_p2p_port")

    def set_username(self, addr_port, user_str):
        """ 
        Safely set username of a peer.
        """
        if addr_port in self.peers:
            self.peers[addr_port].username = user_str
        else:
            print(self.unknown_peer_error(addr_port), "for set_username")
    
    def get_username(self, addr_port):
        """
        Safely get username by checking first if 
        peer is still connected.
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

    def direct_message_username(self, username, message_str):
        """
        Send a peer a message based on their unique username. 
        """
        for addr_port in self.peers:
            if self.peers[addr_port].username == username:
                self.direct_message(addr_port, message_str)
                break
        # python for-else (else body executes if break never happens)
        else:
            print("Error: No peer with username '%s'" % username)


    def broadcast_message(self, msg_str):
        """
        Given a message as a string, send it to every peer. 
        """
        for addr_port in self.peers:
            # send message to a single peer
            self.direct_message(addr_port, msg_str)



class StarHostNode(HostNode):
    """
    StarHostNode has all the same behavior as HostNode
    """
    pass


#######################################################
#######################################################

class MeshAudienceNode(HostNode):
    """
    MeshAudienceNodes are the same as MeshHostNodes in almost all aspects:
    - they wait for incoming connection requests, and when they accept a new 
      connection from a peer, they create a new PeerInfo object
      and start listening for messages from the new peer. 

    The primary difference is in the initialization. 
    A MeshAudienceNode must send a connection request 
    to every other member of the network so the 
    mesh becomes fully connected again. 

    MeshAudienceNode always broadcasts its preferred 
    username to all peers when sending these connection requests.
    """

    # override constructor to add connection to host
    def __init__(self, username, host_addr, host_port, p2p_port):
        # initialize username, self.meetingID, self.peers, 
        # self.p2p_port, and self.connection_thread
        #
        # meetingID doesn't matter for MeshAudienceNode, so just supply -1
        super().__init__(username, -1, p2p_port)

        self.host_addr = host_addr
        self.host_port = host_port

        # connect to host 
        self.host_socket = connect_to_peer((host_addr, host_port))
        if not self.host_socket: # if connection failed
            return

        # tell the host our preferred username 
        send_socket_message(self.host_socket, RegisterUsername(username))
        # tell the host our p2p socket
        send_socket_message(self.host_socket, RegisterPort(p2p_port))
        # send a welcome message for the host user to see we have connected
        send_socket_message(self.host_socket, P2PText(self.welcome_message()))

        # create new PeerInfo object for host and start listening 
        # to its socket 
        self.add_new_peer(self.host_socket, (host_addr, host_port), username=HOST_USERNAME)

    def welcome_message(self):
        return "You are connected to user '%s'" % self.username

    def handle_p2p_message(self, addr_port, message_obj):
        """
        MeshAudienceNode

        Handle a validated P2PMessage object, 
        split by cases on the type of the message. 

        addr_port - address of socket that produced this incoming message
        message_obj - P2PMessage object 
        """

        if message_obj.type == P2P_TEXT:
            # regular text from StarAudienceNode to HostNode
            # self.handle_question(addr_port, message_obj.message)
            peer_username = self.get_username(addr_port)
            print("%s says: %s" % (peer_username, message_obj.message))

        elif message_obj.type == P2P_REGISTER_USERNAME:
            # update username of this peer
            self.set_username(addr_port, message_obj.data.username)

        elif message_obj.type == P2P_MESH_CONNECT:
            # meeting host gives us list of (addr,port) pairs 
            # so we can connect to the rest of the network
            self.connect_to_mesh(message_obj.data.hosts)
        else:
            print("Unknown message type: ", message_obj.type)


    def connect_to_mesh(self, peer_addr_ports):
        """
        Make a connection request to every peer 
        in the provided list 
        """
        
        for addr_port in peer_addr_ports:
            conn_socket = connect_to_peer(addr_port)
            
            # add new peer object to self.peers and create a new
            # thread to listen for messages from this peer
            # 
            # Now there is a two-way connection from this user
            # to the peer at addr_port
            if conn_socket:
                self.add_new_peer(conn_socket, addr_port)

                # also broadcast username to these peers
                send_socket_message(conn_socket, RegisterUsername(self.username))

                # send connection message
                send_socket_message(conn_socket, P2PText(self.welcome_message()))



class MeshHostNode(HostNode):
    """
    Mesh host node simply waits for incoming tcp requests.
    Once a new connection is made with a peer P, the host 
    can broadcast messages to P and all other connected peers. 

    Non-host nodes are responsible for creating the tcp connection
    from the host to themselves. 


    If the host leaves the meeting, then it will no longer 
    be listed by the server and so other users can no longer join. 
    However, the remaining members of the mesh meeting 
    should still be able to communicate. 
    """

    def wait_for_connections(self):
        """
        Wait for incoming tcp connection requests, 
        then send some test data when they connect.

        Since incoming tcp connection requests are 
        users trying to join the full-mesh network, 
        MeshHostNode will send the new user 
        a list of peer ips. 
        """
        accept_socket = socket(AF_INET, SOCK_STREAM)
        accept_socket.bind(('', self.p2p_port))
        accept_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1) # FOR DEBUGGING
        accept_socket.listen()

        while True:
            connection_socket, addr_port = accept_socket.accept()
            # DEBUG print("Host: received a new connection request from ", addr_port)

            # tell new peer our username
            send_socket_message(connection_socket, RegisterUsername(HOST_USERNAME))

            welcome_message = P2PText(self.welcome_message())
            send_socket_message(connection_socket, welcome_message)

            # send addresses of other peers when a new user connects,
            # so new user can connect to all of the peers in the list 
            other_peer_addr_ports = []
            for addr_prt in self.peers:
                peer_obj = self.peers[addr_prt] 
                if peer_obj.p2p_port: # peer must have registered p2p port with host 
                    other_peer_addr_ports.append((addr_prt[0], peer_obj.p2p_port))


            self.add_new_peer(connection_socket, addr_port)
            send_socket_message(connection_socket, MeshConnect(other_peer_addr_ports))
    


    def handle_p2p_message(self, addr_port, message_obj):
        """
        Handle a validated P2PMessage object, 
        split by cases on the type of the message. 

        addr_port - address of socket that produced this incoming message
        message_obj - P2PMessage object 
        """

        if message_obj.type == P2P_TEXT:
            # regular text from StarAudienceNode to HostNode
            # self.handle_question(addr_port, message_obj.message)
            peer_username = self.get_username(addr_port)
            print("%s says: %s" % (peer_username, message_obj.message))

        elif message_obj.type == P2P_REGISTER_USERNAME:
            # update username of this peer
            self.set_username(addr_port, message_obj.data.username)

        elif message_obj.type == P2P_MESH_CONNECT:
            # host shouldn't be receiving this, so ignore it
            pass
        elif message_obj.type == P2P_REGISTER_PORT:
            # register p2p port for this peer
            # so future peers can connect to it
            
            self.set_p2p_port(addr_port, message_obj.data.p2p_port)

        else:
            print("Unknown message type: ", message_obj.type)


#######################################################
#######################################################



class StarHostNode(HostNode):
    """
    Star host nodes accept new peer connections and 
    and broadcast messages to the network as the
    central node in a star topology. 

    Star host nodes can also remove close connections 
    with peers to kick a user out of the meeting. 

    Meeting attendees (peers) can ask questions to 
    the host. If the question doesn't contain any
    'bad words', then the question is broadcast
    to the entire class. Otherwise, the 
    user receives a warning. After three warnings, 
    the user is removed from the meeting.
    """

    def handle_p2p_message(self, addr_port, message_obj):
        """
        Handle a validated P2PMessage object, 
        split by cases on the type of the message. 

        addr_port - address of socket that produced this incoming message
        message_obj - P2PMessage object 
        """

        if message_obj.type == P2P_TEXT:
            # regular text from StarAudienceNode to HostNode
            self.handle_question(addr_port, message_obj.message)

        elif message_obj.type == P2P_REGISTER_USERNAME:
            # update username
            self.set_username(addr_port, message_obj.data.username)

        elif message_obj.type == P2P_MESH_CONNECT:
            # star host shouldn't be receiving this, so ignore it
            pass
        else:
            print("Unknown message type: ", message_obj.type)


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
     


class StarAudienceNode:
    """ 
    StarAudienceNodes make a single connection
    from themselves to the host node in a star-shaped meeting. 
    """

    def __init__(self, username, host_addr, host_port):
        """
        Connect to host and save reference to the socket object.
        """

        self.host_addr = host_addr
        self.host_port = host_port

        # create new tcp connection with hosting peer
        self.client_socket = connect_to_peer((host_addr, host_port))
        if self.client_socket is None: # connection failed
            return


        # tell the host our preferred username 
        send_socket_message(self.client_socket, RegisterUsername(username))

        # listen for messages from host 
        self.host_listen_thread = \
            ListenThread(P2PMessage, \
                        self.client_socket, \
                        lambda pm: print("New message from host:", pm.message), \
                        lambda: print("Connection with meeting host closed."))

        self.host_listen_thread.start()
    
    def ask_question(self, msg_str):
        """
        Send a message to the host, which will 
        potentially be broadcast to the entire meeting
        after review. 
        """
        send_socket_message(self.client_socket, P2PText(msg_str))


