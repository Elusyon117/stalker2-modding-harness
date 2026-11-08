"""Offline tests for bp_anim (no editor needed).

    python tests/test_bp_anim.py

A synthetic AnimBP export in the shape AssetExportTask writes (declaration pass with classes, definition pass with
properties and pins, a nested binding sub-object) stands in for the game's AnimBP_Player; the tests check that each
builder copies the right template, changes only its own settings, drops the template's bindings, and that the wired
result passes verify_paste lint.
"""
import os
import re
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools", "blueprints"))
from bp_t3d import G, pin  # noqa: E402
import bp_anim  # noqa: E402
import verify_paste as V  # noqa: E402

POSE = "\"/Script/CoreUObject.ScriptStruct'/Script/Engine.PoseLink'\""
ASSET = "/Game/Anim/AnimBP_Fake.AnimBP_Fake"


def node(kind, idx, props, pins):
    name = f"AnimGraphNode_{kind}_{idx}"
    path = f"/Script/AnimGraph.AnimGraphNode_{kind}'{ASSET}:AnimGraph.{name}'"
    decl = [f'      Begin Object Class=/Script/AnimGraph.AnimGraphNode_{kind} Name="{name}" ExportPath="{path}"',
            "      End Object"]
    body = [f'      Begin Object Name="{name}" ExportPath="{path}"']
    body += ["         " + p for p in props]
    body += ["         NodePosX=100", "         NodePosY=200", f"         NodeGuid={G()}"]
    for pname, out in pins:
        body.append("      " + pin(G(), pname, "struct", sub=POSE, out=out, links=[("SomeOtherNode", G())]))
    body.append("      End Object")
    return decl, body


def fake_export(path):
    parts = [
        node("SequencePlayer", 0, ['Node=(Sequence="/Script/Engine.AnimSequence\'/Game/Old/AS_old.AS_old\'",PlayRate=1.0)',
                                   'PropertyBindings=(("PlayRate", (PathAsText="Speed")))'], [("Pose", True)]),
        node("LayeredBoneBlend", 3, ['Node=(LayerSetup=((BranchFilters=((BoneName="spine_01",BlendDepth=2)))))'],
             [("BasePose", False), ("BlendPoses_0", False), ("Pose", True)]),
        node("SaveCachedPose", 0, ['CacheName="OldCache"'], [("Pose", False)]),
        node("UseCachedPose", 1, ['NameOfCache="OldCache"',
                                  'SaveCachedPoseNode="/Script/AnimGraph.AnimGraphNode_SaveCachedPose\'AnimBP_Fake:AnimGraph.AnimGraphNode_SaveCachedPose_0\'"'],
             [("Pose", True)]),
        node("Slot", 2, ['Node=(SlotName="DefaultSlot")'], [("Source", False), ("Pose", True)]),
        node("BlendListByBool", 9, ['PropertyBindings=(("bActiveValue", (PathAsText="OldFlag",PropertyPath=("OldFlag"))))',
                                    'NodeComment="old comment"', "bCommentBubbleVisible=True"],
             [("BlendPose_0", False), ("BlendPose_1", False), ("Pose", True)]),
    ]
    lines = [f'Begin Object Class=/Script/Engine.AnimBlueprint Name="AnimBP_Fake" ExportPath="/Script/Engine.AnimBlueprint\'{ASSET}\'"',
             f'   Begin Object Class=/Script/Engine.EdGraph Name="AnimGraph" ExportPath="/Script/Engine.EdGraph\'{ASSET}:AnimGraph\'"']
    for decl, _ in parts:
        lines += decl
    lines += ["   End Object",
              f'   Begin Object Name="AnimGraph" ExportPath="/Script/Engine.EdGraph\'{ASSET}:AnimGraph\'"']
    for _, body in parts:
        lines += body
    lines += ["   End Object", "End Object"]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


class AnimNodes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.export = os.path.join(cls.tmp, "AnimBP_Fake.t3d")
        fake_export(cls.export)

    def build(self):
        ag = bp_anim.AnimGraph(target="ABP_MyLegs", exports=[self.export])
        save = ag.save_cache("GameInput", -700, 0)
        base = ag.use_cache(save, -400, 0)
        sit = ag.sequence("/Game/Anim/AS_sit.AS_sit", -400, 150)
        legs = ag.layered_blend("pelvis", 0, 0, 0, comment="sit legs")
        slot = ag.slot("UpperBody", 200, 0)
        on = ag.blend_by_bool("Seated", 400, 0)
        ag.link(base, "Pose", legs, "BasePose")
        ag.link(sit, "Pose", legs, "BlendPoses_0")
        ag.link(legs, "Pose", slot, "Source")
        ag.link(slot, "Pose", on, "BlendPose_0")
        ag.box(-800, -150, 1500, 700, "Seated legs")
        return ag, "\n".join(ag.text())

    def test_kinds_found(self):
        ag = bp_anim.AnimGraph(target="X", exports=[self.export])
        self.assertEqual(ag.kinds(), {"BlendListByBool": 1, "LayeredBoneBlend": 1, "SaveCachedPose": 1,
                                      "SequencePlayer": 1, "Slot": 1, "UseCachedPose": 1})

    def test_settings_changed(self):
        _, text = self.build()
        self.assertIn("Sequence=\"/Script/Engine.AnimSequence'/Game/Anim/AS_sit.AS_sit'\",PlayRate=1.0", text)
        self.assertIn('BranchFilters=((BoneName="pelvis",BlendDepth=0)', text)
        self.assertIn('CacheName="GameInput"', text)
        self.assertIn('NameOfCache="GameInput"', text)
        self.assertIn("AnimGraphNode_SaveCachedPose'ABP_MyLegs:AnimGraph.AnimGraphNode_SaveCachedPose_901'", text)
        self.assertIn('Node=(SlotName="UpperBody")', text)
        self.assertIn('PathAsText="Seated"', text)
        self.assertIn('PropertyPath=("Seated")', text)
        self.assertNotIn("Speed", text)           # the sequence template's binding is dropped
        self.assertNotIn("old comment", text)
        self.assertIn('NodeComment="sit legs"', text)
        self.assertNotIn("SomeOtherNode", text)   # template links are dropped

    def test_lint_clean(self):
        _, text = self.build()
        nodes, errors, notes = V.lint(text)
        self.assertEqual(errors, [])
        self.assertEqual(len([n for n in nodes if "Comment" not in n.klass]), 6)
        self.assertFalse(any("external link" in n for n in notes))

    def test_bad_pin_is_an_error(self):
        ag = bp_anim.AnimGraph(target="X", exports=[self.export])
        a = ag.sequence("/Game/A.A")
        b = ag.slot("DefaultSlot")
        with self.assertRaises(SystemExit) as e:
            ag.link(a, "Pose", b, "Input")
        self.assertIn("has no pin 'Input'", str(e.exception))

    def test_missing_kind_is_an_error(self):
        ag = bp_anim.AnimGraph(target="X", exports=[self.export])
        with self.assertRaises(SystemExit) as e:
            ag.raw("TwoWayBlend")
        self.assertIn("no AnimGraphNode_TwoWayBlend", str(e.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
