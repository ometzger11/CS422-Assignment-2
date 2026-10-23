import random
import datetime as dt
import iperfserver
import iperftest


SERVLIST = "listed_iperf3_servers.json"
ALGOS = ["cubic", "reno", "bbr"]
#ALGOS = ["cubic", "reno"]

TARGET_NUM = 5
NUM_REPS = 3
NUM_RETRIES = 3
DURATION = 2
INTERVAL = 0.2

def parse_port(port_str):
    parts = port_str.split("-")

    if 1 <= len(parts) <= 2:
        return int(parts[0])
    else:
        raise ValueError("Bad port string in JSON server list")

def robust_repeat(server):
    ever_succeeded = False

    for algo in ALGOS:
        reps = 0
        strikes = 0
    
        while reps < NUM_REPS:
            now_str = dt.datetime.now().isoformat()
            run_id = f"{now_str}-{algo}-r{reps}-s{strikes}"
            
            print("************ " + run_id)
        
            results = iperftest.run_test(
                server.host,
                parse_port(server.port),
                DURATION,
                algo,
                INTERVAL,
                run_id
            )
        
            if results["error"] is None:
                reps += 1
                strikes = 0
                
                ever_succeeded = True
            else:
                strikes += 1
                
                if not ever_succeeded or strikes == NUM_RETRIES:
                    return False
    
    return True


servers = iperfserver.parse_servers(SERVLIST)

successes = 0
failures = 0

while successes < TARGET_NUM:
    serv_count = len(servers)
    
    if serv_count == 0:
        print("\nShortfall occurred!")
        print(f"Managed {successes}/{TARGET_NUM}")
        break
    
    selected_idx = random.randint(0, serv_count - 1)
    selected_server = servers.pop(selected_idx)
    
    print(f"\nChose: {selected_server}")
    
    if robust_repeat(selected_server):
        successes += 1
        print(f"Accepted: {selected_server}")
    else:
        failures += 1
        print(f"Gave up on: {selected_server}")

print("\nDone!")
print(f"Successes: {successes}, Failures: {failures}")
