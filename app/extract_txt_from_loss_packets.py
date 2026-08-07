from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path
from typing import Any

from common.file_io import atomic_pickle_dump, safe_pickle_load


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "loss_packet_group" / "loss_packet_group.pkl"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output" / "loss_packet_txt"
PAYLOAD_SIZE = 1087
TXT_PTYPE = 0x03


def load_packet_groups(path: Path) -> dict[str, dict[str, Any]]:
    return safe_pickle_load(path)


def save_packet_groups(path: Path, groups: dict[str, dict[str, Any]]) -> None:
    atomic_pickle_dump(groups, path)


def packet_type_set(packet_group: dict[str, Any]) -> set[int]:
    return {
        ptype
        for ptype in packet_group.get("ptypes", [])
        if isinstance(ptype, int)
    }


def is_txt_packet_group(packet_group: dict[str, Any]) -> bool:
    return packet_type_set(packet_group) == {TXT_PTYPE}


def missing_sequences(packet_group: dict[str, Any]) -> list[int]:
    return [
        i
        for i, ptype in enumerate(packet_group.get("ptypes", []))
        if ptype is None
    ]


def reassemble_txt(packet_group: dict[str, Any]) -> bytes:
    payloads = packet_group.get("payloads", [])
    return b"".join(payloads).rstrip(b"\0")


def created_time_from_uid(file_uid: str) -> str:
    try:
        return dt.datetime.fromtimestamp(int(file_uid, 16)).strftime("%Y%m%d%H%M%S")
    except ValueError:
        return "unknown_time"


def output_path_for(output_dir: Path, file_uid: str) -> Path:
    extracted_at = dt.datetime.now().strftime("%Y%m%d%H%M%S_%f")
    created_at = created_time_from_uid(file_uid)
    return output_dir / f"loss_txt_{created_at}_{file_uid}_{extracted_at}.txt"


def extract_txt_groups(
    input_path: Path,
    output_dir: Path,
    *,
    remove: bool = False,
    dry_run: bool = False,
) -> tuple[int, int, int]:
    packet_groups = load_packet_groups(input_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    extracted = 0
    removed = 0
    skipped = 0

    for file_uid, packet_group in list(packet_groups.items()):
        ptypes = packet_type_set(packet_group)
        if not is_txt_packet_group(packet_group):
            skipped += 1
            print(f"skip {file_uid}: ptypes={sorted(ptypes) if ptypes else 'unknown'}")
            continue

        missing = missing_sequences(packet_group)
        payload_count = len(packet_group.get("payloads", []))
        total_packet_size = packet_group.get("total_packet_size", payload_count)
        destination = packet_group.get("dest_callsign", "")
        output_path = output_path_for(output_dir, file_uid)

        print(
            "extract "
            f"{file_uid}: total={total_packet_size}, payloads={payload_count}, "
            f"missing={len(missing)}, dest={destination}, output={output_path}"
        )

        if not dry_run:
            output_path.write_bytes(reassemble_txt(packet_group))

        extracted += 1

        if remove:
            if not dry_run:
                packet_groups.pop(file_uid, None)
            removed += 1

    if remove and not dry_run:
        save_packet_groups(input_path, packet_groups)

    return extracted, removed, skipped


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract txt packet groups from data/loss_packet_group/loss_packet_group.pkl."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"loss packet pickle path. default: {DEFAULT_INPUT}",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"directory to write extracted txt files. default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--remove",
        action="store_true",
        help="remove extracted txt packet groups from the pickle after writing files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show what would be extracted without writing txt files or changing the pickle.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    extracted, removed, skipped = extract_txt_groups(
        args.input,
        args.output_dir,
        remove=args.remove,
        dry_run=args.dry_run,
    )
    print(f"summary: extracted={extracted}, removed={removed}, skipped={skipped}")


if __name__ == "__main__":
    main()
