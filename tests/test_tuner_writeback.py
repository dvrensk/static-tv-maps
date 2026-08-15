"""Round-trip tests for the tuner's source write-back.

Every test restores both the files and the in-memory tables it touches, so
the suite leaves the working tree exactly as it found it.
"""

import copy
from dataclasses import MISSING
from pathlib import Path

import pytest

from tvmaps.tuner import registry, writeback


@pytest.fixture(autouse=True)
def restore_sources():
    paths = {Path(registry.table_module(t).__file__) for t in registry.TABLES}
    files = {p: p.read_text(encoding="utf-8") for p in paths}
    snapshots = {t: copy.deepcopy(registry.table_source(t))
                 for t in registry.TABLES}
    yield
    for p, text in files.items():
        if p.read_text(encoding="utf-8") != text:
            p.write_text(text, encoding="utf-8")
    for t, snapshot in snapshots.items():
        tab = registry.TABLES[t]
        setattr(registry.table_module(t), tab.source_var, snapshot)


def edit(table, key, changed, **fields):
    entry = registry.entries(table).get(key)
    defaults = registry.field_defaults(table)
    base = {}
    for f in registry.editable_fields(table):
        if entry is not None:
            base[f] = getattr(entry, f)
        else:
            base[f] = None if defaults[f] is MISSING else defaults[f]
    base.update(fields)
    return {table: {key: {"fields": base, "changed": changed}}}


def source_of(table):
    return Path(registry.table_module(table).__file__).read_text(encoding="utf-8")


def test_unchanged_save_writes_nothing():
    """Saving current values back (every field marked changed) must not
    touch any file — for every entry of every table, all containers."""
    edits = {}
    for table in registry.TABLES:
        for key in registry.entries(table):
            e = edit(table, key, changed=registry.editable_fields(table))
            edits.setdefault(table, {}).update(e[table])
    before = {t: source_of(t) for t in registry.TABLES}
    result = writeback.apply_edits(edits)
    assert result == []
    for t in registry.TABLES:
        assert source_of(t) == before[t]


def test_edit_existing_entry_minimal_diff():
    # ty=80 differs from whatever the table currently holds (tuned values
    # change over time, so assert shape, not exact literals).
    assert registry.entries("CCAA_LABELS")["06"].ty != 80
    result = writeback.apply_edits(edit("CCAA_LABELS", "06",
                                        changed=["ty"], ty=80))
    assert len(result) == 1
    diff = result[0]["diff"]
    removed = [l for l in diff.splitlines() if l.startswith("-") and not l.startswith("---")]
    added = [l for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++")]
    assert len(removed) == 1 and len(added) == 1
    assert "ty=80" in added[0]
    assert "# Cantabria" in added[0], "trailing comment must survive"
    # In-memory table matches the file.
    assert registry.entries("CCAA_LABELS")["06"].ty == 80


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
    # Pick an entry whose size is still the dataclass default (written
    # without a positional size); the edit must insert one at the front.
    key = next(k for k, sp in registry.entries("CCAA_LABELS").items()
               if sp.size == 54)
    writeback.apply_edits(edit("CCAA_LABELS", key, changed=["size"], size=48))
    line = next(l for l in source_of("CCAA_LABELS").splitlines()
                if f'"{key}"' in l)
    assert "Label(48" in line


def test_insert_auto_concejo_entry():
    assert "Tineo" not in registry.entries("CONCEJO_OVERRIDES")
    writeback.apply_edits(edit("CONCEJO_OVERRIDES", "Tineo",
                               changed=["size", "dx"], size=30, dx=4.5))
    src = source_of("CONCEJO_OVERRIDES")
    assert '    "Tineo": Label(30, dx=4.5),\n' in src
    assert registry.entries("CONCEJO_OVERRIDES")["Tineo"].dx == 4.5


def test_insert_auto_num_entry_gets_name_comment():
    assert "33" not in registry.entries("NUM_LABELS")
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
    spec = registry.entries("CIUDADES")["Zaragoza"]
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


# --- absolute idiom (lon/lat + rotation) -----------------------------------

def test_river_rotation_and_position_edit():
    """RiverSpec passes lon/lat/rotation positionally; all three rewrite in
    place and required lon/lat are never dropped."""
    writeback.apply_edits(edit("RIOS_LABELS", "Duero",
                               changed=["lon", "lat", "rotation"],
                               lon=-4.1234, lat=41.5, rotation=-12.5))
    line = next(l for l in source_of("RIOS_LABELS").splitlines()
                if '"Duero"' in l)
    assert "RiverSpec(-4.1234, 41.5, -12.5)," in line
    assert registry.entries("RIOS_LABELS")["Duero"].rotation == -12.5


def test_range_list_entry_matched_by_text():
    """RANGE_LABELS_RIOS is a list; entries are matched by their text arg."""
    writeback.apply_edits(edit("RANGE_LABELS_RIOS", "PIRINEOS",
                               changed=["rotation"], rotation=7))
    line = next(l for l in source_of("RANGE_LABELS_RIOS").splitlines()
                if '"PIRINEOS"' in l)
    assert 'RangeSpec("PIRINEOS", 0.55, 42.63, 7, 32),' in line


def test_hand_river_spec_inside_tuple():
    """HAND_RIVERS nests its spec in a (course, RiverSpec) tuple."""
    writeback.apply_edits(edit("HAND_RIVERS", "Nervión",
                               changed=["rotation"], rotation=-55))
    src = source_of("HAND_RIVERS")
    assert "RiverSpec(-3.27, 43.05, -55, 26))," in src
    assert registry.entries("HAND_RIVERS")["Nervión"].rotation == -55


def test_single_spec_assignment():
    """CANARY_FIRM is a bare single-spec assignment."""
    writeback.apply_edits(edit("CANARY_FIRM", "CANARY_FIRM",
                               changed=["tx"], tx=25))
    assert "tx=25" in source_of("CANARY_FIRM")
    assert registry.entries("CANARY_FIRM")["CANARY_FIRM"].tx == 25


def test_hub_list_entry_matched_by_city():
    writeback.apply_edits(edit("HUBS", "Bilbao", changed=["tx"], tx=99))
    assert registry.entries("HUBS")["Bilbao"].tx == 99
    assert "tx=99" in source_of("HUBS")


def test_no_insert_into_list_tables():
    with pytest.raises(ValueError):
        writeback.apply_edits(edit("HUBS", "Nowhere", changed=["tx"], tx=1))


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
