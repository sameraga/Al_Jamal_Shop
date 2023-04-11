from datetime import datetime
from pathlib import Path
from subprocess import run


def run_backup(source_dir: str, dest_dir: str) -> bool:
    tar_file = Path(dest_dir) / f"{datetime.now():%Y-%m-%d}.tar.gz"
    source = Path(source_dir)
    return (
        run(
            [
                "tar",
                "--exclude",
                ".*",
                "-czf",
                tar_file,
                "-C",
                source.parent,
                source.name,
            ]
        ).returncode
        == 0
    )
