"""Verificação real no navegador. Requer servidor local e Playwright/Edge."""
from pathlib import Path
import json
import math
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = 'http://127.0.0.1:8768/'
OUT = ROOT.parent / 'PLI-ECOSSISTEMA/validacao-redesign-malha'
OUT.mkdir(parents=True, exist_ok=True)
data = json.loads((ROOT/'relatorio/assets/data/indicadores.json').read_text(encoding='utf-8'))
checks = []


def stable(page):
    page.wait_for_function("document.querySelector('[data-ready]')?.dataset.ready==='true' && document.getElementById('dashboard-status').textContent.includes('atualizadas')", timeout=30000)


with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=True)
    context = browser.new_context(viewport={'width':1440,'height':1000})
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    for width in [1440,768,390]:
        page.set_viewport_size({'width':width,'height':1000})
        for path in sorted((ROOT/'relatorio').glob('*.html')):
            response = page.goto(BASE+path.name, wait_until='domcontentloaded')
            assert response.status == 200
            page.wait_for_selector('.study-ready')
            if page.locator('[data-dashboard]').count():
                stable(page)
            assert page.locator('.navbar-menu a').count() == 10
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'), (path.name,width)
            assert not page.evaluate(r"/[\u{1F000}-\u{1FAFF}\u2600-\u27BF]/u.test(document.body.innerText)"), path.name
            if width < 960:
                page.locator('.menu-toggle').click()
                assert page.locator('.navbar').is_visible()
                page.keyboard.press('Escape')
                assert not page.locator('.navbar').is_visible()
            checks.append({'page':path.name,'width':width,'status':'OK'})
        print(f'Páginas completas: largura {width}', flush=True)
    page.set_viewport_size({'width':1440,'height':1000})
    for path in sorted((ROOT/'relatorio/mapas').glob('*.html')):
        page.goto(BASE+'mapas/'+path.name, wait_until='domcontentloaded')
        stable(page)
        assert page.locator('#map-legend strong').count() == 2
        assert page.evaluate('malhaDashboard.map.hasLayer(malhaDashboard.roadLayer)')
        assert page.evaluate('malhaDashboard.roadLayer.getLayers().length') == 4782
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        checks.append({'map':path.name,'status':'OK'})
    print('35 URLs cartográficas: carregamento, malha e legendas OK', flush=True)
    page.goto(BASE+'dashboard.html',wait_until='domcontentloaded');stable(page)
    total = sum(r['extensao'] for r in data['trechos'])
    for level,count in [('municipios',645),('imediatas',53),('intermediarias',11),('administrativas',16),('zee',9)]:
        page.select_option('#recorte',level)
        page.wait_for_function('(level)=>window.malhaDashboard?.level===level',arg=level)
        result = page.evaluate('({model:malhaDashboard.model,n:malhaDashboard.rows.length})')
        assert result['n']==count
        assert math.isclose(result['model']['extensao'],total,abs_tol=1e-6)
        assert result['model']['populacao']==44411238
    page.select_option('#recorte','municipios')
    page.select_option('#administracao','DER')
    expected=sum(r['extensao'] for r in data['trechos'] if r['administracao']=='DER')
    page.wait_for_function('(x)=>Math.abs(malhaDashboard.model.extensao-x)<1e-6',arg=expected)
    page.select_option('#pista','DUP')
    expected=sum(r['extensao'] for r in data['trechos'] if r['administracao']=='DER' and r['pista']=='DUP')
    page.wait_for_function('(x)=>Math.abs(malhaDashboard.model.extensao-x)<1e-6',arg=expected)
    page.locator('#reset-filters').click()
    page.wait_for_function('(x)=>Math.abs(malhaDashboard.model.extensao-x)<1e-6',arg=total)
    page.select_option('#territorio','3550308')
    expected=sum(r['extensao'] for r in data['trechos'] if r['municipio']=='3550308')
    page.wait_for_function('(x)=>malhaDashboard.rows.length===1&&Math.abs(malhaDashboard.model.extensao-x)<1e-6',arg=expected)
    for metric in ['percapita','concessao','urbano','urbanizado','sp','spa','desvio','popkm','extensao','densidade']:
        page.select_option('#indicador',metric)
        page.wait_for_function('(x)=>malhaDashboard.metric===x',arg=metric)
        assert page.locator('#map-legend').inner_text().strip()
        assert 'NaN' not in page.locator('#map-legend').inner_text()
    page.locator('#reset-filters').click();stable(page)
    assert page.locator('#table-body tr').count()==25
    first=page.locator('#table-body tr').first.inner_text()
    page.locator('#table-next').click()
    assert page.locator('#table-body tr').first.inner_text()!=first
    page.locator('#table-search').fill('Cotia')
    assert page.locator('#table-body tr').count()==1
    page.locator('#table-search').fill('')
    with page.expect_download() as download:
        page.locator('#export-csv').click()
    assert download.value.suggested_filename.endswith('.csv')
    page.locator('#malha').uncheck()
    page.wait_for_function('!malhaDashboard.map.hasLayer(malhaDashboard.roadLayer)')
    page.locator('#malha').check();stable(page)
    page.locator('#rodovia').fill('ZZZ_SEM_RESULTADO')
    page.wait_for_function('malhaDashboard.selected.length===0')
    assert page.evaluate('malhaDashboard.model.concessao===null')
    assert 'NaN' not in page.locator('#map-legend').inner_text()
    page.locator('#reset-filters').click();stable(page)
    page.screenshot(path=str(OUT/'dashboard-final-desktop.png'),full_page=True)
    page.locator('#dashboard-map').scroll_into_view_if_needed()
    page.screenshot(path=str(OUT/'dashboard-final-mapa.png'))
    page.set_viewport_size({'width':390,'height':900});page.evaluate('scrollTo(0,0)')
    page.screenshot(path=str(OUT/'dashboard-final-mobile.png'))
    assert not errors, errors
    checks.append({'filters':'5 recortes, filtros combinados, 10 indicadores, paginação, busca, CSV, camadas e resultado vazio','status':'OK'})
    (OUT/'dashboard-browser.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
    print('PASS: verificações no navegador; nenhum erro JavaScript.',flush=True)
    browser.close()
