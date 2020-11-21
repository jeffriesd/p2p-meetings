from socket import *



# this application uses port 40 
# since port 40 is unassigned according IANA:
# https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml
P2P_PORT = 40


# maximum outgoing connections 
MAX_OUTGOING = 5


class HostNode:
    """
    """

    def __init__(self, name):
        self.room_name = name

        # maintain list of peer ips
        self.peers = []

        # maintain dictionary of tcp connections 
        # (socket objects) keyed on ip addr
        self.connections = {}

    def wait_for_connections(self):
        """
        Wait for incoming tcp connection requests, 
        then send some test data when they connect.
        """
        # TODO put this in its own thread
        
        server_socket = socket(AF_INET, SOCK_STREAM)
        server_socket.bind(('', P2P_PORT))
        server_socket.listen(MAX_OUTGOING)

        while True:
            connection_socket, addr = server_socket.accept()
            test_string = "You are connected to host %s!" % self.room_name
            connection_socket.send(test_string.encode())

            # add this connection to the list
            self.connections[addr] = connection_socket


            # TODO just for debugging
            break

    def broadcast_message(self, msg_str):
        """
        Given a message as a string, send it to every peer. 
        """
        msg_bytes = msg_str.encode()
        for peer_addr in self.connections:
            # send encoded message
            self.connections[peer_addr].send(msg_bytes)



class AudienceNode:

    def __init__(self, host_addr):
        """
        Connect to host and save reference to the socket object.
        """
        self.host_addr = host_addr
        # create new tcp connection with hosting peer
        self.client_socket = socket(AF_INET, SOCK_STREAM)

        # TODO ERROR HANDLING
        try:
            self.client_socket.connect((host_addr, P2P_PORT))
            print("Connected successfully")
            
            # listen for messages from host 
            self.listen_to_host()
        except:
            self.client_socket.close()
            print("Connection failed")


        
    def listen_to_host(self):
        """
        Connect with host and listen for incoming data
        """

        # TODO create a new thread to listen 

        # listen for data on tcp connection 
        while True:
            response = self.client_socket.recv(1024)

            # TODO add error handling in case connection
            # is closed by host 
            if not response:
                break
            print("New message: %s" % response.decode())


    

                        


        


