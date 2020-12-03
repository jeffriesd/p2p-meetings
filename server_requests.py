import json
from socket import * 
from constants import * 

##########################################################
##  wrap up request data in a class for abstraction     ##
##  purposes, but make it easy to convert a dictionary  ##
##  into MeetingRequest object and vice versa.          ##
##########################################################


REQUEST_FIELDS = [ "type", "meetingType", "meetingID" ]
LIST = "list"
JOIN = "join"
CREATE = "create"
REQUEST_TYPES = [LIST, JOIN, CREATE]
STAR = "star"
MESH = "mesh"
MEETING_TYPES = [STAR, MESH]

class MeetingRequest: 
    """
    Requests handled by this server are 
    represented as dictionaries. 
    This class serves as a "wrapper"
    for the requests, so a dictionary 

    d = {"a" : 1, "b" : 2 } 

    becomes r = MeetingRequest(d) with

    r.a = 1
    r.b = 2
    """

    def __init__(self, request_dict):
        """
        Construct MeetingRequest object from dictionary.
        """
        for key in request_dict:
            # ignore unexpected fields 
            if key in REQUEST_FIELDS:
                self.__setattr__(key, request_dict[key])

    def _get_dict(self):
        d = {}
        for key in REQUEST_FIELDS:
            if hasattr(self, key):
                d[key] = self.__getattribute__(key)
        return d

    def encode(self):
        """
        Turn request into dictionary, 
        then string, then bytes 
        for sending over a socket. 
        """
        request_str = json.dumps(self._get_dict()) + MSG_DELIM
        return request_str.encode()


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
            return type(self.meetingID) is int \
                and self.meetingType in MEETING_TYPES

        if self.type == CREATE:
            return self.meetingType in MEETING_TYPES

        return False


class ListRequest(MeetingRequest):
    def __init__(self):
        self.type = LIST

class JoinStarRequest(MeetingRequest):
    def __init__(self, meeting_id):
        self.type = JOIN
        self.meetingType = STAR
        self.meetingID = meeting_id

class JoinMeshRequest(MeetingRequest):
    def __init__(self, meeting_id):
        self.type = JOIN
        self.meetingType = MESH
        self.meetingID = meeting_id

class CreateMeshRequest(MeetingRequest):
    def __init__(self):
        self.type = CREATE
        self.meetingType = MESH

class CreateStarRequest(MeetingRequest):
    def __init__(self):
        self.type = CREATE
        self.meetingType = STAR


#######################################################
#######################################################
#######################################################



##########################################################
##  wrap up response data in a class for abstraction    ##
##  purposes, but make it easy to convert a dictionary  ##
##  into ServerResponse object and vice versa.          ##
##########################################################

RESPONSE_FIELDS = [ "type", "success", "message", "data" ]

class ServerResponse:
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
    
    def __init__(self, response_dict):
        for key in response_dict:
            # ignore unexpected fields 
            if key in RESPONSE_FIELDS:
                self.__setattr__(key, response_dict[key])

    def _get_dict(self):
        d = {}
        for key in RESPONSE_FIELDS:
            if hasattr(self, key):
                d[key] = self.__getattribute__(key)
        return d

    def encode(self):
        """
        Turn response into dictionary, 
        then string, then bytes 
        for sending over a socket. 
        """
        response_str = json.dumps(self._get_dict()) + MSG_DELIM
        return response_str.encode()

    def is_valid(self):
        """
        Check that response from server has appropriate
        fields and that they have appropriate types. 
        """

        # success field should be bool
        if not (type(self.success) is bool):
            return False

        if self.type == LIST:
            # List request should always
            # succeed and return a list
            return self.success and type(self.data) is list

        if self.type == JOIN:
            if self.success:
                return type(self.data) is list
            return True

        if self.type == CREATE:
            # CREATE data is meeting ID (integer)
            if self.success:
                return type(self.data) is int
            return True

        return False


class ListResponse(ServerResponse):
    def __init__(self, meeting_id_list):
        self.message = "\nMeetings found: %s\n" % len(meeting_id_list)
        self.type = LIST
        self.success = True
        self.data = meeting_id_list

class JoinSuccess(ServerResponse):
    def __init__(self, addr_port_pairs):
        self.message = "Join request successful! Preparing to join..."
        self.data = addr_port_pairs
        self.type = JOIN
        self.success = True 

class JoinFailure(ServerResponse):
    def __init__(self, error_msg):
        self.message = "Join failed with error: '%s'" % error_msg
        self.type = JOIN
        self.success = False
        self.data = None

class CreateSuccess(ServerResponse):
    def __init__(self, meetingID):
        self.message = "Create request successful! Creating new meeting..."
        self.data = meetingID
        self.type = CREATE
        self.success = True 

