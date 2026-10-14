from collections import Counter

from common import decode_utils


def new_stats():
    return Counter()


def decode_file(target_file, packet_groups, stats):
    """1ファイルだけデコードして packet_groups を更新する。"""
    print(f"[decode] processing: {target_file}")
    return decode_utils.decode_packets(target_file, packet_groups, stats)


def report(stats):
    print(
        f"[decode] 格納 {stats['stored']} / "
        f"非データフレーム {stats['frame_rejected']} / "
        f"payload長不正 {stats['short_payload']} / "
        f"seq範囲外 {stats['seq_out_of_range']}"
    )


def decode_all_files(file_paths, packet_groups):
    """
    Decode all given raw files and update packet_groups.
    Responsible for orchestration only.

    1ファイルずつ確定させたい通常の処理は main 側のループを使う。
    こちらは保存・移動を挟まずに一括でデコードしたい場合に残している。
    """
    stats = new_stats()
    for target_file in file_paths:
        packet_groups = decode_file(target_file, packet_groups, stats)

    report(stats)
    return packet_groups
