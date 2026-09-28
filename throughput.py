import sys
import random
import iperfserver

SERVLIST = "listed_iperf3_servers.json"
DEFAULT_NUM = 10

def print_usage():
    print("Usage: throughput.py [n_servers]")

#print(f"argc: {len(sys.argv)}")
#print("args: ")
#for arg in sys.argv:
#    print(arg)

n_servers = DEFAULT_NUM

if len(sys.argv) == 2:
    try:
        n_servers = int(sys.argv[1])
    except ValueError:
        print("Couldn't parse [n_servers] argument")
        print_usage()
        exit(1)
elif len(sys.argv) > 2:
    print("One or no arguments expected")
    print_usage()
    exit(1)

#print("Running with " + str(n_servers))

biglist = iperfserver.parse_servers(SERVLIST)

for s in biglist:
    print(s.host)

print(f"\nServers available: {len(biglist)}")

servers = random.sample(biglist, n_servers)

print("\nChosen servers:")

for s in servers:
    print(s.host)
