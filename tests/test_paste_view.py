"""tools/blueprints/paste_view.py: the pictures the panel's "Show nodes" draws from paste text.

    py -I tests/test_paste_view.py
"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "blueprints"))

from bp_graph import Graph  # noqa: E402
from bp_nodes import Nodes  # noqa: E402
import paste_view as P  # noqa: E402


def seat_heal():
    """Two comment boxes: a tick chain with math and a constant, and an input that clears a flag."""
    g = Graph()
    n = Nodes(g, self_class="/MyMod/Runtime/BP_MyActor.BP_MyActor_C")
    g.box("EdGraphNode_Comment_900", -80, -140, 900, 520, "Tick: heal while seated")
    tick = n.event_tick()
    pc = n.cast_player(exec_from=[tick["then"]], label="tick")
    br = n.branch(n.self_get("Seated", "bool"), "only while seated")
    n.chain(pc, br)
    dt = n.math("Subtract_DoubleDouble", n.game_time(), n.self_get("LastHeal", "real", "double"))
    br2 = n.branch(n.math("Greater_DoubleDouble", dt, None, b_const="2.0"), "every 2 s")
    n.chain(br, br2)
    n.chain(br2, n.self_set("LastHeal", "real", value=n.game_time(), sub="double", comment="remember when"))
    g.box("EdGraphNode_Comment_901", -80, 500, 900, 400, "Input: stand up")
    ia = n.input_action("/MyMod/Input/IA_StandUp.IA_StandUp", x=20, y=600, comment="stand up")
    n.chain(ia, n.self_set("Seated", "bool", default="false", x=300, y=600, comment="not seated"))
    g.layout_tree()
    return "\n".join(g.text())


def link_out(text, node, pin, target):
    """Points one pin of the paste at a node that is not in it (a wire the tester draws by hand)."""
    out, cur = [], None
    for line in text.splitlines():
        if line.startswith("Begin Object"):
            cur = line.split('Name="')[1].split('"')[0]
        if cur == node and f'PinName="{pin}"' in line and "LinkedTo" not in line:
            line = line.replace("PersistentGuid=", f"LinkedTo=({target} {'0' * 31}1,),PersistentGuid=", 1)
        out.append(line)
    return "\n".join(out)


class PasteView(unittest.TestCase):
    def setUp(self):
        self.text = seat_heal()
        branch = next(n["name"] for n in P.parse(self.text)[0] if n["klass"] == "K2Node_IfThenElse")
        self.ext = link_out(self.text, branch, "else", "K2Node_CallFunction_77")

    def test_one_picture_per_box(self):
        vs = P.views(self.text)
        self.assertEqual([v["title"] for v in vs], ["Tick: heal while seated", "Input: stand up"])
        self.assertEqual(sum(v["nodes"] for v in vs), len(P.parse(self.text)[0]))
        for v in vs:
            self.assertTrue(v["svg"].startswith("<svg ") and v["svg"].endswith("</svg>"))
            self.assertIn(f'viewBox="{v["minx"]} {v["miny"]} {v["w"]} {v["h"]}"', v["svg"])
            self.assertLess(len(v["svg"]), 131072)
            self.assertEqual(v["hand"], [])

    def test_readable_names_and_operators(self):
        svg = P.views(self.text)[0]["svg"]
        for label in ("Event Tick", "Branch", "Get Game Time In Seconds", "only while seated", "2.0", "−", "&gt;"):
            self.assertIn(label, svg)
        self.assertNotIn("K2Node_", svg)

    def test_links_leaving_the_paste_are_wired_by_hand(self):
        hand = P.views(self.ext, {"K2Node_CallFunction_77": "Stop Healing"})[0]["hand"]
        self.assertEqual(hand, ["Branch (only while seated) › false → Stop Healing"])
        self.assertIn("Stop Healing", P.views(self.ext, {"K2Node_CallFunction_77": "Stop Healing"})[0]["svg"])

    def test_a_paste_with_no_box_is_one_picture(self):
        g = Graph()
        n = Nodes(g, self_class="/MyMod/Runtime/BP_MyActor.BP_MyActor_C")
        n.event_tick()
        vs = P.views("\n".join(g.text()))
        self.assertEqual([(v["title"], v["nodes"]) for v in vs], [("Graph", 1)])

    def test_write_view_beside_the_paste_with_names_from_meta(self):
        with tempfile.TemporaryDirectory() as d:
            paste = os.path.join(d, "seat_heal.txt")
            with open(paste, "w", encoding="utf-8") as f:
                f.write(self.ext)
            with open(os.path.join(d, "seat_heal.meta.json"), "w", encoding="utf-8") as f:
                json.dump({"external": {"K2Node_CallFunction_77": "Stop Healing"}}, f)
            self.assertEqual(P.write_view(paste), {"views": 2, "nodes": len(P.parse(self.ext)[0]), "hand": 1})
            with open(os.path.join(d, "seat_heal.view.json"), encoding="utf-8") as f:
                view = json.load(f)
            self.assertEqual(view["version"], 1)
            self.assertEqual(view["hand"], ["Branch (only while seated) › false → Stop Healing"])


if __name__ == "__main__":
    unittest.main()
