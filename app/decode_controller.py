from collections import Counter

from common import decode_utils


def decode_all_files(file_paths, packet_groups):
    """
    Decode all given raw files and update packet_groups.
    Responsible for orchestration only.
    """
    stats = Counter()
    for target_file in file_paths:
        print(f"[decode] processing: {target_file}")
        packet_groups = decode_utils.decode_packets(target_file, packet_groups, stats)

    print(
        f"[decode] 格納 {stats['stored']} / "
        f"非データフレーム {stats['frame_rejected']} / "
        f"payload長不正 {stats['short_payload']} / "
        f"seq範囲外 {stats['seq_out_of_range']}"
    )
    return packet_groups
