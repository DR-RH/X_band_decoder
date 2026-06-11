import pickle
import shutil
import datetime
from common import decode_utils
import csv
from pathlib import Path
from common.paths import (
    LOSS_PACKET_GROUP_DIR,
    RAW_DATA_PROCESSED_DIR,
    REPORT_DIR,
    X_BAND_DECODED_DIR,
    resolve_repo_path,
)

def save_loss_packet_group(packet_loss_group,):
    LOSS_PACKET_GROUP_DIR.mkdir(parents=True, exist_ok=True)
    path = LOSS_PACKET_GROUP_DIR / "loss_packet_group.pkl"
    with path.open("wb") as f:
        pickle.dump(packet_loss_group, f)
    return

def load_loss_packet_group():
    path = LOSS_PACKET_GROUP_DIR / "loss_packet_group.pkl"
    if not path.exists():
        return {}
    with path.open("rb") as f:
        return pickle.load(f)
    
def save_packet_group_file(data, file_uid, extension, output_dir=X_BAND_DECODED_DIR):
    output_path = resolve_repo_path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    file_created_time = datetime.datetime.fromtimestamp(int(file_uid,16)).strftime("%Y%m%d%H%M%S")
    filename = output_path / f"decoded_{file_created_time}_{timestamp}.{extension}"
    with filename.open("wb") as f:
        f.write(data)
    print(f"Saved {extension} file for UID {file_uid} as: {filename}")
    return filename

def move_files(file_paths):
    print(f"move files {file_paths}" )
    RAW_DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for file in file_paths:
        source = Path(file)
        dst_filename = RAW_DATA_PROCESSED_DIR / source.name
        shutil.move(str(source), str(dst_filename))
    return

def write_loss_report(report_path, file_uid, extension, loss_sequence):
    ranges = decode_utils.get_ranges(loss_sequence)
    report_path = resolve_repo_path(report_path)
    with report_path.open(mode="a", newline="") as f:
        writer = csv.writer(f)
        for rng in ranges:
            writer.writerow([file_uid,extension]+list(rng))

def create_loss_report_file():
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"{timestamp}.csv"
    with report_path.open(mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "extension", "start", "end", "number"])
    return report_path
