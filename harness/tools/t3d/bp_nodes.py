"""Ready-made Blueprint nodes on top of bp_graph: events, calls, variables, flow control, casts, loops, delegates.

Every builder below copies a node shape that has been pasted into this kit's editor and compiled in a shipped mod
(ImmersiveCampfires gen_actor_seated_mode.py / gen_actor_seated_input.py, ImmersiveDialogue); pin names, pin
categories and the hidden `self` / `WorldContextObject` pins are kept exactly. Use it instead of writing pins by hand:

    from bp_graph import Graph
    from bp_nodes import Nodes, cls, real, obj, boolean, KML, ACTOR
    g = Graph()
    n = Nodes(g, self_class="/MyMod/Runtime/BP_MyActor.BP_MyActor_C")
    g.box("EdGraphNode_Comment_900", -80, -140, 900, 520, "Tick")
    tick = n.event_tick()
    pc = n.cast_player(exec_from=[tick["then"]], label="tick")
    on = n.self_get("Enabled", "bool")
    br = n.branch(on, "only while enabled")
    n.chain(pc, br)
    ...
    g.layout_tree()
    write(out_path, g.text())

Node positions only choose the comment box a node lands in; layout_tree() places everything (blueprints.md).
Pins: every builder returns the Node (index it by pin name: node["then"], node["ReturnValue"]) unless its doc says
it returns a pin. Pin specs for call()/pure() are tuples (name, category, {Pin kwargs}); the helpers real(), obj(),
boolean(), integer(), name(), string(), struct() write them for you.

Traps these builders already respect (see blueprints.md): a pasted pure flag does not count, the UFunction's purity
does (use call() for impure static functions); never call a BlueprintInternalUseOnly function (Ease etc.: dropped
silently); cast output pins use the display name with spaces ("AsInput Mapping Context"); a pasted 0.0 on a pin
whose C++ default is non-zero comes back as the default.
"""
from bp_t3d import cls, TGT
from bp_graph import Node

BG = "/Script/BlueprintGraph."

# ---- common classes / structs --------------------------------------------------------------------------------
OBJ = cls("/Script/CoreUObject.Object")
ACTOR = cls("/Script/Engine.Actor")
PAWN = cls("/Script/Engine.Pawn")
CHAR = cls("/Script/Engine.Character")
PC = cls("/Script/Stalker2.PC")              # the player character class (BP_Stalker2Character's parent)
GS = cls("/Script/Engine.GameplayStatics")
KML = cls("/Script/Engine.KismetMathLibrary")
KSL = cls("/Script/Engine.KismetSystemLibrary")
ANIMI = cls("/Script/Engine.AnimInstance")
MONT = cls("/Script/Engine.AnimMontage")
SKM = cls("/Script/Engine.SkeletalMeshComponent")
IA = cls("/Script/EnhancedInput.InputAction")


def struct_ref(path):
    """'/Script/CoreUObject.Vector' -> quoted ScriptStruct reference for pin types."""
    return "\"/Script/CoreUObject.ScriptStruct'%s'\"" % path


def enum_ref(path):
    return "\"/Script/CoreUObject.Enum'%s'\"" % path


VEC = struct_ref("/Script/CoreUObject.Vector")
ROT = struct_ref("/Script/CoreUObject.Rotator")
V2D = struct_ref("/Script/CoreUObject.Vector2D")
LATENT = struct_ref("/Script/Engine.LatentActionInfo")

GET_TIP = 'PinToolTip="Retrieves the value of the variable, can use instead of a separate Get node",'
STD_MACROS = ("GraphBlueprint=\"/Script/Engine.Blueprint'/Engine/EditorBlueprintResources/StandardMacros."
              "StandardMacros'\"")
MACRO_GUIDS = {   # read from the kit's Engine/Content/EditorBlueprintResources/StandardMacros.uasset
    "ForEachLoop": "99DBFD5540A796041F72A5A9DA655026",
    "ForLoop": "55C904AF4B45FE1761FB55A8DB9FB801",
}


# ---- pin spec helpers ----------------------------------------------------------------------------------------
def _d(default):
    return f'DefaultValue="{default}",' if default is not None else ""


def real(pin_name, default=None, out=False, single=False):
    """A real pin. Blueprint math is double; native function parameters declared `float` need single=True."""
    return (pin_name, "real", dict(subcat="float" if single else "double", out=out, extra="" if out else _d(default)))


def boolean(pin_name, default=None, out=False):
    return (pin_name, "bool", dict(out=out, extra="" if out else _d(default)))


def integer(pin_name, default=None, out=False):
    return (pin_name, "int", dict(out=out, extra="" if out else _d(default)))


def name(pin_name, default=None, out=False):
    return (pin_name, "name", dict(out=out, extra="" if out else _d(default)))


def string(pin_name, default=None, out=False):
    return (pin_name, "string", dict(out=out, extra="" if out else _d(default)))


def obj(pin_name, klass=OBJ, out=False, default_object=None, hidden=False):
    """Object pin of class `klass` (a cls(...) reference). default_object: asset path literal for an input."""
    extra = f'DefaultObject="{default_object}",' if default_object and not out else ""
    return (pin_name, "object", dict(sub=klass, out=out, extra=extra, hidden=hidden))


def klass_pin(pin_name, klass=OBJ, out=False, default_object=None):
    extra = f'DefaultObject="{default_object}",' if default_object and not out else ""
    return (pin_name, "class", dict(sub=klass, out=out, extra=extra))


def struct(pin_name, struct_type, out=False):
    return (pin_name, "struct", dict(sub=struct_type, out=out))


def ret(spec_fn, *a, **kw):
    """ret(real) / ret(obj, SKM): a ReturnValue output pin."""
    return spec_fn("ReturnValue", *a, out=True, **kw)


def _script_path(klass_ref):
    """cls('/Script/Engine.KismetMathLibrary') -> '/Script/Engine.KismetMathLibrary'."""
    inner = klass_ref.strip('"')
    return inner[inner.index("'") + 1:].rstrip("'")


class Nodes:
    """Node builders bound to one Graph. self_class: the generated class of the Blueprint you paste into
    ('/MyMod/Path/BP_X.BP_X_C'); needed for self_get/self_set (their hidden self pin)."""

    def __init__(self, graph, self_class=None, name_base=900):
        self.g = graph
        self.self_ref = (f"\"/Script/Engine.BlueprintGeneratedClass'{self_class}'\"" if self_class else OBJ)
        self._seq = name_base

    # ---- plumbing --------------------------------------------------------------------------------------------
    def nm(self, kind):
        self._seq += 1
        return f"{kind}_{self._seq}"

    def node(self, kind, x=0, y=0, comment="", body=(), klass=None):
        return Node(self.g, klass or BG + kind, self.nm(kind), x, y, comment, list(body))

    @staticmethod
    def add_pins(n, pins):
        for p in pins:
            n.pin(*p[:2], **(p[2] if len(p) > 2 else {}))
        return n

    @staticmethod
    def exec_pins(n, then_name="then", then_extra=""):
        n.pin("execute", "exec")
        n.pin(then_name, "exec", out=True, extra=then_extra)
        return n

    def link(self, a, b):
        """Link two pins (either order of output/input is fine). None is ignored, so optional inputs read well."""
        if a is not None and b is not None:
            self.g.link(a, b)

    @staticmethod
    def exec_in(n):
        for k in ("execute", "Exec"):
            if k in n.pins:
                return n.pins[k]
        raise KeyError(f"{n.name} has no exec input")

    @staticmethod
    def exec_out(n):
        for k in ("then", "then_0", "LoopBody", "Completed"):
            if k in n.pins and n.pins[k].out:
                return n.pins[k]
        raise KeyError(f"{n.name} has no exec output")

    def chain(self, *steps):
        """Wire exec flow through nodes (each node's then -> next node's execute). A step may also be an exec
        output pin (e.g. br['else'])."""
        for a, b in zip(steps, steps[1:]):
            src = a if not isinstance(a, Node) else self.exec_out(a)
            self.g.link(src, self.exec_in(b))
        return steps[-1]

    # ---- events ----------------------------------------------------------------------------------------------
    def event(self, owner, member, outputs=(), x=0, y=0, comment=""):
        """Override of a native/BP event, e.g. event(ACTOR, 'ReceiveBeginPlay'). outputs: extra output pin specs."""
        n = self.node("K2Node_Event", x, y, comment,
                      [f"EventReference=(MemberParent={owner},MemberName=\"{member}\")", "bOverrideFunction=True"])
        n.pin("OutputDelegate", "delegate", out=True)
        n.pins["OutputDelegate"].member_ref = f'MemberParent={owner},MemberName="{member}"'
        n.pin("then", "exec", out=True)
        return self.add_pins(n, outputs)

    def event_tick(self, owner=ACTOR, x=0, y=0, comment=""):
        return self.event(owner, "ReceiveTick", [real("DeltaSeconds", out=True, single=True)], x, y, comment)

    def event_begin_play(self, owner=ACTOR, x=0, y=0, comment=""):
        return self.event(owner, "ReceiveBeginPlay", (), x, y, comment)

    def input_action(self, ia_path, x=0, y=0, comment="", value="bool"):
        """Enhanced Input action event. ia_path: '/Game/.../IA_Jump.IA_Jump'. Outputs Triggered, Started, Ongoing,
        Canceled, Completed, ActionValue, ElapsedSeconds, TriggeredSeconds, InputAction."""
        n = self.node("K2Node_EnhancedInputAction", x, y, comment,
                      [f"InputAction=\"/Script/EnhancedInput.InputAction'{ia_path}'\""],
                      klass="/Script/InputBlueprintNodes.K2Node_EnhancedInputAction")
        for e in ("Triggered", "Started", "Ongoing", "Canceled", "Completed"):
            n.pin(e, "exec", out=True)
        n.pin("ActionValue", value, out=True)
        n.pin("ElapsedSeconds", "real", subcat="double", out=True, adv=True)
        n.pin("TriggeredSeconds", "real", subcat="double", out=True, adv=True)
        n.pin("InputAction", "object", sub=IA, out=True)
        return n

    def custom_event(self, event_name, params=(), x=0, y=0, comment=""):
        """Custom event. params: [(pin_name, category, sub_object_ref_or_None)], written as UserDefinedPins.
        Do not call it from another pasted node of the same graph (blueprints.md); bind it to a delegate instead."""
        body = [f'CustomFunctionName="{event_name}"']
        for pname, cat, sub in params:
            st = f",PinSubCategoryObject={sub}" if sub else ""
            body.append(f'CustomProperties UserDefinedPin (PinName="{pname}",PinType=(PinCategory="{cat}"{st}),'
                        f'DesiredPinDirection=EGPD_Output)')
        n = self.node("K2Node_CustomEvent", x, y, comment, body)
        n.pin("OutputDelegate", "delegate", out=True)
        n.pins["OutputDelegate"].member_ref = f'MemberName="{event_name}",bSelfContext=True'
        n.pin("then", "exec", out=True)
        for pname, cat, sub in params:
            n.pin(pname, cat, sub=sub or "None", out=True)
        return n

    def bind_delegate(self, owner, delegate, signature_package, signature, target, event, x=0, y=0, comment=""):
        """Bind `event` (a custom_event node) to a multicast delegate, e.g.
        bind_delegate(ANIMI, 'OnMontageStarted', '/Script/Engine', 'OnMontageStartedMCDelegate__DelegateSignature',
        anim_instance_pin, ev). Bind once per target object (keep it in a variable and compare)."""
        n = self.exec_pins(self.node("K2Node_AddDelegate", x, y, comment,
                                     [f'DelegateReference=(MemberParent={owner},MemberName="{delegate}")']))
        n.pin("self", "object", sub=owner,
              extra='PinFriendlyName=NSLOCTEXT("K2Node", "BaseMCDelegateSelfPinName", "Target"),')
        n.pin("Delegate", "delegate",
              extra='PinFriendlyName=NSLOCTEXT("K2Node", "PinFriendlyDelegatetName", "Event"),')
        n.pins["Delegate"].member_ref = (f'MemberParent="/Script/CoreUObject.Package\'{signature_package}\'",'
                                         f'MemberName="{signature}"')
        self.link(target, n["self"])
        self.link(event["OutputDelegate"], n["Delegate"])
        return n

    # ---- function calls --------------------------------------------------------------------------------------
    def _fref(self, owner, member):
        return f"FunctionReference=(MemberParent={owner},MemberName=\"{member}\")"

    def call(self, owner, member, target, pins=(), x=0, y=0, comment=""):
        """Impure member call on `target` (an object pin), e.g. call(CHAR, 'PlayAnimMontage', as_pc, [...])."""
        n = self.exec_pins(self.node("K2Node_CallFunction", x, y, comment, [self._fref(owner, member)]))
        n.pin("self", "object", sub=owner, extra=TGT)
        self.add_pins(n, pins)
        self.link(target, n["self"])
        return n

    def pure(self, owner, member, target, pins=(), x=0, y=0, comment=""):
        """Pure member call (a const / BlueprintPure getter) on `target`."""
        n = self.node("K2Node_CallFunction", x, y, comment, ["bIsPureFunc=True", self._fref(owner, member)])
        n.pin("self", "object", sub=owner, extra=TGT)
        self.add_pins(n, pins)
        self.link(target, n["self"])
        return n

    def lib_call(self, lib, member, pins=(), x=0, y=0, comment="", world_context=False):
        """Impure static library call (exec pins), e.g. lib_call(GS, 'SpawnSound2D', ...). Static functions are
        impure unless declared BlueprintPure: when unsure use this one, not lib_pure."""
        n = self.exec_pins(self.node("K2Node_CallFunction", x, y, comment, [self._fref(lib, member)]))
        self._lib_self(n, lib, world_context)
        return self.add_pins(n, pins)

    def lib_pure(self, lib, member, pins=(), x=0, y=0, comment="", world_context=False):
        """BlueprintPure static library function, e.g. lib_pure(KML, 'BooleanAND', [...])."""
        n = self.node("K2Node_CallFunction", x, y, comment, ["bIsPureFunc=True", self._fref(lib, member)])
        self._lib_self(n, lib, world_context)
        return self.add_pins(n, pins)

    @staticmethod
    def _lib_self(n, lib, world_context):
        path = _script_path(lib)
        pkg, short = path.rsplit(".", 1)
        n.pin("self", "object", sub=lib, hidden=True, extra=f'DefaultObject="{pkg}.Default__{short}",')
        if world_context:
            n.pin("WorldContextObject", "object", sub=OBJ, hidden=True)

    # ---- variables -------------------------------------------------------------------------------------------
    def self_get(self, var, cat, sub="None", subcat="", x=0, y=0):
        """Getter of a variable of this Blueprint. Returns the value pin. Create one per use (layout keeps it local).
        Add the variable first (BlueprintEditorLibrary.add_member_variable from editor Python)."""
        n = self.node("K2Node_VariableGet", x, y, "", [f'VariableReference=(MemberName="{var}",bSelfContext=True)'])
        n.pin(var, cat, sub=sub, subcat=subcat, out=True)
        n.pin("self", "object", sub=self.self_ref, hidden=True, extra=TGT)
        return n[var]

    def self_set(self, var, cat, value=None, default=None, sub="None", subcat="", x=0, y=0, comment=""):
        """Setter of a variable of this Blueprint. value: a pin to feed it, or default: a literal."""
        n = self.exec_pins(self.node("K2Node_VariableSet", x, y, comment,
                                     [f'VariableReference=(MemberName="{var}",bSelfContext=True)']))
        n.pin(var, cat, sub=sub, subcat=subcat, extra=_d(default))
        n.pin("Output_Get", cat, sub=sub, subcat=subcat, out=True, extra=GET_TIP)
        n.pin("self", "object", sub=self.self_ref, hidden=True, extra=TGT)
        self.link(value, n[var])
        return n

    def get(self, owner, var, cat, target, sub="None", subcat="", friendly="", x=0, y=0):
        """Getter of a member of another object (e.g. get(CHAR, 'Mesh', 'object', as_pc, sub=SKM)). Returns the pin.
        friendly: PinFriendlyName=... text for native members whose display name differs."""
        n = self.node("K2Node_VariableGet", x, y, "", [f'VariableReference=(MemberParent={owner},MemberName="{var}")'])
        n.pin(var, cat, sub=sub, subcat=subcat, out=True, extra=friendly)
        n.pin("self", "object", sub=owner, extra=TGT)
        self.link(target, n["self"])
        return n[var]

    def set(self, owner, var, cat, target, value=None, default=None, sub="None", subcat="", x=0, y=0, comment=""):
        n = self.exec_pins(self.node("K2Node_VariableSet", x, y, comment,
                                     [f'VariableReference=(MemberParent={owner},MemberName="{var}")']))
        n.pin(var, cat, sub=sub, subcat=subcat, extra=_d(default))
        n.pin("Output_Get", cat, sub=sub, subcat=subcat, out=True, extra=GET_TIP)
        n.pin("self", "object", sub=owner, extra=TGT)
        self.link(target, n["self"])
        self.link(value, n[var])
        return n

    # ---- flow control ----------------------------------------------------------------------------------------
    def branch(self, cond, comment="", x=0, y=0):
        """Branch on a bool pin. Outputs 'then' (true) and 'else' (false)."""
        n = self.node("K2Node_IfThenElse", x, y, comment)
        n.pin("execute", "exec")
        n.pin("Condition", "bool", extra='DefaultValue="true",')
        n.pin("then", "exec", out=True, extra='PinFriendlyName=NSLOCTEXT("K2Node", "true", "true"),')
        n.pin("else", "exec", out=True, extra='PinFriendlyName=NSLOCTEXT("K2Node", "false", "false"),')
        self.link(cond, n["Condition"])
        return n

    def sequence(self, outputs=2, comment="", x=0, y=0):
        """Sequence with then_0..then_<outputs-1>."""
        n = self.node("K2Node_ExecutionSequence", x, y, comment)
        n.pin("execute", "exec")
        for k in range(outputs):
            n.pin(f"then_{k}", "exec", out=True)
        return n

    def delay(self, seconds, comment="", x=0, y=0):
        """Latent Delay; its exec output is 'then' (shown as Completed)."""
        n = self.node("K2Node_CallFunction", x, y, comment, [self._fref(KSL, "Delay")])
        self.exec_pins(n, then_extra='PinFriendlyName=NSLOCTEXT("K2Node", "Completed", "Completed"),')
        n.pin("self", "object", sub=KSL, hidden=True, extra='DefaultObject="/Script/Engine.Default__KismetSystemLibrary",')
        n.pin("WorldContextObject", "object", sub=OBJ, hidden=True)
        n.pin("Duration", "real", subcat="float", extra=f'DefaultValue="{seconds:.6f}",')
        n.pin("LatentInfo", "struct", sub=LATENT, hidden=True)
        return n

    def _macro(self, macro, comment, x, y):
        return self.node("K2Node_MacroInstance", x, y, comment,
                         [f"MacroGraphReference=(MacroGraph=\"/Script/Engine.EdGraph'/Engine/EditorBlueprintResources/"
                          f"StandardMacros.StandardMacros:{macro}'\",{STD_MACROS},GraphGuid={MACRO_GUIDS[macro]})"])

    def for_loop(self, first=0, last=None, comment="", x=0, y=0):
        """ForLoop: execute, FirstIndex, LastIndex -> LoopBody, Index, Completed. last: an int pin."""
        n = self._macro("ForLoop", comment, x, y)
        n.pin("execute", "exec")
        n.pin("FirstIndex", "int", extra=f'DefaultValue="{first}",')
        n.pin("LastIndex", "int")
        n.pin("LoopBody", "exec", out=True)
        n.pin("Index", "int", out=True)
        n.pin("Completed", "exec", out=True)
        self.link(last, n["LastIndex"])
        return n

    def for_each(self, array, elem_cat, elem_sub="None", comment="", x=0, y=0):
        """ForEachLoop over an array pin: Exec, Array -> LoopBody, Array Element, Array Index, Completed."""
        n = self._macro("ForEachLoop", comment, x, y)
        if elem_cat == "object":
            n.body.append(f'ResolvedWildcardType=(PinCategory="object",PinSubCategoryObject={elem_sub})')
        n.pin("Exec", "exec")
        n.pin("Array", elem_cat, sub=elem_sub)
        n.pins["Array"].container = "Array"
        n.pin("LoopBody", "exec", out=True)
        n.pin("Array Element", elem_cat, sub=elem_sub, out=True)
        n.pin("Array Index", "int", out=True)
        n.pin("Completed", "exec", out=True)
        self.link(array, n["Array"])
        return n

    # ---- casts and the player --------------------------------------------------------------------------------
    def cast(self, class_path, obj_pin, display_name, exec_from=(), comment="", x=0, y=0):
        """Exec cast. class_path: '/Script/Stalker2.PC' or a BP '..._C' path. display_name: the class's display name
        WITH spaces (output pin 'As<display_name>', e.g. 'Input Mapping Context'); a wrong name drops its links.
        Outputs then, CastFailed, As<display_name>, bSuccess."""
        target = (f"\"/Script/Engine.BlueprintGeneratedClass'{class_path}'\"" if class_path.endswith("_C")
                  else cls(class_path))
        c = self.exec_pins(self.node("K2Node_DynamicCast", x, y, comment, [f"TargetType={target}"]))
        c.pin("CastFailed", "exec", out=True)
        c.pin("Object", "object", sub=OBJ)
        c.pin("As" + display_name, "object", sub=target, out=True)
        c.pin("bSuccess", "bool", out=True)
        self.link(obj_pin, c["Object"])
        for e in exec_from:
            self.link(e, c["execute"])
        return c

    def player_pawn(self, index=0, x=0, y=0):
        """GetPlayerPawn(index). Returns the pawn pin."""
        n = self.lib_pure(GS, "GetPlayerPawn", [integer("PlayerIndex", index), ret(obj, PAWN)], x, y,
                          world_context=True)
        return n["ReturnValue"]

    def cast_player(self, exec_from=(), label="", x=0, y=0):
        """GetPlayerPawn -> Cast To PC. Output pin 'AsPC'."""
        return self.cast("/Script/Stalker2.PC", self.player_pawn(x=x - 300, y=y + 220), "PC", exec_from,
                         f"player ({label})" if label else "player", x, y)

    # ---- small pure helpers (return the result pin) ----------------------------------------------------------
    def is_valid(self, obj_pin, x=0, y=0):
        n = self.lib_pure(KSL, "IsValid", [obj("Object"), ret(boolean)], x, y)
        self.link(obj_pin, n["Object"])
        return n["ReturnValue"]

    def b_and(self, a, b, x=0, y=0):
        return self._bool2("BooleanAND", a, b, x, y)

    def b_or(self, a, b, x=0, y=0):
        return self._bool2("BooleanOR", a, b, x, y)

    def b_not(self, a, x=0, y=0):
        n = self.lib_pure(KML, "Not_PreBool", [boolean("A", "false"), ret(boolean)], x, y)
        self.link(a, n["A"])
        return n["ReturnValue"]

    def _bool2(self, fn, a, b, x, y):
        n = self.lib_pure(KML, fn, [boolean("A", "false"), boolean("B", "false"), ret(boolean)], x, y)
        self.link(a, n["A"])
        self.link(b, n["B"])
        return n["ReturnValue"]

    def math(self, fn, a, b=None, b_const="0.0", x=0, y=0):
        """Double math / compare: fn in Add_/Subtract_/Multiply_/Divide_DoubleDouble (real result) or
        Less_/Greater_/LessEqual_/GreaterEqual_/EqualEqual_DoubleDouble (bool result). b: pin or b_const literal."""
        is_cmp = fn.split("_")[0] in ("Less", "Greater", "LessEqual", "GreaterEqual", "EqualEqual", "NotEqual")
        n = self.lib_pure(KML, fn, [real("A", "0.0"), real("B", b_const), ret(boolean) if is_cmp else ret(real)], x, y)
        self.link(a, n["A"])
        self.link(b, n["B"])
        return n["ReturnValue"]

    def clamp(self, value, lo, hi, x=0, y=0):
        n = self.lib_pure(KML, "FClamp", [real("Value", "0.0"), real("Min", lo), real("Max", hi), ret(real)], x, y)
        self.link(value, n["Value"])
        return n["ReturnValue"]

    def name_eq(self, a, literal, x=0, y=0):
        n = self.lib_pure(KML, "EqualEqual_NameName", [name("A", "None"), name("B", literal), ret(boolean)], x, y)
        self.link(a, n["A"])
        return n["ReturnValue"]

    def game_time(self, x=0, y=0):
        """GetGameTimeInSeconds. Returns the double pin."""
        n = self.lib_pure(KSL, "GetGameTimeInSeconds", [ret(real)], x, y, world_context=True)
        return n["ReturnValue"]
