import random
import socket
import struct
import cookie

SERV_ADDR = "speedtest.chi11.us.leaseweb.net"
SERV_PORT = 5201

# Give up on connect() after this many seconds
CONNECT_TIMEOUT = 10

# Give up on any single send/recv that makes no progress
# for this many seconds (non-responsive/overloaded server)
IO_TIMEOUT = 30

# iperf3 states that signal failure. States travel on CTRL
# as a single *signed* byte, so these arrive as 0xff, 0xfe.
SERVER_TERMINATE = 11
ACCESS_DENIED = -1
SERVER_ERROR = -2

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


class IperfError(Exception):
    pass


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


def connect(addr, port):
    sock = socket.create_connection((addr, port), timeout=CONNECT_TIMEOUT)
    sock.settimeout(IO_TIMEOUT)
    return sock


# Generate a token that identifies our iperf3 session
# (and encode it as a UTF-8 bytestring)
sid = cookie.generate_cookie().encode()

# Create some garbage data to send
data = random.randbytes(4194304)

ctrlsock = None
datasock = None

try:
    # Create control (CTRL) socket and connect
    ctrlsock = connect(SERV_ADDR, SERV_PORT)

    # Send the coookie to the server over the CTRL connection
    ctrlsock.sendall(sid)

    # Receive a state update from the server
    recv_state(ctrlsock, 0x09)
    print("Ready to exchange parameters")

    # Send the pre-JSON length specifier
    ctrlsock.sendall(bytes([0x00, 0x00, 0x00, 0x81]))

    # Send the parameters as JSON
    ctrlsock.sendall(PARAMS.encode())

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
    recv_state(ctrlsock, 0x0d)
    print("Server is ready to exchange results")

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
