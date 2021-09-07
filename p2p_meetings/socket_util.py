import traceback
import logging
import threading
from typing import Callable
from p2p_meetings.constants import * 
from p2p_meetings.message_types import * 


def make_socket():
    """
    Make TCP socket with timeout 
    """
    sock = socket(AF_INET, SOCK_STREAM)
    sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1) # FOR DEBUGGING
    # sock.settimeout(5)
    return sock


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
    conn_socket = make_socket()

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
        logging.error("Connection with meeting host failed: %s %s", str(addr_port), str(e))
        return None
    

def safe_send(conn_socket, msg_bytes):
    try:
        conn_socket.send(msg_bytes)
    except Exception as e:
        logging.error("Error occured while sending message over socket: %s", str(e))


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

    logging.error("Error: Second argument is not instance of SocketMessage: %s", str(msg_object))



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
                logging.error("Exception raised while listening to socket: %s", str(e))
                self.on_close()
                return

            # check time limit
            if self.time_exceeded():
                break

            if not message_bytes:
                # perform cleanup function 
                logging.debug("ListenThread socket closed (empty bytes) from recv()") 
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

                # decode message using MessageType constructor and check if 
                # it is a valid instance
                logging.debug("Decoding message with class %s", str(self.MessageType))
                message_obj = decode_message(message_str, self.MessageType)

                if message_obj is None or not message_obj.is_valid():
                    logging.debug("Invalid message object: %s", str(message_obj))
                else:
                    # process the message
                    try:
                        self.handle_message(message_obj)
                    except Exception as e:
                        logging.debug("Failed to process message: %s", str(e))
        
        # if while loop exited, perform cleanup function
        # and close socket
        safe_shutdown_close(self.conn_socket)

        self.on_close()







