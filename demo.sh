#!/usr/bin/env bash
#
# demo.sh orchestrates an end-to-end demonstration of the C3 privacy
# architecture using Docker Compose.  It builds the images, starts
# nginx and the two relay stubs, runs a baseline traffic scenario and
# then an obfuscated traffic scenario.  For each scenario it captures
# the relay logs and analyses them using analyzer.py to compute
# packet size and timing statistics.  Finally it displays the
# results and brings down the services.

set -euo pipefail

ROOT_DIR="$(dirname "$0")"
cd "$ROOT_DIR"

echo "[demo] Building Docker images..."
docker compose build

echo "[demo] Starting nginx and relays..."
# start services in the background; client will be run via docker compose run
docker compose up -d nginx relay2 relay1

# give services time to become ready
sleep 2

run_test() {
    local mode=$1
    local log_file=$2
    # restart relay1 container to clear logs between runs
    echo "[demo] Restarting relay1 for clean logs before ${mode} run..."
    docker compose restart -t 0 relay1
    # allow restart to complete
    sleep 2
    echo "[demo] Running client in ${mode} mode..."
    docker compose run --rm client --mode "${mode}" --host relay1 --port 9001 --count 3
    echo "[demo] Capturing relay1 logs for ${mode} run..."
    docker compose logs --no-color relay1 > "${log_file}"
}

run_test baseline baseline.log
run_test obfuscate obfuscate.log

echo "[demo] Computing metrics..."
python3 analyzer.py baseline.log > baseline_metrics.txt
python3 analyzer.py obfuscate.log > obfuscate_metrics.txt

echo "\n==== Baseline metrics ===="
cat baseline_metrics.txt
echo "\n==== Obfuscation metrics ===="
cat obfuscate_metrics.txt

echo "[demo] Cleaning up containers..."
docker compose down

echo "[demo] Demo complete."



