#!/usr/bin/env python3
"""Reproducible complex-collection comparison across configurable key sizes."""
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
import kvrocks_host
import spdk_host

ROOT = Path(__file__).resolve().parent
HOST, CLIENT, PORT = "172.16.0.4", "172.16.0.5", 6379
PEERS = {"redis": "/mnt/dev/peer-bench/redis/v8.8.0/src/src/redis-server",
         "valkey": "/mnt/dev/peer-bench/valkey/v9.1.0/src/src/valkey-server",
         "kvrocks": "/mnt/dev/peer-bench/tiering-beta1-retest-2026-09-18/sources/kvrocks/build/kvrocks"}
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

def seed_step(kind, field_bytes):
    if kind == "stream":
        return 1
    # Bound each seed command near 16 KiB of payload. Small entries otherwise
    # multiply command count without changing the measured collection shape.
    return min(128, max(16, 16384 // field_bytes))

def fill_worker(kind, field_bytes, entries, indices, pipeline, seed_values,
                seed_fields):
    done = 0
    with socket.create_connection((HOST, PORT), timeout=300) as sock:
        sock.settimeout(300)
        stream = sock.makefile("rb")
        for index in indices:
            key = name(index)
            step = seed_step(kind, field_bytes)
            # Drain each bounded batch before sending another so a 100 MiB
            # key does not turn into unbounded client or server in-flight work.
            pending = []
            for start in range(0, entries, step):
                end = min(start + step, entries)
                values = seed_values[start:end]
                if kind == "hash":
                    args = ("HSET", key, *(a for pair in zip(seed_fields[start:end], values)
                                             for a in pair))
                elif kind == "set":
                    args = ("SADD", key, *values)
                elif kind == "list":
                    args = ("RPUSH", key, *values)
                elif kind == "zset":
                    args = ("ZADD", key, *(a for i in range(start, end)
                                            for a in (i, values[i-start])))
                else:
                    args = ("XADD", key, f"{start + 1}-0", "v", values[0])
                pending.append(resp(*args))
                if len(pending) == pipeline:
                    sock.sendall(b"".join(pending))
                    for _ in pending:
                        if read(stream) is None:
                            raise RuntimeError("null fill reply")
                    done += len(pending)
                    pending.clear()
            if pending:
                sock.sendall(b"".join(pending))
                for _ in pending:
                    if read(stream) is None:
                        raise RuntimeError("null fill reply")
                done += len(pending)
    return done

def fill(kind, field_bytes, entries, keys, pipeline):
    begin = time.monotonic()
    # Every key receives the same deterministic elements. Materialize one
    # immutable copy per fill so a 50,000-key, 128 B run does not format the
    # same 8,192 member values hundreds of millions of times in Python.
    seed_values = tuple(value(i, field_bytes) for i in range(entries))
    seed_fields = (tuple(f"f{i:08d}" for i in range(entries))
                   if kind == "hash" else ())
    with ThreadPoolExecutor(max_workers=8) as pool:
        jobs = [pool.submit(fill_worker, kind, field_bytes, entries,
                            range(i + 1, keys + 1, 8), pipeline, seed_values,
                            seed_fields) for i in range(8)]
        count = sum(job.result() for job in jobs)
    step = seed_step(kind, field_bytes)
    expected = keys * ((entries + step - 1) // step)
    if count != expected:
        raise RuntimeError(f"{kind} fill sent {count} commands, expected {expected}")
    return {"seconds": time.monotonic() - begin, "commands": count,
            "entries_per_command": step}

def validate(kind, field_bytes, entries, keys, product, after=False):
    # Large-key-count runs must reuse a connection. Opening one per key can
    # exhaust the client's ephemeral ports before cardinality is validated.
    with socket.create_connection((HOST, PORT), timeout=120) as sock:
        sock.settimeout(120)
        stream = sock.makefile("rb")

        def check(*args):
            sock.sendall(resp(*args))
            return read(stream)

        if product == "kvrocks":
            # Kvrocks DBSIZE returns periodically refreshed stats, so check
            # the actual keys even when the collection is newly filled.
            observed_keys = set(check("KEYS", "*"))
            expected_keys = {name(i).encode() for i in range(1, keys + 1)}
            if observed_keys != expected_keys:
                raise RuntimeError(f"{kind}: incorrect key count or names")
        elif check("DBSIZE") != keys:
            raise RuntimeError(f"{kind}: incorrect key count")
        counts = {name(i): check(COUNT[kind], name(i))
                  for i in range(1, keys + 1)}
        if not after:
            mid = entries // 2
            expected = value(mid, field_bytes)
            if kind == "hash":
                got = check("HGET", name(1), f"f{mid:08d}")
            elif kind == "set":
                got = expected if check("SISMEMBER", name(1), expected) == 1 else None
            elif kind == "list":
                got = check("LINDEX", name(1), mid)
            elif kind == "zset":
                got = expected if check("ZSCORE", name(1), expected) is not None else None
            else:
                rows = check("XRANGE", name(1), f"{mid+1}-0", f"{mid+1}-0")
                got = rows[0][1][1] if rows else None
            if got != expected:
                raise RuntimeError(f"{kind}: incorrect seeded payload")
    if after and kind == "set":
        valid = all(entries <= count <= entries + 1 for count in counts.values())
    elif after and kind == "stream":
        valid = all(entries - 100 <= count <= entries + 100 for count in counts.values())
    else:
        valid = set(counts.values()) == {entries}
    if not valid:
        raise RuntimeError(f"{kind}: cardinality {counts}")
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

def measure(directory, kind, size, field_bytes, entries, keys, op, conns, seconds,
            client_threads):
    stem = f"{kind}-{size}-{field_bytes}-{op.lower()}-c{conns}"
    remote = f"/mnt/dev/lavik-complex-20260926-client/{directory.name}/{stem}.json"
    argv = ["taskset", "-c", "0-15", "/usr/local/bin/memtier_benchmark",
            f"--server={HOST}", f"--port={PORT}", "--protocol=redis",
            f"--threads={client_threads}", f"--clients={conns//client_threads}", "--pipeline=1",
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
    if product in ("redis", "valkey"):
        return (["taskset", "-c", "0-15", binary, "--bind", HOST,
                 "--protected-mode", "no", "--port", str(PORT), "--daemonize", "no",
                 "--dir", str(directory), "--save", "", "--appendonly", "no",
                 "--maxmemory", "0", "--maxclients", "10000", "--io-threads", "12"], None)
    if product == "kvrocks":
        config = (ROOT / "kvrocks-perf.conf").read_text()
        # FLUSHALL leaves old LSM files and compaction debt behind. Give each
        # measured condition a fresh DB on the same RAID0 so earlier fills
        # cannot change its write or read path. The RAID is discarded after
        # the suite, while the generated config records the exact location.
        source_dir = f"dir {kvrocks_host.MOUNT}/data\n"
        if config.count(source_dir) != 1:
            raise RuntimeError("Kvrocks config has no unique RAID data directory")
        data_dir = kvrocks_host.MOUNT / "data" / f"{directory.name}-{time.time_ns()}"
        data_dir.mkdir()
        config = config.replace(source_dir, f"dir {data_dir}\n", 1)
        target = directory / "kvrocks.conf"
        target.write_text(config)
        return (["prlimit", "--nofile=65535:65535", "taskset", "-c", "0-15",
                 binary, "-c", str(target)], None)
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
    p.add_argument("--full-levels", default="1,4,16")
    p.add_argument("--seconds", type=int, default=8)
    p.add_argument("--mode", choices=("point", "full", "both"), default="point")
    p.add_argument("--client-threads", type=int, default=16)
    p.add_argument("--seed-pipeline", type=int, default=1)
    p.add_argument("--continue-on-error", action="store_true")
    p.add_argument("--backlog-mb", type=int)
    p.add_argument("--tag", default="")
    p.add_argument("--source-repo", default=str(ROOT.parents[1]),
                   help="Lavik source checkout used to build --binary")
    p.add_argument("--source-commit",
                   help="Exact Lavik source commit used to build --binary")
    opt = p.parse_args()
    if opt.product == "lavik":
        assert os.geteuid() == 0 and (ROOT / "spdk-ready.json").exists()
        spdk_host.assert_driver("vfio-pci")
    if opt.product == "kvrocks":
        assert (ROOT / "kvrocks-raid-ready.json").exists()
        assert os.path.ismount(kvrocks_host.MOUNT)
    kinds = tuple(opt.types.split(","))
    sizes = tuple(map(int, opt.sizes.split(",")))
    fields = tuple(map(int, opt.fields.split(",")))
    levels = tuple(map(int, opt.levels.split(",")))
    full_levels = tuple(map(int, opt.full_levels.split(",")))
    assert set(kinds) <= set(TYPES) and opt.keys >= 8
    assert 1 <= opt.client_threads <= 16 and opt.seed_pipeline >= 1
    assert all(c > 0 and c % min(c, opt.client_threads) == 0 for c in levels)
    assert all(c > 0 for c in full_levels)
    assert all(size >= field and size % field == 0 for size in sizes for field in fields)
    directory = ROOT / "raw" / (opt.product + ("-" + opt.tag if opt.tag else ""))
    directory.mkdir(parents=True, exist_ok=True)
    binary = PEERS.get(opt.product, opt.binary)
    argv, env = server(opt.product, directory, binary)
    save(directory / "server-command.json", argv)
    save(directory / ("provenance-" + opt.mode + "-" + "-".join(kinds) + "-" +
                      "-".join(map(str, levels)) + ".json"), {
        "binary": binary, "sha256": hashlib.sha256(Path(binary).read_bytes()).hexdigest(),
        "source_commit": opt.source_commit or subprocess.check_output(
            ["git", "-C", (opt.source_repo if opt.product == "lavik"
                          else "/mnt/dev/peer-bench/tiering-beta1-retest-2026-09-18/sources/kvrocks"),
             "rev-parse", "HEAD"], text=True).strip()
        if opt.product in ("lavik", "kvrocks") else None,
        "fields": fields, "sizes": sizes, "keys": opt.keys, "types": kinds,
        "levels": levels, "full_levels": full_levels,
        "seconds": opt.seconds, "backlog_mb": opt.backlog_mb,
        "client_threads": opt.client_threads, "seed_pipeline": opt.seed_pipeline,
        "mode": opt.mode, "continue_on_error": opt.continue_on_error})
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
        if opt.product == "kvrocks":
            # A running process can use a different config file than the saved
            # launch command. Check the effective settings before any fill.
            settings = {name: query("CONFIG", "GET", name) for name in
                        ("rocksdb.compression", "rocksdb.wal_compression",
                         "rocksdb.write_options.disable_wal")}
            save(directory / "effective-storage-config.json", {
                name: [item.decode() for item in response]
                for name, response in settings.items()})
            expected_settings = {"rocksdb.compression": b"no",
                                 "rocksdb.wal_compression": b"no",
                                 "rocksdb.write_options.disable_wal": b"yes"}
            if any(response[-1].lower() != expected_settings[name]
                   for name, response in settings.items()):
                raise RuntimeError(f"unexpected Kvrocks compression/WAL settings: {settings}")
        save(directory / "version.json", {"server": query("INFO", "SERVER").decode()})
        failures = 0
        for kind in kinds:
            for size in sizes:
                for field_bytes in fields:
                    entries = size // field_bytes
                    combo = f"{kind}-{size}-{field_bytes}"
                    print(time.strftime("%F %T", time.gmtime()), directory.name,
                          combo, "fill", flush=True)
                    flush = ("FLUSHALL",) if opt.product == "kvrocks" else ("FLUSHALL", "SYNC")
                    if query(*flush) != b"OK":
                        raise RuntimeError("FLUSHALL failed")
                    save(directory / f"{combo}.fill.json",
                         fill(kind, field_bytes, entries, opt.keys,
                              opt.seed_pipeline))
                    save(directory / f"{combo}.validated.json",
                         validate(kind, field_bytes, entries, opt.keys, opt.product))
                    # Capture the real memory cost of each seeded collection;
                    # logical payload alone misses field and allocator overhead.
                    (directory / f"{combo}.memory-after-fill.txt").write_text(
                        query("INFO", "MEMORY").decode())
                    operations = ((FULL_OP[kind], *OPS[kind]) if opt.mode == "both"
                                  else OPS[kind] if opt.mode == "point"
                                  else (FULL_OP[kind],))
                    for op in operations:
                        op_levels = full_levels if op == FULL_OP[kind] and opt.mode == "both" else levels
                        for conns in op_levels:
                            stem = f"{combo}-{op.lower()}-c{conns}"
                            result = directory / f"{stem}.result.json"
                            failure = directory / f"{stem}.error.json"
                            if result.exists() or failure.exists():
                                continue
                            try:
                                measure(directory, kind, size, field_bytes, entries,
                                        opt.keys, op, conns, opt.seconds,
                                        min(opt.client_threads, conns))
                            except Exception as exc:
                                if not opt.continue_on_error or proc.poll() is not None:
                                    raise
                                save(failure, {"product": opt.product, "type": kind,
                                               "logical_bytes": size,
                                               "field_bytes": field_bytes,
                                               "operation": op, "connections": conns,
                                               "error": str(exc), "time": time.time()})
                                failures += 1
                                print(time.strftime("%F %T", time.gmtime()),
                                      directory.name, stem, "FAILED", str(exc)[:240],
                                      flush=True)
                    save(directory / f"{combo}.after.json",
                         validate(kind, field_bytes, entries, opt.keys, opt.product,
                                  after=opt.mode != "full"))
                    save(directory / f"{combo}.complete.json", {"time": time.time()})
        save(directory / "complete.json", {"time": time.time(),
                                           "failures_in_this_run": failures,
                                           "failures_total": len(list(directory.glob("*.error.json")))})
    finally:
        if proc.poll() is None:
            proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=600)
        save(directory / "server-exit.json", {"code": proc.returncode})

if __name__ == "__main__":
    main()
