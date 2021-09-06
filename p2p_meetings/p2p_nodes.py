from socket import *
import threading
from p2p_meetings.constants import * 
from p2p_meetings.socket_util import * 
from p2p_meetings.message_types import * 

# Author: Daniel Jeffries
#
# All code is my own, except for some small snippets 
# adapted from the textbook for creating new tcp connections. 
#
# This file implements the peer classes for the star-shaped 
# topology and the full-mesh toplogy. 
#
# Star-shaped topology:
#       There are two types of nodes in this topology, 
#       the host (central) node and 'audience' or 'client' nodes. 
#       In this implementation the host can send messages 
#       directly to a particular client, broadcast messages to 
#       every client, and receive messages ("questions") from individuals. 
#       Maintain a list of 'bad words' 
#       that we will use to filter 
#       questions from meeting attendees.
#       If their question contains no 'bad words',
#       then it will be broadcast to the entire meeting. 
#
#       if a user uses 'bad words' three times, they are 
#       kicked out of the meeting
#
#
# Full-mesh topology:
#       There are also two types of nodes for the full-mesh topology,
#       but they are closer in behavior than the host/audience nodes in the  
#       star-shaped networks. 
#
#       The host is responsible for keeping track of all the peers
#       and sending a list of peer addresses when a new 
#       peer wants to join. Other than this, the host does not
#       have an centralized control over the network
#       like the StarHost does (e.g., StarHost can kick people out).
#
#       Peers in the full-mesh network can broadcast messages
#       to the entire network, or send a private message to a particular user. 
#


class PeerInfo:
    """
    PeerInfo keeps track of 
    the socket object for a peer 
    along with all of its associated application data
    such as username, warnings, etc. 
    """

    def __init__(self, conn_socket, listen_thread, listen_p2p_port, username=DEFAULT_USERNAME):
        self.conn_socket = conn_socket
        self.user_warnings = 0
        self.username = username

        self.listen_thread = listen_thread

        self.listen_p2p_port = listen_p2p_port

class HostNode:
    """
    host nodes 
    listen for new tcp connection requests, and then 
    create new sockets for each newly connected peer 

    this class specializes to both star-shaped and
    full-mesh host nodes. 
    """

    def __init__(self, username, meetingID, listen_p2p_port):
        self.username = username
        self.meetingID = meetingID

        # maintain dictionary mapping
        # (addr,port) -> PeerInfo,
        # which contains socket object 
        # and other peer info 
        self.peers = {}

        # this is the port used for incoming traffic 
        # to this node 
        self.listen_p2p_port = listen_p2p_port

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
        accept_socket.bind(('', self.listen_p2p_port))
        accept_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1) # FOR DEBUGGING
        accept_socket.listen()

        while True:
            # addr_port is address and port 
            # of newly connected peer 
            connection_socket, addr_port = accept_socket.accept()

            # tell new peer our username
            send_socket_message(connection_socket, RegisterUsername(self.username))

            welcome_message = P2PText(self.welcome_message())
            send_socket_message(connection_socket, welcome_message)

            # host node adds new peer, no username established yet
            self.add_new_peer(connection_socket, addr_port)

    def welcome_message(self):
        """Message to send every time a peer joins a network"""
        return "You are connected to host of meeting %s." % self.meetingID

    def add_new_peer(self, connection_socket, addr_port, username=DEFAULT_USERNAME):
        """
        Create a new peer connection object and add
        it to self.peers. First check if this peer is already connected. 
        """
        if type(addr_port) is list:
            addr_port = tuple(addr_port)
            
        if addr_port in self.peers:
            logging.error("Error: Already have peer connection with %s" , str(addr_port))
            return

        # start thread to listen for questions from this peer
        listen_thread = self.make_listen_thread(connection_socket, addr_port)

        # assign default username 
        self.peers[addr_port] = \
            PeerInfo(connection_socket, listen_thread, addr_port, username=username)
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
 
    def unknown_peer_error(self, addr_port, msg):
        """ 
        Log formatted error message for when a peer
        with a particular (addr,port) doesn't have 
        a corresponding entry in self.peers 
        """
        logging.error("Error: Unknown peer - %s - %s", addr_port, msg)

    def set_p2p_port(self, addr_port, listen_p2p_port):
        """
        Safely set p2p port for a peer. 
        """
        if addr_port in self.peers:
            self.peers[addr_port].listen_p2p_port = listen_p2p_port
        else:
            self.unknown_peer_error(addr_port, "for set_p2p_port")

    def set_username(self, addr_port, user_str):
        """ 
        Safely set username of a peer.
        """
        if addr_port in self.peers:
            self.peers[addr_port].username = user_str
        else:
            self.unknown_peer_error(addr_port, "for set_username")
    
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
            self.unknown_peer_error(addr_port, "for give_warning")

    def get_user_warnings(self, addr_port):
        """
        Safely get user warnings
        """
        if addr_port in self.peers:
            return self.peers[addr_port].user_warnings 

        self.unknown_peer_error(addr_port, "for get_user_warnings")
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
            ##  peer.conn_socket.close()
            safe_shutdown_close(peer.conn_socket)
            del self.peers[addr_port]
        else:
            self.unknown_peer_error(addr_port, "for remove_user")

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
                logging.error("Invalid argument to P2PText: %s", str(msg_str))
        else:
            self.unknown_peer_error(addr_port, "for direct_message")

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
            logging.error("Error: No peer with username '%s'", username)


    def broadcast_message(self, msg_str):
        """
        Given a message as a string, send it to every peer. 
        """
        for addr_port in self.peers:
            # send message to a single peer
            self.direct_message(addr_port, msg_str)




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

    For a client to join a mesh network, the following steps must occur: 
    - client makes request to join (gives meeting room # and username)
    - server receives request, if requested meeting room exists and 
      requested username is not taken, server responds with address/port of host 
    - client receives response which contains: 
      - addr/port of requested p2p meeting host 
      - requested username 
      - type of meeting requested 
      - if joining mesh, a unique port (assigned by central server) 
        on which the client can listen for new connections by future clients 
        joining the same mesh. 

    - once client receives response, it 
      creates new Mesh/StarAudienceNode object, 
      which causes it to connect to the host 
    - client sends host its username and a welcome/connection message. 

    - in mesh case, newly joining client 
      also sends host its listening port, which 
      the host will disseminate to future clients joining the same mesh 
    - finally, the host responds with a list of 
      (listening) ports/addresses with one entry 
      for each non-host peer in the mesh 
    - the newly joined mesh client will then connect
      to the other peers in the mesh 
      (see P2P_MESH_CONNECT case of handle_p2p_message below)
    """

    # override constructor to add connection to host
    def __init__(self, username, host_addr, host_port, listen_p2p_port):
        # initialize username, self.meetingID, self.peers, 
        # self.listen_p2p_port, and self.connection_thread
        #
        # meetingID doesn't matter for MeshAudienceNode, so just supply -1
        super().__init__(username, -1, listen_p2p_port)

        self.host_addr = host_addr
        self.host_port = host_port

        # connect to host 
        self.host_socket = connect_to_peer((host_addr, host_port))
        if not self.host_socket: # if connection failed
            return

        # tell the host our preferred username 
        send_socket_message(self.host_socket, RegisterUsername(username))
        # tell the host our p2p socket (for other peers to establish 
        # new connections). this calls host to call HostNode.set_p2p_port
        send_socket_message(self.host_socket, RegisterPort(listen_p2p_port))
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
            logging.info("%s says: %s", str(peer_username), str(message_obj.message))

        elif message_obj.type == P2P_REGISTER_USERNAME:
            # update username of this peer
            self.set_username(addr_port, message_obj.data.username)

        elif message_obj.type == P2P_MESH_CONNECT:
            # meeting host gives us list of (addr,port) pairs 
            # so we can connect to the rest of the network
            self.connect_to_mesh(message_obj.data.hosts)
        else:
            logging.error("Unknown message type: %s", str(message_obj.type))


    def connect_to_mesh(self, peer_addr_ports):
        """
        Make a connection request to every peer 
        in the provided list 
        """
        
        for listen_p2p_port in peer_addr_ports:
            conn_socket = connect_to_peer(listen_p2p_port)
            
            # add new peer object to self.peers and create a new
            # thread to listen for messages from this peer
            # 
            # Now there is a two-way connection from this user
            # to the peer at addr_port
            if conn_socket:
                # non-host node is connecting to other nodes
                # in network, 
                self.add_new_peer(conn_socket, listen_p2p_port)

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
        accept_socket.bind(('', self.listen_p2p_port))
        accept_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1) # FOR DEBUGGING
        accept_socket.listen()

        while True:
            connection_socket, addr_port = accept_socket.accept()

            # tell new peer our username
            send_socket_message(connection_socket, RegisterUsername(HOST_USERNAME))

            welcome_message = P2PText(self.welcome_message())
            send_socket_message(connection_socket, welcome_message)

            # send addresses of other peers when a new user connects,
            # so new user can connect to all of the peers in the list 
            other_peer_addr_ports = []
            for addr_prt in self.peers:
                peer_obj = self.peers[addr_prt] 
                if peer_obj.listen_p2p_port: # peer must have registered p2p port with host 
                    other_peer_addr_ports.append((addr_prt[0], peer_obj.listen_p2p_port))

            # mesh host adds new peer to its network. here addr_port 
            # is the address/port for the tcp connection from the 
            # host to this new node. this will get updated 
            # in self.peers 
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
            logging.info("%s says: %s", str(peer_username), str(message_obj.message))

        elif message_obj.type == P2P_REGISTER_USERNAME:
            # update username of this peer
            self.set_username(addr_port, message_obj.data.username)

        elif message_obj.type == P2P_MESH_CONNECT:
            # host shouldn't be receiving this, so ignore it
            pass
        elif message_obj.type == P2P_REGISTER_PORT:
            # register p2p port for this peer
            # so future peers can connect to it
            # (by connecting the this p2p listening port) 
            self.set_p2p_port(addr_port, message_obj.data.listen_p2p_port)

        else:
            logging.error("Unknown message type: %s", str(message_obj.type))


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
        elif message_obj.type == P2P_REGISTER_PORT:
            # star host shouldn't be receiving this, so ignore it
            pass
        else:
            logging.error("Unknown message type: %s", str(message_obj.type))


    def handle_question(self, addr_port, question_str:str):
        """
        Listen for messages (questions) from meeting attendees
        and possibly broadcast them to the entire meeting. 
        If a message contains 'bad words', then the 
        user receives a warning. Three warnings will result 
        in removal from the meeting. 
        """

        logging.info("New question from client %s: '%s'", self.get_username(addr_port), question_str)

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
                        lambda pm: logging.info("New message from host: %s", pm.message), \
                        lambda: logging.info("Connection with meeting host closed."))

        self.host_listen_thread.start()
    
    def ask_question(self, msg_str):
        """
        Send a message to the host, which will 
        potentially be broadcast to the entire meeting
        after review. 
        """
        send_socket_message(self.client_socket, P2PText(msg_str))


