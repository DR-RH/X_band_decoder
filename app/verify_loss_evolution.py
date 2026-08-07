from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from common import constants as C
from common.decode_utils import extension_from_ptype, process_packet
from common.paths import PROJECT_ROOT


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output" / "loss_evolution"


def file_sort_key(path: Path) -> tuple[str, str, str]:
    match = re.search(r"(\d{8})_(\d{6})", path.name)
    if match:
        return match.group(1), match.group(2), path.name
    return "99999999", "999999", path.name


def iter_input_files(input_dir: Path) -> list[Path]:
    return sorted(
        (
            path
            for path in input_dir.iterdir()
            if path.is_file() and path.suffix.lower() in {".bin", ".cadu"}
        ),
        key=file_sort_key,
    )


def config_for(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".bin":
        return C.CONFIG_ADNICS
    return C.CONFIG_ASTROCUB


def packet_type_set(group: dict[str, Any]) -> set[int]:
    return set(group["ptypes_by_seq"].values())


def group_extension(group: dict[str, Any]) -> str:
    ptypes = packet_type_set(group)
    if not ptypes:
        return "unknown"
    if len(ptypes) > 1:
        return "mixed"
    return extension_from_ptype(next(iter(ptypes)))


def missing_count(group: dict[str, Any]) -> int:
    total = group["total_packet_size"]
    received = sum(1 for seq in group["ptypes_by_seq"] if 0 <= seq < total)
    return total - received


def snapshot_missing(groups: dict[str, dict[str, Any]]) -> dict[str, int]:
    return {
        file_uid: missing_count(group)
        for file_uid, group in groups.items()
    }


def parse_packets(path: Path, groups: dict[str, dict[str, Any]]) -> dict[str, Any]:
    with path.open("rb") as f:
        raw_data = f.read()

    packet_chunks = raw_data.split(C.SYNC_MARKER)[1:]
    config = config_for(path)
    stats: dict[str, Any] = {
        "chunks": len(packet_chunks),
        "valid_packets": 0,
        "new_groups": 0,
        "txt_resets": [],
        "non_txt_total_changes": [],
        "out_of_range": [],
    }

    for chunk in packet_chunks:
        result = process_packet(chunk, config)
        if result is None:
            continue

        seq, ptype, total_packet_size, _payload, file_uid, mdpu_header = result
        stats["valid_packets"] += 1

        if ptype == 0x00:
            total_packet_size = 16621

        if file_uid not in groups:
            dest = mdpu_header[2:9].split(b"\x00")[0].decode(
                "ascii",
                errors="replace",
            )
            groups[file_uid] = {
                "ptypes_by_seq": {},
                "total_packet_size": total_packet_size,
                "dest_callsign": dest,
            }
            stats["new_groups"] += 1
        else:
            current_total = groups[file_uid]["total_packet_size"]
            if ptype == 0x03 and total_packet_size != current_total:
                stats["txt_resets"].append(
                    {
                        "file_uid": file_uid,
                        "old_total": current_total,
                        "new_total": total_packet_size,
                        "old_missing": missing_count(groups[file_uid]),
                    }
                )
                dest = mdpu_header[2:9].split(b"\x00")[0].decode(
                    "ascii",
                    errors="replace",
                )
                groups[file_uid] = {
                    "ptypes_by_seq": {},
                    "total_packet_size": total_packet_size,
                    "dest_callsign": dest,
                    "discarded_total_packet_size": current_total,
                }
            elif total_packet_size != current_total:
                stats["non_txt_total_changes"].append(
                    {
                        "file_uid": file_uid,
                        "ptype": ptype,
                        "extension": extension_from_ptype(ptype),
                        "current_total": current_total,
                        "declared_total": total_packet_size,
                        "seq": seq,
                    }
                )

        current_total = groups[file_uid]["total_packet_size"]
        if seq >= current_total:
            stats["out_of_range"].append(
                {
                    "file_uid": file_uid,
                    "ptype": ptype,
                    "extension": extension_from_ptype(ptype),
                    "total_packet": current_total,
                    "seq": seq,
                }
            )
            continue

        groups[file_uid]["ptypes_by_seq"][seq] = ptype

    return stats


def remove_complete_groups(groups: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    completed = []
    for file_uid, group in list(groups.items()):
        if missing_count(group) == 0:
            completed.append(
                {
                    "file_uid": file_uid,
                    "extension": group_extension(group),
                    "total_packet": group["total_packet_size"],
                }
            )
            groups.pop(file_uid, None)
    return completed


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def verify(input_dir: Path, output_dir: Path, diagnosis_mode: str) -> dict[str, Path]:
    files = iter_input_files(input_dir)
    groups: dict[str, dict[str, Any]] = {}

    summary_rows: list[dict[str, Any]] = []
    increase_rows: list[dict[str, Any]] = []
    reset_rows: list[dict[str, Any]] = []
    total_change_rows: list[dict[str, Any]] = []
    out_of_range_rows: list[dict[str, Any]] = []

    for index, path in enumerate(files, start=1):
        before = snapshot_missing(groups)
        before_total_missing = sum(before.values())

        print(f"[{index}/{len(files)}] {path.name}")
        stats = parse_packets(path, groups)

        after_decode = snapshot_missing(groups)
        increased = [
            (file_uid, before[file_uid], after_decode[file_uid])
            for file_uid in before
            if file_uid in after_decode and after_decode[file_uid] > before[file_uid]
        ]
        decreased = [
            (file_uid, before[file_uid], after_decode[file_uid])
            for file_uid in before
            if file_uid in after_decode and after_decode[file_uid] < before[file_uid]
        ]
        new_loss_ids = [
            file_uid
            for file_uid in after_decode
            if file_uid not in before and after_decode[file_uid] > 0
        ]

        for file_uid, old_missing, new_missing in increased:
            group = groups[file_uid]
            increase_rows.append(
                {
                    "step": index,
                    "file": path.name,
                    "ID": file_uid,
                    "extension": group_extension(group),
                    "old_missing": old_missing,
                    "new_missing": new_missing,
                    "delta": new_missing - old_missing,
                    "total_packet": group["total_packet_size"],
                }
            )

        for reset in stats["txt_resets"]:
            reset_rows.append({"step": index, "file": path.name, **reset})

        for change in stats["non_txt_total_changes"]:
            total_change_rows.append({"step": index, "file": path.name, **change})

        for item in stats["out_of_range"]:
            out_of_range_rows.append({"step": index, "file": path.name, **item})

        if diagnosis_mode == "each":
            completed = remove_complete_groups(groups)
        else:
            completed = []
        after_diagnosis = snapshot_missing(groups)

        summary_rows.append(
            {
                "step": index,
                "file": path.name,
                "bytes": path.stat().st_size,
                "chunks": stats["chunks"],
                "valid_packets": stats["valid_packets"],
                "new_groups": stats["new_groups"],
                "new_loss_ids": len(new_loss_ids),
                "completed_ids": len(completed),
                "decreased_existing_ids": len(decreased),
                "increased_existing_ids": len(increased),
                "txt_resets": len(stats["txt_resets"]),
                "non_txt_total_changes": len(stats["non_txt_total_changes"]),
                "out_of_range": len(stats["out_of_range"]),
                "before_total_missing": before_total_missing,
                "after_decode_total_missing": sum(after_decode.values()),
                "after_diagnosis_total_missing": sum(after_diagnosis.values()),
                "active_loss_ids": len(groups),
                "diagnosis_mode": diagnosis_mode,
            }
        )

    if diagnosis_mode == "end":
        final_completed = remove_complete_groups(groups)
        print(f"final_completed_ids={len(final_completed)}")

    timestamp = dt.datetime.now().strftime("%Y%m%d%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "summary": output_dir / f"{timestamp}_summary.csv",
        "increases": output_dir / f"{timestamp}_increases.csv",
        "txt_resets": output_dir / f"{timestamp}_txt_resets.csv",
        "non_txt_total_changes": output_dir / f"{timestamp}_non_txt_total_changes.csv",
        "out_of_range": output_dir / f"{timestamp}_out_of_range.csv",
    }

    write_csv(
        paths["summary"],
        [
            "step",
            "file",
            "bytes",
            "chunks",
            "valid_packets",
            "new_groups",
            "new_loss_ids",
            "completed_ids",
            "decreased_existing_ids",
            "increased_existing_ids",
            "txt_resets",
            "non_txt_total_changes",
            "out_of_range",
            "before_total_missing",
            "after_decode_total_missing",
            "after_diagnosis_total_missing",
            "active_loss_ids",
            "diagnosis_mode",
        ],
        summary_rows,
    )
    write_csv(
        paths["increases"],
        [
            "step",
            "file",
            "ID",
            "extension",
            "old_missing",
            "new_missing",
            "delta",
            "total_packet",
        ],
        increase_rows,
    )
    write_csv(
        paths["txt_resets"],
        ["step", "file", "file_uid", "old_total", "new_total", "old_missing"],
        reset_rows,
    )
    write_csv(
        paths["non_txt_total_changes"],
        [
            "step",
            "file",
            "file_uid",
            "ptype",
            "extension",
            "current_total",
            "declared_total",
            "seq",
        ],
        total_change_rows,
    )
    write_csv(
        paths["out_of_range"],
        ["step", "file", "file_uid", "ptype", "extension", "total_packet", "seq"],
        out_of_range_rows,
    )

    print(f"processed_files={len(files)}")
    print(f"increased_existing_events={len(increase_rows)}")
    print(f"txt_reset_events={len(reset_rows)}")
    print(f"non_txt_total_change_events={len(total_change_rows)}")
    print(f"out_of_range_events={len(out_of_range_rows)}")
    print(f"final_active_loss_ids={len(groups)}")
    print(f"final_total_missing={sum(snapshot_missing(groups).values())}")
    for name, path in paths.items():
        print(f"{name}: {path}")

    return paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify packet-loss evolution while decoding files in oldest filename order."
    )
    parser.add_argument("input_dir", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--diagnosis-mode",
        choices=["each", "end"],
        default="each",
        help="each: remove complete groups after each file; end: keep groups until all files are decoded.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    verify(args.input_dir, args.output_dir, args.diagnosis_mode)


if __name__ == "__main__":
    main()
