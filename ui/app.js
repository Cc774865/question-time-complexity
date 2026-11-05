const files = [];
let classification = emptyClassification();
const notes = new Map();

const drop = document.querySelector("#drop");
const picker = document.querySelector("#picker");
const fileList = document.querySelector("#file-list");
const clearInput = document.querySelector("#clear-input");
const startWork = document.querySelector("#start-work");
const outputBody = document.querySelector("#output-body");
const reviewBody = document.querySelector("#review-body");
const progress = document.querySelector("#progress");
const progressBar = document.querySelector("#progress-bar");
const progressFill = document.querySelector("#progress-fill");
const progressLabel = document.querySelector("#progress-label");
const inputCount = document.querySelector("#input-count");
const reviewCount = document.querySelector("#review-count");

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
  if (!files.length) return;
  startWork.disabled = true;
  startWork.textContent = "已开始";
  const names = files.map((file) => file.name);
  fetch("/api/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ files: names }),
  })
    .then(() => showProgress({ running: true, percent: 5, label: "已开始" }))
    .catch(() => {
      startWork.disabled = false;
      startWork.textContent = "开始工作";
    });
});

clearInput.addEventListener("click", () => {
  if (!onServer) {
    files.splice(0, files.length);
    render();
    return;
  }
  fetch("/api/files", { method: "DELETE" }).then(() => refreshFiles());
});

function emptyClassification() {
  return { document: null, review: [] };
}

let onServer = false;
let resultStamp = "";

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
  const visible = Boolean(data.running) || percent > 0;
  progress.hidden = !visible;
  progressBar.setAttribute("aria-valuenow", String(percent));
  progressFill.style.width = `${percent}%`;
  progressLabel.textContent = data.label || "";
  if (data.running && startWork.textContent !== "已开始") {
    startWork.disabled = true;
    startWork.textContent = "已开始";
  }
}

function refreshResult() {
  return fetch("/api/result")
    .then((response) => {
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
  renderReview();
}

function renderInput() {
  inputCount.textContent = `${files.length} 个文件`;
  clearInput.disabled = files.length === 0;
  if (startWork.textContent !== "已开始") startWork.disabled = files.length === 0;
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

function renderOutput() {
  outputBody.replaceChildren();
  const doc = classification.document;
  if (!doc) {
    outputBody.append(emptyLine("分档后会给出一个文件。"));
    return;
  }
  const name = doc.filename || LessonFile.filename(doc);
  const row = document.createElement("div");
  row.className = "out-row";
  const button = document.createElement("button");
  button.type = "button";
  button.className = "small-btn";
  button.textContent = "下载";
  button.addEventListener("click", () => downloadReadyFile(name));
  row.append(stamp("DOCX"), named(name, "out-name"), sized(doc.bytes || 0), button);
  outputBody.append(row);
}

function renderReview() {
  const items = classification.review;
  reviewCount.textContent = `${items.length} 道`;
  reviewBody.replaceChildren();
  if (items.length === 0) {
    reviewBody.append(emptyLine("没有待审核的题目。"));
    return;
  }
  const list = document.createElement("ul");
  list.className = "review-list";
  for (const [index, item] of items.entries()) {
    list.append(reviewCard(item, index));
  }
  reviewBody.append(list);
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

function downloadReadyFile(name) {
  fetch("/api/output")
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
  const hasDocument = Boolean(
    next.paragraphs || next.sections || next.header || next.lessons || next.homework || next.promotion || next.filename,
  );
  classification = {
    document: hasDocument ? next : null,
    review: next.review || [],
  };
  notes.clear();
  render();
}

window.setClassification = setClassification;

refreshFiles().then(() => Promise.all([refreshResult(), refreshProgress()]));
setInterval(() => {
  refreshResult();
  refreshProgress();
}, 2000);
render();
