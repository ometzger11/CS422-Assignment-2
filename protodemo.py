import random
import socket
import cookie

SERV_ADDR = "speedtest.chi11.us.leaseweb.net"
SERV_PORT = 5201

###
### FIXME:  Changing this without manually changing the length
###         specifier in the code will cause breakage (unless
###         the number of bytes remains unaffected).
###
###         If you change "num", you also have to change the
###         number of bytes in the randomly generated data block.
###
PARAMS = '{"tcp":true,"omit":0,"time":0,"num":4194304,"blockcount":0,' + \
         '"parallel":1,"len":131072,"pacing_timer":1000,' + \
         '"client_version":"3.16"}'

###
### TODO:   Should we enable TCP immediate send semantics,
###         disabling Nagle's algorithm? The official iperf3
###         implementation seems to do this...
###
###         TCP_NODELAY is probably desirable for the control
###         connection, but the official implementation doesn't
###         seem to use it for the data connection.
###

# Generate a token that identifies our iperf3 session
# (and encode it as a UTF-8 bytestring)
sid = cookie.generate_cookie().encode()

# Create some garbage data to send
data = random.randbytes(4194304)

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
    exit("Server said something invalid (1)")

# Send the pre-JSON length specifier
ctrlsock.sendall(bytes([0x00, 0x00, 0x00, 0x81]))

# Send the parameters as JSON
ctrlsock.sendall(PARAMS.encode())

# Receive another state update
received = ctrlsock.recv(1)

print(f"Got: {received[0]:#x}")

if received[0] == 0x0a:
    print("Ready to create streams")
else:
    exit("Server said something invalid (2)")

# Create data (DATA) socket and connect
datasock = socket.socket()
datasock.connect((SERV_ADDR, SERV_PORT))

# Send the same cookie as before to identify our session
datasock.sendall(sid)

# Receive a third state update on CTRL (!)
received = ctrlsock.recv(1)

print(f"Got: {received[0]:#x}")

if received[0] == 0x01:
    print("Server wants to start test")
else:
    exit("Server said something invalid (3)")

# Receive a fourth state update on CTRL
received = ctrlsock.recv(1)

print(f"Got: {received[0]:#x}")

if received[0] == 0x02:
    print("Server considers test to be running")
else:
    exit("Server said something invalid (4)")

# Send all data

# TODO: Eventually, we may want to refactor this into
# a loop that calls normal send() repeatedly instead of
# sendall(), because that would allow periodic tracking
# of progress/stats when a large transfer takes multiple
# seconds to complete.
print("About to send all data...")
datasock.sendall(data)
print("Done sending data")

# Send a state update on CTRL ending the test
print("Sending end-of-test")
ctrlsock.sendall((0x04).to_bytes())

# Receive a fifth state update on CTRL
received = ctrlsock.recv(1)

print(f"Got: {received[0]:#x}")

if received[0] == 0x0d:
    print("Server is ready to exchange results")
else:
    exit("Server said something invalid (5)")

# Clean up
datasock.close()
ctrlsock.close()
