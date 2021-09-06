from unittest import TestCase
from p2p_meetings.message_types import *

class MessageTypesTest(TestCase):
    """
    Three types of messages:

    MeetingRequest
    - request from client to central server

    ServerResponse
    - response from central server to client 

    P2PMessage
    - message between clients in p2p network 
    

    TODO 

    - test is_valid for each type of SocketMessage

    - test that JoinRequest -> encode -> decode -> MeetingRequest 
      produces a valid MeetingRequest object 
    """
    
    def test_list_valid(self):
        """Test that ListRequest constructor 
        produces valid MeetingRequest object"""
        req = ListRequest()
        self.assertTrue(req.is_valid())

    def test_create_mesh(self):
        """Test that CreateMeshRequest constructor 
        produces valid MeetingRequest object"""
        self.assertTrue(CreateMeshRequest().is_valid())

    def test_create_star(self):
        """Test that CreateStarRequest constructor 
        produces valid MeetingRequest object"""
        self.assertTrue(CreateStarRequest().is_valid())

    def test_join_valid(self):
        """Test that JoinRequest constructor 
        produces valid MeetingRequest object"""
        meetingID = 0
        user = "my_username" 
        req = JoinRequest(meetingID, user)
        self.assertTrue(req.is_valid())


    ### test ServerResponse classes 

    def test_list_response(self):
        """Test that ListResponse constructor 
        produces valid ServerResponse object"""
        self.assertTrue(ListResponse([]).is_valid())

    def test_join_star_success(self):
        """Test that JoinStarSuccess constructor 
        produces valid ServerResponse object"""
        addr_port = (0, 0)
        req = JoinStarSuccess(addr_port, "user")
        self.assertTrue(req.is_valid())

    def test_join_mesh_success(self):
        """Test that JoinMeshSuccess constructor 
        produces valid ServerResponse object"""
        addr_port = (0, 0)
        req = JoinMeshSuccess(addr_port, "user", 0)
        self.assertTrue(req.is_valid())

    def test_join_failure(self):
        """Test that JoinFailure constructor 
        produces valid ServerResponse object"""
        self.assertTrue(JoinFailure("").is_valid())

    def test_create_mesh_success(self):
        """Test that CreateMeshSuccess constructor 
        produces valid ServerResponse object"""
        mtgID = 0
        port = 0 
        self.assertTrue(CreateStarSuccess(mtgID, port).is_valid())

    def test_create_star_success(self):
        """Test that CreateStarSuccess constructor 
        produces valid ServerResponse object"""
        mtgID = 0
        port = 0 
        self.assertTrue(CreateStarSuccess(mtgID, port).is_valid())

    ### test P2PMessage classes 

    def test_p2p_text(self):
        """Test that P2PText constructor 
        produces valid P2PMessage object"""
        text = "asdf"
        self.assertTrue(P2PText(text).is_valid())

    def test_register_username(self):
        """Test that RegisterUsername constructor 
        produces valid P2PMessage object"""
        user = "username"
        self.assertTrue(RegisterUsername(user).is_valid())

    def test_register_port(self):
        """Test that RegisterPort constructor 
        produces valid P2PMessage object"""
        port = 0
        self.assertTrue(RegisterPort(port).is_valid())


    def test_mesh_connect(self):
        """Test that MeshConnect constructor 
        produces valid P2PMessage object"""
        peers = [] 
        self.assertTrue(MeshConnect(peers).is_valid())
