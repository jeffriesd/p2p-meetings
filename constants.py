import json 
import threading
import time

# my ip addr is 24.216.148.212

# SERVER_IP = "localhost"
SERVER_IP = "24.216.148.212"


# this application uses port 40 
# since port 40 is unassigned according IANA:
# https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml
# P2P_PORT  = 8002
SERVER_PORT = 40

# maximum number of queued connection 
# requests for a host 
MAX_QUEUED_REQUESTS = 5


MSG_DELIM = ";"

P2P_PORT_OFFSET = 8000
def get_meeting_port(meetingID):
    """ 
    Give each meeting a unique port 
    based on its ID.
    """
    return P2P_PORT_OFFSET + meetingID


def convert_ip(addr):
    """
    Translate "127.0.0.1" or "localhost" 
    into public IP address 
    """
    if addr == SERVER_IP:
        return "localhost"
    # if addr in ["127.0.0.1", "localhost"]:
    #     return SERVER_IP
    return addr
