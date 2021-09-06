import json 
import threading

def nothing(*args, **kwargs):
    pass

print_to_server_log = nothing

# AWS 
# SERVER_IP = "3.132.213.19"

# local server
SERVER_IP = "localhost"

DEFAULT_USERNAME = "default_user"
HOST_USERNAME = "HOST"

SERVER_PORT = 2000
DEFAULT_P2P_PORT = 3100

# list of disallowed words for star-shaped meetings
#
# real-world use case would be for offensive language, 
# but we just use 'xxx' 'yyy' and 'zzz' as examples 
BAD_WORDS = ["xxx", "yyy", "zzz"]

# maximum number of warnings for users in star-shaped meetings 
MAX_WARNINGS = 3

TEST_MESSAGE = "test"

MSG_DELIM = ";"



