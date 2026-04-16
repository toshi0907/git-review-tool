"""基本ワークフローのE2Eテスト"""
from __future__ import annotations

import json
import subprocess
import uuid

from git_review_tool.diff_parser import parse_diff
from git_review_tool.git_ops import get_diff
from git_review_tool.hunk_id import compute_hunk_hash
from git_review_tool.storage import Storage
from git_review_tool.webapp import create_app


def _run(cmd: list[str], cwd: str) -> str:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def _setup_test_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()

    _run(["git", "init"], str(repo))
    _run(["git", "config", "user.email", "test@example.com"], str(repo))
    _run(["git", "config", "user.name", "Test User"], str(repo))

    target_file = repo / "sample.py"
    target_file.write_text("line1\nline2\n", encoding="utf-8")
    _run(["git", "add", "sample.py"], str(repo))
    _run(["git", "commit", "-m", "initial"], str(repo))
    base = _run(["git", "rev-parse", "HEAD"], str(repo))

    target_file.write_text("line1\nline2 changed\nline3\n", encoding="utf-8")
    _run(["git", "add", "sample.py"], str(repo))
    _run(["git", "commit", "-m", "update"], str(repo))
    target = _run(["git", "rev-parse", "HEAD"], str(repo))

    return repo, base, target


def _build_app(repo: str, base: str, target: str, db_path: str):
    diff_text = get_diff(target, repo_path=repo, base=base)
    files = parse_diff(diff_text)
    for f in files:
        for h in f["hunks"]:
            h["hunk_hash"] = compute_hunk_hash(f["file_path"], h["body_lines"])

    storage = Storage(db_path)
    session_id = storage.get_or_create_repository_session(repo)
    app = create_app(files, storage, commit=f"{base}..{target}", session_id=session_id)
    app.config["TESTING"] = True
    return app, storage, files, session_id


def test_e2e_diff_to_html_display(tmp_path):
    repo, base, target = _setup_test_repo(tmp_path)
    app, _storage, _files, _session_id = _build_app(str(repo), base, target, str(tmp_path / "review.sqlite3"))

    with app.test_client() as client:
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"sample.py" in resp.data
        assert b"@@ -1,2 +1,3 @@" in resp.data


def test_e2e_comment_save_and_restore(tmp_path):
    repo, base, target = _setup_test_repo(tmp_path)
    app, storage, files, session_id = _build_app(str(repo), base, target, str(tmp_path / "review.sqlite3"))
    hunk_hash = files[0]["hunks"][0]["hunk_hash"]

    with app.test_client() as client:
        save_resp = client.post(
            "/api/comment",
            data=json.dumps({"hunk_hash": hunk_hash, "comment_text": "E2E comment"}),
            content_type="application/json",
        )
        assert save_resp.status_code == 200

        reload_resp = client.get("/")
        assert reload_resp.status_code == 200
        assert b"E2E comment" in reload_resp.data
        assert storage.get_comment(hunk_hash, session_id=session_id) == "E2E comment"


def test_e2e_review_status_save_and_restore(tmp_path):
    repo, base, target = _setup_test_repo(tmp_path)
    app, storage, files, session_id = _build_app(str(repo), base, target, str(tmp_path / "review.sqlite3"))
    hunk_hash = files[0]["hunks"][0]["hunk_hash"]

    with app.test_client() as client:
        save_resp = client.post(
            "/api/reviewed",
            data=json.dumps({"hunk_hash": hunk_hash, "is_reviewed": True}),
            content_type="application/json",
        )
        assert save_resp.status_code == 200

        reload_resp = client.get("/")
        assert reload_resp.status_code == 200
        assert b"checked" in reload_resp.data
        assert storage.get_reviewed(hunk_hash, session_id=session_id) is True


def test_e2e_delete_and_rename_diff_can_be_parsed(tmp_path):
    repo = tmp_path / "repo2"
    repo.mkdir()

    _run(["git", "init"], str(repo))
    _run(["git", "config", "user.email", "test@example.com"], str(repo))
    _run(["git", "config", "user.name", "Test User"], str(repo))

    a = repo / "old_name.txt"
    b = repo / "remove_me.txt"
    a.write_text("A\n", encoding="utf-8")
    b.write_text("B\n", encoding="utf-8")
    _run(["git", "add", "old_name.txt", "remove_me.txt"], str(repo))
    _run(["git", "commit", "-m", "add files"], str(repo))
    base = _run(["git", "rev-parse", "HEAD"], str(repo))

    _run(["git", "mv", "old_name.txt", "new_name.txt"], str(repo))
    _run(["git", "rm", "remove_me.txt"], str(repo))
    _run(["git", "commit", "-m", "rename and delete"], str(repo))
    target = _run(["git", "rev-parse", "HEAD"], str(repo))

    diff_text = get_diff(target, repo_path=str(repo), base=base)
    files = parse_diff(diff_text)

    assert len(files) >= 1


def test_e2e_comment_and_status_survive_rewritten_commit_hash(tmp_path):
    repo, base, target = _setup_test_repo(tmp_path)
    db_path = str(tmp_path / "review.sqlite3")

    app1, storage1, files1, _session_id1 = _build_app(str(repo), base, target, db_path)
    hunk_hash = files1[0]["hunks"][0]["hunk_hash"]

    with app1.test_client() as client:
        save_comment_resp = client.post(
            "/api/comment",
            data=json.dumps({"hunk_hash": hunk_hash, "comment_text": "keep me"}),
            content_type="application/json",
        )
        assert save_comment_resp.status_code == 200
        save_reviewed_resp = client.post(
            "/api/reviewed",
            data=json.dumps({"hunk_hash": hunk_hash, "is_reviewed": True}),
            content_type="application/json",
        )
        assert save_reviewed_resp.status_code == 200

    branch_name = f"rewritten-{uuid.uuid4().hex}"
    _run(["git", "checkout", "-b", branch_name, base], str(repo))
    target_file = repo / "sample.py"
    target_file.write_text("line1\nline2 changed\nline3\n", encoding="utf-8")
    _run(["git", "add", "sample.py"], str(repo))
    _run(["git", "commit", "-m", "rewritten update"], str(repo))
    rewritten_target = _run(["git", "rev-parse", "HEAD"], str(repo))
    assert rewritten_target != target

    app2, storage2, files2, session_id2 = _build_app(str(repo), base, rewritten_target, db_path)
    rewritten_hunk_hash = files2[0]["hunks"][0]["hunk_hash"]

    assert rewritten_hunk_hash == hunk_hash
    assert storage2.get_comment(rewritten_hunk_hash, session_id=session_id2) == "keep me"
    assert storage2.get_reviewed(rewritten_hunk_hash, session_id=session_id2) is True
