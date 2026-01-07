import common.constants as C
from tqdm import tqdm

def process_packet(raw_packet):
    """
    Process a single raw optical packet (one chunk from splitting by the sync marker).

    Raw optical packet structure:
      [Optical Extra Header (28 bytes)] +
      [Transmitter Packet: (VCDU header (2) + sequence (3) + reserved (1) + MDPU header (22) + payload (PAYLOAD_SIZE))] +
      [Optical Extra Trailer (160 bytes)]
      
    The new MDPU header (22 bytes) is structured as follows:
      • Bytes  0–1: Reserved (unique ID as 2 bytes, from the first 2 bytes of the provided hex identifier)
      • Bytes  2–8: Destination callsign (7 bytes, e.g. "JG6YBW\x00")
      • Bytes  9–15: Unique identifier (4-byte hex derived from the provided hex identifier, padded with 3 null bytes)
      • Byte     16: Data type (1 byte)
      • Bytes 17–20: Actual file length (4 bytes, big-endian) [Now represents the total number of packets]
      • Byte     21: Packet type indicator (1 byte)
    
    Returns a tuple:
      (seq, ptype, actual_file_length, payload, file_uid, mdpu_header)
    where file_uid is the unique identifier as an 8-digit hex string.
    """
    trimmed = raw_packet[C.OPT_EXTRA_HEADER:]
    transmitter_packet = trimmed[:-C.OPT_EXTRA_TRAILER]
    if len(transmitter_packet) < C.TX_HEADER_SIZE:
        return None

    # Validate VCDU header (first 2 bytes)
    vcdu = transmitter_packet[0:2]
    if vcdu != b'\x55\x40':

        return None
    if len(transmitter_packet) != 1115:
        return None
    # Sequence number: bytes 2-4 (3 bytes)
    seq = int.from_bytes(transmitter_packet[2:5], 'big')
    mdpu_header = transmitter_packet[6:28]
    payload = transmitter_packet[28:28+C.PAYLOAD_SIZE]
    print(len(transmitter_packet))

    ptype = mdpu_header[21]
    # Interpret the MDPU header field as the total number of packets for the file.
    actual_file_length = int.from_bytes(mdpu_header[17:21], 'big')
    # Unique identifier: bytes 9–12 (first 4 bytes of the unique info) as an 8-digit hex string.
    file_uid = mdpu_header[9:13].hex()
    return seq, ptype, actual_file_length, payload, file_uid, mdpu_header

def decode_packets(target_file, packet_groups):
    """
    Reads the received optical file, processes each packet, and packet_groups packets by file UID.
    
    Returns a dictionary where keys are file_uid (8-digit hex string) and values are dictionaries with:
      'packets': list of (seq, ptype, payload)
      'total_packet_size': total number of packets expected (from MDPU header, same for all packets in packet_group)
      'dest_callsign': destination callsign extracted from MDPU header.
    """
    with open(target_file, 'rb') as f:
        raw_data = f.read()
        
    packet_chunks = raw_data.split(C.SYNC_MARKER)[1:]
    if not packet_chunks:
        raise ValueError("No packets found in received file.")
    
    # packet_groups = {}   # key: file_uid, value: dictionary with keys: 'packets', 'total_packet_size', 'dest_callsign'
    for chunk in tqdm(packet_chunks, desc="Processing packets"):
        result = process_packet(chunk)
        if result is None:
            continue
        seq, ptype, total_packet_size, payload, file_uid, mdpu_header = result
        if ptype == 0x00:
            total_packet_size = 16621

        if file_uid not in packet_groups:
            # Extract destination callsign from bytes 2-8 (null terminated)
            dest = mdpu_header[2:9].split(b'\x00')[0].decode('ascii', errors='replace')
            # packet_groups[file_uid] = {'packets':{"payload":[b'FF'] * total_packet_size,'ptype':ptype}, 'total_packet_size': total_packet_size, 'dest_callsign': dest}
            packet_groups[file_uid] = {
                'payloads': [bytes([0xEE]) * C.PAYLOAD_SIZE for _ in range(total_packet_size)],
                'ptypes': [None] * total_packet_size,
                'total_packet_size': total_packet_size,
                'dest_callsign': dest
            }

        packet_groups[file_uid]['payloads'][seq] = payload
        packet_groups[file_uid]['ptypes'][seq] = ptype
    return packet_groups

def get_ranges(nums):
    if not nums:
        return []
    
    ranges = []
    start = nums[0]
    prev = nums[0]

    for n in nums[1:]:
        if n == prev + 1:
            prev = n
            continue
        
        # 連続が途切れたので範囲を保存
        numbers = prev - start + 1
        ranges.append((start, prev, numbers))
    
        start = n
        prev = n

    # 最後の範囲を追加
    numbers = prev - start + 1

    ranges.append((start, prev, numbers))
    return ranges