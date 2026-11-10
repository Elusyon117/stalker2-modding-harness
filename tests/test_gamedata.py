"""Offline tests for the game data index (tools/data): a small fake kit, no Zone Kit needed.

    py -I tests/test_gamedata.py
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "data"))
import cfg_parse as C  # noqa: E402
import gamedata as G  # noqa: E402

FILES = {
    "Stalker2/Content/GameLite/GameData/ItemPrototypes.cfg": """
[0] : struct.begin
   SID = ItemBase
   Weight = 1.0
   Cost = 10
   Icon = None
struct.end
""",
    "Stalker2/Content/GameLite/GameData/ItemPrototypes/ConsumablePrototypes.cfg": """
Bread : struct.begin {refurl=../ItemPrototypes.cfg; refkey=[0]}
   SID = Bread
   Cost = 25
   Effects : struct.begin
      [0] = Hunger
      [1] = Calm
   struct.end
struct.end
BigBread : struct.begin {refkey=Bread}
   SID = BigBread
   Weight = 2.0
struct.end
""",
    "Stalker2/Content/GameLite/GameData/WeaponData/WeaponGeneralSetupPrototypes.cfg": """
// a comment line
GunAK74_ST : struct.begin
   SID = GunAK74_ST
   WeaponReloadTimePerAttachment : struct.begin
      [0] : struct.begin
         TacticalReloadTimeMultiplier = 1.0
         FullReloadTimeMultiplier = 1.0
      struct.end
   struct.end
   Mesh = StaticMesh'/Game/Weapons/AK.AK'  // trailing comment
struct.end
""",
    "Stalker2/Content/GameLite/GameData/CoreVariables.cfg": """
CoreVariables : struct.begin
   SID = CoreVariables
   TalkDistance = 300
struct.end
""",
    "Stalker2/Content/GameLite/GameData/SpawnActorPrototypes/WorldMap_WP/ABC123.cfg": """
ABC123 : struct.begin
   SID = ABC123
   SpawnType = ESpawnType::Item
   ItemSID = Bread
struct.end
""",
    "Stalker2/Content/GameLite/DLCGameData/DLC1/WeaponData/WeaponGeneralSetupPrototypes.cfg": """
GunAK74_ST : struct.begin
   SID = GunAK74_ST
struct.end
""",
    "Stalker2/Content/TextToolBackup/TextDatabase.json": json.dumps(
        {"Items": [{"SID": "sid_items_Bread_name", "en": "Bread"}, {"SID": "sid_character_Sidor", "en": "Sidorovich"}]}),
    # the mod (kit plugin folder)
    "Stalker2/Mods/MyMod/Content/GameLite/GameData/WeaponData/WeaponGeneralSetupPrototypes/MyMod.cfg": """
GunAK74_ST : struct.begin {bpatch}
   WeaponReloadTimePerAttachment : struct.begin {bpatch}
      [0] : struct.begin {bpatch}
         TacticalReloadTimeMultiplier = 0.75
      struct.end
   struct.end
struct.end
""",
    "Stalker2/Mods/MyMod/Content/GameLite/GameData/CoreVariables.cfg_patch_MyMod": """
CoreVariables : struct.begin {bpatch}
   TalkDistance = 450
struct.end
""",
    "Stalker2/Mods/MyMod/Content/GameLite/ModGameData/MyMod/ItemPrototypes/MyItems.cfg": """
MyBread : struct.begin {refurl=../../../GameData/ItemPrototypes/ConsumablePrototypes.cfg; refkey=Bread}
   SID = MyBread
   Cost = 99
struct.end
""",
}


class Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.kit = os.path.join(cls.tmp, "kit")
        for rel, text in FILES.items():
            p = os.path.join(cls.kit, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(text.lstrip("\n"))
        cls.db = os.path.join(cls.tmp, "index.sqlite")
        with contextlib.redirect_stdout(io.StringIO()):
            G.build(cls.kit, cls.db)
        cls.mod_content = os.path.join(cls.kit, "Stalker2", "Mods", "MyMod", "Content")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def ix(self):
        return G.Index(self.db, self.kit, "MyMod", self.mod_content)

    def run_cli(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            G.main(["--kit", self.kit, "--db", self.db, "--mod", "MyMod", "--mod-content", self.mod_content, *args])
        return out.getvalue()


class TestParse(unittest.TestCase):
    def test_parse_and_dump_roundtrip(self):
        root = C.parse(FILES["Stalker2/Content/GameLite/GameData/WeaponData/WeaponGeneralSetupPrototypes.cfg"])
        gun = root.get("GunAK74_ST")
        self.assertEqual(gun.get("Mesh"), "StaticMesh'/Game/Weapons/AK.AK'")
        self.assertEqual(C.lookup(gun, C.split_path("WeaponReloadTimePerAttachment[0].TacticalReloadTimeMultiplier")),
                         "1.0")
        again = C.parse(C.dump(gun)).get("GunAK74_ST")
        self.assertEqual(C.dump(again), C.dump(gun))

    def test_patch_semantics(self):
        base = C.parse("R : struct.begin\n A = 1\n B = 2\n C : struct.begin\n X = 1\n struct.end\n"
                       " L : struct.begin\n [0] = a\n [1] = b\n struct.end\nstruct.end").get("R")
        bp = C.parse("R : struct.begin {bpatch}\n A = 9\n C : struct.begin {bpatch}\n Y = 2\n struct.end\n"
                     " L : struct.begin {bpatch}\n [0] : removenode\n struct.end\n New = 3\nstruct.end").get("R")
        out = C.apply_patch(base, bp)
        self.assertEqual((out.get("A"), out.get("B"), out.get("New")), ("9", "2", "3"))
        self.assertEqual((out.get("C").get("X"), out.get("C").get("Y")), ("1", "2"))
        self.assertIsNone(out.get("L").get("[0]"))
        replace = C.parse("R : struct.begin\n Z = 1\nstruct.end").get("R")  # no {bpatch}: whole node replaced
        self.assertEqual([k for k, _ in C.apply_patch(base, replace).items], ["Z"])

    def test_build_patch(self):
        text = C.build_patch("GunAK74_ST", ["WeaponReloadTimePerAttachment[0].TacticalReloadTimeMultiplier=0.75"],
                             ["PreinstalledUpgrades.[0]"])
        node = C.parse(text).get("GunAK74_ST")
        self.assertTrue(node.bpatch)
        self.assertTrue(node.get("WeaponReloadTimePerAttachment").get("[0]").bpatch)
        self.assertIs(node.get("PreinstalledUpgrades").get("[0]"), C.REMOVED)

    def test_classify(self):
        known = {k.lower(): k for k in ("GameLite/GameData/ItemPrototypes.cfg",
                                        "GameLite/GameData/ItemPrototypes/WeaponPrototypes.cfg",
                                        "GameLite/GameData/WeaponData/WeaponGeneralSetupPrototypes.cfg",
                                        "GameLite/GameData/CoreVariables.cfg")}
        cl = G.classify
        self.assertEqual(cl("GameLite/GameData/CoreVariables.cfg_patch_X", known),
                         ("GameLite/GameData/CoreVariables.cfg", True))
        self.assertEqual(cl("GameLite/GameData/ItemPrototypes/WeaponPrototypes.cfg", known)[0],
                         "GameLite/GameData/ItemPrototypes/WeaponPrototypes.cfg")
        self.assertEqual(cl("GameLite/GameData/ItemPrototypes/WeaponPrototypes/MyMod.cfg", known)[0],
                         "GameLite/GameData/ItemPrototypes/WeaponPrototypes.cfg")
        self.assertEqual(cl("GameLite/GameData/WeaponData/WeaponGeneralSetupPrototypes/"
                            "WeaponGeneralSetupPrototypes_patch_X.cfg", known)[0],
                         "GameLite/GameData/WeaponData/WeaponGeneralSetupPrototypes.cfg")
        self.assertEqual(cl("GameLite/GameData/SpawnActorPrototypes/WorldMap_WP/A.cfg", known)[0],
                         "GameLite/GameData/SpawnActorPrototypes.cfg")


class TestIndex(Fixture):
    def test_inheritance_across_files(self):
        ix = self.ix()
        row = G.pick(ix.lookup("BigBread"), "BigBread")
        node, chain = ix.resolve(row)
        self.assertEqual([c["name"] for c in chain], ["BigBread", "Bread", "[0]"])
        self.assertEqual((node.get("Weight"), node.get("Cost"), node.get("Icon")), ("2.0", "25", "None"))
        self.assertEqual(node.get("Effects").get("[1]"), "Calm")

    def test_mod_new_item_inherits_from_game(self):
        ix = self.ix()
        node, chain = ix.resolve(G.pick(ix.lookup("MyBread"), "MyBread"))
        self.assertEqual([c["name"] for c in chain], ["MyBread", "Bread", "[0]"])
        self.assertEqual(node.get("Cost"), "99")

    def test_mod_patches_found_and_applied(self):
        out = self.run_cli("find", "GunAK74_ST")
        self.assertIn("TacticalReloadTimeMultiplier = 0.75", out)
        self.assertIn("FullReloadTimeMultiplier = 1.0", out)
        self.assertIn("DLC copies exist", out)
        self.assertIn("WeaponData/WeaponGeneralSetupPrototypes/MyMod.cfg", out)
        raw = self.run_cli("find", "GunAK74_ST", "--raw")
        self.assertIn("TacticalReloadTimeMultiplier = 1.0", raw)

    def test_patch_paths(self):
        ix = self.ix()
        sp = lambda k: G.suggest_patch(G.pick(ix.lookup(k), k), "MyMod")  # noqa: E731
        self.assertEqual(sp("CoreVariables"), "GameLite/GameData/CoreVariables.cfg_patch_MyMod")
        self.assertEqual(sp("Bread"), "GameLite/GameData/ItemPrototypes/ConsumablePrototypes/MyMod.cfg")
        self.assertEqual(sp("ABC123"), "GameLite/GameData/SpawnActorPrototypes/WorldMap_WP/ABC123_MyMod.cfg")
        self.assertIn("TalkDistance = 450", self.run_cli("find", "CoreVariables"))

    def test_search_kids_texts_patch(self):
        self.assertIn("BigBread", self.run_cli("search", "bread"))
        self.assertIn("Sidorovich", self.run_cli("search", "sidor"))
        self.assertIn('"Bread"', self.run_cli("find", "Bread"))
        kids = self.run_cli("kids", "Bread")
        self.assertIn("BigBread", kids)
        self.assertIn("MyBread", kids)
        p = self.run_cli("patch", "GunAK74_ST", "--set",
                         "WeaponReloadTimePerAttachment[0].TacticalReloadTimeMultipler=0.5")
        self.assertIn("WARNING", p)  # misspelt field is flagged
        ok = self.run_cli("patch", "GunAK74_ST", "--set",
                          "WeaponReloadTimePerAttachment[0].TacticalReloadTimeMultiplier=0.5")
        self.assertNotIn("WARNING", ok)
        self.assertIn("{bpatch}", ok)

    def run_json(self, *args):
        return json.loads(self.run_cli("--json", *args))

    def test_json_search_and_kinds(self):
        r = self.run_json("search", "bread")
        keys = [x["key"] for x in r["results"]]
        self.assertIn("BigBread", keys)
        self.assertIn("MyBread", keys)
        bread = next(x for x in r["results"] if x["key"] == "Bread")
        self.assertEqual((bread["kind"], bread["game"]), ("items", "Bread"))
        ak = self.run_json("search", "ak74", "--kind", "weapons")["results"]
        self.assertTrue(ak and all(x["kind"] == "weapons" for x in ak))
        self.assertTrue(next(x for x in ak if x["key"] == "GunAK74_ST")["isMine"])
        self.assertEqual(self.run_json("search", "ak74", "--kind", "npcs")["results"], [])

    def test_json_find_fields_and_origins(self):
        f = self.run_json("find", "BigBread")
        self.assertEqual([c["name"] for c in f["chain"]], ["Bread", "[0]"])
        fields = {x["path"]: x for x in f["fields"]}
        self.assertEqual((fields["Weight"]["value"], fields["Weight"]["origin"]), ("2.0", "own"))
        self.assertEqual((fields["Cost"]["value"], fields["Cost"]["origin"]), ("25", "inherited"))
        self.assertTrue(fields["Effects"]["isStruct"])
        gun = {x["path"]: x for x in self.run_json("find", "GunAK74_ST")["fields"]}
        t = gun["WeaponReloadTimePerAttachment.[0].TacticalReloadTimeMultiplier"]
        self.assertEqual((t["value"], t["origin"]), ("0.75", "mine"))
        self.assertEqual(gun["WeaponReloadTimePerAttachment.[0].FullReloadTimeMultiplier"]["origin"], "own")
        whole = self.run_json("find", "GunAK74_ST")
        self.assertTrue(whole["hasDlc"])
        self.assertEqual(whole["patchFile"], "GameLite/GameData/WeaponData/WeaponGeneralSetupPrototypes/MyMod.cfg")

    def test_json_patch_write_merges(self):
        tmp = tempfile.mkdtemp()
        try:
            content = os.path.join(tmp, "Content")
            shutil.copytree(self.mod_content, content)

            def patch(*args):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    G.main(["--kit", self.kit, "--db", self.db, "--mod", "MyMod", "--mod-content", content, "--json",
                            "patch", *args])
                return json.loads(out.getvalue())
            # a typo is refused, nothing written
            with self.assertRaises(SystemExit):
                patch("GunAK74_ST", "--set", "WeaponReloadTimePerAttachment[0].TacticalReloadTimeMultipler=0.5",
                      "--write")
            r = patch("GunAK74_ST", "--set", "WeaponReloadTimePerAttachment[0].FullReloadTimeMultiplier=0.8", "--write")
            self.assertTrue(r["written"] and r["exists"])
            node = C.parse(C.read_text(r["target"])).get("GunAK74_ST")
            first = node.get("WeaponReloadTimePerAttachment").get("[0]")
            self.assertEqual((first.get("TacticalReloadTimeMultiplier"), first.get("FullReloadTimeMultiplier")),
                             ("0.75", "0.8"))  # the earlier change is kept
            new = patch("Bread", "--set", "Cost=40", "--write")
            self.assertFalse(new["exists"])
            self.assertTrue(new["target"].replace("\\", "/").endswith("ItemPrototypes/ConsumablePrototypes/MyMod.cfg"))
            self.assertEqual(C.parse(C.read_text(new["target"])).get("Bread").get("Cost"), "40")
            again = patch("BigBread", "--set", "Cost=50", "--write")  # a second struct in the same patch file
            self.assertEqual(again["target"], new["target"])
            both = C.parse(C.read_text(again["target"]))
            self.assertEqual((both.get("Bread").get("Cost"), both.get("BigBread").get("Cost")), ("40", "50"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_json_status(self):
        self.assertFalse(self.run_json("status")["stale"])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            G.main(["--db", os.path.join(self.tmp, "none.sqlite"), "--json", "status"])
        self.assertFalse(json.loads(out.getvalue())["exists"])

    def test_status_and_missing(self):
        self.assertIn("up to date", self.run_cli("status"))
        with self.assertRaises(SystemExit):
            self.run_cli("find", "NoSuchThing")


if __name__ == "__main__":
    unittest.main()
