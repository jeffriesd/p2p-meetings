

from p2p_meetings.central_server import * 

if __name__ == "__main__":
    import logging
    logging.basicConfig(filename="server.log", level=logging.DEBUG)
    logging.info("""\n
-----------------------------
------ Starting server ------
-----------------------------
    """)

    # TODO print output of log file when running main 

    print("Starting server...")
    server = Server()


