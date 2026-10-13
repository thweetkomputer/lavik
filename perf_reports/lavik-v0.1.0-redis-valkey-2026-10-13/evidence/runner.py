#!/usr/bin/env python3
"""October 13 fresh v0.1.0 acquisition, adapted from the archived September runner.

Run one stage at a time on the dedicated benchmark server. The raw stages
require --allow-clear-benchmark-disks and erase only the six checked NVMe disks.
All logs and datasets created here have a new, dedicated output directory.
"""
import argparse, contextlib, hashlib, json, os, pathlib, re, resource, shlex
import signal, socket, subprocess as sp, sys, time, urllib.request
R = pathlib.Path(__file__).resolve().parent
S = '10.84.1.4'; CLIENT = 'azureuser@10.84.0.5'; PORT = 6379
REMOTE = '/opt/benchmark/release010/memory'
CLI = '/usr/bin/redis-cli'
LAVIK = pathlib.Path('/mnt/dev/benchmark/release010/downloads/lavik-v0.1.0-linux-x86_64/lavik')
DEVICES = [f'/dev/nvme{i}n1' for i in range(1,7)]
SERIALS = {i: f'4d4fd73b0687ec77000{i}' for i in range(1,7)}
CONNECTIONS = [80,160,320,640,1280]
INFO_SECTIONS = None
DBSIZE_TIMEOUT = 120
resource.setrlimit(resource.RLIMIT_NOFILE,(65535,65535))

def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj,indent=2)+'\n')
def event(message):
    print(time.strftime('%Y-%m-%d %H:%M:%S UTC',time.gmtime()),message,flush=True)
    write(R/'status.json',{'time':time.time(),'message':message,'pid':os.getpid()})
def run(args, **kw):
    return sp.run([str(x) for x in args],check=True,**kw)
def out(args, **kw):
    return sp.check_output([str(x) for x in args],text=True,**kw).strip()
def ssh(command, **kw):
    return run(['sudo','-u','azureuser','ssh','-i','/mnt/dev/benchmark/release010/client-control','-o','BatchMode=yes',CLIENT,command],**kw)
def cli(*args):
    if args==('INFO','ALL') and INFO_SECTIONS:
        return '\n'.join(cli('INFO',section) for section in INFO_SECTIONS)
    timeout=DBSIZE_TIMEOUT if args and args[0]=='DBSIZE' else 120
    return out([CLI,'-h',S,'-p',PORT,'--raw',*args],timeout=timeout)
def snapshot(path, pid=None):
    d={'time':time.time(),'clock_ticks':os.sysconf('SC_CLK_TCK')}
    for f in ['stat','meminfo','diskstats','interrupts','net/dev','net/softnet_stat','softirqs']:
        d[f]=pathlib.Path('/proc/'+f).read_text()
    d['irq_affinity']={str(p):p.read_text().strip() for p in pathlib.Path('/proc/irq').glob('*/smp_affinity_list')}
    if pid:
        for f in ['stat','status','io']:
            with contextlib.suppress(FileNotFoundError): d['process_'+f]=pathlib.Path(f'/proc/{pid}/{f}').read_text()
        d['threads']={t.name:sorted(os.sched_getaffinity(int(t.name))) for t in pathlib.Path(f'/proc/{pid}/task').iterdir()}
        d['info']=cli('INFO','ALL')
        if pathlib.Path(f'/proc/{pid}/exe').resolve() == LAVIK:
            d['defrag_config']=verify_defrag()
            d['defrag_status']=cli('DEFRAG','STATUS')
    write(path,d)
def validate(keys):
    event('validating dataset: '+str(keys)+' keys, 1024-byte values')
    d={'dbsize':cli('DBSIZE'),'lengths':{str(k):cli('STRLEN',str(k)) for k in [1,2,keys//2,keys-1,keys]}}
    if d['dbsize'] != str(keys) or set(d['lengths'].values()) != {'1024'}:
        raise RuntimeError('Dataset validation failed: '+str(d))
    return d

def memtier(directory, name, keys, kind, connections=640, seconds=30, pid=None, threads=16):
    if (R/'STOP').exists():raise RuntimeError('Stop requested')
    directory.mkdir(parents=True,exist_ok=True)
    relative=directory.relative_to(R).as_posix()+'/'+name
    remote_path=REMOTE+'/'+relative
    args=['taskset','-c','0-15','memtier_benchmark','--server='+S,'--port='+str(PORT),'--protocol=redis',
          '--threads='+str(threads),'--clients='+str(connections//threads),'--pipeline=1', '--key-minimum=1','--key-maximum='+str(keys),
          '--key-prefix=','--data-size=1024','--hide-histogram','--print-percentiles=50,99,99.9,99.99','--show-config',
          '--json-out-file='+remote_path+'.json']
    if kind=='fill':
        assert keys%connections==0
        args+=['--requests='+str(keys//connections),'--ratio=1:0','--key-pattern=P:P']
    else:
        args+=['--test-time='+str(seconds),'--command='+('GET __key__' if kind=='GET' else 'SET __key__ __data__'),'--command-key-pattern=R']
        if kind=='GET': args+=['--command-is-read']
    # Independent streams are essential for a disk-backed working set: cloned
    # default seeds make clients revisit the same small sequence and inflate
    # cache locality. Keep the archived 10M-key methodology unchanged.
    if keys==10**9 and kind!='fill':args+=['--distinct-client-seed']
    write(directory/(name+'.command.json'),args)
    if pid:snapshot(directory/(name+'.before.json'),pid)
    event(relative)
    t=time.time()
    command='mkdir -p '+shlex.quote(str(pathlib.PurePosixPath(remote_path).parent))+'; ulimit -n 65535; exec '+shlex.join(args)
    with (directory/(name+'.txt')).open('w') as f:
        ssh(command,stdout=f,stderr=sp.STDOUT,timeout=10800)
    with (directory/(name+'.json')).open('w') as f:
        ssh('cat '+shlex.quote(remote_path+'.json'),stdout=f)
    write(directory/(name+'.timing.json'),{'start':t,'end':time.time()})
    stats=json.loads((directory/(name+'.json')).read_text())['ALL STATS']
    assert stats['Totals']['Connection Errors']==0, 'Connection errors'
    assert str(stats['Runtime']['Interrupted']).lower()=='false', 'Interrupted client'
    if kind=='fill':assert stats['Totals']['Count']==keys, 'Incomplete fill'
    body=(directory/(name+'.txt')).read_text().replace('\r','\n')
    totals=[line.split() for line in body.splitlines() if line.startswith('Totals')]
    if len(totals)!=1 or len(totals[0])!=10:raise RuntimeError('Bad totals: '+relative)
    if re.search(r'error response|connection error|error:|OOM command',body,re.I):raise RuntimeError('Client errors: '+relative)
    if kind=='GET':
        gets=[line.split() for line in body.splitlines() if line.startswith('Gets')]
        if len(gets)!=1 or float(gets[0][3])!=0 or abs(float(gets[0][1])-float(gets[0][2]))>.01:raise RuntimeError('GET misses: '+relative)
    if pid:snapshot(directory/(name+'.after.json'),pid)
    row=totals[0]
    result={'name':relative,'kind':kind,'keys':keys,'connections':connections,'qps':float(row[1]),
            'avg_ms':float(row[4]),'p50_ms':float(row[5]),'p99_ms':float(row[6]),'p999_ms':float(row[7]),'p9999_ms':float(row[8])}
    write(directory/(name+'.result.json'),result)
    event(relative+' done: '+str(round(result['qps']))+' QPS, p999='+str(result['p999_ms'])+' ms')
    return result

@contextlib.contextmanager
def server(args, directory, env=None, cwd=None):
    directory.mkdir(parents=True,exist_ok=True)
    try:
        with socket.create_connection((S,PORT),timeout=1):raise RuntimeError('Benchmark port already occupied')
    except ConnectionRefusedError:pass
    args=['taskset','-c','0-15',*[str(x) for x in args]]
    write(directory/'server-command.json',args)
    event('starting '+str(args[3]))
    with (directory/'server.log').open('a') as f:
        p=sp.Popen(args,stdout=f,stderr=sp.STDOUT,env=env,cwd=cwd)
    write(R/'active-server.json',{'pid':p.pid,'command':args,'directory':str(directory)})
    try:
        deadline=time.monotonic()+600
        while time.monotonic()<deadline:
            if p.poll() is not None:raise RuntimeError('Server exited: '+str(directory))
            try:
                if cli('PING')=='PONG':break
            except sp.SubprocessError:pass
            time.sleep(.5)
        else:raise TimeoutError('Server startup')
        yield p.pid
    finally:
        requested_stop = p.poll() is None
        if requested_stop:
            p.send_signal(signal.SIGTERM)
            try:p.wait(timeout=300)
            except sp.TimeoutExpired:
                raise RuntimeError('Server did not shut down cleanly; left running for inspection, no SIGKILL')
        (directory/'exit-code.txt').write_text(str(p.returncode)+'\n')
        (R/'active-server.json').unlink(missing_ok=True)
        expected_garnet_stop = requested_stop and pathlib.Path(args[3]).name == 'GarnetServer' and p.returncode == -signal.SIGTERM
        if p.returncode != 0 and not expected_garnet_stop:raise RuntimeError('Server exit code '+str(p.returncode))

def clear_devices():
    if not OPTIONS.allow_clear_benchmark_disks:raise RuntimeError('Explicit --allow-clear-benchmark-disks required')
    for i,device in enumerate(DEVICES,1):
        serial=pathlib.Path(f'/sys/block/nvme{i}n1/device/serial').read_text().strip()
        if serial!=SERIALS[i]:raise RuntimeError('Unexpected disk serial: '+device)
        if list(pathlib.Path(f'/sys/class/block/nvme{i}n1/holders').iterdir()):raise RuntimeError('Disk has holders: '+device)
        if sp.run(['findmnt','-rn','-S',device],stdout=sp.DEVNULL).returncode==0:raise RuntimeError('Mounted disk: '+device)
        # io_uring teardown can briefly retain device references after a clean
        # process exit. Wait for release rather than weakening the safety gate.
        deadline=time.monotonic()+30
        while sp.run(['fuser',device],stdout=sp.DEVNULL,stderr=sp.DEVNULL).returncode==0:
            if time.monotonic()>=deadline:raise RuntimeError('Disk in use: '+device)
            time.sleep(.5)
    event('clearing six approved benchmark NVMe devices')
    for device in DEVICES:run(['blkdiscard',device])

def verify_defrag():
    value=cli('CONFIG','GET','defrag-paused')
    assert value.splitlines()==['defrag-paused','no'],value
    return {'defrag-paused':value}

def sweep(directory,keys,seconds,pid,storage=False):
    for kind in ['GET','SET']:
        for connections in CONNECTIONS+([2560] if storage else []):
            verify_defrag()
            memtier(directory,f'{kind.lower()}-c{connections}',keys,kind,connections,seconds,pid)
    write(directory/'validation-after.json',validate(keys))

def lavik(keys):
    directory=R/('storage' if keys==10**9 else 'memory')/'lavik'
    if (directory/'validation-after.json').exists():raise RuntimeError('Completed output exists')
    clear_devices()
    args=[LAVIK,'--network=kernel','--storage=uring','--bind='+S,'--port='+str(PORT),'--metrics-port=0',
          '--threads=16','--pin-workers','--maxclients=10000','--busy-poll-us=20','--foreground-budget-us=1000',
          '--background-budget-us=10','--background-warrant-percent=1','--tomb-raider-interval-ms=0',
          '--log-dir='+str(directory/'logs')]+['--data-file='+d for d in DEVICES]
    if keys==10**9:args+=['--shutdown-checkpoint']
    with server(args,directory) as pid:
        assert cli('DBSIZE')=='0'
        write(directory/'runtime-config.json',verify_defrag())
        memtier(directory,'fill',keys,'fill',pid=pid)
        write(directory/'validation-before.json',validate(keys))
        if keys!=10**9:memtier(directory,'warmup',keys,'GET',seconds=10,pid=pid)
        sweep(directory,keys,60 if keys==10**9 else 30,pid,keys==10**9)
    event('COMPLETE lavik '+str(keys))

def memory(product):
    version='8.8.0' if product=='redis' else '9.1.0'
    binary=f'/mnt/dev/benchmark/release010/downloads/{product}/src/{product}-server'
    directory=R/'memory'/product; data=R/'data'/product; data.mkdir(parents=True,exist_ok=True)
    keys=10**7
    def args(threads):
        return [binary,'--bind',S,'--protected-mode','no','--port',PORT,'--daemonize','no','--dir',data,'--dbfilename','dump.rdb',
                '--save','','--appendonly','no','--maxmemory','0','--maxclients','10000','--io-threads',threads]
    baseline=directory/'baseline.json'
    if (data/'dump.rdb').exists():
        assert baseline.exists(), 'Unverified existing RDB'
        assert json.loads(baseline.read_text())['sha256']==hashlib.sha256((data/'dump.rdb').read_bytes()).hexdigest(), 'Baseline changed'
    else:
        with server(args(16),directory/'load') as pid:
            memtier(directory,'fill',keys,'fill',pid=pid)
            write(directory/'validation-fill.json',validate(keys))
            assert cli('SAVE')=='OK'
        write(baseline,{'sha256':hashlib.sha256((data/'dump.rdb').read_bytes()).hexdigest()})
    for threads in [1,2,4,8,16]:
        dest=directory/f'io{threads}'
        if (dest/'validation-after.json').exists():continue
        with server(args(threads),dest) as pid:
            write(dest/'validation-before.json',validate(keys))
            assert cli('CONFIG','GET','io-threads').splitlines()==['io-threads',str(threads)]
            warm='warmup' if not (dest/'warmup.result.json').exists() else 'warmup-resume-'+str(int(time.time()))
            memtier(dest,warm,keys,'GET',seconds=10,pid=pid)
            for kind in ['GET','SET']:
                for c in CONNECTIONS:
                    name=f'{kind.lower()}-c{c}'
                    if not (dest/(name+'.result.json')).exists():memtier(dest,name,keys,kind,c,30,pid)
            write(dest/'validation-after.json',validate(keys))
    event('COMPLETE '+product)

MOUNT=pathlib.Path('/mnt/lavik-nightly-retest-data')
MD='/dev/md/lavik-nightly-retest'

def raid():
    clear_devices()
    if MOUNT.exists() and any(MOUNT.iterdir()):raise RuntimeError('Mount directory not empty')
    if pathlib.Path(MD).exists():raise RuntimeError('RAID name already exists')
    MOUNT.mkdir(exist_ok=True)
    with (R/'host/raid-setup.txt').open('w') as f:
        run(['mdadm','--create',MD,'--run','--level=0','--raid-devices=6','--chunk=512K','--metadata=1.2',*DEVICES],stdout=f,stderr=sp.STDOUT)
        run(['mkfs.xfs','-f','-d','su=512k,sw=6',MD],stdout=f,stderr=sp.STDOUT)
        run(['mount','-o','noatime',MD,MOUNT],stdout=f,stderr=sp.STDOUT)
        run(['mdadm','--detail',MD],stdout=f,stderr=sp.STDOUT)
        run(['findmnt',str(MOUNT)],stdout=f,stderr=sp.STDOUT)
    event('COMPLETE RAID0/XFS setup')

def validate_garnet(directory, phase):
    """Freeze compaction for an exact scan, then restore the measured policy."""
    def positions():
        values = dict(line.split(':', 1) for line in cli('INFO', 'STORE').splitlines() if ':' in line)
        return {k: values[k] for k in ['Log.BeginAddress','Log.HeadAddress','Log.TailAddress','Log.FlushedUntilAddress']}
    assert cli('CONFIG','GET','compaction-type').splitlines() == ['compaction-type','Lookup']
    assert cli('CONFIG','SET','compaction-type','None') == 'OK'
    try:
        event('Garnet '+phase+' validation: wait for stable log boundaries')
        previous = None; stable_since = time.monotonic(); deadline = stable_since + 1800; samples = []
        while True:
            current = positions(); samples.append({'time':time.time(),'positions':current})
            if current != previous: previous = current; stable_since = time.monotonic()
            if time.monotonic()-stable_since >= 30: break
            if time.monotonic()>deadline: raise TimeoutError('Garnet compaction did not quiesce')
            time.sleep(2)
        write(directory/('quiescence-'+phase+'.json'),samples)
        result = validate(10**9)
        after = positions(); assert after == current, (current,after)
        write(directory/('scan-positions-'+phase+'.json'),{'before':current,'after':after})
        write(directory/('validation-'+phase+'.json'),result)
    finally:
        assert cli('CONFIG','SET','compaction-type','Lookup') == 'OK'
        assert cli('CONFIG','GET','compaction-type').splitlines() == ['compaction-type','Lookup']
        write(directory/('restored-compaction-'+phase+'.json'),{'time':time.time(),'compaction-type':'Lookup'})

def tiered(product):
    global INFO_SECTIONS,DBSIZE_TIMEOUT
    # Garnet's DBSIZE/INFO KEYSPACE scan the store. Its v2.1.5 INFO ALL already
    # excludes KEYSPACE; explicitly retain only the lightweight sections here.
    # Exact counts remain outside the sweep and can take much longer than GET.
    if product=='garnet':
        INFO_SECTIONS=['SERVER','MEMORY','STATS']
        DBSIZE_TIMEOUT=3600
    if out(['findmnt','-n','-o','FSTYPE','--target',MOUNT])!='xfs':raise RuntimeError('Expected XFS benchmark volume')
    directory=R/'storage'/product; data=MOUNT/product
    data.mkdir(exist_ok=False)
    env=None;cwd=None
    if product=='dragonfly':
        binary='/mnt/dev/peer-bench/dragonfly/v1.40.2/dragonfly-x86_64'
        args=[binary,'--logtostderr','--bind='+S,'--port='+str(PORT),'--proactor_threads=16','--maxmemory=96GB',
              '--dir='+str(data),'--dbfilename=','--tiered_prefix='+str(data/'tier'),'--tiering_disk_storage_initial_size=64GB',
              '--tiered_max_file_size=2TB','--backing_file_direct=false','--tiered_offload_threshold=1.0',
              '--tiered_experimental_cooling=false','--tiered_max_pending_bytes=16MB']
    else:
        cwd='/mnt/dev/peer-bench/garnet/v2.1.5/net10.0'
        env=dict(os.environ,DOTNET_ROOT='/mnt/dev/peer-bench/garnet/v2.1.5/dotnet',DOTNET_CLI_TELEMETRY_OPTOUT='1',LD_LIBRARY_PATH=cwd)
        args=[cwd+'/GarnetServer','--bind',S,'--port',PORT,'--protected-mode','false','--memory','64g',
              '--page','4m','--segment','1g','--index','16g','--index-max-size','16g','--storage-tier','--logdir',data/'log',
              '--checkpointdir',data/'checkpoints','--readcache','--readcache-memory','32g','--readcache-page','4m',
              '--no-obj','--no-pubsub','--device-type','Native','--device-io-backend','Libaio','--device-completion-threads','4',
              '--device-throttle-limit','512','--initial-io-record-size','8k','--compaction-freq','300','--compaction-type','Lookup',
              '--compaction-force-delete','--network-connection-limit','10000','--minthreads','16','--miniothreads','16','--logger-level','Warning']
        write(directory/'server-env.json',{k:env[k] for k in ['DOTNET_ROOT','DOTNET_CLI_TELEMETRY_OPTOUT','LD_LIBRARY_PATH']})
    with server(args,directory,env,cwd) as pid:
        assert cli('DBSIZE')=='0'
        memtier(directory,'fill',10**9,'fill',pid=pid)
        if product == 'garnet': validate_garnet(directory,'before')
        else: write(directory/'validation-before.json',validate(10**9))
        memtier(directory,'warmup',10**9,'GET',connections=80,seconds=180,pid=pid,threads=8)
        for kind in ['GET','SET']:
            for connections in CONNECTIONS+[2560]:
                if product == 'garnet': assert cli('CONFIG','GET','compaction-type').splitlines() == ['compaction-type','Lookup']
                memtier(directory,f'{kind.lower()}-c{connections}',10**9,kind,connections,60,pid)
        if product == 'garnet': validate_garnet(directory,'after')
        else: write(directory/'validation-after.json',validate(10**9))
    event('COMPLETE '+product)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['lavik-10g','lavik-1t','redis','valkey','raid','dragonfly','garnet'])
    ap.add_argument('--allow-clear-benchmark-disks',action='store_true');OPTIONS=ap.parse_args()
    try:
        if OPTIONS.stage.startswith('lavik'):
            lavik(10**7 if OPTIONS.stage=='lavik-10g' else 10**9)
        elif OPTIONS.stage=='raid':raid()
        elif OPTIONS.stage in ['dragonfly','garnet']:tiered(OPTIONS.stage)
        else:memory(OPTIONS.stage)
    except BaseException as e:
        event('FAILED '+OPTIONS.stage+': '+repr(e));raise
