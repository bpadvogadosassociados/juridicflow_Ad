(function () {
  "use strict";

  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
      const cookies = document.cookie.split(";");
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === name + "=") {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  const CSRF = () => getCookie("csrftoken");

  function qs(sel, root) { return (root || document).querySelector(sel); }
  function qsa(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }

  function escapeHtml(s) {
    return String(s || "")
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function renderMarkdown(md) {
    let text = String(md || "");
    text = escapeHtml(text);

    text = text.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    text = text.replace(/\*(.+?)\*/g, "<em>$1</em>");
    text = text.replace(/`(.+?)`/g, "<code>$1</code>");

    const lines = text.split(/\r?\n/);
    let out = [];
    let inList = false;
    function closeList() {
      if (inList) { out.push("</ul>"); inList = false; }
    }
    for (const ln of lines) {
      const m = ln.match(/^\s*[-*]\s+(.*)$/);
      if (m) {
        if (!inList) { out.push("<ul>"); inList = true; }
        let item = m[1];
        const cb = item.match(/^\[(x| )\]\s+(.*)$/i);
        if (cb) {
          const checked = cb[1].toLowerCase() === "x" ? "checked" : "";
          item = `<label style="display:flex;gap:8px;align-items:flex-start;margin:0;">
                    <input type="checkbox" disabled ${checked} />
                    <span>${cb[2]}</span>
                  </label>`;
          out.push(`<li>${item}</li>`);
        } else {
          out.push(`<li>${item}</li>`);
        }
      } else if (ln.trim() === "") {
        closeList();
        out.push("<br/>");
      } else {
        closeList();
        out.push(`<div>${ln}</div>`);
      }
    }
    closeList();
    return out.join("\n");
  }

  async function apiFetch(url, opts) {
    const o = Object.assign({ headers: {} }, opts || {});
    o.credentials = "same-origin";

    o.headers = Object.assign({ "X-Requested-With": "XMLHttpRequest" }, o.headers || {});
    if (o.method && o.method.toUpperCase() !== "GET") {
      o.headers["X-CSRFToken"] = CSRF();
    }
    const res = await fetch(url, o);
    const ct = res.headers.get("content-type") || "";
    let data = null;
    if (ct.includes("application/json")) data = await res.json().catch(() => ({}));
    else data = await res.text().catch(() => "");
    return { ok: res.ok, status: res.status, data };
  }

  function toast(kind, msg) {
    if (window.toastr && typeof window.toastr[kind] === "function") {
      window.toastr[kind](msg);
      return;
    }
    console[kind === "error" ? "error" : "log"](msg);
  }

  function confirmDialog(title, text, onYes) {
    if (window.Swal) {
      window.Swal.fire({
        title: title || "Confirmar",
        text: text || "",
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "Sim",
        cancelButtonText: "Não",
        confirmButtonColor: "#dc3545",
        cancelButtonColor: "#0d6efd"
      }).then((r) => { if (r.isConfirmed) onYes(); });
      return;
    }
    if (window.confirm((title ? title + "\n\n" : "") + (text || ""))) onYes();
  }

  function debounce(fn, ms) {
    let t = null;
    return function (...args) {
      clearTimeout(t);
      t = setTimeout(() => fn.apply(this, args), ms);
    };
  }

  const PortalSearch = {
    init() {
      const form = qs("#navbar-search-form");
      if (!form) return;
      form.addEventListener("submit", (e) => { e.preventDefault(); this.run(); });

      const input = qs("#navbar-search-input");
      const panel = qs("#navbar-search-results");
      if (!input || !panel) return;

      input.addEventListener("input", debounce(() => {
        if (input.value.trim().length < 2) {
          panel.innerHTML = "";
          panel.classList.add("d-none");
          return;
        }
        this.run(true);
      }, 250));
    },

    async run(isLive) {
      const input = qs("#navbar-search-input");
      const panel = qs("#navbar-search-results");
      if (!input || !panel) return;
      const q = input.value.trim();
      if (!q) return;

      const { ok, data } = await apiFetch(`/app/api/search/?q=${encodeURIComponent(q)}`, { method: "GET" });
      if (!ok) { toast("error", "Falha na busca."); return; }

      const results = data.results || data || [];
      if (!results.length) {
        panel.innerHTML = `<div class="p-2 text-muted">Nenhum resultado.</div>`;
        panel.classList.remove("d-none");
        return;
      }

      panel.innerHTML = results.slice(0, 8).map((r) => {
        const type = escapeHtml(r.type || "item");
        const title = escapeHtml(r.title || r.name || r.number || "Resultado");
        const hint = escapeHtml(r.hint || "");
        const url = escapeHtml(r.url || "#");
        return `
          <a class="dropdown-item" href="${url}">
            <div class="d-flex justify-content-between">
              <span><span class="badge badge-secondary mr-2">${type}</span>${title}</span>
              <small class="text-muted">${hint}</small>
            </div>
          </a>`;
      }).join("");
      panel.classList.remove("d-none");

      if (!isLive) {
        const dd = qs("#navbar-search-dropdown");
        if (dd) dd.classList.add("show");
      }
    }
  };

  const PortalNotifications = {
    timer: null,
    intervalMs: 15000,

    init() {
      const btn = qs("#navbar-notif-btn");
      if (!btn) return;
      btn.addEventListener("click", () => this.refresh(true));
      this.refresh(false);
      this.start();
    },

    start() {
      this.stop();
      this.timer = setInterval(() => this.refresh(false), this.intervalMs);
      document.addEventListener("visibilitychange", () => {
        if (document.hidden) this.stop();
        else this.start();
      });
    },

    stop() {
      if (this.timer) clearInterval(this.timer);
      this.timer = null;
    },

    async refresh(forceOpen) {
      const menu = qs("#navbar-notif-menu");
      const badge = qs("#navbar-notif-badge");
      if (!menu) return;

      const { ok, data } = await apiFetch("/app/api/notifications/", { method: "GET" });
      if (!ok) return;

      const items = data.items || [];
      const count = data.unread_count != null ? data.unread_count : items.length;

      if (badge) {
        badge.textContent = String(count || "");
        badge.style.display = count ? "inline-block" : "none";
      }

      if (!items.length) {
        menu.innerHTML = `<span class="dropdown-item dropdown-header">Sem notificações</span>`;
      } else {
        menu.innerHTML = `
          <span class="dropdown-item dropdown-header">${count} notificações</span>
          <div class="dropdown-divider"></div>
          ${items.slice(0, 8).map((it) => `
            <a href="${escapeHtml(it.url || "#")}" class="dropdown-item">
              <i class="${escapeHtml(it.icon || "fas fa-info-circle")} mr-2"></i>
              ${escapeHtml(it.text || "Atualização")}
              <span class="float-right text-muted text-sm">${escapeHtml(it.when || "")}</span>
            </a>
          `).join("")}
          <div class="dropdown-divider"></div>
          <a href="${escapeHtml(data.all_url || "#")}" class="dropdown-item dropdown-footer">Ver tudo</a>`;
      }

      if (forceOpen) {
        const dd = qs("#navbar-notif-dropdown");
        if (dd) dd.classList.add("show");
      }
    }
  };

  const PortalChat = {
    timer: null,
    intervalMs: 2500,
    activeThreadId: null,
    lastMessageId: null,
    isOpen: false,

    init() {
      const btn = qs("#chat-fab");
      const win = qs("#chat-window");
      if (!btn || !win) return;

      btn.addEventListener("click", () => this.toggle());
      const closeBtn = qs("#chat-close");
      if (closeBtn) closeBtn.addEventListener("click", () => this.close());

      const form = qs("#chat-send-form");
      if (form) form.addEventListener("submit", (e) => { e.preventDefault(); this.send(); });

      const newBtn = qs("#chat-new-thread");
      if (newBtn) newBtn.addEventListener("click", () => this.createThreadUI());

      this.makeFloating(win);
    },

    toggle() { this.isOpen ? this.close() : this.open(); },

    open() {
      const win = qs("#chat-window");
      if (!win) return;
      win.classList.remove("d-none");
      this.isOpen = true;
      this.loadThreads().then(() => {
        if (!this.activeThreadId) {
          const first = qs("#chat-threads [data-thread-id]");
          if (first) this.selectThread(first.getAttribute("data-thread-id"));
        }
      });
      this.startPolling();
    },

    close() {
      const win = qs("#chat-window");
      if (!win) return;
      win.classList.add("d-none");
      this.isOpen = false;
      this.stopPolling();
    },

    startPolling() {
      this.stopPolling();
      this.timer = setInterval(() => {
        if (!this.isOpen) return;
        this.loadThreads(true);
        if (this.activeThreadId) this.loadMessages(true);
      }, this.intervalMs);

      document.addEventListener("visibilitychange", () => {
        if (document.hidden) this.stopPolling();
        else if (this.isOpen) this.startPolling();
      }, { once: true });
    },

    stopPolling() { if (this.timer) clearInterval(this.timer); this.timer = null; },

    async loadThreads(silent) {
      const box = qs("#chat-threads");
      if (!box) return;

      const { ok, status, data } = await apiFetch("/app/api/chat/threads/", { method: "GET" });
      if (!ok) {
        if (!silent) toast("error", "Falha ao carregar conversas.");
        if (!silent && (status === 400 || status === 403)) {
          box.innerHTML = `<div class="p-2 text-muted">Não foi possível carregar conversas. Verifique seu acesso.</div>`;
        }
        return;
      }

      const threads = data.threads || data || [];
      if (!threads.length) {
        box.innerHTML = `<div class="p-2 text-muted">Sem conversas. Crie um grupo.</div>`;
        return;
      }

      box.innerHTML = threads.map((t) => {
        const tid = escapeHtml(t.id);
        const title = escapeHtml(t.title || t.name || `Conversa #${tid}`);
        const unread = t.unread_count || 0;
        const badge = unread ? `<span class="badge badge-danger ml-auto">${unread}</span>` : "";
        const active = String(this.activeThreadId) === String(tid) ? "active" : "";
        return `
          <a href="#" class="list-group-item list-group-item-action d-flex align-items-center ${active}"
             data-thread-id="${tid}">
            <i class="far fa-comments mr-2"></i>
            <span class="text-truncate">${title}</span>
            ${badge}
          </a>`;
      }).join("");

      qsa("[data-thread-id]", box).forEach((el) => {
        el.addEventListener("click", (e) => {
          e.preventDefault();
          const id = el.getAttribute("data-thread-id");
          this.selectThread(id);
        });
      });
    },

    async selectThread(threadId) {
      this.activeThreadId = threadId ? String(threadId) : null;
      this.lastMessageId = null;

      const box = qs("#chat-threads");
      if (box) {
        qsa("[data-thread-id]", box).forEach((el) => {
          el.classList.toggle("active", el.getAttribute("data-thread-id") === String(threadId));
        });
      }

      const head = qs("#chat-thread-title");
      if (head) head.textContent = "Carregando...";
      await this.loadMessages(false);
    },

    async loadMessages(silent) {
      const threadId = this.activeThreadId;
      const list = qs("#chat-messages");
      if (!threadId || !list) return;

      const { ok, data } = await apiFetch(`/app/api/chat/messages/?thread_id=${encodeURIComponent(threadId)}`, { method: "GET" });
      if (!ok) { if (!silent) toast("error", "Falha ao carregar mensagens."); return; }

      const thread = data.thread || {};
      const msgs = data.messages || [];
      const head = qs("#chat-thread-title");
      if (head) head.textContent = thread.title || `Conversa #${threadId}`;

      if (!msgs.length) { list.innerHTML = `<div class="p-2 text-muted">Sem mensagens.</div>`; return; }

      const lastId = msgs[msgs.length - 1]?.id;
      if (silent && this.lastMessageId && String(lastId) === String(this.lastMessageId)) return;
      this.lastMessageId = lastId;

      list.innerHTML = msgs.map((m) => {
        const me = !!m.is_me;
        const cls = me ? "chat-msg chat-msg-me" : "chat-msg chat-msg-other";
        const who = escapeHtml(m.sender_name || m.sender_email || "Usuário");
        const when = escapeHtml(m.created_at || "");
        const body = escapeHtml(m.body || "");
        return `
          <div class="${cls}">
            <div class="small text-muted">${who} • ${when}</div>
            <div class="chat-bubble">${body}</div>
          </div>`;
      }).join("");

      list.scrollTop = list.scrollHeight;
    },

    async send() {
      const threadId = this.activeThreadId;
      const input = qs("#chat-input");
      if (!threadId || !input) return;
      const body = input.value.trim();
      if (!body) return;

      input.value = "";
      const { ok, data } = await apiFetch("/app/api/chat/messages/send/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ thread_id: threadId, body })
      });

      if (!ok) { toast("error", (data && data.detail) ? data.detail : "Falha ao enviar mensagem."); return; }

      await this.loadMessages(false);
      await this.loadThreads(true);
    },

    createThreadUI() {
      const modal = qs("#chatNewThreadModal");
      if (modal && window.$) {
        window.$(modal).modal("show");
        const form = qs("#chat-new-thread-form");
        if (form && !form.dataset.bound) {
          form.dataset.bound = "1";
          form.addEventListener("submit", (e) => {
            e.preventDefault();
            const title = (qs("#chat-new-title")?.value || "").trim();
            const emails = (qs("#chat-new-emails")?.value || "").trim();
            this.createThread(title, emails, modal);
          });
        }
        return;
      }
      const title = window.prompt("Nome do grupo:", "Equipe");
      if (title == null) return;
      const emails = window.prompt("Emails separados por vírgula (mesmo escritório):", "");
      if (emails == null) return;
      this.createThread(title, emails, null);
    },

    async createThread(title, emailsCsv, modalEl) {
      const emails = (emailsCsv || "")
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);

      const { ok, status, data } = await apiFetch("/app/api/chat/thread/create/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: title || "Equipe", emails })
      });

      if (!ok) {
        const msg = data?.detail || data?.error || "Falha ao criar conversa.";
        toast("error", msg);
        if (status === 400 && (data?.error === "no_users_found" || data?.error === "office_required")) {
          toast("error", "Dica: confirme se os emails existem e se os usuários têm membership ativo no escritório.");
        }
        return;
      }

      if (modalEl && window.$) window.$(modalEl).modal("hide");
      await this.loadThreads(false);
      if (data.thread_id) await this.selectThread(data.thread_id);
    },

    makeFloating(win) {
      const header = qs("#chat-window-header", win) || win;
      let isDrag = false, sx = 0, sy = 0, ox = 0, oy = 0;

      header.style.cursor = "move";

      header.addEventListener("mousedown", (e) => {
        if (e.target.closest("button, a, input, textarea, select")) return;
        isDrag = true;
        sx = e.clientX; sy = e.clientY;
        const rect = win.getBoundingClientRect();
        ox = rect.left; oy = rect.top;
        e.preventDefault();
      });

      window.addEventListener("mousemove", (e) => {
        if (!isDrag) return;
        const dx = e.clientX - sx;
        const dy = e.clientY - sy;
        win.style.left = (ox + dx) + "px";
        win.style.top = (oy + dy) + "px";
        win.style.right = "auto";
        win.style.bottom = "auto";
      });

      window.addEventListener("mouseup", () => { isDrag = false; });

      win.style.resize = "both";
      win.style.overflow = "hidden";
      win.style.position = "fixed";
      if (!win.style.width) win.style.width = "360px";
      if (!win.style.height) win.style.height = "480px";
      if (!win.style.right) win.style.right = "24px";
      if (!win.style.bottom) win.style.bottom = "24px";

      const list = qs("#chat-messages", win);
      if (list) list.style.overflow = "auto";
    }
  };

  const PortalKanban = {
    boardId: null,
    timer: null,
    intervalMs: 8000,
    dragCardId: null,

    init() {
      const root = qs("#kanban-root");
      if (!root) return;

      const addColBtn = qs("#kanban-add-column");
      if (addColBtn) addColBtn.addEventListener("click", () => this.createColumn());

      const editForm = qs("#card-edit-form");
      if (editForm && !editForm.dataset.bound) {
        editForm.dataset.bound = "1";
        editForm.addEventListener("submit", (e) => { e.preventDefault(); this.saveCardFromModal(); });
      }

      this.loadBoard(false);
      this.startPolling();
    },

    startPolling() {
      this.stopPolling();
      this.timer = setInterval(() => { if (!document.hidden) this.loadBoard(true); }, this.intervalMs);
      document.addEventListener("visibilitychange", () => {
        if (document.hidden) this.stopPolling();
        else this.startPolling();
      }, { once: true });
    },

    stopPolling() { if (this.timer) clearInterval(this.timer); this.timer = null; },

    async loadBoard(silent) {
      const root = qs("#kanban-root");
      if (!root) return;

      const { ok, data } = await apiFetch("/app/api/kanban/board/", { method: "GET" });
      if (!ok) { if (!silent) toast("error", "Falha ao carregar Kanban."); return; }

      const board = data.board || data;
      this.boardId = board.id;
      const columns = board.columns || [];

      root.innerHTML = columns.map((c) => this.renderColumn(c)).join("");

      columns.forEach((c) => {
        const colEl = qs(`[data-kanban-col="${c.id}"]`);
        if (!colEl) return;

        const addBtn = qs(`[data-action="col-add-card"]`, colEl);
        if (addBtn) addBtn.addEventListener("click", () => this.openAddCard(c.id));

        const renBtn = qs(`[data-action="col-rename"]`, colEl);
        if (renBtn) renBtn.addEventListener("click", () => this.renameColumn(c.id, c.title));

        const delBtn = qs(`[data-action="col-delete"]`, colEl);
        if (delBtn) delBtn.addEventListener("click", () => this.deleteColumn(c.id));

        qsa(`[data-kanban-card]`, colEl).forEach((cardEl) => {
          const cardId = cardEl.getAttribute("data-kanban-card");
          const title = cardEl.getAttribute("data-card-title") || "";
          const number = cardEl.getAttribute("data-card-number") || "";
          const body = cardEl.getAttribute("data-card-body") || "";

          const edit = qs(`[data-action="card-edit"]`, cardEl);
          if (edit) edit.addEventListener("click", (e) => {
            e.preventDefault(); e.stopPropagation();
            this.openEditCard({ id: cardId, title, number, body_md: body, column_id: c.id });
          });

          const head = qs(`[data-action="card-view"]`, cardEl);
          if (head) head.addEventListener("click", (e) => {
            e.preventDefault();
            this.openViewCard({ title, number, body_md: body });
          });

          cardEl.setAttribute("draggable", "true");
          cardEl.addEventListener("dragstart", (e) => { this.dragCardId = cardId; e.dataTransfer.effectAllowed = "move"; });
        });

        const listEl = qs(`[data-kanban-dropzone]`, colEl);
        if (listEl) {
          listEl.addEventListener("dragover", (e) => { e.preventDefault(); e.dataTransfer.dropEffect = "move"; });
          listEl.addEventListener("drop", (e) => {
            e.preventDefault();
            const cardId = this.dragCardId;
            this.dragCardId = null;
            if (!cardId) return;
            this.moveCard(cardId, c.id);
          });
        }
      });
    },

    renderColumn(c) {
      const title = escapeHtml(c.title || "Coluna");
      const cards = (c.cards || []).map((k) => this.renderCard(k)).join("");
      return `
      <div class="card card-row card-secondary" data-kanban-col="${escapeHtml(c.id)}">
        <div class="card-header d-flex align-items-center">
          <h3 class="card-title mb-0">${title}</h3>
          <div class="ml-auto d-flex" style="gap:10px;">
            <a href="#" data-action="col-add-card" class="text-white" title="Adicionar card"><i class="fas fa-plus"></i></a>
            <a href="#" data-action="col-rename" class="text-white" title="Editar coluna"><i class="fas fa-pen"></i></a>
            <a href="#" data-action="col-delete" class="text-white" title="Excluir coluna"><i class="fas fa-trash"></i></a>
          </div>
        </div>
        <div class="card-body" data-kanban-dropzone="1">
          ${cards || `<div class="text-muted small">Sem cards</div>`}
        </div>
      </div>`;
    },

    renderCard(k) {
      const id = escapeHtml(k.id);
      const title = escapeHtml(k.title || "Tarefa");
      const number = escapeHtml(String(k.number || ""));
      const body = String(k.body_md || "");
      const preview = escapeHtml(body).slice(0, 160) + (body.length > 160 ? "…" : "");
      return `
        <div class="card card-outline card-primary mb-2" data-kanban-card="${id}"
             data-card-title="${escapeHtml(k.title || "")}" data-card-number="${number}"
             data-card-body="${escapeHtml(body)}">
          <div class="card-header py-2">
            <div class="d-flex align-items-center">
              <a href="#" data-action="card-view" class="font-weight-bold text-truncate" style="max-width:220px;">
                ${title}${number ? ` <span class="badge badge-light ml-2">#${number}</span>` : ""}
              </a>
              <a href="#" data-action="card-edit" class="ml-auto text-primary" title="Editar"><i class="fas fa-pen"></i></a>
            </div>
          </div>
          <div class="card-body py-2">
            <small class="text-muted">${preview || ""}</small>
          </div>
        </div>`;
    },

    openAddCard(columnId) {
      const colInput = qs("#card-column-id");
      const idInput = qs("#card-id");
      const tInput = qs("#card-title");
      const nInput = qs("#card-number");
      const bInput = qs("#card-body-md");
      if (colInput) colInput.value = String(columnId);
      if (idInput) idInput.value = "";
      if (tInput) tInput.value = "";
      if (nInput) nInput.value = "";
      if (bInput) bInput.value = "";
      if (window.$) window.$("#cardEditModal").modal("show");
    },

    openEditCard(card) {
      const colInput = qs("#card-column-id");
      const idInput = qs("#card-id");
      const tInput = qs("#card-title");
      const nInput = qs("#card-number");
      const bInput = qs("#card-body-md");
      if (colInput) colInput.value = String(card.column_id);
      if (idInput) idInput.value = String(card.id);
      if (tInput) tInput.value = card.title || "";
      if (nInput) nInput.value = String(card.number || "");
      if (bInput) bInput.value = card.body_md || "";
      if (window.$) window.$("#cardEditModal").modal("show");
    },

    openViewCard(card) {
      const titleEl = qs("#cardViewTitle");
      const bodyEl = qs("#cardViewBody");
      if (titleEl) titleEl.textContent = `${card.title || "Tarefa"}${card.number ? " #" + card.number : ""}`;
      if (bodyEl) bodyEl.innerHTML = renderMarkdown(card.body_md || "");
      if (window.$) window.$("#cardViewModal").modal("show");
    },

    async saveCardFromModal() {
      const col = (qs("#card-column-id")?.value || "").trim();
      const id = (qs("#card-id")?.value || "").trim();
      const title = (qs("#card-title")?.value || "").trim();
      const number = (qs("#card-number")?.value || "").trim();
      const body_md = (qs("#card-body-md")?.value || "");

      const endpoint = id ? "/app/api/kanban/cards/update/" : "/app/api/kanban/cards/create/";
      const payload = { column_id: col, title, number, body_md, id };

      const { ok, status, data } = await apiFetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!ok) {
        if (status === 409 || data?.error === "duplicate_title_or_number") {
          toast("error", "Já existe um card com esse título ou numeração.");
        } else {
          toast("error", data?.detail || data?.error || "Falha ao salvar card.");
        }
        return;
      }

      if (window.$) window.$("#cardEditModal").modal("hide");
      await this.loadBoard(false);
    },

    async moveCard(cardId, toColumnId) {
      const { ok } = await apiFetch("/app/api/kanban/cards/move/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: cardId, to_column_id: toColumnId })
      });
      if (!ok) { toast("error", "Falha ao mover card."); return; }
      await this.loadBoard(true);
    },

    async createColumn() {
      const title = window.prompt("Nome da coluna:", "Nova coluna");
      if (title == null) return;

      const { ok, data } = await apiFetch("/app/api/kanban/columns/create/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: title.trim() || "Nova coluna" })
      });
      if (!ok) { toast("error", data?.error || "Falha ao criar coluna."); return; }
      await this.loadBoard(false);
    },

    async renameColumn(colId, currentTitle) {
      const title = window.prompt("Novo nome da coluna:", currentTitle || "");
      if (title == null) return;

      const { ok, data } = await apiFetch("/app/api/kanban/columns/rename/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: colId, title: title.trim() || currentTitle })
      });
      if (!ok) { toast("error", data?.error || "Falha ao renomear coluna."); return; }
      await this.loadBoard(false);
    },

    async deleteColumn(colId) {
      confirmDialog("Excluir coluna?", "Isso removerá a coluna e seus cards.", async () => {
        const { ok, data } = await apiFetch("/app/api/kanban/columns/delete/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id: colId })
        });
        if (!ok) { toast("error", data?.error || "Falha ao excluir coluna."); return; }
        await this.loadBoard(false);
      });
    }
  };

  const PortalCalendar = {
    calendar: null,
    timer: null,
    intervalMs: 20000,

    init() {
      const el = qs("#calendar");
      if (!el || !window.FullCalendar) return;

      if (window.FullCalendar.Draggable) {
        const containerEl = qs("#external-events");
        if (containerEl) {
          new FullCalendar.Draggable(containerEl, {
            itemSelector: ".external-event",
            eventData: function (eventEl) {
              return {
                title: eventEl.innerText.trim(),
                backgroundColor: window.getComputedStyle(eventEl).backgroundColor,
                borderColor: window.getComputedStyle(eventEl).backgroundColor,
                textColor: "#fff"
              };
            }
          });
        }
      }

      this.calendar = new FullCalendar.Calendar(el, {
        themeSystem: "bootstrap",
        initialView: "dayGridMonth",
        editable: true,
        droppable: true,
        selectable: true,
        headerToolbar: {
          left: "prev,next today",
          center: "title",
          right: "dayGridMonth,timeGridWeek,timeGridDay,listWeek"
        },
        events: async (info, success, failure) => {
          const { ok, data } = await apiFetch("/app/api/calendar/events/", { method: "GET" });
          if (!ok) { failure(); return; }
          const events = (data.events || data || []).map((e) => ({
            id: String(e.id),
            title: e.title,
            start: e.start,
            end: e.end || null,
            allDay: !!e.all_day,
            backgroundColor: e.color || undefined,
            borderColor: e.color || undefined
          }));
          success(events);
        },

        eventReceive: async (info) => {
          const title = info.event.title;
          const color = info.event.backgroundColor || info.event.extendedProps?.color;

          const { ok, data } = await apiFetch("/app/api/calendar/events/create/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              title,
              start: info.event.startStr,
              end: info.event.endStr || null,
              all_day: info.event.allDay,
              color: color
            })
          });

          if (!ok) {
            toast("error", data?.error || "Falha ao criar evento.");
            info.revert();
            return;
          }

          if (data && data.id) info.event.setProp("id", String(data.id));

          const chk = qs("#drop-remove");
          if (chk && chk.checked && info.draggedEl) info.draggedEl.parentNode.removeChild(info.draggedEl);
        },

        eventDrop: async (info) => {
          const { ok, data } = await apiFetch("/app/api/calendar/events/update/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              id: info.event.id,
              start: info.event.startStr,
              end: info.event.endStr || null,
              all_day: info.event.allDay
            })
          });
          if (!ok) { toast("error", data?.error || "Falha ao mover evento."); info.revert(); }
        },

        eventResize: async (info) => {
          const { ok, data } = await apiFetch("/app/api/calendar/events/update/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              id: info.event.id,
              start: info.event.startStr,
              end: info.event.endStr || null
            })
          });
          if (!ok) { toast("error", data?.error || "Falha ao redimensionar evento."); info.revert(); }
        },

        eventClick: (info) => {
          confirmDialog("Excluir evento?", info.event.title, async () => {
            const { ok, data } = await apiFetch("/app/api/calendar/events/delete/", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ id: info.event.id })
            });
            if (!ok) { toast("error", data?.error || "Falha ao excluir."); return; }
            info.event.remove();
          });
        }
      });

      this.calendar.render();
      this.startPolling();
    },

    startPolling() {
      this.stopPolling();
      this.timer = setInterval(() => {
        if (document.hidden) return;
        try { this.calendar && this.calendar.refetchEvents(); } catch (e) {}
      }, this.intervalMs);

      document.addEventListener("visibilitychange", () => {
        if (document.hidden) this.stopPolling();
        else this.startPolling();
      }, { once: true });
    },

    stopPolling() { if (this.timer) clearInterval(this.timer); this.timer = null; }
  };

  function boot() {
    PortalSearch.init();
    PortalNotifications.init();
    PortalChat.init();
    PortalKanban.init();
    PortalCalendar.init();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();

  window.JFPortal = { PortalSearch, PortalNotifications, PortalChat, PortalKanban, PortalCalendar, renderMarkdown };
})();
