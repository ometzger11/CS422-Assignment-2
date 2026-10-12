import socket
import cookie

SERV_ADDR = "speedtest.chi11.us.leaseweb.net"
SERV_PORT = 5201

###
### TODO:   Should we enable TCP immediate send semantics,
###         disabling Nagle's algorithm? The official iperf3
###         implementation seems to do this...
###

# Generate a token that identifies our iperf3 session
# (and encode it as a UTF-8 bytestring)
sid = cookie.generate_cookie().encode()

# Create control (CTRL) socket and connect
ctrlsock = socket.socket()
ctrlsock.connect((SERV_ADDR, SERV_PORT))

# Send the coookie to the server over the CTRL connection
ctrlsock.sendall(sid)
