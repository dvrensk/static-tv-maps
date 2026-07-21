# Gijón — mapas esquemáticos de calles (design spec)

Three nested schematic street maps of Gijón for the TV slideshow:
"metro-map-adjacent but geographically true". Only ~10 structural streets as
bold coloured strokes with their names along them, a handful of landmark
pictograms, sea/beach/green shading. Everything else omitted. 4000×2250,
EPSG:25830, house style (small Spanish footer, halo text, no titles).

All coordinates below were verified against OSM (Nominatim + Overpass,
July 2026). Street "route" lines give the OSM way-name extents so the builder
can sanity-check drawn geometry. All labels ≥ 24 pt (33 px).

Proposed map keys: **`gijon-calles-centro`**, **`gijon-calles-medio`**,
**`gijon-calles-amplio`** (module `tvmaps/maps_gijon.py`, functions
`render_gijon_calles_centro` etc., added to the registry in `generate.py`).

---

## 1. Frames

### Arithmetic

Measured in EPSG:25830 at Gijón (lat 43.53, lon −5.65):

- 1° of longitude = **80 809 m** (cos-check: cos(43.53°)·111 320 ≈ 80 720 m ✓)
- 1° of latitude = **111 065 m**

So a 16:9 frame `H` degrees of latitude tall needs
`H · 111 065 · (16/9) / 80 809 ≈ H · 2.443` degrees of longitude.

**Important**: at lon −5.65 we are 2.65° from UTM 30N's central meridian, so
grid convergence is ≈ `sin(43.53°)·2.65° ≈ 1.8°`. A frame that is an
axis-aligned rectangle in projected metres (which is what `draw.new_map`
consumes) is therefore *tilted ~1.8° relative to the parallels*: its SE corner
sits ~0.0013–0.003° further north than its SW corner. The frames are given
below **primarily as EPSG:25830 boxes** (authoritative — feed these straight
to `draw.new_map`), with the lon/lat of all four corners for checking.
Consequence for the drawing: north is ~1.8° tilted clockwise on screen; the
coastline (which runs WSW–ENE anyway) still sits comfortably along the top.

All three frames share the same **north edge y = 4 825 745 m** (≈ 300–350 m of
sea above the tip of the Cerro de Santa Catalina, y = 4 825 395), so the maps
nest exactly: centro ⊂ medio ⊂ amplio, coast always at the top.

### Frame 1 — `gijon-calles-centro`

Southern limit: just past Avenida de Pablo Iglesias (y ≈ 4 823 970) and the
CMI de El Coto (y = 4 823 505), with ~300 m of margin below the CMI for its
icon+label.

| | EPSG:25830 |
|---|---|
| x | **283 076 … 287 593** (W = 4 517 m) |
| y | **4 823 205 … 4 825 745** (H = 2 540 m) |
| ratio | 4517 / 2540 = 1.7783 ≈ 16/9 ✓ |

Corner lon/lat: SW (−5.6845, 43.5303) · SE (−5.6287, 43.5316) ·
NE (−5.6297, 43.5544) · NW (−5.6855, 43.5531).

Contains (verified): Cerro de Santa Catalina + Elogio, harbour & Puerto
Deportivo, Acuario (−5.6770), Sanz Crespo (−5.6756), all of the beach, Avda.
de la Costa and Pablo Iglesias end to end, CMI El Coto (43.5338), El Molinón
(−5.6375, 43.5363) with margin. Calle Quevedo (43.5315) technically clips the
bottom edge but is *not drawn* on this map.

### Frame 2 — `gijon-calles-medio`

Southern limit: past Calle Quevedo (lat 43.5315, y ≈ 4 823 300), extended to
include the Parque de Los Pericones (centroid y = 4 822 470), which begins
directly south of Quevedo — this is the natural "Ceares/Contrueces direction"
stopping line.

| | EPSG:25830 |
|---|---|
| x | **282 020 … 288 465** (W = 6 445 m) |
| y | **4 822 120 … 4 825 745** (H = 3 625 m) |
| ratio | 6445 / 3625 = 1.7779 ≈ 16/9 ✓ |

Corner lon/lat: SW (−5.6971, 43.5202) · SE (−5.6175, 43.5221) ·
NE (−5.6189, 43.5547) · NW (−5.6986, 43.5528).

Adds over frame 1: Playa del Arbeyal (west edge), El Natahoyo, all of El
Llano and Ceares, Los Pericones, Los Fresnos, Somió west edge. Universidad
Laboral (−5.6167) stays *outside* by design (it forces the frame 3 size).

### Frame 3 — `gijon-calles-amplio`

West limit: the GJ-10/AS-19 corridor through Tremañes (trunk bend at
x = 279 832) with margin. East limit: Hospital de Cabueñes (x = 289 200) with
margin. Width then dictates depth: the south edge lands at y = 4 819 997
(lat ≈ 43.503), which duly covers Roces (43.5174), Montevil, Contrueces,
Nuevo Gijón and the AS-II exit.

| | EPSG:25830 |
|---|---|
| x | **279 482 … 289 700** (W = 10 218 m) |
| y | **4 819 997 … 4 825 745** (H = 5 748 m) |
| ratio | 10218 / 5748 = 1.7777 ≈ 16/9 ✓ |

Corner lon/lat: SW (−5.7276, 43.5004) · SE (−5.6014, 43.5033) ·
NE (−5.6036, 43.5550) · NW (−5.7300, 43.5521).

Contains everything in frame 2 plus: La Calzada, Tremañes + GJ-10/AS-19,
Puente Seco (≈ 43.537, −5.716), Avda. Príncipe de Asturias, Nuevo Gijón,
Perchera, Pumarín, Montevil, Roces, Rotonda de Roces/AS-II, Contrueces,
Universidad Laboral, Jardín Botánico, Hospital de Cabueñes, Somió.

Builder note: pass these boxes directly as `frame=(x0, y0, x1, y1)`; do not
run them through `geo.compute_frame` padding (they are already exact 16:9
within 0.05 %, and `compute_frame` would re-pad).

---

## 2. Streets

### AS-19 reality check (important)

Within today's signage/OSM, the road tagged `ref=AS-19` ("Carretera de
L'Empalme a Avilés") only begins **west of Veriña** (lon < −5.733, outside
even frame 3). Its continuation into Gijón — the corridor the user means by
"AS-19 (Tremañes/Puente Seco)" — is the trunk road tagged **GJ-10,
"Carretera Xixón-Avilés" / "Ronda de Tremañes"** (lat 43.525–43.544,
lon −5.7252…−5.6964), passing Puente Seco at ≈ (−5.716, 43.537). Draw the
GJ-10 and label it **"AS-19 · a Avilés"** (the pedagogically useful name),
with a builder comment noting the in-city ref is GJ-10.

### Palette

Near-white ground `#f7f4ee`. Transit-line strokes, all checked for
distinctness against their spatial neighbours (parallel trio
Constitución/Schulz/El Llano gets purple/raspberry/indigo; the two
"carreteras" AS-19 and AS-II share one road-grey so they read as a class).
Street name labels are set in a darkened variant of the stroke colour
(multiply ~0.75) with the standard white halo, rotated along the stroke.

| # | Street (OSM name) | Colour | Hex | Stroke |
|---|---|---|---|---|
| 1 | Paseo del Muro de San Lorenzo | rojo coral | `#e03131` | 22 px |
| 2 | Avenida de la Costa | azul | `#1971c2` | 22 px |
| 3 | Avenida de Pablo Iglesias | verde | `#2f9e44` | 22 px |
| 4 | Avenida de Manuel Llaneza | naranja | `#f08c00` | 20 px |
| 5 | Avenida de la Constitución | morado | `#9c36b5` | 22 px |
| 6 | Calle Corrida | turquesa | `#0c8599` | 16 px |
| 7 | Calle de Los Moros | rosa | `#f06595` | 16 px |
| 8 | Calle Ramón y Cajal | marrón | `#a05a2c` | 18 px |
| 9 | Avenida de Castilla | gris pizarra | `#495057` | 16 px |
| 10 | Avenida de Schulz | frambuesa | `#c2255c` | 20 px |
| 11 | Avenida de El Llano | índigo | `#4263eb` | 22 px |
| 12 | Calle Quevedo | cian | `#15aabf` | 18 px |
| 13 | Avenida de Portugal | lima | `#74b816` | 18 px |
| 14 | AS-19 (GJ-10 Ctra. Xixón-Avilés) | gris carretera | `#343a40` | 26 px |
| 15 | Avenida Príncipe de Asturias | azul acero | `#3b7ea1` | 22 px |
| 16 | Avenida de Galicia | esmeralda | `#0ca678` | 18 px |
| 17 | Carretera del Obispo | marrón oscuro | `#7d4a1e` | 18 px |
| 18 | AS-II (Avenida de Oviedo) | gris carretera | `#343a40` | 26 px |
| 19 | Avda. de Albert Einstein (+ Avda. de la Pecuaria) | violeta | `#7048e8` | 18 px |

Cautions from adjacency: #13 lima vs #3 verde are both green — they never run
parallel (Portugal is W of El Humedal, Pablo Iglesias E of Plaza de Europa)
but re-check at full render; #7 rosa vs #10 frambuesa are 1 km apart and
never co-visible closely.

### Routes (sanity-check lines, from verified OSM extents)

1. **Paseo del Muro de San Lorenzo** — the beach promenade arc, from the
   Iglesia de San Pedro headland (−5.6605, 43.5458) SE along the sand to the
   Piles mouth (−5.6425, 43.5402). OSM splits the seafront: the southern half
   is officially *Avenida de Rufo García Rendueles* (−5.6610…−5.6448); draw
   as ONE stroke, label "Muro de San Lorenzo" (what everyone calls it).
2. **Avenida de la Costa** — E–W spine: from Plaza del Humedal
   (−5.6663, 43.5387) east to the Piles / Avda. de Castilla junction
   (−5.6460, 43.5350).
3. **Avenida de Pablo Iglesias** — E–W, one block south of la Costa: from
   Plaza de Europa (−5.6594, 43.5356) east to the Piles / Parque Isabel la
   Católica (−5.6460, 43.5352). Tagged N-632.
4. **Avenida de Manuel Llaneza** — from the Avda. de la Constitución junction
   (−5.6691, 43.5341) NE to Plaza de Europa (−5.6594, 43.5366). The N-632
   through-line is thus Constitución→Llaneza→Pablo Iglesias; Plaza de Europa
   is a 3-line hub (4 meets 3 meets 11).
5. **Avenida de la Constitución** — the big N–S(-SW) artery: from Plaza del
   Humedal (−5.6647, 43.5380) SW to the Rotonda de Roces / Avda. de Oviedo
   junction (−5.6809, 43.5241).
6. **Calle Corrida** — pedestrian shopping spine, N–S: from Plaza del Marqués
   below Cimavilla (−5.6640, 43.5438) south to Plaza del Seis de Agosto
   (−5.6643, 43.5398).
7. **Calle de Los Moros** — N–S, one short block EAST of Corrida (verified in
   OSM geometry — it does *not* run E–W): from ≈ (−5.6634, 43.5422) south to
   Plaza del Seis de Agosto (−5.6631, 43.5398).
8. **Calle Ramón y Cajal** — N–S axis of El Coto: from Avenida de la Costa
   (−5.6530, 43.5374) south past Plaza de la República/CMI to Calle Quevedo
   (−5.6548, 43.5306).
9. **Avenida de Castilla** — short N–S east link: from the Piles / end of the
   Muro (−5.6450, 43.5399) south past the Plaza de Toros de El Bibio to the
   Costa/Pablo Iglesias convergence (−5.6479, 43.5361).
10. **Avenida de Schulz** — dead-straight N–S: from Plaza del Humedal
    (−5.6648, 43.5379) south to Carretera del Obispo at La Braña/Perchera
    (−5.6677, 43.5246).
11. **Avenida de El Llano** — N–S axis of El Llano: from Plaza de Europa
    (−5.6585, 43.5366) SSW to Contrueces / Carretera del Obispo
    (−5.6637, 43.5199).
12. **Calle Quevedo** — E–W: from Ceares (−5.6559, 43.5317) east along the
    south side of El Coto to Viesques (−5.6450, 43.5315).
13. **Avenida de Portugal** — from Plaza del Humedal (−5.6670, 43.5397) W/SW
    past the Museo del Ferrocarril toward Moreda/El Natahoyo
    (−5.6805, 43.5334). (Partly pedestrianised; still the westward axis.)
14. **AS-19 corridor (GJ-10)** — trunk: from the AS-II/A-8 junction at
    Lloreda (−5.6964, 43.5250) NW through Tremañes past Puente Seco to Veriña
    (−5.7252, 43.5441), where the signed AS-19 continues to Avilés. Label
    "AS-19 · a Avilés".
15. **Avenida Príncipe de Asturias** — trunk N-641: from Moreda/Cuatro
    Caminos (−5.6824, 43.5331) NNW to the El Musel port access
    (−5.6962, 43.5434). Label may add "· a El Musel".
16. **Avenida de Galicia** — E–W: from El Natahoyo (−5.6844, 43.5400) west
    into La Calzada (−5.6930, 43.5400).
17. **Carretera del Obispo** — the old southern road: from Contrueces / south
    end of Avda. de El Llano (−5.6628, 43.5246) SW to Roces
    (−5.6844, 43.5140).
18. **AS-II (Avenida de Oviedo)** — from the Rotonda de Roces
    (−5.6853, 43.5197) south to the frame edge. Label "AS-II · a Oviedo".
19. **Avenida de Albert Einstein → Avenida de la Pecuaria** — the eastern
    road to la Laboral: from the Glorieta de Corín Tellado in Viesques
    (−5.6408, 43.5285) east via Einstein (−5.6406…−5.6284) and Pecuaria
    (−5.6284…−5.6107) to the Rotonda del Piqueru at the Universidad Laboral
    (−5.6105, 43.5264). One stroke, one label ("Avda. de Albert Einstein").

### Streets per map

**Mapa 1 — centro** (9 labelled + 2 unlabelled context stubs):

| Street | Label position (lon, lat) | Rotation | Size |
|---|---|---|---|
| Muro de San Lorenzo | −5.6515, 43.5442 (over the sand, mid-arc) | ≈ −20° following the arc | 40 pt |
| Avenida de la Costa | −5.6560, 43.5372 (just N of the stroke) | ≈ −12° | 36 pt |
| Avenida de Pablo Iglesias | −5.6530, 43.5346 (just S of the stroke) | ≈ −3° | 36 pt |
| Avenida de Manuel Llaneza | −5.6643, 43.5350 (S side) | ≈ +25° | 28 pt |
| Avenida de la Constitución | −5.6710, 43.5340 (W side, along) | ≈ +55° (steep NE–SW) | 32 pt |
| Calle Corrida | −5.6655, 43.5418 (W side, vertical along street) | 90° (reads upward) | 28 pt |
| Calle de Los Moros | −5.6620, 43.5410 (E side, vertical) | 90° | 26 pt |
| Calle Ramón y Cajal | −5.6555, 43.5340 (W side, vertical) | ≈ 80° | 28 pt |
| Avenida de Castilla | −5.6468, 43.5382 (E side, vertical) | ≈ 75° | 26 pt |
| *(unlabelled stubs)* | Avda. de Schulz and Avda. de El Llano drawn to the S frame edge in their colours, no label (picked up in mapa 2) | | |

**Mapa 2 — medio** (12 labelled):

Keep all mapa-1 strokes. Los Moros and Castilla stay drawn but *lose their
labels* (too small at this scale); everything shifts/re-sizes:

| Street | Label position (lon, lat) | Rotation | Size |
|---|---|---|---|
| Muro de San Lorenzo | −5.6515, 43.5445 | ≈ −20° | 36 pt |
| Avenida de la Costa | −5.6570, 43.5374 | ≈ −12° | 32 pt |
| Avenida de Pablo Iglesias | −5.6520, 43.5344 | ≈ −3° | 32 pt |
| Avenida de Manuel Llaneza | −5.6645, 43.5348 | ≈ +25° | 26 pt |
| Avenida de la Constitución | −5.6740, 43.5310 (mid-run) | ≈ +55° | 30 pt |
| Calle Corrida | −5.6657, 43.5418 | 90° | 24 pt |
| Calle Ramón y Cajal | −5.6552, 43.5335 | ≈ 80° | 26 pt |
| Avenida de Schulz | −5.6672, 43.5300 (W side, mid-run) | ≈ 85° | 30 pt |
| Avenida de El Llano | −5.6600, 43.5290 (E side, mid-run) | ≈ 70° | 30 pt |
| Calle Quevedo | −5.6500, 43.5308 (S side) | ≈ −2° | 28 pt |
| Avenida de Portugal | −5.6740, 43.5368 (N side) | ≈ −25° | 26 pt |
| *(context)* | Piles ribbon; Avda. de Galicia + Príncipe de Asturias stubs may clip the W edge unlabelled | | |

**Mapa 3 — amplio** (12 labelled):

Corrida, Los Moros, Manuel Llaneza, Ramón y Cajal, Castilla, Portugal stay
drawn (they keep the coloured skeleton recognisable across the series) but
unlabelled.

| Street | Label position (lon, lat) | Rotation | Size |
|---|---|---|---|
| Muro de San Lorenzo | −5.6515, 43.5448 | ≈ −20° | 32 pt |
| Avenida de la Costa | −5.6580, 43.5376 | ≈ −12° | 28 pt |
| Avenida de Pablo Iglesias | −5.6510, 43.5342 | ≈ −3° | 28 pt |
| Avenida de la Constitución | −5.6752, 43.5300 | ≈ +55° | 28 pt |
| Avenida de Schulz | −5.6675, 43.5290 | ≈ 85° | 26 pt |
| Avenida de El Llano | −5.6598, 43.5285 | ≈ 70° | 26 pt |
| Calle Quevedo | −5.6495, 43.5306 | ≈ −2° | 24 pt |
| Carretera del Obispo | −5.6730, 43.5188 (S side, mid-run) | ≈ −25° | 26 pt |
| AS-19 · a Avilés | −5.7180, 43.5390 (NE side of the GJ-10, near Puente Seco) | ≈ +40° | 30 pt |
| Avenida Príncipe de Asturias | −5.6935, 43.5395 (W side) | ≈ 70° | 26 pt |
| Avenida de Galicia | −5.6890, 43.5407 (N side) | ≈ 0° | 26 pt |
| Avda. de Albert Einstein | −5.6340, 43.5270 (S side) | ≈ −5° | 26 pt |
| AS-II · a Oviedo | −5.6880, 43.5140 (W side) | ≈ 80° | 30 pt |

(That is 13 with AS-II; the two road-shield-style "a Avilés / a Oviedo"
labels read as exits, not street names, so the named-street count stays 11.)

---

## 3. Landmarks

Symbols: Noto Emoji **Bold** (already bundled, `assets/fonts/NotoEmoji-Bold.ttf`;
all codepoints below verified present in its cmap), drawn like
`maps_iconos.py` does (icon above / beside a 26–30 pt name). One `draw.city_star`
is reserved for the Elogio del Horizonte — the symbol of the city. Icon sizes:
mapa 1 ≈ 54 pt, mapa 2 ≈ 48 pt, mapa 3 ≈ 44 pt.

Coordinates verified via Nominatim/Overpass (to 3–4 decimals).

**Mapa 1 — centro (8):**

| Landmark (label text) | Symbol | lon, lat | Notes |
|---|---|---|---|
| Elogio del Horizonte | ★ (`draw.city_star`, gold) | −5.663, 43.549 | on the Cerro green patch; name below |
| Ayuntamiento | 🏛 U+1F3DB | −5.662, 43.545 | Plaza Mayor; label E toward the sea gap |
| Iglesia de San Pedro | ⛪ U+26EA | −5.661, 43.546 | beach W end; Termas Romanas (♨ U+2668, −5.661, 43.545) optional if it fits — else fold into a two-line label "San Pedro y Termas" |
| Puerto Deportivo | ⚓ U+2693 | −5.668, 43.546 | icon in the water basin |
| Acuario | 🐟 U+1F41F | −5.677, 43.542 | Poniente W tip |
| Teatro Jovellanos | 🎭 U+1F3AD | −5.661, 43.539 | Paseo de Begoña |
| El Molinón | ⚽ U+26BD | −5.637, 43.536 | E edge; label pointing W |
| CMI de El Coto | 📚 U+1F4DA | −5.649, 43.534 | Plaza de la República; defines the S edge |

**Mapa 2 — medio (8):** Elogio ★, Ayuntamiento 🏛, Puerto Deportivo ⚓ and
El Molinón ⚽, CMI de El Coto 📚 carry over (same coords, smaller), plus:

| Landmark | Symbol | lon, lat |
|---|---|---|
| Museo del Ferrocarril | 🚂 U+1F682 | −5.674, 43.541 |
| Estación Sanz Crespo | 🚆 U+1F686 | −5.676, 43.538 |
| C.C. Los Fresnos | 🛍 U+1F6CD | −5.662, 43.533 |

(Acuario, Teatro and San Pedro drop out to keep the centro readable at the
smaller scale; Los Pericones appears as a *named green patch*, §4.)

**Mapa 3 — amplio (8):** Elogio ★, Ayuntamiento 🏛, El Molinón ⚽ and
Estación Sanz Crespo 🚆 carry over, plus:

| Landmark | Symbol | lon, lat |
|---|---|---|
| Universidad Laboral | 🗼 U+1F5FC | −5.617, 43.525 | (its tower is Spain's tallest building in stone; alternatively 🎓 U+1F393) |
| Jardín Botánico Atlántico | 🌿 U+1F33F | −5.622, 43.520 |
| Hospital de Cabueñes | 🏥 U+1F3E5 | −5.608, 43.525 |
| Acuario | 🐟 U+1F41F | −5.677, 43.542 |

---

## 4. Water / green / sand

- **Sea**: `style.OCEAN` everywhere north of the coastline, including the
  harbour basins (Puerto Deportivo, El Musel corner on mapa 3). Coastline
  from OSM `natural=coastline`, simplified hard (~20 m) — schematic, not
  fractal. Label **MAR CANTÁBRICO** (house sea style `#7da7bf`, semibold,
  48/52/56 pt) centred in the sea: mapa 1 (−5.650, 43.552); mapa 2
  (−5.648, 43.552); mapa 3 (−5.660, 43.550).
- **Beaches** (sand `#f2dfae`, label colour `#b5924c`, 26–28 pt):
  - *Playa de San Lorenzo* — the arc between the Muro stroke and the sea,
    from San Pedro (−5.6605, 43.5458) to the Piles mouth (−5.6425, 43.5402).
    Label on the sand at (−5.648, 43.5425), all maps.
  - *Playa de Poniente* — pocket beach at (−5.676, 43.5434), all maps
    (labelled maps 1–2, unlabelled map 3).
  - *Playa del Arbeyal* — (−5.694, 43.5448), maps 2–3, labelled on map 3 only.
- **Río Piles**: a 30-px ribbon of `style.OCEAN` from the mouth
  (−5.6425, 43.5400) south past El Molinón and Las Mestas (−5.6405, 43.5325)
  to the frame edge; on map 3 continue to ≈ (−5.640, 43.515). Small label
  "río Piles" (24 pt, sea-label colour, rotated ~80°) at (−5.6408, 43.5330)
  on maps 2–3.
- **Parks** (soft green `#cde8c4`, no outline; names only where noted, park
  label colour `#6f9a5d`, 26 pt):
  - *Cerro de Santa Catalina* — headland green cap around (−5.663, 43.550),
    all maps (unnamed; the Elogio star sits on it).
  - *Parque de Isabel la Católica* — blob centred (−5.643, 43.538) between
    the Piles and Pablo Iglesias, all maps, named on maps 1–2.
  - *Parque de Begoña* — small patch (−5.660, 43.539) under the Teatro icon,
    map 1 only, unnamed.
  - *Parque de Los Pericones* — big blob centred (−5.657, 43.5245), maps
    2–3, named ("Los Pericones").
  - *Jardín Botánico* — patch at (−5.6216, 43.520) under its 🌿 icon, map 3.
  - *Parque de Moreda* — patch at (−5.684, 43.5375), map 3 only, unnamed.

---

## 5. Map keys and captions

House style: `draw.draw_footer` caption lower-right + `draw.draw_attribution`
below it. ALL text Spanish.

| Key | Footer caption | Attribution |
|---|---|---|
| `gijon-calles-centro` | `Gijón · calles principales del centro` | `Datos: © OpenStreetMap` |
| `gijon-calles-medio` | `Gijón · calles principales, del mar a Ceares` | `Datos: © OpenStreetMap` |
| `gijon-calles-amplio` | `Gijón · calles principales, del mar a Roces y Tremañes` | `Datos: © OpenStreetMap` |

The lower-right corner is land on all three maps (El Coto / Viesques /
countryside), so give the footer its usual halo; no repositioning needed.

---

## 6. Barrios (faint background garnish, maps 2–3)

Very faint, large, all-caps names in the style of the sea labels (colour
`#c9c2b4`, ~46 pt map 2 / ~44 pt map 3, semibold, zorder under the streets).
Node coordinates from OSM `place=suburb`:

**Mapa 2 (6):**

| Barrio | lon, lat (nudge to dodge strokes) |
|---|---|
| CIMAVILLA | −5.6631, 43.5471 |
| EL NATAHOYO | −5.6830, 43.5392 |
| EL LLANO | −5.6625, 43.5285 |
| EL COTO | −5.6503, 43.5336 |
| CEARES | −5.6553, 43.5304 |
| SOMIÓ | −5.6219, 43.5361 |

**Mapa 3 (6):**

| Barrio | lon, lat |
|---|---|
| LA CALZADA | −5.6976, 43.5403 |
| EL NATAHOYO | −5.6830, 43.5392 |
| EL LLANO | −5.6625, 43.5285 |
| SOMIÓ | −5.6219, 43.5361 |
| PUMARÍN | −5.6732, 43.5258 |
| ROCES | −5.6812, 43.5174 |

(Also verified if ever needed: Tremañes −5.6948, 43.5267 · Montevil −5.6762,
43.5214 · Contrueces −5.6642, 43.5197 · Nuevo Gijón −5.6825, 43.5255 ·
Perchera-La Braña −5.6819, 43.5311 · Moreda −5.6835, 43.5365 · Laviada
−5.6705, 43.5362 · Viesques −5.6457, 43.5283 · El Coto −5.6503, 43.5336 ·
Ceares −5.6553, 43.5304 · Cimavilla −5.6631, 43.5471.)

---

## 7. Builder notes

- **Data**: extend `scripts/download_data.py` with an Overpass fetch of the
  named ways above (`name=` exact matches inside the municipality area,
  plus `ref=GJ-10` and the AS-II stretch) → merge each street's ways into a
  single LineString, simplify to ~15 m, write
  `data/processed/gijon_streets.geojson` with a `key` property per street.
  Coastline: `natural=coastline` ways in bbox (43.49, −5.75, 43.57, −5.58);
  beaches: `natural=beach`; parks: the six polygons by name; the Piles:
  `waterway=river` `name~"Piles"`. Landmarks/barrios are few enough to
  hardcode in `tvmaps/maps_gijon.py` (like `NEIGHBOR_LABELS`).
- **Rendering order**: ground → parks/sand/sea/Piles → barrio ghost names →
  street casings (optional 4 px white under each stroke, helps crossings) →
  streets (carreteras first, then avenues, then calles so the fine pedestrian
  pair sits on top) → street names → landmark icons+names → footer.
- Round stroke caps/joins (`solid_capstyle="round"`); where two strokes meet
  at a named plaza (Humedal, Plaza de Europa, Seis de Agosto) just let them
  touch — no junction symbols. Optionally a small white dot with dark ring
  (à la `city_dot`) at El Humedal and Plaza de Europa on maps 1–2, unnamed.
- Street-name rotation: compute from the local stroke direction in projected
  coords rather than trusting the table's approximations; the table's
  positions are the anchor points to use.
- Everything stays ≥ 24 pt; if a collision appears at render time, prefer
  dropping a *label* (never a stroke) — the strokes are the skeleton shared
  across the three maps, which is what makes the nesting legible.
- These are not political maps: no theme variants, single palette, and the
  keys do NOT join `POLITICAL_MAPS`.
