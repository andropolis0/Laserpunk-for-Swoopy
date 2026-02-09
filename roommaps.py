from engine import LevelRoom, InterfaceItem
from dictionaries import *

# NOTE: The map classes must always have their connections accessible

class Room1Map(LevelRoom):
    connections = {
        "first_floor":     (0,  (18, 29)),
        "room_1_5":        (-2, (37, 23)),
        "to_be_continued": (-1, (0,  14)),
        "room_4":          (5,  (37, 8 ))
    }

    def __init__(self):
        super().__init__(
            "assets/tilesheets/room_1.png",
            Room1Map.connections,
            { # Laser
                "start": (18, 28),
                "direction": "right"
            },
            { # Locker items (NOTE: 2 lead are here so the player can craft the lvl 2 access card, can be removed when expanding to level 2)
                (23, 30): ["brass", "copper", "", ""],
                (36, 4):  ["copper", "", "brass", ""],
                (29, 1):  ["", "brass", "copper", ""],
                (16, 1):  ["", "copper", "lead", "brass"],
                (18, 15): ["", "copper", "", "brass"],
                (1, 10):  ["", "lead", "brass", "copper"]
            }
        )

class Room1_5Map(LevelRoom):
    connections = {
        "room_1": (0, (0, 11))
    }

    def __init__(self):
        super().__init__(
            "assets/tilesheets/room_1_5.png",
            Room1_5Map.connections,
            { # Laser
                "start": (0, 12),
                "direction": "right"
            },
            { # Locker items
                (1, 1):   ["brass", "copper", "", ""],
                (9, 5):   ["copper", "", "brass", ""],
                (13, 8):  ["", "brass", "copper", ""],
                (21, 8):  ["", "copper", "brass", "brass"],
                (13, 11): ["", "copper", "", "brass"],
                (5, 21):  ["", "copper", "brass", "copper"]
            },
            { # Glass box
                (17, 7): InterfaceItem("gold", "", Scraps.dictionary["lead"])
            }
        )
