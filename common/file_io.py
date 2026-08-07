import pickle
import shutil
import datetime
import os
import tempfile
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

IMAGE_SHAPE = (3003, 3008)
FITS_BLOCK_SIZE = 2880


LOSS_PACKET_GROUP_PATH = LOSS_PACKET_GROUP_DIR / "loss_packet_group.pkl"


def _bak_path(path):
    return path.with_name(path.name + ".bak")


def _fsync_dir(directory):
    """rename 自体をディスクへ確定させる。Windows は非対応なので黙って諦める。"""
    try:
        fd = os.open(str(directory), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def _sweep_stale_tmp(path):
    """異常終了で取り残された一時ファイルを掃除する（1個1GB級なので放置できない）。"""
    for stale in path.parent.glob(path.name + ".*.tmp"):
        try:
            stale.unlink()
            print(f"[file_io] 取り残された一時ファイルを削除: {stale}")
        except OSError:
            pass


def atomic_pickle_dump(obj, path, keep_backup=True):
    """同一ディレクトリの一時ファイルへ書き切ってから os.replace で差し替える。

    途中で落ちても path は直前の内容のまま残り、部分書き込みが表に出ない。
    直前世代は .bak へ退避する。退避にハードリンクを使うので 1GB の
    コピー I/O は発生しない（ただし2世代がディスクを占めるのは避けられない）。
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _sweep_stale_tmp(path)

    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as f:
            pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)
            f.flush()
            os.fsync(f.fileno())

        if keep_backup and path.exists():
            bak = _bak_path(path)
            bak.unlink(missing_ok=True)
            try:
                os.link(path, bak)
            except OSError:
                pass  # 非対応FSならバックアップ無しで続行する

        os.replace(tmp_path, path)
        _fsync_dir(path.parent)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise
    return path


def _quarantine(path):
    """壊れたファイルを退避する。削除はしない（次回起動をブロックさせないため）。"""
    stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    dead = path.with_name(f"{path.name}.corrupt.{stamp}")
    try:
        os.replace(path, dead)
        print(f"[file_io] 破損ファイルを退避しました: {dead}")
    except OSError as exc:
        print(f"[file_io] 破損ファイルの退避に失敗: {path}: {exc!r}")


def safe_pickle_load(path, default_factory=dict):
    """本体 -> .bak の順に読む。壊れていれば退避して次の候補へ落ちる。"""
    path = Path(path)
    for candidate, label in ((path, "本体"), (_bak_path(path), "バックアップ")):
        if not candidate.exists():
            continue
        try:
            with candidate.open("rb") as f:
                data = pickle.load(f)
        except Exception as exc:
            print(f"[file_io] {label}が読めません ({candidate}): {exc!r}")
            _quarantine(candidate)
            continue
        if not isinstance(data, dict):
            print(f"[file_io] {label}の型が不正です ({candidate}): {type(data).__name__}")
            _quarantine(candidate)
            continue
        if label != "本体":
            print(f"[file_io] {label}から復旧しました: {candidate}")
        return data
    return default_factory()


def save_loss_packet_group(packet_loss_group):
    return atomic_pickle_dump(packet_loss_group, LOSS_PACKET_GROUP_PATH)


def load_loss_packet_group():
    return safe_pickle_load(LOSS_PACKET_GROUP_PATH)

def save_bin_bytes_as_fits(data, file_uid, extension, header=None, overwrite=True, output_dir=X_BAND_DECODED_DIR):
    from astropy.io import fits

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

    received_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S_%f")
    file_created_time = datetime.datetime.fromtimestamp(int(file_uid,16)).strftime("%Y%m%d%H%M%S")

    if extension in {"txt", "log"}:
        filename = output_path / f"decoded_{file_created_time}_{received_time}.{extension}"
    else:
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

def write_loss_report(report_path, file_uid, extension, loss_sequence, total_packet):
    ranges = decode_utils.get_ranges(loss_sequence)
    report_path = resolve_repo_path(report_path)
    with report_path.open(mode="a", newline="") as f:
        writer = csv.writer(f)
        for rng in ranges:
            writer.writerow([file_uid, extension] + list(rng) + [total_packet])

def create_loss_report_file():
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"{timestamp}.csv"
    with report_path.open(mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "extension", "start", "end", "number", "total_packet"])
    return report_path
