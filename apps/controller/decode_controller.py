from common import decode_utils

def decode_all_files(file_paths, packet_groups):
    """
    Decode all given raw files and update packet_groups.
    Responsible for orchestration only.
    """
    for target_file in file_paths:
        print(f"[decode] processing: {target_file}")
        packet_groups = decode_utils.decode_packets(target_file, packet_groups)

    return packet_groups