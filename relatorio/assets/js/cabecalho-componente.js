(function () {
    'use strict';

    var HOST_SELECTOR = '[data-cabecalho-host]';
    var DEFAULT_FRAGMENT_SRC = '../cabecalho_fragment.html';

    function getInjectedHeaderHost() {
        return document.querySelector(HOST_SELECTOR + '[data-cabecalho-loaded="true"]');
    }

    function getInjectedHeaderElement() {
        var host = getInjectedHeaderHost();

        if (!host) {
            return null;
        }

        return host.querySelector('.sigma-cabecalho-fixo') || host.firstElementChild;
    }

    function syncInjectedLayout() {
        var header = getInjectedHeaderElement();
        var host = getInjectedHeaderHost();
        var sidebar = document.querySelector('.navbar');
        var isDesktop = window.matchMedia('(min-width: 961px)').matches;
        var headerHeight = header ? header.offsetHeight : 0;
        var sidebarWidth = isDesktop && sidebar ? sidebar.offsetWidth : 0;

        document.documentElement.style.setProperty('--relatorio-header-height', headerHeight + 'px');
        document.documentElement.style.setProperty('--relatorio-sidebar-width', sidebarWidth + 'px');
        if (host) {
            host.style.height = headerHeight + 'px';
        }
        document.body.style.paddingTop = '0px';
        document.body.style.paddingLeft = isDesktop ? sidebarWidth + 'px' : '0px';
        document.body.classList.add('cabecalho-injetado-ativo');
    }

    function bindLayoutUpdates() {
        if (document.body.dataset.cabecalhoObserved === 'true') return;

        document.body.dataset.cabecalhoObserved = 'true';
        syncInjectedLayout();
        window.addEventListener('load', syncInjectedLayout);
        window.addEventListener('resize', syncInjectedLayout);
        setTimeout(syncInjectedLayout, 100);
        setTimeout(syncInjectedLayout, 350);

        if ('ResizeObserver' in window) {
            var observer = new ResizeObserver(syncInjectedLayout);
            var header = getInjectedHeaderElement();
            var sidebar = document.querySelector('.navbar');

            if (header) {
                observer.observe(header);
            }

            if (sidebar) {
                observer.observe(sidebar);
            }
        }
    }

    async function runInjectedScripts(host) {
        var scripts = Array.from(host.querySelectorAll('script'));

        for (var index = 0; index < scripts.length; index += 1) {
            var oldScript = scripts[index];
            var newScript = document.createElement('script');

            Array.from(oldScript.attributes).forEach(function (attribute) {
                newScript.setAttribute(attribute.name, attribute.value);
            });

            if (oldScript.src) {
                await new Promise(function (resolve) {
                    newScript.addEventListener('load', resolve, { once: true });
                    newScript.addEventListener('error', resolve, { once: true });
                    oldScript.replaceWith(newScript);
                });
            } else {
                newScript.textContent = oldScript.textContent;
                oldScript.replaceWith(newScript);
            }
        }
    }

    async function injectHeader(host) {
        if (!host || host.dataset.cabecalhoLoaded === 'true' || host.dataset.cabecalhoLoading === 'true') {
            return;
        }

        var fragmentSrc = host.getAttribute('data-cabecalho-src') || DEFAULT_FRAGMENT_SRC;

        host.dataset.cabecalhoLoading = 'true';

        try {
            var response = await fetch(new URL(fragmentSrc, window.location.href).toString(), {
                cache: 'no-cache'
            });

            if (!response.ok) {
                throw new Error('Falha ao carregar cabecalho: ' + response.status);
            }

            host.innerHTML = await response.text();
            host.classList.add('cabecalho-injetado-host');
            await runInjectedScripts(host);
            host.dataset.cabecalhoLoaded = 'true';
            bindLayoutUpdates();
            syncInjectedLayout();
        } catch (error) {
            console.error('Nao foi possivel injetar o cabecalho do relatorio.', error);
        } finally {
            delete host.dataset.cabecalhoLoading;
        }
    }

    function init() {
        document.querySelectorAll(HOST_SELECTOR).forEach(function (host) {
            injectHeader(host);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init, { once: true });
    } else {
        init();
    }
}());