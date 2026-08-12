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

import ast
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
    if isinstance(a, bool) != isinstance(b, bool):
        return False
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


# Fields the files always write explicitly even when the value matches the
# dataclass default (every PROV_LABELS entry names its group).
KEEP_EXPLICIT = {"group"}


def _find_arg(args, field, field_order):
    """Index of the arg bound to `field`, mapping positionals through the
    dataclass field order. Returns (index, is_positional) or (None, None)."""
    pos = 0
    for i, a in enumerate(args):
        if a.keyword is None:
            bound = field_order[pos]
            pos += 1
        else:
            bound = a.keyword.value
        if bound == field:
            return i, a.keyword is None
    return None, None


def _arg_equals(arg, value) -> bool:
    """True when the arg's current literal already IS `value` — then the node
    is left untouched, preserving the author's formatting (43.220, -5.0)."""
    try:
        current = ast.literal_eval(_CODEGEN.code_for_node(arg.value))
    except (ValueError, SyntaxError):
        return False
    return _values_equal(current, value)


def _edit_call(call, fields, changed, defaults, editable):
    """Update a Label(...)-style Call: rewrite only the changed fields,
    dropping keyword arguments that return to their dataclass default."""
    args = list(call.args)
    field_order = list(defaults)
    for field in sorted(set(changed), key=field_order.index):
        if field not in editable:
            continue
        value = fields[field]
        is_default = (_values_equal(value, defaults[field])
                      and field not in KEEP_EXPLICIT)
        src = _fmt_value(value)
        idx, positional = _find_arg(args, field, field_order)
        if idx is not None and _arg_equals(args[idx], value):
            continue  # unchanged in substance: keep the author's spelling
        if idx is not None:
            if is_default and not positional:
                del args[idx]
            else:
                # Positional args are rewritten in place even at the default
                # value: removing one would shift the bindings after it.
                args[idx] = args[idx].with_changes(value=cst.parse_expression(src))
        elif not is_default:
            if field == field_order[0]:
                # First dataclass field (size in the Label family): the files
                # pass it positionally.
                args.insert(0, _plain_arg(src))
            else:
                args.append(_kwarg(field, src))
    return call.with_changes(args=_normalize_commas(args))


_CODEGEN = cst.parse_module("")  # empty module, used for code_for_node


def _repad_comment(el, delta):
    """Keep a trailing same-line comment in its column when the entry's
    rendered length changed by `delta` characters."""
    if delta == 0 or not isinstance(el.comma, cst.Comma):
        return el
    ws = el.comma.whitespace_after
    if not (isinstance(ws, cst.ParenthesizedWhitespace)
            and ws.first_line.comment):
        return el
    pad = max(1, len(ws.first_line.whitespace.value) + delta)
    return el.with_changes(comma=el.comma.with_changes(
        whitespace_after=ws.with_changes(
            first_line=ws.first_line.with_changes(
                whitespace=cst.SimpleWhitespace(" " * pad)))))


def _call_key(call, table_id) -> str | None:
    """The entry key carried inside a Call, for list containers: the value of
    the table's key_field argument (positional or keyword)."""
    t = registry.TABLES[table_id]
    field_order = list(registry.field_defaults(table_id))
    idx, _ = _find_arg(list(call.args), t.key_field, field_order)
    if idx is None:
        return None
    value = call.args[idx].value
    return value.evaluated_value if isinstance(value, cst.SimpleString) else None


def _tuple_call(node, factory):
    """(index, Call) of the factory call inside a Tuple, or (None, None)."""
    if isinstance(node, cst.Tuple):
        for i, el in enumerate(node.elements):
            v = el.value
            if (isinstance(v, cst.Call) and isinstance(v.func, cst.Name)
                    and v.func.value == factory):
                return i, v
    return None, None


class _Transformer(cst.CSTTransformer):
    """Applies edits to module-level label tables, whatever their shape:
    dicts of Calls, dicts of (data, Call) tuples, lists of Calls keyed by a
    field, and bare single-Call assignments."""

    def __init__(self, edits):
        self.edits = edits  # {source_var: (table_id, {key: (fields, changed)})}

    def _edited(self, table_id, call, pair):
        defaults = registry.field_defaults(table_id)
        editable = set(registry.editable_fields(table_id))
        return _edit_call(call, pair[0], pair[1], defaults, editable)

    def leave_Assign(self, original, updated):
        target = original.targets[0].target
        if not (isinstance(target, cst.Name) and target.value in self.edits):
            return updated
        table_id, table_edits = self.edits[target.value]
        t = registry.TABLES[table_id]

        if t.container == "single" and isinstance(updated.value, cst.Call):
            pair = table_edits.get(t.id)
            if pair:
                return updated.with_changes(
                    value=self._edited(table_id, updated.value, pair))
            return updated

        if t.container in ("dict", "tuple2") and isinstance(updated.value, cst.Dict):
            elements = []
            for el in updated.value.elements:
                if (isinstance(el, cst.DictElement)
                        and isinstance(el.key, cst.SimpleString)):
                    key = el.key.evaluated_value
                    pair = table_edits.get(key)
                    if pair and isinstance(el.value, cst.Call):
                        call = self._edited(table_id, el.value, pair)
                        delta = (len(_CODEGEN.code_for_node(el.value))
                                 - len(_CODEGEN.code_for_node(call)))
                        el = _repad_comment(el.with_changes(value=call), delta)
                    elif pair and t.container == "tuple2":
                        i, call = _tuple_call(el.value, t.factory)
                        if call is not None:
                            new_call = self._edited(table_id, call, pair)
                            tup_els = list(el.value.elements)
                            tup_els[i] = tup_els[i].with_changes(value=new_call)
                            el = el.with_changes(
                                value=el.value.with_changes(elements=tup_els))
                    elements.append(el)
                else:
                    elements.append(el)
            return updated.with_changes(
                value=updated.value.with_changes(elements=elements))

        if t.container == "list" and isinstance(updated.value, cst.List):
            elements = []
            for el in updated.value.elements:
                v = el.value
                if isinstance(v, cst.Call):
                    key = _call_key(v, table_id)
                    pair = table_edits.get(key)
                    if pair:
                        call = self._edited(table_id, v, pair)
                        delta = (len(_CODEGEN.code_for_node(v))
                                 - len(_CODEGEN.code_for_node(call)))
                        el = _repad_comment(el.with_changes(value=call), delta)
                elements.append(el)
            return updated.with_changes(
                value=updated.value.with_changes(elements=elements))

        return updated


def _entry_line(table_id, key, fields) -> str:
    """A brand-new table entry, formatted in the file's style."""
    t = registry.TABLES[table_id]
    defaults = registry.field_defaults(table_id)
    editable = registry.editable_fields(table_id)
    field_order = list(defaults)
    args = []
    for field in field_order:
        if field not in editable:
            continue
        if _values_equal(fields.get(field), defaults[field]):
            continue
        if field == field_order[0]:
            args.append(_fmt_value(fields[field]))  # positional, file style
        else:
            args.append(f"{field}={_fmt_value(fields[field])}")
    line = f'    "{key}": {t.factory}({", ".join(args)}),'
    display = registry.display_name(table_id, key)
    if display != key:
        line += f"  # {display}"
    return line + "\n"


def _insert_entries(source: str, table_id: str, entries) -> str:
    """Append new entries just before the table's closing brace."""
    var = registry.TABLES[table_id].source_var
    lines = source.splitlines(keepends=True)
    start = next(i for i, ln in enumerate(lines)
                 if ln.startswith(f"{var} = {{"))
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
            t = registry.TABLES[table_id]
            existing = registry.entries(table_id)
            for key, edit in edits[table_id].items():
                pair = (edit["fields"], list(edit["changed"]))
                if key in existing:
                    updates.setdefault(t.source_var, (table_id, {}))[1][key] = pair
                elif t.container == "dict":
                    inserts.setdefault(table_id, []).append((key, pair))
                else:
                    raise ValueError(
                        f"{table_id}: unknown entry {key!r} (cannot insert "
                        f"into a {t.container} table)")
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
        existing = registry.entries(table_id)
        cls = registry.factory_class(table_id)
        editable = set(registry.editable_fields(table_id))
        for key, edit in table_edits.items():
            values = {f: v for f, v in edit["fields"].items() if f in editable}
            if key in existing:
                registry.set_entry(table_id, key,
                                   replace(existing[key], **values))
            else:
                registry.set_entry(table_id, key, cls(**values))
    return results
