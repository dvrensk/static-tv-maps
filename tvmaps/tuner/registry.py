"""What the tuner can edit: label tables, their shapes, and their maps.

Three editing idioms:
- "offset":   km offsets from a geometry/point anchor (dx/dy), optional
              leader-line callout (tx/ty) — the Label/CityLabel family.
- "block":    a text block hung off a fixed point by (tx/ty) km with a
              built-in leader (moda firms, marcas hubs, logo chips).
- "absolute": the spec owns its position as lon/lat plus a rotation
              (river names, mountain ranges).

Containers: most tables are plain dicts; a few are lists keyed by a field
(`key_field`), one nests its spec in a (points, spec) tuple (HAND_RIVERS),
and one is a bare single-spec assignment (CANARY_FIRM).

The Gijón street maps (maps_gijon) are deliberately absent: their labels
live in nested per-map config dicts with tuple values and no Figure-returning
entry point — supporting them needs its own pass.
"""

import importlib
from dataclasses import MISSING, dataclass, fields as dc_fields

from .. import style

# Fields the editor never touches. Display overrides (text, wrap), documentary
# fields, and identity/geometry facts that are not placement.
NON_EDITABLE = {"text", "wrap", "icon", "reason", "main", "company", "cat",
                "city", "brands", "kind", "lonlat", "leader", "dot",
                "city_size"}


@dataclass(frozen=True)
class Table:
    id: str            # unique tuner id == hooks table_id
    module: str        # dotted module owning the table
    factory: str       # constructor name as written in source
    var: str | None = None       # source variable name when != id
    container: str = "dict"      # dict | list | tuple2 | single
    key_field: str | None = None # list containers: spec field holding the key
    idiom: str = "offset"        # offset | block | absolute
    display: str | None = None   # key -> name: "ccaa" | "prov" | "ca" | None
    weight: str = "extrabold"    # font weight the map draws this table with
    numbered: bool = False       # rank-badge labels (spain-ciudades)
    size_field: str | None = "size"  # None → size comes from a tier/constant
    exclude: tuple = ()          # extra non-editable fields for this table

    @property
    def source_var(self):
        return self.var or self.id


TABLES = {
    t.id: t for t in [
        # --- offset idiom: the Label / CityLabel family -------------------
        Table("CCAA_LABELS", "tvmaps.maps_spain", "Label", display="ccaa"),
        Table("PROV_LABELS", "tvmaps.maps_spain", "PLabel", display="prov"),
        Table("NUM_LABELS", "tvmaps.maps_spain", "Label", display="prov"),
        Table("CONCEJO_OVERRIDES", "tvmaps.maps_asturias", "Label"),
        Table("COMARCA_LABELS", "tvmaps.maps_asturias", "Label"),
        Table("TOWN_LABELS", "tvmaps.maps_asturias", "Label",
              weight="semibold", exclude=("size",), size_field=None),
        Table("RIOS_TOWN_LABELS", "tvmaps.maps_asturias", "Label"),
        Table("PROV_CAPITAL_LABELS", "tvmaps.maps_capitals", "CityLabel"),
        Table("CCAA_CAPITAL_LABELS", "tvmaps.maps_capitals", "CityLabel"),
        Table("CITY_LABELS", "tvmaps.maps_ciudades", "CityLabel",
              numbered=True),
        Table("CIUDADES", "tvmaps.maps_rios", "CitySpec"),
        Table("COMM_LABELS", "tvmaps.maps_comcap", "Label", display="ccaa"),
        Table("CAP_LABELS", "tvmaps.maps_comcap", "CityLabel",
              weight="semibold"),
        Table("REGIONALS", "tvmaps.maps_editoriales", "CityCo"),
        Table("ICONOS", "tvmaps.maps_iconos", "IconSpec", var="ICONS",
              display="prov", size_field="name_size"),
        Table("COTIDIANO", "tvmaps.maps_cotidiano", "IconSpec", var="ICONS",
              display="prov", size_field="name_size"),
        Table("COUNTRY_LABELS", "tvmaps.maps_centroamerica", "Place",
              display="ca"),
        Table("CAPITAL_LABELS", "tvmaps.maps_centroamerica", "Place",
              display="ca"),
        Table("EXT_COUNTRY_LABELS", "tvmaps.maps_centroamerica", "Place",
              display="ca"),
        # --- block idiom: text blocks hung off a dot ----------------------
        Table("FIRMS", "tvmaps.maps_moda", "Firm", container="list",
              key_field="city", idiom="block", size_field="brand_size",
              exclude=("lat", "lon")),
        Table("CANARY_FIRM", "tvmaps.maps_moda", "Firm", container="single",
              idiom="block", size_field="brand_size",
              exclude=("lat", "lon")),
        Table("HUBS", "tvmaps.maps_marcas", "Hub", container="list",
              key_field="city", idiom="block", size_field="brand_size"),
        Table("PLACE", "tvmaps.maps_marcas_logos", "Place", idiom="block",
              size_field=None),
        # --- absolute idiom: lon/lat + rotation ---------------------------
        Table("RIVER_LABELS", "tvmaps.maps_fisica", "RiverLabel",
              idiom="absolute", weight="semibold"),
        Table("RANGE_LABELS", "tvmaps.maps_fisica", "RangeLabel",
              container="list", key_field="text", idiom="absolute"),
        Table("RIOS_LABELS", "tvmaps.maps_rios", "RiverSpec",
              idiom="absolute", weight="semibold"),
        Table("CIUDADES_RIVER_LABELS", "tvmaps.maps_rios", "RiverSpec",
              idiom="absolute", weight="semibold"),
        Table("RANGE_LABELS_RIOS", "tvmaps.maps_rios", "RangeSpec",
              container="list", key_field="text", idiom="absolute"),
        Table("HAND_RIVERS", "tvmaps.maps_rios", "RiverSpec",
              container="tuple2", idiom="absolute", weight="semibold"),
        Table("ASTURIAS_RIOS", "tvmaps.maps_asturias", "RiverSpec",
              idiom="absolute", weight="semibold"),
    ]
}


@dataclass(frozen=True)
class Map:
    name: str          # map name as in generate.py
    title: str
    module: str
    fn: str            # map_* function returning a Figure
    tables: tuple
    kwargs: tuple = () # ((key, value), ...) passed to fn
    group: str | None = None   # split-map group shown on this map
    scene: tuple = ("tvmaps.maps_spain", "spain_scene")
    crs: str = "MAIN_CRS"      # attribute of tvmaps.geo (for lon/lat math)


_AST = ("tvmaps.maps_asturias", "asturias_scene")
_CA = ("tvmaps.maps_centroamerica", "scene")
_CA_EXT = ("tvmaps.maps_centroamerica", "ext_scene")

MAPS = {
    m.name: m for m in [
        Map("spain-comunidades", "Comunidades autónomas",
            "tvmaps.maps_spain", "map_spain_comunidades", ("CCAA_LABELS",),
            kwargs=(("labels", True),)),
        Map("spain-comunidades-capitales", "Comunidades y sus capitales",
            "tvmaps.maps_comcap", "map_spain_comunidades_capitales",
            ("COMM_LABELS", "CAP_LABELS")),
        Map("spain-provincias-1", "Provincias (nombres 1 de 2)",
            "tvmaps.maps_spain", "map_spain_provincias", ("PROV_LABELS",),
            kwargs=(("group", "A"),), group="A"),
        Map("spain-provincias-2", "Provincias (nombres 2 de 2)",
            "tvmaps.maps_spain", "map_spain_provincias", ("PROV_LABELS",),
            kwargs=(("group", "B"),), group="B"),
        Map("spain-provincias-numeros", "Provincias (números postales)",
            "tvmaps.maps_spain", "map_spain_provincias_numeros",
            ("NUM_LABELS",)),
        Map("spain-provincias-iconos", "Provincias · iconos típicos",
            "tvmaps.maps_iconos", "map_spain_provincias_iconos", ("ICONOS",)),
        Map("spain-provincias-cotidiano", "Provincias · el día a día",
            "tvmaps.maps_cotidiano", "map_spain_provincias_cotidiano",
            ("COTIDIANO",)),
        Map("spain-capitales-provincias", "Capitales de provincia",
            "tvmaps.maps_capitals", "map_spain_capitales_provincias",
            ("PROV_CAPITAL_LABELS",)),
        Map("spain-capitales-comunidades", "Capitales de comunidad",
            "tvmaps.maps_capitals", "map_spain_capitales_comunidades",
            ("CCAA_CAPITAL_LABELS",)),
        Map("spain-ciudades", "Los 30 municipios más poblados",
            "tvmaps.maps_ciudades", "map_spain_ciudades", ("CITY_LABELS",)),
        Map("spain-fisica", "España física",
            "tvmaps.maps_fisica", "map_spain_fisica",
            ("RIVER_LABELS", "RANGE_LABELS")),
        Map("spain-rios", "Los ríos de España",
            "tvmaps.maps_rios", "map_spain_rios",
            ("RIOS_LABELS", "RANGE_LABELS_RIOS")),
        Map("spain-rios-ciudades", "Ríos y las ciudades que bañan",
            "tvmaps.maps_rios", "map_spain_rios_ciudades",
            ("CIUDADES", "CIUDADES_RIVER_LABELS", "HAND_RIVERS")),
        Map("spain-moda", "Moda de España",
            "tvmaps.maps_moda", "map_spain_moda",
            ("FIRMS", "CANARY_FIRM")),
        Map("spain-editoriales", "Editoriales y discográficas",
            "tvmaps.maps_editoriales", "map_spain_editoriales",
            ("REGIONALS",)),
        Map("spain-marcas", "Marcas de España",
            "tvmaps.maps_marcas", "map_spain_marcas", ("HUBS",)),
        Map("spain-marcas-logos", "Marcas de España (logos)",
            "tvmaps.maps_marcas_logos", "map_spain_marcas_logos",
            ("PLACE",)),
        Map("asturias-concejos-1", "Concejos de Asturias (nombres 1 de 2)",
            "tvmaps.maps_asturias", "map_asturias_concejos",
            ("CONCEJO_OVERRIDES",), kwargs=(("group", "A"),), group="A",
            scene=_AST),
        Map("asturias-concejos-2", "Concejos de Asturias (nombres 2 de 2)",
            "tvmaps.maps_asturias", "map_asturias_concejos",
            ("CONCEJO_OVERRIDES",), kwargs=(("group", "B"),), group="B",
            scene=_AST),
        Map("asturias-comarcas", "Comarcas de Asturias",
            "tvmaps.maps_asturias", "map_asturias_comarcas",
            ("COMARCA_LABELS",), scene=_AST),
        Map("asturias-ciudades", "Villas y ciudades de Asturias",
            "tvmaps.maps_asturias", "map_asturias_ciudades", ("TOWN_LABELS",),
            scene=_AST),
        Map("asturias-rios", "Ríos de Asturias",
            "tvmaps.maps_asturias", "map_asturias_rios",
            ("RIOS_TOWN_LABELS", "ASTURIAS_RIOS"), scene=_AST),
        Map("centroamerica", "América Central",
            "tvmaps.maps_centroamerica", "map_centroamerica",
            ("COUNTRY_LABELS", "CAPITAL_LABELS"), scene=_CA,
            crs="CENTRAL_AMERICA_CRS"),
        Map("mexico-centroamerica-caribe", "México, Centroamérica y Caribe",
            "tvmaps.maps_centroamerica", "map_mexico_centroamerica_caribe",
            ("EXT_COUNTRY_LABELS",), scene=_CA_EXT, crs="MEXICO_CARIBE_CRS"),
    ]
}


def table_module(table_id):
    return importlib.import_module(TABLES[table_id].module)


def table_source(table_id):
    """The raw module-level object the table lives in."""
    return getattr(table_module(table_id), TABLES[table_id].source_var)


def entries(table_id) -> dict:
    """key -> spec view of the table, whatever its container shape."""
    t = TABLES[table_id]
    src = table_source(table_id)
    if t.container == "dict":
        return src
    if t.container == "list":
        return {getattr(s, t.key_field): s for s in src}
    if t.container == "tuple2":
        return {k: v[1] for k, v in src.items()}
    return {t.id: src}  # single


def set_entry(table_id, key, spec):
    """Update the in-memory table so the warm process matches the file."""
    t = TABLES[table_id]
    src = table_source(table_id)
    if t.container == "dict":
        src[key] = spec
    elif t.container == "list":
        for i, s in enumerate(src):
            if getattr(s, t.key_field) == key:
                src[i] = spec
                return
        raise KeyError(key)
    elif t.container == "tuple2":
        src[key] = (src[key][0], spec)
    else:  # single
        setattr(table_module(table_id), t.source_var, spec)


def factory_class(table_id):
    return getattr(table_module(table_id), TABLES[table_id].factory)


def field_defaults(table_id) -> dict:
    """field -> default; required fields map to the MISSING sentinel."""
    return {f.name: f.default for f in dc_fields(factory_class(table_id))}


def required_fields(table_id) -> set:
    return {f.name for f in dc_fields(factory_class(table_id))
            if f.default is MISSING and f.default_factory is MISSING}


def editable_fields(table_id) -> list:
    skip = NON_EDITABLE | set(TABLES[table_id].exclude)
    return [f.name for f in dc_fields(factory_class(table_id))
            if f.name not in skip]


_PROV_NAMES = None


def _prov_names() -> dict:
    """prov_code -> official name, for provinces without a display override."""
    global _PROV_NAMES
    if _PROV_NAMES is None:
        from .. import geo
        gdf = geo.load("provincias")
        _PROV_NAMES = dict(zip(gdf.prov_code, gdf.prov_name))
    return _PROV_NAMES


def display_name(table_id, key) -> str:
    """Human name for a table key (search lists, inserted-entry comments)."""
    kind = TABLES[table_id].display
    if kind == "ccaa":
        name = style.CCAA_DISPLAY.get(key, key)
    elif kind == "prov":
        name = style.PROVINCE_DISPLAY.get(key) or _prov_names().get(key, key)
    elif kind == "ca":
        from ..maps_centroamerica import COUNTRY_NAMES
        name = COUNTRY_NAMES.get(key, key)
    else:
        name = key
    return name.replace("\n", " ")


def map_fn(map_name):
    m = MAPS[map_name]
    return getattr(importlib.import_module(m.module), m.fn), dict(m.kwargs)


def map_frame(map_name):
    m = MAPS[map_name]
    scene = getattr(importlib.import_module(m.scene[0]), m.scene[1])
    return scene()["frame"]


def map_crs(map_name) -> str:
    from .. import geo
    return getattr(geo, MAPS[map_name].crs)


def schema(table_id) -> dict:
    t = TABLES[table_id]
    defaults = {k: (None if v is MISSING else v)
                for k, v in field_defaults(table_id).items()}
    editable = editable_fields(table_id)
    return dict(
        factory=t.factory,
        fields=defaults,
        required=sorted(required_fields(table_id)),
        editable=editable,
        idiom=t.idiom,
        weight=t.weight,
        numbered=t.numbered,
        size_field=t.size_field if t.size_field in editable else None,
        has_callout=t.idiom == "offset" and "tx" in defaults,
        has_group="group" in defaults,
        has_va="va" in defaults,
    )
