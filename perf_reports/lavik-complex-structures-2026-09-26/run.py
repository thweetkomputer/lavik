#!/usr/bin/env python3
"""Reproducible complex-collection comparison on 64 hot keys and two payload sizes."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import signal
import socket
import subprocess
import time
import spdk_host

ROOT = Path(__file__).resolve().parent
HOST, CLIENT, PORT = "172.16.0.4", "172.16.0.5", 6379
PEERS = {"redis": "/mnt/dev/peer-bench/redis/v8.8.0/src/src/redis-server",
         "valkey": "/mnt/dev/peer-bench/valkey/v9.1.0/src/src/valkey-server"}
LAVIK = "/mnt/dev/lavik-tx-backlog/build_bench_spdk/lavik"
TYPES = ("hash", "set", "list", "zset", "stream")
OPS = {"hash": ("HGET", "HSET"), "set": ("SISMEMBER", "SADD_SREM"),
       "list": ("LINDEX", "LSET"), "zset": ("ZSCORE", "ZINCRBY"),
       "stream": ("XRANGE", "XADD_MAXLEN")}
FULL_OP = {"hash": "HGETALL", "set": "SMEMBERS", "list": "LRANGE",
           "zset": "ZRANGE", "stream": "XRANGE_FULL"}
COUNT = {"hash": "HLEN", "set": "SCARD", "list": "LLEN",
         "zset": "ZCARD", "stream": "XLEN"}

def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n")

def resp(*args):
    out = [f"*{len(args)}\r\n".encode()]
    for arg in args:
        item = arg if isinstance(arg, bytes) else str(arg).encode()
        out.extend((f"${len(item)}\r\n".encode(), item, b"\r\n"))
    return b"".join(out)

def read(stream):
    tag = stream.read(1)
    if not tag:
        raise EOFError("server closed connection")
    line = stream.readline().rstrip(b"\r\n")
    if tag == b"-":
        raise RuntimeError("server error: " + line.decode(errors="replace"))
    if tag == b"+":
        return line
    if tag == b":":
        return int(line)
    if tag == b"$":
        n = int(line)
        return None if n < 0 else stream.read(n + 2)[:-2]
    if tag == b"*":
        return [read(stream) for _ in range(int(line))]
    raise RuntimeError(f"unknown RESP tag {tag!r}")

def query(*args):
    with socket.create_connection((HOST, PORT), timeout=120) as sock:
        sock.settimeout(120)
        sock.sendall(resp(*args))
        return read(sock.makefile("rb"))

def value(i, n):
    return f"{i:08d}".encode() + b"x" * (n - 8)

def name(i):
    return f"complex_{i}"

def fill_worker(kind, field_bytes, entries, indices):
    values = [value(i, field_bytes) for i in range(entries)]
    done = 0
    with socket.create_connection((HOST, PORT), timeout=300) as sock:
        sock.settimeout(300)
        stream = sock.makefile("rb")
        for index in indices:
            key = name(index)
            step = 1 if kind == "stream" else 16
            for start in range(0, entries, step):
                end = min(start + step, entries)
                if kind == "hash":
                    args = ("HSET", key, *(a for i in range(start, end)
                                             for a in (f"f{i:08d}", values[i])))
                elif kind == "set":
                    args = ("SADD", key, *values[start:end])
                elif kind == "list":
                    args = ("RPUSH", key, *values[start:end])
                elif kind == "zset":
                    args = ("ZADD", key, *(a for i in range(start, end)
                                            for a in (i, values[i])))
                else:
                    args = ("XADD", key, f"{start + 1}-0", "v", values[start])
                sock.sendall(resp(*args))
                if read(stream) is None:
                    raise RuntimeError("null fill reply")
                done += 1
    return done

def fill(kind, field_bytes, entries, keys):
    begin = time.monotonic()
    with ThreadPoolExecutor(max_workers=8) as pool:
        jobs = [pool.submit(fill_worker, kind, field_bytes, entries,
                            range(i + 1, keys + 1, 8)) for i in range(8)]
        count = sum(job.result() for job in jobs)
    return {"seconds": time.monotonic() - begin, "commands": count}

def validate(kind, field_bytes, entries, keys, after=False):
    if query("DBSIZE") != keys:
        raise RuntimeError(f"{kind}: incorrect key count")
    counts = {name(i): query(COUNT[kind], name(i))
              for i in (1, keys // 2, keys)}
    if after and kind == "set":
        valid = all(entries <= count <= entries + 1 for count in counts.values())
    elif after and kind == "stream":
        valid = all(entries - 100 <= count <= entries + 100 for count in counts.values())
    else:
        valid = set(counts.values()) == {entries}
    if not valid:
        raise RuntimeError(f"{kind}: cardinality {counts}")
    if not after:
        mid = entries // 2
        expected = value(mid, field_bytes)
        if kind == "hash":
            got = query("HGET", name(1), f"f{mid:08d}")
        elif kind == "set":
            got = expected if query("SISMEMBER", name(1), expected) == 1 else None
        elif kind == "list":
            got = query("LINDEX", name(1), mid)
        elif kind == "zset":
            got = expected if query("ZSCORE", name(1), expected) is not None else None
        else:
            rows = query("XRANGE", name(1), f"{mid+1}-0", f"{mid+1}-0")
            got = rows[0][1][1] if rows else None
        if got != expected:
            raise RuntimeError(f"{kind}: incorrect seeded payload")
    return {"keys": keys, "entries_per_key": entries,
            "field_bytes": field_bytes, "sample_cardinalities": counts}

def command_lines(op, field_bytes, entries):
    full = {"HGETALL": "HGETALL __key__", "SMEMBERS": "SMEMBERS __key__",
            "LRANGE": "LRANGE __key__ 0 -1",
            "ZRANGE": "ZRANGE __key__ 0 -1 WITHSCORES",
            "XRANGE_FULL": "XRANGE __key__ - +"}
    if op in full:
        return [full[op]]
    if op == "SADD_SREM":
        member = "t" * field_bytes
        return [f"SADD __key__ {member}", f"SREM __key__ {member}"]
    if op == "XADD_MAXLEN":
        return [f"XADD __key__ MAXLEN ~ {entries} * v __data__"]
    positions = sorted({(entries - 1) * i // 7 for i in range(8)})
    result = []
    for pos in positions:
        member = value(pos, field_bytes).decode()
        field = f"f{pos:08d}"
        args = {"HGET": f"{field}", "HSET": f"{field} __data__",
                "SISMEMBER": member, "LINDEX": str(pos),
                "LSET": f"{pos} __data__", "ZSCORE": member,
                "ZINCRBY": f"1 {member}",
                "XRANGE": f"{pos+1}-0 {pos+1}-0"}
        result.append(f"{op} __key__ {args[op]}")
    return result

def measure(directory, kind, size, field_bytes, entries, keys, op, conns, seconds):
    stem = f"{kind}-{size}-{field_bytes}-{op.lower()}-c{conns}"
    remote = f"/mnt/dev/lavik-complex-20260926-client/{directory.name}/{stem}.json"
    argv = ["taskset", "-c", "0-15", "/usr/local/bin/memtier_benchmark",
            f"--server={HOST}", f"--port={PORT}", "--protocol=redis",
            "--threads=16", f"--clients={conns//16}", "--pipeline=1",
            f"--test-time={seconds}", "--key-minimum=1", f"--key-maximum={keys}",
            "--key-prefix=complex_", f"--data-size={field_bytes}", "--random-data",
            "--hide-histogram", "--distinct-client-seed",
            "--command-miss-tracking=off", "--print-percentiles=50,95,99,99.9",
            f"--json-out-file={remote}"]
    for command in command_lines(op, field_bytes, entries):
        argv += ["--command=" + command, "--command-key-pattern=R"]
    save(directory / f"{stem}.command.json", argv)
    ssh = (["sudo", "-u", "azureuser"] if os.geteuid() == 0 else []) + [
        "ssh", "-o", "BatchMode=yes", CLIENT]
    shell = "mkdir -p " + shlex.quote(str(Path(remote).parent)) + "; ulimit -n 65535; exec " + shlex.join(argv)
    before = query("INFO", "STATS")
    start = time.monotonic()
    with (directory / f"{stem}.txt").open("w") as output:
        subprocess.run([*ssh, shell], stdout=output, stderr=subprocess.STDOUT,
                       check=True, timeout=900)
    elapsed = time.monotonic() - start
    (directory / f"{stem}.info-before.txt").write_bytes(
        before.replace(b"\r\n", b"\n").rstrip(b"\n") + b"\n")
    (directory / f"{stem}.info-after.txt").write_bytes(
        query("INFO", "STATS").replace(b"\r\n", b"\n").rstrip(b"\n") + b"\n")
    with (directory / f"{stem}.json").open("w") as output:
        subprocess.run([*ssh, "cat " + shlex.quote(remote)], stdout=output,
                       check=True, timeout=60)
    stats = json.loads((directory / f"{stem}.json").read_text())["ALL STATS"]
    total = stats["Totals"]
    body = (directory / f"{stem}.txt").read_text().replace("\r", "\n")
    if total["Connection Errors"] or str(stats["Runtime"]["Interrupted"]).lower() != "false":
        raise RuntimeError(f"incomplete run {stem}")
    if re.search(r"error response|connection error|OOM command|Maximum reconnection", body, re.I):
        raise RuntimeError(f"server/client error in {stem}: {body[-2500:]}")
    row = {"product": directory.name, "type": kind, "logical_bytes": size,
           "field_bytes": field_bytes, "entries_per_key": entries, "keys": keys,
           "operation": op, "connections": conns, "qps": total["Ops/sec"],
           "p50_ms": total["Percentile Latencies"]["p50.00"],
           "p99_ms": total["Percentile Latencies"]["p99.00"],
           "p999_ms": total["Percentile Latencies"]["p99.90"],
           "requests": total["Count"], "elapsed_seconds": elapsed,
           "seconds": seconds}
    save(directory / f"{stem}.result.json", row)
    print(time.strftime("%F %T", time.gmtime()), directory.name, stem,
          f"{row['qps']:.0f} QPS p99={row['p99_ms']:.2f} ms", flush=True)

def server(product, directory, binary):
    if product in PEERS:
        return (["taskset", "-c", "0-15", binary, "--bind", HOST,
                 "--protected-mode", "no", "--port", str(PORT), "--daemonize", "no",
                 "--dir", str(directory), "--save", "", "--appendonly", "no",
                 "--maxmemory", "0", "--maxclients", "10000", "--io-threads", "12"], None)
    bdfs = list(spdk_host.SERIAL_PCI.values())
    argv = ["prlimit", "--memlock=unlimited:unlimited", "--nofile=65535:65535",
            "taskset", "-c", "0-15", binary, "--network=kernel", "--storage=spdk",
            f"--bind={HOST}", f"--port={PORT}", "--metrics-port=0", "--threads=12",
            "--pin-workers", "--maxclients=10000", "--busy-poll-us=20",
            "--foreground-budget-us=1000", "--background-budget-us=10",
            "--background-warrant-percent=1", "--tomb-raider-interval-ms=0",
            "--spdk-max-completions-per-poll=16", "--spdk-foreground-pre-poll-us=5",
            "--defrag-paused", "--log-dir=" + str(directory / "logs")]
    argv += ["--data-file=spdk://" + bdf + "/1" for bdf in bdfs]
    env = dict(os.environ, BYCORF_EAL_ARGS=" ".join("-a " + bdf for bdf in bdfs),
               BYCORF_DPDK_MEMORY_MB="8192")
    return argv, env

def main():
    p = argparse.ArgumentParser()
    p.add_argument("product", choices=(*PEERS, "lavik"))
    p.add_argument("--binary", default=LAVIK)
    p.add_argument("--keys", type=int, default=64)
    p.add_argument("--sizes", default="65536,1048576")
    p.add_argument("--fields", default="128,1024")
    p.add_argument("--types", default=",".join(TYPES))
    p.add_argument("--levels", default="80,320,1280,2560,5120")
    p.add_argument("--seconds", type=int, default=8)
    p.add_argument("--mode", choices=("point", "full"), default="point")
    p.add_argument("--backlog-mb", type=int)
    p.add_argument("--tag", default="")
    opt = p.parse_args()
    if opt.product == "lavik":
        assert os.geteuid() == 0 and (ROOT / "spdk-ready.json").exists()
        spdk_host.assert_driver("vfio-pci")
    kinds = tuple(opt.types.split(","))
    sizes = tuple(map(int, opt.sizes.split(",")))
    fields = tuple(map(int, opt.fields.split(",")))
    levels = tuple(map(int, opt.levels.split(",")))
    assert set(kinds) <= set(TYPES) and opt.keys >= 8
    assert all(c > 0 and c % 16 == 0 for c in levels)
    assert all(size >= field and size % field == 0 for size in sizes for field in fields)
    directory = ROOT / "raw" / (opt.product + ("-" + opt.tag if opt.tag else ""))
    directory.mkdir(parents=True, exist_ok=True)
    binary = PEERS.get(opt.product, opt.binary)
    argv, env = server(opt.product, directory, binary)
    save(directory / "server-command.json", argv)
    save(directory / ("provenance-" + "-".join(map(str, levels)) + ".json"), {
        "binary": binary, "sha256": hashlib.sha256(Path(binary).read_bytes()).hexdigest(),
        "source_commit": subprocess.check_output(
            ["git", "-C", "/mnt/dev/lavik-tx-backlog", "rev-parse", "HEAD"],
            text=True).strip() if opt.product == "lavik" else None,
        "fields": fields, "sizes": sizes, "keys": opt.keys, "types": kinds,
        "levels": levels, "seconds": opt.seconds, "backlog_mb": opt.backlog_mb})
    try:
        query("PING")
    except (OSError, EOFError):
        pass
    else:
        raise RuntimeError("benchmark port occupied")
    with (directory / "server.log").open("w") as output:
        proc = subprocess.Popen(argv, stdout=output, stderr=subprocess.STDOUT, env=env)
    try:
        for _ in range(6000 if opt.product == "lavik" else 100):
            if proc.poll() is not None:
                raise RuntimeError("server exited during startup")
            try:
                if query("PING") == b"PONG":
                    break
            except (OSError, EOFError):
                pass
            time.sleep(0.2)
        else:
            raise TimeoutError("server startup")
        if opt.backlog_mb is not None:
            assert opt.product == "lavik" and opt.backlog_mb >= 8
            if query("CONFIG", "SET", "tx-backlog-limit-mb-per-worker",
                     opt.backlog_mb) != b"OK":
                raise RuntimeError("unable to set transaction backlog limit")
        save(directory / "version.json", {"server": query("INFO", "SERVER").decode()})
        for kind in kinds:
            for size in sizes:
                for field_bytes in fields:
                    entries = size // field_bytes
                    combo = f"{kind}-{size}-{field_bytes}"
                    print(time.strftime("%F %T", time.gmtime()), directory.name,
                          combo, "fill", flush=True)
                    if query("FLUSHALL", "SYNC") != b"OK":
                        raise RuntimeError("FLUSHALL failed")
                    save(directory / f"{combo}.fill.json",
                         fill(kind, field_bytes, entries, opt.keys))
                    save(directory / f"{combo}.validated.json",
                         validate(kind, field_bytes, entries, opt.keys))
                    operations = OPS[kind] if opt.mode == "point" else (FULL_OP[kind],)
                    for op in operations:
                        for conns in levels:
                            stem = f"{combo}-{op.lower()}-c{conns}"
                            if not (directory / f"{stem}.result.json").exists():
                                measure(directory, kind, size, field_bytes, entries,
                                        opt.keys, op, conns, opt.seconds)
                    save(directory / f"{combo}.after.json",
                         validate(kind, field_bytes, entries, opt.keys,
                                  after=opt.mode == "point"))
                    save(directory / f"{combo}.complete.json", {"time": time.time()})
        save(directory / "complete.json", {"time": time.time()})
    finally:
        if proc.poll() is None:
            proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=600)
        save(directory / "server-exit.json", {"code": proc.returncode})

if __name__ == "__main__":
    main()
