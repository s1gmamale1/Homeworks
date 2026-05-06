// frontend/js/taskboard.js
// Taskboard page — kanban-style tabs with drag-drop reassignment.

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

// ── State ───────────────────────────────────────────────────────────────────
const state = {
  users: [],
  tasks: [],
  activeTabId: null,
  draggedTaskId: null,
  dropTarget: null,
  editingTaskId: null,
  editingUserId: null,
};

// ── DOM refs ────────────────────────────────────────────────────────────────
const els = {
  tabs: document.getElementById("tb-tabs"),
  panel: document.getElementById("tb-panel"),
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
  userNameInput: document.getElementById("tb-user-name"),
};

// ── API helpers ─────────────────────────────────────────────────────────────
const request = window.API?.request ?? window.request;

async function apiListUsers() {
  return request("/api/taskboard/users");
}

async function apiCreateUser(name) {
  return request("/api/taskboard/users", { method: "POST", body: { name } });
}

async function apiPatchUser(id, patch) {
  return request(`/api/taskboard/users/${id}`, { method: "PATCH", body: patch });
}

async function apiArchiveUser(id) {
  return request(`/api/taskboard/users/${id}`, { method: "DELETE" });
}

async function apiListTasks(assigneeId) {
  const qs = assigneeId === null ? "?assignee_id=null" : "";
  return request(`/api/taskboard/tasks${qs}`);
}

async function apiListAllTasks() {
  return request("/api/taskboard/tasks");
}

async function apiCreateTask(title, description = "") {
  return request("/api/taskboard/tasks", { method: "POST", body: { title, description } });
}

async function apiPatchTask(id, patch) {
  return request(`/api/taskboard/tasks/${id}`, { method: "PATCH", body: patch });
}

async function apiArchiveTask(id) {
  return request(`/api/taskboard/tasks/${id}`, { method: "DELETE" });
}

// ── Render ──────────────────────────────────────────────────────────────────
function renderTabs() {
  if (!els.tabs) return;
  els.tabs.innerHTML = "";

  // Issues tab
  const issuesCount = state.tasks.filter((t) => t.assignee_id === null).length;
  const issuesTab = document.createElement("button");
  issuesTab.className = "library-tab" + (state.activeTabId === null ? " is-active" : "");
  issuesTab.dataset.tabId = "issues";
  issuesTab.role = "tab";
  issuesTab.setAttribute("aria-selected", state.activeTabId === null ? "true" : "false");
  issuesTab.innerHTML = `${escapeHtml(t("taskboard.issues_tab", "Issues"))} <span class="tab-count">${issuesCount}</span>`;
  issuesTab.addEventListener("click", () => onTabClick("issues"));
  wireTabDnd(issuesTab);
  els.tabs.appendChild(issuesTab);

  // User tabs
  const users = [...state.users].sort((a, b) => (a.position ?? 0) - (b.position ?? 0));
  users.forEach((user) => {
    const tab = document.createElement("button");
    tab.className = "library-tab" + (state.activeTabId === user.id ? " is-active" : "");
    tab.dataset.tabId = String(user.id);
    tab.role = "tab";
    tab.setAttribute("aria-selected", state.activeTabId === user.id ? "true" : "false");
    tab.innerHTML = `${escapeHtml(user.name)} <span class="tab-count">${user.task_count ?? 0}</span>`;
    tab.addEventListener("click", () => onTabClick(user.id));
    wireTabDnd(tab);
    els.tabs.appendChild(tab);
  });
}

function renderPanel() {
  if (!els.panel) return;
  els.panel.innerHTML = "";
  els.panel.setAttribute("aria-label", t("taskboard.panel_aria", "Task list"));

  const filtered = state.tasks
    .filter((t) => {
      if (state.activeTabId === null) return t.assignee_id === null;
      return t.assignee_id === state.activeTabId;
    })
    .sort((a, b) => (a.position ?? 0) - (b.position ?? 0));

  if (filtered.length === 0) {
    const empty = document.createElement("div");
    empty.className = "taskboard-empty";
    empty.textContent = t("taskboard.empty_text", "No tasks here yet — drag one over.");
    els.panel.appendChild(empty);
    return;
  }

  const frag = document.createDocumentFragment();
  filtered.forEach((task) => frag.appendChild(renderCard(task)));
  els.panel.appendChild(frag);
}

function renderCard(task) {
  const card = document.createElement("div");
  card.className = "taskboard-card";
  card.draggable = true;
  card.dataset.taskId = String(task.id);

  const descPreview = task.description ? task.description.slice(0, 120) : "";

  card.innerHTML = `
    <div class="card-body">
      <h4 class="card-title">${escapeHtml(task.title)}</h4>
      ${descPreview ? `<p class="card-desc">${escapeHtml(descPreview)}</p>` : ""}
    </div>
    <div class="card-menu">
      <button class="card-menu-toggle" type="button" aria-label="${escapeHtml(t("taskboard.more_actions", "Actions"))}">⋮</button>
      <div class="card-menu-dropdown hidden">
        <button class="card-menu-item js-edit" type="button">${escapeHtml(t("taskboard.edit"))}</button>
        <button class="card-menu-item js-archive danger" type="button">${escapeHtml(t("taskboard.archive"))}</button>
      </div>
    </div>
  `;

  const menuToggle = card.querySelector(".card-menu-toggle");
  const menuDropdown = card.querySelector(".card-menu-dropdown");

  menuToggle.addEventListener("click", (e) => {
    e.stopPropagation();
    els.panel.querySelectorAll(".card-menu-dropdown").forEach((d) => {
      if (d !== menuDropdown) d.classList.add("hidden");
    });
    menuDropdown.classList.toggle("hidden");
  });

  card.querySelector(".js-edit").addEventListener("click", (e) => {
    e.stopPropagation();
    menuDropdown.classList.add("hidden");
    editTask(task.id);
  });

  card.querySelector(".js-archive").addEventListener("click", (e) => {
    e.stopPropagation();
    menuDropdown.classList.add("hidden");
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
    card.classList.add("is-dragging");
  });

  card.addEventListener("dragend", () => {
    state.draggedTaskId = null;
    card.classList.remove("is-dragging");
  });

  card.addEventListener("dragover", (e) => {
    e.preventDefault();
    const rect = card.getBoundingClientRect();
    const mid = rect.top + rect.height / 2;
    card.classList.remove("is-drop-above", "is-drop-below");
    if (e.clientY < mid) {
      card.classList.add("is-drop-above");
    } else {
      card.classList.add("is-drop-below");
    }
  });

  card.addEventListener("drop", (e) => {
    e.preventDefault();
    card.classList.remove("is-drop-above", "is-drop-below");
    if (state.draggedTaskId == null) return;

    const cards = Array.from(els.panel.querySelectorAll(".taskboard-card"));
    const index = cards.indexOf(card);
    if (index === -1) return;

    const rect = card.getBoundingClientRect();
    const mid = rect.top + rect.height / 2;
    const targetPos = e.clientY < mid ? index : index + 1;

    moveTask(state.draggedTaskId, { position: targetPos });
  });
}

function wireTabDnd(tab) {
  tab.addEventListener("dragover", (e) => {
    e.preventDefault();
    tab.classList.add("is-drop-target");
  });

  tab.addEventListener("dragleave", () => {
    tab.classList.remove("is-drop-target");
  });

  tab.addEventListener("drop", (e) => {
    e.preventDefault();
    tab.classList.remove("is-drop-target");
    if (state.draggedTaskId == null) return;

    const tabId = tab.dataset.tabId;
    const assigneeId = tabId === "issues" ? null : Number(tabId);
    moveTask(state.draggedTaskId, { assignee_id: assigneeId, position: 999_999 });
  });
}

// ── Mutations ───────────────────────────────────────────────────────────────
async function moveTask(id, patch) {
  const task = state.tasks.find((t) => t.id === id);
  if (task) {
    Object.assign(task, patch);
    renderPanel();
  }
  try {
    await apiPatchTask(id, patch);
  } catch (err) {
    console.error("moveTask failed", err);
    await syncState();
  }
}

async function createTask({ title, description = "" }) {
  await apiCreateTask(title, description);
  await syncState();
  state.activeTabId = null;
  renderTabs();
  renderPanel();
}

async function createUser({ name }) {
  const user = await apiCreateUser(name);
  await syncState();
  const newUser = state.users.find((u) => u.id === user?.id) || state.users.find((u) => u.name === name) || null;
  state.activeTabId = newUser ? newUser.id : null;
  renderTabs();
  renderPanel();
}

function editTask(id) {
  const task = state.tasks.find((t) => t.id === id);
  if (!task) return;
  state.editingTaskId = id;
  if (els.taskTitleInput) els.taskTitleInput.value = task.title || "";
  if (els.taskDescInput) els.taskDescInput.value = task.description || "";
  updateTaskModalTitle();
  if (els.taskModal) els.taskModal.showModal();
}

async function archiveTask(id) {
  const confirmed = window.confirm(t("taskboard.confirm_archive_task", "Archive this task?"));
  if (!confirmed) return;
  await apiArchiveTask(id);
  await syncState();
}

async function archiveUser(id) {
  const confirmed = window.confirm(t("taskboard.confirm_archive_user", "Archive this person? Their tasks will return to Issues."));
  if (!confirmed) return;
  await apiArchiveUser(id);
  await syncState();
}

// ── Modal helpers ───────────────────────────────────────────────────────────
function updateTaskModalTitle() {
  const titleEl = document.getElementById("tb-task-modal-title");
  if (!titleEl) return;
  titleEl.textContent = state.editingTaskId != null
    ? t("taskboard.task_modal_title_edit", "Edit task")
    : t("taskboard.task_modal_title", "New task");
}

function updateUserModalTitle() {
  const titleEl = document.getElementById("tb-user-modal-title");
  if (!titleEl) return;
  titleEl.textContent = state.editingUserId != null
    ? t("taskboard.user_modal_title_edit", "Edit person")
    : t("taskboard.user_modal_title", "New person");
}

function onTabClick(tabId) {
  state.activeTabId = tabId === "issues" ? null : tabId;
  renderTabs();
  renderPanel();
}

// ── Button wiring ───────────────────────────────────────────────────────────
function wireButtons() {
  if (els.newTaskBtn) {
    els.newTaskBtn.addEventListener("click", () => {
      state.editingTaskId = null;
      if (els.taskTitleInput) els.taskTitleInput.value = "";
      if (els.taskDescInput) els.taskDescInput.value = "";
      updateTaskModalTitle();
      if (els.taskModal) els.taskModal.showModal();
    });
  }

  if (els.newUserBtn) {
    els.newUserBtn.addEventListener("click", () => {
      state.editingUserId = null;
      if (els.userNameInput) els.userNameInput.value = "";
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
      const description = els.taskDescInput ? els.taskDescInput.value.trim() : "";
      if (!title) return;

      if (state.editingTaskId != null) {
        await apiPatchTask(state.editingTaskId, { title, description });
        if (els.taskModal) els.taskModal.close();
        await syncState();
      } else {
        if (els.taskModal) els.taskModal.close();
        await createTask({ title, description });
      }
    });
  }

  if (els.saveUser) {
    els.saveUser.addEventListener("click", async () => {
      const name = els.userNameInput ? els.userNameInput.value.trim() : "";
      if (!name) return;

      if (state.editingUserId != null) {
        await apiPatchUser(state.editingUserId, { name });
        if (els.userModal) els.userModal.close();
        await syncState();
      } else {
        if (els.userModal) els.userModal.close();
        await createUser({ name });
      }
    });
  }

  // Close card menus on outside click
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".card-menu")) {
      els.panel.querySelectorAll(".card-menu-dropdown").forEach((d) => d.classList.add("hidden"));
    }
  });
}

// ── Boot ────────────────────────────────────────────────────────────────────
async function syncState() {
  const [users, tasks] = await Promise.all([apiListUsers(), apiListAllTasks()]);
  state.users = users;
  state.tasks = tasks;
  renderTabs();
  renderPanel();
}

async function init() {
  await syncState();
  state.activeTabId = null;
  renderTabs();
  renderPanel();
  wireButtons();
}

await init();
