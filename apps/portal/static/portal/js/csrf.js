/**
 * CSRF Utility - JuridicFlow Portal
 * 
 * Inclua este script ANTES de qualquer outro JS que faça fetch/ajax.
 * Garante que todas as requisições POST/PUT/PATCH/DELETE enviem o token CSRF.
 * 
 * Uso:
 *   // Em qualquer JS do portal:
 *   const resp = await portalFetch('/app/api/kanban/cards/create/', {
 *       method: 'POST',
 *       body: JSON.stringify({ title: 'Nova tarefa' })
 *   });
 *   const data = await resp.json();
 */

(function () {
    'use strict';

    // Lê o CSRF token do cookie (Django seta automaticamente)
    function getCSRFToken() {
        const name = 'csrftoken';
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            cookie = cookie.trim();
            if (cookie.startsWith(name + '=')) {
                return decodeURIComponent(cookie.substring(name.length + 1));
            }
        }
        // Fallback: busca do input hidden ({% csrf_token %})
        const input = document.querySelector('[name=csrfmiddlewaretoken]');
        return input ? input.value : '';
    }

    // Métodos que NÃO precisam de CSRF (safe methods)
    const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS', 'TRACE']);

    /**
     * Wrapper do fetch que injeta CSRF automaticamente.
     * Mesma API do fetch() nativo.
     */
    function portalFetch(url, options = {}) {
        const method = (options.method || 'GET').toUpperCase();

        if (!SAFE_METHODS.has(method)) {
            options.headers = options.headers || {};

            // Não sobrescreve se já definido
            if (!options.headers['X-CSRFToken']) {
                options.headers['X-CSRFToken'] = getCSRFToken();
            }

            // Default content-type para JSON se body é string
            if (typeof options.body === 'string' && !options.headers['Content-Type']) {
                options.headers['Content-Type'] = 'application/json';
            }
        }

        return fetch(url, options);
    }

    // Expõe globalmente
    window.portalFetch = portalFetch;
    window.getCSRFToken = getCSRFToken;

    // Também configura jQuery.ajax se jQuery estiver presente (AdminLTE usa jQuery)
    if (typeof $ !== 'undefined' && $.ajaxSetup) {
        $.ajaxSetup({
            beforeSend: function (xhr, settings) {
                if (!SAFE_METHODS.has(settings.type.toUpperCase())) {
                    xhr.setRequestHeader('X-CSRFToken', getCSRFToken());
                }
            }
        });
    }
})();