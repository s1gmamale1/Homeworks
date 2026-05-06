// frontend/js/taskboard.js
// Kanban-style internal task board: side-by-side columns, drag-and-drop
// reassign + reorder, status toggle, type pill, subtask/attachment meta,
// optional cover image, dynamic columns, bottom dock.

function t(key, fallback) {
  if (window.i18n && typeof window.i18n.t === "function") {
    return window.i18n.t(key, fallback);
  }
  return fallback != null ? fallback : key;
}

function escapeHtml(str) {
  return String(str ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

// Validate cover URL — only http(s) is rendered as <img>; anything else is dropped.
// Prevents javascript: / data: vectors from sneaking through user input.
function safeCoverUrl(raw) {
  if (typeof raw !== "string") return "";
  const trimmed = raw.trim();
  if (!trimmed) return "";
  try {
    const u = new URL(trimmed, window.location.origin);
    if (u.protocol === "http:" || u.protocol === "https:") return u.href;
  } catch (_) { /* fall through */ }
  return "";
}

// Eight-colour accent palette used both for the column dot/border and as
// "New person" swatches in the user modal. The Issues column uses --accent.
const COLOR_PALETTE = [
  "#22c55e", // green
  "#eab308", // gold
  "#a855f7", // purple
  "#3b82f6", // blue
  "#f97316", // orange
  "#ec4899", // pink
  "#06b6d4", // cyan
  "#ef4444", // red
];

function colorForUser(user, fallbackIndex) {
  if (user && typeof user.color === "string" && /^#[0-9a-fA-F]{6}$/.test(user.color)) {
    return user.color;
  }
  return COLOR_PALETTE[fallbackIndex % COLOR_PALETTE.length];
}

// ── State ───────────────────────────────────────────────────────────────────
const state = {
  users: [],
  tasks: [],
  draggedTaskId: null,
  editingTaskId: null,
  editingUserId: null,
  // Pre-selected assignee when "Add card" was clicked on a column footer
  // (null means Issues; -1 means unset / fall back to Issues).
  newTaskAssignee: null,
  newUserColor: COLOR_PALETTE[0],
};

// ── DOM refs ────────────────────────────────────────────────────────────────
const els = {
  board: document.getElementById("tb-board"),
  newTaskBtn: document.getElementById("tb-new-task"),
  newUserBtn: document.getElementById("tb-new-user"),
  taskModal: document.getElementById("tb-task-modal"),
  userModal: document.getElementById("tb-user-modal"),
  closeTaskModal: document.getElementById("tb-close-task-modal"),
  cancelTask: document.getElementById("tb-cancel-task"),
  saveTask: document.getElementById("tb-save-task"),
  closeUserModal: document.getElementById("tb-close-user-modal"),
  cancelUser: document.getElementById("tb-cancel-user"),
  saveUser: document.getElementById("tb-save-user"),
  taskTitleInput: document.getElementById("tb-task-title"),
  taskDescInput: document.getElementById("tb-task-desc"),
  taskTypeInput: document.getElementById("tb-task-type"),
  taskAssigneeInput: document.getElementById("tb-task-assignee"),
  taskSubtotalInput: document.getElementById("tb-task-subtotal"),
  taskSubdoneInput: document.getElementById("tb-task-subdone"),
  taskAttachInput: document.getElementById("tb-task-attach"),
  taskCoverInput: document.getElementById("tb-task-cover"),
  userNameInput: document.getElementById("tb-user-name"),
  userColorSwatches: document.getElementById("tb-user-color-swatches"),
  switchBoardsBtn: document.getElementById("tb-switch-boards"),
};

// ── API helpers ─────────────────────────────────────────────────────────────
const request = window.API?.request ?? window.request;

async function apiListUsers() {
  return request("/api/taskboard/users");
}
async function apiCreateUser(body) {
  return request("/api/taskboard/users", { method: "POST", body });
}
async function apiPatchUser(id, patch) {
  return request(`/api/taskboard/users/${id}`, { method: "PATCH", body: patch });
}
async function apiArchiveUser(id) {
  return request(`/api/taskboard/users/${id}`, { method: "DELETE" });
}
async function apiListAllTasks() {
  return request("/api/taskboard/tasks");
}
async function apiCreateTask(body) {
  return request("/api/taskboard/tasks", { method: "POST", body });
}
async function apiPatchTask(id, patch) {
  return request(`/api/taskboard/tasks/${id}`, { method: "PATCH", body: patch });
}
async function apiArchiveTask(id) {
  return request(`/api/taskboard/tasks/${id}`, { method: "DELETE" });
}

// ── Render ──────────────────────────────────────────────────────────────────
function tasksFor(assigneeId) {
  return state.tasks
    .filter((task) =>
      assigneeId === null ? task.assignee_id == null : task.assignee_id === assigneeId
    )
    .sort((a, b) => (a.position ?? 0) - (b.position ?? 0));
}

function renderBoard() {
  if (!els.board) return;
  els.board.innerHTML = "";

  const sortedUsers = [...state.users].sort(
    (a, b) => (a.position ?? 0) - (b.position ?? 0)
  );

  // Issues column (pinned first), then one column per user.
  const columns = [
    {
      id: "issues",
      assigneeId: null,
      title: t("taskboard.issues_tab", "Issues"),
      accent: "var(--accent, #006FE0)",
      isIssues: true,
    },
    ...sortedUsers.map((u, i) => ({
      id: String(u.id),
      assigneeId: u.id,
      title: u.name,
      accent: colorForUser(u, i),
      user: u,
    })),
  ];

  const frag = document.createDocumentFragment();
  columns.forEach((col) => frag.appendChild(renderColumn(col)));
  els.board.appendChild(frag);
}

function renderColumn(col) {
  const wrap = document.createElement("div");
  wrap.className = "tb-column";
  wrap.dataset.colId = col.id;
  wrap.dataset.assigneeId = col.assigneeId == null ? "" : String(col.assigneeId);
  wrap.style.setProperty("--tb-accent", col.accent);
  wrap.setAttribute("role", "listitem");

  const tasks = tasksFor(col.assigneeId);

  // Header
  const header = document.createElement("div");
  header.className = "tb-col-header";
  header.innerHTML = `
    <h2 class="tb-col-title">
      <span class="tb-col-dot" aria-hidden="true"></span>
      <span class="tb-col-name">${escapeHtml(col.title)}</span>
    </h2>
    <span class="tb-col-count">${tasks.length}</span>
  `;
  if (!col.isIssues && col.user) {
    const actions = document.createElement("div");
    actions.className = "tb-col-actions";
    actions.innerHTML = `
      <button class="tb-col-action js-edit-user" type="button"
        aria-label="${escapeHtml(t("taskboard.edit_person", "Edit person"))}"
        title="${escapeHtml(t("taskboard.edit_person", "Edit person"))}">✎</button>
      <button class="tb-col-action danger js-archive-user" type="button"
        aria-label="${escapeHtml(t("taskboard.archive_person", "Archive person"))}"
        title="${escapeHtml(t("taskboard.archive_person", "Archive person"))}">×</button>
    `;
    actions.querySelector(".js-edit-user").addEventListener("click", () => editUser(col.user));
    actions.querySelector(".js-archive-user").addEventListener("click", () => archiveUser(col.user.id));
    header.appendChild(actions);
  }
  wrap.appendChild(header);

  // Body (drop zone)
  const body = document.createElement("div");
  body.className = "tb-col-body";
  body.dataset.assigneeId = col.assigneeId == null ? "" : String(col.assigneeId);

  if (tasks.length === 0) {
    const empty = document.createElement("div");
    empty.className = "tb-empty-row";
    empty.textContent = t("taskboard.empty_text", "No tasks here yet — drag one over.");
    body.appendChild(empty);
  } else {
    tasks.forEach((task) => body.appendChild(renderCard(task, col.accent)));
  }

  wireColumnDnd(body, col.assigneeId);
  wrap.appendChild(body);

  // Footer
  const footer = document.createElement("div");
  footer.className = "tb-col-footer";
  const addBtn = document.createElement("button");
  addBtn.type = "button";
  addBtn.className = "tb-add-card";
  addBtn.textContent = t("taskboard.add_card", "+ Add a card");
  addBtn.addEventListener("click", () => openTaskModal({ assignee_id: col.assigneeId }));
  footer.appendChild(addBtn);
  wrap.appendChild(footer);

  return wrap;
}

function renderCard(task, accent) {
  const card = document.createElement("div");
  card.className = "tb-card";
  if (task.status === "done") card.classList.add("is-done");
  card.draggable = true;
  card.dataset.taskId = String(task.id);
  if (accent) card.style.setProperty("--tb-accent", accent);

  const cover = safeCoverUrl(task.cover_url);
  const subTotal = Number(task.subtask_total) || 0;
  const subDone = Number(task.subtask_done) || 0;
  const attach = Number(task.attachment_count) || 0;
  const taskType = (task.task_type || "general").toLowerCase();
  const typeLabel = t(`taskboard.type.${taskType}`, taskType);
  const checkAriaKey = task.status === "done"
    ? t("taskboard.mark_open", "Mark as not done")
    : t("taskboard.mark_done", "Mark as done");

  card.innerHTML = `
    ${cover ? `<img class="tb-card-cover" src="${escapeHtml(cover)}" alt="" loading="lazy">` : ""}
    <div class="tb-card-top">
      <span class="tb-type-pill">${escapeHtml(typeLabel)}</span>
      <button class="tb-card-check ${task.status === "done" ? "is-done" : ""}" type="button"
        aria-pressed="${task.status === "done" ? "true" : "false"}"
        aria-label="${escapeHtml(checkAriaKey)}"
        title="${escapeHtml(checkAriaKey)}">✓</button>
    </div>
    <h3 class="tb-card-title">${escapeHtml(task.title)}</h3>
    ${task.description ? `<p class="tb-card-desc">${escapeHtml(task.description.slice(0, 140))}</p>` : ""}
    <div class="tb-card-meta">
      ${subTotal > 0
        ? `<span class="tb-meta-item" title="${escapeHtml(t("taskboard.subtasks_label", "Sub-tasks"))}">☑ ${subDone}/${subTotal}</span>`
        : ""}
      ${attach > 0
        ? `<span class="tb-meta-item" title="${escapeHtml(t("taskboard.attachments_label", "Attachments"))}">📎 ${attach}</span>`
        : ""}
      <span class="tb-card-actions">
        <button class="tb-card-action js-edit" type="button"
          aria-label="${escapeHtml(t("taskboard.edit", "Edit"))}"
          title="${escapeHtml(t("taskboard.edit", "Edit"))}">✎</button>
        <button class="tb-card-action danger js-archive" type="button"
          aria-label="${escapeHtml(t("taskboard.archive", "Archive"))}"
          title="${escapeHtml(t("taskboard.archive", "Archive"))}">🗑</button>
      </span>
    </div>
  `;

  card.querySelector(".tb-card-check").addEventListener("click", (e) => {
    e.stopPropagation();
    toggleStatus(task.id);
  });
  card.querySelector(".js-edit").addEventListener("click", (e) => {
    e.stopPropagation();
    editTask(task.id);
  });
  card.querySelector(".js-archive").addEventListener("click", (e) => {
    e.stopPropagation();
    archiveTask(task.id);
  });

  wireCardDnd(card, task);
  return card;
}

// ── Drag-drop ───────────────────────────────────────────────────────────────
function wireCardDnd(card, task) {
  card.addEventListener("dragstart", (e) => {
    state.draggedTaskId = task.id;
    e.dataTransfer.effectAllowed = "move";
    // Some browsers require setData for the drag to start cleanly.
    try { e.dataTransfer.setData("text/plain", String(task.id)); } catch (_) {}
    card.classList.add("is-dragging");
  });
  card.addEventListener("dragend", () => {
    state.draggedTaskId = null;
    card.classList.remove("is-dragging");
    document.querySelectorAll(".tb-card.is-drop-above, .tb-card.is-drop-below")
      .forEach((c) => c.classList.remove("is-drop-above", "is-drop-below"));
    document.querySelectorAll(".tb-col-body.is-drop-target")
      .forEach((b) => b.classList.remove("is-drop-target"));
  });

  card.addEventListener("dragover", (e) => {
    e.preventDefault();
    e.stopPropagation();
    e.dataTransfer.dropEffect = "move";
    const rect = card.getBoundingClientRect();
    const mid = rect.top + rect.height / 2;
    card.classList.remove("is-drop-above", "is-drop-below");
    if (e.clientY < mid) card.classList.add("is-drop-above");
    else card.classList.add("is-drop-below");
  });
  card.addEventListener("dragleave", () => {
    card.classList.remove("is-drop-above", "is-drop-below");
  });

  card.addEventListener("drop", (e) => {
    e.preventDefault();
    e.stopPropagation();
    card.classList.remove("is-drop-above", "is-drop-below");
    if (state.draggedTaskId == null) return;
    if (state.draggedTaskId === task.id) return;

    const body = card.parentElement;
    if (!body) return;
    const colAssignee = body.dataset.assigneeId === "" ? null : Number(body.dataset.assigneeId);

    const cards = Array.from(body.querySelectorAll(".tb-card"));
    const targetIdx = cards.indexOf(card);
    if (targetIdx === -1) return;

    const rect = card.getBoundingClientRect();
    const mid = rect.top + rect.height / 2;
    let position = e.clientY < mid ? targetIdx : targetIdx + 1;

    const dragged = state.tasks.find((t) => t.id === state.draggedTaskId);
    if (!dragged) return;
    const sameColumn =
      (dragged.assignee_id == null && colAssignee == null) ||
      dragged.assignee_id === colAssignee;
    if (sameColumn && dragged.position < position) position -= 1;

    moveTask(state.draggedTaskId, { assignee_id: colAssignee, position });
  });
}

function wireColumnDnd(body, assigneeId) {
  body.addEventListener("dragover", (e) => {
    // Only trigger column-level drop when the cursor isn't over a card.
    if (e.target.closest(".tb-card")) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    body.classList.add("is-drop-target");
  });
  body.addEventListener("dragleave", (e) => {
    if (e.target === body) body.classList.remove("is-drop-target");
  });
  body.addEventListener("drop", (e) => {
    if (e.target.closest(".tb-card")) return;  // card-level handler took it
    e.preventDefault();
    body.classList.remove("is-drop-target");
    if (state.draggedTaskId == null) return;
    moveTask(state.draggedTaskId, { assignee_id: assigneeId, position: 999_999 });
  });
}

// ── Mutations ───────────────────────────────────────────────────────────────
async function moveTask(id, patch) {
  // Optimistic: mutate local state, re-render, then PATCH; on failure re-sync.
  const task = state.tasks.find((t) => t.id === id);
  if (task) {
    if ("assignee_id" in patch) task.assignee_id = patch.assignee_id;
    if ("position" in patch) task.position = patch.position;
    renderBoard();
  }
  try {
    const updated = await apiPatchTask(id, patch);
    if (updated && task) Object.assign(task, updated);
    await syncState();
  } catch (err) {
    console.error("moveTask failed", err);
    await syncState();
  }
}

async function toggleStatus(id) {
  const task = state.tasks.find((t) => t.id === id);
  if (!task) return;
  const next = task.status === "done" ? "open" : "done";
  task.status = next;
  renderBoard();
  try {
    const updated = await apiPatchTask(id, { status: next });
    if (updated) Object.assign(task, updated);
  } catch (err) {
    console.error("toggleStatus failed", err);
    await syncState();
  }
}

function openTaskModal({ assignee_id = null } = {}) {
  state.editingTaskId = null;
  state.newTaskAssignee = assignee_id;
  if (els.taskTitleInput) els.taskTitleInput.value = "";
  if (els.taskDescInput) els.taskDescInput.value = "";
  if (els.taskTypeInput) els.taskTypeInput.value = "general";
  if (els.taskSubtotalInput) els.taskSubtotalInput.value = "";
  if (els.taskSubdoneInput) els.taskSubdoneInput.value = "";
  if (els.taskAttachInput) els.taskAttachInput.value = "";
  if (els.taskCoverInput) els.taskCoverInput.value = "";
  populateAssigneeSelect(assignee_id);
  updateTaskModalTitle();
  if (els.taskModal) els.taskModal.showModal();
}

function editTask(id) {
  const task = state.tasks.find((t) => t.id === id);
  if (!task) return;
  state.editingTaskId = id;
  state.newTaskAssignee = task.assignee_id ?? null;
  if (els.taskTitleInput) els.taskTitleInput.value = task.title || "";
  if (els.taskDescInput) els.taskDescInput.value = task.description || "";
  if (els.taskTypeInput) els.taskTypeInput.value = task.task_type || "general";
  if (els.taskSubtotalInput) els.taskSubtotalInput.value = task.subtask_total || "";
  if (els.taskSubdoneInput) els.taskSubdoneInput.value = task.subtask_done || "";
  if (els.taskAttachInput) els.taskAttachInput.value = task.attachment_count || "";
  if (els.taskCoverInput) els.taskCoverInput.value = task.cover_url || "";
  populateAssigneeSelect(task.assignee_id ?? null);
  updateTaskModalTitle();
  if (els.taskModal) els.taskModal.showModal();
}

function populateAssigneeSelect(selected) {
  if (!els.taskAssigneeInput) return;
  els.taskAssigneeInput.innerHTML = "";
  const issuesOpt = document.createElement("option");
  issuesOpt.value = "";
  issuesOpt.textContent = t("taskboard.issues_tab", "Issues");
  els.taskAssigneeInput.appendChild(issuesOpt);
  [...state.users]
    .sort((a, b) => (a.position ?? 0) - (b.position ?? 0))
    .forEach((u) => {
      const opt = document.createElement("option");
      opt.value = String(u.id);
      opt.textContent = u.name;
      els.taskAssigneeInput.appendChild(opt);
    });
  els.taskAssigneeInput.value =
    selected == null ? "" : String(selected);
}

async function archiveTask(id) {
  const confirmed = window.confirm(t("taskboard.confirm_archive_task", "Archive this task?"));
  if (!confirmed) return;
  await apiArchiveTask(id);
  await syncState();
}

function editUser(user) {
  state.editingUserId = user.id;
  state.newUserColor = user.color || colorForUser(user, state.users.indexOf(user));
  if (els.userNameInput) els.userNameInput.value = user.name || "";
  renderColorSwatches();
  updateUserModalTitle();
  if (els.userModal) els.userModal.showModal();
}

async function archiveUser(id) {
  const confirmed = window.confirm(
    t("taskboard.confirm_archive_user", "Archive this person? Their tasks will return to Issues.")
  );
  if (!confirmed) return;
  await apiArchiveUser(id);
  await syncState();
}

// ── Modal helpers ───────────────────────────────────────────────────────────
function updateTaskModalTitle() {
  const titleEl = document.getElementById("tb-task-modal-title");
  if (!titleEl) return;
  titleEl.textContent =
    state.editingTaskId != null
      ? t("taskboard.task_modal_title_edit", "Edit task")
      : t("taskboard.task_modal_title", "New task");
}
function updateUserModalTitle() {
  const titleEl = document.getElementById("tb-user-modal-title");
  if (!titleEl) return;
  titleEl.textContent =
    state.editingUserId != null
      ? t("taskboard.user_modal_title_edit", "Edit person")
      : t("taskboard.user_modal_title", "New person");
}

function renderColorSwatches() {
  if (!els.userColorSwatches) return;
  els.userColorSwatches.innerHTML = "";
  COLOR_PALETTE.forEach((color) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "tb-color-swatch" + (color === state.newUserColor ? " is-selected" : "");
    btn.style.background = color;
    btn.dataset.color = color;
    btn.setAttribute("role", "radio");
    btn.setAttribute("aria-checked", color === state.newUserColor ? "true" : "false");
    btn.setAttribute("aria-label", color);
    btn.addEventListener("click", () => {
      state.newUserColor = color;
      renderColorSwatches();
    });
    els.userColorSwatches.appendChild(btn);
  });
}

// ── Button wiring ───────────────────────────────────────────────────────────
function wireButtons() {
  if (els.newTaskBtn) {
    els.newTaskBtn.addEventListener("click", () => openTaskModal({ assignee_id: null }));
  }

  if (els.newUserBtn) {
    els.newUserBtn.addEventListener("click", () => {
      state.editingUserId = null;
      state.newUserColor = COLOR_PALETTE[state.users.length % COLOR_PALETTE.length];
      if (els.userNameInput) els.userNameInput.value = "";
      renderColorSwatches();
      updateUserModalTitle();
      if (els.userModal) els.userModal.showModal();
    });
  }

  [els.closeTaskModal, els.cancelTask].forEach((btn) => {
    if (btn) btn.addEventListener("click", () => { if (els.taskModal) els.taskModal.close(); });
  });
  [els.closeUserModal, els.cancelUser].forEach((btn) => {
    if (btn) btn.addEventListener("click", () => { if (els.userModal) els.userModal.close(); });
  });

  if (els.saveTask) {
    els.saveTask.addEventListener("click", async () => {
      const title = els.taskTitleInput ? els.taskTitleInput.value.trim() : "";
      if (!title) return;

      const description = els.taskDescInput ? els.taskDescInput.value.trim() : "";
      const task_type = els.taskTypeInput ? els.taskTypeInput.value : "general";
      const assigneeRaw = els.taskAssigneeInput ? els.taskAssigneeInput.value : "";
      const assignee_id = assigneeRaw === "" ? null : Number(assigneeRaw);
      const subtask_total = Number(els.taskSubtotalInput?.value) || 0;
      let subtask_done = Number(els.taskSubdoneInput?.value) || 0;
      if (subtask_done > subtask_total) subtask_done = subtask_total;
      const attachment_count = Number(els.taskAttachInput?.value) || 0;
      const cover_url = els.taskCoverInput ? els.taskCoverInput.value.trim() : "";

      const body = {
        title,
        description,
        task_type,
        subtask_total,
        subtask_done,
        attachment_count,
        cover_url: cover_url || null,
      };

      if (state.editingTaskId != null) {
        await apiPatchTask(state.editingTaskId, { ...body, assignee_id });
      } else {
        await apiCreateTask({ ...body, assignee_id });
      }
      if (els.taskModal) els.taskModal.close();
      await syncState();
    });
  }

  if (els.saveUser) {
    els.saveUser.addEventListener("click", async () => {
      const name = els.userNameInput ? els.userNameInput.value.trim() : "";
      if (!name) return;

      const color = state.newUserColor || null;

      if (state.editingUserId != null) {
        await apiPatchUser(state.editingUserId, { name, color });
      } else {
        await apiCreateUser({ name, color });
      }
      if (els.userModal) els.userModal.close();
      await syncState();
    });
  }

  if (els.switchBoardsBtn) {
    els.switchBoardsBtn.addEventListener("click", () => {
      // Visual placeholder — no second board exists yet.
      window.alert(t("taskboard.switch_boards_placeholder",
        "Only one board exists right now. Multi-board switching is coming soon."));
    });
  }
}

// ── Boot ────────────────────────────────────────────────────────────────────
async function syncState() {
  const [users, tasks] = await Promise.all([apiListUsers(), apiListAllTasks()]);
  state.users = users;
  state.tasks = tasks;
  renderBoard();
}

async function init() {
  await syncState();
  wireButtons();
}

await init();
