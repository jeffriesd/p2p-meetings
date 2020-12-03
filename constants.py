import json 
import threading
import time

# my ip addr is 24.216.148.212

SERVER_IP = "localhost"

SERVER_PORT = 40

# this application uses port 40 
# since port 40 is unassigned according IANA:
# https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml
P2P_PORT = SERVER_PORT


# maximum number of queued connection 
# requests for a host 
MAX_QUEUED_REQUESTS = 5


MSG_DELIM = ";"



def safe_send(conn_socket, msg_bytes):
    try:
        conn_socket.send(msg_bytes)
    except Exception as e:
        print("Error occured while sending message over socket: ", e)


class ListenThread:
# [-] need abstraction for "listen to messages from this socket
#     in a separate thread until the socket is closed, 
#     and when you get a message mbytes, perform f(mbytes)"

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

    def check_timer(self):
        """
        If timer being used, check time limit.
        If time is up, close the connection.
        """
        # if flag True and using timer, check time
        if self.keep_alive_sec:
            cur_secs = int(time.time())
            if cur_secs - self.start_time > self.keep_alive_sec:
                self.conn_socket.close()

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
            # check time limit, possibly closing socket
            self.check_timer()

            message_bytes = bytearray()
            try:
                message_bytes = self.conn_socket.recv(1024)
            except:
                print("Exception raised while listening to socket")
                self.on_close()
                return

            if not message_bytes:
                # perform cleanup function 
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
                    print("Received non-dictionary message:", message_str)
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
                    except:
                        print("Failed to process message")
        
        # if while loop exited, still perform cleanup function
        # and close socket

        self.conn_socket.close()

        self.on_close()






