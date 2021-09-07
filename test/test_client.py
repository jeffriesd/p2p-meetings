from unittest import TestCase
from time import sleep 
from test.test_central_server import P2PTestCase
from test.test_util import sleep_until
from p2p_meetings.client import Client
from p2p_meetings.message_types import STAR, MESH


class ClientTest(P2PTestCase):
    """
    Tests to check that clients can
    create new rooms and establish p2p connections 

    - test join
      - try joining nonexistent room
      - try joining existing room and making sure expected 
        connections are established 

    - test list 
      - test formatting, test with star_create, mesh_create as 
        described above 
    """
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # clients whose p2p nodes need to be shutdown 
        cls.p2p_clients = [] 

        # clients who never join a p2p network 
        cls.non_p2p_clients = []

    @classmethod
    def tearDownClass(cls):
        # shutdown clients before shutting down server
        # because we need to shutdown the p2p nodes,
        # and these don't get created until server
        # responds to client (we may have to wait a 
        # second for the node to be created 
        # before shutting it down) 
        for client in cls.non_p2p_clients:
            client.shutdown()

        for client in cls.p2p_clients:
            # wait until client.node is defined 
            # so it can be shutdown 
            condition = lambda: client.node is not None
            sleep_until(condition)
            client.shutdown()

        # shutdown server
        super().tearDownClass()

    def make_p2p_client(self):
        c = Client()
        self.p2p_clients.append(c)
        return c

    def make_non_p2p_client(self):
        c = Client()
        self.non_p2p_clients.append(c)
        return c

    def _test_until(self, condition):
        sleep_until(condition)
        self.assertTrue(condition())

    def wait_for_node(self, client):
        """
        Wait until client.node is defined but
        fail if it times out. 
        """
        condition = lambda: client.node is not None
        self._test_until(condition)


    def test_mesh_create(self):
        """Test listing of new mesh meeting """
        mesh_create = lambda client: client.mesh_create()
        self._test_meeting_create(mesh_create, MESH)

    def test_star_create(self):
        """Test listing of new star meeting """
        star_create = lambda client: client.star_create()
        self._test_meeting_create(star_create, STAR)

    def _test_meeting_create(self, client_create, expected_mtype:str):
        """Test that a client creating a new meeting results 
        in a new meeting of the correct type in the listing"""
        c = self.make_p2p_client()

        # create star/mesh meeting
        client_create(c)

        # use non_p2p since c2 won't 
        # connect to any p2p networks 
        c2 = self.make_non_p2p_client()

        # wait until list response data is received
        n = len(c2.meeting_response_data)
        condition = lambda: len(c2.meeting_response_data) == n+1

        c2.list()
        self._test_until(condition)
        # get meeting id and type 
        meetings = c2.meeting_response_data[-1]
        mid, mtype = meetings[-1]

        self.assertEqual(mtype, expected_mtype)


    def test_join_nonexistent_meeting(self):
        """
        Test that attempting to join a nonexistent 
        meeting results in an error message. 
        """
        c = self.make_non_p2p_client()
        # try to join nonexistent meeting
        c.join(-1, "dummy_username")

        # server should reply with error message 
        err_text = "Join request failed"
        condition = lambda: any([err_text in m for m in c.server_messages])
        self._test_until(condition)

    def test_join_star(self):
        """
        Test that clients can join star meeting. 
        """
        client_create = lambda cl: cl.star_create()
        self._test_join_meeting(client_create)

    def test_join_mesh(self):
        """
        Test that clients can join mesh meeting. 
        """
        client_create = lambda cl: cl.mesh_create()
        self._test_join_meeting(client_create)

    def _test_join_meeting(self, client_create):
        """
        Test that clients can join star meeting. 
        """
        host = self.make_p2p_client()
        client_create(host)

        c = self.make_p2p_client()
        n = len(c.meeting_response_data)
        condition = lambda: len(c.meeting_response_data) == n+1

        c.list()
        self._test_until(condition)

        meetings = c.meeting_response_data[-1]
        mid, mtype = meetings[-1]
        
        c.join(mid, "test user")

        # if c.node is set, then 
        # c has joined a p2p network 
        self.wait_for_node(c)

        # also test that host and 
        # client peer sockets are connected
        self.wait_for_node(host)
        self.assert_peer_connection(host, c)

    def assert_peer_connection(self, host, client):
        """
        Test whether host and client 
        have sockets connected to each other. 
        """
        # get address on client side 
        client_peer_sock = client.node.host_socket
        cp_addr = client_peer_sock.getsockname()

        # get address on host side and 
        # make sure it matches with client 
        self.assertTrue(cp_addr in host.node.peers)
        peer_info = host.node.peers[cp_addr]
        host_peer_addr = peer_info.conn_socket.getpeername()
        self.assertEqual(host_peer_addr, cp_addr)

