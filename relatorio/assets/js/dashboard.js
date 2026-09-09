/* Modelo único: os filtros alimentam indicadores, mapa, gráficos e tabela. */
(() => {
  'use strict';
  const root = document.querySelector('[data-dashboard]');
  if (!root) return;
  const base = root.dataset.base || 'assets/data/';
  const config = window.MAP_CONFIG || {};
  const titles = {municipios:'Municípios',imediatas:'Regiões Geográficas Imediatas',intermediarias:'Regiões Geográficas Intermediárias',administrativas:'Regiões Administrativas',zee:'Grupos de Análise Integrada do ZEE'};
  const metrics = {
    extensao:{label:'Extensão cadastral de rodovias',unit:'km',digits:2},
    densidade:{label:'Densidade rodoviária por área',unit:'km/km²',digits:4},
    percapita:{label:'Extensão rodoviária por população',unit:'km/10.000 habitantes',digits:2},
    concessao:{label:'Participação da extensão concessionada',unit:'%',digits:1},
    urbano:{label:'Participação da extensão em trechos classificados como urbanos',unit:'%',digits:1},
    urbanizado:{label:'Extensão estimada dentro de áreas urbanizadas',unit:'km',digits:2},
    sp:{label:'Participação dos eixos SP na extensão',unit:'%',digits:1},
    spa:{label:'Extensão dos acessos SPA',unit:'km',digits:2},
    desvio:{label:'Desvio da densidade por área em relação ao estado',unit:'%',digits:1},
    popkm:{label:'População por extensão rodoviária',unit:'habitantes/km',digits:1}
  };
  const colors = {SP:'#ba483c',SPA:'#bd731e',SPI:'#6d5ca0',BR:'#236ba0',Outros:'#56666a'};
  const roadNames = {SP:'SP — eixo',SPA:'SPA — acesso',SPI:'SPI — interligação',BR:'BR — código federal',Outros:'Outros códigos'};
  const palette = ['#eff4eb','#c1d6b7','#7eaf89','#367d66','#114a43'];
  const $ = id => document.getElementById(id);
  const esc = s => String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt = (n,d=2) => Number.isFinite(n) ? n.toLocaleString('pt-BR',{maximumFractionDigits:d,minimumFractionDigits:d}) : 'Sem valor';
  const sum = (rows,key) => rows.reduce((a,r)=>a+(r[key]||0),0);
  let data, rows=[], selected=[], polygons, roadLayer, geometry, model, map, requestId=0, tablePage=0;
  const cache = new Map();
  async function get(name) {
    if (!cache.has(name)) cache.set(name,fetch(base+name).then(r=>{if(!r.ok)throw Error('Falha ao carregar '+name);return r.json();}));
    return cache.get(name);
  }
  function options(id, values, first) {
    $(id).innerHTML=(first?`<option value="">${esc(first)}</option>`:'')+values.map(v=>`<option value="${esc(Array.isArray(v)?v[0]:v)}">${esc(Array.isArray(v)?v[1]:v)}</option>`).join('');
  }
  function group(records,field) {
    const out=new Map();records.forEach(r=>out.set(r[field],(out.get(r[field])||0)+r.extensao));return [...out].sort((a,b)=>b[1]-a[1]);
  }
  function aggregate(unit, records, reference) {
    const extent=sum(records,'extensao');
    return {...unit,extensao:extent,trechos:records.length,
      densidade:extent/unit.area,percapita:extent/unit.populacao*10000,
      concessao:extent?sum(records.filter(r=>r.administracao==='Concessionária'),'extensao')/extent*100:null,
      urbano:extent?sum(records.filter(r=>r.localizacao==='Urbano'),'extensao')/extent*100:null,
      urbanizado:sum(records,'urbano_estimado_km'),
      sp:extent?sum(records.filter(r=>r.tipo==='SP'),'extensao')/extent*100:null,
      spa:sum(records.filter(r=>r.tipo==='SPA'),'extensao'),
      desvio:reference>0?(extent/unit.area/reference-1)*100:null,
      popkm:extent?unit.populacao/extent:null};
  }
  function bars(id, entries, unit='km', click=false) {
    if(!$(id))return;
    const max=Math.max(...entries.map(x=>Math.abs(x[1])),1);
    $(id).innerHTML=entries.length?entries.map(([name,value,key])=>`<${click?'button':'div'} class="bar-row" ${click?`type="button" data-unit="${esc(key)}"`:''}><span>${esc(name)}</span><span class="bar-track"><i style="width:${Math.abs(value)/max*100}%"></i></span><b>${fmt(value,unit==='municípios'?0:2)} <small>${esc(unit)}</small></b></${click?'button':'div'}>`).join(''):'<p>Nenhum trecho corresponde aos filtros.</p>';
    if(click)$(id).querySelectorAll('[data-unit]').forEach(b=>b.onclick=()=>{$('territorio').value=b.dataset.unit;update(true);});
  }
  function renderTable() {
    if(!$('table-body'))return;
    const metric=$('indicador').value;
    const query=$('table-search').value.normalize('NFD').replace(/\p{M}/gu,'').toLowerCase();
    const filtered=rows.filter(r=>r.nome.normalize('NFD').replace(/\p{M}/gu,'').toLowerCase().includes(query)).sort((a,b)=>(b[metric]??-Infinity)-(a[metric]??-Infinity));
    const pages=Math.max(1,Math.ceil(filtered.length/25));tablePage=Math.min(tablePage,pages-1);
    $('table-body').innerHTML=filtered.slice(tablePage*25,(tablePage+1)*25).map(r=>`<tr><th scope="row"><button data-unit="${esc(r.id)}">${esc(r.nome)}</button></th><td>${fmt(r.extensao)}</td><td>${fmt(r.densidade,4)}</td><td>${fmt(r.percapita)}</td><td>${fmt(r.concessao,1)}</td><td>${fmt(r.trechos,0)}</td><td>${fmt(r.populacao,0)}</td></tr>`).join('');
    $('table-count').textContent=`${filtered.length} unidades · Página ${tablePage+1} de ${pages} (até 25 linhas). Ordenação: ${metrics[metric].label.toLowerCase()}, decrescente.`;
    $('table-prev').disabled=tablePage===0;$('table-next').disabled=tablePage>=pages-1;
    $('table-body').querySelectorAll('button').forEach(b=>b.onclick=()=>{$('territorio').value=b.dataset.unit;update(true);});
  }
  function updateCharts(metric) {
    if(!$('kpis'))return;
    const cards=[['Extensão cadastral',model.extensao,'km',2],['Densidade por área',model.densidade,'km/km²',4],['Extensão por população',model.percapita,'km/10.000 habitantes',2],['Extensão concessionada',model.concessao,'%',1],['Trechos selecionados',model.trechos,'registros',0],['População do território',model.populacao,'habitantes · Censo 2022',0]];
    $('kpis').innerHTML=cards.map(([label,value,unit,digits])=>`<article class="kpi"><h2>${label}</h2><strong>${fmt(value,digits)}</strong><span>${unit}</span></article>`).join('');
    bars('administracao-bars',group(selected,'administracao'));
    bars('tipo-bars',group(selected,'tipo'));
    bars('urbano-bars',group(selected,'localizacao'));
    bars('pista-bars',group(selected,'pista'));
    bars('ranking',rows.filter(r=>Number.isFinite(r[metric])).sort((a,b)=>b[metric]-a[metric]).slice(0,15).map(r=>[r.nome,r[metric],r.id]),metrics[metric].unit,true);
    $('ranking-title').textContent=`Maiores valores: ${metrics[metric].label.toLowerCase()}`;
    $('urban-detail').textContent=`${fmt(model.urbanizado)} km estimados dentro das áreas urbanizadas de 2019. A extensão dos trechos da classe “Urbano” inclui também suas partes fora da mancha; são medidas diferentes.`;
    const edges=[0,20,40,60,80,100,Infinity];
    const counts=edges.slice(0,-1).map((lo,i)=>[i===5?'100 km ou mais':`${lo} a menos de ${edges[i+1]} km`,rows.filter(r=>r.extensao>=lo&&r.extensao<edges[i+1]).length]);
    bars('histogram',counts,'municípios');
    $('histogram-title').textContent='Unidades territoriais por faixa de extensão cadastral';
    $('histogram').querySelectorAll('small').forEach(e=>e.textContent='unidades');
    renderTable();
  }
  async function update(fit=false) {
    const ticket=++requestId;
    tablePage=0;
    $('dashboard-status').textContent='Atualizando visualizações…';
    const level=$('recorte').value, territory=$('territorio').value, metric=$('indicador').value;
    const filters=['administracao','tipo','pista','localizacao'];
    const search=$('rodovia').value.trim().toUpperCase();
    const statewide=data.trechos.filter(r=>filters.every(k=>!$(k).value||r[k]===$(k).value)&&(!search||r.rodovia.toUpperCase().includes(search)));
    selected=statewide.filter(r=>!territory||r[level]===territory);
    const units=data.recortes[level].filter(u=>!territory||u.id===territory);
    const reference=sum(statewide,'extensao')/sum(data.recortes[level],'area');
    const byUnit=new Map(units.map(u=>[u.id,[]]));selected.forEach(r=>byUnit.get(r[level])?.push(r));
    rows=units.map(u=>aggregate(u,byUnit.get(u.id),reference));
    model=aggregate({area:sum(units,'area'),populacao:sum(units,'populacao'),nome:territory?units[0].nome:'Estado de São Paulo'},selected,reference);
    updateCharts(metric);
    const context=territory?units[0].nome:titles[level];
    $('map-title').textContent=`${metrics[metric].label} — ${context}`;
    $('selection-context').textContent=`${context} · ${selected.length.toLocaleString('pt-BR')} registros · ${fmt(model.extensao)} km · ${filters.filter(k=>$(k).value).map(k=>$(k).value).join(' / ')||'Todas as categorias'}${search?' · Rodovia: '+search:''}`;
    const geo=await get(level+'.geojson');
    if(ticket!==requestId)return;
    if(polygons)map.removeLayer(polygons);
    if(roadLayer)map.removeLayer(roadLayer);
    const lookup=new Map(rows.map(r=>[r.id,r]));
    const values=rows.map(r=>r[metric]).filter(Number.isFinite);
    let low=Math.min(...values),high=Math.max(...values);
    const diverging=metric==='desvio';
    if(diverging){high=Math.max(Math.abs(low),Math.abs(high));low=-high;}
    const ramp=diverging?['#8b5741','#d5ae8d','#f2f0e4','#8db9ae','#246858']:palette;
    const positive=values.filter(v=>v>0).sort((a,b)=>a-b);
    const quantiles=!diverging&&$('classificacao').value==='quantis'&&positive.length;
    const boundaries=quantiles?Array.from({length:5},(_,i)=>positive[Math.min(positive.length-1,Math.ceil(positive.length*(i+1)/5)-1)]):Array.from({length:5},(_,i)=>low+(high-low)*(i+1)/5);
    const color=v=>!Number.isFinite(v)?'#d6dbdf':v===0&&!diverging?'#fff':ramp[Math.max(0,boundaries.findIndex(b=>v<=b))];
    const showPolygons=$('territorial').checked;
    polygons=L.geoJSON(geo,{filter:f=>lookup.has(f.properties.id),style:f=>({color:'#778c87',weight:.6,fillColor:color(lookup.get(f.properties.id)[metric]),fillOpacity:showPolygons?.72:0}),onEachFeature:(f,l)=>{
      const r=lookup.get(f.properties.id);
      l.bindTooltip(`<strong>${esc(r.nome)}</strong><br>${esc(metrics[metric].label)}: ${fmt(r[metric],metrics[metric].digits)} ${esc(metrics[metric].unit)}<br>Extensão: ${fmt(r.extensao)} km<br>População: ${fmt(r.populacao,0)} habitantes`);
      l.on('click',()=>{$('territorio').value=r.id;update(true);});
    }}).addTo(map);
    const recordIndex=new Map(selected.map(r=>[r.id,r]));
    if($('malha').checked){
      const roadGeo=await get('malha.geojson');if(ticket!==requestId)return;
      roadLayer=L.geoJSON(roadGeo,{filter:f=>recordIndex.has(f.properties.id),style:f=>({color:colors[recordIndex.get(f.properties.id).tipo]||colors.Outros,weight:2,opacity:.9,dashArray:recordIndex.get(f.properties.id).pista==='PLAN'?'6 4':null}),onEachFeature:(f,l)=>{
        const r=recordIndex.get(f.properties.id);l.bindTooltip(`<strong>${esc(r.rodovia)}</strong> · ${esc(r.id)}<br>Extensão cadastral do registro: ${fmt(r.extensao,3)} km<br>${esc(r.administracao)} · ${esc(r.pista)}<br>Classe por mancha IBGE: ${esc(r.localizacao)}<br>Proporção dentro da mancha: ${fmt(r.proporcao_urbanizada*100,1)}%<br>Perímetro urbano cadastrado no DER: ${esc(r.perimetro)}`);
      }}).addTo(map);
    }
    if(fit)map.fitBounds(polygons.getBounds(),{padding:[18,18],maxZoom:11,animate:false});
    let scale='';
    if(showPolygons&&values.length){
      scale=ramp.map((c,i)=>i>0&&boundaries[i]===boundaries[i-1]?'':`<span><i style="background:${c}"></i>${i===0?'Até':'> '+fmt(boundaries[i-1],metrics[metric].digits)+' até'} ${fmt(boundaries[i],metrics[metric].digits)}</span>`).join('');
      if(high===low)scale=`<span><i style="background:${color(low)}"></i>Valor único: ${fmt(low,metrics[metric].digits)}</span>`;
      if(!diverging&&!positive.length)scale='';
    }
    $('map-legend').innerHTML=`${showPolygons?`<strong>Polígonos: ${esc(metrics[metric].label)} (${esc(metrics[metric].unit)})</strong><div class="legend-items">${scale}${!diverging?'<span><i style="background:#fff"></i>Zero</span>':''}<span><i style="background:#d6dbdf"></i>Sem valor: denominador zero</span></div><p>${quantiles?'Quintis dos valores positivos':'Intervalos iguais'} no recorte exibido; limites arredondados. ${diverging?`Referência estadual com os filtros de malha: ${fmt(reference,4)} km/km².`:''}</p>`:''}${$('malha').checked?`<strong>Linhas: cadastro rodoviário por tipo (categoria, sem unidade)</strong><div class="legend-items">${Object.entries(colors).map(([k,c])=>`<span><i class="line-swatch" style="background:${c}"></i>${roadNames[k]}</span>`).join('')}<span>Tracejado: PLAN (planejada)</span></div>`:''}`;
    $('dashboard-status').textContent=selected.length?`Visualizações atualizadas. ${rows.length} unidades territoriais.`:'Nenhum trecho corresponde aos filtros. Extensão zero; percentuais sem denominador ficam sem valor.';
    window.malhaDashboard={rows,model,selected,reference,level,metric,map,polygons,roadLayer};
    root.dataset.ready='true';
  }
  async function start() {
    data=await get('indicadores.json');
    options('recorte',Object.entries(titles));options('indicador',Object.entries(metrics).map(([k,v])=>[k,`${v.label} (${v.unit})`]));
    for(const field of ['administracao','tipo','pista','localizacao'])options(field,[...new Set(data.trechos.map(r=>r[field]))].sort(),'Todas');
    $('recorte').value=config.level||'municipios';$('indicador').value=config.metric||'densidade';
    function units(){options('territorio',data.recortes[$('recorte').value].slice().sort((a,b)=>a.nome.localeCompare(b.nome,'pt-BR')).map(u=>[u.id,u.nome]),'Todo o estado');}
    units();
    map=L.map('dashboard-map',{preferCanvas:true,scrollWheelZoom:false,zoomSnap:.25});
    map.attributionControl.setPrefix('<a href="https://leafletjs.com">Leaflet</a>');
    L.control.scale({imperial:false}).addTo(map);map.attributionControl.addAttribution('DER/SP · IBGE · Limites RA/ZEE do estudo');
    $('recorte').onchange=()=>{units();update(true);};
    for(const id of ['territorio','indicador','administracao','tipo','pista','localizacao','malha','territorial','classificacao'])$(id).onchange=()=>update(id==='territorio');
    let debounce;$('rodovia').oninput=()=>{clearTimeout(debounce);debounce=setTimeout(()=>update(),250);};
    $('reset-filters').onclick=()=>{for(const k of ['territorio','administracao','tipo','pista','localizacao','rodovia'])$(k).value='';update(true);};
    $('fit-map').onclick=()=>map.fitBounds(polygons.getBounds(),{padding:[18,18],maxZoom:11});
    if($('table-search')){
      $('table-search').oninput=()=>{tablePage=0;renderTable();};
      $('table-prev').onclick=()=>{tablePage--;renderTable();};$('table-next').onclick=()=>{tablePage++;renderTable();};
    }
    if($('export-csv'))$('export-csv').onclick=()=>{
      const fields=['nome','extensao','densidade','percapita','concessao','urbano','urbanizado','sp','spa','desvio','popkm','trechos','area','populacao'];
      const quote=x=>'"'+String(x??'').replace(/"/g,'""')+'"';
      const headers=['Unidade territorial','Extensão cadastral (km)','Densidade (km/km²)','Extensão por população (km/10.000 habitantes)','Concessionada (%)','Classe urbana (%)','Dentro da mancha urbanizada, estimativa (km)','Eixos SP (%)','Acessos SPA (km)','Desvio da densidade estadual (%)','População por extensão (habitantes/km)','Registros','Área territorial (km²)','População Censo 2022 (habitantes)'];
      const contextFields=['recorte','administracao','tipo','pista','localizacao','rodovia'];
      const contextValues=contextFields.map(k=>quote($(k).value||'Todas'));
      const csv='\uFEFF'+[[...contextFields,...headers].map(quote).join(';'),...rows.map(r=>[...contextValues,...fields.map(k=>quote(typeof r[k]==='number'?String(r[k]).replace('.',','):r[k]))].join(';'))].join('\r\n');
      const link=document.createElement('a');link.href=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));link.download='indicadores-'+$('recorte').value+'.csv';link.click();setTimeout(()=>URL.revokeObjectURL(link.href),1000);
    };
    await update(true);
  }
  start().catch(error=>{$('dashboard-status').textContent='Não foi possível carregar a base: '+error.message;root.dataset.error='true';console.error(error);});
})();
