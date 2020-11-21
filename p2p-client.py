from sockets import *



# this application uses port 40 
# since port 40 is unassigned according IANA:
# https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml
P2P_PORT = 40



class PeerNode:
    """
    """

    def __init__(self):
        # maintain list of peer ips
        self.peers = []

        # maintain dictionary of tcp connections
        # keyed on ip addr
        self.connections = {}

    def connect_and_listen(self, addr):
        """
        Connect with peer and listen for incoming data
        """
        # create new tcp connection with peer
        client_socket = socket(AF_INET, SOCK_STREAM)
        client_socket.connect((addr, P2P_PORT))

        # TODO create a new thread to listen 

        # listen for data on tcp connection 
        response_bytes = bytearray()
        while True:
            response = client_socket.recv(1024)
            if not response:
                break
            response_bytes += response



        


    

                        


        


