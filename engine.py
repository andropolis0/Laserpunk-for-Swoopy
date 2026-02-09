import pygame
import globals as glb
import settings
import random
import utils
import math
import scene
import data
from dictionaries import *

# NOTE in case this game is to be expanded: When a room passes "to_be_continued" as the next room, it pushes a new ToBeContinued() scene
# the logic is only defined in:
# RoomTransition > update() (marked),
# RoomManager > moveTo() (additional condition)

class GameEngine:
    def __init__(self):
        # Play again variables (have to be here in order to not get reset during transition)
        self.trans_to_new_game = False
        self.play_again_trans = pygame.Surface((glb.screen_width, glb.screen_height), pygame.SRCALPHA)
        self.play_again_trans.fill((0, 0, 0))
        self.play_again_trans.set_alpha(0)

    def gameStart(self):
        # Rendering layers
        self.layer_1     = pygame.Surface((glb.screen_width, glb.screen_height), pygame.SRCALPHA) # The closest layer to the view (for UI and transitions)
        self.layer_2     = pygame.Surface((glb.screen_width, glb.screen_height), pygame.SRCALPHA) # The layer 2nd closest to the view (for the player and entities)
        self.layer_3     = pygame.Surface((glb.screen_width, glb.screen_height)                 ) # The layer 3rd closest to the view (for the map, objects and dropped items)
        self.final_layer = pygame.Surface((glb.screen_width, glb.screen_height)                 ) # The layer for combining all of the other ones (DO NOT DRAW ON IT)

        def playAgain():
            self.trans_to_new_game = True
            self.play_again_trans.set_alpha(5) # Kick off the transition

        def goToMainMenu():
            glb.sound_engine.switchMusic("main_theme", 0.8, 2000, 500, 12)

            glb.scene_manager.changeScene(glb.main_menu)

        def backToGame():
            self.paused = False

        # Pause menu variables
        self.paused = False
        self.pause_menu = pygame.Surface((glb.screen_width, glb.screen_height), pygame.SRCALPHA)
        self.pause_menu.fill((10, 10, 10, 104))
        self.pause_menu.set_alpha(0)
        self.pause_menu_BA = utils.Button(((glb.screen_width - 204) // 2, 300), "assets/ui/back_button.png", "assets/ui/back_button_hovered.png", backToGame)
        self.pause_menu_MM = utils.Button(((glb.screen_width - 204) // 2, 400), "assets/ui/main_menu_button.png", "assets/ui/main_menu_button_hovered.png", goToMainMenu)

        paused_font = utils.SmallFont((225, 225, 225, 255))
        paused_text = paused_font.render("PAUSED")
        paused_text = pygame.transform.scale(paused_text, (paused_text.get_width() * 2, paused_text.get_height() * 2))
        self.pause_menu.blit(paused_text, ((glb.screen_width - paused_text.get_width()) // 2, 170))

        # Game over variables
        self.game_over = False
        self.death_menu = pygame.Surface((glb.screen_width, glb.screen_height), pygame.SRCALPHA)
        self.death_menu.fill((124, 0, 0, 100))
        self.death_menu.set_alpha(0)
        self.death_menu_PA = utils.Button(((glb.screen_width - 200) // 2, 300), "assets/ui/play_again_button.png", "assets/ui/play_again_button_hovered.png", playAgain)
        self.death_menu_MM = utils.Button(((glb.screen_width - 204) // 2, 400), "assets/ui/main_menu_button.png", "assets/ui/main_menu_button_hovered.png", goToMainMenu)

        you_died_font = utils.SmallFont((255, 0, 0, 255))
        you_died_text = you_died_font.render("YOU DIED")
        you_died_text = pygame.transform.scale(you_died_text, (you_died_text.get_width() * 2, you_died_text.get_height() * 2))
        self.death_menu.blit(you_died_text, ((glb.screen_width - you_died_text.get_width()) // 2, 170))

        # Blood vingette
        self.blood_vingette = utils.loadScaledAsset("assets/ui/blood_vingette.png").convert_alpha()
        self.blood_vingette.set_alpha(0)

        # Managers
        self.om = ObjectivesManager()
        self.rm = RoomManager()

        # Utility for animating typing text on the screen
        self.typing_utility = utils.Typer((255, 255, 255))

        # The cinematic transition at the start, and to look at the bots when they enter the ResourceRoom
        self.cinematic_camera = True

        self.player = Player(640, 1120, self.rm.current_room_map) # The player start coords in the FirstFloorMap
        self.camera = Camera(
            -(self.rm.current_room_map.map_image.get_width() // 2 - glb.screen_width // 2), # Center the camera to the middle of the current map
            -300
        )
        self.camera.setSize(*self.rm.current_room_map.map_image.get_size())

        # So the camera doesnt bump in to the wall
        self.camera_custom_target = CollidableEntity(640, 950, utils.loadScaledAsset("assets/player/player_up.png"), self.rm.current_room_map)

        # Scoring system:
        # - crafting something = 10
        # - collecting a crystal = 20
        # - killing an automaton = 20
        # - turning on the laser/crystal machine = 40
        # - unlocking a golden locker = 80
        # - unlocking a glass box = 100
        # - playing without hints = 100
        # - completing a regular level = 100

        # Score
        self.score = 0
        self.score_time_boost = 9800 # Starts at 9800 and decreases each frame

        # Start playing the music
        if data.DBData.player_name == glb.names[0]:
            glb.sound_engine.playMusic("test")
        elif data.DBData.player_name == glb.names[1]:
            glb.sound_engine.playMusic("u_music", 0.9)

        # Optional hints stuff
        if settings.hints:
            if settings.movement[0] == pygame.K_w: self.keys_hint = utils.loadScaledAsset("assets/ui/keys.png")
            else:                                  self.keys_hint = utils.loadScaledAsset("assets/ui/keys_arrows.png")

            self.keys_hint_current_alpha = 0
            self.keys_hint_target_alpha = 0 # It gets set to 255 later
            self.keys_hint.set_alpha(self.keys_hint_current_alpha)

            self.keys_hint_pos = ((glb.screen_width - self.keys_hint.get_width()) // 2, 120)
            self.keys_hint_timer = 150

        # Function that is set in SaveSelect if the player is opening an opened world, to apply the previous progress
        if hasattr(self, "to_apply"):
            self.to_apply()

    def input(self, input_stream):
        if not self.trans_to_new_game:
            if self.game_over:
                self.death_menu_PA.input(input_stream)
                self.death_menu_MM.input(input_stream)

            else:
                # Pause menu
                if input_stream.keyboard.isKeyPressed(pygame.K_ESCAPE):
                    self.paused = not self.paused

                if self.paused:
                    self.pause_menu_BA.input(input_stream)
                    self.pause_menu_MM.input(input_stream)

                elif not self.rm.room_transition.active and not self.cinematic_camera:
                    self.player.input(input_stream) # If anything is fucked up try switching deez
                    self.om.input(input_stream)
                    self.rm.input(input_stream)

                    # ----- CHEATS ----- #

                    # Get promoted
                    if (input_stream.keyboard.isKeyDown(pygame.K_g) and
                        input_stream.keyboard.isKeyDown(pygame.K_p) and
                        input_stream.keyboard.isKeyPressed(pygame.K_m)):
                        if self.player.current_access_lvl != 9:
                            self.player.current_access_lvl = 9

                    # Get weapon_luminite
                    if (input_stream.keyboard.isKeyDown(pygame.K_g) and
                        input_stream.keyboard.isKeyDown(pygame.K_b) and
                        input_stream.keyboard.isKeyPressed(pygame.K_l)):
                        if self.player.inventory.weapon_slot == None or self.player.inventory.weapon_slot.name == "stick":
                            self.player.inventory.aquireNewWeapon("weapon_luminite")

                    # Skip beginning
                    if (input_stream.keyboard.isKeyDown(pygame.K_k) and
                        input_stream.keyboard.isKeyDown(pygame.K_b) and
                        input_stream.keyboard.isKeyPressed(pygame.K_g)):

                        # NOTE: The big rock will remain, the automatons will still follow the player in the first_floor room

                        # Also has to create the resource room to unlock crafting
                        if "resource_room" not in self.rm.active_rooms:
                            self.rm.active_rooms["resource_room"] = self.rm.rooms["resource_room"]["map"]()

                        if not self.player.turned_on_crystal_machine:
                            self.player.turned_on_crystal_machine = True

                        laser_machine = self.rm.active_rooms["first_floor"].laser_machine

                        if not laser_machine.mirror_repaired:
                            laser_machine.repaired = True
                            laser_machine.mirror = BaseObject(1100, 1520, "assets/objects/mirror.png") # Show the mirror is repaired
                            laser_machine.mirror_repaired = True
                            laser_machine.perma_laser_on = True

    def update(self):
        # Not using self.trans_to_new_game because it will be set to False mid transition
        if self.play_again_trans.get_alpha() > 0:
            # Transition opacity logic
            if self.trans_to_new_game:
                self.play_again_trans.set_alpha(self.play_again_trans.get_alpha() + 5)

                if self.play_again_trans.get_alpha() == 255: # When the screen is fully covered, start a new game
                    self.trans_to_new_game = False
                    self.gameStart()

            else:
                self.play_again_trans.set_alpha(self.play_again_trans.get_alpha() - 1.5)

        # This will become available because it will be set to False mid transition
        if not self.trans_to_new_game:
            if not self.game_over:
                if not self.paused:
                    # Slowly hide the paused overlay if it's visible
                    if self.pause_menu.get_alpha() > 0:
                        self.pause_menu.set_alpha(self.pause_menu.get_alpha() - 15)

                    # Decrease the score time boost (stops at 0)
                    if self.score_time_boost > 0:
                        self.score_time_boost -= 1

                    self.om.update()
                    self.rm.update()
                    self.player.update()

                    # Check if the player is dead
                    if self.player.health < 1:
                        self.game_over = True

                    # If the typing utiliy is supposed to be typing, update it
                    if self.typing_utility.active:
                        self.typing_utility.update()

                    # This is used at the start of the game
                    if self.cinematic_camera:
                        if int(self.camera.y) == -600: # -600 is the final Y position of the camera at the start (only works with the cinematic fade transition in scenes)
                            self.cinematic_camera = False

                        self.camera.update(self.camera_custom_target, True, 0.99, 0.01)

                    else:
                        self.camera.update(self.player)

                        # Optional hints stuff
                        if settings.hints:
                            if not self.player.has_moved:
                                # Ticking the timer
                                if self.keys_hint_timer != 0:
                                    self.keys_hint_timer -= 1

                                    if self.keys_hint_timer == 0:
                                        self.keys_hint_target_alpha = 255 # To start the transition

                            # If the player has moved, but hasnt moved before (the keys UI is shown)
                            elif self.keys_hint_timer == 0 and self.keys_hint_target_alpha != 0:
                                self.keys_hint_target_alpha = 0 # To start the transition

                # Slowly show the paused overlay if it's not visible
                else:
                    if self.pause_menu.get_alpha() < 255:
                        self.pause_menu.set_alpha(self.pause_menu.get_alpha() + 15)

            # Slowly show the death screen if it's not visible
            else:
                if self.death_menu.get_alpha() < 255:
                    self.death_menu.set_alpha(self.death_menu.get_alpha() + 15)

    def draw(self, screen):
        # Prepare layer_1 and layer_2 for drawing (layer_3 doesn't need this because it is getting refreshed with the map)
        self.layer_1.fill((0, 0, 0, 0))
        self.layer_2.fill((0, 0, 0, 0))

        # Draw the player sprite, healthbar and staminabar
        self.layer_2.blit(self.player.image, self.camera.apply(self.player.rect))
        self.layer_1.blit(self.player.healthbar, (100, 20))
        pygame.draw.rect(self.layer_1, (0, 93, 93), (104, 48, self.player.stamina, 8))

        self.player.inventory.draw(self.layer_1)
        self.player.facility_map.draw(self.layer_1)

        # Draw the player weapon slash if slashing
        if 0 < self.player.weapon_cooldown < 12:
            self.layer_2.blit(self.player.current_slash_image, self.camera.apply(self.player.current_slash_rect))

        # Optional hints stuff
        if settings.hints:
            if self.keys_hint_timer == 0:
                # Transition
                if self.keys_hint_current_alpha != self.keys_hint_target_alpha and not self.paused:
                    da = self.keys_hint_target_alpha - self.keys_hint_current_alpha

                    # 0.2 is for easing in/out effect, 0.05 is for general speed
                    self.keys_hint_current_alpha += (da * 0.2) * 0.2

                    # Snap when really close to target
                    if abs(da) < 1:
                        self.keys_hint_current_alpha = self.keys_hint_target_alpha

                    self.keys_hint.set_alpha(self.keys_hint_current_alpha)

                # Blit only if its gonna be visible
                if 0 < self.keys_hint_current_alpha:
                    self.layer_1.blit(self.keys_hint, self.keys_hint_pos)

        # Draw managers
        self.om.draw(self.layer_1)
        self.rm.draw([self.layer_1, self.layer_2, self.layer_3])

        # If the typing utiliy is supposed to be typing, make it draw it
        if self.typing_utility.active:
            self.typing_utility.draw(self.layer_1)

        # Draw the blood vingette
        if self.player.health < 100:
            self.layer_2.blit(self.blood_vingette, (0, 0)) # Has to be blitted on to layer_2 in order to be compatible with pause_menu

        # Draw the paused overlay if needed or if it's still transitioning from visible to invisible
        if self.paused or self.pause_menu.get_alpha() > 0:
            self.pause_menu.blit(self.pause_menu_BA.current_image, self.pause_menu_BA.pos)
            self.pause_menu.blit(self.pause_menu_MM.current_image, self.pause_menu_MM.pos)
            self.layer_1.blit(self.pause_menu, (0, 0))

        # Draw the game over screen if needed (doesn't have to transition from visible back to invisible)
        if self.game_over:
            # Draw the buttons on the death menu srface instead of the layer
            self.death_menu.blit(self.death_menu_PA.current_image, self.death_menu_PA.pos)
            self.death_menu.blit(self.death_menu_MM.current_image, self.death_menu_MM.pos)
            self.layer_1.blit(self.death_menu, (0, 0))

        # Not using self.trans_to_new_game because it will be set to False mid transition
        if self.play_again_trans.get_alpha() > 0:
            self.layer_1.blit(self.play_again_trans, (0, 0))

        # Combine all of the layers in to the final one
        self.final_layer.blit(self.layer_3, (0, 0))
        self.final_layer.blit(self.layer_2, (0, 0))
        self.final_layer.blit(self.layer_1, (0, 0))

        screen.blit(self.final_layer, (0, 0))

class RoomManager:
    class RoomTransition:
        def __init__(self):
            self.active = False
            self.surf = pygame.Surface((glb.screen_width, glb.screen_height), pygame.SRCALPHA)

        def activate(self, prev_room, next_room):
            self.active = True
            self.percentage = 0
            self.prev_room = prev_room
            self.next_room = next_room
            self.wait = 0

        def update(self):
            if self.percentage < 101:
                # Wait a little before opening back up
                if self.percentage == 50:
                    self.wait += 1

                    if self.wait == 25:
                        self.wait = 0
                        self.percentage = 51

                else:
                    self.percentage += 1

                # The transition is halfway complete (dark screen before opening back up)
                if self.percentage == 50 and self.wait == 1:

                    # === TO BE CONTINUED LOGIC === #
                    if self.next_room == "to_be_continued":
                        # Finish the transition early
                        self.percentage = 101
                        self.active = False
                        self.percentage = 0
                        self.prev_room = ""
                        self.next_room = ""
                        self.wait = 0

                        glb.scene_manager.changeScene(scene.ToBeContinued(), 100, 0.2, 50) # 100 skips the fade out

                        return

                    # Regular room entering
                    glb.engine.rm.current_room_name = self.next_room

                    # Get the map and instantiate it, if the room is not active yet
                    if self.next_room not in glb.engine.rm.active_rooms:
                        glb.engine.rm.active_rooms[self.next_room] = glb.engine.rm.rooms[self.next_room]["map"]()

                    glb.engine.rm.current_room_map = glb.engine.rm.active_rooms[self.next_room]
                    glb.engine.rm.current_room_map.onEnter(self.prev_room)

                    # Update player and camera attributes
                    glb.engine.player.setLimits(glb.engine.rm.current_room_map.map_rect, glb.engine.rm.current_room_map.map_borders)
                    glb.engine.camera.setSize(glb.engine.rm.current_room_map.map_image.get_size()[0], glb.engine.rm.current_room_map.map_image.get_size()[1])

                    # Small fix: If the player is sprinting when leaving, stop sprinting when entering
                    if glb.engine.player.sprinting:
                        glb.engine.player.sprinting = False
                        glb.engine.player.player_speed = 4

                    # Another small fix: If the player has moving on when leaving, flip it and stop the sound
                    if glb.engine.player.moving:
                        glb.engine.player.moving = False

                        glb.sound_engine.stopSound("footsteps")

                # If the transition is at the end finish it
                elif self.percentage == 101:
                    self.active = False
                    self.percentage = 0
                    self.prev_room = ""
                    self.next_room = ""
                    self.wait = 0

        def draw(self, layer):
            self.surf.fill((0, 0, 0, 0)) # Clear the surface

            linear_progress = 1 - abs(self.percentage - 50) / 50
            progress = linear_progress ** 3 # Speeds up near the edges, slows at the middle
            current_length = int((glb.screen_width + glb.screen_height) * progress)

            # Draw the transition shape (black will be kept, white will be cut out)
            pygame.draw.polygon(self.surf, (0, 0, 0), [
                (0, glb.screen_height),                  # Bottom left corner
                (0, glb.screen_height - current_length), # Expanding side (upward)
                (current_length, glb.screen_height),     # Expanding side (rightward)
            ])

            layer.blit(self.surf, (0, 0))

    def __init__(self):
        # The variable 'rooms' contains info on every possible room in the game
        # The variable 'active_rooms' stores only the active room class instances
        self.rooms = {
            "first_floor":   {"map": FirstFloorMap,   "connections": ["resource_room", "room_1"]},
            "resource_room": {"map": ResourceRoomMap, "connections": ["first_floor"]},
            "room_1":        {"map": Room1Map,        "connections": list(Room1Map.connections.keys())},
            "room_1_5":      {"map": Room1_5Map,      "connections": list(Room1_5Map.connections.keys())}
        }
        self.active_rooms = {}

        # Variables for keeping track of rooms
        self.current_room_map = self.rooms["first_floor"]["map"]()
        self.current_room_name = "first_floor"
        self.active_rooms[self.current_room_name] = self.current_room_map

        self.room_transition = self.RoomTransition()

    def moveTo(self, new_room_name):
        # Check if the 'new_room' is connected to the current room or if it is to be continued
        if new_room_name in self.rooms[self.current_room_name]["connections"] or new_room_name == "to_be_continued":
            # Close any currently opened PaperItems
            for item in self.current_room_map.dropped_items:
                if type(item) == PaperItem and item.current_y == item.opened_y:
                    item.target_y = item.closed_y

                    # Important - call the callback function
                    if item.hide_callback is not None:
                        item.hide_callback()

            self.room_transition.activate(self.current_room_name, new_room_name)

        else:
            print(f"Cant move to {new_room_name} from {self.current_room_name}")

    def input(self, input_stream):
        self.current_room_map.input(input_stream)

        # Call input for all of the objects (that can do that) in the current room
        for object in self.current_room_map.objects:
            # Check if its one the three  main interaction stations
            if (type(object) is LaserMachine or type(object) is CrystalMachine or type(object) is TinkerTable):
                object.input(input_stream)

            elif isinstance(object, TileObject):
                # These need additional interaction condition checking
                if type(object) is Redirector or type(object) is Blocker:
                    if self.current_room_map.interactable_redirectors:
                        object.input(input_stream)

                # This one too
                elif type(object) is GlassBox:
                    if object.unlocked and object.item != None: object.input(input_stream)

                else:
                    object.input(input_stream)

        # Call input for all of the dropped items (that can do that) in the current room
        for item in self.current_room_map.dropped_items:
            if isinstance(item, ClickableItem): # Check if its a ClickableItem or subclass of it
                item.input(input_stream)

    def update(self):
        self.current_room_map.update()

        # Only when the crystal machine is turned on, allow background processing for crystal growing
        if glb.engine.player.turned_on_crystal_machine: self.active_rooms["resource_room"].crystal_machine.growingCrystals()

        if self.room_transition.active: self.room_transition.update()

        # Call the update() for all of the entities in the current room
        for entity in self.current_room_map.entities:
            entity.update()

    def draw(self, layers):
        # For optimization
        visible_rect = pygame.Rect(-(glb.engine.camera.rect.x), -(glb.engine.camera.rect.y), glb.screen_width, glb.screen_height)

        layers[2].blit(self.current_room_map.map_image, (0, 0), visible_rect) # Only blit it where its visible

        # Draw the static objects of the current room
        for object in self.current_room_map.objects:
            # Only blit the object's image if its in the view
            if visible_rect.colliderect(object.rect):
                layers[2].blit(object.image, glb.engine.camera.apply(object.rect)) # Blit to layer_3

            if type(object) is LaserMachine or type(object) is TinkerTable or type(object) is CrystalMachine:
                object.draw(layers) # Just pass all layers (for lasers / crafting UI and ground)

            elif type(object) is Locker or type(object) is GlassBox:
                object.draw(layers[0]) # Blit to layer_1 (for drawing UI elements)

        # Draw the entities of the current room
        for entity in self.current_room_map.entities:
            # Only blit the enemy if its in the view
            if visible_rect.colliderect(entity.rect):
                layers[1].blit(entity.image, glb.engine.camera.apply(entity.rect)) # Blit to layer_2

        # Draw the dropped items of the current room
        for item in self.current_room_map.dropped_items:
            # Only blit the item if its in the view
            if visible_rect.colliderect(item.rect):
                layers[2].blit(item.image, glb.engine.camera.apply(item.rect)) # Blit to layer_3

            if type(item) is PaperItem:
                item.draw(layers[0]) # Blit to layer_1 (for drawing the paper UI element)

        # If the current room is a subclass of LevelRoom also blit its lasers
        if isinstance(self.current_room_map, LevelRoom):
            layers[2].blit(self.current_room_map.laser_surf, (0, 0), visible_rect) # Same as the map_image

        if self.room_transition.active: self.room_transition.draw(layers[0]) # Blit to layer_1

class ObjectivesManager:
    # NOTE: setObjective and clearObjective can still be called when hints are off, just nothing will happen

    possible_objectives = [
        "Look around",
        "Read the \nblueprint",
        "Turn on the \ncrystal \nmachine",
        "Turn on the \nlaser machine",
        "Collect the \nscraps and \nthe stick",
        "Use the \nscraps at the \ncrystal \nmachine",
        "Repair the \nmirror",
        "Redirect the \nlaser and \ncraft a high \nenough access \ncard"
    ]

    def __init__(self):
        self.panel_image = utils.loadScaledAsset("assets/ui/objective.png")
        self.hovered_panel_image = utils.loadScaledAsset("assets/ui/objective_hovered.png")
        self.current_panel_image = self.panel_image

        # Animation variables
        self.panel_opened_x = glb.screen_width - self.panel_image.get_width()
        self.panel_closed_x = glb.screen_width - self.panel_image.get_width() + 248
        self.panel_current_x = self.panel_closed_x
        self.panel_target_x = None

        self.button_rect = pygame.Rect(self.panel_closed_x, 104, 52, 48)

        # Surface to display text
        self.font = utils.SmallFont((255, 255, 255, 255))
        self.current_objective_text = pygame.Surface((240, 240), pygame.SRCALPHA)
        self.current_objective_text.blit(self.font.render(ObjectivesManager.possible_objectives[0]), (16, 8))

        # This is just for collision detection, always stays open
        self.panel_rect = pygame.Rect(self.panel_opened_x, 104, *self.panel_image.get_size())

        self.time_opened = 300 # When an objective is set this starts going down

        if data.DBData.player_name == glb.names[0]:
            ObjectivesManager.possible_objectives = ["".join(chr(x) for x in [100, 97, 106, 32, 109, 105, 32, 100, 114, 111, 103, 111]) for _ in range(len(ObjectivesManager.possible_objectives))]

    def setObjective(self, objective_text):
        self.clearObjective()

        self.current_objective_text.blit(self.font.render(objective_text), (16, 8))

        # If the panel was closed before, open it for a limited time
        if self.button_rect.x == self.panel_closed_x:
            # Open the panel
            self.panel_target_x = self.panel_opened_x

            # Start the opened timer
            self.time_opened = 299

    def clearObjective(self):
        self.current_objective_text.fill((0, 0, 0, 0))

    def input(self, input_stream):
        if settings.hints:
            if self.button_rect.collidepoint(input_stream.mouse.getPosition()):
                if self.current_panel_image != self.hovered_panel_image:
                    self.current_panel_image = self.hovered_panel_image

                # Opening and closing the panel
                if input_stream.mouse.isButtonPressed(0):
                    if self.button_rect.x == self.panel_closed_x:
                        self.panel_target_x = self.panel_opened_x

                    elif self.button_rect.x == self.panel_opened_x:
                        self.panel_target_x = self.panel_closed_x

                        # If the timer was still going down when the panel was closed, reset it
                        if self.time_opened != 300: self.time_opened = 300

            else:
                if (self.panel_current_x == self.panel_opened_x and input_stream.mouse.isButtonPressed(0) and
                    not self.panel_rect.collidepoint(input_stream.mouse.getPosition())):
                    self.panel_target_x = self.panel_closed_x

                    # If the timer was still going down when the panel was closed, reset it
                    if self.time_opened != 300: self.time_opened = 300

                if self.current_panel_image != self.panel_image:
                    self.current_panel_image = self.panel_image

    def update(self):
        if settings.hints:
            # New objective set
            if self.time_opened < 300:
                self.time_opened -= 1

                if self.time_opened == 0:
                    self.panel_target_x = self.panel_closed_x

                    self.time_opened = 300

    def draw(self, layer_1):
        if settings.hints:
            # If it has not yet reached the target x
            if self.panel_target_x is not None and self.panel_current_x != self.panel_target_x:
                dx = self.panel_target_x - self.panel_current_x

                # 0.2 is for easing in/out effect, 0.5 is for general speed
                self.panel_current_x += (dx * 0.2) * 0.5

                # Apply the virtual pos
                self.button_rect.x = self.panel_current_x

                # When really close, just snap
                if abs(dx) < 1:
                    self.panel_current_x = self.panel_target_x

                    # Apply the virtual pos
                    self.button_rect.x = self.panel_current_x

                    # Clear the target x
                    self.panel_target_x = None

            layer_1.blit(self.current_panel_image, self.button_rect.topleft)
            layer_1.blit(self.current_objective_text, (self.button_rect.x + 56, self.button_rect.y + 44))

            if self.time_opened != 300:
                visual_length = 240 / 300 * self.time_opened

                pygame.draw.rect(layer_1, (255, 5, 5), pygame.Rect(self.button_rect.x + 56, self.button_rect.y + 200, visual_length, 4))

class Camera:
    def __init__(self, pos_x, pos_y):
        self.rect = pygame.Rect(0, 0, 0, 0)

        # Track the camera's precise current position
        self.x = pos_x
        self.y = pos_y

        self.shake_timer = 0

    def setSize(self, width, height):
        self.rect.size = (width, height)

    def apply(self, entity_rect):
        return entity_rect.move(self.rect.topleft)

    def update(self, target, smoothing = True, speed_start = 0.92, speed_end = 0.08):
        calculated_x = -target.rect.x + glb.screen_width  / 2 - target.rect.width  / 2
        calculated_y = -target.rect.y + glb.screen_height / 2 - target.rect.height / 2

        self.x = self.x * speed_start + calculated_x * speed_end if smoothing else calculated_x
        self.y = self.y * speed_start + calculated_y * speed_end if smoothing else calculated_y

        # Limit scrolling to map size
        x = min(0, int(self.x)) # Left
        y = min(0, int(self.y)) # Top
        x = max(-(self.rect.width - glb.screen_width), x) # Right
        y = max(-(self.rect.height - glb.screen_height), y) # Bottom

        # Add turbulance if the camera has to shake
        if self.shake_timer > 0:
            self.shake_timer -= 1

            x += random.randint(-5, 5)
            y += random.randint(-5, 5)

        # Update the rects position
        self.rect.topleft = (x, y)

class CollidableEntity(pygame.sprite.Sprite):
    def __init__(self, start_x, start_y, image, current_map):
        super().__init__()

        self.collision_mask = pygame.mask.from_surface(image)

        self.rect = image.get_rect()
        self.x = self.rect.x = start_x
        self.y = self.rect.y = start_y

        # glb.engine.rm cannot be accesses this early, so current_map needs to be passed in manually
        # 0 = Top, 1 = Left, 2 = Bottom, 3 = Right
        self.limits = [
            current_map.map_rect.top    + current_map.map_borders[0],
            current_map.map_rect.left   + current_map.map_borders[1],
            current_map.map_rect.bottom - current_map.map_borders[2],
            current_map.map_rect.right  - current_map.map_borders[3]
        ]

    def setLimits(self, map_rect, borders):
        # Calculate the actual movement limits using borders (mainly used by the player when entering rooms)
        self.limits = [
            map_rect.top    + borders[0],
            map_rect.left   + borders[1],
            map_rect.bottom - borders[2],
            map_rect.right  - borders[3]
        ]

    def collideCheck(self, vx, vy, speed = 4):
        self.x += vx
        self.y += vy

        # Update position
        self.rect.topleft = (self.x, self.y)

        # Check if the current room is a tiled room (LevelRoom)
        if isinstance(glb.engine.rm.current_room_map, LevelRoom): # Check if its a subclass of LevelRoom
            # Go through all tiles and check if the entity would be standing on a wall/door if the move was applied
            for i, row in enumerate(glb.engine.rm.current_room_map.tilemap):
                for j, tile in enumerate(row):
                    # If the current tile is a door or a wall or a reciever
                    if tile in (2, 3, 5, 6):
                        x = j * Tiles.size + glb.engine.rm.current_room_map.map_margin_x / 2
                        y = i * Tiles.size + glb.engine.rm.current_room_map.map_margin_y / 2

                        while self.rect.colliderect((x, y, Tiles.size, Tiles.size)):
                            # Go back half a pixel until they don't collide anymore (because of the players speed 6 (goes in to half pixels))
                            self.x += -2 if vx > 0 else 2 if vx < 0 else 0
                            self.y += -2 if vy > 0 else 2 if vy < 0 else 0

                            # Update the position
                            self.rect.topleft = (self.x, self.y)

        # If its a regular room, check with limits
        else:
            # Wall collision detection
            if self.rect.right > self.limits[3]: # Right wall collision
                self.x = self.limits[3] - self.rect.width
                vx = 0
            elif self.rect.left < self.limits[1]: # Left wall collision
                self.x = self.limits[1]
                vx = 0
            if self.rect.bottom > self.limits[2]: # Bottom wall collision
                self.y = self.limits[2] - self.rect.height
                vy = 0
            elif self.rect.top < self.limits[0]: # Top wall collision
                self.y = self.limits[0]
                vy = 0

        # Static object collision detection
        for obj in glb.engine.rm.current_room_map.objects:
            # Checking with mask overlap because it offers pixel perfect collisions
            while self.collision_mask.overlap(obj.mask, (obj.rect.x - self.rect.x, obj.rect.y - self.rect.y)):
                # Go back half a pixel until they don't collide anymore (because of the players speed 6 (goes in to half pixels))
                self.x += -2 if vx > 0 else 2 if vx < 0 else 0
                self.y += -2 if vy > 0 else 2 if vy < 0 else 0

                # Update position
                self.rect.topleft = (self.x, self.y)

        # Update the position one more time
        self.rect.topleft = (self.x, self.y)

class Player(CollidableEntity):
    def __init__(self, start_x, start_y, current_map):
        # Player attributes
        self.read_instructions = False
        self.turned_on_crystal_machine = False
        self.knows_to_fix_machine = False
        self.knows_to_fix_mirror = False

        self.current_access_lvl = 0

        # Internal stuff
        self.health = 100
        self.heal_timer = 0
        self.moving = False
        self.stamina = 200
        self.sprinting = False
        self.inventory = Inventory()
        self.facility_map = FacilityMap()

        if settings.hints:
            self.has_moved = False

        # Weapon stuff
        self.weapon_cooldown = 0

        slash_image = utils.loadScaledAsset("assets/player/slash.png").convert_alpha()
        self.slash_images = [
            pygame.transform.rotate(slash_image, 180),
            pygame.transform.rotate(slash_image, -90),
            slash_image, # The image is already pointed downwards by default
            pygame.transform.rotate(slash_image, 90)
        ]
        self.current_slash_image = self.slash_images[0]
        self.current_slash_rect = pygame.Rect(0, 0, 0, 0)

        # Visual stuff
        self.healthbar_image = utils.loadScaledAsset("assets/ui/healthbar.png").convert_alpha()
        self.healthbar = pygame.Surface(self.healthbar_image.get_size(), pygame.SRCALPHA)

        self.looks = [
            utils.loadScaledAsset("assets/player/player_up.png"),
            utils.loadScaledAsset("assets/player/player_left.png"),
            utils.loadScaledAsset("assets/player/player_down.png"),
            utils.loadScaledAsset("assets/player/player_right.png")
        ]

        self.image = self.looks[0]
        self.direction = 1 # 1 = Up, 2 = Left, 3 = Down, 4 = Right
        self.player_speed = 4

        # Init the CollidableEntity
        super().__init__(start_x, start_y, self.image, current_map)

    def changeXY(self, new_x = None, new_y = None):
        if new_x != None: self.x = self.rect.x = new_x
        if new_y != None: self.y = self.rect.y = new_y

    def move(self, direction):
        vx = vy = 0

        # Check if the player turned in a new direction
        if direction != self.direction:
            self.direction = direction

            # Refresh the looks
            self.image = self.looks[direction-1]
            self.rect.size = self.image.get_size()
            self.collision_mask = pygame.mask.from_surface(self.image)

        # 1 = Up, 2 = Left, 3 = Down, 4 = Right
        match direction:
            case 1: vy = -self.player_speed
            case 2: vx = -self.player_speed
            case 3: vy =  self.player_speed
            case 4: vx =  self.player_speed

        self.collideCheck(vx, vy, self.player_speed)

    def hurt(self, by):
        if by == "automaton":
            self.health -= 10

            # Wind up the shake
            glb.engine.camera.shake_timer = 10

        elif by == "laser":
            # This will happen every tick the player is in the laser path
            self.health -= 1

            # Wind up the shake
            glb.engine.camera.shake_timer = 1

        # Update the blood vingette
        glb.engine.blood_vingette.set_alpha(255 - self.health * 2.5)

    def input(self, input_stream):
        self.inventory.input(input_stream)
        self.facility_map.input(input_stream)

        # If moving and sprinting, use up stamina
        if (input_stream.keyboard.isKeyDown(settings.movement[0]) or
            input_stream.keyboard.isKeyDown(settings.movement[1]) or
            input_stream.keyboard.isKeyDown(settings.movement[2]) or
            input_stream.keyboard.isKeyDown(settings.movement[3])):

            if settings.hints and not self.has_moved:
                self.has_moved = True

            prev_x = self.x
            prev_y = self.y

            # Movement
            if input_stream.keyboard.isKeyDown(settings.movement[0]): self.move(1)
            if input_stream.keyboard.isKeyDown(settings.movement[1]): self.move(2)
            if input_stream.keyboard.isKeyDown(settings.movement[2]): self.move(3)
            if input_stream.keyboard.isKeyDown(settings.movement[3]): self.move(4)

            # Footsteps logic
            if self.x == prev_x and self.y == prev_y:
                if self.moving:
                    self.moving = False

                    glb.sound_engine.stopSound("footsteps")

            # If the player has actually moved, play the footsteps sound
            elif not self.moving:
                self.moving = True

                glb.sound_engine.playSound("footsteps", 0.8, True)

            # Stamina usage
            if self.sprinting and self.stamina > 0:
                self.stamina -= 1

                # Stop sprinting once the player doesn't have any stamina
                if self.stamina == 0:
                    self.sprinting = False
                    self.player_speed = 4

        # If the player stopped moving
        else:
            if self.moving:
                self.moving = False

                # Also stop the sound
                glb.sound_engine.stopSound("footsteps")

            # If stopped moving, but still has sprinting on, turn it off
            if self.sprinting:
                self.sprinting = False
                self.player_speed = 4

        # If not sprinting, heal stamina
        if self.stamina < 200 and not self.sprinting:
            self.stamina += 1

        # Toggle sprinting
        if input_stream.keyboard.isKeyPressed(settings.sprint_key):
            if not self.sprinting:
                self.sprinting = True
                self.player_speed = 6

            else:
                self.sprinting = False
                self.player_speed = 4

        current_room = glb.engine.rm.current_room_map

        # Check if the player is getting hit by the laser in a LevelRoom
        if isinstance(current_room, LevelRoom): # Check if its a subclass of LevelRoom
            if self.collision_mask.overlap(current_room.laser_surf_mask, (0 - self.rect.x, 0 - self.rect.y)):
                self.hurt("laser")

        # If not, check if it is the first floor and the mirror on the laser machine has been repaired
        elif glb.engine.rm.current_room_name == "first_floor" and current_room.laser_machine.mirror_repaired:
            laser_machine = current_room.laser_machine

            if self.collision_mask.overlap(laser_machine.perma_laser_mask, (laser_machine.perma_laser_rect.x - self.rect.x, laser_machine.perma_laser_rect.y - self.rect.y)):
                self.hurt("laser")

        # Attacking
        if (input_stream.mouse.isButtonPressed(0) and self.inventory.weapon_slot != None and
            self.inventory.weapon_slot.name != "stick" and self.weapon_cooldown == 0
            ):

            # Check if the cursor is not over the inventory or any of the dropped items or any machines
            current_room = glb.engine.rm.current_room_map
            mouse_pos = input_stream.mouse.getPosition()
            inflated_player_rect = self.rect.inflate(96, 96)
            engine_camera = glb.engine.camera

            def collidesMouse(rect, in_range=True):
                if in_range: return engine_camera.apply(rect).collidepoint(mouse_pos) and inflated_player_rect.colliderect(rect)
                else:        return engine_camera.apply(rect).collidepoint(mouse_pos)

            # End the function if the player clicked anywhere that uses the mouse pointer

            # Inventory UI collision check (dependant on Inventory pos and item dimensions)
            if pygame.Rect(10, 10, 64, 64 + 74 * len(self.inventory.slots)).collidepoint(mouse_pos): return

            # Objective button UI collision check
            if glb.engine.om.button_rect.collidepoint(mouse_pos): return

            # Check for close enough items
            if any(collidesMouse(item.rect) for item in current_room.dropped_items): return

            # Room-specific checking
            if glb.engine.rm.current_room_name == "first_floor":
                if collidesMouse(current_room.laser_machine.console.rect): return
                if collidesMouse(current_room.laser_machine.mirror.rect): return

            elif glb.engine.rm.current_room_name == "resource_room":
                if collidesMouse(current_room.tinker_table.tinker_place.rect): return
                if collidesMouse(current_room.crystal_machine.console.rect): return
                if collidesMouse(current_room.crystal_machine.crystal_collection.rect): return
                if collidesMouse(current_room.crystal_machine.scrap_place.rect): return

            elif isinstance(current_room, LevelRoom):
                for object in current_room.objects:
                    # Check if its a Redirector or Blocker that the player can interact with
                    if type(object) is Redirector or type(object) is Blocker:
                        if current_room.interactable_redirectors and collidesMouse(object.rect): return

                    # Check if its an *unlocked* or opened Locker
                    elif type(object) is Locker:
                        if object.unlocked and collidesMouse(object.rect): return
                        if object.opened and collidesMouse(object.opened_ui_rect, False): return

                    # Check if its an *unlocked* glass box and not empty
                    elif type(object) is GlassBox:
                        if object.unlocked and object.item != None and collidesMouse(object.rect): return

                    # Generally check if its a TileObject
                    elif isinstance(object, TileObject):
                        if collidesMouse(object.rect): return

            # If none of the previous conditions ended the function: Actually attack

            self.weapon_cooldown = 1 # Start the cooldown

            # Rotate the player in the direction the cursor is closer to
            applied_rect = glb.engine.camera.apply(self.rect)

            # Mouse offset from player
            dx = mouse_pos[0] - applied_rect.center[0]
            dy = mouse_pos[1] - applied_rect.center[1]

            # Check which axis dominates
            if abs(dx) > abs(dy): # Horizontal direction is stronger
                if   dx > 0: self.direction = 4
                elif dx < 0: self.direction = 2

            else: # Vertical direction is stronger
                if   dy > 0: self.direction = 3
                elif dy < 0: self.direction = 1

            # Refresh the looks based on the new direction
            self.image = self.looks[self.direction-1]
            self.rect.size = self.image.get_size()
            self.collision_mask = pygame.mask.from_surface(self.image)

            # Visual and damaging stuff
            self.current_slash_image = self.slash_images[self.direction - 1]
            self.current_slash_rect = self.current_slash_image.get_rect()

            # Correct the position
            match self.direction:
                case 1: self.current_slash_rect.topleft = (
                    self.rect.x - (self.current_slash_rect.width - self.rect.width) // 2,
                    self.rect.y - self.current_slash_rect.height + 15
                ) # Up
                
                case 3: self.current_slash_rect.topleft = (
                    self.rect.x - (self.current_slash_rect.width - self.rect.width) // 2,
                    self.rect.bottom - 15
                ) # Down

                case 2: self.current_slash_rect.topleft = (
                    self.rect.x - self.current_slash_rect.width + 15,
                    self.rect.y - (self.current_slash_rect.height - self.rect.height) // 2
                ) # Left

                case 4: self.current_slash_rect.topleft = (
                    self.rect.right - 15,
                    self.rect.y - (self.current_slash_rect.height - self.rect.height) // 2
                ) # Right

            # Play the sound
            glb.sound_engine.playSound(f"slash_{random.randint(1, 4)}", 0.3)

            # Check if any entities are touching the tip of dis weapon
            for enemy in glb.engine.rm.current_room_map.entities:
                if enemy.rect.colliderect(self.current_slash_rect):
                    enemy.damage(self.inventory.weapon_slot.name)

    def update(self):
        # If the player is hurt, slowly heal over time
        if self.health < 100:
            if self.heal_timer == 200: # Heal every 200 frames
                self.health += 10

                # Just in case the "+= 10" overshoots 100
                if self.health > 100: self.health = 100

                self.heal_timer = 0 # Reset the timer for the next round of healing
            
            self.heal_timer += 1

        # Attack cooldown logic
        if self.weapon_cooldown > 0:
            if self.weapon_cooldown < 40:
                self.weapon_cooldown += 1
            else:
                self.weapon_cooldown = 0

        # Assemble the healthbar
        self.healthbar.fill((0, 0, 0, 0)) # Refresh

        pygame.draw.rect(self.healthbar, (147, 0, 21), (32, 8, self.health // 10 * 20 + (self.health // 10 - 1) * 4, 12))

        self.healthbar.blit(self.healthbar_image, (0, 0))

class Inventory:
    def __init__(self):
        self.slots = []
        self.slot_amounts = [] # List of amounts of individual items in slots (slots[2] = InventoryItem --> slot_amounts[2] = 7)
        self.slot_amounts_font = utils.SmallFont((255, 255, 255, 255))
        self.current_item_idx = -1 # When its -1 no items are selected

        self.weapon_slot = None
        self.weapon_slot_indicator = pygame.Surface((16, 16), pygame.SRCALPHA)
        self.weapon_slot_cooldown_color = None

        self.access_display = utils.loadScaledAsset("assets/ui/access_display.png").convert_alpha() # For displaying the player's current highest access card

    def aquireNewWeapon(self, weapon_name):
        match weapon_name:
            case "weapon":          self.weapon_slot_cooldown_color = (200, 175, 108)
            case "weapon_silver":   self.weapon_slot_cooldown_color = (175, 190, 200)
            case "weapon_cobalt":   self.weapon_slot_cooldown_color = ( 15, 105, 185)
            case "weapon_gold":     self.weapon_slot_cooldown_color = (200, 180,  75)
            case "weapon_luminite": self.weapon_slot_cooldown_color = (255, 255, 255) # When its white it gets rendered as green and pink
            case _:                 self.weapon_slot_cooldown_color = (  0,   0,   0) # Just in case

        self.weapon_slot = InterfaceItem(weapon_name, f"assets/items/{weapon_name}.png")

    def collect(self, item):
        already_in_slots_idx = -1

        glb.sound_engine.playSound("collect", 0.8)

        for index, slot_item in enumerate(self.slots):
            if slot_item.name == item.name:
                already_in_slots_idx = index
                break

        # If the item type is already in slots, dont add it, but increase the correct slot_amounts number
        if already_in_slots_idx != -1:
            self.slot_amounts[already_in_slots_idx] += 1

        else:
            self.slots.append(item)
            self.slot_amounts.append(1)

    def discard(self, item=None, pos=None):
        if item == None and pos == None:
            raise Exception("Neither pos nor item were provided!")

        else:
            index_to_remove = -1

            if item != None: index_to_remove = self.slots.index(item)
            elif pos != None: index_to_remove = pos

            # If theres more than one of the item, dont remove it, but decrease the correct slot_amounts number
            if self.slot_amounts[index_to_remove] > 1:
                self.slot_amounts[index_to_remove] -= 1

            else:
                self.slots.pop(index_to_remove)
                self.slot_amounts.pop(index_to_remove)

                # The item that was removed was before the selected item, the selection has to move up
                if index_to_remove < self.current_item_idx:
                    self.current_item_idx -= 1

                # If the item was selected or it was the last one in slots, reset the current index
                if index_to_remove == self.current_item_idx or len(self.slots) == 0: self.current_item_idx = -1

    def input(self, input_stream):
        mouse_pos = input_stream.mouse.getPosition()

        for index, item in enumerate(self.slots):
            # Mouse hover and click selection
            if pygame.Rect(10, 64 + 10 + 10 + index * (item.fixed_dim + 10), item.fixed_dim, item.fixed_dim).collidepoint(mouse_pos):
                if input_stream.mouse.isButtonPressed(0):
                    # Deselect if it has been previously selected
                    if self.current_item_idx == index:
                        item.final_image = item.selected_image
                        self.current_item_idx = -1

                    # Select if it has not been previously selected
                    else:
                        item.final_image = item.chosen_image
                        self.current_item_idx = index

                elif item.final_image != item.selected_image and self.current_item_idx != index:
                    item.final_image = item.selected_image

            elif item.final_image != item.normal_image and self.current_item_idx != index:
                item.final_image = item.normal_image

            # Number key support for slot selection
            if input_stream.keyboard.isKeyPressed(pygame.K_1 + index):
                # Deselect if it has been previously selected
                if self.current_item_idx == index:
                    item.final_image = item.normal_image
                    self.current_item_idx = -1

                # Select if it has not been previously selected
                else:
                    item.final_image = item.chosen_image
                    self.current_item_idx = index

    def drawWeaponIndicatorPath(self, color, rem, path_one, path_two):
        for sx, sy, dx, dy, seg_len in [path_one, path_two]:
            if rem <= 0: break

            draw_len = min(seg_len, rem)

            pygame.draw.line(
                self.weapon_slot_indicator,
                color,
                (round(sx), round(sy)),
                (round(sx + dx * draw_len), round(sy + dy * draw_len))
            )

            rem -= draw_len

            # Break, if the full segment isnt drawn
            if draw_len < seg_len: break
            # Otherwise continue to the next segment (next segment's start is its defined sx, sy)

    def draw(self, layer_1):
        # Draw an empty slot if the player has a too low access level
        if glb.engine.player.current_access_lvl == 0:
            pygame.draw.rect(layer_1, (42, 24, 36), (glb.screen_width - 22 * 4, 32, 64, 40))

        else:
            layer_1.blit(AccessCards.dictionary[glb.engine.player.current_access_lvl - 1], (glb.screen_width - 22 * 4, 20))

        layer_1.blit(self.access_display, (glb.screen_width - 26 * 4, 20))

        if self.weapon_slot != None:
            layer_1.blit(self.weapon_slot.normal_image, (10, 10))

            # Only draw this when the cooldown is active
            if glb.engine.player.weapon_cooldown != 0:
                # Refresh the indicator surface
                self.weapon_slot_indicator.fill((0, 0, 0, 0))

                # Drawing cooldown indicator
                x = y = 0
                w = h = 15

                # Clamp the clamped cooldown and multiply by the total length of both lines to get the amount to draw on each path
                remaining_len = max(0.0, min(1.0, max(0.0, min(1.0, glb.engine.player.weapon_cooldown / 40.0)))) * (w + h)

                # TL -> TR -> BR
                self.drawWeaponIndicatorPath(
                    self.weapon_slot_cooldown_color if self.weapon_slot.name != "weapon_luminite" else (165, 100, 125), # Pink
                    remaining_len,
                    (x,     y, 1, 0, w), # top (left -> right)
                    (x + w, y, 0, 1, h), # right (top -> bottom)
                )

                # BR -> BL -> TL
                self.drawWeaponIndicatorPath(
                    self.weapon_slot_cooldown_color if self.weapon_slot.name != "weapon_luminite" else (45, 105, 75), # Green
                    remaining_len,
                    (x + w, y + h, -1,  0, w), # bottom (right -> left)
                    (x,     y + h,  0, -1, h), # left (bottom -> top)
                )

                # Blit the scaled up indicator, because line thickness in pygame is aids
                layer_1.blit(pygame.transform.scale(self.weapon_slot_indicator, (64, 64)), (10, 10))

        # Display the inventory items and their amounts
        for index, item in enumerate(self.slots):
            item_pos = (10, 64 + 10 + 10 + index * (item.fixed_dim + 10))

            layer_1.blit(item.final_image, item_pos)

            # If theres only one, theres no need to display the amount
            if self.slot_amounts[index] > 1:
                amount_render = self.slot_amounts_font.render(str(self.slot_amounts[index]))

                layer_1.blit(amount_render, (item_pos[0] + item.fixed_dim - amount_render.get_width(), item_pos[1] + item.fixed_dim - amount_render.get_height() - 4))

class Automaton(CollidableEntity):
    def __init__(self, start_x, start_y, current_map):
        # Internal stuff
        self.health = 100
        self.attack_cooldown = 0 # So the player doesn't insta die when touching automaton
        self.freeze_place = False # To be able to make automatons stay still at will
        self.walking_to = None # For when the automaton is needed at a cerain place
        self.dmg_last = 0

        # Visual stuff
        if data.DBData.player_name == glb.names[0]:
            version = random.choice([1, 2])

            self.dmg_image = pygame.image.load(f"assets/ui/unused/hurtaumaton{version}.png").convert_alpha()
            self.nrm_image = pygame.image.load(f"assets/ui/unused/automaton{version}.png").convert_alpha()

        else:
            self.dmg_image = utils.loadScaledAsset("assets/automaton/hurt.png").convert_alpha()
            self.nrm_image = utils.loadScaledAsset("assets/automaton/normal.png").convert_alpha()

        self.image = self.nrm_image

        # Init the inner CollidableEntity
        super().__init__(start_x, start_y, self.image, current_map)

    def damage(self, damaged_by=""):
        match damaged_by:
            case "weapon":          self.health -= 20
            case "weapon_silver":   self.health -= 25
            case "weapon_cobalt":   self.health -= 35
            case "weapon_gold":     self.health -= 80
            case "weapon_luminite": self.health -= 100
            case "":                self.health -= 20 # Just in case

        self.dmg_last = 30 # Switch to the hurt image for 30 frames
        self.image = self.dmg_image

        glb.sound_engine.playSound(f"metal_{random.randint(1, 4)}")

        # Only take knockback if not frozen in place
        if not self.freeze_place:
            overlaps = [
                abs(self.rect.right - glb.engine.player.rect.left), # Player damaged automaton from left
                abs(self.rect.left - glb.engine.player.rect.right), # Player damaged automaton from right
                abs(self.rect.bottom - glb.engine.player.rect.top), # Player damaged automaton from top
                abs(self.rect.top - glb.engine.player.rect.bottom)  # Player damaged automaton from bottom
            ]

            # Get the OPPOSITE direction of the player's attack, to knockback to
            match overlaps.index(min(overlaps)):
                case 0: self.rect.x -= 8 # Knockback left
                case 1: self.rect.x += 8 # Knockback right
                case 2: self.rect.y -= 8 # Knockback up
                case 3: self.rect.y += 8 # Knockback down

    def update(self):
        # If automaton health is 0 or lower, remove it from entities
        if self.health < 1:
            current_room = glb.engine.rm.current_room_map

            # If the current room is a class inherriting from LevelRoom
            if isinstance(current_room, LevelRoom): current_room.reward_locker_key_pos = (self.x, self.y)

            current_room.entities.remove(self)

            glb.engine.score += 20

        # Reset to the normal image after the dmg_last timer runs out
        if self.dmg_last > 0:
            self.dmg_last -= 1

            if self.dmg_last == 0:
                self.image = self.nrm_image

        # Attack cooldown logic
        if self.attack_cooldown > 0:
            if self.attack_cooldown < 20:
                self.attack_cooldown += 1
            else:
                self.attack_cooldown = 0

        # Checking with mask overlap, because it gives pixel perfect collisions
        if (self.collision_mask.overlap(glb.engine.player.collision_mask, (glb.engine.player.rect.x - self.rect.x, glb.engine.player.rect.y - self.rect.y)) and
            self.attack_cooldown == 0):
            self.attack_cooldown = 1 # Start the cooldown
            glb.engine.player.hurt("automaton")

        if not self.freeze_place:
            # To imitate the automaton stepping slowly and randomly (goes faster if walking to somewhere)
            if (random.randint(1, 10) if self.walking_to != None else random.randint(1, 25)) == 1:
                target = self.walking_to if self.walking_to != None else glb.engine.player.rect.center

                # Get the distance between the automaton and the target
                vx = target[0] - self.rect.center[0]
                vy = target[1] - self.rect.center[1]
                distance = math.sqrt(vx**2 + vy**2)

                # Detection radius (only when going after the player)
                if distance > 1200 and self.walking_to == None: # (if it were any lower, sometimes they just wouldnt move when in the corner of the camera)
                    return # Just end the funtion, the player is out of range

                if distance != 0:
                    vx /= distance # Normalize x
                    vy /= distance # Normalize y

                self.collideCheck(round(vx) * 4, round(vy) * 4)

                # Reset when the automaton reaches its programmed destination (statement is like this because of the * 4)
                if (self.walking_to != None and
                    self.walking_to[0] <= self.rect.center[0] <= self.walking_to[0] + 4 and
                    self.walking_to[1] <= self.rect.center[1] <= self.walking_to[1] + 4):
                    self.walking_to = None # Start going after the player again

class Map:
    def __init__(self, map_path, map_borders):
        if data.DBData.player_name == glb.names[1] and map_borders == (144, 316, 144, 316):
            self.map_image = pygame.image.load("assets/ui/unused/poole.png").convert()
        else:
            self.map_image = utils.loadScaledAsset(map_path).convert()

        self.map_rect = self.map_image.get_rect()
        self.map_borders = map_borders

        self.objects = pygame.sprite.Group()
        self.entities = pygame.sprite.Group()
        self.dropped_items = pygame.sprite.Group()

    def onEnter(self, entering_from): pass

    def input(self, input_stream): pass

    def update(self): pass

    def draw(self, layers): pass

class BaseObject(pygame.sprite.Sprite):
    def __init__(self, x, y, image_path):
        super().__init__()

        if image_path == "": image_path = "assets/crowbr.png" # Crowbr is crucial to this game!! (if the path is empty, it has to be then reset after this function ends)

        self.image = utils.loadScaledAsset(image_path).convert_alpha()
        self.rect = self.image.get_rect()
        self.x,      self.y      = x, y
        self.rect.x, self.rect.y = x, y

        if image_path == "assets/objects/laser_machine.png" and data.DBData.player_name == glb.names[0]:
            self.image = pygame.image.load("assets/ui/unused/machine.png")

        # Needed for collision detection / mouse hover
        self.mask = pygame.mask.from_surface(self.image)

class InterfaceItem:
    def __init__(self, name, image_path, preloaded_image=None):
        self.name = name
        self.fixed_dim = 64 # Fixed dimension (64x64) (loaded image has to be this size after scaled up)

        self.image_path = image_path # Only used in DBData when loading an opened save

        if preloaded_image is not None: # In case the texture is already loaded (like in the case of Lockers)
            self.normal_image = preloaded_image.copy() # copy() is necessary
        else:
            self.normal_image = utils.loadScaledAsset(image_path).convert_alpha()

        self.selected_image = self.normal_image.copy()
        self.chosen_image = self.normal_image.copy()

        # Draw the selected outline to the appropriate image
        pygame.draw.rect(self.selected_image, (255, 255, 0), self.selected_image.get_rect(), 4)
        pygame.draw.rect(self.chosen_image, (255, 0, 0), self.chosen_image.get_rect(), 4)

        self.final_image = self.normal_image

class ClickableItem(BaseObject):
    def __init__(self, x, y, image_path, callback, preloaded_image=None):
        super().__init__(x, y, image_path) # Still have to call this because of the pygame.sprite init

        if preloaded_image is not None: # For classes like TileObject
            self.image = preloaded_image.copy() # copy() is necessary
            self.rect = self.image.get_rect()
            self.x,      self.y      = x, y
            self.rect.x, self.rect.y = x, y

            # Needed for collision detection / mouse hover
            self.mask = pygame.mask.from_surface(self.image)

        self.callback = callback # Set the function to be called when clicked

        self.og_image = self.image
        self.outlined_image = pygame.Surface((self.og_image.get_width() + 8, self.og_image.get_height() + 8), pygame.SRCALPHA)

        # Make a copy of the image filled with the outline color
        outline_surface = pygame.mask.from_surface(self.og_image).to_surface(setcolor=(216, 155, 32))
        outline_surface.set_colorkey((0, 0, 0)) # Make unset pixels transparent

        # Blit outline in 4 directions (up, down, left, right)
        for offset_x, offset_y in [(0, 4), (0, -4), (4, 0), (-4, 0)]: self.outlined_image.blit(outline_surface, (offset_x, offset_y))  

        # To cover the exess inner part of the outline
        self.outlined_image.blit(self.og_image, (0, 0))

        self.image = self.og_image # Going to be switching between og_image and outlined_image

    def input(self, input_stream):
        mouse_pos = input_stream.mouse.getPosition()
        updated_rect = glb.engine.camera.apply(self.rect)

        if (glb.engine.player.rect.colliderect(self.rect.inflate(96, 96)) and # Check if the player is close enough (48 pixels in each direction)
            updated_rect.collidepoint(mouse_pos) and
            self.mask.get_at((mouse_pos[0] - updated_rect.x, mouse_pos[1] - updated_rect.y))): # Check if the mouse is colliding with the mask

            if self.image != self.outlined_image:
                self.image = self.outlined_image

            # General ClickableItems only use left click, but Redirectors also use right click and parameters in the callback
            if input_stream.mouse.isButtonPressed(0) or (type(self) == Redirector and input_stream.mouse.isButtonPressed(2)):
                self.image = self.og_image # Remove outline

                if type(self) == Redirector:
                    self.callback("left" if input_stream.mouse.isButtonPressed(0) else "right")

                else:
                    self.callback()

        elif self.image != self.og_image:
            self.image = self.og_image

class PickupableItem(ClickableItem):
    # Convenience class - ClickableItem that automatically gets added to the player's inventory and removes itself from dropped items
    def __init__(self, name, x, y, image_path, preloaded_image=None):
        def callback():
            glb.engine.player.inventory.collect(InterfaceItem(name, image_path, preloaded_image))
            glb.engine.rm.current_room_map.dropped_items.remove(self)

        super().__init__(x, y, image_path, callback, preloaded_image)

class PaperItem(ClickableItem):
    def __init__(self, x, y, item_image_path, paper_image_path, hide_callback = None, reopenable = False):
        super().__init__(x, y, item_image_path, self.showPaper)

        self.paper_image = utils.loadScaledAsset(paper_image_path).convert_alpha()
        self.close_button_image = utils.loadScaledAsset("assets/ui/close_button.png").convert_alpha()
        self.close_button_hovered_image = utils.loadScaledAsset("assets/ui/close_button_hovered.png").convert_alpha()
        self.close_button_current_image = self.close_button_image
        self.close_button_rect = pygame.Rect(
            (glb.screen_width - self.close_button_image.get_size()[0]) // 2,
            600,
            *self.close_button_current_image.get_size()
        )

        self.x_pos = (glb.screen_width - self.paper_image.get_width()) // 2

        # Animation variables
        self.closed_y = glb.screen_height
        self.opened_y = 0

        self.current_y = self.closed_y
        self.target_y  = None

        # Close timer variables
        self.time_opened_limit = 150 # 1.5 seconds (150 frames at 100 FPS)
        self.time_opened = 0 if not reopenable else 150 # If its reopenable the player can close it as soon as its fully opened

        self.hide_callback = hide_callback # To be able to do things after hiding the paper, without having to rewrite the hidePaper function
        self.reopenable = reopenable

    def showPaper(self):
        if self.current_y == self.closed_y:
            self.target_y = self.opened_y

            glb.sound_engine.playSound("paper_open", 1)

    def hidePaper(self, input_stream):
        if self.current_y == self.opened_y and self.time_opened >= self.time_opened_limit:
            # Mouse hover check
            if self.close_button_rect.collidepoint(input_stream.mouse.getPosition()):
                if self.close_button_current_image != self.close_button_hovered_image:
                    self.close_button_current_image = self.close_button_hovered_image

                    glb.sound_engine.playSound("button")

                # Hide the paper
                if input_stream.mouse.isButtonPressed(0):
                    self.target_y = self.closed_y
                    self.close_button_current_image = self.close_button_image

                    glb.sound_engine.playSound("paper_close", 1)

                    if self.hide_callback is not None:
                        self.hide_callback()

            # Reset to the normal image
            elif self.close_button_current_image != self.close_button_image:
                self.close_button_current_image = self.close_button_image

            # Keyboard ENTER and ESC check
            if input_stream.keyboard.isKeyPressed(pygame.K_RETURN):
                self.target_y = self.closed_y
                self.close_button_current_image = self.close_button_image

                glb.sound_engine.playSound("paper_close", 1)

                if self.hide_callback is not None:
                    self.hide_callback()

    def input(self, input_stream):
        # If its fully opened -> Start checking every frame if it can be closed
        # If its fully closed -> Do the ClickableItem input() (ground interaction)

        match self.current_y:
            case self.opened_y: self.hidePaper(input_stream)
            case self.closed_y: super().input(input_stream)

    def draw(self, layer_1):
        # Draw the UI all of the time EXEPT for when its fully closed
        if self.current_y != self.closed_y:
            layer_1.blit(self.paper_image, (self.x_pos, self.current_y))

        if self.target_y is not None and self.current_y != self.target_y:
            dy = self.target_y - self.current_y

            # 0.2 is for easing in/out effect, 0.5 is for general speed
            self.current_y += (dy * 0.2) * 0.5

            # When really close, just snap
            if abs(dy) < 1: self.current_y = self.target_y

        # If it has reached the target y and that y happens to be the fully opened y
        elif self.target_y == self.opened_y:
            # Start counting the opened time
            if self.time_opened < self.time_opened_limit:
                self.time_opened += 1

            # When it has been opened for long enough start showing the close button
            elif self.time_opened == self.time_opened_limit:
                layer_1.blit(self.close_button_current_image, self.close_button_rect.topleft)

        # If it has reached the target y and that y happens to be the fully closed y
        elif self.target_y == self.closed_y:
            if not self.reopenable: # If its one time use only, immediatly remove it from the dropped items
                glb.engine.rm.current_room_map.dropped_items.remove(self)

class FacilityMap(PaperItem):
    def __init__(self):
        super().__init__(424, 160, "assets/crowbr.png", "assets/ui/unused/facility_map.png" if data.DBData.player_name == glb.names[0] else "assets/ui/facility_map.png", None, True)

        # Make the close button invisible
        self.close_button_image = pygame.Surface((0, 0))
        self.close_button_hovered_image = pygame.Surface((0, 0))
        self.close_button_rect = pygame.Rect(0, 0, 0, 0)

        if settings.hints:
            self.hint = utils.loadScaledAsset("assets/ui/facility_map_hint.png")

            self.hint_closed_x = glb.screen_width
            self.hint_opened_x = glb.screen_width - self.hint.get_width()
            self.hint_target_x = self.hint_closed_x

            self.hint_rect = pygame.Rect(self.hint_closed_x, 600, *self.hint.get_size())

            self.show_hint_timer = 7000
            self.has_opened_map = False

    def input(self, input_stream):
        if settings.hints:
            if self.hint_rect.x == self.hint_opened_x:
                if input_stream.mouse.isButtonPressed(0) and self.hint_rect.collidepoint(input_stream.mouse.getPosition()):
                    self.has_opened_map = True # If the player closed the hint they must already know how to open the map

        match self.current_y:
            case self.opened_y:
                self.hidePaper(input_stream)

                # Additional M key check
                if input_stream.keyboard.isKeyPressed(pygame.K_m):
                    self.target_y = self.closed_y
                    self.close_button_current_image = self.close_button_image

                    glb.sound_engine.playSound("paper_close", 1)

            case self.closed_y:
                if input_stream.keyboard.isKeyPressed(pygame.K_m):
                    self.showPaper()

                    if not self.has_opened_map: self.has_opened_map = True

    def draw(self, layer_1):
        super().draw(layer_1)

        if settings.hints:
            if not self.has_opened_map:
                if self.show_hint_timer > 0:
                    self.show_hint_timer -= 1

                elif self.hint_target_x != self.hint_opened_x:
                    self.hint_target_x = self.hint_opened_x # Open

            elif self.hint_target_x != self.hint_closed_x:
                self.hint_target_x = self.hint_closed_x # Close

            # Draw always exept when its closed
            if self.hint_rect.x != self.hint_closed_x:
                layer_1.blit(self.hint, self.hint_rect.topleft)

            if self.hint_rect.x != self.hint_target_x:
                dx = self.hint_target_x - self.hint_rect.x

                # 0.2 is for easing in/out effect
                self.hint_rect.x += dx * 0.2

                # When really close, just snap
                if abs(dx) < 3: self.hint_rect.x = self.hint_target_x

class TinkerTable(BaseObject):
    # Dictionary of all possible recipes the player can do on the tinker table (needs to be also accessible to RecipesPanel)
    recipes = {}

    class RecipesPanel:
        def __init__(self):
            self.surf = pygame.Surface((64 * 4 + 12 * 3, 64 * 2 + 12 * 1), pygame.SRCALPHA) # 4x2 maximum item display
            self.surf.set_alpha(0)

            self.available_recipe_bg = utils.loadScaledAsset("assets/ui/available_recipe_bg.png")

            # Transition variables
            self.fully_closed_y = 136
            self.fully_opened_y = 36

            self.rect = pygame.Rect(338, self.fully_closed_y, self.surf.get_width(), self.surf.get_height())

            self.opened = False
            self.opening = False
            self.closing = False

            # Recipe grid variables
            self.recipe_grid = [[], []] # List of InterfaceItems, that are shown when the panel is open
            self.recipe_grid_rects = [[], []] # The same list, but with rects of individual recipes in the recipe_grid, so that it is known which one was selected

        def tryPanel(self):
            if not self.opened:
                # Basically just adds the recipe in the correct slot on the grid
                def recipeGridSorter(recipe):
                    # Check if the first row has any space left
                    if len(self.recipe_grid[0]) < 4:
                        self.recipe_grid[0].append(recipe)

                        self.recipe_grid_rects[0].append(pygame.Rect(76 * len(self.recipe_grid_rects[0]), 0, 64, 64))

                    # Check if the second row has any space left
                    elif len(self.recipe_grid[1]) < 4:
                        self.recipe_grid[1].append(recipe)

                        self.recipe_grid_rects[1].append(pygame.Rect(76 * len(self.recipe_grid_rects[1]), 76, 64, 64))

                    # If both of the rows are full:
                    else:
                        pass # Fuck em

                self.recipe_grid = [[], []] # Reset the lists to refresh them
                self.recipe_grid_rects = [[], []]
                player_inv = glb.engine.player.inventory

                for recipe_combination in TinkerTable.recipes:
                    # Special crafting recipes that include the weapon slot
                    if "stick" in recipe_combination or "weapon" in recipe_combination[0]:
                        if recipe_combination[0] == player_inv.weapon_slot.name and any(recipe_combination[1] == slot.name for slot in player_inv.slots):
                            recipeGridSorter(TinkerTable.recipes[recipe_combination])

                    # Normal crafting recipes
                    elif any(recipe_combination[0] == slot.name for slot in player_inv.slots) and any(recipe_combination[1] == slot.name for slot in player_inv.slots):
                        recipeGridSorter(TinkerTable.recipes[recipe_combination])

                # Only open if there are any available recipes
                if len(self.recipe_grid[0]) > 0:
                    # Center the top row
                    if 0 < len(self.recipe_grid_rects[0]) < 4:
                        combined_top_row_width = 64 * len(self.recipe_grid_rects[0]) + 12 * (len(self.recipe_grid_rects[0]) - 1)
                        top_row_x_offset = (self.rect.width - combined_top_row_width) // 2

                        # Apply the offset
                        for recipe_rect in self.recipe_grid_rects[0]:
                            recipe_rect.x += top_row_x_offset

                    # Center the bottom row
                    if 0 < len(self.recipe_grid_rects[1]) < 4:
                        combined_bottom_row_width = 64 * len(self.recipe_grid_rects[1]) + 12 * (len(self.recipe_grid_rects[1]) - 1)
                        bottom_row_x_offset = (self.rect.width - combined_bottom_row_width) // 2

                        # Apply the offset
                        for recipe_rect in self.recipe_grid_rects[1]:
                            recipe_rect.x += bottom_row_x_offset

                    # If the second row is empty, shift down the first one
                    if len(self.recipe_grid_rects[1]) == 0:
                        for recipe_rect in self.recipe_grid_rects[0]:
                            recipe_rect.y += 76

                    if not self.opening and not self.closing: # Make it only interactable when not transitioning
                        self.opened = True

                        self.opening = True
                        self.closing = False

            # If it is already opened, only start closing it if its not transitioning
            elif not (self.opening or self.closing):
                self.opened = False

                self.opening = False
                self.closing = True

        def makeRecipe(self, recipe):
            # Find the required combination based on the name of the result (the name of the passed in recipe InterfaceItem)
            found_combination = [combination for combination, result in TinkerTable.recipes.items() if result.name == recipe.name][0]
            player_inv = glb.engine.player.inventory

            # NOTE: The recipe InterfaceItem is used to create a new one, bc it will still have to be visible in the closing transition

            # Check if its a special recipe related to the weapon slot
            if "stick" in found_combination or "weapon" in found_combination[0]:
                # Find the item in the player's inventory based on its name (combination_item_1 is in the weapon slot)
                combination_item_2 = [index for index, item in enumerate(player_inv.slots) if item.name == found_combination[1]][0]

                player_inv.discard(pos=combination_item_2)

                player_inv.aquireNewWeapon(recipe.name)

            else:
                # If the player is crafting a lower access card than their current level
                if "access" in recipe.name and int(recipe.name[-1]) <= glb.engine.player.current_access_lvl: return # Dont let them craft it

                # Find the items in the player's inventory based on their names
                combination_item_1 = [index for index, item in enumerate(player_inv.slots) if item.name == found_combination[0]][0]
                player_inv.discard(pos=combination_item_1)

                combination_item_2 = [index for index, item in enumerate(player_inv.slots) if item.name == found_combination[1]][0]
                player_inv.discard(pos=combination_item_2)

                # If the player is making an access card, dont add it to the inventory, just upgrade the access level
                if "access" in recipe.name:
                    glb.engine.player.current_access_lvl = int(recipe.name[-1]) # The last letter HAS TO BE the access level
                else:
                    player_inv.collect(InterfaceItem(recipe.name, "", recipe.normal_image))

            # Reset the UI recipe's final image
            recipe.final_image = recipe.normal_image

            # Close the panel
            self.opened = False

            self.opening = False
            self.closing = True

            glb.engine.score += 10

        def input(self, input_stream):
            for i, row in enumerate(self.recipe_grid_rects):
                for j, recipe_rect in enumerate(row):
                    current_recipe = self.recipe_grid[i][j]

                    # Correctly position it in the room
                    positioned_recipe_rect = recipe_rect.copy()
                    positioned_recipe_rect.x += self.rect.x
                    positioned_recipe_rect.y += self.rect.y

                    if glb.engine.camera.apply(positioned_recipe_rect).collidepoint(input_stream.mouse.getPosition()):
                        if current_recipe.final_image != current_recipe.selected_image:
                            current_recipe.final_image = current_recipe.selected_image

                        if input_stream.mouse.isButtonPressed(0):
                            self.makeRecipe(current_recipe)

                    else:
                        if current_recipe.final_image != current_recipe.normal_image:
                            current_recipe.final_image = current_recipe.normal_image

            accurate_rect = self.rect.copy() # The combined rect of the recipe items (self.rect is the entire surface, so its way to big most of the time)

            wider_row = max(len(self.recipe_grid_rects[0]), len(self.recipe_grid_rects[1]))
            accurate_rect.width = wider_row * 64 + (wider_row - 1) * 12
            accurate_rect.height = 64 if len(self.recipe_grid_rects[1]) == 0 else 64 * 2 + 12

            # If the player clicked away from the surface, close it
            if (not glb.engine.camera.apply(accurate_rect).collidepoint(input_stream.mouse.getPosition()) and input_stream.mouse.isButtonPressed(0) and
                not (self.opening or self.closing)):
                self.opened = False

                self.opening = False
                self.closing = True

        def draw(self, layer_2):
            self.surf.fill((0, 0, 0, 0)) # Clear the surface for new drawing

            for i, row in enumerate(self.recipe_grid):
                for j, recipe in enumerate(row):
                    self.surf.blit(self.available_recipe_bg, self.recipe_grid_rects[i][j])
                    self.surf.blit(recipe.final_image, self.recipe_grid_rects[i][j])

            # Ehh copied logic from Locker, but thats okay
            if self.opening or self.closing:
                target_y = self.fully_opened_y if self.opening else self.fully_closed_y
                target_alpha = 255 if self.opening else 0

                # Move a fraction of the remaining distance each frame
                dy = target_y     - self.rect.y
                da = target_alpha - self.surf.get_alpha()

                # 0.2 is for easing in/out effect
                self.rect.y += dy * 0.2
                self.surf.set_alpha(self.surf.get_alpha() + da * 0.2)

                # When really close, just snap
                if abs(dy) < 3:
                    self.rect.y = target_y
                    self.surf.set_alpha(target_alpha)
                    self.opening = self.closing = False

            # Also draw the UI if its in the middle of closing
            if self.opened or self.closing:
                layer_2.blit(self.surf, glb.engine.camera.apply(self.rect))

    def __init__(self):
        super().__init__(404, 144, "assets/objects/tinker_table.png")

        # Needs to have the values set here, because AccessCards.dictionary is empty at compile time
        TinkerTable.recipes = {
            # Weapons
            ("stick",         "brass"):    InterfaceItem("weapon", "assets/items/weapon.png"),
            ("weapon",        "silver"):   InterfaceItem("weapon_silver",   "assets/items/weapon_silver.png"),
            ("weapon_silver", "cobalt"):   InterfaceItem("weapon_cobalt",   "assets/items/weapon_cobalt.png"),
            ("weapon_cobalt", "gold"):     InterfaceItem("weapon_gold",     "assets/items/weapon_gold.png"),
            ("weapon_gold",   "luminite"): InterfaceItem("weapon_luminite", "assets/items/weapon_luminite.png"),

            # Access card crafting (access cards have preloaded textures)
            ("brass",     "quartz"):     InterfaceItem("access 1", "", AccessCards.dictionary[0]),
            ("lead",      "jade"):       InterfaceItem("access 2", "", AccessCards.dictionary[1]),
            ("silver",    "topaz"):      InterfaceItem("access 3", "", AccessCards.dictionary[2]),
            ("platinum",  "sapphire"):   InterfaceItem("access 4", "", AccessCards.dictionary[3]),
            ("cobalt",    "ruby"):       InterfaceItem("access 5", "", AccessCards.dictionary[4]),
            ("titanium",  "aquamarine"): InterfaceItem("access 6", "", AccessCards.dictionary[5]),
            ("gold",      "painite"):    InterfaceItem("access 7", "", AccessCards.dictionary[6]),
            ("adamatite", "celestine"):  InterfaceItem("access 8", "", AccessCards.dictionary[7]),
            ("luminite",  "diamond"):    InterfaceItem("access 9", "", AccessCards.dictionary[8])
        }

        self.huh = utils.loadScaledAsset("assets/ui/huh.png").convert_alpha()
        self.huh_rect = self.huh.get_rect()
        self.huh_rect.x = 454
        self.huh_rect.y = 152

        self.recipes_panel = self.RecipesPanel()

        self.tinker_place = ClickableItem(424, 148, "assets/objects/tinker_place.png", self.recipes_panel.tryPanel)

    def input(self, input_stream):
        player = glb.engine.player # For faster lookup times

        # Only allow any kind of tinkering if the player has any kind of weapon and the recipes panel isnt opened
        if player.inventory.weapon_slot != None and not self.recipes_panel.opened:
            # Only allow regular interaction if the player has fixed the weapon
            # OR
            # If any item in the inventory is selected and the bots have been released (needed at the start of the game)
            if ("weapon" in player.inventory.weapon_slot.name or
                (player.inventory.current_item_idx != -1 and glb.engine.rm.current_room_map.bots_released)):
                self.tinker_place.input(input_stream)

        if self.recipes_panel.opened:
            if not self.recipes_panel.opening:
                self.recipes_panel.input(input_stream)

            # If the player is too far, close the panel
            if not self.recipes_panel.closing and not player.rect.colliderect(self.rect.inflate(96, 96)):
                self.recipes_panel.opened = False

                self.recipes_panel.opening = False
                self.recipes_panel.closing = True

    def draw(self, layers):
        layers[2].blit(self.tinker_place.image, glb.engine.camera.apply(self.tinker_place.rect))

        # Show the player they need to craft
        if glb.engine.rm.current_room_map.bots_released and glb.engine.player.inventory.weapon_slot.name == "stick":
            layers[2].blit(self.huh, glb.engine.camera.apply(self.huh_rect))

        if self.recipes_panel.opened or self.recipes_panel.closing:
            self.recipes_panel.draw(layers[1])

class LaserMachine(BaseObject):
    def __init__(self):
        self.base_x = 556
        self.base_y = 500
        super().__init__(self.base_x, self.base_y, "assets/objects/laser_machine.png")

        # Lasers (later to be replaced with animations)
        self.broken_laser = utils.loadScaledAsset("assets/objects/broken_laser.png").convert_alpha()
        self.broken_laser_rect = pygame.Rect(self.base_x + 76, self.base_y + 84, *self.broken_laser.get_size())
        self.broken_laser_timer = 200

        self.perma_laser = utils.loadScaledAsset("assets/objects/perma_laser.png").convert_alpha()
        self.perma_laser_rect = pygame.Rect(self.base_x + 76, self.base_y + 84, *self.perma_laser.get_size())
        self.perma_laser_on = False
        self.perma_laser_mask = pygame.mask.from_surface(self.perma_laser) # For collision detection with the player

        # Internal stuff
        self.repaired = False
        self.mirror_repaired = False

        def mirrorRepairNeedLearned():
            glb.engine.player.knows_to_fix_mirror = True

            # In case the player already picked up the items before the text ended
            if len(glb.engine.rm.current_room_map.dropped_items) != 0:
                glb.engine.om.setObjective(ObjectivesManager.possible_objectives[4])

        def machineRepaired():
            self.repaired = True

            self.broken_laser_timer -= 1 # Start the broken laser

            current_room = glb.engine.rm.current_room_map

            # Remove the pile and replace it with the stick and scraps
            current_room.objects.remove(current_room.pile)

            current_room.dropped_items.add(current_room.stick)
            current_room.dropped_items.add(current_room.brass_1)
            current_room.dropped_items.add(current_room.brass_2)

            glb.engine.om.clearObjective()

            glb.engine.typing_utility.startTyping(
                "You repaired the laser machine!\nBut it appears the laser has melted a hole through the redirection mirror\nfrom overuse. You need to fix the mirror.",
                (50, 550),
                mirrorRepairNeedLearned,
                5
            )

            glb.engine.score += 40

        def mirrorRepaired():
            self.mirror = BaseObject(self.base_x + 80, self.base_y + 212, "assets/objects/mirror.png") # Show the mirror is repaired
            self.mirror_repaired = True

            # Take out the quartz from the player's inventory
            glb.engine.player.inventory.discard(pos=glb.engine.player.inventory.current_item_idx) # The crystal will still be selected at this time

            self.perma_laser_on = True

            glb.engine.om.clearObjective()

            # Show that the player can enter the new room
            glb.engine.rm.current_room_map.map_image.blit(utils.loadScaledAsset("assets/objects/room_1_active_door.png"), (300 * 4, 218 * 4))

        self.console = ClickableItem(self.base_x + 16, self.base_y + 144, "", machineRepaired, pygame.transform.rotate(utils.loadScaledAsset("assets/objects/machine_console.png"), -90))
        self.mirror = ClickableItem(self.base_x + 80, self.base_y + 212, "assets/objects/broken_mirror.png", mirrorRepaired)

    def input(self, input_stream):
        if not self.repaired and glb.engine.player.knows_to_fix_machine:
            self.console.input(input_stream)

        # Check if the mirror has not been repaired yet and the player knows about it
        if not self.mirror_repaired and glb.engine.player.knows_to_fix_mirror:
            # Check if the player has a quartz and has selected it
            for index, item in enumerate(glb.engine.player.inventory.slots):
                if item.name == "quartz" and index == glb.engine.player.inventory.current_item_idx:
                    self.mirror.input(input_stream)

    def draw(self, layers):
        layers[2].blit(self.console.image, glb.engine.camera.apply(self.console.rect))
        layers[2].blit(self.mirror.image, glb.engine.camera.apply(self.mirror.rect))

        # Blit layers to the second layer
        if self.broken_laser_timer < 200 and self.broken_laser_timer != 0:
            layers[1].blit(self.broken_laser, glb.engine.camera.apply(self.broken_laser_rect))
            self.broken_laser_timer -= 1

        if self.perma_laser_on:
            layers[1].blit(self.perma_laser, glb.engine.camera.apply(self.perma_laser_rect))

class CrystalMachine(BaseObject):
    def __init__(self):
        self.x = 332
        self.y = 316
        super().__init__(self.x, self.y, "assets/objects/crystal_machine.png")

        self.scrap_place_close_anim = utils.Gif("assets/objects/scrap_place_close.gif", (self.x + 144, self.y + 152))

        self.current_crystal = ""
        self.current_crystal_time = 0 # The amount of time required for the current_crystal to become current_grown_crystal
        self.current_grown_crystal = ""
        self.current_scraps = [] # Array of only 2 scrap names, that is used when checking if the required scraps are in to start making a crystal

        # Crystal-growing scrap combinations
        self.combinations = {
            # Base        # Reactant    # Result
            ("brass",     "copper"):    ("quartz",     1000),
            ("brass",     "lead"):      ("jade",       1500),
            ("magnesium", "silver"):    ("topaz",      2000),
            ("magnesium", "tungsten"):  ("sapphire",   2500),
            ("platinum",  "cobalt"):    ("ruby",       3000),
            ("platinum",  "palladium"): ("aquamarine", 3500),
            ("titanium",  "gold"):      ("painite",    4000),
            ("titanium",  "indium"):    ("celestine",  4500),
            ("adamatite", "luminite"):  ("diamond",    5000)
        }

        def machineTurnedOn():
            glb.engine.player.turned_on_crystal_machine = True

            # Show the door is opened
            current_map = glb.engine.rm.current_room_map
            current_map.map_image.blit(current_map.door, (964, 432))

            # Turning on the crystal machine was the last thing the player did
            if glb.engine.player.knows_to_fix_machine:
                glb.engine.om.setObjective(ObjectivesManager.possible_objectives[3])
            
            # The player hasn't read the blueprints so they have to do that now
            else:
                glb.engine.om.setObjective(ObjectivesManager.possible_objectives[1])

            glb.engine.score += 40

        def crystalCollected():
            glb.engine.player.inventory.collect(InterfaceItem(self.current_grown_crystal, "", Crystals.dictionary[self.current_grown_crystal]))

            self.scrap_place_close_anim.start(True) # Start the reversed gif, so it opens
            self.scrap_place_close_anim.reset()

            # For the player's first time collecting a crystal
            if not glb.engine.rm.active_rooms["first_floor"].laser_machine.mirror_repaired:
                glb.engine.om.setObjective(ObjectivesManager.possible_objectives[6])

            self.current_grown_crystal = ""
            self.current_scraps = []

            glb.engine.score += 20

        def scrapsPlaced():
            # The scrap the player wants to use should be selected at this point
            current_scrap = glb.engine.player.inventory.slots[glb.engine.player.inventory.current_item_idx].name

            # Only for the first placed scraps when the player has to fight bots to escape
            if not glb.engine.rm.active_rooms["first_floor"].laser_machine.mirror_repaired:
                # Remove it from the player's inventory
                glb.engine.player.inventory.discard(pos=glb.engine.player.inventory.current_item_idx)

                self.scrap_place_close_anim.start()

                glb.engine.rm.current_room_map.releaseTheBots() # The current room will be the ResourceRoom
                # Do not do anything about the crystals here, they will become already fully grown when the player beats all of the bots

            # Check if there is space for another scrap
            elif len(self.current_scraps) < 2:
                # Second crystal checking
                if len(self.current_scraps) == 1:
                    # Dont allow input if theres a duplicate scrap already inside
                    if self.current_scraps[0] == current_scrap:
                        return

                    # Dont allow input if its not a valid recipe
                    if not (
                        self.combinations.get((self.current_scraps[0], current_scrap)) or
                        self.combinations.get((current_scrap, self.current_scraps[0]))
                        ):
                        return

                # Remove it from the player's inventory and add it to the scrap array
                glb.engine.player.inventory.discard(pos=glb.engine.player.inventory.current_item_idx)
                self.current_scraps.append(current_scrap)

                # Main crystal-recipe checker
                if len(self.current_scraps) == 2:
                    self.scrap_place_close_anim.start()
                    self.scrap_place_close_anim.reset()

                    for combination in self.combinations.keys():
                        if self.current_scraps[0] in combination and self.current_scraps[1] in combination:
                            self.current_crystal = self.combinations[combination][0]
                            self.current_crystal_time = self.combinations[combination][1]

                            break

        # Scrap indicator lights
        self.scrap_1_light_rect = pygame.Rect(self.x + 148, self.y + 132, 8, 8)
        self.scrap_2_light_rect = pygame.Rect(self.x + 168, self.y + 132, 8, 8)

        # Interactable parts
        self.console = ClickableItem(self.x + 16, self.y + 16, "assets/objects/machine_console.png", machineTurnedOn)
        self.crystals_book = PaperItem(self.x + 96, self.y + 16, "assets/objects/crystals_book.png", "assets/ui/book.png", None, True)
        self.scrap_place = ClickableItem(self.x + 140, self.y + 148, "assets/objects/scrap_place.png", scrapsPlaced)
        self.crystal_collection = ClickableItem(self.x + 100, self.y + 76, "assets/objects/crystal_collection.png", crystalCollected)

        # Crystal collection animations
        crystal_throbber_img = utils.loadScaledAsset("assets/objects/crystal_throbber.png")

        self.crystal_throbber_frames = [
            pygame.transform.rotate(crystal_throbber_img, -90),
            pygame.transform.rotate(crystal_throbber_img, 180),
            pygame.transform.rotate(crystal_throbber_img, 90),
            crystal_throbber_img
        ]

        self.crystal_throbber_current_frame = 0
        self.crystal_throbber_timer = 0

        self.crystal_finished_frames = [
            utils.loadScaledAsset("assets/objects/crystal_finished_on.png"),
            utils.loadScaledAsset("assets/objects/crystal_finished_off.png")
        ]

        self.crystal_finished_current_frame = 0
        self.crystal_finished_timer = 0

    def growingCrystals(self):
        if self.current_crystal != "" and self.current_crystal_time > 0:
            self.current_crystal_time -= 1

            # The crystal has finished growing
            if self.current_crystal_time == 0:
                self.current_grown_crystal = self.current_crystal
                self.current_crystal = ""
                self.current_scraps = []

    def input(self, input_stream):
        if glb.engine.player.read_instructions:
            if glb.engine.player.turned_on_crystal_machine: self.crystals_book.input(input_stream)
            else: self.console.input(input_stream)

        if self.current_grown_crystal != "":
            self.crystal_collection.input(input_stream)

        # Check if the place is free for a new crystal
        if self.current_crystal == "" and not glb.engine.rm.current_room_map.bots_released:
            # Check if the player has any kind of scraps selected
            for index, item in enumerate(glb.engine.player.inventory.slots):
                for scrap_name in Scraps.dictionary.keys(): # Go through all scrap names to see if the player has it
                    if scrap_name == item.name and index == glb.engine.player.inventory.current_item_idx:
                        self.scrap_place.input(input_stream)

    def draw(self, layers):
        layers[2].blit(self.console.image,            glb.engine.camera.apply(self.console.rect))
        layers[2].blit(self.scrap_place.image,        glb.engine.camera.apply(self.scrap_place.rect))
        layers[2].blit(self.crystals_book.image,      glb.engine.camera.apply(self.crystals_book.rect))
        layers[2].blit(self.crystal_collection.image, glb.engine.camera.apply(self.crystal_collection.rect)) # Always has to be drawn (so the outline displays)

        self.crystals_book.draw(layers[0]) # Draw to layer_1

        self.scrap_place_close_anim.draw(layers[2], glb.engine.camera.apply(self.scrap_place_close_anim.rect))

        # The player can collect the crystal (do the blinking animation)
        if self.current_grown_crystal != "":
            self.crystal_finished_timer += 1

            if self.crystal_finished_timer == 50:
                self.crystal_finished_timer = 0

                # FLip the frame
                self.crystal_finished_current_frame = 0 if self.crystal_finished_current_frame == 1 else 1

            layers[2].blit(self.crystal_finished_frames[self.crystal_finished_current_frame], glb.engine.camera.apply(self.crystal_collection.rect))

        # Show the throbber
        elif len(self.current_scraps) == 2:
            self.crystal_throbber_timer += 1

            if self.crystal_throbber_timer == 50:
                self.crystal_throbber_timer = 0

                # Move to the next frame
                self.crystal_throbber_current_frame += 1

                if self.crystal_throbber_current_frame == 4:
                    self.crystal_throbber_current_frame = 0

            layers[2].blit(self.crystal_throbber_frames[self.crystal_throbber_current_frame], glb.engine.camera.apply(self.crystal_collection.rect))

        # Scrap indicator lights drawing
        if len(self.current_scraps) >= 1:
            scrap_1_color = (0, 0, 0)

            match self.current_scraps[0]:
                case "brass":     scrap_1_color = (175, 147,  93)
                case "copper":    scrap_1_color = (195, 126,  95)
                case "lead":      scrap_1_color = ( 85, 114, 123)
                case "magnesium": scrap_1_color = (187, 187, 187)
                case "silver":    scrap_1_color = (176, 190, 197)
                case "tungsten":  scrap_1_color = (139, 175, 140)
                case "platinum":  scrap_1_color = (128, 151, 184)
                case "cobalt":    scrap_1_color = ( 61, 164, 196)
                case "palladium": scrap_1_color = (228, 104,  63)
                case "titanium":  scrap_1_color = (187, 179, 167)
                case "gold":      scrap_1_color = (203, 179,  73)
                case "indium":    scrap_1_color = (145, 106, 176)
                case "adamatite": scrap_1_color = (207,  75,  86)
                case "luminite":  scrap_1_color = ( 69, 167, 119)

            pygame.draw.rect(layers[2], scrap_1_color, glb.engine.camera.apply(self.scrap_1_light_rect))

            if len(self.current_scraps) == 2:
                scrap_2_color = (0, 0, 0)

                match self.current_scraps[1]:
                    case "brass":     scrap_2_color = (175, 147,  93)
                    case "copper":    scrap_2_color = (195, 126,  95)
                    case "lead":      scrap_2_color = ( 85, 114, 123)
                    case "magnesium": scrap_2_color = (187, 187, 187)
                    case "silver":    scrap_2_color = (176, 190, 197)
                    case "tungsten":  scrap_2_color = (139, 175, 140)
                    case "platinum":  scrap_2_color = (128, 151, 184)
                    case "cobalt":    scrap_2_color = ( 61, 164, 196)
                    case "palladium": scrap_2_color = (228, 104,  63)
                    case "titanium":  scrap_2_color = (187, 179, 167)
                    case "gold":      scrap_2_color = (203, 179,  73)
                    case "indium":    scrap_2_color = (145, 106, 176)
                    case "adamatite": scrap_2_color = (207,  75,  86)
                    case "luminite":  scrap_2_color = ( 69, 167, 119)

                pygame.draw.rect(layers[2], scrap_2_color, glb.engine.camera.apply(self.scrap_2_light_rect))

class FirstFloorMap(Map):
    def __init__(self):
        super().__init__("assets/ui/unused/harden.png" if data.DBData.player_name == glb.names[1] else "assets/maps/first_floor.png", (120, 120, 120, 120))
        self.interaction = True

        # Entities
        self.entities.add(Automaton(400, 970, self))
        self.entities.add(Automaton(500, 850, self))
        self.entities.add(Automaton(630, 900, self))
        self.entities.add(Automaton(800, 900, self))
        self.entities.add(Automaton(850, 1000, self))

        # Objects
        self.laser_machine = LaserMachine()
        self.objects.add(self.laser_machine)

        pile_x = 1060
        pile_y = 1084

        self.pile = BaseObject(pile_x, pile_y, "assets/objects/pile.png") # At the start the stick is hidden under a pile
        self.objects.add(self.pile)

        # Items
        def aquireStick():
            self.dropped_items.remove(self.stick) # Pick it up and add it to the player's weapon slot

            glb.engine.player.inventory.aquireNewWeapon("stick")

        # (these get added to dropped items when the player turns on the laser machine)
        self.stick = ClickableItem(pile_x + 48, pile_y - 32, "assets/items/stick.png", aquireStick)
        self.brass_1 = PickupableItem("brass", pile_x + 32, pile_y + 32, "", Scraps.dictionary["brass"])
        self.brass_2 = PickupableItem("brass", pile_x + 88, pile_y + 72, "", Scraps.dictionary["brass"])

        # Other
        self.told_resource_room_objective = False

    def onEnter(self, entering_from):
        self.interaction = True

        match entering_from:
            case "resource_room": glb.engine.player.changeXY(140,  880)
            case "room_1":        glb.engine.player.changeXY(1140, 880)

        glb.engine.camera.update(glb.engine.player, False)

    def update(self):
        if self.interaction:
            # Doors to the resource room and room 1
            if 844 <= glb.engine.player.y <= 924:
                # Resource room
                if glb.engine.player.x == 120:
                    self.interaction = False
                    glb.engine.rm.moveTo("resource_room")

                # Room 1
                elif glb.engine.player.x == 1160 and self.laser_machine.mirror_repaired:
                    self.interaction = False
                    glb.engine.rm.moveTo("room_1")

            # When the player picks up all of the scraps (when the dropped items are empty)
            if self.laser_machine.repaired and not self.dropped_items and not self.told_resource_room_objective:
                self.told_resource_room_objective = True

                glb.engine.om.setObjective(ObjectivesManager.possible_objectives[5])

class ResourceRoomMap(Map):
    def __init__(self):
        super().__init__("assets/maps/resource_room.png", (144, 316, 144, 316))

        self.interaction = True
        self.bots_released = False # For the fight that happens after the player places the first crystal (gets set back to False when the player beats all of the bots)
        self.bot_release_timer = 0 # So all of the bots dont enter at the same time
        self.bot_pos = [(804, 176), (852, 272), (852, 368), (804, 468)] # Only the first four bots will be walking to somewhere (the last one is at the door)

        self.door = utils.loadScaledAsset("assets/objects/opened_door.png")

        # Objects
        self.tinker_table = TinkerTable()
        self.crystal_machine = CrystalMachine()

        self.objects.add(self.tinker_table)
        self.objects.add(self.crystal_machine)

        # Items
        def knowsToFixMachine():
            glb.engine.player.knows_to_fix_machine = True

            # The player hasn't read the instructions and hasn't turned on the crystal machine
            if not glb.engine.player.read_instructions:
                glb.engine.om.clearObjective()

            # The player HAS read the instructions but hasn't yet turned on the crystal machine
            elif not glb.engine.player.turned_on_crystal_machine:
                glb.engine.om.setObjective(ObjectivesManager.possible_objectives[2])

            # Reading the blueprint was the last thing the player did
            else:
                glb.engine.om.setObjective(ObjectivesManager.possible_objectives[3])

        def readInstructions():
            glb.engine.player.read_instructions = True

            glb.engine.om.setObjective(ObjectivesManager.possible_objectives[2])

        blueprint_path = "assets/ui/unused/blueprint.png" if data.DBData.player_name == glb.names[0] else "assets/ui/blueprint.png"
        paper_path = "assets/ui/unused/paper.png" if data.DBData.player_name == glb.names[0] else "assets/ui/paper.png"

        self.dropped_items.add(PaperItem(432, 148, "assets/items/blueprint.png", blueprint_path, knowsToFixMachine))
        self.dropped_items.add(PaperItem(472, 360, "assets/items/instructions.png", paper_path, readInstructions))

    def releaseTheBots(self):
        self.bots_released = True
        self.bot_release_timer = 1 # Kick off the entering

        # The player already knows to make the weapon and fight the bots
        glb.engine.om.clearObjective()

    def onEnter(self, entering_from):
        if entering_from == "first_floor":
            self.interaction = True

            glb.engine.player.changeXY(904, 444)
            glb.engine.camera.update(glb.engine.player, False)

            if data.DBData.player_name == glb.names[1] and glb.sound_engine.current_music != "u2_music":
                glb.sound_engine.switchMusic("u2_music")

            # If its the first time entering the room
            if not glb.engine.player.turned_on_crystal_machine:
                glb.engine.om.setObjective(ObjectivesManager.possible_objectives[1])

    def update(self):
        player = glb.engine.player

        if (self.interaction and player.x == 924 and
            420 < player.y < 492 and
            player.turned_on_crystal_machine and # Don't let them leave until they turned on the crystal machine
            len(self.entities) == 0): # Don't let them leave until there are no entities left in the room to kill (automatons when the player palces the first scrap)

            self.interaction = False
            glb.engine.rm.moveTo("first_floor")

        if self.bots_released:
            # For the timing of the entering only when there are any bots left in the first floor (its expected the only entities on the first floor are the automatons)
            if self.bot_release_timer > 0 and len(glb.engine.rm.active_rooms["first_floor"].entities) > 0:
                if self.bot_release_timer < 150:
                    self.bot_release_timer += 1

                else:
                    self.bot_release_timer = 1
                    # BTW setting bot_release_timer to 0 to stop everything here is not necessary, because of the len checking in the if above

                    # Remove all of the bots from the first floor one by one as they enter (yes, it has to be done like this)
                    glb.engine.rm.active_rooms["first_floor"].entities.remove(glb.engine.rm.active_rooms["first_floor"].entities.sprites()[0])

                    automaton_entity = Automaton(916, 444, self)
                    self.entities.add(automaton_entity)

                    # When the last automaton has been removed and added, make it freeze at the door
                    if len(glb.engine.rm.active_rooms["first_floor"].entities) == 0:
                        automaton_entity.freeze_place = True
                    else:
                        automaton_entity.walking_to = self.bot_pos[4 - len(glb.engine.rm.active_rooms["first_floor"].entities)]

            # After all of the automatons have been moved, start checking if they have been beaten
            elif len(self.entities) == 0:
                self.crystal_machine.current_grown_crystal = "quartz" # The crystal will conveniently become fully grow when the bots are beaten
                self.bots_released = False # Set back to False so this entire checking doesn't happen again

# Import the required assets for levels
from levelassets import *

# Import the maps last
from roommaps import *
