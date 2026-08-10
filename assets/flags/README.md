# Bundled flags

National flags of the seven Central American countries, named by ISO 3166-1
alpha-2 code (`GT`, `BZ`, `SV`, `HN`, `NI`, `CR`, `PA`).

Downloaded at 640 px wide from https://flagcdn.com/ (public-domain images,
redrawn from Wikimedia Commons). Each file keeps its flag's official
proportions, which differ per country (Honduras 1:2, Panamá 2:3, Guatemala 8:5,
…), so `draw.flag()` scales by width and lets the height follow.

Refresh with `python scripts/download_data.py` (see `process_flags`). They are
committed because rendering must work offline.
