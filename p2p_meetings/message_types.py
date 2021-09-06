import json
from socket import * 
from p2p_meetings.constants import * 
import logging 
from typing import Callable 

##########################################################
##  wrap up request data in a class for abstraction     ##
##  purposes, but make it easy to convert a dictionary  ##
##  into SocketMessage object and vice versa.           ##
##########################################################

def decode_message(message_str:bytes, MessageType:Callable[[dict], "SocketMessage"]):
    """
    Decode some json (in the form of a bytestring)
    and return an object of type MessageType.
    Return None on failure. 
    """
    message_dict = {}
    try:
        message_dict = json.loads(message_str)
    except Exception as e: 
        logging.debug("Decoding failed for: '%s'", message_str)
        print("Decoding failed for: '%s'" % message_str)
        return None

    return MessageType(message_dict)


REQUEST_FIELDS = [ "type", "data", "message" ]
LIST = "list"
JOIN = "join"
CREATE = "create"
REQUEST_TYPES = [LIST, JOIN, CREATE]
STAR = "star"
MESH = "mesh"
MEETING_TYPES = [STAR, MESH]

# valid fields of application messages 
DATA_FIELDS = [
    "meetingType", "meetingID", 
    "hosts", "username", "host", "listen_p2p_port"
]

class SocketMessage:
    """
    Messages in this application are 
    represented as dictionaries. 
    This class serves as a "wrapper"
    for the requests, so a dictionary 

    d = {"a" : 1, "b" : 2 } 

    becomes r = MeetingRequest(d) with

    r.a = 1
    r.b = 2
    """

    def __init__(self, msg_dict, msg_fields):
        self.msg_fields = msg_fields 
        for key in msg_dict:
            # ignore unexpected fields 
            if key in msg_fields:
                attr = msg_dict[key]
                if type(attr) is dict:
                    # recursively convert keys of dictionary to be attributes of 
                    # the object itself 
                    attr = SocketMessage(attr, DATA_FIELDS + msg_fields)

                # assign dictionary key/value to 
                # be attribute of this SocketMessage object
                setattr(self, key, attr)
            else:
                logging.error("Unexpected field for SocketMessage: %s", str(key))

    def _get_dict(self):
        """
        Convert SocketMessage back to dictionary
        for serialization purposes. 
        """
        d = {}
        for key in self.msg_fields:
            if hasattr(self, key):
                attr = self.__getattribute__(key)
                
                # convert nested SocketMessage objects 
                # back to dictionaries
                if isinstance(attr, SocketMessage):
                    attr = attr._get_dict()

                d[key] = attr
        return d

    def encode(self):
        """
        Turn message into dictionary, 
        then string, then bytes 
        for sending over a socket. 
        """
        request_str = json.dumps(self._get_dict()) + MSG_DELIM
        return request_str.encode()

    def is_valid(self):
        """
        Default method performs no error-checking
        on the contents of a message and 
        returns False. Subclasses 
        must define their own is_valid method 
        """
        return False


class MeetingRequest(SocketMessage): 
    """
    Requests from clients to central server. 
    May take the form of JOIN, CREATE, or LIST.
    """

    def __init__(self, request_dict={}):
        """
        Construct MeetingRequest object from dictionary.
        """
        super().__init__(request_dict, REQUEST_FIELDS)

    def is_valid(self):
        """
        Check that a request has the
        appropriate fields and values. 

        Note this doesn't check whether a meeting
        with the requested ID exists. 

        Possible requests:
        - type = "list"
        
        - type = "join"
          meetingID = .. some int ..
          meetingType = {"mesh", "star"}
        
        - type = "create"
          meetingType = {"mesh", "star"}
        """
        # request must be either "list", "join" or "create"
        if self.type == LIST:
            return True

        if self.type == JOIN:
            return type(self.data.meetingID) is int 

        if self.type == CREATE:
            return self.data.meetingType in MEETING_TYPES

        return False


class ListRequest(MeetingRequest):
    def __init__(self):
        super().__init__({ "type": LIST })

class JoinRequest(MeetingRequest):
    def __init__(self, meeting_id, username):
        req_data = { "meetingID" : meeting_id , "username" : username}
        req_type = JOIN
        req_dict = {"data": req_data, "type": req_type }
        super().__init__(req_dict)

class CreateMeshRequest(MeetingRequest):
    def __init__(self):
        data = { "meetingType" : MESH } 
        req_dict = {"type": CREATE, "data": data}
        super().__init__(req_dict)

class CreateStarRequest(MeetingRequest):
    def __init__(self):
        data = { "meetingType" : STAR } 
        req_dict = {"type": CREATE, "data": data}
        super().__init__(req_dict)


##########################################################
##  wrap up response data in a class for abstraction    ##
##  purposes, but make it easy to convert a dictionary  ##
##  into ServerResponse object and vice versa.          ##
##########################################################

RESPONSE_FIELDS = [ "type", "success", "message", "data" ]

class ServerResponse(SocketMessage):
    """
    Server may reply to requests with different data
    and messages. This class encapsulates the structure
    of these responses. 

    Possible response types:
    - list response (text)
    - join successfull (list of ip addresses/ports)
    - join failure 
        - unregistered meeting ID
        - meeting is full , etc. 
    - create success (new meetingID?)
    - create failure
      - why would this happen? 
    """
    
    def __init__(self, request_dict={}):
        """
        Construct ServerResponse object from dictionary.
        """
        super().__init__(request_dict, RESPONSE_FIELDS)

    def is_valid(self):
        """
        Check that response from server has appropriate
        fields and that they have appropriate types. 
        """

        # success field should be bool
        if not (type(self.success) is bool):
            return False

        if self.type == LIST:
            # List response should always
            # return a list
            return type(self.data) is list
            # return True

        if self.type == JOIN:
            # if self.success:
                # return type(self.data) is list
            return True

        if self.type == CREATE:
            # CREATE data is meeting ID (integer)
            # if self.success:
                # return type(self.data) is int
            return True

        return False


class ListResponse(ServerResponse):
    def __init__(self, meeting_id_list):
        message = "\nMeetings found: %s\n" % len(meeting_id_list)
        resp_dict = {"message": message, 
                    "type": LIST,
                    "success": True,
                    "data": meeting_id_list }
        super().__init__(resp_dict) 

class JoinStarSuccess(ServerResponse):
    def __init__(self, host_addr_port, username):
        super().__init__()
        message = "Join request successful! Preparing to join..."
        data = { "host" : host_addr_port, "meetingType": STAR , "username" : username}
        resp_dict = {"message": message, 
                    "type": JOIN,
                    "success": True,
                    "data": data }
        super().__init__(resp_dict) 

class JoinMeshSuccess(ServerResponse):
    def __init__(self, host_addr_port, username, listen_p2p_port):
        message = "Join request successful! Preparing to join..."
        data = { "host" : host_addr_port , "meetingType": MESH , "username" : username, "listen_p2p_port" : listen_p2p_port}
        resp_dict = {"message": message, 
                    "type": JOIN,
                    "success": True,
                    "data": data }
        super().__init__(resp_dict) 


class JoinFailure(ServerResponse):
    def __init__(self, error_msg):
        message = "Join failed with error: '%s'" % error_msg
        resp_dict = {"message": message, 
                    "type": JOIN,
                    "success": False,
                    "data": None }
        super().__init__(resp_dict) 

class CreateStarSuccess(ServerResponse):
    def __init__(self, meetingID, listen_p2p_port):
        message = "Create request successful! Creating new meeting..."
        data = { "meetingID" : meetingID , "meetingType" : STAR , 
                 "listen_p2p_port" : listen_p2p_port} 
        resp_dict = {"message": message, 
                    "type": CREATE,
                    "success": True,
                    "data": data }
        super().__init__(resp_dict) 

class CreateMeshSuccess(ServerResponse):
    def __init__(self, meetingID, listen_p2p_port):
        message = "Create request successful! Creating new meeting..."
        data = { "meetingID" : meetingID , "meetingType" : MESH , "listen_p2p_port" : listen_p2p_port } 
        resp_dict = {"message": message, 
                    "type": CREATE,
                    "success": True,
                    "data": data }
        super().__init__(resp_dict) 


#######################################################

# messages between nodes in p2p network (not client/server)

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
        msg_dict = {"message": message_str, "type": P2P_TEXT}
        super().__init__(msg_dict)

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
        # pass username using data field
        data = { "username" : username }

        msg_dict = {"type": P2P_REGISTER_USERNAME,
                    "data": data}
        super().__init__(msg_dict)

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
    def __init__(self, listen_p2p_port):
        # pass username using data field
        data = { "listen_p2p_port" : listen_p2p_port }
        msg_dict = {"type": P2P_REGISTER_PORT,
                    "data": data}
        super().__init__(msg_dict)

    def is_valid(self):
        return super().is_valid() \
                and (type(self.data.listen_p2p_port) is int)

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
        data = { "hosts" : addr_ports }
        msg_dict = {"type": P2P_MESH_CONNECT,
                    "data": data}
        super().__init__(msg_dict)


    def is_valid(self):
        return super().is_valid() \
            and (type(self.data.hosts) is list)









