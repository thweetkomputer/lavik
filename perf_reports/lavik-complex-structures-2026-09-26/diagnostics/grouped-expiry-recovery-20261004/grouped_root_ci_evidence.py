"""Retain the frozen parent's diagnosed external Redis startup failure."""

import hashlib
from pathlib import Path


def validate_ci(label, proof, expected_head):
    """Check exact CI coverage without relabeling a failed parent run as green."""
    assert proof["headSha"] == expected_head and proof["status"] == "completed"
    assert len(proof["jobs"]) == 17
    if label == "candidate":
        assert proof["conclusion"] == "success"
        assert all(job["conclusion"] == "success" for job in proof["jobs"])
        return
    assert label == "parent"
    assert expected_head == "19496654cc43b21df11fb59be60e174dc4c89dbc"
    assert proof["url"].endswith("/actions/runs/37237724710")
    assert proof["conclusion"] == "failure"
    failed = {job["databaseId"]: (job["name"], job["conclusion"])
              for job in proof["jobs"] if job["conclusion"] != "success"}
    assert failed == {
        111541360623: ("Test shard (arm64, 4)", "failure"),
        111547426721: ("Tests (amd64)", "failure"),
        111547426765: ("Tests (arm64)", "failure"),
    }
    # This exception is tied to one reviewed failure, not arbitrary red CI.
    log = Path(__file__).with_name("grouped-root-parent-arm64-shard4-failed.log")
    raw = log.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == (
        "6a9fc94d439772984caf4b706c12f43b0c61b21c828783db0396c73ed16b50e5"
    )
    text = raw.decode()
    failures = [line for line in text.splitlines() if "***Failed" in line]
    assert len(failures) == 1 and "lavik_redis_sync_reader_cluster-cluster" in failures[0]
    assert "bind: Address already in use" in text
    assert "Failed listening on port 54785 (cluster), aborting." in text
    assert "99% tests passed, 1 tests failed out of 290" in text
    proof["reviewed_limitation"] = {
        "case": "lavik_redis_sync_reader_cluster-cluster",
        "reason": "External Redis cluster-bus port 54785 was occupied; source Redis aborted during startup.",
        "failed_job": 111541360623,
        "log_sha256": hashlib.sha256(raw).hexdigest(),
        "scope": "Parent CI remains failed. Its import scenario is not validated; all other jobs/tests passed. Native grouped validation is still required for both binaries.",
    }
