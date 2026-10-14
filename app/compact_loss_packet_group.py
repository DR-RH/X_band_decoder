"""既存の loss_packet_group.pkl を圧縮する（1回だけ実行する移行スクリプト）。

decode_utils が未受信スロットを共有オブジェクトで埋めるようになる前に
保存された pkl は、値が同じ EE 埋めパケットを total_packet_size 個ぶん
別オブジェクトとして持っている。これを共有オブジェクトへ差し替えると、
値は一切変わらないまま保存サイズとメモリが大きく減る。

    python -m app.compact_loss_packet_group --dry-run
    python -m app.compact_loss_packet_group
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common.decode_utils import EE_PAYLOAD
from common.file_io import (
    LOSS_PACKET_GROUP_PATH,
    atomic_pickle_dump,
    safe_pickle_load,
)


def compact_groups(groups: dict[str, dict[str, Any]]) -> tuple[int, int]:
    """EE 埋めスロットを共有オブジェクトに差し替える。値は変えない。

    戻り値は (差し替えたスロット数, 実パケットのスロット数)。
    """
    shared = 0
    real = 0
    for packet_group in groups.values():
        payloads = packet_group.get("payloads")
        if not payloads:
            continue
        for i, payload in enumerate(payloads):
            if payload == EE_PAYLOAD:
                if payload is not EE_PAYLOAD:
                    payloads[i] = EE_PAYLOAD
                shared += 1
            else:
                real += 1
    return shared, real


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Share the EE fill object inside loss_packet_group.pkl to shrink it."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=LOSS_PACKET_GROUP_PATH,
        help=f"loss packet pickle path. default: {LOSS_PACKET_GROUP_PATH}",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would change without writing the pickle.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)

    if not input_path.exists():
        print(f"not found: {input_path}")
        return

    before = input_path.stat().st_size
    groups = safe_pickle_load(input_path)
    if not groups:
        print(f"no packet groups in {input_path}")
        return

    shared, real = compact_groups(groups)
    print(
        f"groups={len(groups)}, EE埋め={shared:,} スロット, "
        f"実パケット={real:,} スロット"
    )

    if args.dry_run:
        print(f"dry-run: {input_path} ({before / 1e9:.3f} GB) は変更しない")
        return

    atomic_pickle_dump(groups, input_path)
    after = input_path.stat().st_size
    ratio = before / after if after else 0
    print(
        f"compacted: {before / 1e9:.3f} GB -> {after / 1e9:.3f} GB "
        f"({ratio:.1f} 倍削減)"
    )


if __name__ == "__main__":
    main()
