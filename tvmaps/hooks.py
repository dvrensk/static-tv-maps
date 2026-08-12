"""Seams the label tuner uses to look inside a render.

The maps route every tunable label spec through spec_for(), which is a
no-op during normal generate.py runs: SUPPRESS is False and OVERRIDES is
empty, so the spec comes back unchanged. The tuner server flips these
globals to render base maps without labels, to preview edited values
without touching the source files, and to learn each label's anchor point.
"""

from dataclasses import asdict, replace

# When True, tunable labels are skipped entirely (base-map renders for the
# tuner). Footers, legends, city dots and other fixed ink are unaffected.
SUPPRESS = False

# {table_id: {key: {field: value}}} merged over the source specs at render
# time. table_id is the module-level dict variable name (e.g. "PROV_LABELS").
OVERRIDES: dict = {}

# When a list, every tunable label appends a record with its anchor point in
# data coordinates and its effective spec as it renders (or would render).
CAPTURE: list | None = None


def spec_for(table_id, key, spec):
    """The spec to render: the source spec with any live overrides merged."""
    ov = OVERRIDES.get(table_id, {}).get(key) if table_id else None
    return replace(spec, **ov) if ov else spec


def capture(table_id, key, text, xy, spec=None, **extra):
    if CAPTURE is not None and table_id:
        CAPTURE.append(dict(
            table=table_id, key=key, text=text,
            anchor=(float(xy[0]), float(xy[1])),
            fields=asdict(spec) if spec is not None else None,
            extra=extra,
        ))
