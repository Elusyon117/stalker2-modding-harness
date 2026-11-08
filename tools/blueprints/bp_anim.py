"""Ready-made AnimGraph nodes: Sequence Player, Sequence Evaluator, Layered Blend per Bone, Save / Use Cached Pose,
Slot, Blend Poses by Bool, wired into paste text for an Animation Blueprint's AnimGraph.

AnimGraph nodes carry many settings the editor needs (inner Node structs, binding sub-objects, pose-link pins), so
they are not written from scratch: each one is a copy of a real node of the same kind taken from the game's own
AnimBPs (exported with tools/editor/export_t3d.py), with only the settings below changed. That is how the shipped
mods built theirs (ImmersiveCampfires' seated legs: knowledge/animation.md).

    from bp_anim import AnimGraph
    ag = AnimGraph(target="ABP_MySeatedLegs", exports=[f"{SCRATCH}/AnimBP_Player.t3d", f"{SCRATCH}/AnimBP_player_bh.t3d"])
    save = ag.save_cache("GameInput", -700, 0)
    base = ag.use_cache(save, -400, 0)
    sit = ag.sequence("/Game/_STALKER2/Animations/Player/AnimSequences/.../AS_sit_idle.AS_sit_idle", -400, 150)
    legs = ag.layered_blend("pelvis", 0, 0, 0, comment="sit pose below the spine")
    ag.link(base, "Pose", legs, "BasePose")
    ag.link(sit, "Pose", legs, "BlendPoses_0")
    on = ag.blend_by_bool("Seated", 400, 0)
    ag.link(legs, "Pose", on, "BlendPose_0")
    ag.box(-800, -150, 1500, 700, "Seated legs")
    write(out_path, ag.text())

Then `verify_paste.py lint`, the tester pastes into the AnimGraph and wires Input Pose / Output Pose by hand
(LinkedInputPose and Root nodes do not paste), compiles, saves; `verify_paste.py compare --asset ...` checks it.

What node kinds the exports hold, and how many of each:
    python bp_anim.py kinds <export.t3d> [...]
"""
import re
import sys

from bp_t3d import comment_box
from t3d_lift import Lifted, link as _link

ANIM = "/Script/AnimGraph.AnimGraphNode_"
DECL = re.compile(r'^\s*Begin Object Class=(/Script/AnimGraph\.AnimGraphNode_(\w+)) Name="([^"]+)" ExportPath="([^"]+)"')


def _export_path(raw):
    """ExportPath value -> the object path Lifted matches on ('/Game/X.X:AnimGraph.Node_0')."""
    raw = raw.rstrip("'")
    return raw.split("'", 1)[1] if "'" in raw else raw


def scan(export_file):
    """[(kind, export_path), ...] for every AnimGraph node declared in an export, in file order."""
    out = []
    with open(export_file, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = DECL.match(line)
            if m:
                out.append((m.group(2), _export_path(m.group(4))))
    return out


def _no_bindings(line):
    return "" if line.strip().startswith("PropertyBindings=") else line


def _set_in_node(line, field, value):
    """Set Field=value inside the 'Node=(...)' struct line, adding the field if the template has none."""
    if not line.strip().startswith("Node=("):
        return line
    if re.search(rf'\b{field}=', line):
        return re.sub(rf'\b{field}=("[^"]*"|[^,)]*)', f"{field}={value}", line, count=1)
    return line.replace("Node=(", f"Node=({field}={value},", 1)


class AnimGraph:
    """Collects lifted AnimGraph nodes and links for one paste.

    target: the Animation Blueprint the text is pasted into (its asset name, e.g. 'ABP_MySeatedLegs'); Use Cached Pose
            nodes point at their Save node by '<target>:<graph>.<node>'.
    exports: T3D exports of game AnimBPs to take node templates from (export_t3d.py; AnimBP_Player and
             AnimBP_player_bh hold every kind below).
    """

    def __init__(self, target, exports, graph="AnimGraph", name_base=900):
        self.target, self.graph = target, graph
        self.templates = {}
        for f in exports:
            for kind, path in scan(f):
                self.templates.setdefault(kind, []).append((f, path))
        self.nodes, self.boxes = [], []
        self._seq = name_base

    def kinds(self):
        return {k: len(v) for k, v in sorted(self.templates.items())}

    def _lift(self, kind, x, y, patch, comment="", pick=0):
        found = self.templates.get(kind)
        if not found:
            raise SystemExit(f"no AnimGraphNode_{kind} in the exports; export an AnimBP that uses one "
                             f"(have: {', '.join(self.kinds()) or 'nothing'})")
        f, path = found[min(pick, len(found) - 1)]
        self._seq += 1
        name = f"AnimGraphNode_{kind}_{self._seq}"

        def fix(line):
            line = patch(line)
            # the template's own comment never carries over; a new one is added below when given
            if line and line.strip().startswith(("NodeComment=", "bCommentBubbleVisible=")):
                return ""
            return line

        n = Lifted(f, path, name, x, y, fix)
        n.lines = [l for l in n.lines if l != ""]
        if comment:
            n.lines += ["   bCommentBubbleVisible=True", f'   NodeComment="{comment}"']
        n.kind = kind
        self.nodes.append(n)
        return n

    # ---- nodes -------------------------------------------------------------------------------------------------
    def sequence(self, asset, x=0, y=0, comment="", pick=0):
        """Sequence Player playing `asset` ('/Game/.../AS_x.AS_x'). Out: Pose."""
        ref = f"\"/Script/Engine.AnimSequence'{asset}'\""
        return self._lift("SequencePlayer", x, y, lambda l: _set_in_node(_no_bindings(l), "Sequence", ref), comment, pick)

    def sequence_evaluator(self, asset, x=0, y=0, comment="", pick=0):
        """Sequence Evaluator showing one frame of `asset` (bind or set ExplicitTime after the paste). Out: Pose."""
        ref = f"\"/Script/Engine.AnimSequence'{asset}'\""
        return self._lift("SequenceEvaluator", x, y, lambda l: _set_in_node(_no_bindings(l), "Sequence", ref), comment, pick)

    def layered_blend(self, bone, depth=0, x=0, y=0, comment="", pick=0):
        """Layered Blend per Bone: the blend pose from `bone` down (depth 0 = the bone itself fully). In: BasePose,
        BlendPoses_0 (and BlendWeights_0); out: Pose. The template's first branch filter gets the bone."""
        def patch(l):
            l = _no_bindings(l)
            return re.sub(r'BranchFilters=\(\(BoneName="[^"]*",BlendDepth=-?\d+\)',
                          f'BranchFilters=((BoneName="{bone}",BlendDepth={depth})', l, count=1)
        return self._lift("LayeredBoneBlend", x, y, patch, comment, pick)

    def save_cache(self, cache, x=0, y=0, comment="", pick=0):
        """Save Cached Pose named `cache`. In: Pose."""
        return self._lift("SaveCachedPose", x, y,
                          lambda l: re.sub(r'CacheName="[^"]*"', f'CacheName="{cache}"', _no_bindings(l)), comment, pick)

    def use_cache(self, save, x=0, y=0, comment="", pick=0):
        """Use Cached Pose reading `save` (a save_cache node of this paste). Out: Pose."""
        ref = (f"SaveCachedPoseNode=\"/Script/AnimGraph.AnimGraphNode_SaveCachedPose'"
               f"{self.target}:{self.graph}.{save.name}'\"")
        cache = next((re.search(r'CacheName="([^"]*)"', l).group(1) for l in save.lines if 'CacheName="' in l), "")

        def patch(l):
            l = _no_bindings(l)
            l = re.sub(r'SaveCachedPoseNode="[^"]*"', ref, l)
            return re.sub(r'NameOfCache="[^"]*"', f'NameOfCache="{cache}"', l)
        return self._lift("UseCachedPose", x, y, patch, comment, pick)

    def slot(self, slot_name, x=0, y=0, comment="", pick=0):
        """Slot node playing montages of `slot_name` (DefaultSlot, UpperBody, FullBody, ...: knowledge/animation.md).
        In: Source; out: Pose."""
        return self._lift("Slot", x, y, lambda l: _set_in_node(_no_bindings(l), "SlotName", f'"{slot_name}"'),
                          comment, pick)

    def blend_by_bool(self, variable, x=0, y=0, comment="", pick=0):
        """Blend Poses by bool with Active Value bound to the AnimBP's bool `variable` (add it first). In: BlendPose_0
        (True), BlendPose_1 (False), BlendTime_0/1; out: Pose."""
        def patch(l):
            if l.strip().startswith("PropertyBindings="):
                l = re.sub(r'PathAsText="[^"]*"', f'PathAsText="{variable}"', l)
                l = re.sub(r'PropertyPath=\([^)]*\)', f'PropertyPath=("{variable}")', l)
            return l
        return self._lift("BlendListByBool", x, y, patch, comment, pick)

    def raw(self, kind, x=0, y=0, comment="", pick=0, patch=_no_bindings):
        """Any other AnimGraphNode_<kind> found in the exports, copied as is (bindings dropped unless `patch` keeps
        them)."""
        return self._lift(kind, x, y, patch, comment, pick)

    # ---- wiring and output -------------------------------------------------------------------------------------
    def link(self, a, a_pin, b, b_pin):
        """Wire a's pin to b's pin (written on both ends). Pin names are the template's: an unknown one is an error,
        so a typo never drops a link silently."""
        for n, p in ((a, a_pin), (b, b_pin)):
            if p not in n.pin_ids:
                raise SystemExit(f"{n.name} has no pin {p!r} (has: {', '.join(n.pin_ids)})")
        _link(a, a_pin, b, b_pin)

    def box(self, x, y, w, h, text):
        self._seq += 1
        self.boxes.append(comment_box(f"EdGraphNode_Comment_{self._seq}", x, y, w, h, text))

    def text(self):
        out = []
        for n in self.nodes:
            out += n.text()
        for b in self.boxes:
            out += b
        return out


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] != "kinds":
        print(__doc__)
        sys.exit(2)
    total = {}
    for f in sys.argv[2:]:
        for kind, _ in scan(f):
            total[kind] = total.get(kind, 0) + 1
    for k, n in sorted(total.items()):
        print(f"{n:5d}  AnimGraphNode_{k}")
