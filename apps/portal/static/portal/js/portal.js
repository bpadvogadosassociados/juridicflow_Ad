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
const CSRFTOKEN = getCookie('csrftoken');

async function jsonFetch(url, opts={}){
  const headers = opts.headers || {};
  headers["X-CSRFToken"] = CSRFTOKEN;
  headers["Content-Type"] = headers["Content-Type"] || "application/json";
  opts.headers = headers;
  const res = await fetch(url, opts);
  if(!res.ok){
    const text = await res.text();
    throw new Error(text || ("HTTP " + res.status));
  }
  return await res.json();
}

const PortalSearch = {
  async submit(ev){
    ev.preventDefault();
    const q = document.getElementById("navbar-search-input").value.trim();
    const box = document.getElementById("navbar-search-results");
    if(!q){ box.style.display="none"; return false; }
    const data = await jsonFetch("/app/api/search/?q=" + encodeURIComponent(q), {method:"GET", headers: {"Content-Type": "application/json"}});
    box.innerHTML = "";
    if(data.results.length === 0){
      box.innerHTML = '<div class="text-muted p-2">Nenhum resultado.</div>';
    } else {
      for(const r of data.results){
        const a = document.createElement("a");
        a.href = r.url || "#";
        a.innerHTML = `<i class="${r.icon} mr-2"></i>${r.label} <small class="text-muted">(${r.type})</small>`;
        box.appendChild(a);
      }
    }
    box.style.display="block";
    return false;
  }
};

const PortalNotifications = {
  async refresh(){
    try{
      const data = await jsonFetch("/app/api/notifications/", {method:"GET", headers: {"Content-Type": "application/json"}});
      document.getElementById("notif-count").innerText = data.count;
      const items = document.getElementById("notif-items");
      items.innerHTML = "";
      for(const n of data.items){
        const div = document.createElement("a");
        div.href = "#";
        div.className = "dropdown-item";
        div.innerHTML = `<i class="fas fa-bolt mr-2"></i> ${n.text} <span class="float-right text-muted text-sm">${n.when}</span>`;
        items.appendChild(div);
        const dd = document.createElement("div");
        dd.className = "dropdown-divider";
        items.appendChild(dd);
      }
    }catch(e){ /* ignore */ }
  }
};
setInterval(()=>PortalNotifications.refresh(), 15000);
setTimeout(()=>PortalNotifications.refresh(), 800);

const PortalChat = {
  open: false,
  activeThread: null,
  initDone: false,
  dragging: false,
  dragOffset: {x:0,y:0},

  toggle(){
    const w = document.getElementById("chat-window");
    if(w.classList.contains("d-none")){
      w.classList.remove("d-none");
      this.open = true;
      if(!this.initDone){ this.init(); this.initDone = true; }
      this.refreshThreads();
    } else {
      w.classList.add("d-none");
      this.open = false;
    }
  },
  close(){
    document.getElementById("chat-window").classList.add("d-none");
    this.open = false;
  },
  init(){
    const header = document.querySelector(".portal-chat-header");
    const win = document.getElementById("chat-window");
    header.addEventListener("mousedown", (e)=>{
      this.dragging = true;
      const rect = win.getBoundingClientRect();
      this.dragOffset.x = e.clientX - rect.left;
      this.dragOffset.y = e.clientY - rect.top;
      e.preventDefault();
    });
    window.addEventListener("mousemove", (e)=>{
      if(!this.dragging) return;
      win.style.left = (e.clientX - this.dragOffset.x) + "px";
      win.style.top = (e.clientY - this.dragOffset.y) + "px";
      win.style.right = "auto";
      win.style.bottom = "auto";
    });
    window.addEventListener("mouseup", ()=>{ this.dragging=false; });
    setInterval(()=>{ if(this.open) this.refreshMessages(); }, 4000);
  },
  async refreshThreads(){
    const data = await jsonFetch("/app/api/chat/threads/", {method:"GET", headers: {"Content-Type": "application/json"}});
    const box = document.getElementById("chat-threads");
    box.innerHTML = "";
    for(const t of data.threads){
      const div = document.createElement("div");
      div.className = "thread" + (this.activeThread===t.id ? " active" : "");
      div.innerText = t.title;
      div.onclick = ()=>{ this.activeThread = t.id; this.refreshThreads(); this.refreshMessages(true); };
      box.appendChild(div);
    }
    if(!this.activeThread && data.threads.length){ this.activeThread = data.threads[0].id; this.refreshThreads(); }
  },
  async refreshMessages(scrollBottom=false){
    if(!this.activeThread) return;
    const data = await jsonFetch(`/app/api/chat/thread/${this.activeThread}/messages/?after_id=${window.__lastMsgId||0}`, {method:"GET", headers: {"Content-Type": "application/json"}});
    const box = document.getElementById("chat-messages");
    for(const m of data.messages){
      const div = document.createElement("div");
      div.className = "portal-msg";
      div.innerHTML = `<div class="meta">${m.sender} • ${m.when}</div><div class="body">${m.body}</div>`;
      box.appendChild(div);
      window.__lastMsgId = m.id;
      scrollBottom = true;
    }
    if(scrollBottom){ box.scrollTop = box.scrollHeight; }
  },
  async send(ev){
    ev.preventDefault();
    if(!this.activeThread) return false;
    const inp = document.getElementById("chat-input");
    const body = inp.value.trim();
    if(!body) return false;
    await jsonFetch(`/app/api/chat/thread/${this.activeThread}/send/`, {method:"POST", body: JSON.stringify({body})});
    inp.value = "";
    await this.refreshMessages(true);
    return false;
  },
  async newGroup(){
    const title = prompt("Nome do grupo:");
    if(!title) return;
    const emails = prompt("Emails (separados por vírgula) dos membros do escritório:");
    const list = emails ? emails.split(",").map(x=>x.trim()).filter(Boolean) : [];
    const data = await jsonFetch("/app/api/chat/thread/create/", {method:"POST", body: JSON.stringify({title, emails:list})});
    this.activeThread = data.thread_id;
    await this.refreshThreads();
    await this.refreshMessages(true);
  }
};

const PortalCalendar = {
  init(){
    const Calendar = window.FullCalendar.Calendar;
    const Draggable = window.FullCalendar.Draggable;

    const containerEl = document.getElementById('external-events');
    if(containerEl){
      new Draggable(containerEl, {
        itemSelector: '.external-event',
        eventData: function(eventEl) {
          const color = eventEl.getAttribute("data-color") || "#3c8dbc";
          return { title: eventEl.innerText.trim(), backgroundColor: color, borderColor: color };
        }
      });
    }

    const calendarEl = document.getElementById('calendar');
    const calendar = new Calendar(calendarEl, {
      locale: 'pt-br',
      headerToolbar: { left: 'prev,next today', center: 'title', right: 'dayGridMonth,timeGridWeek,timeGridDay' },
      themeSystem: 'bootstrap',
      editable: true,
      droppable: true,
      events: '/app/api/calendar/events/',
      drop: async function(info){
        const rm = document.getElementById('drop-remove');
        if (rm && rm.checked) info.draggedEl.parentNode.removeChild(info.draggedEl);
        try{
          await jsonFetch('/app/api/calendar/events/create/', {method:'POST', body: JSON.stringify({
            title: info.draggedEl.innerText.trim(),
            start: info.dateStr,
            all_day: info.allDay,
            color: info.draggedEl.getAttribute("data-color") || "#3c8dbc",
          })});
          calendar.refetchEvents();
        }catch(e){ alert("Erro ao criar evento: " + e.message); }
      },
      eventDrop: async function(info){
        try{
          await jsonFetch(`/app/api/calendar/events/update/${info.event.id}/`, {method:'POST', body: JSON.stringify({
            start: info.event.start.toISOString(),
            end: info.event.end ? info.event.end.toISOString() : null,
            all_day: info.event.allDay
          })});
        }catch(e){ alert("Erro ao mover: " + e.message); info.revert(); }
      },
      eventResize: async function(info){
        try{
          await jsonFetch(`/app/api/calendar/events/update/${info.event.id}/`, {method:'POST', body: JSON.stringify({
            start: info.event.start.toISOString(),
            end: info.event.end ? info.event.end.toISOString() : null,
            all_day: info.event.allDay
          })});
        }catch(e){ alert("Erro ao redimensionar: " + e.message); info.revert(); }
      },
      eventClick: async function(info){
        if(confirm("Deletar este evento?")){
          await jsonFetch(`/app/api/calendar/events/delete/${info.event.id}/`, {method:"POST", body: "{}"});
          calendar.refetchEvents();
        }
      }
    });
    calendar.render();
  }
};

const ERPTemplates = {
  async init(){
    await this.refresh();
  },
  async refresh(){
    const list = document.getElementById("tpl-list");
    const data = await jsonFetch("/app/api/calendar/templates/list/", {method:"GET", headers: {"Content-Type":"application/json"}});
    list.innerHTML = "";
    if(data.items.length===0){
      list.innerHTML = '<p class="text-muted">Sem modelos.</p>';
      return;
    }
    for(const t of data.items){
      const row = document.createElement("div");
      row.className = "d-flex align-items-center mb-2";
      row.innerHTML = `<span class="badge mr-2" style="background:${t.color}">&nbsp;</span><span class="mr-auto">${t.title}</span>
        <button class="btn btn-sm btn-danger"><i class="fas fa-trash"></i></button>`;
      row.querySelector("button").onclick = async ()=>{
        if(confirm("Deletar?")){
          await jsonFetch(`/app/api/calendar/templates/delete/${t.id}/`, {method:"POST", body:"{}"});
          await this.refresh();
        }
      };
      list.appendChild(row);
    }
  },
  async create(ev){
    ev.preventDefault();
    const title = document.getElementById("tpl-title").value.trim();
    const color = document.getElementById("tpl-color").value.trim();
    if(!title) return false;
    await jsonFetch("/app/api/calendar/templates/create/", {method:"POST", body: JSON.stringify({title, color})});
    document.getElementById("tpl-title").value = "";
    await this.refresh();
    return false;
  }
};

const KanbanUI = {
  boardId: null,
  async init(){
    await this.refresh();
    // live markdown preview
    const md = document.getElementById("card-body-md");
    if(md){
      md.addEventListener("input", ()=>{ document.getElementById("card-preview").innerHTML = MarkedLite.render(md.value); });
    }
  },
  async refresh(){
    const data = await jsonFetch("/app/api/kanban/board/", {method:"GET", headers: {"Content-Type":"application/json"}});
    this.boardId = data.board_id;
    const row = document.getElementById("kanban-columns");
    row.innerHTML = "";
    for(const col of data.columns){
      const colEl = document.createElement("div");
      colEl.className = "col-md-3";
      colEl.innerHTML = `
        <div class="card card-row card-secondary">
          <div class="card-header">
            <h3 class="card-title">${col.title}</h3>
            <div class="card-tools float-right">
              <a href="#" class="btn btn-tool" title="Adicionar card" onclick="KanbanUI.addCard(${col.id}); return false;"><i class="fas fa-plus"></i></a>
              <a href="#" class="btn btn-tool" title="Editar coluna" onclick="KanbanUI.editColumn(${col.id}, '${col.title.replace(/'/g,"&#39;")}'); return false;"><i class="fas fa-pencil-alt"></i></a>
              <a href="#" class="btn btn-tool text-danger" title="Deletar coluna" onclick="KanbanUI.deleteColumn(${col.id}); return false;"><i class="fas fa-trash"></i></a>
            </div>
          </div>
          <div class="card-body">
            <div class="card-column connectedSortable" data-col="${col.id}"></div>
          </div>
        </div>`;
      row.appendChild(colEl);
      const container = colEl.querySelector(".card-column");
      for(const card of col.cards){
        const c = document.createElement("div");
        c.className = "card card-light card-outline";
        c.setAttribute("data-card", card.id);
        c.innerHTML = `
          <div class="card-header">
            <h5 class="card-title"><a href="#" onclick="KanbanUI.viewCard(${card.id}); return false;">#${card.number} ${card.title}</a></h5>
            <div class="card-tools">
              <a href="#" class="btn btn-tool" onclick="KanbanUI.editCard(${card.id}); return false;"><i class="fas fa-pencil-alt"></i></a>
            </div>
          </div>
          <div class="card-body text-sm text-truncate">${card.body_preview}</div>`;
        container.appendChild(c);
      }
    }

    // sortable
    $(".connectedSortable").sortable({
      connectWith: ".connectedSortable",
      placeholder: "sort-highlight",
      forcePlaceholderSize: true,
      zIndex: 999999,
      stop: async (event, ui)=>{
        const cardId = ui.item.attr("data-card");
        const newCol = ui.item.parent().attr("data-col");
        const order = ui.item.index();
        try{
          await jsonFetch("/app/api/kanban/cards/move/", {method:"POST", body: JSON.stringify({card_id: parseInt(cardId), column_id: parseInt(newCol), order})});
        }catch(e){
          alert("Erro ao mover: " + e.message);
          await this.refresh();
        }
      }
    }).disableSelection();
  },
  async addColumn(){
    const title = prompt("Título da coluna:");
    if(!title) return;
    await jsonFetch("/app/api/kanban/columns/create/", {method:"POST", body: JSON.stringify({title})});
    await this.refresh();
  },
  async editColumn(colId, currentTitle){
    const title = prompt("Novo título:", currentTitle);
    if(!title) return;
    await jsonFetch(`/app/api/kanban/columns/update/${colId}/`, {method:"POST", body: JSON.stringify({title})});
    await this.refresh();
  },
  async deleteColumn(colId){
    if(!confirm("Deletar coluna?")) return;
    await jsonFetch(`/app/api/kanban/columns/delete/${colId}/`, {method:"POST", body: "{}"});
    await this.refresh();
  },
  async addCard(colId){
    // cria com defaults
    await jsonFetch("/app/api/kanban/cards/create/", {method:"POST", body: JSON.stringify({column_id: colId, title: "Exemplo", number: Date.now()%100000, body_md: "Texto **exemplo**"})});
    await this.refresh();
  },
  async editCard(cardId){
    const data = await jsonFetch(`/app/api/kanban/cards/detail/${cardId}/`, {method:"GET", headers: {"Content-Type":"application/json"}});
    document.getElementById("card-id").value = data.id;
    document.getElementById("card-title").value = data.title;
    document.getElementById("card-number").value = data.number;
    document.getElementById("card-body-md").value = data.body_md;
    document.getElementById("card-preview").innerHTML = MarkedLite.render(data.body_md);
    $("#cardEditModal").modal("show");
  },
  async saveCard(ev){
    ev.preventDefault();
    const id = document.getElementById("card-id").value;
    const title = document.getElementById("card-title").value.trim();
    const number = parseInt(document.getElementById("card-number").value);
    const body_md = document.getElementById("card-body-md").value;
    await jsonFetch(`/app/api/kanban/cards/update/${id}/`, {method:"POST", body: JSON.stringify({title, number, body_md})});
    $("#cardEditModal").modal("hide");
    await this.refresh();
    return false;
  },
  async viewCard(cardId){
    const data = await jsonFetch(`/app/api/kanban/cards/detail/${cardId}/`, {method:"GET", headers: {"Content-Type":"application/json"}});
    document.getElementById("card-view-title").innerText = `#${data.number} ${data.title}`;
    document.getElementById("card-view-body").innerHTML = MarkedLite.render(data.body_md);
    $("#cardViewModal").modal("show");
  }
};
