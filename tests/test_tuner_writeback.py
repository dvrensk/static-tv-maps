"""Round-trip tests for the tuner's source write-back.

Every test restores both the files and the in-memory tables it touches, so
the suite leaves the working tree exactly as it found it.
"""

import copy
from pathlib import Path

import pytest

from tvmaps.tuner import registry, writeback

MODULES = sorted({t.module for t in registry.TABLES.values()})


@pytest.fixture(autouse=True)
def restore_sources():
    paths = [Path(registry.table_module(t).__file__) for t in registry.TABLES]
    files = {p: p.read_text(encoding="utf-8") for p in paths}
    tables = {t: copy.deepcopy(registry.table_dict(t)) for t in registry.TABLES}
    yield
    for p, text in files.items():
        if p.read_text(encoding="utf-8") != text:
            p.write_text(text, encoding="utf-8")
    for t, snapshot in tables.items():
        d = registry.table_dict(t)
        d.clear()
        d.update(snapshot)


def edit(table, key, changed, **fields):
    entry = registry.table_dict(table).get(key)
    base = ({f: getattr(entry, f) for f in registry.editable_fields(table)}
            if entry is not None else
            {f: registry.field_defaults(table)[f]
             for f in registry.editable_fields(table)})
    base.update(fields)
    return {table: {key: {"fields": base, "changed": changed}}}


def source_of(table):
    return Path(registry.table_module(table).__file__).read_text(encoding="utf-8")


def test_unchanged_save_writes_nothing():
    """Saving current values back (every field marked changed) must not
    touch any file — for every entry of every table."""
    edits = {}
    for table in registry.TABLES:
        for key in registry.table_dict(table):
            e = edit(table, key, changed=registry.editable_fields(table))
            edits.setdefault(table, {}).update(e[table])
    before = {t: source_of(t) for t in registry.TABLES}
    result = writeback.apply_edits(edits)
    assert result == []
    for t in registry.TABLES:
        assert source_of(t) == before[t]


def test_edit_existing_entry_minimal_diff():
    result = writeback.apply_edits(edit("CCAA_LABELS", "06",
                                        changed=["ty"], ty=80))
    assert len(result) == 1
    diff = result[0]["diff"]
    removed = [l for l in diff.splitlines() if l.startswith("-") and not l.startswith("---")]
    added = [l for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++")]
    assert len(removed) == 1 and len(added) == 1
    assert 'Label(40, tx=-20, ty=80),' in added[0]
    assert "# Cantabria" in added[0], "trailing comment must survive"
    # In-memory table matches the file.
    assert registry.table_dict("CCAA_LABELS")["06"].ty == 80


def test_comment_column_is_preserved():
    before = source_of("CCAA_LABELS")
    line_before = next(l for l in before.splitlines() if '"06"' in l)
    writeback.apply_edits(edit("CCAA_LABELS", "06", changed=["ty"], ty=9))
    line_after = next(l for l in source_of("CCAA_LABELS").splitlines()
                      if '"06"' in l)
    assert line_before.index("#") == line_after.index("#")


def test_field_reset_to_default_removes_kwarg():
    writeback.apply_edits(edit("CCAA_LABELS", "08", changed=["dx"], dx=0))
    line = next(l for l in source_of("CCAA_LABELS").splitlines() if '"08"' in l)
    assert "Label(54)," in line and "dx" not in line


def test_callout_off_folds_into_offsets():
    writeback.apply_edits(edit("PROV_LABELS", "39",
                               changed=["tx", "ty", "dx", "dy"],
                               tx=None, ty=None, dx=-25, dy=65))
    line = next(l for l in source_of("PROV_LABELS").splitlines() if '"39"' in l)
    assert 'PLabel(30, group="B", dx=-25, dy=65),' in line
    assert "tx" not in line


def test_callout_on_appends_kwargs():
    writeback.apply_edits(edit("CCAA_LABELS", "03",
                               changed=["tx", "ty"], tx=10, ty=42.5))
    line = next(l for l in source_of("CCAA_LABELS").splitlines() if '"03"' in l)
    assert "Label(46, tx=10, ty=42.5)," in line


def test_size_edit_on_bare_call_inserts_positional():
    writeback.apply_edits(edit("CCAA_LABELS", "01", changed=["size"], size=48))
    line = next(l for l in source_of("CCAA_LABELS").splitlines() if '"01"' in l)
    assert "Label(48)," in line


def test_insert_auto_concejo_entry():
    assert "Tineo" not in registry.table_dict("CONCEJO_OVERRIDES")
    writeback.apply_edits(edit("CONCEJO_OVERRIDES", "Tineo",
                               changed=["size", "dx"], size=30, dx=4.5))
    src = source_of("CONCEJO_OVERRIDES")
    assert '    "Tineo": Label(30, dx=4.5),\n' in src
    assert registry.table_dict("CONCEJO_OVERRIDES")["Tineo"].dx == 4.5


def test_insert_auto_num_entry_gets_name_comment():
    assert "33" not in registry.table_dict("NUM_LABELS")
    writeback.apply_edits(edit("NUM_LABELS", "33", changed=["dy"],
                               size=46, dy=-10))
    src = source_of("NUM_LABELS")
    assert '    "33": Label(46, dy=-10),  # Asturias\n' in src


def test_cityspec_positional_args_stay_bound():
    """CIUDADES entries pass dx/dy positionally: CitySpec(0, 14). Editing dy
    must rewrite the second positional, never append a duplicate kwarg."""
    writeback.apply_edits(edit("CIUDADES", "Zaragoza", changed=["dy"], dy=16))
    line = next(l for l in source_of("CIUDADES").splitlines()
                if '"Zaragoza": CitySpec' in l)
    assert "CitySpec(0, 16)," in line
    spec = registry.table_dict("CIUDADES")["Zaragoza"]
    assert spec.dx == 0 and spec.dy == 16


def test_cityspec_size_appends_as_kwarg():
    """size is the LAST field of CitySpec, so it must never be positional."""
    writeback.apply_edits(edit("CIUDADES", "Zaragoza", changed=["size"],
                               size=34))
    line = next(l for l in source_of("CIUDADES").splitlines()
                if '"Zaragoza": CitySpec' in l)
    assert "CitySpec(0, 14, size=34)," in line


def test_group_flip():
    writeback.apply_edits(edit("PROV_LABELS", "33", changed=["group"],
                               group="B"))
    line = next(l for l in source_of("PROV_LABELS").splitlines() if '"33"' in l)
    assert 'PLabel(38, group="B"),' in line


def test_edited_module_still_parses_everywhere():
    writeback.apply_edits(edit("CCAA_LABELS", "06", changed=["ty"], ty=80))
    writeback.apply_edits(edit("CONCEJO_OVERRIDES", "Tineo",
                               changed=["size"], size=30))
    for table in ("CCAA_LABELS", "CONCEJO_OVERRIDES"):
        path = Path(registry.table_module(table).__file__)
        compile(path.read_text(encoding="utf-8"), str(path), "exec")


def test_unknown_table_rejected():
    with pytest.raises(ValueError):
        writeback.apply_edits({"NOPE": {"x": {"fields": {}, "changed": []}}})
