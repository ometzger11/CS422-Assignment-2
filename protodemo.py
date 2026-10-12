import socket
import cookie

SERV_ADDR = "speedtest.chi11.us.leaseweb.net"
SERV_PORT = 5201

PARAMS = '{"tcp":true,"omit":0,"time":10,"num":0,"blockcount":0,' + \
         '"parallel":1,"len":131072,"pacing_timer":1000,' + \
         '"client_version":"3.16"}'

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

# Receive a state update from the server
received = ctrlsock.recv(1)

if len(received) == 0:
    exit("Uh-oh. We got disconnected")

print(f"Got: {received[0]:#x}")

if received[0] == 0x09:
    print("Ready to exchange parameters")
else:
    exit("Server said something invalid")

# Send the pre-JSON length specifier
ctrlsock.sendall(bytes([0x00, 0x00, 0x00, 0x7c]))

# Send the parameters as JSON
ctrlsock.sendall(PARAMS.encode())

# Receive another state update
received = ctrlsock.recv(1)

print(f"Got: {received[0]:#x}")
