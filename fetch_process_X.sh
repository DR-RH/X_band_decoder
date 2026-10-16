#!/bin/bash
#
# X-band データの取得と処理。
#
# 設計上の約束:
#   - 取得済み判定は raw_data_unprocessed と raw_data_processed の両方を見る。
#     片方しか見ないと、未処理のまま残っているファイルを毎回再ダウンロードする。
#   - unprocessed に置くのは「完全に転送し終えたファイル」だけ。転送中は .part
#     という名前にしておく（app.main は .bin / .cadu しか拾わないので無視される）。
#     中途半端なファイルを置くと、app.main がそれを処理済みとして processed へ
#     移してしまい、そのパスは二度と取得されなくなる。
#   - 1ファイルの取得失敗で全体を止めない。既に取得済みのファイルの処理は進める。
#   - 多重起動しない。前回が走っている間に cron が重なると、メモリを二重に
#     消費し、pkl の更新も後勝ちで失われる。
#
# 終了コード: 取得に失敗したファイルがあっても、処理まで到達すれば app.main の
#             終了コードを返す。

echo "===== start: $(date '+%Y-%m-%d %H:%M:%S') ====="
set -euo pipefail

PROJECT_DIR="$HOME/X_band_decoder"
DEST_DIR="$PROJECT_DIR/data/raw_data_unprocessed"
PROCESSING_DIR="$PROJECT_DIR/data/raw_data_processing"
PROCESSED_DIR="$PROJECT_DIR/data/raw_data_processed"
PYTHON="$PROJECT_DIR/.venv/bin/python3.11"

# 「既に持っている」と見なす置き場。ここに1つでも漏れがあると、そのパスは
# リモートから再ダウンロードされ、同じデータが二重に存在することになる。
# 退避用の置き場を増やしたときは、必ずここにも足すこと。
HAVE_DIRS=(
    "$DEST_DIR"                             # 未処理
    "$PROCESSING_DIR"                       # 処理中（前回の中断分を含む）
    "$PROCESSED_DIR"                        # 処理済み
    "$PROJECT_DIR/data/hold"                # 手動退避
    "$DEST_DIR/hold"                        # 旧来の退避場所
)

REMOTE="vertecs_x_band@133.18.122.205"
KEY="$HOME/.ssh/x_band_key"
REMOTE_DATA_DIR="/home/vertecs_x_band/data"

SSH_OPTS=(-i "$KEY" -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=30)
SUFFIX="_qpsk20Mbps.cadu"
LOCK_FILE="$HOME/.fetch_process_X.lock"

mkdir -p "$DEST_DIR" "$PROCESSING_DIR" "$PROCESSED_DIR"

# --- 多重起動の防止 ---------------------------------------------------------
# 前回の実行が続いている間は何もせず正常終了する。
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    echo "前回の実行が継続中のため終了する"
    echo "===== end: $(date '+%Y-%m-%d %H:%M:%S') ====="
    exit 0
fi

# --- 取り残された .part の掃除 ----------------------------------------------
# 前回の異常終了で残ったものは不完全なので捨てる。この後の差分判定で
# 再取得の対象に戻る。
for stale in "$DEST_DIR"/*"$SUFFIX".part; do
    [ -f "$stale" ] || continue
    echo "取り残された一時ファイルを削除: $(basename "$stale")"
    rm -f "$stale"
done

# --- 既に持っているパス名の一覧 ---------------------------------------------
# HAVE_DIRS のすべてを見る。1つ漏れるとそのパスが再ダウンロードされる。
local_names() {
    local dir f base
    for dir in "${HAVE_DIRS[@]}"; do
        for f in "$dir"/*"$SUFFIX"; do
            [ -f "$f" ] || continue
            base=$(basename "$f")
            echo "${base%"$SUFFIX"}"
        done
    done | LC_ALL=C sort -u
}

# --- リモートのパス名の一覧 -------------------------------------------------
remote_names() {
    ssh "${SSH_OPTS[@]}" "$REMOTE" \
        "LC_ALL=C find '$REMOTE_DATA_DIR' -maxdepth 1 -mindepth 1 -type d -printf '%f\n'" |
        LC_ALL=C sort
}

remote_size() {
    # リモートが BSD 系なら 'stat -c %s' を 'stat -f %z' に変える。
    ssh "${SSH_OPTS[@]}" "$REMOTE" "stat -c %s '$1' 2>/dev/null" || true
}

# --- 取得対象の決定 ---------------------------------------------------------
# ssh が落ちたときに全件を「新規」と誤認しないよう、一覧をいったん変数に取って
# 成否を見てから差分を取る。
missing_names=""
if ! ssh "${SSH_OPTS[@]}" "$REMOTE" "test -d '$REMOTE_DATA_DIR'"; then
    echo "リモートに接続できないか $REMOTE_DATA_DIR が無い。取得は飛ばして処理に進む"
elif ! remote_list=$(remote_names); then
    echo "リモートの一覧取得に失敗した。取得は飛ばして処理に進む"
else
    # comm -23 A B = A にあって B に無いもの（= まだ持っていないパス）
    missing_names=$(LC_ALL=C comm -23 \
        <(printf '%s\n' "$remote_list" | LC_ALL=C sed '/^$/d') \
        <(local_names) || true)
fi

# --- 取得 -------------------------------------------------------------------
# while をパイプの先に置くとサブシェルになり、集計が消えるうえ scp の失敗が
# pipefail で全体を落とす。ヒア文字列で現在のシェルで回す。
copied=0
skipped=0

while IFS= read -r name; do
    [ -n "$name" ] || continue

    src="$REMOTE_DATA_DIR/$name/qpsk20Mbps.cadu"
    dst="$DEST_DIR/${name}${SUFFIX}"
    tmp="$DEST_DIR/${name}${SUFFIX}.part"

    # 書き込み途中のディレクトリを拾っていないか、サイズで先に確かめる。
    size=$(remote_size "$src")
    if ! [[ "$size" =~ ^[0-9]+$ ]]; then
        echo "skip ($name): リモートのサイズを取得できない（未生成か照会失敗）"
        skipped=$((skipped + 1))
        continue
    fi
    if [ "$size" -eq 0 ]; then
        echo "skip ($name): リモートが 0 バイト"
        skipped=$((skipped + 1))
        continue
    fi

    echo "copy: $name/qpsk20Mbps.cadu ($size bytes)"
    if ! scp "${SSH_OPTS[@]}" "$REMOTE:$src" "$tmp"; then
        echo "skip ($name): 転送に失敗した"
        rm -f "$tmp"
        skipped=$((skipped + 1))
        continue
    fi

    got=$(stat -c %s "$tmp" 2>/dev/null || echo 0)
    if [ "$got" -ne "$size" ]; then
        echo "skip ($name): サイズ不一致 期待 $size / 実際 $got"
        rm -f "$tmp"
        skipped=$((skipped + 1))
        continue
    fi

    # ここで初めて app.main が拾う名前にする。
    if ! mv "$tmp" "$dst"; then
        echo "skip ($name): 配置に失敗した"
        rm -f "$tmp"
        skipped=$((skipped + 1))
        continue
    fi
    copied=$((copied + 1))
done <<< "$missing_names"

echo "取得: 成功 $copied / 見送り $skipped"

# --- 処理 -------------------------------------------------------------------
# app.main は 1 回の呼び出しで 1 ファイルだけ処理する（処理中ディレクトリへ
# 移して処理し、終わったら processed へ移す）。プロセスが終わるたびに OS が
# メモリを完全に回収するので、ファイル数が増えてもメモリは積み上がらない。
# 対象が無くなると EXIT_NOTHING_TO_DO(10) を返すので、それを停止条件にする。
cd "$PROJECT_DIR"
set +e

NOTHING_TO_DO=10
status=0
processed=0

while :; do
    "$PYTHON" -m app.main
    rc=$?

    if [ "$rc" -eq "$NOTHING_TO_DO" ]; then
        break
    fi
    if [ "$rc" -ne 0 ]; then
        # 失敗したファイルは処理中ディレクトリに残る。次回も同じファイルから
        # 始まるので、ここで止めて人が見られるようにする。
        echo "処理に失敗した (終了コード $rc)。処理中ディレクトリを確認すること:"
        ls -la "$PROJECT_DIR/data/raw_data_processing" || true
        status=$rc
        break
    fi
    processed=$((processed + 1))
done

set -e

echo "処理: $processed ファイル"
echo "===== end: $(date '+%Y-%m-%d %H:%M:%S') ====="
exit "$status"
