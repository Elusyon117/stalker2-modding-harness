"""Open a Blueprint in the tester's open editor and bring one of its graphs forward: the panel's Open graph button,
so the tester can click into the graph and press Ctrl+V.

    run through ue_exec with --arg ASSET=/MyMod/Runtime/BP_X --arg GRAPH=EventGraph

Prints OPENED <asset>, then GRAPH <name> when the graph tab was brought forward, or GRAPH_TAB <name> when only the
Blueprint opened (the tester clicks that tab: bringing a graph forward from Python is not certain in every build).
"""
import unreal

path = ARGS["ASSET"]
bp = unreal.load_asset(path)
if bp is None:
    raise RuntimeError("load failed: " + path)
editors = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
editors.open_editor_for_assets([bp])
print("OPENED " + path)

name = ARGS.get("GRAPH", "") or "EventGraph"
graph = None
try:
    graph = unreal.BlueprintEditorLibrary.find_graph(bp, name)
except Exception:  # noqa: BLE001 - not every build has find_graph
    graph = None
if graph is None and name == "EventGraph":
    try:
        graph = unreal.BlueprintEditorLibrary.find_event_graph(bp)
    except Exception:  # noqa: BLE001
        graph = None
focused = False
if graph is not None:
    try:
        focused = bool(editors.open_editor_for_assets([graph]))
    except Exception:  # noqa: BLE001
        focused = False
print(("GRAPH " if focused else "GRAPH_TAB ") + name)
