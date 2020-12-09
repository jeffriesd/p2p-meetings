import json
from socket import * 
import threading 
from server_requests import * 
from constants import * 
from socket_util import * 


class MeetingEntry:
    """
    Keep track of host (addr, port) 
    and the set of usernames which have been claimed so far. 

    Note that once a peer chooses a particular username in a 
    meeting, no future peer can use this username in the same meeting,
    even if the original peer with that username leaves. 
    """
    def __init__(self, addr_port):
        self.host_addr_port = addr_port
        self.host_addr, self.host_port = addr_port 

        # keep track of usernames registered within a meeting 
        self.usernames = set()

    def has_username(self, name):
        return name in self.usernames

    def add_username(self, name):
        self.usernames.add(name)

# StarMeetingEntry and MeshMeetingEntry 
# have the exact same behavior, but they 
# are handled differently when 
# creating a response, so these classes
# just provide a tag for which kind of meeting is being recorded. 
class StarMeetingEntry(MeetingEntry):
    pass

class MeshMeetingEntry(MeetingEntry):
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


        # map meetingID to MeetingEntry
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
        server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1) # 
        # server_socket.bind(('localhost', SERVER_PORT))
        server_socket.bind(('', SERVER_PORT))
        # server_socket.listen(MAX_QUEUED_REQUESTS)
        server_socket.listen()


        while True:
            connection_socket, addr_port = server_socket.accept()
            print("Central server: got a new connection from ", addr_port)

            connection_msg = "You are connected to the central server."
            connection_socket.send(connection_msg.encode())


            # listen for requests from this client in a separate thread
            # so other clients can connect simultaneously
            request_thread = self.make_request_thread(connection_socket, addr_port)
            request_thread.start()

    def make_request_thread(self, connection_socket, addr_port):
        """
        Can't inline this above, or else binding issues arise
        since connection_socket and addr_port get reassigned every
        iteration of the while loop. 
        """
        return ListenThread(MeetingRequest,   \
                             connection_socket, \
                             lambda req: self.handle_request(req, connection_socket, addr_port), \
                             lambda: print("Client closed connection."), \
                             keep_alive_sec = 5 * 60 \
                             )

    def send_response(self, response_obj, conn_socket):
        """ 
        response_obj - ServerResponse object
        """
        if response_obj.is_valid():
            safe_send(conn_socket, response_obj.encode())
        else:
            print("Error: Cannot send invalid ServerResponse object: ", response_obj)

    def handle_request(self, mtng_request, conn_socket, addr_port):
        """ 
        mtng_request - MeetingRequest object

        addr_port - ip address and port for socket connection from client to server... 
        """
        if mtng_request.type == LIST:
            # TODO LIST COMMAND<S-F7> SHOULD<S-F7> CHECK 
            # WHETHER MEETINGS ARE OPEN !!!!!!!!!!!!!!!!!!!!!!!!11
            # at least whether hosts are still connected. 

            # create new response with list of meeting ids
            response = ListResponse(list(self.meetings.keys()))

        elif mtng_request.type == JOIN:
            if mtng_request.data.meetingID in self.meetings:
                meeting_entry = self.meetings[mtng_request.data.meetingID]

                # check if username is already taken 
                requested_username = mtng_request.data.username 
                if meeting_entry.has_username(requested_username):
                    response = JoinFailure("Username '%s' already taken. Please choose another.")
                else:
                    # add new username to record for this meeting 
                    meeting_entry.add_username(requested_username)

                    if isinstance(meeting_entry, StarMeetingEntry):
                        response = JoinStarSuccess(meeting_entry.host_addr_port, requested_username)
                    elif isinstance(meeting_entry, MeshMeetingEntry):
                        response = JoinMeshSuccess(meeting_entry.host_addr_port, requested_username)
                    else:
                        response = JoinFailure("Meeting ID '%s' has wrong type." % mtng_request.data.meetingID)
            else:
                response = JoinFailure("Meeting ID '%s' not found." % mtng_request.data.meetingID)

        # create a new meeting and record the address of
        # the host and the port that will be used to make connections
        # in the p2p meeting network 
        elif mtng_request.type == CREATE:
            # generate unique meetingID
            meetingID = self.new_meetingID()

            # determine port for p2p connections for this new meeting
            p2p_port = get_meeting_port(meetingID)


            # store address and p2p port so other users can join 
            # this meeting in the future 
            if mtng_request.data.meetingType == STAR:
                response = CreateStarSuccess(meetingID)
                self.meetings[meetingID] = StarMeetingEntry((addr_port[0], p2p_port))

            if mtng_request.data.meetingType == MESH:
                response = CreateMeshSuccess(meetingID)
                self.meetings[meetingID] = MeshMeetingEntry((addr_port[0], p2p_port))

        # send response to requesting client 
        self.send_response(response, conn_socket)



print("Starting server...")
Server()
