"""Tests for the labeling layer: overrides, export manifests, drag math.

Run with: .venv/bin/python -m unittest discover tests
"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tvmaps import labeling  # noqa: E402


def _render(name):
    from generate import registry

    return registry()[name]()


class LabelingTest(unittest.TestCase):
    def setUp(self):
        self._overrides_dir = labeling.OVERRIDES_DIR
        self._editor_dir = labeling.EDITOR_DIR
        self.tmp = Path(tempfile.mkdtemp())
        labeling.OVERRIDES_DIR = self.tmp / "overrides"
        labeling.EDITOR_DIR = self.tmp / "editor"
        labeling.OVERRIDES_DIR.mkdir()

    def tearDown(self):
        labeling.OVERRIDES_DIR = self._overrides_dir
        labeling.EDITOR_DIR = self._editor_dir
        shutil.rmtree(self.tmp)

    def _write_override(self, map_name, labels):
        path = labeling.OVERRIDES_DIR / f"{map_name}.json"
        path.write_text(json.dumps({"schema": 1, "map": map_name,
                                    "labels": labels}))

    def _export(self, name, overrides=None):
        if overrides:
            self._write_override(name, overrides)
        labeling.begin(name, mode="export")
        try:
            _render(name)
        finally:
            ctx = labeling.finish()
        manifest = json.loads(
            (labeling.EDITOR_DIR / name / "labels.json").read_text())
        return ctx, manifest

    def test_manifest_schema(self):
        ctx, m = self._export("spain-comunidades")
        self.assertEqual(m["schema"], 1)
        self.assertEqual(m["canvas"], {"width_px": 4000, "height_px": 2250,
                                       "dpi": 100})
        self.assertGreater(m["km_per_px"], 0)
        self.assertIsNotNone(m["canary_inset_px"])
        self.assertEqual(len(m["labels"]), 21)   # 18 CCAA + 3 countries
        ids = [e["id"] for e in m["labels"]]
        self.assertEqual(len(ids), len(set(ids)), "label ids must be unique")
        for e in m["labels"]:
            for key in ("id", "kind", "text", "anchor_px", "offset_km",
                        "text_px", "bbox_px", "size_pt", "weight", "color",
                        "halo", "ha", "va", "rotation", "editable"):
                self.assertIn(key, e, f"{e['id']} missing {key}")
            self.assertTrue(0 <= e["text_px"]["x"] <= 4000, e["id"])
            self.assertTrue(0 <= e["text_px"]["y"] <= 2250, e["id"])
            b = e["bbox_px"]
            self.assertLess(b["x0"], b["x1"], e["id"])
            self.assertLess(b["y0"], b["y1"], e["id"])
        locked = {e["id"] for e in m["locked"]}
        self.assertIn("locked:footer", locked)
        self.assertIn("locked:attribution", locked)
        self.assertIn("locked:inset-caption", locked)
        self.assertEqual(ctx.warnings, [])

    def test_callout_leader_endpoints(self):
        _, m = self._export("spain-comunidades")
        pv = next(e for e in m["labels"] if e["id"] == "ccaa:16")  # País Vasco
        self.assertEqual(pv["callout_km"], {"tx": 75, "ty": 100})
        self.assertEqual(pv["leader"]["from_px"], pv["text_px"])
        # The leader points from the text back to the (unmoved) anchor.
        self.assertEqual(pv["leader"]["to_px"], pv["anchor_px"])

    def test_drag_math_roundtrip(self):
        """text_px must equal anchor_px shifted by the km offsets, so the
        editor can convert a pixel drag back to km exactly."""
        _, m = self._export("spain-comunidades")
        k = m["km_per_px"]
        for e in m["labels"]:
            dx = e["offset_km"]["dx"] + (e["callout_km"]["tx"]
                                         if e["callout_km"] else 0)
            dy = e["offset_km"]["dy"] + (e["callout_km"]["ty"]
                                         if e["callout_km"] else 0)
            self.assertAlmostEqual(e["text_px"]["x"],
                                   e["anchor_px"]["x"] + dx / k, delta=0.2)
            self.assertAlmostEqual(e["text_px"]["y"],
                                   e["anchor_px"]["y"] - dy / k, delta=0.2)

    def test_override_moves_label(self):
        _, base = self._export("spain-comunidades")
        _, moved = self._export("spain-comunidades",
                                overrides={"ccaa:12": {"dx": 60, "dy": -40}})
        e0 = next(e for e in base["labels"] if e["id"] == "ccaa:12")
        e1 = next(e for e in moved["labels"] if e["id"] == "ccaa:12")
        k = base["km_per_px"]
        self.assertAlmostEqual(e1["text_px"]["x"] - e0["text_px"]["x"],
                               60 / k, delta=0.2)
        self.assertAlmostEqual(e1["text_px"]["y"] - e0["text_px"]["y"],
                               40 / k, delta=0.2)

    def test_override_promote_and_demote_callout(self):
        _, m = self._export("spain-comunidades", overrides={
            "ccaa:13": {"tx": 90, "ty": -70},   # Madrid: plain -> callout
            "ccaa:06": {"tx": None, "ty": None, "dy": 20},  # Cantabria: -> plain
        })
        madrid = next(e for e in m["labels"] if e["id"] == "ccaa:13")
        self.assertEqual(madrid["callout_km"], {"tx": 90, "ty": -70})
        self.assertIsNotNone(madrid["leader"])
        cant = next(e for e in m["labels"] if e["id"] == "ccaa:06")
        self.assertIsNone(cant["callout_km"])
        self.assertIsNone(cant["leader"])

    def test_bad_overrides_warn_and_skip(self):
        ctx, m = self._export("spain-comunidades", overrides={
            "ccaa:01": {"weight": "regular", "dx": "oops", "size": 60},
            "ccaa:99": {"dx": 10},
        })
        warnings = "\n".join(ctx.warnings)
        self.assertIn("'weight' is not editable", warnings)
        self.assertIn("bad value for 'dx'", warnings)
        self.assertIn("unknown label id 'ccaa:99'", warnings)
        # The valid field of a partly-bad override still applies.
        e = next(e for e in m["labels"] if e["id"] == "ccaa:01")
        self.assertEqual(e["size_pt"], 60)

    def test_badge_geometry_exported(self):
        _, m = self._export("spain-ciudades")
        e = next(e for e in m["labels"] if e["id"] == "bigcity:Madrid")
        self.assertEqual(e["badge"]["number"], 1)
        self.assertGreater(e["badge"]["radius_px"], 10)
        self.assertIn("center_px", e["badge"])
        legend = [x for x in m["locked"] if x["kind"] == "legend"]
        self.assertEqual(len(legend), 34)  # 30 cities + 4 wrap continuations

    def test_zone_sub_and_leader_style(self):
        _, m = self._export("spain-vinos")
        rioja = next(e for e in m["labels"] if e["id"] == "zone:Rioja")
        self.assertIsNotNone(rioja["leader"])
        rb = next(e for e in m["labels"] if e["id"] == "zone:Rías Baixas")
        self.assertEqual(rb["sub"], {"text": "albariño", "size_pt": 24})
        self.assertEqual(rb["leader"]["shrink_from_pt"], 26)

    def test_index(self):
        self._export("spain-comunidades")
        labeling.write_index(["spain-comunidades"])
        idx = json.loads((labeling.EDITOR_DIR / "index.json").read_text())
        self.assertEqual(idx["maps"][0]["name"], "spain-comunidades")
        self.assertEqual(idx["maps"][0]["labels"], 21)


if __name__ == "__main__":
    unittest.main()
