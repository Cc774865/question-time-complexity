const files = [];
let classification = emptyClassification();
const notes = new Map();

const drop = document.querySelector("#drop");
const picker = document.querySelector("#picker");
const fileList = document.querySelector("#file-list");
const clearInput = document.querySelector("#clear-input");
const startWork = document.querySelector("#start-work");
const outputBody = document.querySelector("#output-body");
const starBoard = document.querySelector("#star-board");
const outputNote = document.querySelector("#output-note");
const reviewBody = document.querySelector("#review-body");
const progress = document.querySelector("#progress");
const progressBar = document.querySelector("#progress-bar");
const progressFill = document.querySelector("#progress-fill");
const progressLabel = document.querySelector("#progress-label");
const visionKey = document.querySelector("#vision-key");
const inputCount = document.querySelector("#input-count");
const reviewCount = document.querySelector("#review-count");
const reviewSubmit = document.querySelector("#review-submit");
const reviewNote = document.querySelector("#review-note");
const starFoot = document.querySelector("#star-foot");
const previewSubmit = document.querySelector("#preview-submit");

picker.addEventListener("change", () => {
  addFiles(picker.files);
  picker.value = "";
});

drop.addEventListener("dragover", (event) => {
  event.preventDefault();
  drop.classList.add("over");
});

drop.addEventListener("dragleave", () => {
  drop.classList.remove("over");
});

drop.addEventListener("drop", (event) => {
  event.preventDefault();
  drop.classList.remove("over");
  addFiles(event.dataTransfer.files);
});

startWork.addEventListener("click", () => {
  if (!files.length || working) return;
  setWorking(true);
  const names = files.map((file) => file.name);
  fetch("/api/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ files: names, apiKey: visionKey.value }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (!data.started) setWorking(false);
      return refreshProgress();
    })
    .catch(() => setWorking(false));
});

clearInput.addEventListener("click", () => {
  if (!onServer) {
    files.splice(0, files.length);
    render();
    return;
  }
  fetch("/api/files", { method: "DELETE" }).then(() => refreshFiles());
});

function setWorking(next) {
  working = next;
  startWork.textContent = next ? "已开始" : "开始工作";
  startWork.disabled = next || files.length === 0;
}

function emptyClassification() {
  return { document: null, preview: null, review: [], pairs: [] };
}

let onServer = false;
let resultStamp = "";
let working = false;

function addFiles(list) {
  if (!onServer) {
    for (const file of list) files.push(file);
    render();
    return;
  }
  const uploads = [...list].map((file) => fetch(`/api/files?name=${encodeURIComponent(file.name)}`, {
    method: "POST",
    body: file,
  }));
  Promise.all(uploads).then(() => refreshFiles());
}

function refreshFiles() {
  return fetch("/api/files")
    .then((response) => {
      if (!response.ok) throw new Error("no files");
      return response.json();
    })
    .then((data) => {
      onServer = true;
      files.splice(0, files.length, ...data.files);
      render();
    })
    .catch(() => {
      onServer = false;
    });
}

function refreshProgress() {
  return fetch("/api/progress")
    .then((response) => (response.ok ? response.json() : null))
    .then((data) => {
      if (data) showProgress(data);
    })
    .catch(() => {});
}

function showProgress(data) {
  const percent = Math.max(0, Math.min(100, Number(data.percent) || 0));
  const visible = Boolean(data.running) || percent > 0 || Boolean(data.label);
  progress.hidden = !visible;
  progressBar.setAttribute("aria-valuenow", String(percent));
  progressFill.style.width = `${percent}%`;
  progressLabel.textContent = data.label || "";
  setWorking(Boolean(data.running));
}

function refreshResult() {
  return fetch("/api/result")
    .then((response) => {
      if (response.status === 404) {
        resultStamp = "";
        setClassification({});
        return "";
      }
      if (!response.ok) return "";
      return response.text();
    })
    .then((text) => {
      if (!text || text === resultStamp) return;
      resultStamp = text;
      setClassification(JSON.parse(text));
    })
    .catch(() => {});
}

function render() {
  renderInput();
  renderOutput();
  renderStars();
  renderReview();
}

function renderInput() {
  inputCount.textContent = `${files.length} 个文件`;
  clearInput.disabled = files.length === 0;
  startWork.disabled = working || files.length === 0;
  if (!working) startWork.textContent = "开始工作";
  fileList.replaceChildren();
  for (const [index, file] of files.entries()) {
    const row = document.createElement("li");
    row.className = "file-row";
    row.append(
      stamp(extensionOf(file.name)),
      named(file.name, "file-name"),
      sized(file.size),
      removeButton(index),
    );
    fileList.append(row);
  }
}

reviewSubmit.addEventListener("click", () => {
  reviewNote.hidden = true;
  fetch("/api/submit", { method: "POST" })
    .then((response) => response.json())
    .then((data) => {
      if (!data.ok) {
        reviewNote.hidden = false;
        reviewNote.textContent = data.message || "还有题目没选班型";
        return;
      }
      resultStamp = JSON.stringify(data.result);
      setClassification(data.result);
      refreshProgress();
    })
    .catch(() => {
      reviewNote.hidden = false;
      reviewNote.textContent = "提交没有完成";
    });
});

function renderOutput() {
  outputBody.replaceChildren();
  const preview = classification.preview;
  const doc = classification.document;
  if (!preview && !doc) {
    outputBody.append(emptyLine("开始工作后会先给出预览文档。"));
    return;
  }
  if (preview) {
    const name = previewName(preview.filename || LessonFile.filename(preview));
    outputBody.append(fileRow("预览", name, preview.previewBytes || 0, () => downloadFile("/api/preview", name)));
    for (const revision of preview.previewRevisions || []) {
      const revisionLabel = previewRevisionName(preview.filename || LessonFile.filename(preview), revision.n);
      outputBody.append(fileRow("预览", revisionLabel, revision.bytes || 0, () => downloadFile(`/api/preview?n=${revision.n}`, revisionLabel)));
    }
  }
  if (doc) {
    const name = doc.productionName || productionName(doc.filename || LessonFile.filename(doc));
    outputBody.append(fileRow("生产", name, doc.bytes || 0, () => downloadFile("/api/output", name)));
  }
}

function previewName(filename) {
  return String(filename || "预览.docx").replace(/\.docx$/i, "") + "-预览.docx";
}

function previewRevisionName(filename, count) {
  return String(filename || "预览.docx").replace(/\.docx$/i, "") + `-预览(${count}).docx`;
}

function productionName(filename) {
  return String(filename || "生产.docx").replace(/\.docx$/i, "") + "-生产.docx";
}

function fileRow(label, name, bytes, onClick) {
  const row = document.createElement("div");
  row.className = "out-row";
  const button = document.createElement("button");
  button.type = "button";
  button.className = "small-btn";
  button.textContent = "下载";
  button.addEventListener("click", onClick);
  row.append(stamp(label), named(name, "out-name"), sized(bytes), button);
  return row;
}

function renderStars() {
  const pairs = classification.pairs || [];
  starBoard.replaceChildren();
  starFoot.hidden = pairs.length === 0;
  if (!pairs.length) return;
  const hint = document.createElement("p");
  hint.className = "empty";
  hint.textContent = "从上到下是 2 星到 8 星。换完顺序后点提交，生成新的预览。";
  starBoard.append(hint, pairList(pairs));
}

function renderReview() {
  const items = classification.review;
  const pairs = classification.pairs || [];
  reviewCount.textContent = `${items.length} 道`;
  reviewSubmit.disabled = pairs.length === 0;
  reviewBody.replaceChildren();
  if (items.length === 0 && pairs.length === 0) {
    reviewBody.append(emptyLine("没有待审核的题目。"));
    return;
  }
  if (items.length === 0) {
    reviewBody.append(emptyLine("没有作业题和晋级题。提交后生成生产文档。"));
    return;
  }
  const list = document.createElement("ul");
  list.className = "review-list";
  for (const [index, item] of items.entries()) {
    list.append(reviewCard(item, index));
  }
  reviewBody.append(list);
}

function pairList(pairs) {
  const list = document.createElement("ul");
  list.className = "review-list star-order";
  for (const [index, pair] of pairs.entries()) list.append(pairCard(pair, index));
  list.addEventListener("dragover", (event) => {
    event.preventDefault();
    const dragging = list.querySelector(".dragging");
    const element = event.target instanceof Element ? event.target : event.target.parentElement;
    const target = element && element.closest(".star-row");
    if (!dragging || !target || dragging === target) return;
    const rect = target.getBoundingClientRect();
    const after = event.clientY > rect.top + rect.height / 2;
    list.insertBefore(dragging, after ? target.nextSibling : target);
    paintStars(list);
  });
  list.addEventListener("drop", (event) => {
    event.preventDefault();
    const order = [...list.querySelectorAll(".star-row")].map((row) => Number(row.dataset.block));
    saveStarOrder(order);
  });
  return list;
}

function pairCard(pair, index) {
  const card = document.createElement("li");
  card.className = "review-card star-row";
  card.draggable = true;
  card.dataset.block = String(pair.example_block);
  const kind = document.createElement("div");
  kind.className = "review-kind";
  kind.textContent = `${index + 2}星`;
  const text = document.createElement("p");
  text.className = "review-text";
  text.textContent = [pair.example, pair.practice ? `练：${pair.practice}` : ""].filter(Boolean).join("\n");
  card.addEventListener("dragstart", (event) => {
    card.classList.add("dragging");
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", card.dataset.block);
  });
  card.addEventListener("dragend", () => card.classList.remove("dragging"));
  card.append(kind, text);
  return card;
}

function paintStars(list) {
  [...list.querySelectorAll(".star-row")].forEach((row, index) => {
    const kind = row.querySelector(".review-kind");
    if (kind) kind.textContent = `${index + 2}星`;
  });
}

previewSubmit.addEventListener("click", submitPreview);

function submitPreview() {
  outputNote.hidden = true;
  fetch("/api/preview-submit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  })
    .then((response) => response.text())
    .then((text) => {
      const data = text ? JSON.parse(text) : {};
      if (data.ok === false) {
        outputNote.hidden = false;
        outputNote.textContent = data.message || "预览没有写出";
        return;
      }
      resultStamp = text;
      setClassification(data);
    })
    .catch(() => {
      outputNote.hidden = false;
      outputNote.textContent = "预览没有写出";
    });
}

function saveStarOrder(order) {
  outputNote.hidden = true;
  fetch("/api/reorder-stars", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ order }),
  })
    .then((response) => response.text())
    .then((text) => {
      const data = text ? JSON.parse(text) : {};
      if (data.ok === false) {
        outputNote.hidden = false;
        outputNote.textContent = data.message || "这份排序和正课对不上";
        return;
      }
      resultStamp = text;
      setClassification(data);
    })
    .catch(() => {
      outputNote.hidden = false;
      outputNote.textContent = "顺序没有记下";
    });
}

function reviewCard(item, index) {
  const card = document.createElement("li");
  card.className = "review-card";
  const kind = document.createElement("div");
  kind.className = "review-kind";
  kind.textContent = item.kind || "待审核";
  const text = document.createElement("p");
  text.className = "review-text";
  text.textContent = item.text || item.title || "";
  const pick = document.createElement("select");
  pick.className = "level-pick";
  pick.append(new Option("班型", ""));
  for (const level of ["B", "A", "AA", "AAA", "S"]) {
    pick.append(new Option(level, level));
  }
  pick.value = item.level || "";
  pick.addEventListener("change", () => saveReviewLevel(index, pick.value));
  card.append(kind, text, pick);
  return card;
}

function saveReviewLevel(index, level) {
  fetch("/api/review", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ index, level }),
  })
    .then((response) => response.text())
    .then((text) => {
      if (!text) return;
      resultStamp = text;
      setClassification(JSON.parse(text));
    });
}

function downloadFile(url, name) {
  fetch(url)
    .then((response) => {
      if (!response.ok) throw new Error("no output");
      return response.blob();
    })
    .then((blob) => {
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = name;
      link.click();
      URL.revokeObjectURL(link.href);
    });
}

function stamp(label) {
  const node = document.createElement("span");
  node.className = "stamp";
  node.textContent = label || "FILE";
  return node;
}

function named(text, className) {
  const node = document.createElement("span");
  node.className = className;
  node.textContent = text;
  node.title = text;
  return node;
}

function sized(bytes) {
  const node = document.createElement("span");
  node.className = "file-size";
  node.textContent = formatSize(bytes);
  return node;
}

function removeButton(index) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "small-btn danger";
  button.textContent = "移除";
  button.addEventListener("click", () => {
    const file = files[index];
    if (!onServer) {
      files.splice(index, 1);
      render();
      return;
    }
    fetch(`/api/files?name=${encodeURIComponent(file.name)}`, { method: "DELETE" }).then(() => refreshFiles());
  });
  return button;
}

function emptyLine(text) {
  const node = document.createElement("p");
  node.className = "empty";
  node.textContent = text;
  return node;
}

function extensionOf(name) {
  const match = /\.([A-Za-z0-9]+)$/.exec(name || "");
  return match ? match[1].toUpperCase() : "FILE";
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function setClassification(next) {
  const hasDocument = Boolean(next.released);
  classification = {
    document: hasDocument ? next : null,
    preview: next.preview ? next : null,
    review: next.review || [],
    pairs: next.pairs || [],
  };
  notes.clear();
  render();
}

window.setClassification = setClassification;

fetch("/api/vision")
  .then((response) => (response.ok ? response.json() : null))
  .then((data) => {
    if (data && data.configured) visionKey.placeholder = "已保存，留空则沿用";
  })
  .catch(() => {});

refreshFiles().then(() => Promise.all([refreshResult(), refreshProgress()]));
setInterval(() => {
  refreshResult();
  refreshProgress();
}, 800);
render();
