import json 
import threading
import time

# SERVER_IP = "localhost"

# AWS 
# SERVER_IP = "3.132.213.19"
SERVER_IP = "localhost"

DEFAULT_USERNAME = "default_user"
HOST_USERNAME = "HOST"

SERVER_PORT = 40
DEFAULT_P2P_PORT = 2000

# list of disallowed words for star-shaped meetings
BAD_WORDS = ["xxx", "yyy", "zzz"]

# maximum number of warnings for users in star-shaped meetings 
MAX_WARNINGS     = 3

# maximum number of queued connection 
# requests for a host 
MAX_QUEUED_REQUESTS = 5


MSG_DELIM = ";"



