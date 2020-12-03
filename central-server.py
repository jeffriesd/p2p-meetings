import json
from socket import * 
import threading 
from server_requests import * 
from constants import * 

class MeetingEntry: 
    pass

class LectureMeetingEntry:
    """ 
    Maintain address of host, 
    number of attendees, ...
    """ 
    pass

class MeshMeetingEntry:
    """ 
    Maintain addresses of all 
    attendees, number of attendees, ...
    """ 
    pass



#######################################################


class Server:
    """
    This class implements the functions used 
    by the central server. The server's role is
    to maintain a directory of ongoing meetings,
    mapping meeting IDs to the IP addresses/port 
    of the host(s). 


    The server handles three types of requests:
    - List meetings
    - Join meeting
    - Create meeting
    """

    def __init__(self):


        # map meetingID to list of MeetingEntry
        # objects 
        self.meetings = {} 

        self._unique_meetingID = 0
        self._unique_meetingID_lock = threading.Lock()

        self.connection_thread = threading.Thread(target=self.wait_for_connections)
        self.connection_thread.start()

    def new_meetingID(self):
        """
        Assign new meeting ID and increment global counter. 
        Synchronized to avoid multiple threads assigning the 
        same meeting ID. 
        """
        uid = 0
        with self._unique_meetingID_lock:
            uid = self._unique_meetingID
            self._unique_meetingID += 1
        return uid

    def wait_for_connections(self):
        """
        Loop forever and wait for 
        new clients to make tcp connection 
        requests. 
        
        Once a client connects, they
        can make some requests (in a new thread)
        and then eventually disconnect. If clients don't disconnect
        on their own, they will be kicked 
        """

        server_socket = socket(AF_INET, SOCK_STREAM)
        server_socket.bind(('', SERVER_PORT))
        server_socket.listen(MAX_QUEUED_REQUESTS)

        server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

        while True:
            connection_socket, addr = server_socket.accept()
            print("Got a new connection")

            connection_msg = "You are connected to the central server."
            connection_socket.send(connection_msg.encode())
            
            # # process requests for this client before accepting
            # # more connections
            # self.wait_for_requests(connection_socket, addr)

            # listen for requests from this client in a separate thread
            # so other clients can connect simultaneously
            request_thread = \
                ListenThread(MessageRequest,   \   
                             connection_socket, \ 
                             lambda req: self.handle_request(req, connection_socket, addr) \ 
                             lambda: print("Client closed connection."), \
                             keep_alive_sec = 5 * 60 \ # keep connection alive 5 minutes 
                             )

            request_thread.start()

    # def wait_for_requests(self, conn_socket, addr):
    #     """ 
    #     Wait for incoming requests from a 
    #     specific TCP connection
    #     """
    #     while True:
    #         request_bytes = bytearray()

    #         try:
    #             print("waiting to receive...")
    #             request_bytes = conn_socket.recv(1024)
    #             print("... received")
    #         except:
    #             print("TCP connection for central server request closed.")

    #             # stop listening for requests from this socket
    #             return

    #         # TODO add error handling in case connection
    #         # is closed by requesting client
    #         if not request_bytes:
    #             return

    #         # try to parse request as dictionary
    #         request_dict = {}
    #         try:
    #             print("request decoded: ", request_bytes.decode())
    #             request_str = request_bytes.decode()
    #             request_str = request_str.replace(";","")
    #             print("Rs = ", request_str)
    #             request_dict = json.loads(request_str)
    #         except:
    #             print("Server failed to parse request")
    #             continue

    #         mtng_request = MeetingRequest(request_dict)

    #         if mtng_request.is_valid():
    #             self.handle_request(mtng_request, conn_socket, addr)
    #         else:
    #             print("Invalid request")

    def send_response(self, response_obj, conn_socket):
        """ 
        response_obj - ServerResponse object
        """
        # TODO error handling in case connection closed 

        if response_obj.is_valid():
            safe_send(conn_socket, response_obj.encode())
        else:
            print("!!!!! INVALID  response")

    def handle_request(self, mtng_request, conn_socket, addr):
        """ 
        mtng_request - MeetingRequest object
        """
        # TODO error handling in case connection closed 

        if mtng_request.type == LIST:
            # create new response with list of meeting ids
            response = ListResponse(list(self.meetings.keys()))

        elif mtng_request.type == JOIN:
            if mtng_request.meetingID in self.meetings:
                # TODO if it exists, make sure it is accepting 
                # new members (it may be full) 
                #
                response = JoinSuccess(self.meetings[mtng_request.meetingID])
            else:
                response = JoinFailure("Meeting ID '%s' not found." % mtng_request.meetingID)

        elif mtng_request.type == CREATE:
            meetingID = self.new_meetingID()

            # register new meeting with new ID
            self.meetings[meetingID] = [ addr ]

            # response to Create should be the meetingID
            response = CreateSuccess(meetingID)

        # send response to requesting client 
        self.send_response(response, conn_socket)



print("Starting server...")
Server()
