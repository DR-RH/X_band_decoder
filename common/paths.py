from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_UNPROCESSED_DIR = DATA_DIR / "raw_data_unprocessed"
# 処理中の1ファイルだけを置く場所。unprocessed からここへ移してから処理し、
# 終わったら processed へ移す。ここに残っているファイルは「前回の実行が
# 途中で落ちた」ことを意味するので、次回はそれを最優先で処理する。
RAW_DATA_PROCESSING_DIR = DATA_DIR / "raw_data_processing"
RAW_DATA_PROCESSED_DIR = DATA_DIR / "raw_data_processed"
LOSS_PACKET_GROUP_DIR = DATA_DIR / "loss_packet_group"

OUTPUT_DIR = PROJECT_ROOT / "output"
X_BAND_DECODED_DIR = OUTPUT_DIR / "X_band_decoded"
X_BAND_DECODED_DIR_EE_FILLED = OUTPUT_DIR / "X_band_decoded_EE_filled"
REPORT_DIR = OUTPUT_DIR / "packet_loss_report"


def resolve_repo_path(path):
    path = Path(path)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def ensure_runtime_dirs():
    for directory in (
        RAW_DATA_UNPROCESSED_DIR,
        RAW_DATA_PROCESSING_DIR,
        RAW_DATA_PROCESSED_DIR,
        LOSS_PACKET_GROUP_DIR,
        X_BAND_DECODED_DIR,
        X_BAND_DECODED_DIR_EE_FILLED,
        REPORT_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)
