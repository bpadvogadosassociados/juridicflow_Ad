// apps/portal/static/portal/js/portal.js

// ===== BUSCA GLOBAL (navbar) =====
const PortalSearch = {
  submit(e) {
    e.preventDefault();
    const q = document.getElementById('navbar-search-input').value.trim();
    if (!q) return false;
    
    fetch(`/app/api/search/?q=${encodeURIComponent(q)}`)
      .then(r => r.json())
      .then(data => {
        const div = document.getElementById('navbar-search-results');
        if (!data.results || data.results.length === 0) {
          div.innerHTML = '<div class="p-3 text-muted">Nenhum resultado.</div>';
          return;
        }
        
        let html = '<div class="list-group">';
        data.results.forEach(item => {
          html += `<a href="${item.url}" class="list-group-item list-group-item-action">
            <i class="${item.icon}"></i> ${item.label} <small class="text-muted">(${item.type})</small>
          </a>`;
        });
        html += '</div>';
        div.innerHTML = html;
      });
    return false;
  }
};

// ===== NOTIFICAÇÕES =====
function loadNotifications() {
  fetch('/app/api/notifications/')
    .then(r => r.json())
    .then(data => {
      document.getElementById('notif-count').textContent = data.count || 0;
      const container = document.getElementById('notif-items');
      if (!data.items || data.items.length === 0) {
        container.innerHTML = '<div class="dropdown-item text-muted">Sem notificações.</div>';
        return;
      }
      
      let html = '';
      data.items.forEach(item => {
        html += `<a href="#" class="dropdown-item">
          <i class="fas fa-envelope mr-2"></i> ${item.text}
          <span class="float-right text-muted text-sm">${item.when}</span>
        </a><div class="dropdown-divider"></div>`;
      });
      container.innerHTML = html;
    });
}

// Carregar notificações ao iniciar
document.addEventListener('DOMContentLoaded', () => {
  loadNotifications();
  setInterval(loadNotifications, 60000); // Atualiza a cada 1min
});

// ===== CHAT =====
const PortalChat = {
  currentThreadId: null,
  pollInterval: null,
  lastMessageId: 0,

  toggle() {
    const win = document.getElementById('chat-window');
    win.classList.toggle('d-none');
    if (!win.classList.contains('d-none')) {
      this.loadThreads();
      this.startPolling();
    } else {
      this.stopPolling();
    }
  },

  close() {
    document.getElementById('chat-window').classList.add('d-none');
    this.stopPolling();
  },

  loadThreads() {
    fetch('/app/api/chat/threads/')
      .then(r => r.json())
      .then(data => {
        const container = document.getElementById('chat-threads');
        if (!data.threads || data.threads.length === 0) {
          container.innerHTML = '<div class="p-2 text-muted">Sem conversas.</div>';
          return;
        }
        
        let html = '<div class="list-group">';
        data.threads.forEach(t => {
          const active = t.id === this.currentThreadId ? 'active' : '';
          html += `<a href="#" class="list-group-item list-group-item-action ${active}" 
                      onclick="PortalChat.selectThread(${t.id}); return false;">
                    ${t.title}
                  </a>`;
        });
        html += '</div>';
        container.innerHTML = html;
      });
  },

  selectThread(threadId) {
    this.currentThreadId = threadId;
    this.lastMessageId = 0;
    this.loadThreads();
    this.loadMessages();
  },

  loadMessages() {
    if (!this.currentThreadId) return;
    
    fetch(`/app/api/chat/thread/${this.currentThreadId}/messages/?after_id=${this.lastMessageId}`)
      .then(r => r.json())
      .then(data => {
        if (!data.messages || data.messages.length === 0) {
          if (this.lastMessageId === 0) {
            document.getElementById('chat-messages').innerHTML = '<div class="p-3 text-muted">Sem mensagens.</div>';
          }
          return;
        }
        
        const container = document.getElementById('chat-messages');
        data.messages.forEach(msg => {
          const div = document.createElement('div');
          div.className = 'portal-chat-message';
          div.innerHTML = `<strong>${msg.sender}</strong> <small class="text-muted">${msg.when}</small><br>${msg.body}`;
          container.appendChild(div);
          this.lastMessageId = Math.max(this.lastMessageId, msg.id);
        });
        
        container.scrollTop = container.scrollHeight;
      });
  },

  send(e) {
    e.preventDefault();
    if (!this.currentThreadId) {
      alert('Selecione uma conversa primeiro.');
      return false;
    }
    
    const input = document.getElementById('chat-input');
    const body = input.value.trim();
    if (!body) return false;
    
    fetch(`/app/api/chat/thread/${this.currentThreadId}/send/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
      body: JSON.stringify({ body })
    })
    .then(r => r.json())
    .then(() => {
      input.value = '';
      this.loadMessages();
    });
    
    return false;
  },

  newGroup() {
    const title = prompt('Nome do grupo:');
    if (!title) return;
    
    const emailsStr = prompt('Emails dos participantes (separados por vírgula):');
    if (!emailsStr) return;
    
    const emails = emailsStr.split(',').map(e => e.trim()).filter(e => e);
    
    fetch('/app/api/chat/thread/create/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
      body: JSON.stringify({ title, emails })
    })
    .then(r => r.json())
    .then(data => {
      if (data.thread_id) {
        this.loadThreads();
        this.selectThread(data.thread_id);
      }
    });
  },

  startPolling() {
    this.pollInterval = setInterval(() => {
      if (this.currentThreadId) {
        this.loadMessages();
      }
    }, 3000); // Poll a cada 3s
  },

  stopPolling() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  }
};

// ===== CALENDAR =====
const PortalCalendar = {
  calendar: null,

  init() {
    const calendarEl = document.getElementById('calendar');
    if (!calendarEl) return;

    this.calendar = new FullCalendar.Calendar(calendarEl, {
      headerToolbar: {
        left: 'prev,next today',
        center: 'title',
        right: 'dayGridMonth,timeGridWeek,timeGridDay'
      },
      themeSystem: 'bootstrap',
      editable: true,
      droppable: true,
      events: '/app/api/calendar/events/',
      
      eventDrop: (info) => {
        this.updateEvent(info.event);
      },
      
      eventResize: (info) => {
        this.updateEvent(info.event);
      },
      
      drop: (info) => {
        const title = info.draggedEl.innerText;
        const color = info.draggedEl.getAttribute('data-color');
        
        fetch('/app/api/calendar/events/create/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
          body: JSON.stringify({
            title,
            start: info.dateStr,
            all_day: info.allDay,
            color
          })
        })
        .then(r => r.json())
        .then(() => {
          this.calendar.refetchEvents();
          if (document.getElementById('drop-remove').checked) {
            info.draggedEl.parentNode.removeChild(info.draggedEl);
          }
        });
      }
    });

    this.calendar.render();
    this.initDraggable();
  },

  initDraggable() {
    const containerEl = document.getElementById('external-events');
    if (!containerEl) return;

    new FullCalendar.Draggable(containerEl, {
      itemSelector: '.external-event',
      eventData: (eventEl) => ({
        title: eventEl.innerText,
        backgroundColor: eventEl.getAttribute('data-color'),
        borderColor: eventEl.getAttribute('data-color')
      })
    });
  },

  updateEvent(event) {
    fetch(`/app/api/calendar/events/update/${event.id}/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
      body: JSON.stringify({
        start: event.start.toISOString(),
        end: event.end ? event.end.toISOString() : null,
        all_day: event.allDay
      })
    });
  }
};

// ===== KANBAN =====
const KanbanUI = {
  board: null,

  init() {
    this.loadBoard();
  },

  loadBoard() {
    fetch('/app/api/kanban/board/')
      .then(r => r.json())
      .then(data => {
        this.board = data;
        this.render();
      });
  },

  render() {
    const container = document.getElementById('kanban-columns');
    if (!container) return;

    let html = '';
    this.board.columns.forEach(col => {
      html += `
        <div class="col-md-3">
          <div class="card card-row card-default">
            <div class="card-header">
              <h3 class="card-title">${col.title}</h3>
              <div class="card-tools">
                <button class="btn btn-tool btn-sm" onclick="KanbanUI.addCard(${col.id}); return false;">
                  <i class="fas fa-plus"></i>
                </button>
                <button class="btn btn-tool btn-sm" onclick="KanbanUI.editColumn(${col.id}); return false;">
                  <i class="fas fa-pencil-alt"></i>
                </button>
                <button class="btn btn-tool btn-sm" onclick="KanbanUI.deleteColumn(${col.id}); return false;">
                  <i class="fas fa-trash"></i>
                </button>
              </div>
            </div>
            <div class="card-body" data-column-id="${col.id}">
              ${col.cards.map(card => `
                <div class="card card-light card-outline kanban-card" data-card-id="${card.id}" draggable="true">
                  <div class="card-header">
                    <h5 class="card-title">#${card.number} ${card.title}</h5>
                    <div class="card-tools">
                      <button class="btn btn-tool btn-sm" onclick="KanbanUI.editCard(${card.id}); return false;">
                        <i class="fas fa-pencil-alt"></i>
                      </button>
                    </div>
                  </div>
                  <div class="card-body" onclick="KanbanUI.viewCard(${card.id});" style="cursor:pointer;">
                    ${card.body_preview}
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        </div>
      `;
    });
    container.innerHTML = html;
    this.initDragDrop();
  },

  initDragDrop() {
    const cards = document.querySelectorAll('.kanban-card');
    cards.forEach(card => {
      card.addEventListener('dragstart', (e) => {
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', card.getAttribute('data-card-id'));
        card.classList.add('dragging');
      });
      
      card.addEventListener('dragend', () => {
        card.classList.remove('dragging');
      });
    });

    const columns = document.querySelectorAll('[data-column-id]');
    columns.forEach(col => {
      col.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
      });
      
      col.addEventListener('drop', (e) => {
        e.preventDefault();
        const cardId = e.dataTransfer.getData('text/plain');
        const columnId = col.getAttribute('data-column-id');
        
        fetch('/app/api/kanban/cards/move/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
          body: JSON.stringify({ card_id: cardId, column_id: columnId, order: 0 })
        })
        .then(() => this.loadBoard());
      });
    });
  },

  addColumn() {
    const title = prompt('Título da coluna:');
    if (!title) return;
    
    fetch('/app/api/kanban/columns/create/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
      body: JSON.stringify({ title })
    })
    .then(() => this.loadBoard());
  },

  editColumn(colId) {
    const title = prompt('Novo título:');
    if (!title) return;
    
    fetch(`/app/api/kanban/columns/update/${colId}/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
      body: JSON.stringify({ title })
    })
    .then(() => this.loadBoard());
  },

  deleteColumn(colId) {
    if (!confirm('Deletar esta coluna?')) return;
    
    fetch(`/app/api/kanban/columns/delete/${colId}/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': getCookie('csrftoken') }
    })
    .then(() => this.loadBoard());
  },

  addCard(colId) {
    document.getElementById('card-id').value = '';
    document.getElementById('card-title').value = 'Exemplo';
    document.getElementById('card-number').value = Date.now() % 10000;
    document.getElementById('card-body-md').value = '';
    document.getElementById('card-edit-form').setAttribute('data-column-id', colId);
    $('#cardEditModal').modal('show');
  },

  editCard(cardId) {
    fetch(`/app/api/kanban/cards/detail/${cardId}/`)
      .then(r => r.json())
      .then(data => {
        document.getElementById('card-id').value = data.id;
        document.getElementById('card-title').value = data.title;
        document.getElementById('card-number').value = data.number;
        document.getElementById('card-body-md').value = data.body_md || '';
        $('#cardEditModal').modal('show');
      });
  },

  saveCard(e) {
    e.preventDefault();
    const cardId = document.getElementById('card-id').value;
    const title = document.getElementById('card-title').value;
    const number = parseInt(document.getElementById('card-number').value);
    const body_md = document.getElementById('card-body-md').value;
    
    if (cardId) {
      // Update
      fetch(`/app/api/kanban/cards/update/${cardId}/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
        body: JSON.stringify({ title, number, body_md })
      })
      .then(() => {
        $('#cardEditModal').modal('hide');
        this.loadBoard();
      });
    } else {
      // Create
      const columnId = document.getElementById('card-edit-form').getAttribute('data-column-id');
      fetch('/app/api/kanban/cards/create/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
        body: JSON.stringify({ column_id: columnId, title, number, body_md })
      })
      .then(() => {
        $('#cardEditModal').modal('hide');
        this.loadBoard();
      });
    }
    
    return false;
  },

  viewCard(cardId) {
    fetch(`/app/api/kanban/cards/detail/${cardId}/`)
      .then(r => r.json())
      .then(data => {
        document.getElementById('card-view-title').textContent = `#${data.number} ${data.title}`;
        document.getElementById('card-view-body').innerHTML = marked.parse(data.body_md || '');
        $('#cardViewModal').modal('show');
      });
  }
};

// ===== ERP TEMPLATES (Settings) =====
const ERPTemplates = {
  init() {
    this.load();
  },

  load() {
    fetch('/app/api/calendar/templates/list/')
      .then(r => r.json())
      .then(data => {
        const container = document.getElementById('tpl-list');
        if (!data.items || data.items.length === 0) {
          container.innerHTML = '<p class="text-muted">Sem modelos.</p>';
          return;
        }
        
        let html = '<div class="list-group">';
        data.items.forEach(t => {
          html += `<div class="list-group-item d-flex justify-content-between align-items-center">
            <span><span style="width:20px;height:20px;background:${t.color};display:inline-block;border-radius:3px;"></span> ${t.title}</span>
            <button class="btn btn-sm btn-danger" onclick="ERPTemplates.delete(${t.id}); return false;">Deletar</button>
          </div>`;
        });
        html += '</div>';
        container.innerHTML = html;
      });
  },

  create(e) {
    e.preventDefault();
    const title = document.getElementById('tpl-title').value.trim();
    const color = document.getElementById('tpl-color').value.trim();
    
    fetch('/app/api/calendar/templates/create/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
      body: JSON.stringify({ title, color })
    })
    .then(() => {
      document.getElementById('tpl-title').value = '';
      this.load();
    });
    
    return false;
  },

  delete(tplId) {
    if (!confirm('Deletar este modelo?')) return;
    
    fetch(`/app/api/calendar/templates/delete/${tplId}/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': getCookie('csrftoken') }
    })
    .then(() => this.load());
  }
};

// ===== HELPER: GET CSRF TOKEN =====
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}