"""Spain map with what everyday life brings to mind for each province — the
thing you would actually think of when you meet somebody from there.

Sister map of maps_iconos ("lo más típico"), same machinery, different
editorial rule: monuments, museums and dead artists are out unless they truly
dominate daily identity. In their place go food, fiestas, weather, work and
the things people actually live with. Meeting somebody from Sevilla you think
of flamenco (so it stays); meeting somebody from Málaga you don't ask about
Picasso's childhood — you think of espetos on the beach.

Position tuning (dx/dy/tx/ty) is carried over from maps_iconos since the
geometry and name lengths are identical.
"""

from . import draw
from .maps_iconos import IconSpec, build_icon_map

# prov_code -> icon. Reasons in Spanish; the table doubles as documentation
# and feeds the legend page (docs/leyenda-cotidiano.html).
ICONS = {
    # --- Galicia -----------------------------------------------------------
    "15": IconSpec("\U0001F455", "Zara / Inditex (Arteixo)",         # A Coruña
                   dx=-8, dy=28),
    "27": IconSpec("\U0001F404", "vacas y ternera gallega"),         # Lugo
    "32": IconSpec("\U0001F419", "pulpo á feira"),                   # Ourense
    "36": IconSpec("\U0001F990", "marisco y albariño",               # Pontevedra
                   dx=-10, dy=-30),
    # --- Cornisa cantábrica -----------------------------------------------
    "33": IconSpec("\U0001F37E", "sidra escanciada"),                # Asturias
    "39": IconSpec("\U0001F370", "sobaos y quesadas"),               # Cantabria
    # --- País Vasco -------------------------------------------------------
    "48": IconSpec("⚽", "el Athletic de Bilbao",                # Bizkaia
                   name_size=26, icon_size=46, tx=-48, ty=80),
    "20": IconSpec("\U0001F37D", "pintxos y sociedades",             # Gipuzkoa
                   name_size=26, icon_size=46, tx=46, ty=98),
    "01": IconSpec("\U0001F333", "Vitoria, capital verde",           # Álava
                   name_size=26, icon_size=48, dy=-6),
    # --- Navarra / La Rioja / Aragón --------------------------------------
    "31": IconSpec("\U0001F402", "San Fermín"),                      # Navarra
    "26": IconSpec("\U0001F377", "el vino",                          # La Rioja
                   name_size=26, icon_size=48, dx=18, dy=-6),
    "22": IconSpec("⛷", "esquí y montaña"),                     # Huesca
    "50": IconSpec("\U0001F4A8", "el cierzo"),                       # Zaragoza
    "44": IconSpec("❄", "el frío («Teruel existe»)"),           # Teruel
    # --- Cataluña ---------------------------------------------------------
    "25": IconSpec("\U0001F34E", "la fruta dulce"),                  # Lleida
    "43": IconSpec("\U0001F9C5", "calçotadas"),                      # Tarragona
    "08": IconSpec("⚽", "el Barça"),                            # Barcelona
    "17": IconSpec("\U0001F3D6", "la Costa Brava"),                  # Girona
    # --- Comunidad Valenciana / Murcia ------------------------------------
    "12": IconSpec("\U0001F9F1", "azulejos (cerámica)"),             # Castellón
    "46": IconSpec("\U0001F386", "las Fallas"),                      # Valencia
    "03": IconSpec("\U0001F3D9", "Benidorm y la playa"),             # Alicante
    "30": IconSpec("\U0001F96C", "la huerta de Europa"),             # Murcia
    # --- Andalucía --------------------------------------------------------
    "04": IconSpec("\U0001F345", "los invernaderos"),                # Almería
    "18": IconSpec("\U0001F37B", "tapas gratis"),                    # Granada
    "29": IconSpec("\U0001F41F", "espetos y playa"),                 # Málaga
    "23": IconSpec("\U0001FAD2", "aceite de oliva"),                 # Jaén
    "14": IconSpec("☀", "el calor"),                            # Córdoba
    "41": IconSpec("\U0001F483", "flamenco y Feria"),                # Sevilla
    "11": IconSpec("\U0001F3AD", "carnaval y guasa"),                # Cádiz
    "21": IconSpec("\U0001F353", "fresas y el Rocío"),               # Huelva
    # --- Extremadura ------------------------------------------------------
    "06": IconSpec("\U0001F356", "jamón ibérico"),                   # Badajoz
    "10": IconSpec("\U0001F336", "pimentón de la Vera"),             # Cáceres
    # --- Castilla-La Mancha / Madrid --------------------------------------
    "45": IconSpec("\U0001F36C", "mazapán", dx=22, dy=-30),          # Toledo
    "13": IconSpec("\U0001F9C0", "queso manchego"),                  # Ciudad Real
    "16": IconSpec("\U0001F3E0", "casas colgadas"),                  # Cuenca
    "19": IconSpec("\U0001F36F", "miel de la Alcarria",              # Guadalajara
                   dx=30, dy=6),
    "02": IconSpec("\U0001F52A", "navajas"),                         # Albacete
    "28": IconSpec("\U0001F687", "el metro y las prisas",            # Madrid
                   icon_size=52, dx=-12, dy=-16),
    # --- Castilla y León --------------------------------------------------
    "05": IconSpec("\U0001F969", "chuletón"),                        # Ávila
    "40": IconSpec("\U0001F416", "cochinillo", dx=8, dy=-30),        # Segovia
    "37": IconSpec("\U0001F393", "vida universitaria"),              # Salamanca
    "49": IconSpec("\U0001F56F", "Semana Santa"),                    # Zamora
    "47": IconSpec("\U0001F4AC", "«el mejor castellano»", dy=8),     # Valladolid
    "34": IconSpec("\U0001F33E", "Tierra de Campos"),                # Palencia
    "09": IconSpec("\U0001F32D", "morcilla"),                        # Burgos
    "42": IconSpec("\U0001F953", "torreznos"),                       # Soria
    "24": IconSpec("\U0001F969", "cecina"),                          # León
    # --- Islas ------------------------------------------------------------
    "07": IconSpec("\U0001F950", "ensaimadas"),                      # Illes Balears
    "35": IconSpec("\U0001F3D6", "playa todo el año"),               # Las Palmas
    "38": IconSpec("\U0001F34C", "plátanos"),                        # S.C. Tenerife
    # --- Ciudades autónomas -----------------------------------------------
    "51": IconSpec("⚓", "la frontera y el Estrecho"),           # Ceuta
    "52": IconSpec("\U0001F91D", "cuatro culturas"),                 # Melilla
}


def render_spain_provincias_cotidiano():
    fig = build_icon_map(ICONS, "España · el día a día de cada provincia")
    return draw.save(fig, "spain-provincias-cotidiano")
