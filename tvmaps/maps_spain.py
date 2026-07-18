"""Spain-wide maps: autonomous communities and provinces."""

from dataclasses import dataclass

from . import draw, geo, style

KM = 1000.0  # offsets below are given in km for readability


def _project_lonlat(lon, lat):
    import geopandas as gpd
    from shapely.geometry import Point

    return (
        gpd.GeoSeries([Point(lon, lat)], crs="EPSG:4326")
        .to_crs(geo.MAIN_CRS)
        .iloc[0]
        .coords[0]
    )


def spain_scene():
    """Everything shared by the Spain-wide maps: projected layers, the 16:9
    frame, and the Canary Islands translated into the lower-left corner."""
    ccaa = geo.load("comunidades")
    prov = geo.load("provincias")
    countries = geo.load("context_countries").to_crs(geo.MAIN_CRS)

    ccaa_pen = ccaa[ccaa.acom_code != "05"].to_crs(geo.MAIN_CRS)
    prov_pen = prov[prov.acom_code != "05"].to_crs(geo.MAIN_CRS)
    # Keep just enough sea at the top for the northern callout labels; every
    # km of padding makes the peninsula smaller.
    frame = geo.compute_frame(ccaa_pen.total_bounds, pad=(0.03, 0.05, 0.03, 0.085))
    # The Canary inset may cover Portugal or Morocco but never Spain: cap its
    # right edge just west of the Huelva coast.
    limit = _project_lonlat(-7.6, 37.0)[0]
    ccaa_can, box, tf = geo.place_canary(ccaa[ccaa.acom_code == "05"], frame, max_x=limit)
    prov_can, _, _ = geo.place_canary(prov[prov.acom_code == "05"], frame, max_x=limit)

    return dict(
        frame=frame,
        countries=countries,
        ccaa_pen=ccaa_pen,
        ccaa_can=ccaa_can,
        prov_pen=prov_pen,
        prov_can=prov_can,
        canary_box=box,
        canary_tf=tf,
    )


COUNTRY_LABELS = [
    ("PORTUGAL", -8.05, 39.55, 46, 90),
    ("FRANCIA", 1.7, 43.85, 46, 0),
    ("MARRUECOS", -4.9, 35.02, 36, 0),
]


def _draw_country_labels(ax, frame):
    fx0, fy0, fx1, fy1 = frame
    for text, lon, lat, size, rotation in COUNTRY_LABELS:
        x, y = _project_lonlat(lon, lat)
        if fx0 < x < fx1 and fy0 < y < fy1:
            t = draw.halo_text(ax, x, y, text, size, weight="semibold",
                               color=style.NEIGHBOR_LABEL, halo_width=6, zorder=5)
            t.set_rotation(rotation)


# ---------------------------------------------------------------------------
# Communities map
# ---------------------------------------------------------------------------

@dataclass
class Label:
    size: float = 54
    dx: float = 0.0          # anchor shift, km
    dy: float = 0.0
    # If set, the label is drawn away from the feature with a leader line,
    # offset by (tx, ty) km from the anchor point.
    tx: float | None = None
    ty: float | None = None
    ha: str = "center"


CCAA_LABELS = {
    "01": Label(),                      # Andalucía
    "02": Label(),                      # Aragón
    "03": Label(46),                    # Asturias
    "04": Label(44, dx=-30, dy=-75),    # Islas Baleares — at sea below Mallorca
    "06": Label(40, tx=-20, ty=75),     # Cantabria — callout into the sea
    "07": Label(),                      # Castilla y León
    "08": Label(54, dx=-35),            # Castilla-La Mancha
    "09": Label(),                      # Cataluña
    "10": Label(38, dx=28, dy=-25),     # Comunidad Valenciana
    "11": Label(52, dx=-25, dy=-20),    # Extremadura
    "12": Label(48),                    # Galicia
    "13": Label(40),                    # Madrid
    "14": Label(40),                    # Murcia
    "15": Label(40),                    # Navarra
    "16": Label(40, tx=75, ty=100),     # País Vasco — callout into the sea
    "17": Label(30),                    # La Rioja
    "18": Label(34, tx=-55, ty=25, ha="right"),    # Ceuta
    "19": Label(34, tx=25, ty=45, ha="left"),      # Melilla
}


def _label_regions(ax, gdf, code_field, name_lookup, specs, default_size=54):
    for _, row in gdf.iterrows():
        code = row[code_field]
        spec = specs.get(code)
        if spec is None:
            continue
        text = name_lookup(code, row)
        x, y = geo.label_point(row.geometry)
        x, y = x + spec.dx * KM, y + spec.dy * KM
        if spec.tx is not None:
            draw.callout(ax, (x, y), (x + spec.tx * KM, y + spec.ty * KM),
                         text, spec.size, weight="extrabold", ha=spec.ha)
        else:
            draw.halo_text(ax, x, y, text, spec.size, weight="extrabold")


def map_spain_comunidades(labels=True):
    s = spain_scene()
    fig, ax = draw.new_map(s["frame"])
    draw.draw_context(ax, s["countries"])

    colors = [style.CCAA_COLORS[c] for c in s["ccaa_pen"].acom_code]
    draw.draw_layer(ax, s["ccaa_pen"], colors, style.BORDER_DARK, 3.0, zorder=2)

    draw.draw_inset_box(ax, s["canary_box"], label="Canarias" if labels else None)
    draw.draw_layer(ax, s["ccaa_can"], style.CCAA_COLORS["05"],
                    style.BORDER_DARK, 2.0, zorder=4)

    if labels:
        _label_regions(ax, s["ccaa_pen"], "acom_code",
                       lambda c, r: style.CCAA_DISPLAY[c], CCAA_LABELS)
        footer = "Comunidades autónomas de España"
    else:
        footer = "Mapa mudo · Comunidades autónomas de España"
    _draw_country_labels(ax, s["frame"])
    draw.draw_footer(ax, s["frame"], footer)
    draw.draw_attribution(ax, s["frame"])
    return fig


def render_spain_comunidades():
    return draw.save(map_spain_comunidades(labels=True), "spain-comunidades")


def render_spain_comunidades_mudo():
    return draw.save(map_spain_comunidades(labels=False), "spain-comunidades-mudo")


# ---------------------------------------------------------------------------
# Provinces maps
# ---------------------------------------------------------------------------

@dataclass
class PLabel(Label):
    group: str = "A"   # which of the two maps carries this province's name


# All 50 provinces (+ Ceuta and Melilla) split into two interleaved label
# groups, so that on each map every label has room to breathe.
PROV_LABELS = {
    # Galicia
    "15": PLabel(32, group="A", dx=15),                 # A Coruña
    "27": PLabel(34, group="B"),                 # Lugo
    "32": PLabel(34, group="A", dx=10, dy=-15),                 # Ourense
    "36": PLabel(28, group="B", dx=12),                 # Pontevedra
    # Cornisa cantábrica
    "33": PLabel(38, group="A"),                 # Asturias
    "39": PLabel(30, group="B", tx=-25, ty=65),  # Cantabria
    # País Vasco
    "01": PLabel(26, group="A"),                 # Álava
    "48": PLabel(30, group="B", tx=-30, ty=75),  # Bizkaia
    "20": PLabel(30, group="B", tx=45, ty=100),  # Gipuzkoa
    # Navarra / La Rioja / Aragón
    "31": PLabel(36, group="A"),                 # Navarra
    "26": PLabel(26, group="B", dx=20, dy=-6),                 # La Rioja
    "22": PLabel(40, group="A"),                 # Huesca
    "50": PLabel(40, group="B"),                 # Zaragoza
    "44": PLabel(38, group="A"),                 # Teruel
    # Cataluña
    "17": PLabel(36, group="A"),                 # Girona
    "25": PLabel(36, group="B"),                 # Lleida
    "08": PLabel(36, group="B", dx=25, dy=-8),                 # Barcelona
    "43": PLabel(34, group="A", dx=-10, dy=20),                 # Tarragona
    # Castilla y León
    "24": PLabel(40, group="A"),                 # León
    "49": PLabel(36, group="B"),                 # Zamora
    "34": PLabel(34, group="B"),                 # Palencia
    "09": PLabel(38, group="B", dx=-15),                 # Burgos
    "47": PLabel(36, group="A"),                 # Valladolid
    "37": PLabel(38, group="B"),                 # Salamanca
    "40": PLabel(32, group="B"),                 # Segovia
    "42": PLabel(36, group="A"),                 # Soria
    "05": PLabel(32, group="A"),                 # Ávila
    # Madrid / Castilla-La Mancha
    "28": PLabel(32, group="A"),                 # Madrid
    "19": PLabel(34, group="B"),                 # Guadalajara
    "45": PLabel(38, group="A", dx=30, dy=-8),                 # Toledo
    "16": PLabel(40, group="B"),                 # Cuenca
    "13": PLabel(40, group="B"),                 # Ciudad Real
    "02": PLabel(40, group="A"),                 # Albacete
    # Comunidad Valenciana / Murcia
    "12": PLabel(34, group="B"),                 # Castellón
    "46": PLabel(36, group="A"),                 # Valencia
    "03": PLabel(34, group="B"),                 # Alicante
    "30": PLabel(38, group="A"),                 # Murcia
    # Extremadura
    "10": PLabel(40, group="A"),                 # Cáceres
    "06": PLabel(40, group="B"),                 # Badajoz
    # Andalucía
    "21": PLabel(34, group="A", dx=10),                 # Huelva
    "41": PLabel(38, group="B"),                 # Sevilla
    "11": PLabel(34, group="B"),                 # Cádiz
    "29": PLabel(34, group="B"),                 # Málaga
    "14": PLabel(38, group="A"),                 # Córdoba
    "23": PLabel(38, group="B"),                 # Jaén
    "18": PLabel(36, group="A", dx=-30),                 # Granada
    "04": PLabel(34, group="A", dx=30, dy=-10),                 # Almería
    # Islas
    "07": PLabel(34, group="A", dx=-30, dy=-75), # Illes Balears
    "35": PLabel(32, group="A", dy=-55),         # Las Palmas
    "38": PLabel(30, group="B", dy=-65),         # Santa Cruz de Tenerife
    # Ciudades autónomas
    "51": PLabel(28, group="A", tx=-55, ty=25, ha="right"),  # Ceuta
    "52": PLabel(28, group="B", tx=25, ty=45, ha="left"),    # Melilla
}


def _province_colors(prov):
    colors = []
    counters = {}
    for _, row in prov.iterrows():
        i = counters.setdefault(row.acom_code, 0)
        counters[row.acom_code] += 1
        base = style.CCAA_COLORS[row.acom_code]
        colors.append(style.shade(base, style.PROVINCE_SHADES[i % len(style.PROVINCE_SHADES)]))
    return colors


def _prov_name(code, row):
    return style.PROVINCE_DISPLAY.get(code, row.prov_name)


def map_spain_provincias(group=None):
    s = spain_scene()
    fig, ax = draw.new_map(s["frame"])
    draw.draw_context(ax, s["countries"])

    draw.draw_layer(ax, s["prov_pen"], _province_colors(s["prov_pen"]),
                    style.BORDER_LIGHT, 1.8, zorder=2)
    # Thick community borders on top of the thin province borders.
    draw.draw_layer(ax, s["ccaa_pen"], "none", style.BORDER_DARK, 3.2, zorder=3)

    draw.draw_inset_box(ax, s["canary_box"],
                        label="Islas Canarias" if group else None)
    draw.draw_layer(ax, s["prov_can"], _province_colors(s["prov_can"]),
                    style.BORDER_LIGHT, 1.8, zorder=4)
    draw.draw_layer(ax, s["ccaa_can"], "none", style.BORDER_DARK, 2.2, zorder=5)

    if group:
        specs = {c: sp for c, sp in PROV_LABELS.items() if sp.group == group}
        _label_regions(ax, s["prov_pen"], "prov_code", _prov_name, specs)
        _label_regions(ax, s["prov_can"], "prov_code", _prov_name, specs)
        n = "1" if group == "A" else "2"
        footer = (f"Provincias de España (nombres {n} de 2) · "
                  "colores por comunidad autónoma")
    else:
        footer = "Mapa mudo · Provincias de España"
    _draw_country_labels(ax, s["frame"])
    draw.draw_footer(ax, s["frame"], footer)
    draw.draw_attribution(ax, s["frame"])
    return fig


def render_spain_provincias_1():
    return draw.save(map_spain_provincias("A"), "spain-provincias-1")


def render_spain_provincias_2():
    return draw.save(map_spain_provincias("B"), "spain-provincias-2")


def render_spain_provincias_mudo():
    return draw.save(map_spain_provincias(None), "spain-provincias-mudo")


# Number placement: numbers are compact, so nearly all fit directly; only the
# smallest features get size tweaks or (Ceuta/Melilla) leader lines.
NUM_LABELS = {
    "01": Label(36), "20": Label(34), "48": Label(34),   # País Vasco
    "26": Label(36), "28": Label(40), "39": Label(40),   # Rioja/Madrid/Cantabria
    "36": Label(40),                                      # Pontevedra
    "07": Label(40),                                      # Baleares (on Mallorca)
    "35": Label(38), "38": Label(38),                     # Canarias
    "51": Label(30, tx=-45, ty=20, ha="right"),           # Ceuta
    "52": Label(30, tx=20, ty=35, ha="left"),             # Melilla
}


def map_spain_provincias_numeros():
    s = spain_scene()
    fig, ax = draw.new_map(s["frame"])
    draw.draw_context(ax, s["countries"])

    draw.draw_layer(ax, s["prov_pen"], _province_colors(s["prov_pen"]),
                    style.BORDER_LIGHT, 1.8, zorder=2)
    draw.draw_layer(ax, s["ccaa_pen"], "none", style.BORDER_DARK, 3.2, zorder=3)
    draw.draw_inset_box(ax, s["canary_box"], label="Islas Canarias")
    draw.draw_layer(ax, s["prov_can"], _province_colors(s["prov_can"]),
                    style.BORDER_LIGHT, 1.8, zorder=4)
    draw.draw_layer(ax, s["ccaa_can"], "none", style.BORDER_DARK, 2.2, zorder=5)

    specs = {code: NUM_LABELS.get(code, Label(46)) for code in PROV_LABELS}
    for layer in (s["prov_pen"], s["prov_can"]):
        _label_regions(ax, layer, "prov_code", lambda c, r: c, specs)

    # Name legend: 01-26 over the Atlantic (above the Canary inset box),
    # 27-52 over the Mediterranean along the right edge.
    names = {}
    for _, row in geo.load("provincias").iterrows():
        names[row.prov_code] = style.PROVINCE_DISPLAY.get(
            row.prov_code, row.prov_name).replace("\n", " ")
    rows = [(code, names[code]) for code in sorted(names)]
    draw.legend_column(ax, s["frame"], 0.030, 0.86, rows[:26],
                       size=25, leading=1.38)
    draw.legend_column(ax, s["frame"], 0.855, 0.80, rows[26:],
                       size=25, leading=1.38)

    _draw_country_labels(ax, s["frame"])
    draw.draw_footer(ax, s["frame"],
                     "Provincias de España · el número es el prefijo "
                     "del código postal")
    draw.draw_attribution(ax, s["frame"])
    return fig


def render_spain_provincias_numeros():
    return draw.save(map_spain_provincias_numeros(), "spain-provincias-numeros")
