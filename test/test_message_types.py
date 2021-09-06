from unittest import TestCase
from p2p_meetings.message_types import *

class MessageTypesTest(TestCase):
    """
    Three types of socket messages (subclasses of SocketMessage):

    MeetingRequest
    - request from client to central server

    ServerResponse
    - response from central server to client 

    P2PMessage
    - message between clients in p2p network 
    
    Tests

    - test is_valid for each type of SocketMessage

    - test that JoinRequest -> encode -> decode -> MeetingRequest 
      produces a valid MeetingRequest object and similarly for 
      other SocketMessage subclasses 
    """

    @classmethod
    def setUpClass(cls):
        """Initialize all the SocketMessage objects we want to test"""
        meetingID = 0
        username = "my_username" 
        port = 0
        addr_port = (0, 0)

        # MeetingRequest subclasses
        cls.request_objs = [ 
            ListRequest(),
            CreateMeshRequest(),
            CreateStarRequest(),
            JoinRequest(meetingID, username)]

        # ServerResponse subclasses
        cls.resp_objs = [ 
            ListResponse([]),
            JoinFailure(""),
            JoinMeshSuccess(addr_port, username, port),
            CreateMeshSuccess(meetingID, port),
            CreateStarSuccess(meetingID, port)]

        # P2PMessage subclasses
        cls.p2pmsg_objs = [
            MeshConnect([]),
            RegisterPort(port),
            RegisterUsername(username),
            P2PText("")
        ]

        cls.message_objs = cls.request_objs + cls.resp_objs + cls.p2pmsg_objs

    def test_is_valid(self):
        """
        Test that is_valid() returns True 
        for every SocketMessage object.
        """
        for msg_obj in self.message_objs:
            self.assertTrue(msg_obj.is_valid())

    def test_requests_encode_decode(self):
        """
        Test that MeetingRequest objects can 
        be encoded/decoded successfully. 
        """
        for msg_obj in self.request_objs:
            self._test_encode_message(msg_obj, MeetingRequest)

    def test_responses_encode_decode(self):
        """
        Test that ServerResponse objects can 
        be encoded/decoded successfully. 
        """
        for msg_obj in self.resp_objs:
            self._test_encode_message(msg_obj, ServerResponse)

    def test_p2p_messages_encode_decode(self):
        """
        Test that P2PMessage objects can 
        be encoded/decoded successfully. 
        """
        for msg_obj in self.p2pmsg_objs:
            self._test_encode_message(msg_obj, P2PMessage)

    def _test_encode_message(self, message_obj:"SocketMessage", MessageType):
        """
        Encode an object and then try to decode the bytes. 
        """
        # encoding gives bytes delimited by ';' 
        byte_str = message_obj.encode().decode()
        # so we have to get rid of the delimiter
        byte_str = byte_str.split(MSG_DELIM)[0]

        mtg_req_obj = decode_message(byte_str, MessageType)

        # if decoding fails, decode_message returns None
        self.assertIsNotNone(mtg_req_obj)

        # test that decoded SocketMessage object is valid 
        self.assertTrue(mtg_req_obj.is_valid())
        
