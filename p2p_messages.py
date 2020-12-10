from server_messages import * 

###############################################################
##### classes for messages between nodes in a p2p network #####
###############################################################

# These classes add some structure and error-checking 
# to the message-passing mechanism between p2p nodes. 
#
# Messages are broken up into classes based on their purpose. 
# P2PText represents a simple text message, while other 
# classes (e.g. P2P_REGISTER_USERNAME) are used for sharing
# particular kinds of data.


P2P_MESSAGE_FIELDS = ["type", "message", "data"]
P2P_TEXT   = "p2p_text" # normal text message between nodes 
P2P_REGISTER_USERNAME = "p2p_username"
P2P_REGISTER_PORT= "p2p_register_port"
P2P_MESH_CONNECT = "p2p_mesh_connect"
P2P_MESSAGE_TYPES = [P2P_TEXT, P2P_REGISTER_USERNAME, P2P_MESH_CONNECT, P2P_REGISTER_PORT]

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
    Sent from StarAudienceNode to StarHostNode to 
    register their username for the meeting.
    The host associates the username with the address
    of the StarAudienceNode. 
    """
    def __init__(self, username):
        super().__init__()

        self.type = P2P_REGISTER_USERNAME
        # pass username using data field
        self.data = { "username" : username }

    def is_valid(self):
        return super().is_valid() \
                and (type(self.data.username) is str)

class RegisterPort(P2PMessage):
    """
    Sent from MeshAudienceNode to MeshHostNode to 
    register their p2p port for the meeting. 
    (The port via which other peers will 
    connect to this peer in the full-mesh network.)
    """
    def __init__(self, meeting_port):
        super().__init__()

        self.type = P2P_REGISTER_PORT
        # pass username using data field
        self.data = { "p2p_port" : meeting_port }

    def is_valid(self):
        return super().is_valid() \
                and (type(self.data.meeting_port) is int)

class MeshConnect(P2PMessage):
    """
    MeshConnect message is sent from MeshHostNode
    to MeshAudienceNode and contains the list
    of all other peers addresses in the mesh. 

    This is shared from the meeting host to the new peer 
    so that the server only needs to keep track of
    the host for each meeting. 
    """
        
    def __init__(self, addr_ports):
        super().__init__()
        self.type = P2P_MESH_CONNECT
        self.data = { "hosts" : addr_ports }

    def is_valid(self):
        return super().is_valid() \
            and (type(self.data.hosts) is list)


