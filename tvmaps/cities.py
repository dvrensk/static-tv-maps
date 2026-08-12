"""City locations and metadata for the capitals and big-cities maps."""

import json

from . import geo


def load_points(crs=geo.MAIN_CRS):
    """key -> (x, y) in the requested CRS for every geocoded city."""
    import geopandas as gpd

    gdf = gpd.read_file(geo.PROCESSED / "cities.geojson").to_crs(crs)
    return {row.key: (row.geometry.x, row.geometry.y) for _, row in gdf.iterrows()}


# prov_code -> capital city key (keys of data/processed/cities.geojson)
PROV_CAPITALS = {
    "01": "Vitoria-Gasteiz", "02": "Albacete", "03": "Alicante",
    "04": "Almería", "05": "Ávila", "06": "Badajoz", "07": "Palma",
    "08": "Barcelona", "09": "Burgos", "10": "Cáceres", "11": "Cádiz",
    "12": "Castellón de la Plana", "13": "Ciudad Real", "14": "Córdoba",
    "15": "A Coruña", "16": "Cuenca", "17": "Girona", "18": "Granada",
    "19": "Guadalajara", "20": "San Sebastián", "21": "Huelva",
    "22": "Huesca", "23": "Jaén", "24": "León", "25": "Lleida",
    "26": "Logroño", "27": "Lugo", "28": "Madrid", "29": "Málaga",
    "30": "Murcia", "31": "Pamplona", "32": "Ourense", "33": "Oviedo",
    "34": "Palencia", "35": "Las Palmas de Gran Canaria",
    "36": "Pontevedra", "37": "Salamanca", "38": "Santa Cruz de Tenerife",
    "39": "Santander", "40": "Segovia", "41": "Sevilla", "42": "Soria",
    "43": "Tarragona", "44": "Teruel", "45": "Toledo", "46": "Valencia",
    "47": "Valladolid", "48": "Bilbao", "49": "Zamora", "50": "Zaragoza",
    "51": "Ceuta", "52": "Melilla",
}

# acom_code -> capital city key(s). Canarias has two co-capitals.
CCAA_CAPITALS = {
    "01": ["Sevilla"], "02": ["Zaragoza"], "03": ["Oviedo"], "04": ["Palma"],
    "05": ["Santa Cruz de Tenerife", "Las Palmas de Gran Canaria"],
    "06": ["Santander"], "07": ["Valladolid"], "08": ["Toledo"],
    "09": ["Barcelona"], "10": ["Valencia"], "11": ["Mérida"],
    "12": ["Santiago de Compostela"], "13": ["Madrid"], "14": ["Murcia"],
    "15": ["Pamplona"], "16": ["Vitoria-Gasteiz"], "17": ["Logroño"],
    "18": ["Ceuta"], "19": ["Melilla"],
}

# The 30 most populated municipalities (INE, 1 January 2025), leaving out
# municipalities that belong to the metropolitan areas of Madrid, Barcelona
# and Santa Cruz de Tenerife (L'Hospitalet, Terrassa, Badalona, Sabadell,
# Móstoles, Alcalá de Henares, Leganés, Getafe, Fuenlabrada, Alcorcón,
# San Cristóbal de La Laguna).
BIG_CITIES = [
    ("Madrid", 3_506_730),
    ("Barcelona", 1_731_649),
    ("Valencia", 840_792),
    ("Zaragoza", 693_091),
    ("Sevilla", 689_423),
    ("Málaga", 599_063),
    ("Murcia", 479_405),
    ("Palma", 434_786),
    ("Las Palmas de Gran Canaria", 381_868),
    ("Alicante", 366_221),
    ("Bilbao", 351_124),
    ("Córdoba", 323_262),
    ("Valladolid", 302_614),
    ("Vigo", 294_489),
    ("Gijón", 269_894),
    ("Vitoria-Gasteiz", 260_699),
    ("A Coruña", 251_543),
    ("Elche", 245_557),
    ("Granada", 233_975),
    ("Oviedo", 223_968),
    ("Cartagena", 220_704),
    ("Jerez de la Frontera", 213_634),
    ("Santa Cruz de Tenerife", 211_957),
    ("Pamplona", 209_094),
    ("Almería", 205_468),
    ("San Sebastián", 189_866),
    ("Castellón de la Plana", 183_711),
    ("Burgos", 177_402),
    ("Santander", 175_425),
    ("Albacete", 175_400),
]

# Concejos of Asturias over 10 000 inhabitants (INE 2023) and their capital
# town, which is where the dot goes.
ASTURIAS_TOWNS = [
    # (town key, concejo, population)
    ("Gijón", "Gijón", 268_313),
    ("Oviedo", "Oviedo", 217_584),
    ("Avilés", "Avilés", 75_518),
    ("Pola de Siero", "Siero", 52_194),
    ("Langreo", "Langreo", 37_978),
    ("Mieres", "Mieres", 36_195),
    ("Piedras Blancas", "Castrillón", 22_103),
    ("Nubledo", "Corvera de Asturias", 15_612),
    ("Sotrondio", "San Martín del Rey Aurelio", 15_431),
    ("Villaviciosa", "Villaviciosa", 15_000),
    ("Posada", "Llanera", 13_948),
    ("Llanes", "Llanes", 13_524),
    ("Pola de Laviana", "Laviana", 12_355),
    ("Cangas del Narcea", "Cangas del Narcea", 11_596),
    ("Luarca", "Valdés", 10_958),
    ("Luanco", "Gozón", 10_470),
    ("Pola de Lena", "Lena", 10_312),
    ("Candás", "Carreño", 10_177),
    ("Cabañaquinta", "Aller", 10_076),
]

# The eight functional comarcas of Asturias (decree 11/91) -> their concejos.
ASTURIAS_COMARCAS = {
    "Eo-Navia": [
        "Boal", "Castropol", "Coaña", "El Franco", "Grandas de Salime",
        "Illano", "Navia", "Pesoz", "San Martín de Oscos", "San Tirso de Abres",
        "Santa Eulalia de Oscos", "Tapia de Casariego", "Taramundi", "Valdés",
        "Vegadeo", "Villanueva de Oscos", "Villayón",
    ],
    "Narcea": ["Allande", "Cangas del Narcea", "Degaña", "Ibias", "Tineo"],
    "Avilés": [
        "Avilés", "Candamo", "Castrillón", "Corvera de Asturias", "Cudillero",
        "Gozón", "Illas", "Muros de Nalón", "Pravia", "Soto del Barco",
    ],
    "Oviedo": [
        "Belmonte de Miranda", "Bimenes", "Cabranes", "Grado", "Llanera",
        "Morcín", "Nava", "Noreña", "Oviedo", "Proaza", "Quirós",
        "Las Regueras", "Ribera de Arriba", "Riosa", "Salas", "Santo Adriano",
        "Sariego", "Siero", "Somiedo", "Teverga", "Yernes y Tameza",
    ],
    "Gijón": ["Carreño", "Gijón", "Villaviciosa"],
    "Caudal": ["Aller", "Lena", "Mieres"],
    "Nalón": ["Caso", "Langreo", "Laviana", "San Martín del Rey Aurelio",
              "Sobrescobio"],
    "Oriente": [
        "Amieva", "Cabrales", "Cangas de Onís", "Caravia", "Colunga", "Llanes",
        "Onís", "Parres", "Peñamellera Alta", "Peñamellera Baja", "Piloña",
        "Ponga", "Ribadedeva", "Ribadesella",
    ],
}


# Padrón population of every concejo of Asturias, INE 1 January 2025
# (tabla 2886, "Asturias: Población por municipios y sexo",
# https://www.ine.es/jaxiT3/Tabla.htm?t=2886). Names as in ASTURIAS_COMARCAS.
# Total: 1 013 529 (Asturias). Used to sum populations per comarca.
CONCEJO_POPULATION = {
    "Allande": 1_506,
    "Aller": 10_011,
    "Amieva": 591,
    "Avilés": 75_517,
    "Belmonte de Miranda": 1_366,
    "Bimenes": 1_639,
    "Boal": 1_372,
    "Cabrales": 1_884,
    "Cabranes": 1_094,
    "Candamo": 1_902,
    "Cangas de Onís": 6_344,
    "Cangas del Narcea": 11_282,
    "Caravia": 486,
    "Carreño": 10_292,
    "Caso": 1_437,
    "Castrillón": 21_998,
    "Castropol": 3_202,
    "Coaña": 3_321,
    "Colunga": 3_143,
    "Corvera de Asturias": 15_785,
    "Cudillero": 4_867,
    "Degaña": 768,
    "El Franco": 3_728,
    "Gijón": 269_894,
    "Gozón": 10_407,
    "Grado": 9_681,
    "Grandas de Salime": 767,
    "Ibias": 1_084,
    "Illano": 277,
    "Illas": 1_048,
    "Langreo": 38_612,
    "Las Regueras": 1_892,
    "Laviana": 12_352,
    "Lena": 10_382,
    "Llanera": 14_020,
    "Llanes": 13_486,
    "Mieres": 36_373,
    "Morcín": 2_460,
    "Muros de Nalón": 1_955,
    "Nava": 5_244,
    "Navia": 8_031,
    "Noreña": 5_131,
    "Onís": 739,
    "Oviedo": 223_968,
    "Parres": 5_150,
    "Pesoz": 134,
    "Peñamellera Alta": 500,
    "Peñamellera Baja": 1_194,
    "Piloña": 6_716,
    "Ponga": 576,
    "Pravia": 7_792,
    "Proaza": 686,
    "Quirós": 1_142,
    "Ribadedeva": 1_693,
    "Ribadesella": 5_591,
    "Ribera de Arriba": 1_852,
    "Riosa": 1_686,
    "Salas": 4_771,
    "San Martín de Oscos": 337,
    "San Martín del Rey Aurelio": 15_531,
    "San Tirso de Abres": 396,
    "Santa Eulalia de Oscos": 420,
    "Santo Adriano": 281,
    "Sariego": 1_252,
    "Siero": 53_049,
    "Sobrescobio": 838,
    "Somiedo": 1_031,
    "Soto del Barco": 3_801,
    "Tapia de Casariego": 3_538,
    "Taramundi": 545,
    "Teverga": 1_495,
    "Tineo": 8_679,
    "Valdés": 10_776,
    "Vegadeo": 3_928,
    "Villanueva de Oscos": 244,
    "Villaviciosa": 15_379,
    "Villayón": 1_054,
    "Yernes y Tameza": 134,
}


def comarca_population(comarca: str) -> int:
    """Padrón population of a functional comarca (sum of its concejos)."""
    return sum(CONCEJO_POPULATION[c] for c in ASTURIAS_COMARCAS[comarca])


def format_population(n: int) -> str:
    """Round to the nearest thousand, Spanish thousands separators."""
    rounded = round(n / 1000) * 1000
    return f"{rounded:,}".replace(",", ".")