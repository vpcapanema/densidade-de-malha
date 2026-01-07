# -*- coding: utf-8 -*-
"""
Script para Geração de Mapas Completos com Camada de Malha Viária
==================================================================

Gera todos os mapas temáticos para as 6 Questões Norteadoras, incluindo:
- Camada toggle de malha viária classificada por tipo (SP/SPA/SPI/BR)
- Cores e espessuras seguindo padrões cartográficos OSM Carto
- Mapas multicamada para concessão e urbano/rural
- Duas versões de densidade: por área e por população

Autor: Densidade de Malha SP
Data: Janeiro/2026
"""

import geopandas as gpd
import pandas as pd
import numpy as np
import folium
from folium import plugins
import branca.colormap as cm
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# =============================================================================
# CONFIGURAÇÕES
# =============================================================================

BASE_DIR = Path(r"d:\densidade _de_malha")
DADOS_SAIDA = BASE_DIR / "dados" / "saida"
RELATORIO_DIR = BASE_DIR / "relatorio" / "mapas"
RELATORIO_DIR.mkdir(parents=True, exist_ok=True)

# Centro de SP
SP_CENTER = [-22.5, -48.5]
SP_ZOOM = 7

# =============================================================================
# PADRÃO DE CORES E ESPESSURAS (baseado em OSM Carto)
# =============================================================================

# Cores por tipo de rodovia
CORES_TIPO = {
    # Malha viária: SP mais grossa; demais mais finas
    'SP':    {'cor': '#dc2626', 'peso': 3.0, 'nome': 'Eixo Principal (SP)'},
    'SPA':   {'cor': '#f97316', 'peso': 1.3, 'nome': 'Acessos (SPA)'},
    'SPI':   {'cor': '#eab308', 'peso': 0.9, 'nome': 'Interligações (SPI)'},
    'BR':    {'cor': '#2563eb', 'peso': 1.6, 'nome': 'Federais (BR)'},
    'Outros': {'cor': '#6b7280', 'peso': 0.8, 'nome': 'Outros'},
}

# Cores para mapas multicamada
CORES_CONCESSAO = {
    'Concessionada':     '#8e44ad',
    'Não_Concessionada': '#27ae60',
}

# Cores para camada de malha viária por administração/concessão
CORES_MALHA_CONCESSAO = {
    'Concessionária': {'cor': '#e91e63', 'nome': 'Concessionada', 'peso': 4},
    'DER': {'cor': '#4caf50', 'nome': 'Não Concessionada (DER)', 'peso': 3},
    'DNIT': {'cor': '#2196f3', 'nome': 'Federal (DNIT)', 'peso': 4},
    'Prefeitura': {'cor': '#ff9800', 'nome': 'Municipal (Prefeitura)', 'peso': 2},
}

CORES_LOCALIZACAO = {
    'Urbano': '#e74c3c',
    'Rural':  '#27ae60',
    'Misto':  '#f39c12',
}

# Estilo de linha por tipo de pista
DASH_ARRAY = {
    'PAV':  None,        # Sólida - Pavimentada
    'DUP':  None,        # Sólida - Duplicada
    'IMP':  '8, 4',      # Tracejada - Em Implantação
    'PLAN': '4, 8',      # Pontilhada - Planejada
}

# =============================================================================
# FUNÇÕES DE CARREGAMENTO
# =============================================================================

def carregar_dados():
    """Carrega os dados processados."""
    print("📂 Carregando dados...")
    
    gpkg_path = DADOS_SAIDA / "densidade_malha.gpkg"
    
    municipios = gpd.read_file(gpkg_path, layer='municipios')
    rg_imediatas = gpd.read_file(gpkg_path, layer='rg_imediatas')
    rg_intermediarias = gpd.read_file(gpkg_path, layer='rg_intermediarias')
    
    # Converter para WGS84 (necessário para Folium)
    municipios = municipios.to_crs('EPSG:4326')
    rg_imediatas = rg_imediatas.to_crs('EPSG:4326')
    rg_intermediarias = rg_intermediarias.to_crs('EPSG:4326')
    
    print(f"   Municípios: {len(municipios)}")
    print(f"   RG Imediatas: {len(rg_imediatas)}")
    print(f"   RG Intermediárias: {len(rg_intermediarias)}")
    
    return municipios, rg_imediatas, rg_intermediarias

def carregar_malha_viaria():
    """Carrega a malha viária classificada."""
    print("📂 Carregando malha viária...")
    
    malha_path = DADOS_SAIDA / "malha_der_classificada.gpkg"
    if not malha_path.exists():
        print("   ⚠️ Arquivo malha_der_classificada.gpkg não encontrado!")
        return None
    
    malha = gpd.read_file(malha_path)
    malha = malha.to_crs('EPSG:4326')
    
    # Extrair tipo de rodovia se não existir
    if 'Tipo_Rod' not in malha.columns:
        malha['Tipo_Rod'] = malha['Rodovia'].str.extract(r'^([A-Z]+)', expand=False)
        malha['Tipo_Rod'] = malha['Tipo_Rod'].fillna('Outros')
    
    print(f"   Trechos carregados: {len(malha)}")
    print(f"   Tipos: {malha['Tipo_Rod'].value_counts().to_dict()}")
    
    return malha

def carregar_zee():
    """Carrega as camadas do ZEE se existirem."""
    print("📂 Carregando camadas ZEE...")
    
    gpkg_path = DADOS_SAIDA / "densidade_malha.gpkg"
    
    try:
        ra = gpd.read_file(gpkg_path, layer='regioes_administrativas')
        zee = gpd.read_file(gpkg_path, layer='grupos_zee')
        ra = ra.to_crs('EPSG:4326')
        zee = zee.to_crs('EPSG:4326')
        print(f"   Regiões Administrativas: {len(ra)}")
        print(f"   Grupos ZEE: {len(zee)}")
        return ra, zee
    except Exception as e:
        print(f"   ⚠️ Camadas ZEE não encontradas: {e}")
        return None, None

# =============================================================================
# FUNÇÃO PARA ADICIONAR CAMADA DE MALHA VIÁRIA
# =============================================================================

def adicionar_camada_malha(mapa, malha, nome_grupo="Malha Viária"):
    """
    Adiciona a camada de malha viária classificada por tipo ao mapa.
    Cria um FeatureGroup com toggle liga/desliga.
    """
    if malha is None:
        print("   ⚠️ Malha viária não disponível")
        return mapa
    
    print(f"   Adicionando camada de malha viária...")
    
    # Criar grupo principal (por padrão, desligado; usuário ativa no controle de camadas)
    grupo_malha = folium.FeatureGroup(name=nome_grupo, show=False, overlay=True)

    # Normalizar os valores de tipo (o dataset pode vir como SP/SPA/SPI/BR ou como Eixo/Acesso/Interligação)
    def _normalizar_tipo_rodovi(valor: str) -> str:
        if valor is None:
            return 'Outros'
        v = str(valor).strip()
        if v in CORES_TIPO:
            return v
        vl = v.lower()
        if 'eixo' in vl:
            return 'SP'
        if 'acesso' in vl:
            return 'SPA'
        if 'interliga' in vl:
            return 'SPI'
        if vl == 'br' or vl.startswith('br'):
            return 'BR'
        return 'Outros'

    malha_norm = malha.copy()

    # Fonte do tipo: prioriza colunas já classificadas; fallback para prefixo da rodovia
    tipo_col = None
    for candidate in ['Tipo_Rod', 'TipoRodovi', 'Tipo_Rodovia', 'TipoRod']:
        if candidate in malha_norm.columns:
            tipo_col = candidate
            break
    if tipo_col is None:
        # Fallback: tenta extrair do nome da rodovia
        if 'Rodovia' in malha_norm.columns:
            malha_norm['_tipo_bruto'] = malha_norm['Rodovia'].astype(str).str.extract(r'^([A-Za-z]+)', expand=False)
            tipo_col = '_tipo_bruto'
        else:
            malha_norm['_tipo_bruto'] = 'Outros'
            tipo_col = '_tipo_bruto'

    malha_norm['_tipo_norm'] = malha_norm[tipo_col].apply(_normalizar_tipo_rodovi)

    # Adicionar cada tipo de rodovia como sublayer
    for tipo, config in CORES_TIPO.items():
        malha_tipo = malha_norm[malha_norm['_tipo_norm'] == tipo].copy()
        
        if len(malha_tipo) == 0:
            continue
        
        # Criar subgrupo para este tipo
        for idx, row in malha_tipo.iterrows():
            # Determinar dash_array baseado no tipo de pista
            tipo_pista = row.get('TipoPista', 'PAV')
            dash = DASH_ARRAY.get(tipo_pista, None)
            
            # Estilo da linha - peso maior para aparecer sobre polígonos
            style = {
                'color': config['cor'],
                'weight': config['peso'],
                'opacity': 1.0,  # Opacidade total
                'zIndex': 1000,  # Z-index alto
            }
            if dash:
                style['dashArray'] = dash
            
            # Tooltip
            tooltip_text = f"{row.get('Rodovia', 'N/I')} - {config['nome']}"
            
            # Adicionar linha
            try:
                folium.GeoJson(
                    row.geometry.__geo_interface__,
                    style_function=lambda x, s=style: s,
                    tooltip=tooltip_text
                ).add_to(grupo_malha)
            except:
                pass  # Ignorar geometrias inválidas
    
    grupo_malha.add_to(mapa)
    
    # Script para garantir que a malha fique visível sobre as camadas coropléticas
    script_bringToFront = f'''
    <script>
    (function() {{
        function getLeafletMap() {{
            var maps = Object.keys(window).filter(function(k) {{
                return k.startsWith('map_') && window[k] && window[k].eachLayer;
            }});
            return maps.length ? window[maps[0]] : null;
        }}

        function getMalhaLayer(layerName) {{
            var candidates = Object.keys(window).filter(function(k) {{
                return k.endsWith('_layers') && window[k] && window[k].overlays;
            }});
            for (var i = 0; i < candidates.length; i++) {{
                var obj = window[candidates[i]];
                if (obj.overlays && obj.overlays[layerName]) {{
                    return obj.overlays[layerName];
                }}
            }}
            return null;
        }}

        function bringMalhaToFront() {{
            setTimeout(function() {{
                var map = getLeafletMap();
                if (!map) return;
                var malhaLayer = getMalhaLayer({nome_grupo!r});
                if (!malhaLayer) return;
                if (!map.hasLayer(malhaLayer)) return;

                if (malhaLayer.bringToFront) {{
                    malhaLayer.bringToFront();
                }}
                if (malhaLayer.eachLayer) {{
                    malhaLayer.eachLayer(function(sublayer) {{
                        if (sublayer && sublayer.bringToFront) {{
                            sublayer.bringToFront();
                        }}
                    }});
                }}
            }}, 250);
        }}

        function init() {{
            var map = getLeafletMap();
            if (!map) return;

            bringMalhaToFront();
            map.on('overlayadd', bringMalhaToFront);
        }}

        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', init);
        }} else {{
            init();
        }}
    }})();
    </script>
    '''
    mapa.get_root().html.add_child(folium.Element(script_bringToFront))
    
    # Adicionar legenda da malha viária (visível apenas quando a camada estiver ativada)
    legenda_html = '''
    <div id="malha-legend" style="display: none; position: fixed; bottom: 20px; left: 20px; z-index: 1000;
                background: white; padding: 8px 12px; border-radius: 6px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2); font-family: Arial; font-size: 8.8px;">
        <div style="font-weight: bold; margin-bottom: 6px; color: #333;">🛣️ Malha Viária DER</div>
        <div style="display: flex; align-items: center; margin: 3px 0;">
                <div style="width: 24px; height: 3.0px; background: #dc2626; margin-right: 6px;"></div>
            <span>SP (Eixo Principal)</span>
        </div>
        <div style="display: flex; align-items: center; margin: 3px 0;">
                <div style="width: 24px; height: 1.6px; background: #f97316; margin-right: 6px;"></div>
            <span>SPA (Acessos)</span>
        </div>
        <div style="display: flex; align-items: center; margin: 3px 0;">
                <div style="width: 24px; height: 1.6px; background: #eab308; margin-right: 6px;"></div>
            <span>SPI (Interligações)</span>
        </div>
        <div style="display: flex; align-items: center; margin: 3px 0;">
                <div style="width: 24px; height: 2.0px; background: #2563eb; margin-right: 6px;"></div>
            <span>BR (Federais)</span>
        </div>
    </div>
    '''
    mapa.get_root().html.add_child(folium.Element(legenda_html))

    # Script para mostrar/ocultar legenda conforme toggle da camada no Leaflet LayerControl
    script_toggle_legenda = f'''
    <script>
    (function() {{
        function getLeafletMap() {{
            var maps = Object.keys(window).filter(function(k) {{
                return k.startsWith('map_') && window[k] && window[k].eachLayer;
            }});
            return maps.length ? window[maps[0]] : null;
        }}

        function getMalhaLayer(layerName) {{
            var candidates = Object.keys(window).filter(function(k) {{
                return k.endsWith('_layers') && window[k] && window[k].overlays;
            }});
            for (var i = 0; i < candidates.length; i++) {{
                var obj = window[candidates[i]];
                if (obj.overlays && obj.overlays[layerName]) {{
                    return obj.overlays[layerName];
                }}
            }}
            return null;
        }}

        function init() {{
            var map = getLeafletMap();
            if (!map) return;

            var legend = document.getElementById('malha-legend');
            if (!legend) return;

            var malhaLayer = getMalhaLayer({nome_grupo!r});
            if (!malhaLayer) return;

            function updateLegend() {{
                legend.style.display = map.hasLayer(malhaLayer) ? 'block' : 'none';
            }}

            map.on('overlayadd', updateLegend);
            map.on('overlayremove', updateLegend);
            setTimeout(updateLegend, 200);
        }}

        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', init);
        }} else {{
            init();
        }}
    }})();
    </script>
    '''
    mapa.get_root().html.add_child(folium.Element(script_toggle_legenda))
    
    return mapa

def adicionar_camada_malha_concessao(mapa, malha, nome_grupo="Malha Viária por Concessão"):
    """
    Adiciona a malha viária classificada por concessão ao mapa.
    Categorias: Concessionária, DER, DNIT (BR), Prefeitura
    """
    if malha is None:
        print("   ⚠️ Malha viária não disponível")
        return mapa
    
    print(f"   Adicionando camada de malha viária por concessão...")
    
    # Criar grupo principal (por padrão, desligado; usuário ativa no controle de camadas)
    grupo_malha = folium.FeatureGroup(name=nome_grupo, show=False, overlay=True)
    
    # Adicionar cada tipo de administração como sublayer
    for admin, config in CORES_MALHA_CONCESSAO.items():
        malha_admin = malha[malha['Administra'] == admin].copy()
        
        if len(malha_admin) == 0:
            continue
        
        # Criar subgrupo para este tipo
        for idx, row in malha_admin.iterrows():
            # Determinar dash_array baseado no tipo de pista
            tipo_pista = row.get('TipoPista', 'PAV')
            dash = DASH_ARRAY.get(tipo_pista, None)
            
            # Estilo da linha
            style = {
                'color': config['cor'],
                'weight': config['peso'],
                'opacity': 0.8,
            }
            if dash:
                style['dashArray'] = dash
            
            # Tooltip
            tooltip_text = f"{row.get('Rodovia', 'N/I')} - {config['nome']}"
            
            # Adicionar linha
            try:
                folium.GeoJson(
                    row.geometry.__geo_interface__,
                    style_function=lambda x, s=style: s,
                    tooltip=tooltip_text
                ).add_to(grupo_malha)
            except:
                pass  # Ignorar geometrias inválidas
    
    grupo_malha.add_to(mapa)
    
    # Adicionar legenda da malha por concessão (visível apenas quando a camada estiver ativada)
    legenda_html = '''
    <div id="malha-concessao-legend" style="display: none; position: fixed; bottom: 20px; left: 20px; z-index: 1000;
                background: white; padding: 8px 12px; border-radius: 6px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2); font-family: Arial; font-size: 8.8px;">
        <div style="font-weight: bold; margin-bottom: 6px; color: #333;">🛣️ Malha por Concessão</div>
        <div style="display: flex; align-items: center; margin: 3px 0;">
            <div style="width: 24px; height: 3.2px; background: #e91e63; margin-right: 6px;"></div>
            <span>Concessionária</span>
        </div>
        <div style="display: flex; align-items: center; margin: 3px 0;">
            <div style="width: 24px; height: 2.4px; background: #4caf50; margin-right: 6px;"></div>
            <span>Não Conc. (DER)</span>
        </div>
        <div style="display: flex; align-items: center; margin: 3px 0;">
            <div style="width: 24px; height: 3.2px; background: #2196f3; margin-right: 6px;"></div>
            <span>Federal (DNIT)</span>
        </div>
        <div style="display: flex; align-items: center; margin: 3px 0;">
            <div style="width: 24px; height: 1.6px; background: #ff9800; margin-right: 6px;"></div>
            <span>Municipal</span>
        </div>
    </div>
    <style>
        @media (max-width: 768px) {
            #malha-concessao-legend { bottom: 60px !important; left: 5px !important; }
        }
    </style>
    '''
    mapa.get_root().html.add_child(folium.Element(legenda_html))
    
    # Script para garantir que a malha fique visível sobre as camadas coropléticas
    script_bringToFront = f'''
    <script>
    (function() {{
        function getLeafletMap() {{
            var maps = Object.keys(window).filter(function(k) {{
                return k.startsWith('map_') && window[k] && window[k].eachLayer;
            }});
            return maps.length ? window[maps[0]] : null;
        }}

        function getLayerByName(layerName) {{
            var candidates = Object.keys(window).filter(function(k) {{
                return k.endsWith('_layers') && window[k] && window[k].overlays;
            }});
            for (var i = 0; i < candidates.length; i++) {{
                var obj = window[candidates[i]];
                if (obj.overlays && obj.overlays[layerName]) {{
                    return obj.overlays[layerName];
                }}
            }}
            return null;
        }}

        function bringToFront() {{
            setTimeout(function() {{
                var map = getLeafletMap();
                if (!map) return;
                var layer = getLayerByName({nome_grupo!r});
                if (!layer) return;
                if (!map.hasLayer(layer)) return;

                if (layer.bringToFront) {{
                    layer.bringToFront();
                }}
                if (layer.eachLayer) {{
                    layer.eachLayer(function(sublayer) {{
                        if (sublayer && sublayer.bringToFront) {{
                            sublayer.bringToFront();
                        }}
                    }});
                }}
            }}, 250);
        }}

        function init() {{
            var map = getLeafletMap();
            if (!map) return;
            bringToFront();
            map.on('overlayadd', bringToFront);
        }}

        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', init);
        }} else {{
            init();
        }}
    }})();
    </script>
    '''
    mapa.get_root().html.add_child(folium.Element(script_bringToFront))

    # Script para mostrar/ocultar legenda conforme toggle da camada
    script_toggle_legenda = f'''
    <script>
    (function() {{
        function getLeafletMap() {{
            var maps = Object.keys(window).filter(function(k) {{
                return k.startsWith('map_') && window[k] && window[k].eachLayer;
            }});
            return maps.length ? window[maps[0]] : null;
        }}

        function getLayerByName(layerName) {{
            var candidates = Object.keys(window).filter(function(k) {{
                return k.endsWith('_layers') && window[k] && window[k].overlays;
            }});
            for (var i = 0; i < candidates.length; i++) {{
                var obj = window[candidates[i]];
                if (obj.overlays && obj.overlays[layerName]) {{
                    return obj.overlays[layerName];
                }}
            }}
            return null;
        }}

        function init() {{
            var map = getLeafletMap();
            if (!map) return;

            var legend = document.getElementById('malha-concessao-legend');
            if (!legend) return;

            var layer = getLayerByName({nome_grupo!r});
            if (!layer) return;

            function updateLegend() {{
                legend.style.display = map.hasLayer(layer) ? 'block' : 'none';
            }}

            map.on('overlayadd', updateLegend);
            map.on('overlayremove', updateLegend);
            setTimeout(updateLegend, 200);
        }}

        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', init);
        }} else {{
            init();
        }}
    }})();
    </script>
    '''
    mapa.get_root().html.add_child(folium.Element(script_toggle_legenda))
    
    return mapa

# =============================================================================
# FUNÇÕES DE CRIAÇÃO DE MAPAS TEMÁTICOS
# =============================================================================

def criar_mapa_base(titulo, subtitulo="", full_height: bool = False):
    """Cria mapa base com camadas de fundo."""
    m = folium.Map(location=SP_CENTER, zoom_start=SP_ZOOM, tiles=None)
    
    # Adicionar metadados de acessibilidade e segurança
    meta_html = f'''
    <title>{titulo} - Análise de Densidade de Malha Viária</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src * 'unsafe-inline' 'unsafe-eval'; script-src * 'unsafe-inline' 'unsafe-eval'; connect-src * 'unsafe-inline'; img-src * data: blob: 'unsafe-inline'; frame-src *; style-src * 'unsafe-inline';">
    '''
    m.get_root().header.add_child(folium.Element(meta_html))
    
    # Adicionar atributo lang no HTML
    html_lang = '''
    <script>
        document.documentElement.lang = 'pt-BR';
    </script>
    '''
    m.get_root().html.add_child(folium.Element(html_lang))
    
    # Camadas base
    folium.TileLayer('cartodbpositron', name='Fundo Claro').add_to(m)
    folium.TileLayer('cartodbdark_matter', name='Fundo Escuro').add_to(m)
    
    # Título
    extra_height_css = ""
    if full_height:
        extra_height_css = """
            html, body { width: 100%; height: 100%; margin: 0; padding: 0; }
            .folium-map { width: 100% !important; height: 100% !important; }
            .leaflet-container { width: 100% !important; height: 100% !important; }
        """

    title_html = f'''
        <style>
            .map-title-box {{
                position: fixed; top: 10px; left: 50%; transform: translateX(-50%);
                z-index: 1000; background: white; padding: 10px 20px; border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2); font-family: Arial;
                text-align: center;
            }}
            .map-title-box h4 {{ margin: 0; color: #1a5276; font-size: 14px; }}
            .map-title-box p {{ margin: 5px 0 0; font-size: 11px; color: #666; }}
            .leaflet-tooltip {{ background: white !important; color: #333 !important; 
                               border: 1px solid #ccc !important; }}
            {extra_height_css}
        </style>
        <div class="map-title-box">
            <h4>{titulo}</h4>
            <p>{subtitulo}</p>
        </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))

    if full_height:
        # Em iframes, o Leaflet pode inicializar com tamanho errado e ficar "travado" numa faixa.
        # Este script força o recálculo após load/resize e em timeouts curtos.
        full_height_script = '''
        <script>
        (function () {
            function getLeafletMap() {
                var keys = Object.keys(window).filter(function (k) {
                    return k.startsWith('map_') && window[k] && typeof window[k].invalidateSize === 'function';
                });
                return keys.length ? window[keys[0]] : null;
            }

            function invalidate() {
                try {
                    var m = getLeafletMap();
                    if (!m) return;
                    m.invalidateSize();
                } catch (e) {}
            }

            function schedule() {
                [0, 150, 400, 900, 1500].forEach(function (ms) {
                    setTimeout(invalidate, ms);
                });
            }

            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', schedule);
            } else {
                schedule();
            }
            window.addEventListener('load', schedule);
            window.addEventListener('resize', function () { setTimeout(invalidate, 150); });
        })();
        </script>
        '''
        m.get_root().html.add_child(folium.Element(full_height_script))
    
    return m

def criar_mapa_coropletico(gdf, col_valor, col_nome, titulo, subtitulo, output_name, 
                           malha=None, colormap_cores=None, caption=""):
    """Cria mapa coroplético genérico com camada de malha."""
    print(f"   Gerando mapa: {titulo}...")
    
    gdf = gdf.copy()
    
    if col_valor not in gdf.columns:
        print(f"      ⚠️ Coluna {col_valor} não encontrada!")
        return
    
    # Limpar valores e converter para JSON-safe
    gdf[col_valor] = gdf[col_valor].replace([np.inf, -np.inf], np.nan).fillna(0)
    gdf[col_valor] = gdf[col_valor].astype(float).round(4)
    
    # Limpar geometria (remover features inválidas)
    gdf = gdf[gdf.geometry.notnull()]
    gdf = gdf[gdf.geometry.is_valid]
    
    # Manter apenas colunas necessárias para otimizar serialização
    gdf = gdf[[col_nome, col_valor, 'geometry']].copy()
    
    # Criar mapa base
    m = criar_mapa_base(titulo, subtitulo)
    
    # Colormap
    vmin = gdf[col_valor].quantile(0.05)
    vmax = gdf[col_valor].quantile(0.95)
    
    if colormap_cores is None:
        colormap_cores = ['#f7fbff', '#6baed6', '#2171b5', '#08306b']
    
    colormap = cm.LinearColormap(
        colors=colormap_cores,
        vmin=vmin,
        vmax=vmax,
        caption=caption or col_valor
    )
    
    # Estilo
    def style_function(feature):
        valor = feature['properties'].get(col_valor, 0)
        if valor is None or pd.isna(valor):
            valor = 0
        return {
            'fillColor': colormap(valor) if valor > 0 else '#ffffff',
            'color': '#333333',
            'weight': 0.5,
            'fillOpacity': 0.7
        }
    
    # Tooltip
    tooltip = folium.GeoJsonTooltip(
        fields=[col_nome, col_valor],
        aliases=['Nome:', f'{caption}:'],
        localize=True,
        sticky=True
    )
    
    # Adicionar camada coroplética
    folium.GeoJson(
        gdf,
        name=titulo,
        style_function=style_function,
        highlight_function=lambda x: {'weight': 2, 'color': '#ff6b6b', 'fillOpacity': 0.9},
        tooltip=tooltip
    ).add_to(m)
    
    # Criar gradiente de cores para legenda HTML
    cores_gradient = ', '.join(colormap_cores)
    
    # Adicionar legenda HTML customizada
    legenda_html = f'''
    <div class="legenda-custom" style="
        position: fixed; bottom: 30px; right: 10px; z-index: 1000;
        background: white; padding: 8px 12px; border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2); font-family: Arial; font-size: 9px;
        max-width: 160px;">
        <div style="font-weight: bold; margin-bottom: 6px; color: #333;">{caption}</div>
        <div style="display: flex; align-items: center; height: 12px; margin-bottom: 4px;">
            <div style="flex: 1; height: 100%; background: linear-gradient(to right, {cores_gradient});"></div>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 8px; color: #666;">
            <span>{vmin:.2f}</span><span>{vmax:.2f}</span>
        </div>
    </div>
    <style>
        @media (max-width: 768px) {{
            .legenda-custom {{ bottom: 60px !important; right: 5px !important; max-width: 140px !important; }}
        }}
    </style>
    '''
    m.get_root().html.add_child(folium.Element(legenda_html))
    
    # Adicionar camada de malha viária (toggle)
    if malha is not None:
        m = adicionar_camada_malha(m, malha)
    
    # Controle de camadas colapsado
    folium.LayerControl(collapsed=True).add_to(m)
    
    # Salvar
    output_path = RELATORIO_DIR / f"{output_name}.html"
    m.save(str(output_path))
    print(f"      ✓ Salvo: {output_path.name}")

# =============================================================================
# MAPAS PARA AS 6 QUESTÕES NORTEADORAS
# =============================================================================

def gerar_mapas_distribuicao(municipios, malha):
    """Q1: Distribuição Espacial - Extensão total por município"""
    print("\n🗺️ Q1: Mapas de Distribuição Espacial...")
    
    # Extensão Total
    criar_mapa_coropletico(
        municipios, 'Ext_Total', 'NM_MUN',
        'Extensão Total de Rodovias', 'Quilômetros de malha viária por município',
        'mapa_q1_extensao_mun',
        malha=malha,
        colormap_cores=['#f5f3ff', '#c4b5fd', '#7c3aed', '#3b0764'],
        caption='Extensão (km)'
    )
    
    # Densidade por Área
    criar_mapa_coropletico(
        municipios, 'Dens_Area_Total', 'NM_MUN',
        'Densidade por Área', 'km de rodovia / km² de território',
        'mapa_q1_densidade_area_mun',
        malha=malha,
        colormap_cores=['#f7fbff', '#6baed6', '#2171b5', '#08306b'],
        caption='Densidade (km/km²)'
    )

def gerar_mapas_concessao(municipios, malha):
    """Q2: Concessões - Mapas multicamada com legendas dinâmicas"""
    print("\n🗺️ Q2: Mapas de Concessões (Multicamada com legendas dinâmicas)...")
    
    gdf = municipios.copy()
    
    if 'Ext_Concessionada' not in gdf.columns or 'Ext_Não_Concessionada' not in gdf.columns:
        print("   ⚠️ Colunas de concessão não encontradas")
        return
    
    # Calcular proporção
    gdf['Prop_Concessao'] = (gdf['Ext_Concessionada'] / gdf['Ext_Total'] * 100).fillna(0)
    gdf['Prop_NaoConcessao'] = (gdf['Ext_Não_Concessionada'] / gdf['Ext_Total'] * 100).fillna(0)
    
    # Valores para legendas
    max_conc = gdf['Ext_Concessionada'].quantile(0.95)
    max_nao = gdf['Ext_Não_Concessionada'].quantile(0.95)
    
    # Criar mapa base
    m = criar_mapa_base('Regime de Concessão de Rodovias', 
                        'Extensão por tipo de administração (Concessionada vs Não Concessionada)')
    
    # Camada 1: Extensão Concessionada
    colormap_conc = cm.LinearColormap(
        colors=['#f3e5f5', '#ce93d8', '#ab47bc', '#6a1b9a'],
        vmin=0,
        vmax=max_conc,
        caption='Concessionada (km)'
    )
    
    def style_conc(feature):
        valor = feature['properties'].get('Ext_Concessionada', 0) or 0
        return {
            'fillColor': colormap_conc(valor) if valor > 0 else '#ffffff',
            'color': '#333333',
            'weight': 0.5,
            'fillOpacity': 0.7
        }
    
    tooltip_conc = folium.GeoJsonTooltip(
        fields=['NM_MUN', 'Ext_Concessionada', 'Prop_Concessao'],
        aliases=['Município:', 'Extensão Concessionada (km):', '% do Total:'],
        localize=True
    )
    
    layer_conc = folium.GeoJson(
        gdf,
        name='🟣 Concessionada',
        style_function=style_conc,
        highlight_function=lambda x: {'weight': 2, 'color': '#8e44ad'},
        tooltip=tooltip_conc,
        show=True
    )
    layer_conc.add_to(m)
    
    # Camada 2: Extensão Não Concessionada
    colormap_nao = cm.LinearColormap(
        colors=['#e8f5e9', '#81c784', '#43a047', '#1b5e20'],
        vmin=0,
        vmax=max_nao,
        caption='Não Concessionada (km)'
    )
    
    def style_nao(feature):
        valor = feature['properties'].get('Ext_Não_Concessionada', 0) or 0
        return {
            'fillColor': colormap_nao(valor) if valor > 0 else '#ffffff',
            'color': '#333333',
            'weight': 0.5,
            'fillOpacity': 0.7
        }
    
    tooltip_nao = folium.GeoJsonTooltip(
        fields=['NM_MUN', 'Ext_Não_Concessionada', 'Prop_NaoConcessao'],
        aliases=['Município:', 'Extensão Não Concessionada (km):', '% do Total:'],
        localize=True
    )
    
    layer_nao = folium.GeoJson(
        gdf,
        name='🟢 Não Concessionada',
        style_function=style_nao,
        highlight_function=lambda x: {'weight': 2, 'color': '#27ae60'},
        tooltip=tooltip_nao,
        show=False
    )
    layer_nao.add_to(m)
    
    # Adicionar AMBAS as camadas de malha viária ANTES do LayerControl
    if malha is not None:
        # Camada 1: Malha classificada por tipo (SP/SPA/SPI/BR)
        m = adicionar_camada_malha(m, malha, nome_grupo="🛣️ Malha por Tipo")
        # Camada 2: Malha classificada por concessão
        m = adicionar_camada_malha_concessao(m, malha, nome_grupo="🛣️ Malha por Concessão")
    
    # Controle de camadas DEPOIS de todas as camadas
    folium.LayerControl(collapsed=True).add_to(m)
    
    # Legendas HTML customizadas com toggle
    legendas_html = f'''
    <div id="legenda-conc" class="legenda-custom" style="
        position: fixed; bottom: 30px; right: 10px; z-index: 1000;
        background: white; padding: 8px 12px; border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2); font-family: Arial; font-size: 9px;
        max-width: 160px;">
        <div style="font-weight: bold; margin-bottom: 8px; color: #6a1b9a;">🟣 Concessionada (km)</div>
        <div style="display: flex; align-items: center; height: 15px; margin-bottom: 5px;">
            <div style="flex: 1; height: 100%; background: linear-gradient(to right, #f3e5f5, #ce93d8, #ab47bc, #6a1b9a);"></div>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 10px; color: #666;">
            <span>0</span><span>{max_conc:.0f}</span>
        </div>
    </div>
    <div id="legenda-nao" class="legenda-custom" style="
        position: fixed; bottom: 30px; right: 10px; z-index: 1000;
        background: white; padding: 8px 12px; border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2); font-family: Arial; font-size: 9px;
        max-width: 160px; display: none;">
        <div style="font-weight: bold; margin-bottom: 8px; color: #1b5e20;">🟢 Não Concessionada (km)</div>
        <div style="display: flex; align-items: center; height: 15px; margin-bottom: 5px;">
            <div style="flex: 1; height: 100%; background: linear-gradient(to right, #e8f5e9, #81c784, #43a047, #1b5e20);"></div>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 10px; color: #666;">
            <span>0</span><span>{max_nao:.0f}</span>
        </div>
    </div>
    <style>
        @media (max-width: 768px) {{
            .legenda-custom {{ bottom: 60px !important; right: 5px !important; max-width: 150px !important; }}
        }}
    </style>
    <script>
    document.addEventListener('DOMContentLoaded', function() {{
        setTimeout(function() {{
            // Esconder legendas do Branca (colormap padrão)
            var brancaLegends = document.querySelectorAll('.legend');
            brancaLegends.forEach(function(el) {{ el.style.display = 'none'; }});
            
            // Observar mudanças no controle de camadas
            var layerControl = document.querySelector('.leaflet-control-layers-overlays');
            if (layerControl) {{
                layerControl.addEventListener('click', function(e) {{
                    setTimeout(function() {{
                        var inputs = layerControl.querySelectorAll('input');
                        inputs.forEach(function(input) {{
                            var label = input.nextSibling.textContent.trim();
                            if (label.includes('Concessionada') && !label.includes('Não')) {{
                                document.getElementById('legenda-conc').style.display = input.checked ? 'block' : 'none';
                            }}
                            if (label.includes('Não Concessionada')) {{
                                document.getElementById('legenda-nao').style.display = input.checked ? 'block' : 'none';
                            }}
                        }});
                    }}, 100);
                }});
            }}
        }}, 500);
    }});
    </script>
    '''
    m.get_root().html.add_child(folium.Element(legendas_html))
    
    # Salvar
    output_path = RELATORIO_DIR / "mapa_q2_concessao_mun.html"
    m.save(str(output_path))
    print(f"      ✓ Salvo: {output_path.name}")

def gerar_mapas_urbano_rural(municipios, malha):
    """Q3: Urbano vs Rural - Mapas multicamada com legendas dinâmicas"""
    print("\n🗺️ Q3: Mapas Urbano vs Rural (Multicamada com legendas dinâmicas)...")
    
    gdf = municipios.copy()
    
    if 'Ext_Urbano' not in gdf.columns:
        print("   ⚠️ Colunas de localização não encontradas")
        return
    
    # Calcular proporções
    gdf['Prop_Urbano'] = (gdf['Ext_Urbano'] / gdf['Ext_Total'] * 100).fillna(0)
    gdf['Prop_Rural'] = (gdf['Ext_Rural'] / gdf['Ext_Total'] * 100).fillna(0)
    gdf['Prop_Misto'] = (gdf['Ext_Misto'] / gdf['Ext_Total'] * 100).fillna(0)
    
    # Valores máximos para legendas
    max_urb = gdf['Ext_Urbano'].quantile(0.95)
    max_rur = gdf['Ext_Rural'].quantile(0.95)
    max_mix = gdf['Ext_Misto'].quantile(0.95)
    
    # Criar mapa base
    m = criar_mapa_base('Classificação Urbano/Rural de Rodovias', 
                        'Extensão por localização geográfica (baseado em manchas urbanas IBGE)')
    
    # Camada 1: Extensão Urbana
    colormap_urb = cm.LinearColormap(
        colors=['#ffebee', '#ef9a9a', '#e53935', '#b71c1c'],
        vmin=0,
        vmax=max_urb if max_urb > 0 else 1,
        caption='Urbano (km)'
    )
    
    def style_urb(feature):
        valor = feature['properties'].get('Ext_Urbano', 0) or 0
        return {
            'fillColor': colormap_urb(valor) if valor > 0 else '#ffffff',
            'color': '#333333',
            'weight': 0.5,
            'fillOpacity': 0.7
        }
    
    tooltip_urb = folium.GeoJsonTooltip(
        fields=['NM_MUN', 'Ext_Urbano', 'Prop_Urbano'],
        aliases=['Município:', 'Extensão Urbana (km):', '% do Total:'],
        localize=True
    )
    
    layer_urb = folium.GeoJson(
        gdf,
        name='🔴 Urbano',
        style_function=style_urb,
        highlight_function=lambda x: {'weight': 2, 'color': '#e74c3c'},
        tooltip=tooltip_urb,
        show=True
    )
    layer_urb.add_to(m)
    
    # Camada 2: Extensão Rural
    colormap_rur = cm.LinearColormap(
        colors=['#e8f5e9', '#81c784', '#43a047', '#1b5e20'],
        vmin=0,
        vmax=max_rur if max_rur > 0 else 1,
        caption='Rural (km)'
    )
    
    def style_rur(feature):
        valor = feature['properties'].get('Ext_Rural', 0) or 0
        return {
            'fillColor': colormap_rur(valor) if valor > 0 else '#ffffff',
            'color': '#333333',
            'weight': 0.5,
            'fillOpacity': 0.7
        }
    
    tooltip_rur = folium.GeoJsonTooltip(
        fields=['NM_MUN', 'Ext_Rural', 'Prop_Rural'],
        aliases=['Município:', 'Extensão Rural (km):', '% do Total:'],
        localize=True
    )
    
    layer_rur = folium.GeoJson(
        gdf,
        name='🟢 Rural',
        style_function=style_rur,
        highlight_function=lambda x: {'weight': 2, 'color': '#27ae60'},
        tooltip=tooltip_rur,
        show=False
    )
    layer_rur.add_to(m)
    
    # Camada 3: Extensão Mista
    colormap_mix = cm.LinearColormap(
        colors=['#fff8e1', '#ffcc80', '#ff9800', '#e65100'],
        vmin=0,
        vmax=max_mix if max_mix > 0 else 1,
        caption='Misto (km)'
    )
    
    def style_mix(feature):
        valor = feature['properties'].get('Ext_Misto', 0) or 0
        return {
            'fillColor': colormap_mix(valor) if valor > 0 else '#ffffff',
            'color': '#333333',
            'weight': 0.5,
            'fillOpacity': 0.7
        }
    
    tooltip_mix = folium.GeoJsonTooltip(
        fields=['NM_MUN', 'Ext_Misto', 'Prop_Misto'],
        aliases=['Município:', 'Extensão Mista (km):', '% do Total:'],
        localize=True
    )
    
    layer_mix = folium.GeoJson(
        gdf,
        name='🟠 Misto',
        style_function=style_mix,
        highlight_function=lambda x: {'weight': 2, 'color': '#f39c12'},
        tooltip=tooltip_mix,
        show=False
    )
    layer_mix.add_to(m)
    
    # Adicionar camada de malha viária
    if malha is not None:
        m = adicionar_camada_malha(m, malha)
    
    # Controle de camadas
    folium.LayerControl(collapsed=True).add_to(m)
    
    # Legendas HTML customizadas com toggle
    legendas_html = f'''
    <div id="legenda-urb" class="legenda-custom" style="
        position: fixed; bottom: 30px; right: 10px; z-index: 1000;
        background: white; padding: 8px 12px; border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2); font-family: Arial; font-size: 9px;
        max-width: 160px;">
        <div style="font-weight: bold; margin-bottom: 8px; color: #b71c1c;">🔴 Urbano (km)</div>
        <div style="display: flex; align-items: center; height: 15px; margin-bottom: 5px;">
            <div style="flex: 1; height: 100%; background: linear-gradient(to right, #ffebee, #ef9a9a, #e53935, #b71c1c);"></div>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 10px; color: #666;">
            <span>0</span><span>{max_urb:.0f}</span>
        </div>
    </div>
    <div id="legenda-rur" class="legenda-custom" style="
        position: fixed; bottom: 30px; right: 10px; z-index: 1000;
        background: white; padding: 8px 12px; border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2); font-family: Arial; font-size: 9px;
        max-width: 160px; display: none;">
        <div style="font-weight: bold; margin-bottom: 8px; color: #1b5e20;">🟢 Rural (km)</div>
        <div style="display: flex; align-items: center; height: 15px; margin-bottom: 5px;">
            <div style="flex: 1; height: 100%; background: linear-gradient(to right, #e8f5e9, #81c784, #43a047, #1b5e20);"></div>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 10px; color: #666;">
            <span>0</span><span>{max_rur:.0f}</span>
        </div>
    </div>
    <div id="legenda-mix" class="legenda-custom" style="
        position: fixed; bottom: 30px; right: 10px; z-index: 1000;
        background: white; padding: 8px 12px; border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2); font-family: Arial; font-size: 9px;
        max-width: 160px; display: none;">
        <div style="font-weight: bold; margin-bottom: 8px; color: #e65100;">🟠 Misto (km)</div>
        <div style="display: flex; align-items: center; height: 15px; margin-bottom: 5px;">
            <div style="flex: 1; height: 100%; background: linear-gradient(to right, #fff8e1, #ffcc80, #ff9800, #e65100);"></div>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 10px; color: #666;">
            <span>0</span><span>{max_mix:.0f}</span>
        </div>
    </div>
    <style>
        @media (max-width: 768px) {{
            .legenda-custom {{ bottom: 60px !important; right: 5px !important; max-width: 150px !important; }}
        }}
    </style>
    <script>
    document.addEventListener('DOMContentLoaded', function() {{
        setTimeout(function() {{
            // Esconder legendas do Branca (colormap padrão)
            var brancaLegends = document.querySelectorAll('.legend');
            brancaLegends.forEach(function(el) {{ el.style.display = 'none'; }});
            
            // Observar mudanças no controle de camadas
            var layerControl = document.querySelector('.leaflet-control-layers-overlays');
            if (layerControl) {{
                layerControl.addEventListener('click', function(e) {{
                    setTimeout(function() {{
                        var inputs = layerControl.querySelectorAll('input');
                        inputs.forEach(function(input) {{
                            var label = input.nextSibling.textContent.trim();
                            if (label.includes('Urbano')) {{
                                document.getElementById('legenda-urb').style.display = input.checked ? 'block' : 'none';
                            }}
                            if (label.includes('Rural')) {{
                                document.getElementById('legenda-rur').style.display = input.checked ? 'block' : 'none';
                            }}
                            if (label.includes('Misto')) {{
                                document.getElementById('legenda-mix').style.display = input.checked ? 'block' : 'none';
                            }}
                        }});
                    }}, 100);
                }});
            }}
        }}, 500);
    }});
    </script>
    '''
    m.get_root().html.add_child(folium.Element(legendas_html))
    
    # Salvar
    output_path = RELATORIO_DIR / "mapa_q3_urbano_mun.html"
    m.save(str(output_path))
    print(f"      ✓ Salvo: {output_path.name}")

def gerar_mapas_acessibilidade(municipios, malha):
    """Q4: Acessibilidade - Mapa multicamada com 3 métricas e legendas dinâmicas"""
    print("\n🗺️ Q4: Mapas de Acessibilidade (Multicamada com 3 métricas)...")
    
    gdf = municipios.copy()

    # Indicador adicional: população por km de rodovia (hab/km)
    # (pedido: população do município ÷ extensão da malha no município)
    if 'Populacao' in gdf.columns and 'Ext_Total' in gdf.columns:
        ext_km = gdf['Ext_Total'].replace(0, np.nan)
        gdf['Hab_por_km'] = (gdf['Populacao'] / ext_km).replace([np.inf, -np.inf], np.nan).fillna(0)
        gdf['Hab_por_km'] = gdf['Hab_por_km'].astype(float).round(2)
    
    # Criar mapa base
    m = criar_mapa_base(
        'Indicadores de Acessibilidade Rodoviária',
        'Três métricas: Extensão Total, Densidade por Área e Disponibilidade por Habitante',
        full_height=True,
    )
    
    # Valores máximos para legendas
    max_ext = gdf['Ext_Total'].quantile(0.95)
    max_dens_area = gdf['Dens_Area_Total'].quantile(0.95)
    max_dens_pop = gdf['Dens_Pop_Total'].quantile(0.95)
    
    # ===== Camada 1: Extensão Total (km) =====
    colormap_ext = cm.LinearColormap(
        colors=['#e3f2fd', '#90caf9', '#42a5f5', '#1565c0'],
        vmin=0,
        vmax=max_ext if max_ext > 0 else 1,
        caption='Extensão Total (km)'
    )
    
    def style_ext(feature):
        valor = feature['properties'].get('Ext_Total', 0) or 0
        return {
            'fillColor': colormap_ext(valor) if valor > 0 else '#ffffff',
            'color': '#333333',
            'weight': 0.5,
            'fillOpacity': 0.7
        }
    
    tooltip_ext = folium.GeoJsonTooltip(
        fields=['NM_MUN', 'Ext_Total', 'Area_km2', 'Populacao'],
        aliases=['Município:', 'Extensão (km):', 'Área (km²):', 'População:'],
        localize=True
    )
    
    layer_ext = folium.GeoJson(
        gdf,
        name='🔵 Extensão Total (km)',
        style_function=style_ext,
        highlight_function=lambda x: {'weight': 2, 'color': '#1565c0'},
        tooltip=tooltip_ext,
        show=True
    )
    layer_ext.add_to(m)
    
    # ===== Camada 2: Densidade por Área (km/km²) =====
    colormap_area = cm.LinearColormap(
        colors=['#e8f5e9', '#81c784', '#43a047', '#1b5e20'],
        vmin=0,
        vmax=max_dens_area if max_dens_area > 0 else 1,
        caption='Densidade por Área (km/km²)'
    )
    
    def style_area(feature):
        valor = feature['properties'].get('Dens_Area_Total', 0) or 0
        return {
            'fillColor': colormap_area(valor) if valor > 0 else '#ffffff',
            'color': '#333333',
            'weight': 0.5,
            'fillOpacity': 0.7
        }
    
    tooltip_area = folium.GeoJsonTooltip(
        fields=['NM_MUN', 'Dens_Area_Total', 'Area_km2', 'Ext_Total'],
        aliases=['Município:', 'Densidade (km/km²):', 'Área (km²):', 'Extensão (km):'],
        localize=True
    )
    
    layer_area = folium.GeoJson(
        gdf,
        name='🟢 Densidade por Área (km/km²)',
        style_function=style_area,
        highlight_function=lambda x: {'weight': 2, 'color': '#1b5e20'},
        tooltip=tooltip_area,
        show=False
    )
    layer_area.add_to(m)
    
    # ===== Camada 3: Densidade por População (km/1000hab) =====
    colormap_pop = cm.LinearColormap(
        colors=['#fff7ec', '#fc8d59', '#d7301f', '#7f0000'],
        vmin=0,
        vmax=max_dens_pop if max_dens_pop > 0 else 1,
        caption='Disponibilidade por Habitante (km/1000hab)'
    )
    
    def style_pop(feature):
        valor = feature['properties'].get('Dens_Pop_Total', 0) or 0
        return {
            'fillColor': colormap_pop(valor) if valor > 0 else '#ffffff',
            'color': '#333333',
            'weight': 0.5,
            'fillOpacity': 0.7
        }
    
    tooltip_pop = folium.GeoJsonTooltip(
        fields=['NM_MUN', 'Dens_Pop_Total', 'Populacao', 'Ext_Total'],
        aliases=['Município:', 'km/1000hab:', 'População:', 'Extensão (km):'],
        localize=True
    )
    
    layer_pop = folium.GeoJson(
        gdf,
        name='🟠 Disponibilidade por Habitante (km/1000hab)',
        style_function=style_pop,
        highlight_function=lambda x: {'weight': 2, 'color': '#d35400'},
        tooltip=tooltip_pop,
        show=False
    )
    layer_pop.add_to(m)
    
    # Adicionar camada de malha viária
    if malha is not None:
        m = adicionar_camada_malha(m, malha)
    
    # Controle de camadas
    folium.LayerControl(collapsed=True).add_to(m)
    
    # Legendas HTML customizadas com toggle dinâmico
    legendas_html = f'''
    <div id="legenda-ext" class="legenda-custom" style="
        position: fixed; bottom: 30px; right: 10px; z-index: 1000;
        background: white; padding: 8px 12px; border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2); font-family: Arial; font-size: 9px;
        max-width: 160px;">
        <div style="font-weight: bold; margin-bottom: 8px; color: #1565c0;">🔵 Extensão Total (km)</div>
        <div style="display: flex; align-items: center; height: 15px; margin-bottom: 5px;">
            <div style="flex: 1; height: 100%; background: linear-gradient(to right, #e3f2fd, #90caf9, #42a5f5, #1565c0);"></div>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 10px; color: #666;">
            <span>0</span><span>{max_ext:.0f}</span>
        </div>
    </div>
    <div id="legenda-area" class="legenda-custom" style="
        position: fixed; bottom: 30px; right: 10px; z-index: 1000;
        background: white; padding: 8px 12px; border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2); font-family: Arial; font-size: 9px;
        max-width: 160px; display: none;">
        <div style="font-weight: bold; margin-bottom: 8px; color: #1b5e20;">🟢 Densidade (km/km²)</div>
        <div style="display: flex; align-items: center; height: 15px; margin-bottom: 5px;">
            <div style="flex: 1; height: 100%; background: linear-gradient(to right, #e8f5e9, #81c784, #43a047, #1b5e20);"></div>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 10px; color: #666;">
            <span>0</span><span>{max_dens_area:.2f}</span>
        </div>
    </div>
    <div id="legenda-pop" class="legenda-custom" style="
        position: fixed; bottom: 30px; right: 10px; z-index: 1000;
        background: white; padding: 8px 12px; border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2); font-family: Arial; font-size: 9px;
        max-width: 160px; display: none;">
        <div style="font-weight: bold; margin-bottom: 8px; color: #d7301f;">🟠 Disponibilidade (km/1000hab)</div>
        <div style="display: flex; align-items: center; height: 15px; margin-bottom: 5px;">
            <div style="flex: 1; height: 100%; background: linear-gradient(to right, #fff7ec, #fc8d59, #d7301f, #7f0000);"></div>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 10px; color: #666;">
            <span>0</span><span>{max_dens_pop:.1f}</span>
        </div>
    </div>
    <style>
        @media (max-width: 768px) {{
            .legenda-custom {{ bottom: 60px !important; right: 5px !important; max-width: 150px !important; }}
        }}
    </style>
    <script>
    document.addEventListener('DOMContentLoaded', function() {{
        setTimeout(function() {{
            // Esconder legendas do Branca (colormap padrão)
            var brancaLegends = document.querySelectorAll('.legend');
            brancaLegends.forEach(function(el) {{ el.style.display = 'none'; }});
            
            // Observar mudanças no controle de camadas
            var layerControl = document.querySelector('.leaflet-control-layers-overlays');
            if (layerControl) {{
                layerControl.addEventListener('click', function(e) {{
                    setTimeout(function() {{
                        var inputs = layerControl.querySelectorAll('input');
                        inputs.forEach(function(input) {{
                            var label = input.nextSibling.textContent.trim();
                            if (label.includes('Extensão')) {{
                                document.getElementById('legenda-ext').style.display = input.checked ? 'block' : 'none';
                            }}
                            if (label.includes('Área')) {{
                                document.getElementById('legenda-area').style.display = input.checked ? 'block' : 'none';
                            }}
                            if (label.includes('Habitante')) {{
                                document.getElementById('legenda-pop').style.display = input.checked ? 'block' : 'none';
                            }}
                        }});
                    }}, 100);
                }});
            }}
        }}, 500);
    }});
    </script>
    '''
    m.get_root().html.add_child(folium.Element(legendas_html))
    
    # Salvar
    output_path = RELATORIO_DIR / "mapa_q4_acessibilidade_mun.html"
    m.save(str(output_path))
    print(f"      ✓ Salvo: {output_path.name}")
    
    # Também gerar mapas separados para referência
    criar_mapa_coropletico(
        municipios, 'Ext_Total', 'NM_MUN',
        'Extensão Total de Rodovias', 'km de rodovia por município',
        'mapa_q4_extensao_mun',
        malha=malha,
        colormap_cores=['#e3f2fd', '#90caf9', '#42a5f5', '#1565c0'],
        caption='Extensão (km)'
    )
    
    criar_mapa_coropletico(
        municipios, 'Dens_Area_Total', 'NM_MUN',
        'Densidade por Área', 'km de rodovia por km² de território',
        'mapa_q4_densidade_area_mun',
        malha=malha,
        colormap_cores=['#e8f5e9', '#81c784', '#43a047', '#1b5e20'],
        caption='Densidade (km/km²)'
    )
    
    criar_mapa_coropletico(
        municipios, 'Dens_Pop_Total', 'NM_MUN',
        'Disponibilidade por Habitante', 'km de rodovia por 1.000 habitantes',
        'mapa_q4_denspop_mun',
        malha=malha,
        colormap_cores=['#fff7ec', '#fc8d59', '#d7301f', '#7f0000'],
        caption='km/1.000 hab'
    )

    # População por km de rodovia (hab/km)
    if 'Hab_por_km' in gdf.columns:
        criar_mapa_coropletico(
            gdf, 'Hab_por_km', 'NM_MUN',
            'População por km de Rodovia', 'Habitantes por km de rodovia no município',
            'mapa_q4_pop_por_km_mun',
            malha=malha,
            colormap_cores=['#f7fbff', '#6baed6', '#2171b5', '#08306b'],
            caption='hab/km'
        )

def gerar_mapas_hierarquia(municipios, malha):
    """Q5: Hierarquia Viária - Proporção por tipo de rodovia"""
    print("\n🗺️ Q5: Mapas de Hierarquia Viária...")
    
    gdf = municipios.copy()
    
    # Calcular proporção de SP (eixos principais)
    if 'Ext_SP' in gdf.columns and 'Ext_Total' in gdf.columns:
        gdf['Prop_SP'] = (gdf['Ext_SP'] / gdf['Ext_Total'] * 100).fillna(0)
        
        criar_mapa_coropletico(
            gdf, 'Prop_SP', 'NM_MUN',
            'Proporção de Eixos Principais (SP)', 'Percentual de rodovias SP sobre total',
            'mapa_q5_hierarquia_sp_mun',
            malha=malha,
            colormap_cores=['#f7fcf5', '#74c476', '#238b45', '#00441b'],
            caption='% Rodovias SP'
        )
    
    # Mapa com extensão de SPA (acessos)
    if 'Ext_SPA' in gdf.columns:
        criar_mapa_coropletico(
            gdf, 'Ext_SPA', 'NM_MUN',
            'Extensão de Rodovias de Acesso (SPA)', 'Quilômetros de SPAs por município',
            'mapa_q5_hierarquia_spa_mun',
            malha=malha,
            colormap_cores=['#fff7ec', '#fdbb84', '#e34a33', '#7f0000'],
            caption='Extensão SPA (km)'
        )

def gerar_mapas_disparidades(municipios, rg_intermediarias, malha):
    """Q6: Disparidades Regionais - Comparativo com média estadual"""
    print("\n🗺️ Q6: Mapas de Disparidades Regionais...")
    
    gdf = municipios.copy()
    
    # Calcular desvio da média estadual
    media_estadual = gdf['Dens_Area_Total'].mean()
    gdf['Desvio_Media'] = ((gdf['Dens_Area_Total'] - media_estadual) / media_estadual * 100).fillna(0)
    
    # Criar mapa com escala divergente
    print(f"   Gerando mapa: Desvio da Média Estadual...")
    
    m = criar_mapa_base('Disparidade Regional', f'Desvio em relação à média estadual ({media_estadual:.3f} km/km²)')
    
    # Colormap divergente
    vmin = gdf['Desvio_Media'].quantile(0.05)
    vmax = gdf['Desvio_Media'].quantile(0.95)
    vabs = max(abs(vmin), abs(vmax))
    
    colormap = cm.LinearColormap(
        colors=['#d73027', '#fc8d59', '#fee08b', '#ffffbf', '#d9ef8b', '#91cf60', '#1a9850'],
        vmin=-vabs,
        vmax=vabs,
        caption='Desvio da Média (%)'
    )
    
    def style_function(feature):
        valor = feature['properties'].get('Desvio_Media', 0)
        if valor is None or pd.isna(valor):
            valor = 0
        return {
            'fillColor': colormap(valor),
            'color': '#333333',
            'weight': 0.5,
            'fillOpacity': 0.7
        }
    
    tooltip = folium.GeoJsonTooltip(
        fields=['NM_MUN', 'Dens_Area_Total', 'Desvio_Media'],
        aliases=['Município:', 'Densidade:', 'Desvio (%):'],
        localize=True
    )
    
    folium.GeoJson(
        gdf,
        name='Disparidades',
        style_function=style_function,
        highlight_function=lambda x: {'weight': 2, 'color': '#333'},
        tooltip=tooltip
    ).add_to(m)
    
    # Legenda HTML customizada (padrão do projeto)
    cores_gradient = ', '.join(['#d73027', '#fc8d59', '#fee08b', '#ffffbf', '#d9ef8b', '#91cf60', '#1a9850'])
    legenda_html = f'''
    <div class="legenda-custom" style="
        position: fixed; bottom: 30px; right: 10px; z-index: 1000;
        background: white; padding: 8px 12px; border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2); font-family: Arial; font-size: 9px;
        max-width: 160px;">
        <div style="font-weight: bold; margin-bottom: 6px; color: #333;">Desvio da Média (%)</div>
        <div style="display: flex; align-items: center; height: 12px; margin-bottom: 4px;">
            <div style="flex: 1; height: 100%; background: linear-gradient(to right, {cores_gradient});"></div>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 8px; color: #666;">
            <span>{-vabs:.0f}%</span><span>{vabs:.0f}%</span>
        </div>
    </div>
    <style>
        @media (max-width: 768px) {{
            .legenda-custom {{ bottom: 60px !important; right: 5px !important; max-width: 140px !important; }}
        }}
    </style>
    <script>
    document.addEventListener('DOMContentLoaded', function() {{
        setTimeout(function() {{
            var brancaLegends = document.querySelectorAll('.legend');
            brancaLegends.forEach(function(el) {{ el.style.display = 'none'; }});
        }}, 200);
    }});
    </script>
    '''
    m.get_root().html.add_child(folium.Element(legenda_html))
    
    if malha is not None:
        m = adicionar_camada_malha(m, malha)
    
    folium.LayerControl().add_to(m)
    
    output_path = RELATORIO_DIR / "mapa_q6_disparidades_mun.html"
    m.save(str(output_path))
    print(f"      ✓ Salvo: {output_path.name}")
    
    # Mapa de regiões intermediárias
    if rg_intermediarias is not None:
        col_nome = [c for c in rg_intermediarias.columns if 'NM_' in c][0]
        criar_mapa_coropletico(
            rg_intermediarias, 'Dens_Area_Total', col_nome,
            'Densidade por Região Intermediária', 'Visão macrorregional (11 regiões)',
            'mapa_q6_disparidades_rgint',
            malha=malha,
            colormap_cores=['#f7fbff', '#6baed6', '#2171b5', '#08306b'],
            caption='Densidade (km/km²)'
        )

# =============================================================================
# MAPAS PARA ANEXO (TODAS AS GRANULARIDADES)
# =============================================================================

def gerar_mapas_anexo(municipios, rg_imediatas, rg_intermediarias, ra, zee, malha):
    """Gera todos os mapas para a página de anexo."""
    print("\n📎 Gerando mapas para Anexo (todas as granularidades)...")
    
    # Identificar colunas de nome
    col_mun = 'NM_MUN'
    col_rgi = [c for c in rg_imediatas.columns if 'NM_' in c][0] if rg_imediatas is not None else None
    col_rgint = [c for c in rg_intermediarias.columns if 'NM_' in c][0] if rg_intermediarias is not None else None
    
    # --- MUNICÍPIOS ---
    print("\n   📍 Mapas Municipais...")
    criar_mapa_coropletico(municipios, 'Ext_Total', col_mun,
        'Extensão Total - Municípios', '645 municípios',
        'mapa_anexo_extensao_mun', malha, caption='Extensão (km)')
    
    criar_mapa_coropletico(municipios, 'Dens_Area_Total', col_mun,
        'Densidade por Área - Municípios', '645 municípios',
        'mapa_anexo_densidade_mun', malha, caption='Densidade (km/km²)')
    
    criar_mapa_coropletico(municipios, 'Dens_Pop_Total', col_mun,
        'Densidade por População - Municípios', '645 municípios',
        'mapa_anexo_denspop_mun', malha, caption='km/1000 hab')
    
    # --- RG IMEDIATAS ---
    if rg_imediatas is not None and col_rgi:
        print("\n   🗺️ Mapas RG Imediatas...")
        criar_mapa_coropletico(rg_imediatas, 'Ext_Total', col_rgi,
            'Extensão Total - RG Imediatas', '53 regiões',
            'mapa_anexo_extensao_rgi', malha, caption='Extensão (km)')
        
        criar_mapa_coropletico(rg_imediatas, 'Dens_Area_Total', col_rgi,
            'Densidade por Área - RG Imediatas', '53 regiões',
            'mapa_anexo_densidade_rgi', malha, caption='Densidade (km/km²)')
    
    # --- RG INTERMEDIÁRIAS ---
    if rg_intermediarias is not None and col_rgint:
        print("\n   🌐 Mapas RG Intermediárias...")
        criar_mapa_coropletico(rg_intermediarias, 'Ext_Total', col_rgint,
            'Extensão Total - RG Intermediárias', '11 macrorregiões',
            'mapa_anexo_extensao_rgint', malha, caption='Extensão (km)')
        
        criar_mapa_coropletico(rg_intermediarias, 'Dens_Area_Total', col_rgint,
            'Densidade por Área - RG Intermediárias', '11 macrorregiões',
            'mapa_anexo_densidade_rgint', malha, caption='Densidade (km/km²)')
    
    # --- REGIÕES ADMINISTRATIVAS (ZEE) ---
    if ra is not None:
        print("\n   🌿 Mapas Regiões Administrativas...")
        col_ra = 'Nome' if 'Nome' in ra.columns else [c for c in ra.columns if 'Nome' in c or 'NM_' in c][0]
        criar_mapa_coropletico(ra, 'Dens_Area_Total', col_ra,
            'Densidade por Área - Regiões Administrativas', '16 regiões do ZEE',
            'mapa_anexo_densidade_ra', malha, caption='Densidade (km/km²)')
    
    # --- GRUPOS ZEE ---
    if zee is not None:
        print("\n   🌿 Mapas Grupos ZEE...")
        col_zee = 'Nome' if 'Nome' in zee.columns else [c for c in zee.columns if 'Nome' in c or 'grupo' in c.lower()][0]
        criar_mapa_coropletico(zee, 'Dens_Area_Total', col_zee,
            'Densidade por Área - Grupos ZEE', '9 unidades de análise integrada',
            'mapa_anexo_densidade_zee', malha, caption='Densidade (km/km²)')

# =============================================================================
# FUNÇÃO PRINCIPAL
# =============================================================================

def main():
    print("="*70)
    print("GERAÇÃO DE MAPAS COMPLETOS COM CAMADA DE MALHA VIÁRIA")
    print("="*70)
    
    # Carregar dados
    municipios, rg_imediatas, rg_intermediarias = carregar_dados()
    malha = carregar_malha_viaria()
    ra, zee = carregar_zee()
    
    # Gerar mapas para as 6 Questões Norteadoras
    gerar_mapas_distribuicao(municipios, malha)
    gerar_mapas_concessao(municipios, malha)
    gerar_mapas_urbano_rural(municipios, malha)
    gerar_mapas_acessibilidade(municipios, malha)
    gerar_mapas_hierarquia(municipios, malha)
    gerar_mapas_disparidades(municipios, rg_intermediarias, malha)
    
    # Gerar mapas para anexo
    gerar_mapas_anexo(municipios, rg_imediatas, rg_intermediarias, ra, zee, malha)
    
    print("\n" + "="*70)
    print("✅ MAPAS GERADOS COM SUCESSO!")
    print(f"📂 Local: {RELATORIO_DIR}")
    print("="*70)

if __name__ == "__main__":
    main()
