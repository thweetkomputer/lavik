#!/usr/bin/env python3
"""Run reproducible fixed-footprint String sweeps from the benchmark server.

The memtier client lives on 172.16.0.5. Each size rebuilds an exact key range
before random reads, so GET miss counts and value lengths can be checked.
"""

import argparse
import json
import os
from pathlib import Path
import re
import shlex
import signal
import subprocess
import time


ROOT = Path(__file__).resolve().parent
HOST = "172.16.0.4"
CLIENT = "172.16.0.5"
PORT = "6379"
CLI = "/mnt/dev/peer-bench/redis/v8.8.0/src/src/redis-cli"
PEERS = {
    "redis": "/mnt/dev/peer-bench/redis/v8.8.0/src/src/redis-server",
    "valkey": "/mnt/dev/peer-bench/valkey/v9.1.0/src/src/valkey-server",
}
SIZES = (2048, 4096, 8192, 32768, 131072)
CONNECTIONS = 80
CLIENT_THREADS = 8
FOOTPRINT = 8 * 1024**3


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def call(args, **kwargs):
    return subprocess.run(args, check=True, text=True, **kwargs)


def cli(*args):
    return subprocess.check_output([CLI, "-h", HOST, "-p", PORT, "--raw", *map(str, args)], text=True, timeout=120,
                                   stderr=subprocess.DEVNULL).strip()


def run_client(directory, kind, size, keys, seconds, *, connections=CONNECTIONS,
               client_threads=CLIENT_THREADS, sweep=False):
    stem = f"{size}-{kind.lower()}" + (f"-c{connections}" if sweep and kind != "FILL" else "")
    remote = f"/mnt/dev/lavik-large-value-20260926-client/{directory.name}/{stem}.json"
    cmd = ["taskset", "-c", "0-15", "memtier_benchmark", "--server=" + HOST,
           "--port=" + PORT, "--protocol=redis", f"--threads={client_threads}",
           f"--clients={connections // client_threads}", "--pipeline=1",
           "--ratio=" + ("1:0" if kind == "FILL" else "0:1" if kind == "GET" else "1:0"),
           "--key-minimum=1", f"--key-maximum={keys}", "--key-prefix=kv_",
           f"--data-size={size}", "--hide-histogram",
           "--print-percentiles=50,95,99,99.9,99.99", "--show-config",
           "--json-out-file=" + remote]
    if kind == "FILL":
        cmd += ["--requests=allkeys", "--key-pattern=P:P"]
    else:
        cmd += [f"--test-time={seconds}", "--key-pattern=R:R", "--distinct-client-seed"]
    save(directory / f"{stem}.command.json", cmd)
    remote_cmd = "mkdir -p " + shlex.quote(str(Path(remote).parent)) + "; ulimit -n 65535; exec " + shlex.join(cmd)
    print(time.strftime("%F %T", time.gmtime()), directory.name, stem, "start", flush=True)
    nic = Path("/sys/class/net/eth0/statistics")
    net_before = {name: int((nic / name).read_text()) for name in ("tx_bytes", "rx_bytes")}
    started = time.monotonic()
    ssh = (["sudo", "-u", "azureuser"] if os.geteuid() == 0 else []) + ["ssh", "-o", "BatchMode=yes", CLIENT]
    with (directory / f"{stem}.txt").open("w") as log:
        call([*ssh, remote_cmd], stdout=log, stderr=subprocess.STDOUT, timeout=7200)
    elapsed = time.monotonic() - started
    net_after = {name: int((nic / name).read_text()) for name in net_before}
    save(directory / f"{stem}.net.json", {"before": net_before, "after": net_after,
                                           "elapsed_seconds": elapsed})
    with (directory / f"{stem}.json").open("w") as output:
        call([*ssh, "cat " + shlex.quote(remote)], stdout=output, timeout=60)
    data = json.loads((directory / f"{stem}.json").read_text())["ALL STATS"]
    body = (directory / f"{stem}.txt").read_text().replace("\r", "\n")
    total = [s.split() for s in body.splitlines() if s.startswith("Totals")]
    if len(total) != 1 or len(total[0]) != 11:
        raise RuntimeError(f"Unexpected memtier total: {stem}")
    if data["Totals"]["Connection Errors"] != 0 or str(data["Runtime"]["Interrupted"]).lower() != "false":
        raise RuntimeError(f"Client connection error or interrupt: {stem}")
    if re.search(r"error response|OOM command|connection error", body, re.I):
        raise RuntimeError(f"Server error: {stem}")
    if kind == "GET":
        gets = [s.split() for s in body.splitlines() if s.startswith("Gets")]
        if len(gets) != 1 or float(gets[0][3]) != 0:
            raise RuntimeError(f"GET misses: {stem}")
    if kind == "FILL" and data["Totals"]["Count"] != keys:
        raise RuntimeError(f"Incomplete fill: {stem} {data['Totals']['Count']} != {keys}")
    row = total[0]
    result = dict(product=directory.name, size=size, keys=keys, kind=kind,
                  connections=connections, client_threads=client_threads,
                  qps=float(row[1]), avg_ms=float(row[4]), p99_ms=float(row[7]),
                  p999_ms=float(row[8]), p9999_ms=float(row[9]),
                  count=data["Totals"]["Count"], seconds=seconds)
    save(directory / f"{stem}.result.json", result)
    print(time.strftime("%F %T", time.gmtime()), directory.name, stem,
          f"{result['qps']:.1f} QPS p99={result['p99_ms']}", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("product", choices=PEERS)
    parser.add_argument("--seconds", type=int, default=30)
    parser.add_argument("--sweep", action="store_true")
    parser.add_argument("--levels", default="80,320,640,1280,2560,5120")
    parser.add_argument("--sizes", default=",".join(map(str, SIZES)))
    parser.add_argument("--tag", default="")
    options = parser.parse_args()
    directory = ROOT / "raw" / (options.product + ("-" + options.tag if options.tag else ""))
    directory.mkdir(parents=True, exist_ok=True)
    binary = PEERS[options.product]
    command = ["taskset", "-c", "0-15", binary, "--bind", HOST,
               "--protected-mode", "no", "--port", PORT, "--daemonize", "no",
               "--dir", str(directory), "--save", "", "--appendonly", "no",
               "--maxmemory", "0", "--maxclients", "10000", "--io-threads", "12"]
    save(directory / "server-command.json", command)
    if cli_available():
        raise RuntimeError("Port already in use")
    with (directory / "server.log").open("w") as output:
        process = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT)
    try:
        for _ in range(100):
            if process.poll() is not None:
                raise RuntimeError("Server exited during startup")
            if cli_available():
                break
            time.sleep(0.2)
        else:
            raise TimeoutError("Server startup")
        save(directory / "version.json", {"binary": binary, "version": cli("INFO", "SERVER"),
                                          "io_threads": cli("CONFIG", "GET", "io-threads")})
        for size in map(int, options.sizes.split(",")):
            keys = (FOOTPRINT // size // CONNECTIONS) * CONNECTIONS
            levels = tuple(map(int, options.levels.split(","))) if options.sweep else (80,)
            if any(c % 16 or c <= 0 for c in levels):
                raise ValueError("Sweep connections must be positive multiples of 16")
            suffix = f"-c{levels[-1]}" if options.sweep else ""
            if (directory / f"{size}-set{suffix}.result.json").exists():
                continue
            assert cli("FLUSHALL", "SYNC") == "OK"
            assert cli("DBSIZE") == "0"
            run_client(directory, "FILL", size, keys, options.seconds)
            lengths = {f"kv_{key}": cli("STRLEN", f"kv_{key}")
                       for key in (1, keys // 2, keys)}
            if cli("DBSIZE") != str(keys) or set(lengths.values()) != {str(size)}:
                raise RuntimeError(f"Invalid dataset size={size} lengths={lengths}")
            save(directory / f"{size}-validated.json", {"keys": keys, "value_bytes": size,
                                                         "lengths": lengths})
            for kind in ("GET", "SET"):
                for connections in levels:
                    stem = f"{size}-{kind.lower()}" + (f"-c{connections}" if options.sweep else "")
                    if not (directory / f"{stem}.result.json").exists():
                        run_client(directory, kind, size, keys, options.seconds,
                                   connections=connections,
                                   client_threads=16 if options.sweep else 8,
                                   sweep=options.sweep)
            if cli("DBSIZE") != str(keys):
                raise RuntimeError(f"Key count changed for size {size}")
        save(directory / ("complete-sweep.json" if options.sweep else "complete.json"),
             {"time": time.time(), "sizes": options.sizes,
              "levels": options.levels if options.sweep else "80",
              "seconds": options.seconds})
    finally:
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
        process.wait(timeout=120)
        save(directory / "server-exit.json", {"code": process.returncode})


def cli_available():
    try:
        return cli("PING") == "PONG"
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


if __name__ == "__main__":
    main()
