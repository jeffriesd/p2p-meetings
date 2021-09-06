import logging
import sys
from p2p_meetings.client import * 

if __name__ == "__main__":
    logging.basicConfig(filename="client.log", level=logging.DEBUG)

    # create new log stream handler to print logs to stdout
    # in addition to log file 
    handler = logging.StreamHandler(sys.stdout)
    # only print INFO for client 
    handler.setLevel(logging.INFO)
    logging.getLogger().addHandler(handler)

    logging.debug("""\n
---------------------------------
------ Starting new client ------
---------------------------------
    """)



    c = Client()
