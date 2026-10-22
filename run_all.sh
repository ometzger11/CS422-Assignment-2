#!/usr/bin/env bash
# Full pipeline: record environment -> run tests -> make plots.
#
# Usage: ./run_all.sh [-n SERVERS] [--duration SEC] [--interval SEC] [--reps N] [--out DIR]
#
# Works both in Docker (results go to /results) and directly in the repo.
set -euo pipefail
cd "$(dirname "$0")"

N=10
DURATION=60
INTERVAL=0.2
REPS=3
OUT="${RESULTS_DIR:-results}"

while [ $# -gt 0 ]; do
    case "$1" in
        -n)         N="$2"; shift 2 ;;
        --duration) DURATION="$2"; shift 2 ;;
        --interval) INTERVAL="$2"; shift 2 ;;
        --reps)     REPS="$2"; shift 2 ;;
        --out)      OUT="$2"; shift 2 ;;
        -h|--help)  sed -n '2,6p' "$0"; exit 0 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

mkdir -p "$OUT"
REPO="$(pwd)"

# 1. Record the host environment (the kernel decides TCP behavior, not the container)
{
    echo "date_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "kernel: $(uname -r)"
    echo "arch: $(uname -m)"
    echo "available_cc: $(cat /proc/sys/net/ipv4/tcp_available_congestion_control)"
    echo "allowed_cc: $(cat /proc/sys/net/ipv4/tcp_allowed_congestion_control)"
    echo "default_cc: $(cat /proc/sys/net/ipv4/tcp_congestion_control)"
    echo "python: $(python3 --version 2>&1)"
    echo "settings: n=$N duration=$DURATION interval=$INTERVAL reps=$REPS"
} > "$OUT/environment.txt"
cat "$OUT/environment.txt"

# Make sure every algorithm can actually be selected on a socket here
python3 - <<'PY' || exit 1
import socket, sys, tcpinfo
bad = []
for algo in ("cubic", "reno", "bbr"):
    with socket.socket() as s:
        try:
            tcpinfo.set_congestion(s, algo)
        except OSError as e:
            bad.append(f"{algo} ({e.strerror})")
if bad:
    sys.exit("ERROR: can't select " + ", ".join(bad) + ".\n"
             "On the host: sudo modprobe tcp_bbr, and list all three in "
             "net.ipv4.tcp_allowed_congestion_control")
PY

# 2. Run the tests (writes runs.csv and samples.csv into $OUT)
# TODO: replace with Trevor's runner once it exists, e.g.
#   python3 "$REPO/runner.py" -n "$N" --duration "$DURATION" --interval "$INTERVAL" \
#       --reps "$REPS" --runs "$OUT/runs.csv" --samples "$OUT/samples.csv"
# Placeholder: single-server test (ignores -n and --interval; TEST_HOST overrides the server)
(cd "$OUT" && python3 "$REPO/tests/mini_batch.py" "$DURATION" "$REPS" ${TEST_HOST:+"$TEST_HOST"})

# 3. Plots and summary tables
python3 "$REPO/plots.py" --runs "$OUT/runs.csv" --samples "$OUT/samples.csv" \
    --out "$OUT/plots"

echo "Done. Results in $OUT/"