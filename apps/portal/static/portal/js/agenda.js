/**
 * JuridicFlow — agenda.js
 * Depende de: FullCalendar (main.js), moment (opcional), AdminLTE assets
 * Usa helpers globais (se existirem): apiGet, apiPost
 *
 * Inicializa a agenda na página portal/agenda.html.
 */
(function () {
  "use strict";

  function hasEl(sel) { return document.querySelector(sel) !== null; }

  function ensureApi() {
    if (typeof apiGet !== "function" || typeof apiPost !== "function") {
      console.error("agenda.js: apiGet/apiPost não encontrados. Carregue portal.js antes.");
      return false;
    }
    return true;
  }

  function parseExternalEvents() {
    const container = document.getElementById("external-events");
    if (!container || !window.FullCalendar) return;

    // FullCalendar Draggable (v5+)
    if (FullCalendar.Draggable) {
      new FullCalendar.Draggable(container, {
        itemSelector: ".external-event",
        eventData: function (eventEl) {
          return {
            title: eventEl.innerText.trim(),
            color: eventEl.getAttribute("data-color") || undefined,
          };
        }
      });
    }
  }

  const PortalCalendar = {
    calendar: null,

    async init() {
      if (!hasEl("#calendar")) return;
      if (!ensureApi()) return;
      if (!window.FullCalendar) {
        console.error("agenda.js: FullCalendar não encontrado. Verifique includes do template.");
        return;
      }

      parseExternalEvents();

      const calendarEl = document.getElementById("calendar");
      const self = this;

      self.calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: "dayGridMonth",
        height: "auto",
        headerToolbar: {
          left: "prev,next today",
          center: "title",
          right: "dayGridMonth,timeGridWeek,timeGridDay"
        },
        editable: true,
        droppable: true,
        selectable: true,

        events: async function (fetchInfo, successCallback, failureCallback) {
          try {
            const qs = new URLSearchParams({
              start: fetchInfo.startStr,
              end: fetchInfo.endStr,
            }).toString();
            const data = await apiGet(`/app/api/calendar/events/?${qs}`);
            successCallback(data);
          } catch (e) {
            console.error(e);
            failureCallback(e);
          }
        },

        // Create by selecting range
        select: async function (info) {
          const title = prompt("Título do evento:");
          if (!title) return;

          const payload = {
            title,
            start: info.startStr,
            end: info.endStr || null,
            all_day: info.allDay,
            color: "#3c8dbc",
          };
          const r = await apiPost("/app/api/calendar/events/create/", payload);
          if (r.ok) {
            self.calendar.refetchEvents();
          } else {
            alert(r.error || "Erro ao criar evento");
          }
        },

        // Drop from external template
        drop: async function (info) {
          const title = info.draggedEl.innerText.trim();
          const color = info.draggedEl.getAttribute("data-color") || "#3c8dbc";
          const payload = {
            title,
            start: info.dateStr,
            all_day: info.allDay || false,
            color
          };
          const r = await apiPost("/app/api/calendar/events/create/", payload);
          if (!r.ok) alert(r.error || "Erro ao criar evento");
          self.calendar.refetchEvents();

          const removeAfter = document.getElementById("drop-remove");
          if (removeAfter && removeAfter.checked) info.draggedEl.parentNode.removeChild(info.draggedEl);
        },

        eventDrop: async function (info) {
          const payload = {
            start: info.event.start ? info.event.start.toISOString() : null,
            end: info.event.end ? info.event.end.toISOString() : null,
            all_day: info.event.allDay,
          };
          const r = await apiPost(`/app/api/calendar/events/update/${info.event.id}/`, payload);
          if (!r.ok) {
            alert(r.error || "Erro ao mover evento");
            info.revert();
          }
        },

        eventResize: async function (info) {
          const payload = {
            start: info.event.start ? info.event.start.toISOString() : null,
            end: info.event.end ? info.event.end.toISOString() : null,
          };
          const r = await apiPost(`/app/api/calendar/events/update/${info.event.id}/`, payload);
          if (!r.ok) {
            alert(r.error || "Erro ao redimensionar evento");
            info.revert();
          }
        },

        eventClick: async function (info) {
          const ok = confirm(`Excluir evento: "${info.event.title}"?`);
          if (!ok) return;
          const r = await apiPost(`/app/api/calendar/events/delete/${info.event.id}/`, {});
          if (r.ok) self.calendar.refetchEvents();
          else alert(r.error || "Erro ao excluir evento");
        },
      });

      self.calendar.render();
    }
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => PortalCalendar.init());
  } else {
    PortalCalendar.init();
  }

  window.PortalCalendar = PortalCalendar;
})();
