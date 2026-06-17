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
    X_BAND_DECODED_DIR_EE_FILLED,
    resolve_repo_path,
)
import numpy as np
from astropy.io import fits

IMAGE_SHAPE = (3003, 3008)
FITS_BLOCK_SIZE = 2880


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

def save_bin_bytes_as_fits(data, file_uid, extension, header=None, overwrite=True, output_dir=X_BAND_DECODED_DIR):
    output_path = resolve_repo_path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    file_created_time = datetime.datetime.fromtimestamp(int(file_uid,16)).strftime("%Y%m%d%H%M%S")
    filename = output_path / f"decoded_{file_created_time}.fits"

    expected_bytes = IMAGE_SHAPE[0] * IMAGE_SHAPE[1] * 2
    if len(data) != expected_bytes:
        raise ValueError(f"Expected {expected_bytes} bytes, got {len(data)}")

    image = np.frombuffer(data, dtype=np.uint16)
    image = (image.astype(np.int32)).astype(np.int16)
    image = image.reshape(IMAGE_SHAPE)


    hdu = fits.PrimaryHDU(data=image)
    if header:
        for key, value in header.items():
            hdu.header[key] = value
    hdu.writeto(filename, overwrite=overwrite)
    return 

def save_packet_group_file(data, file_uid, extension, output_dir=X_BAND_DECODED_DIR):
    output_path = resolve_repo_path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    file_created_time = datetime.datetime.fromtimestamp(int(file_uid,16)).strftime("%Y%m%d%H%M%S")
    filename = output_path / f"decoded_{file_created_time}.{extension}"
    with filename.open("wb") as f:
        f.write(data)
        
    print(f"Saved {extension} file for UID {file_uid} as: {filename}")
    return filename

def save_packet_group_file_EE_filled(data, file_uid, extension, output_dir=X_BAND_DECODED_DIR_EE_FILLED):
    output_path = resolve_repo_path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    file_created_time = datetime.datetime.fromtimestamp(int(file_uid,16)).strftime("%Y%m%d%H%M%S")
    filename = output_path / f"decoded_{file_created_time}.{extension}"
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
