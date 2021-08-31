import traceback
import threading
from p2p_meetings.constants import * 
from p2p_meetings.server_messages import * 


def safe_shutdown_close(socket):
    """
    Shutdown and close a socket. 
    This function ensures no exceptions are 
    raised (e.g., because the socket has already been closed).
    """
    try:
        # shutdown socket, disallowing further 
        # sends or receives 
        socket.shutdown(SHUT_RDWR)
        # close socket
        socket.close()
    except:
        pass

def connect_to_peer(addr_port):
    """
    Try to connect to host at addr_port 
    and return socket object on success. 
    """
    conn_socket = socket(AF_INET, SOCK_STREAM)
    conn_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1) # FOR DEBUGGING

    if type(addr_port) is list:
        addr_port = tuple(addr_port)

    try:
        # connecting to another mesh will cause 
        # P to add a new entry to P.peers and create a new
        # thread to listen to messages from this user
        conn_socket.connect(addr_port)

        return conn_socket
    except Exception as e:
        safe_shutdown_close(conn_socket)
        print("Connection with meeting host failed: ", addr_port, e)
        traceback.print_stack()
        return None
    

def safe_send(conn_socket, msg_bytes):
    try:
        conn_socket.send(msg_bytes)
    except Exception as e:
        print("Error occured while sending message over socket: ", e)


def send_socket_message(conn_socket, msg_object):
    """
    Accepts a SocketMessage object and 
    sends it over a socket. Perform a simple
    instance check to ensure msg_object is an instance
    of SocketMessage
    """
    if isinstance(msg_object, SocketMessage):
        safe_send(conn_socket, msg_object.encode())
        return

    print("Error: Second argument is not instance of SocketMessage: ", msg_object)
    traceback.print_stack()



class ListenThread:
    """
    ListenThread is an abstraction for the process of 
    looping continuously to listen and respond to messages on a socket.


    A timer option (keep_alive_sec specifies the number of seconds on the timer, 
    or 0 for no limit) allows one to specify how long the connection should be 
    left open. After the time limit expires, if the connection is still open, then
    it is closed. 
    """

    def __init__(self, MessageType, conn_socket, handle_message, 
                    on_close, keep_alive_sec = 0):

        self.MessageType = MessageType
        self.conn_socket = conn_socket
        self.handle_message = handle_message
        self.on_close = on_close
        
        self.keep_alive = True

        # optional timer for thread 
        self.keep_alive_sec = keep_alive_sec
        if keep_alive_sec:
            self.start_time = int(time.time())

        self.listen_thread = threading.Thread(target=self.listen_and_do)

    def start(self):
        """
        Start listening thread"
        """
        self.listen_thread.start()

    def stop(self):
        """
        Stop thread by setting loop flag to False. 
        """
        self.keep_alive = False

    def time_exceeded(self):
        """
        If timer being used, check time limit.
        If time is up, close the connection.
        """
        if self.keep_alive_sec <= 0:
            return False

        cur_secs = int(time.time())
        return cur_secs - self.start_time > self.keep_alive_sec

    def listen_and_do(self):
        """
        While keep_alive flag is set, 
        listen for messages on a socket. 

        If socket is closed, on_close function is performed.

        Messages should fit into some class given
        by MessageType. Example classes are 
        MeetingRequest or ServerResponse. These
        classes come equipped with an is_valid 
        method to validate the message contents. 

        Well-formed messages get processed by 
        handle_message function.
        """
        while self.keep_alive:
            message_bytes = bytearray()
            try:
                message_bytes = self.conn_socket.recv(1024)
            except Exception as e:
                print("Exception raised while listening to socket:", e)
                self.on_close()
                return

            # check time limit
            if self.time_exceeded():
                break

            if not message_bytes:
                # perform cleanup function 
                # print("ListenThread socket closed (empty bytes) from recv()") 
                self.on_close()
                return
            
            message_str = ""
            try:
                message_str = message_bytes.decode()
            except:
                # message cant be decoded, just ignore it
                continue

            # message may contain several requests, 
            # so split it on the special request delimiter 
            # character
            message_strs = message_str.split(MSG_DELIM)

            for message_str in message_strs: 
                if not message_str:  # ignore empty string
                    continue

                # we only want to handle message
                # that can be parsed as dictionaries (JSON)
                message_dict = {}
                try:
                    message_dict = json.loads(message_str)
                except:
                    # couldn't parse as dictionary, ignore it
                    continue
                
                # use MessageType constructor and check if 
                # it is a valid instance
                message_obj = self.MessageType(message_dict)

                if not message_obj.is_valid():
                    print("Invalid message object: ", message_obj)
                else:
                    # process the message
                    try:
                        self.handle_message(message_obj)
                    except Exception as e:
                        print("Failed to process message: ", e)
                        traceback.print_exc()
        
        # if while loop exited, still perform cleanup function
        # and close socket
        safe_shutdown_close(self.conn_socket)

        self.on_close()







