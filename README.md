# p2p-meetings

In this project, I implement a peer-to-peer chat/meeting application using TCP connections via the socket library in Python. 
There are two types of meeting rooms in this application, one using a full-mesh network topology and one using a star-shaped network topology. 
Each meeting room has a host who is responsible for connecting with new meeting attendees and maintaining a list of attendees. 
There is a central server that is responsible for keeping a list of active meetings and the address of each host. 

## Creating/joining new meetings
To create a new meeting, the client connects to the central server. The client then gives the central server its IP address and port, 
and the server creates a new entry in its list of active meetings. 
To join an existing meeting, a client must first connect to the central server and ask for the list of active meetings.
The client can then pick one of the active meetings to join. A peer-to-peer TCP connection is established between the new client 
and the host of the chosen meeting. Then the client disconnects from the server and only communicates with the other clients 
in the meeting. 


## Star-shaped
In a star-shaped meeting, there is a host client and 0 or more attendee clients. There is a single TCP connection from each attendee client to the host, 
so the host can broadcast messages to the entire group, but attendees cannot communicate directly. 
Attendees can communicate with the host, but only the host.
This type of meeting is intended for classrooms or lectures where there is a single individual in charge of communication. 

## Full-mesh 
In a full-mesh meeting, all peers are connected to each other. There is a still a host, but its only role is to maintain the list of attendees 
and share this list with new attendees so they may join the full-mesh network. All clients in a full-mesh meeting can communicate with each other. 
They can broadcast messages to the whole meeting, or they direct other clients in the meeting directly. This type of meeting 
is intended for decentralized communications like chat rooms. 
