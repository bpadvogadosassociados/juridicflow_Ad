/**
 * JuridicFlow — kanban.js
 * Depende de: jQuery, jQuery UI (sortable), Bootstrap modal, marked.min.js
 * Usa helpers globais (se existirem): apiGet, apiPost, csrfToken
 *
 * Este arquivo existe para manter portal.js enxuto (chat/notificações/busca)
 * e ainda assim suportar a página Kanban (portal/kanban.html).
 */
(function () {
  "use strict";

  // ---------- helpers ----------
  function hasEl(sel) { return document.querySelector(sel) !== null; }

  function ensureApi() {
    if (typeof apiGet !== "function" || typeof apiPost !== "function") {
      console.error("kanban.js: apiGet/apiPost não encontrados. Carregue portal.js antes.");
      return false;
    }
    return true;
  }

  function renderMarkdown(md) {
    if (window.marked) return window.marked.parse(md || "");
    // fallback ultra simples (não ideal, mas evita tela vazia)
    return (md || "").replace(/</g, "&lt;").replace(/\n/g, "<br>");
  }

  function escapeHtml(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // ---------- UI ----------
  function columnHtml(col) {
    const cardsHtml = (col.cards || []).map(cardHtml).join("");
    return `
      <div class="col-md-3 kanban-col" data-col-id="${col.id}">
        <div class="card card-outline card-primary">
          <div class="card-header d-flex align-items-center justify-content-between">
            <h3 class="card-title mb-0">${escapeHtml(col.title)}</h3>
            <div class="card-tools">
              <button class="btn btn-xs btn-light js-add-card" title="Nova tarefa"><i class="fas fa-plus"></i></button>
              <button class="btn btn-xs btn-light js-rename-col" title="Renomear coluna"><i class="fas fa-pen"></i></button>
              <button class="btn btn-xs btn-light js-del-col" title="Excluir coluna"><i class="fas fa-trash"></i></button>
            </div>
          </div>
          <div class="card-body p-2">
            <div class="kanban-cards" data-col-id="${col.id}">
              ${cardsHtml || ""}
            </div>
          </div>
        </div>
      </div>
    `;
  }

  function cardHtml(card) {
    const title = escapeHtml(card.title);
    const num = card.number != null ? `#${card.number}` : "";
    return `
      <div class="kanban-card card card-light mb-2" data-card-id="${card.id}">
        <div class="card-body p-2">
          <div class="d-flex align-items-start justify-content-between" style="gap:.5rem;">
            <div class="flex-grow-1">
              <div class="text-muted" style="font-size:.8rem">${escapeHtml(num)}</div>
              <div class="font-weight-bold">${title}</div>
            </div>
            <div class="btn-group btn-group-sm">
              <button class="btn btn-light js-view-card" title="Ver"><i class="fas fa-eye"></i></button>
              <button class="btn btn-light js-edit-card" title="Editar"><i class="fas fa-edit"></i></button>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  // ---------- main object ----------
  const PortalKanban = {
    board: null,
    root: null,

    async init() {
      if (!hasEl("#kanban-root")) return;
      if (!ensureApi()) return;

      this.root = document.getElementById("kanban-root");

      // bind "Adicionar coluna"
      const btnAddCol = document.getElementById("kanban-add-column");
      if (btnAddCol) btnAddCol.addEventListener("click", (e) => {
        e.preventDefault();
        this.createColumn();
      });

      // bind modal form
      const form = document.getElementById("card-edit-form");
      if (form) form.addEventListener("submit", (e) => this.saveCard(e));

      const md = document.getElementById("card-body-md");
      if (md) md.addEventListener("input", () => this.updatePreview());

      await this.reloadBoard();
    },

    async reloadBoard() {
      this.root.innerHTML = `
        <div class="col-12 text-center text-muted py-5">
          <i class="fas fa-spinner fa-spin fa-2x"></i>
          <p class="mt-2">Carregando board...</p>
        </div>
      `;

      const data = await apiGet("/app/api/kanban/board/");
      this.board = data;

      const cols = (data.columns || []).sort((a,b)=> (a.order||0)-(b.order||0));
      this.root.innerHTML = cols.map(columnHtml).join("");

      this.bindColumnActions();
      this.enableDragAndDrop();
    },

    bindColumnActions() {
      this.root.querySelectorAll(".kanban-col").forEach(colEl => {
        const colId = parseInt(colEl.getAttribute("data-col-id"), 10);

        colEl.querySelector(".js-add-card")?.addEventListener("click", (e) => {
          e.preventDefault();
          this.openEditModal({ id: "", title: "", number: "", body_md: "", column_id: colId });
        });

        colEl.querySelector(".js-rename-col")?.addEventListener("click", async (e) => {
          e.preventDefault();
          const current = colEl.querySelector(".card-title")?.textContent?.trim() || "";
          const title = prompt("Novo título da coluna:", current);
          if (!title) return;
          // IMPORTANTE: endpoint atual no urls.py usa col_id; se o backend estiver com bug de nome de parâmetro,
          // isso pode retornar 500. Veja nota no final da resposta.
          await apiPost(`/app/api/kanban/columns/update/${colId}/`, { title });
          await this.reloadBoard();
        });

        colEl.querySelector(".js-del-col")?.addEventListener("click", async (e) => {
          e.preventDefault();
          if (!confirm("Excluir coluna e todos os cards?")) return;
          await apiPost(`/app/api/kanban/columns/delete/${colId}/`, {});
          await this.reloadBoard();
        });

        // card actions
        colEl.querySelectorAll(".kanban-card").forEach(cardEl => {
          const cardId = parseInt(cardEl.getAttribute("data-card-id"), 10);

          cardEl.querySelector(".js-edit-card")?.addEventListener("click", async (e) => {
            e.preventDefault();
            const card = await apiGet(`/app/api/kanban/cards/detail/${cardId}/`);
            this.openEditModal(card);
          });

          cardEl.querySelector(".js-view-card")?.addEventListener("click", async (e) => {
            e.preventDefault();
            const card = await apiGet(`/app/api/kanban/cards/detail/${cardId}/`);
            this.openViewModal(card);
          });
        });
      });
    },

    enableDragAndDrop() {
      if (!window.jQuery || !jQuery.fn.sortable) {
        console.warn("kanban.js: jQuery UI sortable não encontrado; drag-and-drop desativado.");
        return;
      }

      // cards sortable within and across columns
      jQuery(".kanban-cards").sortable({
        connectWith: ".kanban-cards",
        placeholder: "kanban-card-placeholder",
        forcePlaceholderSize: true,
        tolerance: "pointer",
        start: function(e, ui){
          ui.placeholder.height(ui.item.height());
        },
        update: async (e, ui) => {
          // Called for both source and destination lists; only act on the list that contains the moved item
          const $list = jQuery(e.target);
          const colId = parseInt($list.attr("data-col-id"), 10);

          // Recompute order for this column
          const cardIds = $list.children(".kanban-card").map(function(){ return parseInt(this.getAttribute("data-card-id"), 10); }).get();

          // update each card order; also ensure column move for the moved card
          for (let i = 0; i < cardIds.length; i++) {
            const id = cardIds[i];
            // use card_move to set column + order for every card in this column (simple, reliable)
            await apiPost("/app/api/kanban/cards/move/", { card_id: id, column_id: colId, order: i + 1 });
          }
        }
      }).disableSelection();
    },

    openEditModal(card) {
      document.getElementById("card-id").value = card.id || "";
      document.getElementById("card-title").value = card.title || "";
      document.getElementById("card-number").value = card.number || "";
      document.getElementById("card-body-md").value = card.body_md || "";
      document.getElementById("card-column-id").value = card.column_id || card.columnId || "";

      const modalTitle = document.getElementById("card-modal-title");
      if (modalTitle) modalTitle.textContent = card.id ? "Editar Tarefa" : "Nova Tarefa";

      this.updatePreview();
      if (window.jQuery) jQuery("#cardEditModal").modal("show");
    },

    openViewModal(card) {
      const t = document.getElementById("cardViewTitle");
      const b = document.getElementById("cardViewBody");
      if (t) t.textContent = `#${card.number || ""} ${card.title || ""}`.trim();
      if (b) b.innerHTML = renderMarkdown(card.body_md || "");
      if (window.jQuery) jQuery("#cardViewModal").modal("show");
    },

    updatePreview() {
      const md = document.getElementById("card-body-md")?.value || "";
      const box = document.getElementById("card-preview");
      if (box) box.innerHTML = renderMarkdown(md);
    },

    async saveCard(e) {
      e.preventDefault();
      const id = document.getElementById("card-id").value;
      const column_id = parseInt(document.getElementById("card-column-id").value, 10);
      const title = document.getElementById("card-title").value.trim();
      const body_md = document.getElementById("card-body-md").value || "";

      if (!title) {
        alert("Título obrigatório");
        return;
      }
      if (!column_id) {
        alert("Erro: column_id obrigatório");
        return;
      }

      if (!id) {
        // create
        const r = await apiPost("/app/api/kanban/cards/create/", { column_id, title, body_md });
        if (!r.ok) {
          alert(r.error || "Erro ao criar card");
          return;
        }
      } else {
        // update
        const r = await apiPost(`/app/api/kanban/cards/update/${id}/`, { title, body_md });
        if (!r.ok && r.ok !== undefined) {
          alert(r.error || "Erro ao salvar card");
          return;
        }
      }

      if (window.jQuery) jQuery("#cardEditModal").modal("hide");
      await this.reloadBoard();
    },

    async createColumn() {
      const title = prompt("Título da nova coluna:");
      if (!title) return;
      const r = await apiPost("/app/api/kanban/columns/create/", { title });
      if (!r.ok) {
        alert(r.error || "Erro ao criar coluna");
        return;
      }
      await this.reloadBoard();
    }
  };

  // auto-boot only on kanban page
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => PortalKanban.init());
  } else {
    PortalKanban.init();
  }

  window.PortalKanban = PortalKanban;
})();
