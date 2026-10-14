"""pkl から完成済みグループを抜き出し、未完成だけを残す。

手順3（ファイルごとの保存）は完成・未完成を区別せず packet_groups 全体を
保存する。そのため診断に到達せず落ちた実行の pkl には、出力ファイルが
書かれていない完成済みグループが残っている。これを回収して pkl を縮める。

    python -m app.extract_completed --dry-run
    python -m app.extract_completed

メモリ: pkl を全ロードするため、ピークは pkl のサイズ相当（2.2GB の pkl なら
約 2.3GiB）。搭載メモリが足りない機械では、スワップを足すか、余裕のある別の
機械で --input / --output-dir を指定して実行する。完成グループは書き出し次第
解放されるので、ピークは読み込み直後。
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from app.compact_loss_packet_group import compact_groups
from app.loss_diagnosis import (
    _extract_extension,
    analyze_packet_loss,
    reassemble_payload,
)
from common import file_io
from common.file_io import (
    LOSS_PACKET_GROUP_PATH,
    atomic_pickle_dump,
    safe_pickle_load,
)
from common.paths import X_BAND_DECODED_DIR, ensure_runtime_dirs


def describe(file_uid: str, packet_group: dict[str, Any], missing: int) -> str:
    total = packet_group.get("total_packet_size", len(packet_group.get("ptypes", [])))
    return f"{file_uid}: total={total}, missing={missing}"


def extract_completed(
    input_path: Path,
    output_dir: Path,
    *,
    dry_run: bool = False,
) -> tuple[int, int, int]:
    """完成済みグループを output_dir へ書き出し、pkl からは取り除く。

    戻り値は (完成して抜いた数, 未完成で残した数, 判定できなかった数)。
    """
    groups = safe_pickle_load(input_path)
    if not groups:
        print(f"no packet groups in {input_path}")
        return 0, 0, 0

    print(f"groups={len(groups)}")

    completed = 0
    remaining = 0
    undecidable = 0

    for file_uid in list(groups):
        packet_group = groups[file_uid]
        try:
            missing = analyze_packet_loss(packet_group)
        except (KeyError, TypeError) as exc:
            print(f"skip {file_uid}: 構造が想定と違う: {exc!r}")
            undecidable += 1
            remaining += 1
            continue

        if missing:
            remaining += 1
            continue

        # 完成している。拡張子は受信済み ptype から決める。
        try:
            extension = _extract_extension(packet_group)
        except ValueError as exc:
            print(f"skip {file_uid}: {exc}")
            undecidable += 1
            remaining += 1
            continue

        print(f"complete {describe(file_uid, packet_group, 0)} -> .{extension}")
        if not dry_run:
            data = reassemble_payload(packet_group["payloads"], extension)
            file_io.save_packet_group_file(
                data, file_uid, extension, output_dir=output_dir
            )
            # 書き出した時点で参照を切る。ここでメモリが減っていく。
            del groups[file_uid]
        completed += 1

    if dry_run:
        print(f"dry-run: {input_path} は変更しない")
        return completed, remaining, undecidable

    # 残った未完成グループの EE 埋めを共有オブジェクトに揃えてから保存する。
    shared, real = compact_groups(groups)
    print(f"残り {len(groups)} グループ: EE埋め={shared:,} / 実パケット={real:,}")

    before = input_path.stat().st_size if input_path.exists() else 0
    atomic_pickle_dump(groups, input_path)
    after = input_path.stat().st_size
    ratio = before / after if after else 0
    print(f"pkl: {before / 1e9:.3f} GB -> {after / 1e9:.3f} GB ({ratio:.1f} 倍削減)")

    return completed, remaining, undecidable


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write out completed packet groups and keep only the incomplete ones."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=LOSS_PACKET_GROUP_PATH,
        help=f"loss packet pickle path. default: {LOSS_PACKET_GROUP_PATH}",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=X_BAND_DECODED_DIR,
        help=f"directory for the completed files. default: {X_BAND_DECODED_DIR}",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would be extracted without writing anything.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.dry_run:
        ensure_runtime_dirs()
    completed, remaining, undecidable = extract_completed(
        Path(args.input),
        Path(args.output_dir),
        dry_run=args.dry_run,
    )
    print(
        f"summary: completed={completed}, remaining={remaining}, "
        f"undecidable={undecidable}"
    )


if __name__ == "__main__":
    main()
