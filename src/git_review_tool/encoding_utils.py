"""エンコーディング検出・デコードユーティリティ"""
from __future__ import annotations


def detect_and_decode(data: bytes) -> str:
    """バイト列を適切なエンコーディングで文字列にデコードする。

    以下の順序でデコードを試みる:
    1. UTF-8
    2. EUC-JP
    3. CP932（Shift_JIS の上位互換。Shift_JIS エンコードのファイルもカバーする）
    4. latin-1（フォールバック、バイトを損なわない）

    Args:
        data: デコード対象のバイト列

    Returns:
        デコードされた文字列
    """
    for encoding in ("utf-8", "euc-jp", "cp932"):
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    # latin-1 は必ず成功する（バイトを損なわない）
    return data.decode("latin-1")
