"""Resolve dependency provenance from the configured build, never an empty checkout."""
from datetime import datetime, timezone
from pathlib import Path
import subprocess


def native_dependency_provenance(build_directory):
    """Capture the actual CMake-selected bycorf checkout and its current status."""
    cache = {}
    for line in (Path(build_directory) / 'CMakeCache.txt').read_text().splitlines():
        if not line or line.startswith(('#', '//')) or '=' not in line:
            continue
        key, value = line.split('=', 1)
        cache[key.split(':', 1)[0]] = value
    source = Path(cache['bycorf_SOURCE_DIR']).resolve()
    override = cache.get('LAVIK_BYCORF_SOURCE_DIR')
    if override:
        assert Path(override).resolve() == source, 'CMake dependency source mismatch'
    def git(*args):
        return subprocess.check_output(['git', '-C', str(source), *args], text=True).rstrip('\n')
    # git walks upward from an empty submodule directory and would otherwise
    # silently label the parent Lavik commit as the dependency revision.
    assert Path(git('rev-parse', '--show-toplevel')).resolve() == source
    return {
        'bycorf_commit': git('rev-parse', '--verify', 'HEAD'),
        'bycorf_source_repo': str(source),
        'bycorf_source_status': git('status', '--short', '--untracked-files=no'),
        'bycorf_submodule_revisions': git('submodule', 'status', '--recursive').splitlines(),
        'bycorf_provenance_observed_at': datetime.now(timezone.utc).isoformat(),
    }
