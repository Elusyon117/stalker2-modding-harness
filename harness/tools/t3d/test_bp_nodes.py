"""Offline tests for bp_nodes and verify_paste (no editor needed).

    python harness/tools/t3d/test_bp_nodes.py

1. bp_nodes builders write the same text as the hand-written factories of ImmersiveCampfires'
   gen_actor_seated_mode.py, which were pasted and compiled in the Zone Kit (reference copies below; GUIDs and node
   numbers are normalised before comparing).
2. A sample graph made with bp_nodes passes verify_paste lint; broken text fails it.
3. compare() finds missing nodes and lost links in an export-shaped text.
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bp_t3d import cls, TGT  # noqa: E402
from bp_graph import Graph, Node  # noqa: E402
import bp_nodes as N  # noqa: E402
import verify_paste as V  # noqa: E402

BG = "/Script/BlueprintGraph."
SELF_PATH = "/ImmersiveCampfires/Runtime/BP_ImmCampActor.BP_ImmCampActor_C"
SELF = f"\"/Script/Engine.BlueprintGeneratedClass'{SELF_PATH}'\""
GET_TIP = 'PinToolTip="Retrieves the value of the variable, can use instead of a separate Get node",'


class Ref:
    """Reference factories copied from gen_actor_seated_mode.py (tested in the editor)."""

    def __init__(self, g):
        self.g, self.seq = g, 0

    def nm(self, kind):
        self.seq += 1
        return f"{kind}_{900 + self.seq}"

    @staticmethod
    def exec_pins(n):
        n.pin("execute", "exec")
        n.pin("then", "exec", out=True)
        return n

    def lib_pure(self, lib, libname, member, x, y, pins, comment=""):
        n = Node(self.g, BG + "K2Node_CallFunction", self.nm("K2Node_CallFunction"), x, y, comment,
                 ["bIsPureFunc=True", f"FunctionReference=(MemberParent={lib},MemberName=\"{member}\")"])
        n.pin("self", "object", sub=lib, hidden=True, extra=f'DefaultObject="/Script/Engine.Default__{libname}",')
        for p in pins:
            n.pin(*p[:2], **p[2]) if len(p) > 2 else n.pin(*p)
        return n

    def member_call(self, owner_cls, member, x, y, target, comment, pins=()):
        n = self.exec_pins(Node(self.g, BG + "K2Node_CallFunction", self.nm("K2Node_CallFunction"), x, y, comment,
                                [f"FunctionReference=(MemberParent={owner_cls},MemberName=\"{member}\")"]))
        n.pin("self", "object", sub=owner_cls, extra=TGT)
        for p in pins:
            n.pin(*p[:2], **p[2]) if len(p) > 2 else n.pin(*p)
        self.g.link(target, n["self"])
        return n

    def self_get(self, var, cat, x, y, sub="None", subcat=""):
        n = Node(self.g, BG + "K2Node_VariableGet", self.nm("K2Node_VariableGet"), x, y, "",
                 [f'VariableReference=(MemberName="{var}",bSelfContext=True)'])
        n.pin(var, cat, sub=sub, subcat=subcat, out=True)
        n.pin("self", "object", sub=SELF, hidden=True, extra=TGT)
        return n[var]

    def self_set(self, var, cat, x, y, comment="", default=None, sub="None", subcat=""):
        n = self.exec_pins(Node(self.g, BG + "K2Node_VariableSet", self.nm("K2Node_VariableSet"), x, y, comment,
                                [f'VariableReference=(MemberName="{var}",bSelfContext=True)']))
        n.pin(var, cat, sub=sub, subcat=subcat, extra=f'DefaultValue="{default}",' if default is not None else "")
        n.pin("Output_Get", cat, sub=sub, subcat=subcat, out=True, extra=GET_TIP)
        n.pin("self", "object", sub=SELF, hidden=True, extra=TGT)
        return n

    def branch(self, x, y, comment, cond):
        n = Node(self.g, BG + "K2Node_IfThenElse", self.nm("K2Node_IfThenElse"), x, y, comment)
        n.pin("execute", "exec")
        n.pin("Condition", "bool", extra='DefaultValue="true",')
        n.pin("then", "exec", out=True, extra='PinFriendlyName=NSLOCTEXT("K2Node", "true", "true"),')
        n.pin("else", "exec", out=True, extra='PinFriendlyName=NSLOCTEXT("K2Node", "false", "false"),')
        self.g.link(cond, n["Condition"])
        return n

    def b_and(self, x, y, a, b):
        n = self.lib_pure(N.KML, "KismetMathLibrary", "BooleanAND", x, y,
                          [("A", "bool", dict(extra='DefaultValue="false",')),
                           ("B", "bool", dict(extra='DefaultValue="false",')),
                           ("ReturnValue", "bool", dict(out=True))])
        self.g.link(a, n["A"])
        self.g.link(b, n["B"])
        return n["ReturnValue"]

    def player_cast(self, x, y, label, exec_from):
        gp = self.lib_pure(N.GS, "GameplayStatics", "GetPlayerPawn", x - 300, y + 220,
                           [("WorldContextObject", "object", dict(sub=N.OBJ, hidden=True)),
                            ("PlayerIndex", "int", dict(extra='DefaultValue="0",')),
                            ("ReturnValue", "object", dict(sub=N.PAWN, out=True))])
        c = self.exec_pins(Node(self.g, BG + "K2Node_DynamicCast", self.nm("K2Node_DynamicCast"), x, y,
                                f"player ({label})", [f"TargetType=\"/Script/CoreUObject.Class'/Script/Stalker2.PC'\""]))
        c.pin("CastFailed", "exec", out=True)
        c.pin("Object", "object", sub=N.OBJ)
        c.pin("AsPC", "object", sub=N.PC, out=True)
        c.pin("bSuccess", "bool", out=True)
        self.g.link(gp["ReturnValue"], c["Object"])
        for e in exec_from:
            self.g.link(e, c["execute"])
        return c

    def delay(self, x, y, seconds, comment):
        dl = Node(self.g, BG + "K2Node_CallFunction", self.nm("K2Node_CallFunction"), x, y, comment,
                  [f"FunctionReference=(MemberParent={N.KSL},MemberName=\"Delay\")"])
        dl.pin("execute", "exec")
        dl.pin("then", "exec", out=True, extra='PinFriendlyName=NSLOCTEXT("K2Node", "Completed", "Completed"),')
        dl.pin("self", "object", sub=N.KSL, hidden=True,
               extra='DefaultObject="/Script/Engine.Default__KismetSystemLibrary",')
        dl.pin("WorldContextObject", "object", sub=N.OBJ, hidden=True)
        dl.pin("Duration", "real", subcat="float", extra=f'DefaultValue="{seconds:.6f}",')
        dl.pin("LatentInfo", "struct", sub=N.LATENT, hidden=True)
        return dl

    def tick(self):
        t = Node(self.g, BG + "K2Node_Event", self.nm("K2Node_Event"), 0, 0, "",
                 [f"EventReference=(MemberParent={N.ACTOR},MemberName=\"ReceiveTick\")", "bOverrideFunction=True"])
        t.pin("OutputDelegate", "delegate", out=True)
        t.pins["OutputDelegate"].member_ref = f'MemberParent={N.ACTOR},MemberName="ReceiveTick"'
        t.pin("then", "exec", out=True)
        t.pin("DeltaSeconds", "real", subcat="float", out=True)
        return t


def norm(lines):
    """Hide GUIDs and node numbers; keep everything else."""
    t = "\n".join(lines)
    t = re.sub(r"\b[0-9A-F]{32}\b", "GUID", t)
    t = re.sub(r"(K2Node_\w+?)_\d+", r"\1_N", t)
    return t


def build_ref():
    g = Graph()
    r = Ref(g)
    t = r.tick()
    c = r.player_cast(300, 0, "tick", [t["then"]])
    cond = r.b_and(600, 300, r.self_get("SeatedMode", "bool", 400, 300), r.self_get("Standing", "bool", 400, 400))
    br = r.branch(600, 0, "seated?", cond)
    g.link(c["then"], br["execute"])
    s = r.self_set("Standing", "bool", 900, 0, "stand up", default="true")
    g.link(br["then"], s["execute"])
    m = r.member_call(N.CHAR, "StopAnimMontage", 1200, 0, c["AsPC"], "stop sit",
                      [("AnimMontage", "object", dict(sub=N.MONT))])
    g.link(s["then"], m["execute"])
    d = r.delay(1500, 0, 3.6, "wait")
    g.link(m["then"], d["execute"])
    return g


def build_new():
    g = Graph()
    n = N.Nodes(g, self_class=SELF_PATH)
    t = n.event_tick()
    c = n.cast_player(exec_from=[t["then"]], label="tick", x=300, y=0)
    cond = n.b_and(n.self_get("SeatedMode", "bool", x=400, y=300), n.self_get("Standing", "bool", x=400, y=400),
                   x=600, y=300)
    br = n.branch(cond, "seated?", x=600, y=0)
    s = n.self_set("Standing", "bool", default="true", x=900, y=0, comment="stand up")
    m = n.call(N.CHAR, "StopAnimMontage", c["AsPC"], [N.obj("AnimMontage", N.MONT)], x=1200, y=0, comment="stop sit")
    d = n.delay(3.6, "wait", x=1500, y=0)
    n.chain(c, br, s, m, d)
    return g


def blocks(text):
    """Node blocks sorted by class + member + comment (node order differs between builders); inside a block the
    line order is kept (pin order included), only GUIDs and node numbers are hidden."""
    out = []
    for b in V.nodes_of_paste(text):
        body = re.sub(r"\b[0-9A-F]{32}\b", "GUID", "\n".join(b.lines))
        body = re.sub(r"(K2Node_\w+?)_\d+", r"\1_N", body)
        out.append((V.sig(b), V.short(b.klass), body))
    return [(k, body) for _, k, body in sorted(out)]


class Equivalence(unittest.TestCase):
    def test_same_text_as_tested_factories(self):
        ref = blocks("\n".join(build_ref().text()))
        new = blocks("\n".join(build_new().text()))
        self.assertEqual(len(ref), len(new))
        for (kr, br_), (kn, bn) in zip(ref, new):
            self.assertEqual(kr, kn)
            self.assertEqual(br_, bn, f"{kr} differs")


class Lint(unittest.TestCase):
    def test_generated_graph_is_clean(self):
        g = build_new()
        n = N.Nodes(g, self_class=SELF_PATH, name_base=5000)
        ev = n.custom_event("OnStarted", [("Montage", "object", N.MONT)], x=0, y=600)
        anim = n.self_get("BoundAnim", "object", sub=N.ANIMI, x=0, y=800)
        bind = n.bind_delegate(N.ANIMI, "OnMontageStarted", "/Script/Engine",
                               "OnMontageStartedMCDelegate__DelegateSignature", anim, ev, x=300, y=600)
        arr = n.self_get("HiddenBones", "name", x=0, y=1000)
        fe = n.for_each(arr, "name", x=300, y=1000)
        sq = n.sequence(3, x=600, y=1000)
        n.link(fe["LoopBody"], sq["execute"])
        n.link(ev["then"], bind["execute"])
        g.layout_tree()
        _, errors, notes = V.lint("\n".join(g.text()))
        self.assertEqual(errors, [])

    def test_catches_broken_text(self):
        g = Graph()
        n = N.Nodes(g)
        a = n.sequence(1)
        b = n.sequence(1)
        a["then_0"].links.append(b["execute"])        # one-sided
        n.call(N.KML, "Ease", None)                    # internal-only
        n.lib_pure(N.KSL, "GetAllActorsOfClass")       # impure without exec
        _, errors, _ = V.lint("\n".join(g.text()))
        text = " | ".join(errors)
        self.assertIn("one-sided", text)
        self.assertIn("BlueprintInternalUseOnly", text)
        self.assertIn("pruned", text)

    def test_external_link_is_a_note(self):
        g = Graph()
        n = N.Nodes(g)
        s = n.sequence(1)
        lines = g.text()
        lines = [l.replace('PinName="execute",', 'PinName="execute",LinkedTo=(K2Node_Outside_1 ABC,),') for l in lines]
        _, errors, notes = V.lint("\n".join(lines))
        self.assertTrue(any("external link" in x for x in notes))


def fake_export(paste_lines, drop=None, unlink=None, deleted_extra=True):
    """Export-shaped text: declaration pass, definition pass, Nodes(n) list. drop: node name left out of the list;
    unlink: node whose LinkedTo entries are removed."""
    nodes = V.nodes_of_paste("\n".join(paste_lines))
    out = ['Begin Object Class=/Script/Engine.Blueprint Name="BP_X" ExportPath="/Script/Engine.Blueprint\'/M/BP_X.BP_X\'"',
           '   Begin Object Class=/Script/Engine.EdGraph Name="EventGraph" ExportPath="/M/BP_X.BP_X:EventGraph"']
    for b in nodes:
        out.append(f'      Begin Object Class={b.klass} Name="{b.name}" ExportPath="/M/BP_X.BP_X:EventGraph.{b.name}"')
        out.append("      End Object")
    if deleted_extra:
        out.append('      Begin Object Class=/Script/BlueprintGraph.K2Node_CallFunction Name="K2Node_Dead_1" '
                   'ExportPath="/M/BP_X.BP_X:EventGraph.K2Node_Dead_1"')
        out.append("      End Object")
    out.append("   End Object")
    out.append('   Begin Object Name="EventGraph" ExportPath="/M/BP_X.BP_X:EventGraph"')
    for b in nodes:
        out.append(f'      Begin Object Name="{b.name}" ExportPath="/M/BP_X.BP_X:EventGraph.{b.name}"')
        for l in b.lines:
            if b.name == unlink:
                l = re.sub(r"LinkedTo=\([^)]*\),", "", l)
            out.append("         " + l)
        out.append("      End Object")
    k = 0
    for b in nodes:
        if b.name == drop:
            continue
        out.append(f"      Nodes({k})=\"/Script/BlueprintGraph.{V.short(b.klass)}'{b.name}'\"")
        k += 1
    out.append("   End Object")
    out.append("End Object")
    return "\n".join(out)


class Compare(unittest.TestCase):
    def setUp(self):
        self.lines = build_new().text()
        self.nodes = V.nodes_of_paste("\n".join(self.lines))

    def test_all_arrived(self):
        _, live, missing, thin = V.compare("\n".join(self.lines), fake_export(self.lines))
        self.assertEqual(len(live), len(self.nodes))       # the deleted node is not counted
        self.assertEqual((missing, thin), ([], []))

    def test_missing_and_thin(self):
        br = next(b for b in self.nodes if "IfThenElse" in b.klass).name
        dl = next(b for b in self.nodes if V.member(b) == "Delay").name
        _, _, missing, thin = V.compare("\n".join(self.lines), fake_export(self.lines, drop=br, unlink=dl))
        self.assertEqual([s[0] for s, _ in missing], ["K2Node_IfThenElse"])
        self.assertEqual([s[1] for s, _, _ in thin], ["Delay"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
