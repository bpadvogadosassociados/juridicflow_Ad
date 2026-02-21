/**
 * JuridicFlow — portal.js
 * Gerencia: Busca Global, Notificações, Chat
 */

/* ============================================================
   CSRF Token helper
   ============================================================ */
function csrfToken() {
  const el = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
  if (el) return el.split('=')[1].trim();
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.content : '';
}

async function apiPost(url, data) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() },
    body: JSON.stringify(data),
  });
  return res.json();
}

async function apiGet(url) {
  const res = await fetch(url, {
    headers: { 'X-Requested-With': 'XMLHttpRequest' }
  });
  return res.json();
}


/* ============================================================
   BUSCA GLOBAL
   ============================================================ */
const PortalSearch = {
  timer: null,
  input: null,
  resultsBox: null,

  init() {
    this.input = document.getElementById('navbar-search-input');
    this.resultsBox = document.getElementById('navbar-search-results');
    if (!this.input || !this.resultsBox) return;

    this.input.addEventListener('input', () => {
      clearTimeout(this.timer);
      const q = this.input.value.trim();
      if (q.length < 2) { this.resultsBox.innerHTML = ''; return; }
      this.timer = setTimeout(() => this.search(q), 280);
    });

    document.addEventListener('click', (e) => {
      if (!this.resultsBox.contains(e.target) && e.target !== this.input)
        this.resultsBox.innerHTML = '';
    });
  },

  async search(q) {
    try {
      const data = await apiGet('/app/api/search/?q=' + encodeURIComponent(q));
      this.render(data.results || []);
    } catch (e) { console.warn('Search error:', e); }
  },

  render(results) {
    const iconMap = {
      process: 'fas fa-balance-scale text-primary',
      customer: 'fas fa-user text-success',
      deadline: 'fas fa-clock text-warning',
      document: 'fas fa-file text-info',
    };
    if (!results.length) {
      this.resultsBox.innerHTML = '<div class="search-item text-muted">Nenhum resultado encontrado</div>';
      return;
    }
    this.resultsBox.innerHTML = results.map(r => `
      <a href="${r.url}" class="search-item">
        <span class="search-icon"><i class="${iconMap[r.type] || 'fas fa-circle'}"></i></span>
        <span class="search-text">
          <div class="search-title">${r.title}</div>
          ${r.subtitle ? `<div class="search-sub">${r.subtitle}</div>` : ''}
        </span>
      </a>
    `).join('');
  }
};


/* ============================================================
   NOTIFICAÇÕES
   ============================================================ */
const PortalNotifications = {
  badge: null,
  menu: null,
  pollInterval: null,

  init() {
    this.badge = document.getElementById('navbar-notif-badge');
    this.menu = document.getElementById('navbar-notif-menu');
    if (!this.badge || !this.menu) return;

    this.refresh();
    this.pollInterval = setInterval(() => this.refresh(), 30000);

    // Ao abrir dropdown, marca como lidas após 2s
    const btn = document.getElementById('navbar-notif-btn');
    if (btn) {
      btn.addEventListener('click', () => {
        setTimeout(() => this.markAllRead(), 2000);
      });
    }
  },

  async refresh() {
    try {
      const data = await apiGet('/app/api/notifications/');
      const items = data.items || [];
      const unread = data.unread_count || 0;

      // Badge
      if (unread > 0) {
        this.badge.textContent = unread > 99 ? '99+' : unread;
        this.badge.style.display = '';
      } else {
        this.badge.style.display = 'none';
      }

      this.renderMenu(items, unread);
    } catch (e) { console.warn('Notifications error:', e); }
  },

  renderMenu(items, unread) {
    if (!items.length) {
      this.menu.innerHTML = '<span class="dropdown-item dropdown-header text-muted">Sem notificações</span>';
      return;
    }

    const header = `<span class="dropdown-item dropdown-header">${unread} notificação(ões) não lida(s)</span>`;
    const list = items.slice(0, 8).map(n => `
      <div class="notif-item ${n.is_read ? '' : 'unread'}" data-id="${n.id}" data-url="${n.url}" onclick="PortalNotifications.clickItem(this)">
        <div class="d-flex align-items-start">
          <i class="${n.icon || 'fas fa-bell text-muted'} mt-1 mr-2"></i>
          <div class="flex-1">
            <div class="notif-title">${n.title}</div>
            ${n.message ? `<div class="notif-meta">${n.message}</div>` : ''}
            <div class="notif-meta">${n.when || ''}</div>
          </div>
        </div>
      </div>
    `).join('');

    const footer = `<div class="notif-footer"><a href="#" onclick="PortalNotifications.markAllRead();return false;">Marcar todas como lidas</a></div>`;
    this.menu.innerHTML = header + list + footer;
  },

  async clickItem(el) {
    const id = el.dataset.id;
    const url = el.dataset.url;
    el.classList.remove('unread');
    try {
      await apiPost(`/app/api/notifications/${id}/read/`, {});
      const unread = parseInt(this.badge.textContent || '0') - 1;
      if (unread > 0) { this.badge.textContent = unread; }
      else { this.badge.style.display = 'none'; }
    } catch (e) {}
    if (url) window.location.href = url;
  },

  async markAllRead() {
    try {
      await apiPost('/app/api/notifications/read-all/', {});
      this.badge.style.display = 'none';
      await this.refresh();
    } catch (e) {}
  }
};


/* ============================================================
   CHAT
   ============================================================ */
const PortalChat = {
  window: null,
  threadsEl: null,
  messagesEl: null,
  titleEl: null,
  sendForm: null,
  sendInput: null,
  fab: null,

  currentThread: null,
  pollTimer: null,
  lastMsgId: 0,

  init() {
    this.window = document.getElementById('chat-window');
    this.threadsEl = document.getElementById('chat-threads');
    this.messagesEl = document.getElementById('chat-messages');
    this.titleEl = document.getElementById('chat-thread-title');
    this.sendForm = document.getElementById('chat-send-form');
    this.sendInput = document.getElementById('chat-input');
    this.fab = document.getElementById('chat-fab');

    if (!this.window || !this.fab) return;

    this.fab.addEventListener('click', (e) => { e.preventDefault(); this.toggleWindow(); });
    document.getElementById('chat-close').addEventListener('click', () => this.closeWindow());
    document.getElementById('chat-new-thread').addEventListener('click', () => {
      $('#chatNewThreadModal').modal('show');
    });

    if (this.sendForm) {
      this.sendForm.addEventListener('submit', (e) => { e.preventDefault(); this.sendMessage(); });
    }

    // Modal de nova conversa
    const newForm = document.getElementById('chat-new-thread-form');
    if (newForm) {
      newForm.addEventListener('submit', (e) => { e.preventDefault(); this.createThread(); });
    }

    // Autocomplete de emails no modal
    const emailInput = document.getElementById('chat-new-emails');
    if (emailInput) {
      let acTimer = null;
      emailInput.addEventListener('input', () => {
        clearTimeout(acTimer);
        const parts = emailInput.value.split(',');
        const lastPart = parts[parts.length - 1].trim();
        if (lastPart.length < 2) return;
        acTimer = setTimeout(() => this.autocompleteUsers(lastPart, emailInput), 300);
      });
    }
  },

  toggleWindow() {
    if (this.window.classList.contains('d-none')) {
      this.window.classList.remove('d-none');
      this.loadThreads();
    } else {
      this.closeWindow();
    }
  },

  closeWindow() {
    this.window.classList.add('d-none');
    clearInterval(this.pollTimer);
    this.currentThread = null;
  },

  async loadThreads() {
    try {
      const data = await apiGet('/app/api/chat/threads/');
      const items = data.items || [];
      if (!items.length) {
        this.threadsEl.innerHTML = '<div class="px-2 py-3 text-muted" style="font-size:.75rem">Nenhuma conversa</div>';
        return;
      }
      this.threadsEl.innerHTML = items.map(t => `
        <div class="portal-chat-thread-item" data-id="${t.id}" title="${t.title}" onclick="PortalChat.selectThread(${t.id}, '${t.title.replace(/'/g, "\\'")}')">
          ${t.title}
        </div>
      `).join('');
    } catch (e) { console.warn('Chat threads error:', e); }
  },

  async selectThread(threadId, title) {
    clearInterval(this.pollTimer);
    this.currentThread = threadId;
    this.lastMsgId = 0;

    // Marca activo
    document.querySelectorAll('.portal-chat-thread-item').forEach(el => {
      el.classList.toggle('active', parseInt(el.dataset.id) === threadId);
    });

    await this.loadMessages(threadId, title);
    this.pollTimer = setInterval(() => this.pollMessages(threadId), 3000);
  },

  async loadMessages(threadId, title) {
    try {
      const data = await apiGet(`/app/api/chat/thread/${threadId}/messages/`);
      const items = data.items || [];
      this.titleEl.textContent = data.thread_title || title || 'Conversa';
      this.renderMessages(items);
      if (items.length) this.lastMsgId = items[items.length - 1].id;
    } catch (e) { console.warn('Load messages error:', e); }
  },

  async pollMessages(threadId) {
    if (!this.currentThread) return;
    try {
      const data = await apiGet(`/app/api/chat/thread/${threadId}/messages/`);
      const items = data.items || [];
      const newItems = items.filter(m => m.id > this.lastMsgId);
      if (newItems.length) {
        newItems.forEach(m => this.appendMessage(m));
        this.lastMsgId = items[items.length - 1].id;
      }
    } catch (e) {}
  },

  renderMessages(items) {
    if (!items.length) {
      this.messagesEl.innerHTML = '<div class="text-muted text-center py-4" style="font-size:.8rem">Sem mensagens ainda</div>';
      return;
    }
    this.messagesEl.innerHTML = '';
    items.forEach(m => this.appendMessage(m));
    this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
  },

  appendMessage(m) {
    const div = document.createElement('div');
    div.className = 'chat-msg ' + (m.is_mine ? 'mine' : 'theirs');
    div.innerHTML = `
      <div class="bubble">${this.escHtml(m.body)}</div>
      <div class="meta">${m.is_mine ? '' : m.sender + ' · '}${this.formatTime(m.created_at)}</div>
    `;
    this.messagesEl.appendChild(div);
    this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
  },

  async sendMessage() {
    const body = this.sendInput.value.trim();
    if (!body || !this.currentThread) return;
    this.sendInput.value = '';
    try {
      const data = await apiPost(`/app/api/chat/thread/${this.currentThread}/send/`, { body });
      if (data.ok) this.appendMessage(data.message);
    } catch (e) { console.warn('Send message error:', e); }
  },

  async createThread() {
    const title = document.getElementById('chat-new-title').value.trim();
    const emailsRaw = document.getElementById('chat-new-emails').value;
    const emails = emailsRaw.split(',').map(e => e.trim()).filter(Boolean);

    if (!title) { alert('Informe o nome da conversa'); return; }

    try {
      const data = await apiPost('/app/api/chat/thread/create/', {
        title, emails, type: 'group'
      });
      if (data.ok) {
        $('#chatNewThreadModal').modal('hide');
        document.getElementById('chat-new-title').value = '';
        document.getElementById('chat-new-emails').value = '';
        await this.loadThreads();
        if (data.thread) this.selectThread(data.thread.id, data.thread.title);
      } else {
        alert(data.error || 'Erro ao criar conversa');
      }
    } catch (e) { alert('Erro ao criar conversa'); }
  },

  async autocompleteUsers(q, inputEl) {
    try {
      const data = await apiGet('/app/api/chat/users/search/?q=' + encodeURIComponent(q));
      const items = data.items || [];
      // Remove ac anterior
      const prev = document.getElementById('chat-ac-list');
      if (prev) prev.remove();
      if (!items.length) return;

      const list = document.createElement('div');
      list.id = 'chat-ac-list';
      list.className = 'list-group';
      list.style.cssText = 'position:absolute;z-index:9999;max-width:300px;';
      items.forEach(u => {
        const item = document.createElement('button');
        item.type = 'button';
        item.className = 'list-group-item list-group-item-action py-1 px-2';
        item.style.fontSize = '.82rem';
        item.textContent = `${u.name} <${u.email}>`;
        item.onclick = () => {
          const parts = inputEl.value.split(',');
          parts[parts.length - 1] = ' ' + u.email;
          inputEl.value = parts.join(',') + ', ';
          list.remove();
          inputEl.focus();
        };
        list.appendChild(item);
      });
      inputEl.parentNode.style.position = 'relative';
      inputEl.parentNode.appendChild(list);
      document.addEventListener('click', () => { const l = document.getElementById('chat-ac-list'); if(l) l.remove(); }, { once: true });
    } catch(e) {}
  },

  escHtml(str) {
    return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  },

  formatTime(iso) {
    try {
      const d = new Date(iso);
      return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    } catch(e) { return ''; }
  }
};


/* ============================================================
   INIT
   ============================================================ */
document.addEventListener('DOMContentLoaded', () => {
  PortalSearch.init();
  PortalNotifications.init();
  PortalChat.init();
});
