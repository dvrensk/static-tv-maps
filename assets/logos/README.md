# Brand logos for `spain-marcas-logos`

This folder holds the company logo image files used by the
**spain-marcas-logos** map (`tvmaps/maps_marcas_logos.py`).

## What to do

Drop a logo image here named `<slug>.png` (a transparent-background PNG is
strongly preferred; `.jpg`/`.jpeg` also work). The map picks it up
automatically on the next render and draws it on a small white rounded card at
the brand's origin city.

- If a file is **present**, that brand shows its **logo**.
- If a file is **absent**, that brand shows a **coloured name chip** (the
  brand name in the company's primary colour). This is the default: a fresh
  checkout ships with **no** logo files, so the map renders all chips.

You can add logos for only some brands — each is independent.

## Important: these files are NOT committed

Company logos are copyrighted / trademarked artwork. This whole folder
(except this README) is **gitignored** — see the `assets/logos/` line in the
repository `.gitignore`. Nothing you drop here will be committed or
redistributed. Keep your own local copies.

## Sizing tips

Logos are scaled to a consistent on-canvas height (~46 px) and centred on the
white card, so only the aspect ratio matters. A logo roughly 300–600 px wide
with a transparent background gives the crispest result. Very wide wordmarks
still work but make a wide card.

## Exact filenames the code looks for

The slug is the brand name lowercased, with accents stripped and every run of
non-alphanumeric characters turned into a single hyphen (see `brand_slug()` in
`tvmaps/maps_marcas_logos.py`). The 40 brands and their expected files:

| File (`.png` or `.jpg`) | Brand | Origin city |
| --- | --- | --- |
| `inditex-zara.png` | Inditex · Zara | A Coruña · Arteixo |
| `estrella-galicia.png` | Estrella Galicia | A Coruña · Arteixo |
| `pescanova.png` | Pescanova | Redondela · Vigo |
| `central-lechera-asturiana.png` | Central Lechera Asturiana | Siero |
| `banco-santander.png` | Banco Santander | Santander |
| `bbva.png` | BBVA | Bilbao |
| `iberdrola.png` | Iberdrola | Bilbao |
| `corporacion-mondragon.png` | Corporación Mondragón | Arrasate · Mondragón |
| `fagor.png` | Fagor | Arrasate · Mondragón |
| `grupo-antolin.png` | Grupo Antolín | Burgos |
| `campofrio.png` | Campofrío | Burgos |
| `pikolin.png` | Pikolin | Zaragoza |
| `tous.png` | Tous | Manresa |
| `banco-sabadell.png` | Banco Sabadell | Sabadell |
| `mango.png` | Mango | Palau-solità |
| `estrella-damm.png` | Estrella Damm | Barcelona |
| `puig.png` | Puig | Barcelona |
| `cola-cao.png` | Cola Cao | Barcelona |
| `gallina-blanca.png` | Gallina Blanca | Barcelona |
| `chupa-chups.png` | Chupa Chups | Barcelona |
| `seat.png` | SEAT | Martorell |
| `freixenet.png` | Freixenet | Sant Sadurní |
| `codorniu.png` | Codorníu | Sant Sadurní |
| `roca.png` | Roca | Gavà |
| `porcelanosa.png` | Porcelanosa | Vila-real |
| `mercadona.png` | Mercadona | Valencia |
| `lladro.png` | Lladró | Valencia |
| `garcia-carrion.png` | García Carrión | Jumilla |
| `don-simon.png` | Don Simón | Jumilla |
| `elpozo.png` | ElPozo | Alhama de Murcia |
| `gonzalez-byass.png` | González Byass | Jerez de la Frontera |
| `tio-pepe.png` | Tío Pepe | Jerez de la Frontera |
| `osborne.png` | Osborne | El Puerto de Santa María |
| `camper.png` | Camper | Inca |
| `melia.png` | Meliá | Palma |
| `el-corte-ingles.png` | El Corte Inglés | Madrid |
| `repsol.png` | Repsol | Madrid |
| `telefonica.png` | Telefónica | Madrid |
| `iberia.png` | Iberia | Madrid |
| `mahou.png` | Mahou | Madrid |
</content>
