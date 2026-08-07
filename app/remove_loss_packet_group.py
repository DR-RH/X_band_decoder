from __future__ import annotations

import argparse
import datetime as dt
import os
import shutil
from pathlib import Path
from typing import Any

from common.file_io import atomic_pickle_dump, safe_pickle_load


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "loss_packet_group" / "loss_packet_group.pkl"

PTYPE_EXTENSIONS = {
    0x01: "csv",
    0x03: "txt",
    0x04: "log",
    0x05: "jpg",
    0x06: "h264",
}


def load_packet_groups(path: Path) -> dict[str, dict[str, Any]]:
    return safe_pickle_load(path)


def save_packet_groups(
    path: Path,
    groups: dict[str, dict[str, Any]],
    *,
    keep_backup: bool = True,
) -> None:
    atomic_pickle_dump(groups, path, keep_backup=keep_backup)


def backup_path_for(path: Path) -> Path:
    timestamp = dt.datetime.now().strftime("%Y%m%d%H%M%S_%f")
    return path.with_name(f"{path.name}.{timestamp}.bak")


def create_backup(path: Path, backup_path: Path) -> None:
    """世代バックアップを取る。

    pkl をその場で書き換えるコードはもう無い（書き込みは全て一時ファイル +
    os.replace）ので、ハードリンクで足りる。1GB の実コピーが不要になる。
    """
    try:
        os.link(path, backup_path)
    except OSError:
        shutil.copy2(path, backup_path)


def packet_type_set(packet_group: dict[str, Any]) -> set[int]:
    return {
        ptype
        for ptype in packet_group.get("ptypes", [])
        if isinstance(ptype, int)
    }


def extension_from_ptypes(ptypes: set[int]) -> str:
    if len(ptypes) == 1:
        return PTYPE_EXTENSIONS.get(next(iter(ptypes)), "bin")
    if not ptypes:
        return "unknown"
    return "mixed"


def missing_count(packet_group: dict[str, Any]) -> int:
    return sum(1 for ptype in packet_group.get("ptypes", []) if ptype is None)


def describe_packet_group(file_uid: str, packet_group: dict[str, Any]) -> str:
    ptypes = packet_type_set(packet_group)
    extension = extension_from_ptypes(ptypes)
    total_packet = packet_group.get(
        "total_packet_size",
        len(packet_group.get("ptypes", [])),
    )
    return (
        f"{file_uid}: extension={extension}, "
        f"total={total_packet}, missing={missing_count(packet_group)}, "
        f"ptypes={sorted(ptypes) if ptypes else 'unknown'}"
    )


def remove_packet_groups(
    input_path: Path,
    ids: list[str],
    *,
    dry_run: bool = False,
    backup: bool = True,
) -> tuple[int, int]:
    packet_groups = load_packet_groups(input_path)
    target_ids = [file_uid.lower() for file_uid in ids]

    removed = 0
    not_found = 0

    for file_uid in target_ids:
        packet_group = packet_groups.get(file_uid)
        if packet_group is None:
            not_found += 1
            print(f"not found {file_uid}")
            continue

        print(f"remove {describe_packet_group(file_uid, packet_group)}")
        if not dry_run:
            packet_groups.pop(file_uid, None)
        removed += 1

    if removed and not dry_run:
        if backup and input_path.exists():
            backup_path = backup_path_for(input_path)
            create_backup(input_path, backup_path)
            print(f"backup: {backup_path}")

        save_packet_groups(input_path, packet_groups, keep_backup=backup)

    print(
        f"summary: removed={removed}, not_found={not_found}, "
        f"remaining={len(packet_groups)}"
    )
    return removed, not_found


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove specified IDs from data/loss_packet_group/loss_packet_group.pkl."
    )
    parser.add_argument(
        "ids",
        nargs="+",
        help="file UID(s) to remove, for example: 6a5c6db6",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"loss packet pickle path. default: {DEFAULT_INPUT}",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show what would be removed without changing the pickle.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="do not create a timestamped .bak file before writing the pickle.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    remove_packet_groups(
        args.input,
        args.ids,
        dry_run=args.dry_run,
        backup=not args.no_backup,
    )


if __name__ == "__main__":
    main()
