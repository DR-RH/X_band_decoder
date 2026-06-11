import shutil
from pathlib import Path

from common.paths import RAW_DATA_PROCESSED_DIR


def move_files(file_paths):
    print(f"move files {file_paths}" )
    RAW_DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for file in file_paths:
        source = Path(file)
        dst_filename = RAW_DATA_PROCESSED_DIR / source.name
        shutil.move(str(source), str(dst_filename))
    return
