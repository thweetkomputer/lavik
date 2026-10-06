"""Execute in an already private mount namespace with scratch on the data disk."""
import os
from pathlib import Path
import pwd
import subprocess
import sys

scratch, uid, gid, *command = sys.argv[1:]
scratch = Path(scratch).resolve()
uid, gid = int(uid), int(gid)
assert os.geteuid() == 0 and scratch.is_dir() and command
assert scratch.is_relative_to('/mnt/dev/lavik-main-920f879b-20261006')
# The caller must unshare first: binding here never changes the host /tmp.
assert os.readlink('/proc/self/ns/mnt') != os.readlink('/proc/1/ns/mnt')
subprocess.run(['mount', '--bind', str(scratch), '/tmp'], check=True)
assert os.stat('/tmp').st_dev == os.stat(scratch).st_dev
os.initgroups(pwd.getpwuid(uid).pw_name, gid)
os.setgid(gid)
os.setuid(uid)
os.execvpe(command[0], command, os.environ)
