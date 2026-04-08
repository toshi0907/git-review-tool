/* app.js – hunkコメント保存 / レビュー済み状態保存 */

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json();
}

async function deleteJSON(url, body) {
  const res = await fetch(url, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json();
}

function showStatus(hunkHash) {
  const shortHash = hunkHash.slice(0, 12);
  const el = document.getElementById(`status-${shortHash}`);
  if (!el) return;
  el.style.display = "inline";
  setTimeout(() => { el.style.display = "none"; }, 2000);
}

function findCommentBox(hunkHash) {
  return document.querySelector(`textarea[data-hunk-hash="${hunkHash}"]`);
}

// コメント保存ボタン
document.querySelectorAll("button.save-btn").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const hunkHash = btn.dataset.hunkHash;
    const textarea = findCommentBox(hunkHash);
    if (!textarea) return;
    try {
      await postJSON("/api/comment", {
        hunk_hash: hunkHash,
        comment_text: textarea.value,
      });
      textarea.dataset.initialComment = textarea.value;
      showStatus(hunkHash);
    } catch (err) {
      alert("保存に失敗しました: " + err.message);
    }
  });
});

// コメントリセット
document.querySelectorAll("button.reset-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const hunkHash = btn.dataset.hunkHash;
    const textarea = findCommentBox(hunkHash);
    if (!textarea) return;
    textarea.value = textarea.dataset.initialComment || "";
  });
});

// コメント削除
document.querySelectorAll("button.delete-btn").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const hunkHash = btn.dataset.hunkHash;
    const textarea = findCommentBox(hunkHash);
    if (!textarea) return;

    if (!window.confirm("このhunkのコメントを削除しますか？")) {
      return;
    }
    try {
      await deleteJSON("/api/comment", { hunk_hash: hunkHash });
      textarea.value = "";
      textarea.dataset.initialComment = "";
      showStatus(hunkHash);
    } catch (err) {
      alert("削除に失敗しました: " + err.message);
    }
  });
});

// レビュー済みチェックボックス
document.querySelectorAll("input.reviewed-cb").forEach((cb) => {
  cb.addEventListener("change", async () => {
    const hunkHash = cb.dataset.hunkHash;
    const isReviewed = cb.checked;
    try {
      await postJSON("/api/reviewed", {
        hunk_hash: hunkHash,
        is_reviewed: isReviewed,
      });
      // hunk ブロックの背景色を切り替え
      const block = document.getElementById(`hunk-${hunkHash.slice(0, 12)}`);
      if (block) {
        if (isReviewed) {
          block.classList.add("is-reviewed");
        } else {
          block.classList.remove("is-reviewed");
        }
      }
    } catch (err) {
      // チェック状態を元に戻す
      cb.checked = !isReviewed;
      alert("保存に失敗しました: " + err.message);
    }
  });
});
