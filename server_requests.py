import json
from socket import * 
from constants import * 

##########################################################
##  wrap up request data in a class for abstraction     ##
##  purposes, but make it easy to convert a dictionary  ##
##  into MeetingRequest object and vice versa.          ##
##########################################################


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
    "hosts", "username", "host", "p2p_port"
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
                    # recursively lift keys of dictionary to be attributes of 
                    # the object itself 
                    attr = SocketMessage(attr, DATA_FIELDS)

                # assign dictionary key/value to 
                # be attribute of this SocketMessage object
                setattr(self, key, attr)
            else:
                print("Unexpected field for SocketMessage: ", key)

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
        on the contents of a message. 
        """
        return True 


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
        super().__init__()
        self.type = LIST


class JoinRequest(MeetingRequest):
    def __init__(self, meeting_id, username):
        super().__init__()
        self.type = JOIN
        self.data = { "meetingID" : meeting_id , "username" : username}

# class JoinStarRequest(MeetingRequest):
#     def __init__(self, meeting_id):
#         super().__init__()
#         self.type = JOIN
#         self.data = { "meetingType" : STAR ,
#                       "meetingID" : meeting_id }
# 
# class JoinMeshRequest(MeetingRequest):
#     def __init__(self, meeting_id):
#         super().__init__()
#         self.type = JOIN
#         self.data = { "meetingType" : MESH , 
#                       "meetingID" : meeting_id }

class CreateMeshRequest(MeetingRequest):
    def __init__(self):
        super().__init__()
        self.type = CREATE
        self.data = { "meetingType" : MESH } 

class CreateStarRequest(MeetingRequest):
    def __init__(self):
        super().__init__()
        self.type = CREATE
        self.data = { "meetingType" : STAR } 


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
            # return type(self.data) is list
            return True

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
        super().__init__()
        self.message = "\nMeetings found: %s\n" % len(meeting_id_list)
        self.type = LIST
        self.success = True
        self.data = meeting_id_list

class JoinStarSuccess(ServerResponse):
    def __init__(self, host_addr_port, username):
        super().__init__()
        self.message = "Join request successful! Preparing to join..."
        self.data = { "host" : host_addr_port, "meetingType": STAR , "username" : username}
        self.type = JOIN
        self.success = True 

class JoinMeshSuccess(ServerResponse):
    def __init__(self, host_addr_port, username):
        super().__init__()
        self.message = "Join request successful! Preparing to join..."
        self.data = { "host" : host_addr_port , "meetingType": MESH , "username" : username}
        self.type = JOIN
        self.success = True 


class JoinFailure(ServerResponse):
    def __init__(self, error_msg):
        super().__init__()
        self.message = "Join failed with error: '%s'" % error_msg
        self.type = JOIN
        self.success = False
        self.data = None

class CreateStarSuccess(ServerResponse):
    def __init__(self, meetingID, p2p_port):
        super().__init__()
        self.message = "Create request successful! Creating new meeting..."
        self.data = { "meetingID" : meetingID , "meetingType" : STAR , "p2p_port" : p2p_port} 
        self.type = CREATE
        self.success = True 

class CreateMeshSuccess(ServerResponse):
    def __init__(self, meetingID, p2p_port):
        super().__init__()
        self.message = "Create request successful! Creating new meeting..."
        self.data = { "meetingID" : meetingID , "meetingType" : MESH , "p2p_port" : p2p_port } 
        self.type = CREATE
        self.success = True 

