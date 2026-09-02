"""Mapa-base vetorial do OpenFreeMap para uso com folium.

O folium so oferece mapas-base raster, e os atalhos 'cartodbpositron' /
'cartodbdark_matter' apontam para os tiles legados da CARTO, que passaram a
exigir API key e estao sendo descontinuados pelo provedor.

O OpenFreeMap serve tiles vetoriais de OpenStreetMap, open source, sem chave e
sem registro. Como e vetorial, quem desenha e o MapLibre; a ponte
maplibre-gl-leaflet entrega o resultado como uma camada Leaflet comum, entao a
camada continua aparecendo e alternando normalmente no LayerControl do folium.

Uso:

    from basemap_openfreemap import OpenFreeMapLayer

    m = folium.Map(location=..., zoom_start=7, tiles=None)
    OpenFreeMapLayer("positron", name="Claro").add_to(m)
    OpenFreeMapLayer("dark", name="Escuro", show=False).add_to(m)
"""

from __future__ import annotations

from branca.element import Figure, Template
from folium.map import Layer

MAPLIBRE_VERSAO = "5.9.0"
PONTE_VERSAO = "0.1.2"

ESTILOS = ("positron", "bright", "liberty", "dark")


class OpenFreeMapLayer(Layer):
    """Camada de mapa-base vetorial servida pelo OpenFreeMap."""

    _template = Template(
        """
        {% macro script(this, kwargs) %}
            var {{ this.get_name() }} = L.maplibreGL(
                {
                    "style": "https://tiles.openfreemap.org/styles/{{ this.estilo }}",
                    "interactive": false,
                    "attributionControl": false
                }
            );
        {% endmacro %}
        """
    )

    def __init__(
        self,
        estilo: str = "positron",
        name: str | None = None,
        overlay: bool = False,
        control: bool = True,
        show: bool = True,
    ) -> None:
        if estilo not in ESTILOS:
            raise ValueError(f"estilo '{estilo}' invalido; use um de {ESTILOS}")
        super().__init__(name=name or estilo, overlay=overlay, control=control, show=show)
        self._name = "OpenFreeMapLayer"
        self.estilo = estilo

    def render(self, **kwargs) -> None:
        figura = self.get_root()
        if not isinstance(figura, Figure):
            raise TypeError("OpenFreeMapLayer precisa estar dentro de uma Figure")
        # Carregados uma unica vez por figura, mesmo com varias camadas.
        figura.header.add_child(
            Template(
                f'<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/'
                f'maplibre-gl@{MAPLIBRE_VERSAO}/dist/maplibre-gl.css"/>'
            ),
            name="maplibre-gl-css",
        )
        figura.header.add_child(
            Template(
                f'<script src="https://cdn.jsdelivr.net/npm/'
                f'maplibre-gl@{MAPLIBRE_VERSAO}/dist/maplibre-gl.js"></script>'
            ),
            name="maplibre-gl-js",
        )
        figura.header.add_child(
            Template(
                f'<script src="https://cdn.jsdelivr.net/npm/@maplibre/'
                f'maplibre-gl-leaflet@{PONTE_VERSAO}/leaflet-maplibre-gl.js"></script>'
            ),
            name="maplibre-gl-leaflet",
        )
        super().render(**kwargs)
