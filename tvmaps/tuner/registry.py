"""What the tuner can edit: the offset-idiom label tables and their maps.

Every table here follows the same editing idiom — a spec dataclass with km
offsets from an anchor (dx/dy), an optional leader-line callout (tx/ty) and
alignment fields. Absolute lon/lat specs (rivers, mountain ranges, product
zones) are a future extension and are not listed.
"""

import importlib
from dataclasses import dataclass, fields as dc_fields

from .. import style

# Fields the editor may change. Display overrides (text, wrap) are shown but
# never written back.
NON_EDITABLE = {"text", "wrap"}


@dataclass(frozen=True)
class Table:
    id: str            # module-level dict variable name == hooks table_id
    module: str        # dotted module owning the dict
    factory: str       # constructor name as written in source
    display: str | None = None   # key -> name lookup: "ccaa" | "prov" | None
    weight: str = "extrabold"    # font weight the map draws this table with
    numbered: bool = False       # rank-badge labels (spain-ciudades)


TABLES = {
    "CCAA_LABELS": Table("CCAA_LABELS", "tvmaps.maps_spain", "Label",
                         display="ccaa"),
    "PROV_LABELS": Table("PROV_LABELS", "tvmaps.maps_spain", "PLabel",
                         display="prov"),
    "NUM_LABELS": Table("NUM_LABELS", "tvmaps.maps_spain", "Label",
                        display="prov"),
    "CONCEJO_OVERRIDES": Table("CONCEJO_OVERRIDES", "tvmaps.maps_asturias",
                               "Label"),
    "COMARCA_LABELS": Table("COMARCA_LABELS", "tvmaps.maps_asturias", "Label"),
    "TOWN_LABELS": Table("TOWN_LABELS", "tvmaps.maps_asturias", "Label",
                         weight="semibold"),
    "RIOS_TOWN_LABELS": Table("RIOS_TOWN_LABELS", "tvmaps.maps_asturias",
                              "Label"),
    "PROV_CAPITAL_LABELS": Table("PROV_CAPITAL_LABELS", "tvmaps.maps_capitals",
                                 "CityLabel"),
    "CCAA_CAPITAL_LABELS": Table("CCAA_CAPITAL_LABELS", "tvmaps.maps_capitals",
                                 "CityLabel"),
    "CITY_LABELS": Table("CITY_LABELS", "tvmaps.maps_ciudades", "CityLabel",
                         numbered=True),
    "CIUDADES": Table("CIUDADES", "tvmaps.maps_rios", "CitySpec"),
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


MAPS = {
    m.name: m for m in [
        Map("spain-comunidades", "Comunidades autónomas",
            "tvmaps.maps_spain", "map_spain_comunidades", ("CCAA_LABELS",),
            kwargs=(("labels", True),)),
        Map("spain-provincias-1", "Provincias (nombres 1 de 2)",
            "tvmaps.maps_spain", "map_spain_provincias", ("PROV_LABELS",),
            kwargs=(("group", "A"),), group="A"),
        Map("spain-provincias-2", "Provincias (nombres 2 de 2)",
            "tvmaps.maps_spain", "map_spain_provincias", ("PROV_LABELS",),
            kwargs=(("group", "B"),), group="B"),
        Map("spain-provincias-numeros", "Provincias (números postales)",
            "tvmaps.maps_spain", "map_spain_provincias_numeros",
            ("NUM_LABELS",)),
        Map("spain-capitales-provincias", "Capitales de provincia",
            "tvmaps.maps_capitals", "map_spain_capitales_provincias",
            ("PROV_CAPITAL_LABELS",)),
        Map("spain-capitales-comunidades", "Capitales de comunidad",
            "tvmaps.maps_capitals", "map_spain_capitales_comunidades",
            ("CCAA_CAPITAL_LABELS",)),
        Map("spain-ciudades", "Los 30 municipios más poblados",
            "tvmaps.maps_ciudades", "map_spain_ciudades", ("CITY_LABELS",)),
        Map("spain-rios-ciudades", "Ríos y las ciudades que bañan",
            "tvmaps.maps_rios", "map_spain_rios_ciudades", ("CIUDADES",)),
        Map("asturias-concejos-1", "Concejos de Asturias (nombres 1 de 2)",
            "tvmaps.maps_asturias", "map_asturias_concejos",
            ("CONCEJO_OVERRIDES",), kwargs=(("group", "A"),), group="A"),
        Map("asturias-concejos-2", "Concejos de Asturias (nombres 2 de 2)",
            "tvmaps.maps_asturias", "map_asturias_concejos",
            ("CONCEJO_OVERRIDES",), kwargs=(("group", "B"),), group="B"),
        Map("asturias-comarcas", "Comarcas de Asturias",
            "tvmaps.maps_asturias", "map_asturias_comarcas",
            ("COMARCA_LABELS",)),
        Map("asturias-ciudades", "Villas y ciudades de Asturias",
            "tvmaps.maps_asturias", "map_asturias_ciudades", ("TOWN_LABELS",)),
        Map("asturias-rios", "Ríos de Asturias (pueblos de referencia)",
            "tvmaps.maps_asturias", "map_asturias_rios",
            ("RIOS_TOWN_LABELS",)),
    ]
}


def table_module(table_id):
    return importlib.import_module(TABLES[table_id].module)


def table_dict(table_id) -> dict:
    return getattr(table_module(table_id), table_id)


def factory_class(table_id):
    return getattr(table_module(table_id), TABLES[table_id].factory)


def field_defaults(table_id) -> dict:
    return {f.name: f.default for f in dc_fields(factory_class(table_id))}


def editable_fields(table_id) -> list:
    return [f.name for f in dc_fields(factory_class(table_id))
            if f.name not in NON_EDITABLE]


def display_name(table_id, key) -> str:
    """Human name for a table key (search lists, inserted-entry comments)."""
    kind = TABLES[table_id].display
    if kind == "ccaa":
        name = style.CCAA_DISPLAY.get(key, key)
    elif kind == "prov":
        name = style.PROVINCE_DISPLAY.get(key, key)
    else:
        name = key
    return name.replace("\n", " ")


def map_fn(map_name):
    m = MAPS[map_name]
    return getattr(importlib.import_module(m.module), m.fn), dict(m.kwargs)


def map_frame(map_name):
    m = MAPS[map_name]
    if m.module == "tvmaps.maps_asturias":
        from ..maps_asturias import asturias_scene
        return asturias_scene()["frame"]
    from ..maps_spain import spain_scene
    return spain_scene()["frame"]


def schema(table_id) -> dict:
    t = TABLES[table_id]
    defaults = field_defaults(table_id)
    return dict(
        factory=t.factory,
        fields=defaults,
        editable=editable_fields(table_id),
        weight=t.weight,
        numbered=t.numbered,
        has_callout="tx" in defaults,
        has_group="group" in defaults,
        has_va="va" in defaults,
    )
