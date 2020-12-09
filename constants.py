import json 
import threading
import time

# SERVER_IP = "localhost"

# AWS 
SERVER_IP = "3.132.213.19"

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

