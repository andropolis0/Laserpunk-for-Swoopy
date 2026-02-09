import utils

class Crystals:
    dictionary = {} # Dictionary with keys as names and loaded crystal textures for values

    def loadCrystalTextures():
        Crystals.dictionary["quartz"]     = utils.loadScaledAsset("assets/crystals/quartz.png").convert_alpha()
        Crystals.dictionary["jade"]       = utils.loadScaledAsset("assets/crystals/jade.png").convert_alpha()
        Crystals.dictionary["topaz"]      = utils.loadScaledAsset("assets/crystals/topaz.png").convert_alpha()
        Crystals.dictionary["sapphire"]   = utils.loadScaledAsset("assets/crystals/sapphire.png").convert_alpha()
        Crystals.dictionary["ruby"]       = utils.loadScaledAsset("assets/crystals/ruby.png").convert_alpha()
        Crystals.dictionary["aquamarine"] = utils.loadScaledAsset("assets/crystals/aquamarine.png").convert_alpha()
        Crystals.dictionary["painite"]    = utils.loadScaledAsset("assets/crystals/painite.png").convert_alpha()
        Crystals.dictionary["celestine"]  = utils.loadScaledAsset("assets/crystals/celestine.png").convert_alpha()
        Crystals.dictionary["diamond"]    = utils.loadScaledAsset("assets/crystals/diamond.png").convert_alpha()

class Scraps:
    dictionary = {} # Dictionary with keys as names and loaded scrap textures for values

    def loadScrapTextures():
        Scraps.dictionary["brass"]     = utils.loadScaledAsset("assets/scraps/brass.png").convert_alpha()
        Scraps.dictionary["copper"]    = utils.loadScaledAsset("assets/scraps/copper.png").convert_alpha()
        Scraps.dictionary["lead"]      = utils.loadScaledAsset("assets/scraps/lead.png").convert_alpha()
        Scraps.dictionary["magnesium"] = utils.loadScaledAsset("assets/scraps/magnesium.png").convert_alpha()
        Scraps.dictionary["silver"]    = utils.loadScaledAsset("assets/scraps/silver.png").convert_alpha()
        Scraps.dictionary["tungsten"]  = utils.loadScaledAsset("assets/scraps/tungsten.png").convert_alpha()
        Scraps.dictionary["platinum"]  = utils.loadScaledAsset("assets/scraps/platinum.png").convert_alpha()
        Scraps.dictionary["cobalt"]    = utils.loadScaledAsset("assets/scraps/cobalt.png").convert_alpha()
        Scraps.dictionary["palladium"] = utils.loadScaledAsset("assets/scraps/palladium.png").convert_alpha()
        Scraps.dictionary["titanium"]  = utils.loadScaledAsset("assets/scraps/titanium.png").convert_alpha()
        Scraps.dictionary["gold"]      = utils.loadScaledAsset("assets/scraps/gold.png").convert_alpha()
        Scraps.dictionary["indium"]    = utils.loadScaledAsset("assets/scraps/indium.png").convert_alpha()
        Scraps.dictionary["adamatite"] = utils.loadScaledAsset("assets/scraps/adamatite.png").convert_alpha()
        Scraps.dictionary["luminite"]  = utils.loadScaledAsset("assets/scraps/luminite.png").convert_alpha()

class AccessCards:
    # NOTE: A single card is good for 2 rooms

    dictionary = [] # The indexes + 1 represent the level (its still a dictionary even though its a list)

    def loadCardTextures():
        AccessCards.dictionary.append(utils.loadScaledAsset("assets/cards/level_1.png").convert_alpha())
        AccessCards.dictionary.append(utils.loadScaledAsset("assets/cards/level_2.png").convert_alpha())
        AccessCards.dictionary.append(utils.loadScaledAsset("assets/cards/level_3.png").convert_alpha())
        AccessCards.dictionary.append(utils.loadScaledAsset("assets/cards/level_4.png").convert_alpha())
        AccessCards.dictionary.append(utils.loadScaledAsset("assets/cards/level_5.png").convert_alpha())
        AccessCards.dictionary.append(utils.loadScaledAsset("assets/cards/level_6.png").convert_alpha())
        AccessCards.dictionary.append(utils.loadScaledAsset("assets/cards/level_7.png").convert_alpha())
        AccessCards.dictionary.append(utils.loadScaledAsset("assets/cards/level_8.png").convert_alpha())
        AccessCards.dictionary.append(utils.loadScaledAsset("assets/cards/level_9.png").convert_alpha())

class Tiles:
    size = 72 # To be compatible with 4x scaling

    dictionary = {
        (255, 255, 255, 255): 0, # Blank
        (0,     0,   0, 255): 1, # Floor
        (38,  128, 130, 255): 2, # Entrance
        (92,    0,   0, 255): 3, # Wall

        # Laser redirectors
        (179, 102, 255, 255): 4.0, # Up-Left
        (179, 102, 205, 255): 4.1, # Down-Left
        (179, 102, 155, 255): 4.2, # Down-Right
        (179, 102, 105, 255): 4.3, # Up-Right

        # Laser recievers
        (162,   0,   0, 255): 5, # Regular
        (163,   62,  62, 255): 6, # Weak

        # Laser blockers
        (150,  92,  31, 255): 7.0, # Up
        (140,  92,  31, 255): 7.1, # Left
        (130,  92,  31, 255): 7.2, # Down
        (120,  92,  31, 255): 7.3, # Right

        # Laser splitters
        (128,   0, 255, 255): 8.0, # Up
        (128,   0, 205, 255): 8.1, # Left
        (128,   0, 155, 255): 8.2, # Down
        (128,   0, 105, 255): 8.3, # Right

        # Lockers
        (48,   96, 130, 255): 9.0, # Blue
        (48,  130,  89, 255): 9.1, # Green
        (199, 149,  21, 255): 9.2, # Reward

        (104, 104, 104, 255): 10, # Automaton

        (255, 180, 100, 255): 11 # Glass box
    }

    wall_tiles = {}
    floor_tiles = {}
    object_tiles = {}
    other_tiles = {}

    def loadTileTextures():
        # Quick utility function
        def loadTile(category, file_name, key, all_rotations=True, specific_rotations=[0, 90, 180, -90]):
            for rot in specific_rotations:
                loaded_image = utils.loadScaledAsset("assets/tiles/" + file_name + ".png", rotation=rot).convert_alpha()

                new_key = key
                if all_rotations: new_key = f"{key}_r{rot}" # Rotated tiles have different keys ("WLN" and "WLN_r90" for example)

                match category:
                    case "wall":   Tiles.wall_tiles[new_key]   = loaded_image
                    case "floor":  Tiles.floor_tiles[new_key]  = loaded_image
                    case "object": Tiles.object_tiles[new_key] = loaded_image
                    case "other":  Tiles.other_tiles[new_key]  = loaded_image

                # Only load the 0 rotation if default loading is needed
                if not all_rotations: return

        loadTile("wall", "wall_normal",          "WLN")
        loadTile("wall", "wall_outer_corner",    "WOC")
        loadTile("wall", "wall_inner_corner",    "WIC")
        loadTile("wall", "wall_door",            "WDO")
        loadTile("wall", "wall_door_active",     "WDA")
        loadTile("wall", "reciever",             "REC")
        loadTile("wall", "reciever_active",      "RAC")
        loadTile("wall", "weak_reciever",        "WRC")
        loadTile("wall", "weak_reciever_active", "WRA")

        loadTile("floor", "floor_1",        "FL1", False)
        loadTile("floor", "floor_2",        "FL2", False)
        loadTile("floor", "floor_1_broken", "F1B", False)
        loadTile("floor", "floor_2_broken", "F2B", False)

        loadTile("object", "redirector",         "RED")
        loadTile("object", "redirector_active",  "RDA")
        loadTile("object", "blocker",            "BLO")
        loadTile("object", "blocker_active",     "BLA")
        loadTile("object", "blocker_blocking",   "BLB")
        loadTile("object", "splitter",           "SPL")
        loadTile("object", "splitter_active",    "SPA")
        loadTile("object", "locker_1",           "LK1")
        loadTile("object", "locker_2",           "LK2")
        loadTile("object", "locker_3",           "LK3")
        loadTile("object", "glass_box_empty",    "GBE", False)
        loadTile("object", "glass_box_locked",   "GBL", False)
        loadTile("object", "glass_box_unlocked", "GBU", False)

        # Laser parts only need horizontal and vertical
        loadTile("other", "laser",     "LAS", specific_rotations=[0, 90])
        loadTile("other", "laser_bit", "LSB", specific_rotations=[0, 90])
