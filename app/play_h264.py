import argparse
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_H264_DIR = PROJECT_ROOT / "output" / "X_band_decoded"
MAC_APP_PATHS = {
    "IINA": [Path("/Applications/IINA.app"), Path.home() / "Applications/IINA.app"],
    "VLC.app": [Path("/Applications/VLC.app"), Path.home() / "Applications/VLC.app"],
}


def find_latest_h264():
    candidates = sorted(
        DEFAULT_H264_DIR.glob("*.h264"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(f"No .h264 files found in {DEFAULT_H264_DIR}")
    return candidates[0]


def iter_start_codes(data):
    i = 0
    limit = len(data) - 3
    while i < limit:
        if data[i : i + 4] == b"\x00\x00\x00\x01":
            yield i, 4
            i += 4
            continue
        if data[i : i + 3] == b"\x00\x00\x01":
            yield i, 3
            i += 3
            continue
        i += 1


def inspect_h264(path):
    data = path.read_bytes()
    starts = list(iter_start_codes(data))
    nal_types = Counter()
    first_nals = []

    for offset, marker_size in starts:
        nal_offset = offset + marker_size
        if nal_offset >= len(data):
            continue
        nal_type = data[nal_offset] & 0x1F
        nal_types[nal_type] += 1
        if len(first_nals) < 12:
            first_nals.append((offset, nal_type))

    print(f"file: {path}")
    print(f"bytes: {len(data)}")
    print(f"start_codes: {len(starts)}")
    print(f"nal_type_counts: {dict(sorted(nal_types.items()))}")
    print(f"first_nals: {first_nals}")


def ffplay_command(path):
    return [
        "ffplay",
        "-hide_banner",
        "-loglevel",
        "warning",
        "-f",
        "h264",
        "-autoexit",
        str(path),
    ]


def mpv_command(path):
    return ["mpv", "--demuxer-lavf-format=h264", str(path)]


def vlc_command(path):
    return ["vlc", str(path)]


def mac_app_command(app_name, path):
    return ["open", "-a", app_name, str(path)]


def player_candidates(path, player):
    if player == "ffplay":
        return [("ffplay", ffplay_command(path))]
    if player == "mpv":
        return [("mpv", mpv_command(path))]
    if player == "vlc":
        return [("vlc", vlc_command(path))]
    if player == "iina":
        return [("IINA", mac_app_command("IINA", path))]
    if player == "mac-vlc":
        return [("VLC.app", mac_app_command("VLC", path))]
    if player == "opencv":
        return []

    return [
        ("ffplay", ffplay_command(path)),
        ("mpv", mpv_command(path)),
        ("vlc", vlc_command(path)),
        ("IINA", mac_app_command("IINA", path)),
        ("VLC.app", mac_app_command("VLC", path)),
    ]


def command_is_available(label, command):
    executable = command[0]
    if executable == "open":
        return shutil.which("open") is not None and any(
            path.exists() for path in MAC_APP_PATHS.get(label, [])
        )
    return shutil.which(executable) is not None


def preflight_command(label, command):
    executable = command[0]
    if executable == "open":
        return True, ""

    result = subprocess.run(
        [executable, "-version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode == 0:
        return True, ""
    detail = (result.stderr or result.stdout).strip()
    return False, detail


def opencv_is_available():
    try:
        import cv2  # noqa: F401
    except ImportError:
        return False
    return True


def play_with_opencv(path, fps=None, max_frames=None):
    try:
        import cv2
    except ImportError:
        print("OpenCV is not installed. Install opencv-python or use another player.", file=sys.stderr)
        return 1

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        print(f"OpenCV could not open: {path}", file=sys.stderr)
        return 1

    source_fps = cap.get(cv2.CAP_PROP_FPS)
    playback_fps = fps or source_fps or 30.0
    if playback_fps <= 0:
        playback_fps = 30.0
    delay_ms = max(1, int(1000 / playback_fps))

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    print("player: OpenCV")
    print(f"video: {width}x{height}, fps={source_fps or 'unknown'}")
    print("keys: q or Esc to quit")

    window_name = f"H.264: {path.name}"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    frame_count = 0
    started_at = time.monotonic()
    try:
        while True:
            if max_frames is not None and frame_count >= max_frames:
                break
            ok, frame = cap.read()
            if not ok:
                break
            frame_count += 1
            cv2.imshow(window_name, frame)
            key = cv2.waitKey(delay_ms) & 0xFF
            if key in (27, ord("q")):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()

    elapsed = max(time.monotonic() - started_at, 0.001)
    print(f"frames_played: {frame_count}, elapsed_sec={elapsed:.1f}")
    return 0


def play_h264(path, player, no_preflight, fps=None, max_frames=None):
    if player == "opencv":
        return play_with_opencv(path, fps=fps, max_frames=max_frames)

    errors = []
    for label, command in player_candidates(path, player):
        if not command_is_available(label, command):
            errors.append(f"{label}: command not found")
            continue

        if not no_preflight:
            ok, detail = preflight_command(label, command)
            if not ok:
                errors.append(f"{label}: preflight failed: {detail}")
                continue

        print(f"player: {label}")
        print("command:", " ".join(command))
        return subprocess.call(command)

    if player == "auto" and opencv_is_available():
        if errors:
            print("External players were not usable; falling back to OpenCV.")
            for error in errors:
                print(f"- {error}")
        return play_with_opencv(path, fps=fps, max_frames=max_frames)

    print("No usable H.264 player was found.", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    return 1


def parse_args():
    parser = argparse.ArgumentParser(description="Inspect and play a raw H.264 Annex B stream.")
    parser.add_argument(
        "path",
        nargs="?",
        help="Path to .h264 file. Defaults to the latest output/X_band_decoded/*.h264.",
    )
    parser.add_argument(
        "--player",
        choices=("auto", "ffplay", "mpv", "vlc", "iina", "mac-vlc", "opencv"),
        default="auto",
        help="Player command to use.",
    )
    parser.add_argument("--fps", type=float, help="Playback FPS for the OpenCV player.")
    parser.add_argument("--max-frames", type=int, help="Stop OpenCV playback after this many frames.")
    parser.add_argument("--inspect", action="store_true", help="Only print stream information.")
    parser.add_argument(
        "--no-preflight",
        action="store_true",
        help="Skip '<player> -version' check before launching.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    path = Path(args.path) if args.path else find_latest_h264()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    path = path.resolve()

    if not path.exists():
        raise FileNotFoundError(path)

    inspect_h264(path)
    if args.inspect:
        return 0

    return play_h264(
        path,
        args.player,
        args.no_preflight,
        fps=args.fps,
        max_frames=args.max_frames,
    )


if __name__ == "__main__":
    raise SystemExit(main())
