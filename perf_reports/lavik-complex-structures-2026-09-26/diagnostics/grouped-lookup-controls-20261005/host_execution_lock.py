"""Serialize benchmark-host work; never unlink the lock file while tasks exist."""
from pathlib import Path
import fcntl
import os
import time


def acquire_host(task):
    """Return a held descriptor; retain it for all builds/tests/seed/perf work."""
    path = Path(__file__).parent / 'benchmark-host.execution.lock'
    handle = path.open('a')
    print('WAIT_FOR_HOST_LOCK', task, os.getpid(), time.time(), flush=True)
    fcntl.flock(handle, fcntl.LOCK_EX)
    print('HOST_LOCK_ACQUIRED', task, os.getpid(), time.time(), flush=True)
    return handle
