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

function showLineStatus(hunkHash, newLineNum) {
  const shortHash = hunkHash.slice(0, 12);
  const el = document.getElementById(`line-status-${shortHash}-${newLineNum}`);
  if (!el) return;
  el.style.display = "inline";
  setTimeout(() => { el.style.display = "none"; }, 2000);
}

function findCommentBox(hunkHash) {
  return document.querySelector(`textarea[data-hunk-hash="${hunkHash}"]`);
}

function findLineCommentBox(hunkHash, newLineNum) {
  return document.querySelector(
    `textarea.line-comment-box[data-hunk-hash="${hunkHash}"][data-new-line-num="${newLineNum}"]`
  );
}

function findLineCommentRow(hunkHash, newLineNum) {
  return document.querySelector(
    `.line-comment-row[data-hunk-hash="${hunkHash}"][data-new-line-num="${newLineNum}"]`
  );
}

function findDiffLine(hunkHash, newLineNum) {
  return document.querySelector(
    `.diff-line-commentable[data-hunk-hash="${hunkHash}"][data-new-line-num="${newLineNum}"]`
  );
}

function shouldKeepLineCommentRowOpen(row) {
  const textarea = row.querySelector("textarea.line-comment-box");
  if (!textarea) return false;
  const current = textarea.value.trim();
  const initial = (textarea.dataset.initialComment || "").trim();
  return current.length > 0 || initial.length > 0;
}

function showLineCommentEditor(hunkHash, newLineNum) {
  const hunkBlock = document.querySelector(`.hunk-block[data-hunk-hash="${hunkHash}"]`);
  if (!hunkBlock) return;

  hunkBlock.querySelectorAll(".line-comment-row").forEach((row) => {
    if (!shouldKeepLineCommentRowOpen(row)) {
      row.classList.remove("is-active");
    }
  });
  hunkBlock.querySelectorAll(".diff-line-commentable").forEach((line) => {
    line.classList.remove("is-active");
  });

  const row = findLineCommentRow(hunkHash, newLineNum);
  const line = findDiffLine(hunkHash, newLineNum);
  if (!row || !line) return;

  row.classList.add("is-active");
  line.classList.add("is-active");

  const textarea = row.querySelector("textarea.line-comment-box");
  if (textarea) {
    textarea.focus();
  }
}

function setLineCommentMarker(hunkHash, newLineNum, hasComment) {
  const line = findDiffLine(hunkHash, newLineNum);
  if (!line) return;
  line.classList.toggle("has-line-comment", hasComment);
}

function getLineTarget(line) {
  const hunkHash = line.dataset.hunkHash;
  const rawLineNum = line.dataset.newLineNum;
  if (!hunkHash || !rawLineNum) {
    return null;
  }
  const newLineNum = Number(rawLineNum);
  if (!Number.isInteger(newLineNum) || newLineNum <= 0) {
    return null;
  }
  return { hunkHash, newLineNum };
}

document.querySelectorAll(".diff-line-commentable").forEach((line) => {
  line.addEventListener("click", () => {
    const target = getLineTarget(line);
    if (!target) return;
    showLineCommentEditor(target.hunkHash, target.newLineNum);
  });
  line.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    const target = getLineTarget(line);
    if (!target) return;
    showLineCommentEditor(target.hunkHash, target.newLineNum);
  });
});

// コメント保存ボタン
document.querySelectorAll("button.hunk-save-btn").forEach((btn) => {
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
document.querySelectorAll("button.hunk-delete-btn").forEach((btn) => {
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

// 行コメント保存
document.querySelectorAll("button.line-save-btn").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const hunkHash = btn.dataset.hunkHash;
    const newLineNum = Number(btn.dataset.newLineNum || 0);
    const textarea = findLineCommentBox(hunkHash, newLineNum);
    if (!textarea) return;
    try {
      await postJSON("/api/line-comment", {
        hunk_hash: hunkHash,
        new_line_num: newLineNum,
        comment_text: textarea.value,
      });
      textarea.dataset.initialComment = textarea.value;
      setLineCommentMarker(hunkHash, newLineNum, textarea.value.trim().length > 0);
      showLineStatus(hunkHash, newLineNum);
    } catch (err) {
      alert("保存に失敗しました: " + err.message);
    }
  });
});

// 行コメントリセット
document.querySelectorAll("button.line-reset-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const hunkHash = btn.dataset.hunkHash;
    const newLineNum = Number(btn.dataset.newLineNum || 0);
    const textarea = findLineCommentBox(hunkHash, newLineNum);
    if (!textarea) return;
    textarea.value = textarea.dataset.initialComment || "";
  });
});

// 行コメント削除
document.querySelectorAll("button.line-delete-btn").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const hunkHash = btn.dataset.hunkHash;
    const newLineNum = Number(btn.dataset.newLineNum || 0);
    const textarea = findLineCommentBox(hunkHash, newLineNum);
    if (!textarea) return;

    if (!window.confirm(`L${newLineNum} のコメントを削除しますか？`)) {
      return;
    }
    try {
      await deleteJSON("/api/line-comment", {
        hunk_hash: hunkHash,
        new_line_num: newLineNum,
      });
      textarea.value = "";
      textarea.dataset.initialComment = "";
      const row = findLineCommentRow(hunkHash, newLineNum);
      if (row) {
        row.classList.remove("is-active");
      }
      setLineCommentMarker(hunkHash, newLineNum, false);
      showLineStatus(hunkHash, newLineNum);
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
          block.classList.add("is-collapsed");
        } else {
          block.classList.remove("is-reviewed");
          block.classList.remove("is-collapsed");
        }
      }
    } catch (err) {
      // チェック状態を元に戻す
      cb.checked = !isReviewed;
      alert("保存に失敗しました: " + err.message);
    }
  });
});

// フローティングTOCサイドバー
(function initToc() {
  const sidebar = document.getElementById("toc-sidebar");
  if (!sidebar) return;

  const headerEl = document.querySelector("header");
  const headerGap = document.getElementById("toc-header-gap");
  const fileBlocks = Array.from(document.querySelectorAll(".file-block"));
  const tocItems = Array.from(document.querySelectorAll(".toc-item"));

  // TOCのヘッダーギャップをヘッダー高さに合わせる
  function syncHeaderGap() {
    if (headerEl && headerGap) {
      headerGap.style.height = headerEl.offsetHeight + "px";
    }
  }
  syncHeaderGap();
  window.addEventListener("resize", syncHeaderGap);

  // アクティブファイルをTOCで強調表示
  function updateActiveTocItem() {
    const headerH = headerEl ? headerEl.offsetHeight : 0;
    const scrollY = window.scrollY || window.pageYOffset;

    let activeIdx = 1;
    fileBlocks.forEach((block, i) => {
      const blockTop = block.getBoundingClientRect().top + scrollY;
      if (scrollY + headerH + 8 >= blockTop) {
        activeIdx = i + 1;
      }
    });

    tocItems.forEach((item) => {
      const idx = parseInt(item.dataset.fileIndex, 10);
      const nowActive = idx === activeIdx;
      const wasActive = item.classList.contains("is-active");
      if (wasActive !== nowActive) {
        item.classList.toggle("is-active", nowActive);
      }
    });

    // アクティブアイテムをTOCパネル内でスクロールして表示
    const activeItem = sidebar.querySelector(".toc-item.is-active");
    if (activeItem) {
      activeItem.scrollIntoView({ block: "nearest" });
    }
  }

  window.addEventListener("scroll", updateActiveTocItem, { passive: true });
  updateActiveTocItem();
})();
