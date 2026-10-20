import random
import socket
import struct
import time
import cookie

SERV_ADDR = "speedtest.chi11.us.leaseweb.net"
SERV_PORT = 5201

# Give up on connect() after this many seconds
CONNECT_TIMEOUT = 10

# Give up on any single send/recv that makes no progress
# for this many seconds (non-responsive/overloaded server)
IO_TIMEOUT = 30

# Send data in chunks not exceeding this size. This TCP
# block size is from iperf_api.h
DATASIZE = 128 * 1024

# iperf3 states that signal failure. States travel on CTRL
# as a single *signed* byte, so these arrive as 0xff, 0xfe.
SERVER_TERMINATE = 11
ACCESS_DENIED = -1
SERVER_ERROR = -2

###
### FIXME:  If you change "num", you also have to change the
###         number of bytes in the randomly generated data block.
###
PARAMS = '{"tcp":true,"omit":0,"time":0,"num":4194304,"blockcount":0,' + \
         '"parallel":1,"len":131072,"pacing_timer":1000,' + \
         '"client_version":"3.16"}'

###
### FIXME: This is fudged data. We may be able to get real
###        values for some fields, but others are just going
###        to be reasonable pretend values to make the server
###        happy.
###
RESULTS = '{"cpu_util_total":53.2998321894476,"cpu_util_user":53.0150572247701,' + \
          '"cpu_util_system":0.28468351478516135,"sender_has_retransmits":1,' + \
          '"congestion_used":"cubic","streams":[{"id":1,"bytes":4194304,' + \
          '"retransmits":0,"jitter":0,"errors":0,"omitted_errors":0,"packets":0,' + \
          '"omitted_packets":0,"start_time":0,"end_time":1.000399}]}'


# Type of exception raised when iperf3 server does
# something bad
class IperfError(Exception):
    pass


# Receive an exact number of bytes from the socket.
#
# Blocks until the desired length is met by incoming
# data. When the data is available, it is returned as
# as a bytes object.
#
# If the connection is closed before n bytes can be
# received, an IperfError exception is raised.
def recv_exact(sock, n):
    # recv() may return fewer bytes than asked for, and returns
    # b"" once the peer has closed the connection
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise IperfError("Server closed the connection prematurely")
        buf += chunk
    return bytes(buf)

# Get a state update from the server (blocking).
#
# If the server sets the state to the expected state,
# nothing happens, and None is returned.
#
# If the server encounters an errorr or unilaterally
# terminates the test, an IperfError is raised.
#
# An IperfError is also raised if the state update
# is valid, but does not match expected.
def recv_state(sock, expected):
    state = recv_exact(sock, 1)[0]

    print(f"Got: {state:#x}")

    if state == expected:
        return

    if state == ACCESS_DENIED:
        # Sent by servers that are busy running another test
        raise IperfError("Server denied access (busy or rate-limited)")

    if state == SERVER_ERROR:
        # Followed by the server's iperf3 error code and errno,
        # each a 4-byte big-endian int
        i_errno, err = struct.unpack("!ii", recv_exact(sock, 8))
        raise IperfError(f"Server reported an error "
                         f"(i_errno={i_errno}, errno={err})")

    if state == SERVER_TERMINATE:
        raise IperfError("Server terminated the test")

    raise IperfError(f"Server said something invalid "
                     f"(got {state:#x}, expected {expected:#x})")

# Send a bytestring of variable length by first sending an
# integer specifying the length followed by the encoded
# string itself.
#
# The argument should be a bytes object (not a
# conventional Python string)
def send_varbytes(sock, bytestring):
    # Length indicator is 32-bit (4 bytes) and
    # must be big-endian
    length = len(bytestring)
    length_bstr = length.to_bytes(4, "big")
    
    sock.sendall(length_bstr)
    sock.sendall(bytestring)

# Send an ordinary Python string of variable length by
# first sending an integer specifying the length followed
# by the UTF-8 encoding of the string.
#
# For dumb bytes or strings of different encodings, see
# send_varbytes() above.
def send_varstr(sock, pystring):
    send_varbytes(sock, pystring.encode())

# Open a TCP socket and connect to address and port.
# A timeout is used for the connection. See the constant
# CONNECT_TIMEOUT above.
#
# Exceptions from socket module are allowed to propagate
# on failure.
def connect(addr, port):
    sock = socket.create_connection((addr, port), timeout=CONNECT_TIMEOUT)
    sock.settimeout(IO_TIMEOUT)
    return sock

# Shut down a TCP socket for writing and then wait
# for the other end to hang up before destroying the
# socket.
def sync_close(sock):
    sock.shutdown(socket.SHUT_WR)
    
    while sock.recv(128):
        pass
    
    sock.close()

# Generate a token that identifies our iperf3 session
# (and encode it as a UTF-8 bytestring)
sid = cookie.generate_cookie().encode()

# Create some garbage data to send
#data = random.randbytes(4194304)
data = random.randbytes(DATASIZE)

# Sockets for control and data streams
ctrlsock = None
datasock = None

try:
    # Create control (CTRL) socket and connect
    ctrlsock = connect(SERV_ADDR, SERV_PORT)
    
    # Eliminate unnecessary buffering on CTRL connection
    ctrlsock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    # Send the coookie to the server over the CTRL connection
    ctrlsock.sendall(sid)

    # Receive a state update from the server
    recv_state(ctrlsock, 0x09)
    print("Ready to exchange parameters")
    
    # Send the parameters as JSON
    send_varstr(ctrlsock, PARAMS)

    # Receive another state update (a server that rejects
    # our parameters answers with SERVER_ERROR or hangs up)
    recv_state(ctrlsock, 0x0a)
    print("Ready to create streams")

    # Create data (DATA) socket and connect
    datasock = connect(SERV_ADDR, SERV_PORT)

    # Send the same cookie as before to identify our session
    datasock.sendall(sid)

    # Receive a third state update on CTRL (!)
    recv_state(ctrlsock, 0x01)
    print("Server wants to start test")

    # Receive a fourth state update on CTRL
    recv_state(ctrlsock, 0x02)
    print("Server considers test to be running")

    # Send all data
    print("About to send data blocks...")
    
    # TODO: customizable time
    duration = 4.0
    
    launch_time = time.time()
    done_at = launch_time + duration
    
    bytes_sent = 0
    
    while time.time() < done_at:
        if bytes_sent == len(data):
            bytes_sent = 0
    
        bytes_sent = datasock.send(data[bytes_sent:])
    
    print("Done sending data")
    
    # Seeks to avoid a race condition where the data is in
    # flight when the test terminates.
    # TODO: make sure this doesn't impact result accuracy
    time.sleep(0.5)

    # Send a state update on CTRL ending the test
    print("Sending end-of-test")
    ctrlsock.sendall((0x04).to_bytes())

    # Receive a fifth state update on CTRL
    recv_state(ctrlsock, 0x0d)
    print("Server is ready to exchange results")
    
    # Send the JSON result string to the server
    send_varstr(ctrlsock, RESULTS)
    
    # Get JSON results from the server
    reslen = struct.unpack("!i", recv_exact(ctrlsock, 4))[0]
    resjson = recv_exact(ctrlsock, reslen).decode()

    # Receive a sixth state update on CTRL
    recv_state(ctrlsock, 0x0e)
    print("Server is ready for us to display results")
    
    # Close DATA connection
    datasock.close()
    datasock = None
    
    # Inform server of state transition to IPERF_DONE
    ctrlsock.sendall((0x10).to_bytes())
    
    # Close CTRL connection
    sync_close(ctrlsock)
    ctrlsock = None
    
    # Output
    print("Got results:")
    print(resjson)

except IperfError as e:
    exit(str(e))
except socket.gaierror as e:
    exit(f"Couldn't resolve {SERV_ADDR}: {e}")
except TimeoutError:
    exit("Timed out waiting on the server")
except ConnectionError as e:
    # Refused, reset, or broken pipe mid-test
    exit(f"Connection failed: {e}")
except OSError as e:
    exit(f"Network error: {e}")
finally:
    # Clean up
    if datasock:
        datasock.close()
    if ctrlsock:
        ctrlsock.close()
