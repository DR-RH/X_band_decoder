# Constants (should match the transmitter and optical processing)
SYNC_MARKER = b'\x1A\xCF\xFC\x1D'
OPT_EXTRA_HEADER = 28      # Optical receiver adds 28 bytes at the beginning
OPT_EXTRA_TRAILER = 160    # ...and 160 bytes at the end of each packet
TX_HEADER_SIZE = 28        # Transmitter header after sync marker (2+3+1+22 = 28 bytes)
PAYLOAD_SIZE = 1087       # Payload size per packet

PTYPE_NORMAL  = 0x00
PTYPE_FINAL  = 0x02