"""tools/pak/conflicts.py on made-up container listings (no kit needed).

    py -I tests/test_conflicts.py
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools", "pak"))
import conflicts as C  # noqa: E402

GD = "Stalker2/Content/GameLite/GameData/"
LISTING = {
    "zzzz_Mine_P.pak": {
        "Stalker2/Content/_Stalker_2/Player/AnimBP_Player.uasset": "AA",
        "Stalker2/Content/_Stalker_2/UI/W_Map.uasset": "11",
        GD + "CoreVariables.cfg": "C1",
        GD + "WeaponData/WeaponGeneralSetupPrototypes/Mine.cfg": "",
    },
    "OtherMod_P.pak": {
        "Stalker2/Content/_Stalker_2/Player/AnimBP_Player.uasset": "BB",
        "Stalker2/Content/_Stalker_2/UI/W_Map.uasset": "11",
        "Stalker2/Content/_Stalker_2/UI/W_Hud.uasset": "22",
        GD + "CoreVariables.cfg": "C2",
        GD + "WeaponData/WeaponGeneralSetupPrototypes/Other.cfg": "",
    },
    "Third_1_P.pak": {
        "Stalker2/Content/_Stalker_2/UI/W_Hud.uasset": "33",
    },
    "__text__": {
        f"zzzz_Mine_P.pak:{GD}WeaponData/WeaponGeneralSetupPrototypes/Mine.cfg":
            "GunAK74_ST : struct.begin {bpatch}\n   Damage = 10\n   Recoil : struct.begin {bpatch}\n      Up = 1\n"
            "   struct.end\nstruct.end\n",
        f"OtherMod_P.pak:{GD}WeaponData/WeaponGeneralSetupPrototypes/Other.cfg":
            "GunAK74_ST : struct.begin {bpatch}\n   Recoil : struct.begin\n      Side = 2\n   struct.end\n"
            "   Weight = 3\nstruct.end\n",
    },
}


class Lister(C.Lister):
    def __init__(self):  # noqa: D401 (no cache file, the listing above)
        self.fixed, self.cache, self.dirty, self.cache_path = LISTING, {}, False, ""


class Conflicts(unittest.TestCase):
    def report(self, only_yours=False):
        mods = C.gather([("yours: Mine", ["x/zzzz_Mine_P.pak"], True),
                         ("installed", ["m/OtherMod_P.pak", "m/Third_1_P.pak"], False)])
        return C.scan(mods, Lister(), only_yours)

    def find(self, rep, what):
        return [c for c in rep["conflicts"] if what in c["what"]]

    def test_priority_and_names(self):
        self.assertEqual(C.priority("x_P.pak"), 103)
        self.assertEqual(C.priority("x_1_P.utoc"), 203)
        self.assertEqual(C.priority("MyModStalker2-Windows-NewContent.pak"), 3)
        self.assertEqual(C.mod_name_of("zzzz_MyMod_P"), "MyMod")
        self.assertEqual(C.mod_name_of("MyModStalker2-Windows-OverrideContent"), "MyMod")

    def test_cfg_targets(self):
        self.assertEqual(C.cfg_target(GD + "CoreVariables.cfg_patch_X"), ("patch", "corevariables.cfg"))
        self.assertEqual(C.cfg_target(GD + "ObjPrototypes/ObjPrototypes.cfg_patch_X.cfg"), ("patch", "objprototypes.cfg"))
        self.assertEqual(C.cfg_target(GD + "A/BPrototypes/Mine.cfg"), ("patch", "a/bprototypes.cfg"))
        self.assertEqual(C.cfg_target(GD + "CoreVariables.cfg"), ("file", "corevariables.cfg"))
        self.assertIsNone(C.cfg_target("Stalker2/Content/X.uasset"))

    def test_asset_conflicts(self):
        rep = self.report()
        anim = self.find(rep, "animbp_player")[0]
        self.assertEqual(anim["verdict"], "risky")  # heavily shared asset
        self.assertEqual(anim["mods"][0]["name"], "Mine")  # zzzz_ ties at 103 and sorts after OtherMod
        self.assertTrue(anim["isYours"])
        self.assertEqual(self.find(rep, "w_map")[0]["verdict"], "same")
        hud = self.find(rep, "w_hud")[0]
        self.assertEqual(hud["verdict"], "wins")
        self.assertEqual(hud["mods"][0]["name"], "Third")  # _1_P beats _P
        self.assertFalse(hud["isYours"])

    def test_cfg_conflicts(self):
        rep = self.report()
        self.assertEqual(self.find(rep, "corevariables.cfg")[0]["kind"], "cfg-file")
        fields = [c["what"] for c in rep["conflicts"] if c["kind"] == "cfg"]
        # Other's Recoil has no {bpatch}: it replaces the node, so it overlaps Mine's Recoil.Up; Damage and Weight don't
        self.assertEqual(len(fields), 1)
        self.assertIn("Recoil", fields[0])

    def test_only_yours(self):
        rep = self.report(only_yours=True)
        self.assertTrue(all(c["isYours"] for c in rep["conflicts"]))
        self.assertFalse(self.find(rep, "w_hud"))


if __name__ == "__main__":
    unittest.main()
