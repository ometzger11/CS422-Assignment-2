import csv, datetime, os, sys, time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
import iperftest

# Usage: python3 mini_batch.py [duration_s] [reps] [host] [port]
DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 60
REPS = int(sys.argv[2]) if len(sys.argv) > 2 else 1
HOST = sys.argv[3] if len(sys.argv) > 3 else "speedtest.chi11.us.leaseweb.net"
PORT = int(sys.argv[4]) if len(sys.argv) > 4 else 5201

with open("runs.csv", "w", newline="") as rf, open("samples.csv", "w", newline="") as sf:
    rw, sw = csv.writer(rf), csv.writer(sf)
    rw.writerow("run_id,server,port,algo_requested,algo_actual,rep,start_utc,status,error".split(","))
    sw.writerow(iperftest.SAMPLE_COLUMNS)
    for rep in range(REPS):
        for algo in ["cubic", "reno", "bbr"]:          # interleaved, as planned
            run_id = f"test-{algo}-r{rep}"
            start = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
            print(f"=== {run_id} ({DURATION}s)", flush=True)
            r = iperftest.run_test(HOST, PORT, DURATION, algo, 0.2, run_id, sw)
            rw.writerow([run_id, HOST, PORT, algo, r["algo_actual"] or "", rep,
                         start, r["status"], r["error"] or ""])
            rf.flush(); sf.flush()                     # keep data if you Ctrl+C
            time.sleep(1)                              # brief gap between tests