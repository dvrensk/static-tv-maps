"""Write tuned label values back into the map modules.

Existing entries are edited through libcst, which round-trips the file
losslessly: only the arguments that actually changed are touched, so the
hand-written comments and layout survive. Entries that only exist as
auto-generated specs (concejos without an override, provinces without a
NUM_LABELS tweak) are appended to their table as a new formatted line.
After a successful write the in-memory table is updated to match, so the
long-lived tuner process keeps rendering the saved state.

Edits arrive as {table_id: {key: {"fields": {...}, "changed": [...]}}} where
`fields` holds the complete final values and `changed` names the fields the
user actually touched (only those are rewritten on existing entries).
"""

import difflib
from dataclasses import fields as dc_fields, replace
from pathlib import Path

import libcst as cst

from . import registry


def _fmt_value(v) -> str:
    if v is None:
        return "None"
    if isinstance(v, bool):
        return "True" if v else "False"
    if isinstance(v, str):
        return '"' + v.replace('"', '\\"') + '"'
    f = float(v)
    return str(int(f)) if f == int(f) else f"{f:g}"


def _values_equal(a, b) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return float(a) == float(b)
    return a == b


def _plain_arg(value_src: str) -> cst.Arg:
    return cst.Arg(value=cst.parse_expression(value_src))


def _kwarg(field: str, value_src: str) -> cst.Arg:
    return cst.Arg(
        value=cst.parse_expression(value_src),
        keyword=cst.Name(field),
        equal=cst.AssignEqual(whitespace_before=cst.SimpleWhitespace(""),
                              whitespace_after=cst.SimpleWhitespace("")),
    )


def _normalize_commas(args):
    """Every arg but the last separated by ", ", no trailing comma."""
    out = []
    for i, a in enumerate(args):
        if i == len(args) - 1:
            out.append(a.with_changes(comma=cst.MaybeSentinel.DEFAULT))
        elif a.comma is cst.MaybeSentinel.DEFAULT or not isinstance(a.comma, cst.Comma):
            out.append(a.with_changes(comma=cst.Comma(
                whitespace_after=cst.SimpleWhitespace(" "))))
        else:
            out.append(a)
    return out


def _edit_call(call, fields, changed, defaults, editable):
    """Update a Label(...)-style Call: rewrite only the changed fields,
    dropping arguments that return to their dataclass default."""
    args = list(call.args)
    field_order = list(defaults)
    for field in sorted(set(changed), key=field_order.index):
        if field not in editable:
            continue
        value = fields[field]
        is_default = _values_equal(value, defaults[field])
        src = _fmt_value(value)
        if field == "size":
            # File convention: size is the first positional argument.
            if args and args[0].keyword is None:
                if is_default:
                    del args[0]
                else:
                    args[0] = args[0].with_changes(value=cst.parse_expression(src))
            elif not is_default:
                args.insert(0, _plain_arg(src))
            continue
        idx = next((i for i, a in enumerate(args)
                    if a.keyword is not None and a.keyword.value == field), None)
        if is_default:
            if idx is not None:
                del args[idx]
        elif idx is not None:
            args[idx] = args[idx].with_changes(value=cst.parse_expression(src))
        else:
            args.append(_kwarg(field, src))
    return call.with_changes(args=_normalize_commas(args))


class _Transformer(cst.CSTTransformer):
    """Applies edits to module-level `VAR = { "key": Factory(...) }` tables."""

    def __init__(self, edits):
        self.edits = edits  # {var: {key: (fields, changed)}}

    def leave_Assign(self, original, updated):
        target = original.targets[0].target
        if not (isinstance(target, cst.Name) and target.value in self.edits):
            return updated
        if not isinstance(updated.value, cst.Dict):
            return updated
        table_id = target.value
        table_edits = self.edits[table_id]
        defaults = registry.field_defaults(table_id)
        editable = set(registry.editable_fields(table_id))
        elements = []
        for el in updated.value.elements:
            if (isinstance(el, cst.DictElement)
                    and isinstance(el.key, cst.SimpleString)
                    and isinstance(el.value, cst.Call)):
                key = el.key.evaluated_value
                if key in table_edits:
                    fields, changed = table_edits[key]
                    el = el.with_changes(value=_edit_call(
                        el.value, fields, changed, defaults, editable))
            elements.append(el)
        return updated.with_changes(
            value=updated.value.with_changes(elements=elements))


def _entry_line(table_id, key, fields) -> str:
    """A brand-new table entry, formatted in the file's style."""
    t = registry.TABLES[table_id]
    defaults = registry.field_defaults(table_id)
    editable = registry.editable_fields(table_id)
    args = []
    size = fields.get("size")
    if "size" in editable and not _values_equal(size, defaults.get("size")):
        args.append(_fmt_value(size))
    for field in defaults:
        if field == "size" or field not in editable:
            continue
        if not _values_equal(fields.get(field), defaults[field]):
            args.append(f"{field}={_fmt_value(fields[field])}")
    line = f'    "{key}": {t.factory}({", ".join(args)}),'
    display = registry.display_name(table_id, key)
    if display != key:
        line += f"  # {display}"
    return line + "\n"


def _insert_entries(source: str, table_id: str, entries) -> str:
    """Append new entries just before the table's closing brace."""
    lines = source.splitlines(keepends=True)
    start = next(i for i, ln in enumerate(lines)
                 if ln.startswith(f"{table_id} = {{"))
    depth = 0
    for i in range(start, len(lines)):
        depth += lines[i].count("{") - lines[i].count("}")
        if depth == 0:
            end = i  # line holding the closing brace
            break
    new = [_entry_line(table_id, key, fields) for key, (fields, _) in entries]
    return "".join(lines[:end] + new + lines[end:])


def apply_edits(edits: dict) -> list:
    """Patch the source files and the in-memory tables. Returns a list of
    {path, diff} for every modified file."""
    by_file = {}
    for table_id in edits:
        if table_id not in registry.TABLES:
            raise ValueError(f"unknown table {table_id!r}")
        path = Path(registry.table_module(table_id).__file__)
        by_file.setdefault(path, []).append(table_id)

    results = []
    staged = []  # (path, new_source, in-memory updates)
    for path, table_ids in by_file.items():
        old = path.read_text(encoding="utf-8")
        updates, inserts = {}, {}
        for table_id in table_ids:
            table = registry.table_dict(table_id)
            for key, edit in edits[table_id].items():
                pair = (edit["fields"], list(edit["changed"]))
                if key in table:
                    updates.setdefault(table_id, {})[key] = pair
                else:
                    inserts.setdefault(table_id, []).append((key, pair))
        new = old
        if updates:
            new = cst.parse_module(new).visit(_Transformer(updates)).code
        for table_id, entries in inserts.items():
            new = _insert_entries(new, table_id, entries)
        if new == old:
            continue
        compile(new, str(path), "exec")  # refuse to write broken syntax
        diff = "".join(difflib.unified_diff(
            old.splitlines(keepends=True), new.splitlines(keepends=True),
            fromfile=str(path), tofile=str(path)))
        staged.append((path, new))
        results.append(dict(path=str(path.relative_to(path.parents[1])),
                            diff=diff))

    # All files validated: write, then sync the in-memory tables.
    for path, new in staged:
        tmp = path.with_suffix(".py.tmp")
        tmp.write_text(new, encoding="utf-8")
        tmp.replace(path)
    for table_id, table_edits in edits.items():
        table = registry.table_dict(table_id)
        cls = registry.factory_class(table_id)
        editable = set(registry.editable_fields(table_id))
        for key, edit in table_edits.items():
            values = {f: v for f, v in edit["fields"].items() if f in editable}
            if key in table:
                table[key] = replace(table[key], **values)
            else:
                table[key] = cls(**values)
    return results
