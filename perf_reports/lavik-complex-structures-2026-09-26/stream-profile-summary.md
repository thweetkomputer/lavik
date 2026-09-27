# 100 MiB Stream CPU sampling

The pre-selected-page-pin Lavik binary was sampled for 20 seconds during the
100 MiB / 1 KiB `XRANGE` sweep. The sample overlapped the 80- and 320-connection
points. It is a CPU sample, not a request latency decomposition.

```sh
sudo perf record -e cpu-clock -F 99 -g -p <lavik-pid> -o /tmp/lavik-stream-read-fast.perf.data -- sleep 20
sudo perf report -i /tmp/lavik-stream-read-fast.perf.data --stdio --no-children --sort symbol
```

The binary under sample contained the resident boundary index and local
directory-update optimization (source commit `6145eec7`), but still prepared
pins for the complete grouped graph on each range reply. Top self percentages:

| Symbol | CPU samples |
|---|---:|
| SipHash round | 28.45% |
| Record-index bucket-chain lookup | 14.16% |
| `ComputeDigest` | 12.49% |
| Record-index rehash-table lookup | 11.61% |
| `VisitPhysical` grouped graph traversal | 11.52% |
| Pin-list sort | 5.07% |
| `PrepareSnapshotBlockPins` body | 1.54% |

Some hashing samples may come from physical-page index lookup and other server
work. The `VisitPhysical` and pin-list symbols directly identify the complete
graph preparation path. The selected-page-pin benchmark, which changed that
path, is the stronger evidence for its throughput impact.
