/* Navegação compartilhada. O conteúdo técnico permanece nos documentos HTML. */
(() => {
  'use strict';
  const pages = [['index.html','Introdução'],['objetivos.html','Objetivos'],['dados.html','Dados'],['metodologia.html','Metodologia'],['resultados.html','Resultados'],['discussao.html','Discussão'],['conclusao.html','Conclusão'],['anexo-mapas.html','Mapas e malha'],['dashboard.html','Dashboard'],['glossario.html','Glossário']];
  function init() {
    const current = location.pathname.split('/').pop() || 'index.html';
    const page = pages.find(([file]) => file === current) || pages[0];
    document.body.classList.add('study-ready');
    document.querySelector('[data-cabecalho-host]')?.remove();
    const header = document.createElement('header');
    header.className = 'study-topbar';
    header.innerHTML = `<a class="study-wordmark" href="index.html" aria-label="PLI — início do estudo">PLI <span>Estudos territoriais</span></a><div class="study-topbar-links"><a href="https://56.125.163.194/pli-hub/">← PLI Hub</a><a href="glossario.html">Glossário</a><button class="menu-toggle" aria-controls="study-navigation" aria-expanded="false">Menu</button></div>`;
    document.body.prepend(header);
    let nav = document.querySelector('.navbar');
    if (!nav) {nav=document.createElement('nav');nav.className='navbar';header.after(nav);}
    nav.id='study-navigation';nav.setAttribute('aria-label','Seções do estudo');
    nav.innerHTML = `<a href="index.html" class="navbar-brand"><span class="nav-eyebrow">São Paulo · Rodovias</span>Densidade<br>de Malha</a><div><p class="nav-caption">Conteúdo do estudo</p><ul class="navbar-menu">${pages.map(([file,label],i)=>`<li><a href="${file}" data-number="${String(i+1).padStart(2,'0')}"${file===current?' class="active" aria-current="page"':''}>${label}</a></li>`).join('')}</ul></div><div class="nav-footnote"><strong>DER/SP · IBGE</strong>Análise Geoespacial<br>Revisão: setembro 2026</div>`;
    const toggle=header.querySelector('.menu-toggle');
    const closeMenu=()=>{nav.classList.remove('is-open');toggle.setAttribute('aria-expanded','false');};
    toggle.addEventListener('click',()=>{const open=nav.classList.toggle('is-open');toggle.setAttribute('aria-expanded',String(open));if(open)nav.querySelector('.active')?.focus();});
    document.addEventListener('keydown',e=>{if(e.key==='Escape'&&nav.classList.contains('is-open')){closeMenu();toggle.focus();}});
    document.addEventListener('click',e=>{if(!nav.contains(e.target)&&!toggle.contains(e.target))closeMenu();});
    const hero=document.querySelector('.hero')||document.querySelector('.glossary');if(!hero)return;
    const breadcrumb=document.createElement('div');breadcrumb.className='study-breadcrumb';breadcrumb.innerHTML=`<a href="index.html">Estudo rodoviário</a><span aria-hidden="true">/</span><span>${page[1]}</span>`;hero.before(breadcrumb);
    if(!hero.id)hero.id='conteudo';hero.setAttribute('tabindex','-1');
    const skip=document.createElement('a');skip.className='skip-link';skip.href='#'+hero.id;skip.textContent='Ir para o conteúdo';document.body.prepend(skip);
    if(current==='index.html'){
      hero.classList.add('home-hero');const figure=document.createElement('figure');figure.className='hero-map';
      figure.innerHTML='<figcaption><strong>Malha viária DER/SP</strong><span>São Paulo</span></figcaption><img src="assets/images/malha-sp.svg" alt="Rede do cadastro DER/SP: SP, SPA, SPI e BR; linhas coloridas por tipo de rodovia." width="800" height="560"><a href="anexo-mapas.html">Explorar os mapas do estudo ↗</a>';hero.append(figure);
      const overview=document.querySelector('.stats-container')?.closest('.section');if(overview){overview.classList.add('home-overview');hero.after(overview);}
    }else if(current!=='glossario.html'){
      const headings=Array.from(document.querySelectorAll('.section-header h2,.questao-header h2'));
      if(headings.length){const index=document.createElement('details');index.className='page-index';const summary=document.createElement('summary');summary.textContent='Nesta página';index.append(summary);const links=document.createElement('nav');links.setAttribute('aria-label','Nesta página');index.append(links);headings.forEach((h,i)=>{if(!h.id)h.id='secao-'+(i+1);const a=document.createElement('a');a.href='#'+h.id;a.textContent=h.textContent.trim();links.append(a);});hero.after(index);}
    }
    document.querySelectorAll('iframe').forEach((frame,i)=>{if(!frame.title)frame.title=frame.closest('.map-card,.map-panel,.questao-container')?.querySelector('h3,h2')?.textContent.trim()||'Mapa interativo '+(i+1);});
    document.querySelectorAll('.topic-header').forEach((h,i)=>{
      const content=h.parentElement.querySelector('.topic-content');if(!content)return;
      h.removeAttribute('onclick');h.setAttribute('role','button');h.tabIndex=0;content.id=content.id||'topico-'+i;h.setAttribute('aria-controls',content.id);
      const sync=()=>h.setAttribute('aria-expanded',String(h.parentElement.classList.contains('open')));sync();
      const flip=()=>{h.parentElement.classList.toggle('open');sync();};h.addEventListener('click',flip);h.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();flip();}});
    });
    document.querySelectorAll('.granularity-tab').forEach(button=>{
      const match=button.getAttribute('onclick')?.match(/showMaps\(['"]([^'"]+)['"]\)/);if(!match)return;
      button.removeAttribute('onclick');button.setAttribute('aria-controls','maps-'+match[1]);button.setAttribute('aria-pressed',String(button.classList.contains('active')));
      button.addEventListener('click',()=>{document.querySelectorAll('.maps-section').forEach(section=>section.classList.toggle('active',section.id==='maps-'+match[1]));document.querySelectorAll('.granularity-tab').forEach(tab=>{tab.classList.toggle('active',tab===button);tab.setAttribute('aria-pressed',String(tab===button));});});
    });
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
