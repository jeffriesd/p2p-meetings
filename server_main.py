from p2p_meetings.central_server import * 
import sys
import logging

if __name__ == "__main__":
    logging.basicConfig(filename="server.log", level=logging.DEBUG)

    # create new log stream handler to print logs to stdout
    # in addition to log file 
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    logging.getLogger().addHandler(handler)

    logging.info("""\n
-----------------------------
------ Starting server ------
-----------------------------
    """)

    server = Server()
