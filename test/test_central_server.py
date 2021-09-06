from unittest import TestCase
import json 
from threading import Thread
from typing import Callable 

from p2p_meetings.central_server import *
from p2p_meetings.constants import *
from test.test_util import sleep_until

class LocalServerTest(TestCase):
    """
    Note: this test must be run with permission 
    to open sockets on server port 
    """
    @classmethod
    def setUpClass(cls):
        # set up logging 
        logging.basicConfig(filename="test-server.log", level=logging.DEBUG)

        cls.server = Server()
        cls.client_sockets = []

        # wait until cls.connect_socket is initialized 
        while cls.server.connection_socket is None:
            pass

    @classmethod
    def tearDownClass(cls):
        cls.server.stop_server()

        # close any opened client sockets 
        for sock in cls.client_sockets:
            safe_shutdown_close(sock)

    def make_request_get_response(self, request:"MeetingRequest"): 
        """Take a function that returns a MeetingRequest object, 
        send a request to the server and return the response as a dictionary"""
        # test that list request generates correct response 
        client_socket = self.make_client()
        # if connection fails, self.make_client returns None
        self.assertIsNotNone(client_socket)

        client_socket.send(request.encode())

        # wait up to 3 seconds for message 
        client_socket.settimeout(3)
        response_bytes = client_socket.recv(1024)
        response_str = response_bytes.decode().split(MSG_DELIM)[0]
        response_dict = json.loads(response_str)
        return response_dict


    def make_client(self): 
        # make a tcp client and connect with the server 
        client_socket = socket(AF_INET, SOCK_STREAM)
        try:
            # try connecting to central server 
            client_socket.connect((SERVER_IP, SERVER_PORT))
        except Exception as e:
            print("Failed to create client socket:", e)
            return None
        
        # append to list so all opened sockets can be closed
        # in class tear down 
        LocalServerTest.client_sockets.append(client_socket)
        return client_socket

    def test_server_accepts_connections(self): 
        """Test that server accepts client connections"""
        # also check that self.server.client_sockets has one entry 
        # after connection client_socket.
        # This may take a short amount of time to update, 
        # so sleep until it does 
        prev_num_clients = len(self.server.client_sockets)
        condition = lambda: len(self.server.client_sockets) == prev_num_clients+1

        client_socket = self.make_client()
        # if connection fails, self.make_client returns None
        self.assertIsNotNone(client_socket)

        sleep_until(condition)

        self.assertTrue(condition())


    def test_server_accepts_data(self):
        """Test that server accepts client data"""
        # after connecting, 
        # try sending something to the server socket. 
        client_socket = self.make_client()
        # if connection fails, self.make_client returns None
        self.assertIsNotNone(client_socket)

        # try sending some bytes. if it 
        # doesn't raise any exceptions, then 
        # it is working correctly
        client_socket.send(bytes())


    def generate_unique_values(self, generate_value:Callable[[], int]): 
        # test that generated meeting ids/ports
        # are unique. use multiple threads to 
        # request new meeting ids/ports. 
        
        # number of id's for each thread to request 
        num_ids = 100
        num_threads = 100

        all_ids = []

        def request_new_ids():
            for _ in range(num_ids):
                new_id = generate_value()
                all_ids.append(new_id)

        
        for _ in range(num_threads):
            test_thread = threading.Thread(target=request_new_ids)
            test_thread.start()

        return all_ids

    def test_new_meetingID(self):
        """Test new meeting IDs are unique"""
        ids = self.generate_unique_values(self.server.new_meetingID)
        # test that generated ids are all distinct 
        self.assertEqual(len(ids), len(set(ids)))
        
    def test_new_meeting_port(self):
        """Test new meeting ports are unique"""
        ports = self.generate_unique_values(self.server.new_meeting_port)
        # test that generated ports are all distinct 
        self.assertEqual(len(ports), len(set(ports)))

    def test_send_response(self):
        """Test that send_response works when given valid response object"""
        
        # just use a list response with empty list of 
        # ids to test send_response 
        response = ListResponse([]) # does not cause "unexpected field issue" 

        # sleep until server-side client socket is available 
        prev_num_clients = len(self.server.client_sockets)
        condition = lambda: len(self.server.client_sockets) == prev_num_clients+1

        client_socket = self.make_client()
        # if connection fails, self.make_client returns None
        self.assertIsNotNone(client_socket)

        sleep_until(condition)
        ss_client_socket = self.server.client_sockets[-1]

        # try sending response from server to client 
        self.server.send_response(response, ss_client_socket)

    def test_handle_request_create_star(self):
        """Test that sending a CREATE (star topology) request 
        actually creates a new meeting entry on server side"""
        self._test_handle_request_create(CreateStarRequest())

    def test_handle_request_create_mesh(self):
        """Test that sending a CREATE (mesh topology) request 
        actually creates a new meeting entry on server side"""
        self._test_handle_request_create(CreateMeshRequest())

    def _test_handle_request_create(self, request: "MeetingRequest"):
        """helper method for testing CREATE requests"""
        client_socket = self.make_client()
        # if connection fails, self.make_client returns None
        self.assertIsNotNone(client_socket)

        # test that server adds one new meeting entry
        prev_num_meetings = len(self.server.meetings)
        condition = lambda: len(self.server.meetings) == prev_num_meetings + 1

        client_socket.send(request.encode())

        sleep_until(condition) 
        self.assertTrue(condition())

        # test (below) that server gets client port/IP correct

        # access meeting entry using most recently generated meetingID. 
        # this works because dicts are ordered as of pythone 3.6
        most_recent_id = list(self.server.meetings.keys())[-1]
        meeting_entry = self.server.meetings[most_recent_id]
        # get server-side client socket 
        ss_client_socket = meeting_entry.client_socket

        # test that ip/port of client-side client socket 
        # match ip/port of server-side client socket 
        self.assertEqual(ss_client_socket.getpeername(), client_socket.getsockname())

        return most_recent_id

    def test_handle_request_list(self):
        """Test that list request generates correct response"""
        response_dict = self.make_request_get_response(ListRequest())

        self.assertTrue(response_dict["success"])
        self.assertEqual(response_dict["type"], LIST)
        self.assertTrue(isinstance(response_dict["data"], list))

    def test_handle_request_join(self):
        """Test that join request generates correct response"""

        # first make a create request to make a new room to join 
        room_id = self._test_handle_request_create(CreateStarRequest())

        # parameterize JoinRequest with a dummy username 
        # and a meetingID 
        request = JoinRequest(room_id, "test_username")
        response_dict = self.make_request_get_response(request)

        self.assertEqual(response_dict["type"], JOIN)
        self.assertTrue(isinstance(response_dict["data"], dict))
        self.assertTrue(response_dict["success"])

