"""Hunk の決定論的ハッシュ（SHA256）を生成する"""
from __future__ import annotations

import hashlib


def compute_hunk_hash(file_path: str, body_lines: list[str]) -> str:
    """ファイルパスと hunk 本文行から SHA256 ハッシュを生成する。

    行番号は含めず、コンテンツのみでハッシュを生成するため、
    コミット間でも同じ変更であれば同じハッシュが得られる。

    Args:
        file_path: ファイルパス
        body_lines: hunk 本文行のリスト（+/-/スペースで始まる行）

    Returns:
        16進数文字列（SHA256、64文字）
    """
    content = file_path + "\n" + "\n".join(body_lines)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
