"""Gera as páginas do estudo a partir dos extratos auditados, sem publicar na rede."""
from pathlib import Path
import json
import re
import html
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'relatorio'
DATA = json.loads((SITE / 'assets/data/indicadores.json').read_text(encoding='utf-8'))
AUDIT = json.loads((SITE / 'assets/data/auditoria.json').read_text(encoding='utf-8'))
ROADS = DATA['trechos']
EXT = sum(r['extensao'] for r in ROADS)
POP = sum(u['populacao'] for u in DATA['recortes']['municipios'])
AREA = sum(u['area'] for u in DATA['recortes']['municipios'])


def n(value, digits=2):
    return f'{value:,.{digits}f}'.replace(',', '_').replace('.', ',').replace('_', '.')


def grouped(field):
    totals = defaultdict(float)
    for row in ROADS:
        totals[row[field]] += row['extensao']
    return sorted(totals.items(), key=lambda x: -x[1])


def table(headers, rows, cls=''):
    return '<div class="table-container"><table class="'+cls+'"><thead><tr>'+''.join('<th scope="col">'+v+'</th>' for v in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'


def breakdown(field):
    return table(['Categoria', 'Extensão cadastral (km)', 'Participação (%)'], [(html.escape(k), n(v), n(v/EXT*100,1)) for k,v in grouped(field)])


def page(title, subtitle, content, dashboard=False):
    return f'''<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} | Densidade de Malha</title><link rel="stylesheet" href="assets/css/style.css"><link rel="stylesheet" href="assets/css/dashboard.css">
{'<link rel="stylesheet" href="assets/vendor/leaflet/leaflet.css">' if dashboard else ''}</head><body>
<section class="hero"><div class="hero-content"><span class="badge">Estudo rodoviário revisado</span><h1>{title}</h1><p class="subtitle">{subtitle}</p></div></section>
{content}<footer class="footer"><div class="container"><p>DER/SP · IBGE · Limites RA/ZEE preservados do estudo. Revisão técnica: setembro de 2026.</p><a href="metodologia.html">Metodologia e limitações</a> · <a href="dashboard.html">Dashboard</a> · <a href="glossario.html">Glossário</a></div></footer>
<script src="assets/js/cabecalho-componente.js"></script>{'<script src="assets/vendor/leaflet/leaflet.js"></script><script src="assets/js/dashboard.js"></script>' if dashboard else ''}</body></html>'''


def section(title, content):
    return f'<section class="dashboard-panel"><div class="section-header"><h2>{title}</h2></div>{content}</section>'


NOTE = '''<div class="data-note"><strong>Como ler os números</strong><p>Extensão cadastral, incluindo registros PLAN (planejada). Não é comprimento de pista em operação nem malha geométrica única: há sobreposições declaradas. População: Censo 2022. Os filtros de malha mudam os numeradores; área e população continuam sendo as do território selecionado. <a href="metodologia.html">Ver método e limites</a>.</p></div>'''


def dashboard_body(full=True, prefix='', base='assets/data/'):
    filters = [('recorte','Recorte territorial'),('territorio','Unidade territorial'),('indicador','Indicador do mapa e ranking'),('administracao','Administração'),('tipo','Tipo de rodovia'),('pista','Tipo de pista (cadastro DER)'),('localizacao','Classe por mancha IBGE 2019')]
    controls=''.join(f'<label for="{key}">{label}<select id="{key}" name="{key}"></select></label>' for key,label in filters)
    controls+='<label for="rodovia">Buscar código da rodovia<input id="rodovia" name="rodovia" placeholder="Ex.: SP 280" autocomplete="off"></label>'
    panels=''
    if full:
        for target,title in [('administracao-bars','Extensão por administração (km)'),('tipo-bars','Extensão por tipo de rodovia (km)'),('urbano-bars','Extensão por classe de urbanização do trecho (km)'),('pista-bars','Extensão por tipo de pista cadastrado (km)')]:
            note='<p class="chart-note" id="urban-detail"></p>' if target=='urbano-bars' else ('<p class="chart-note">DUP: duplicada; PAV: pavimentada; IMP: implantada; PLAN: planejada. A extensão não conta faixas nem multiplica pistas.</p>' if target=='pista-bars' else '')
            panels+=f'<section class="dashboard-panel"><div class="panel-heading"><h2>{title}</h2></div><div class="bars" id="{target}"></div>{note}</section>'
    return f'''<main class="dashboard-shell" data-dashboard data-base="{base}">
<div class="dashboard-heading"><div><p class="eyebrow">Cadastro DER/SP · População IBGE 2022</p><p>Selecione um recorte e explore os indicadores. Clique em uma unidade no mapa ou no ranking para detalhar. A malha viária está ativada.</p></div><a href="{prefix}metodologia.html" class="btn btn-outline">Ler metodologia</a></div>
<div class="dashboard-toolbar">{controls}</div><button id="reset-filters" class="btn btn-outline">Limpar filtros de território e malha</button>
<p id="selection-context" class="dashboard-status"></p><p id="dashboard-status" class="dashboard-status" role="status" aria-live="polite">Carregando base auditada…</p>
{'<div id="kpis" class="kpi-grid"></div>'+NOTE if full else ''}
<section class="dashboard-panel"><div class="panel-heading"><h2 id="map-title">Indicadores territoriais e malha viária</h2><p>Comprimentos em km; densidades e proporções conforme a legenda. Passe o cursor ou toque nas feições para consultar seus atributos.</p></div>
<div class="map-actions"><label><input type="checkbox" id="malha" checked>Exibir malha viária</label><label><input type="checkbox" id="territorial" checked>Colorir territórios</label><label for="classificacao">Classes<select id="classificacao"><option value="quantis">Quintis</option><option value="iguais">Intervalos iguais</option></select></label><button id="fit-map" type="button">Enquadrar recorte</button></div>
<div id="dashboard-map" role="region" aria-label="Mapa interativo dos indicadores e da malha rodoviária"></div><div id="map-legend" class="map-legend"></div></section>
{('<div class="chart-grid">'+panels+'</div><section class="dashboard-panel"><div class="panel-heading"><h2 id="ranking-title">Ranking territorial</h2><p>Até 15 maiores valores. Clique para filtrar o território. Valores não definem prioridade de investimento.</p></div><div class="bars" id="ranking"></div></section><section class="dashboard-panel"><div class="panel-heading"><h2 id="histogram-title">Distribuição territorial</h2><p>Faixas sem sobreposição; unidades sem trecho entram na primeira faixa.</p></div><div class="bars" id="histogram"></div></section>') if full else ''}
{'''<section class="dashboard-panel"><div class="panel-heading"><h2>Tabela dos recortes selecionados</h2><p id="table-count"></p></div><div class="table-actions"><label for="table-search">Buscar nome somente nesta tabela<input id="table-search" type="search"></label><button id="export-csv" class="btn btn-outline">Exportar seleção territorial (CSV)</button></div><div class="table-container"><table><thead><tr><th>Unidade territorial</th><th>Extensão (km)</th><th>Densidade (km/km²)</th><th>km/10.000 hab.</th><th>Concessionada (%)</th><th>Trechos</th><th>População (hab.)</th></tr></thead><tbody id="table-body"></tbody></table></div></section>''' if full else ''}
{'<div class="table-actions"><button id="table-prev" class="btn btn-outline">Página anterior</button><button id="table-next" class="btn btn-outline">Próxima página</button></div>' if full else ''}
<section class="sources-panel"><h2>Fontes e referência</h2><p>Malha: ZIP presente no repositório; data máxima de atualização de registro: 19/01/2026 (não representa atualização de toda a base). População: <a href="https://sidra.ibge.gov.br/tabela/4714">IBGE/SIDRA, Censo 2022, tabela 4714</a>. Limites municipais e regionais: bases do estudo original. Áreas urbanizadas: <a href="https://www.ibge.gov.br/geociencias/cartas-e-mapas/redes-geograficas/15789-areas-urbanizadas.html">IBGE, 2019</a>.</p><p>RAs e ZEE recebem os municípios pela maior área de interseção, não por corte de cada trecho. A área usada é a soma das áreas municipais. <a href="{prefix}metodologia.html">Limitações e auditoria</a> · <a href="{base}auditoria.json">Evidências em JSON</a></p></section></main>'''


def generate():
    # Leitura integral prévia: nenhuma edição parcial é feita sem carregar o documento.
    original = {p: p.read_text(encoding='utf-8') for p in SITE.glob('*.html')}
    map_original = {p: p.read_text(encoding='utf-8') for p in (SITE/'mapas').glob('*.html')}
    (SITE/'dashboard.html').write_text(page('Dashboard da malha rodoviária','Indicadores conciliados, recortes territoriais e consulta à rede.',dashboard_body(),True),encoding='utf-8')
    (SITE/'anexo-mapas.html').write_text(page('Mapas e malha viária','Um explorador cartográfico para os cinco recortes do estudo.',dashboard_body(False),True),encoding='utf-8')
    method = section('O que está sendo medido',f'''<p>A unidade é o <strong>registro de subtrecho do cadastro DER/SP</strong>. O universo integral contém {len(ROADS):,} registros e {n(EXT,3)} km, somados do atributo <code>Extensao</code>. O painel inclui todas as administrações e tipos de pista existentes no arquivo, inclusive PLAN. O usuário pode restringir esses grupos.</p><p>Não se deve chamar esse total de “quilômetros de rodovias em operação” ou “comprimento físico único da rede”. Há {AUDIT['cadastro_atual']['registros_sobreposicao_declarada']} registros com sobreposição declarada. A soma geométrica, {n(AUDIT['cadastro_atual']['soma_comprimento_geometrico_km'],3)} km, é outra medida e não é usada nos indicadores.</p>''')
    method += section('Fórmulas e denominadores',table(['Indicador','Fórmula','Unidade'],[
        ['Extensão cadastral','Soma de Extensao dos registros selecionados','km'],
        ['Densidade por área','Extensão selecionada / soma das áreas municipais','km/km²'],
        ['Extensão por população','Extensão selecionada / população × 10.000','km/10.000 habitantes'],
        ['Participação concessionada','Extensão concessionada selecionada / extensão selecionada × 100','%'],
        ['Desvio territorial','(Densidade da unidade / densidade estadual com os mesmos filtros de malha − 1) × 100','%'],
        ['Parte urbanizada estimada','Extensão cadastral × proporção geométrica dentro da área urbanizada','km']])+'''<p>As densidades regionais são <strong>razões de somas</strong>, não médias simples das densidades municipais. Denominador zero gera “Sem valor”; extensão zero com população e área válidas produz densidade zero. O filtro de administração, tipo, pista ou urbanização não reduz a população nem a área do território.</p>''')
    method += section('Integração municipal e regional',f'''<ol><li>O município do cadastro DER é associado ao código IBGE por nome normalizado. A equivalência “São Luís do Paraitinga” / “São Luiz do Paraitinga” foi explicitada; no processamento antigo, esse desencontro explica a perda de 86,79 km na junção municipal.</li><li>População: ligação por código municipal à tabela 4714, variável 93, Censo 2022. Total confirmado: {n(POP,0)} habitantes.</li><li>Regiões Imediatas (53) e Intermediárias (11): códigos regionais existentes na malha municipal IBGE.</li><li>Regiões Administrativas (16) e grupos ZEE (9): cada município recebe a unidade com maior área de interseção, em EPSG:5880. A menor proporção é {n(AUDIT['associacao_territorial']['min_proporcao']*100,2)}%; 12 municípios têm menos de 99% de sua área dentro do grupo ZEE associado. Trata-se de <strong>agregação municipal aproximada aos limites ZEE</strong>, não rateio de população dentro de polígonos.</li><li>Área: {n(AREA)} km², soma das áreas municipais preservadas da malha IBGE 2024 do estudo, utilizada consistentemente em todos os recortes.</li></ol><p>Um registro inteiro é atribuído ao município cadastrado. A geometria mostrada pode atravessar um limite municipal; não se afirma que toda sua extensão está fisicamente contida nesse município. A soma dos cinco recortes reconcilia a mesma base cadastral.</p>''')
    method += section('Urbanização: método reprocessado',f'''<p>Foi baixada novamente a base <a href="https://www.ibge.gov.br/geociencias/cartas-e-mapas/redes-geograficas/15789-areas-urbanizadas.html">Áreas Urbanizadas do Brasil 2019, IBGE</a>. O produto de 2019 utiliza imagens Sentinel-2/MSI (10 m); o texto anterior confundia essa edição com a metodologia RapidEye de edições anteriores.</p><p>O processamento seleciona apenas feições com <code>Tipo = Área urbanizada</code>, densas e pouco densas. Exclui loteamentos vazios, outros equipamentos e vazios intraurbanos. Mede, em EPSG:5880, a proporção do comprimento de cada registro dentro da união dos polígonos que o interceptam.</p>'''+table(['Classe analítica do trecho','Proporção geométrica dentro da mancha'],[['Urbano','Maior que 50%'],['Misto','De 10% até 50%, inclusive'],['Rural','Menor que 10%']])+'''<p>Os limiares são <strong>escolhas analíticas do estudo</strong>, não classificação oficial prescrita pelo IBGE. Somar a extensão inteira de trechos classificados como urbanos não mede a extensão exata dentro das manchas. Esta última é estimada aplicando a proporção geométrica à extensão cadastral; pressupõe distribuição uniforme da extensão cadastral ao longo da geometria.</p><p>O campo <code>PerimetroU</code> do DER é cadastral e tem outra definição. Divergência entre ele e a mancha de 2019 não demonstra, sozinha, erro ou subestimação do DER. As datas das fontes também são diferentes.</p>''')
    legacy=AUDIT['legado']
    method += section('Auditoria do relatório anterior',table(['Problema confirmado','Evidência','Tratamento'],[
        ['Gráficos sem reconciliação','Concessão: gráfico 6.847 km; mapas municipais 9.245,51 km. Histograma publicado 285/168/92/48/27/25; recalculado 267/189/89/40/35/25.','Gráficos reconstruídos a partir dos mesmos registros usados nos cartões, mapas e tabelas.'],
        ['População incompatível com o rótulo Censo 2022',f'{n(legacy["populacao_rotulada_2022"],0)} habitantes na base antiga, contra {n(POP,0)} na tabela oficial.','Substituição pela população municipal oficial, por código IBGE.'],
        ['Fatores de escala conflitantes','Valores municipais por população calculados por 1.000 habitantes, rotulados por 10.000; scripts por área também alternavam fatores.','Fórmulas explícitas e cálculo a partir de extensão, área e população.'],
        ['Mistura entre cadastro e geometria',f'Municípios: {n(legacy["extensao_municipal_km"])} km; RAs: {n(legacy["extensao_ra_geometrica_km"])} km no legado.','Uma única medida cadastral agregada em todos os recortes.'],
        ['Gestão direta confundida com não concessionada','Além do DER, há DNIT e Prefeitura no cadastro.','Quatro administrações distintas; categoria não concessionada não é sinônimo de DER.'],
        ['Inferências sem indicadores de suporte','Saturação, qualidade de serviço e causalidade econômica eram afirmadas sem tráfego, capacidade ou teste causal.','Retiradas como conclusões demonstradas; mantidas como perguntas para estudos complementares.'],
    ],'audit-table')+'''<p>Os números da revisão também refletem a versão do ZIP atualmente disponível, que contém 4.782 registros, enquanto o texto antigo citava 4.779. Isso é mudança de insumo, além das correções de cálculo. <a href="assets/data/auditoria.json">Baixar a evidência da auditoria</a>.</p>''')
    method += section('Limites e reprodutibilidade','''<ul><li>Densidade não mede tempo de viagem, conectividade topológica, congestionamento, estado do pavimento ou prioridade de investimento.</li><li>Malha cadastral, Censo 2022, limites do estudo e manchas de 2019 têm referências temporais distintas.</li><li>Não foram removidas sobreposições de itinerários para produzir uma rede física única. Esse é outro produto analítico.</li><li>As geometrias foram simplificadas apenas para exibição (80 m nos polígonos; 12 m nas linhas); comprimentos e áreas dos indicadores não são calculados sobre a versão simplificada.</li><li>Os limites RA/ZEE foram recuperados dos mapas originais; sua atualização legal não foi revalidada. A associação municipal ZEE é aproximada e está documentada.</li></ul><p>Reprodução: <code>python scripts/auditar_e_construir_dashboard.py</code> e <code>python scripts/publicar_paginas_auditadas.py</code>. Os insumos preservados e hashes estão em <code>fontes/</code> e no JSON de auditoria. O relatório de validação testa unicidade, cobertura das junções, reconciliação e filtros.</p>''')
    (SITE/'metodologia.html').write_text(page('Metodologia e auditoria','Definições, cálculos reproduzíveis e limites de interpretação.','<main class="report-body">'+method+'</main>'),encoding='utf-8')
    stats=f'<div class="metric-inline"><div><strong>{n(EXT,3)}</strong>km cadastrais</div><div><strong>{n(EXT/AREA,4)}</strong>km/km²</div><div><strong>{n(EXT/POP*10000,2)}</strong>km/10.000 habitantes</div></div>'
    results=section('Síntese revisada',stats+NOTE+'<p><a class="btn btn-primary" href="dashboard.html">Explorar todos os resultados no dashboard</a></p>')
    results+=section('1. Distribuição espacial','<p>São 645 municípios, 53 regiões imediatas, 11 intermediárias, 16 administrativas e 9 grupos ZEE. O dashboard apresenta extensão, densidade e ranking de cada recorte; cada filtro recalcula a distribuição.</p>')
    results+=section('2. Administração da malha',breakdown('administracao')+'<p>Não concessionada inclui DER, DNIT e Prefeitura. A base não permite contar concessionárias individualmente: o campo identifica a categoria de administração.</p>')
    results+=section('3. Urbanização dos trechos',breakdown('localizacao')+f'<p>A parte estimada da extensão cadastral dentro de feições “Área urbanizada” é <strong>{n(sum(r["urbano_estimado_km"] for r in ROADS))} km</strong>. O total da classe Urbano na tabela é a extensão inteira dos trechos com mais de 50% da geometria dentro da mancha. Não são medidas equivalentes.</p>')
    results+=section('4. Extensão por população',f'<p>O denominador oficial é {n(POP,0)} habitantes, Censo 2022. A razão estadual é {n(EXT/POP*10000)} km/10.000 habitantes. O índice não mede acessibilidade real: municípios pouco populosos podem ter valores elevados mesmo com longos tempos de viagem. O dashboard permite comparar essa razão com densidade por área e extensão absoluta.</p>')
    results+=section('5. Tipo de rodovia e pista',breakdown('tipo')+breakdown('pista')+'<p>SP: eixo; SPA: acesso; SPI: interligação; BR: código federal. DUP: duplicada; PAV: pavimentada; IMP: implantada; PLAN: planejada. A classificação por prefixo não é uma avaliação da função operacional da rede.</p>')
    results+=section('6. Diferenças territoriais',f'<p>A referência estadual é a razão de somas: {n(EXT/AREA,4)} km/km². O desvio de uma unidade é calculado como (densidade local / referência − 1) × 100. A referência mantém os mesmos filtros de malha e abrange todo o estado. Ausência de extensão no cadastro produz densidade zero, mas não prova ausência de ruas ou de outras vias no território.</p><p><a href="dashboard.html">Comparar territórios e exportar indicadores</a> · <a href="anexo-mapas.html">Ver a rede e os mapas temáticos</a></p>')
    (SITE/'resultados.html').write_text(page('Resultados revisados','Síntese calculada a partir da base conciliada.','<main class="report-body">'+results+'</main>'),encoding='utf-8')
    discussion=section('O que os dados permitem concluir','<p>É possível comparar a distribuição cadastral da extensão e sua relação com área e população. Os filtros mostram quais administrações, tipos de rodovia e classes de urbanização contribuem para cada total. A diferença entre territórios é descritiva; não estabelece causa econômica.</p>')
    discussion+=section('O que os dados não demonstram','<p>Baixa densidade não prova subdimensionamento, e alta densidade não prova saturação. A participação concessionada não demonstra qualidade superior nem causalidade sobre desigualdade. Essas hipóteses exigem tráfego, capacidade, velocidades, manutenção, custos, demanda e análise temporal.</p><p>A baixa proporção de códigos SPI também não é, isoladamente, evidência de falta de conexões. A redundância deve ser medida em uma rede topologicamente conectada, considerando a função das vias de todas as classes.</p>')
    discussion+=section('Comparabilidade espacial e temporal','<p>As RAs e os grupos ZEE são agregações de municípios atribuídos pelo maior recobrimento espacial. Os polígonos não se encaixam perfeitamente; a densidade usa a soma das áreas municipais, sem alegar precisão submunicipal. Mudanças de escala alteram rankings e podem esconder heterogeneidade local.</p><p>A classificação por manchas de 2019 não descreve necessariamente a ocupação em 2026. Crescimento urbano, atualização de cadastros e diferenças de definição explicam parte das divergências possíveis com o campo PerimetroU.</p>')
    discussion+=section('Como usar o painel para investigar','<ol><li>Compare extensão absoluta, densidade por área e extensão por população, mantendo o mesmo universo de pistas.</li><li>Separe PLAN antes de discutir infraestrutura existente e examine IMP, PAV e DUP conforme o objetivo.</li><li>Use o mapa de linhas para localizar os registros que compõem o indicador; consulte o identificador e a administração.</li><li>Documente o recorte e os filtros junto com qualquer exportação.</li><li>Para decisões de investimento, complemente a descrição com tráfego, acessibilidade por tempo, segurança viária e condições de conservação.</li></ol>')
    (SITE/'discussao.html').write_text(page('Discussão crítica','Evidências descritivas e hipóteses que ainda exigem investigação.','<main class="report-body">'+discussion+'</main>'),encoding='utf-8')
    conclusion=section('Conclusões sustentadas pela revisão',stats+f'<p>A revisão conciliou {len(ROADS):,} registros da malha com os 645 municípios e a população oficial. Os cinco recortes agora usam o mesmo universo cadastral e fórmulas de densidade consistentes.</p><p>A composição administrativa, os tipos de rodovia, os tipos de pista e a classificação por manchas urbanizadas são calculados a partir dos registros. Gráficos e mapas deixam de depender de números digitados manualmente.</p>')
    conclusion+=section('Correções que mudam a leitura','<p>Foram corrigidos os valores divergentes entre gráficos e mapas, a população incorretamente rotulada, os fatores de escala, a perda de registros por grafia municipal e a confusão entre gestão DER e todo o grupo não concessionado.</p><p>Não se mantém como resultado demonstrado a suposta saturação de regiões, a subestimação cadastral por um fator fixo ou a prioridade automática de expansão baseada apenas em densidade. A metodologia explicita as incertezas.</p>')
    conclusion+=section('Próximos passos técnicos','<ul><li>Validar a edição e a associação oficial dos limites RA/ZEE.</li><li>Construir uma rede física única, com tratamento das sobreposições, caso o objetivo seja medir quilômetros de infraestrutura sem dupla contagem.</li><li>Integrar tráfego, velocidades e condições do pavimento antes de avaliar capacidade ou prioridade de obras.</li><li>Atualizar o recorte urbano para comparação temporal compatível, mantendo as versões e critérios documentados.</li></ul><a class="btn btn-primary" href="dashboard.html">Abrir dashboard interativo</a>')
    (SITE/'conclusao.html').write_text(page('Conclusão','Resultados conciliados e limites para o uso no planejamento.','<main class="report-body">'+conclusion+'</main>'),encoding='utf-8')
    sources=section('Fontes usadas na revisão',table(['Base','Conteúdo e referência','Uso'],[
        ['DER/SP',f'Sistema Rodoviário Estadual.zip no repositório; {len(ROADS)} registros. Data máxima de atualização individual: 19/01/2026.','Extensao, Subtrecho, Rodovia, Municipio, Administra, TipoPista, PerimetroU e geometria.'],
        ['IBGE/SIDRA','<a href="https://sidra.ibge.gov.br/tabela/4714">Tabela 4714, variável 93, Censo 2022</a>; 645 códigos municipais.','População residente: 44.411.238 habitantes. Consulta preservada em fontes/.'],
        ['Limites IBGE do estudo','Geometrias e atributos recuperados integralmente dos mapas originais; referência municipal 2024.','Municípios, regiões imediatas e intermediárias; área municipal.'],
        ['RA/ZEE do estudo','16 regiões administrativas e 9 grupos de análise integrada, recuperados dos mapas originais.','Agregação municipal por maior área de interseção; atualização da edição não revalidada.'],
        ['IBGE, Áreas Urbanizadas 2019','<a href="https://geoftp.ibge.gov.br/organizacao_do_territorio/tipologias_do_territorio/areas_urbanizadas_do_brasil/2019/Shapefile/AreasUrbanizadas2019_Brasil/">Shapefile oficial, baixado na revisão</a>.','Somente Tipo = Área urbanizada, densa e pouco densa.'],
    ],'audit-table'))
    sources+=section('Qualidade e rastreabilidade',f'<p>Subtrecho é único nos {len(ROADS)} registros; não há extensão ausente, negativa ou zero, nem geometria inválida no insumo verificado. Todos os registros foram associados a um município. Foram preservados hashes dos insumos e as métricas da auditoria.</p><p>O arquivo é um cadastro multijurisdicional: o filtro de jurisdição não foi aplicado implicitamente. Administração por Prefeitura não significa, por si só, jurisdição municipal. A descrição anterior que afirmava exclusão absoluta de rodovias municipais não era sustentada por um filtro do processamento.</p><p><a href="assets/data/indicadores.json">Base compacta do dashboard (JSON)</a> · <a href="assets/data/auditoria.json">Auditoria (JSON)</a> · <a href="metodologia.html">Fórmulas e limitações</a></p>')
    (SITE/'dados.html').write_text(page('Dados e fontes','Insumos efetivamente utilizados e evidências de qualidade.','<main class="report-body">'+sources+'</main>'),encoding='utf-8')
    # Cada URL cartográfica antiga recebe um mapa atualizado, com a mesma intenção temática.
    for p, source in map_original.items():
        name=p.stem
        level='municipios'
        if '_rgint' in name: level='intermediarias'
        elif '_rgi' in name: level='imediatas'
        elif '_ra_' in name or name.endswith('_ra'): level='administrativas'
        elif '_zee' in name: level='zee'
        metric='extensao'
        if 'densidade' in name or 'dens_area' in name: metric='densidade'
        if 'denspop' in name or 'acessibilidade' in name: metric='percapita'
        if 'concessao' in name: metric='concessao'
        if 'urbano' in name: metric='urbano'
        if 'hierarquia_spa' in name: metric='spa'
        elif 'hierarquia_sp' in name: metric='sp'
        if 'disparidade' in name: metric='desvio'
        if 'pop_por_km' in name: metric='popkm'
        body=dashboard_body(False,'../','../assets/data/')
        doc=f'''<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Mapa rodoviário | {level} | {metric}</title><link rel="stylesheet" href="../assets/css/style.css"><link rel="stylesheet" href="../assets/css/dashboard.css"><link rel="stylesheet" href="../assets/vendor/leaflet/leaflet.css"></head><body class="map-page">{body}<script>window.MAP_CONFIG={json.dumps({'level':level,'metric':metric})};</script><script src="../assets/vendor/leaflet/leaflet.js"></script><script src="../assets/js/dashboard.js"></script></body></html>'''
        p.write_text(doc,encoding='utf-8')
    print('Páginas revisadas e 35 mapas gerados.')


if __name__ == '__main__':
    generate()
