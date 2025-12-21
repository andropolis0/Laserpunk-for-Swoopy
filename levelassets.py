from engine import *
import settings
import data

# Tile objects

class TileObject(ClickableItem):
    def __init__(self, scr_x, scr_y, tile_pos, callback, image):
        super().__init__(scr_x, scr_y, "", callback, image) # Tiles are preloaded images by default

        self.tile_pos = tile_pos # For keeping track of the position on the tilemap (tuple)
        self.pure_outline = self.outlined_image.copy() # For refreshing the outlined_image (sometimes active images go over the outline so this refreshes that)

    def refreshOutline(self):
        # QOL function yea
        self.outlined_image.blit(self.pure_outline, (0, 0))
        self.outlined_image.blit(self.og_image, (0, 0))

class Redirector(TileObject):
    def __init__(self, type, scr_x, scr_y, tile_pos):
        # Get the correct rotation of the image based on the type (for example: 4.2 as string's last char is 2 and orientation at index 2 is 180
        super().__init__(scr_x, scr_y, tile_pos, self.rotate, Tiles.object_tiles[f"RED_r{ [0, 90, 180, -90][ int(str(type)[-1]) ] }"])

        self.type = type # Can only be 4.0, 4.1, 4.2, 4.3
        self.active = False # If it is actively redirecting the laser

    def activate(self):
        # Used by drawLaserPath() when the laser hits the Redirector
        self.active = True

        # Update the og and outlined image
        self.og_image = Tiles.object_tiles[f"RDA_r{ [0, 90, 180, -90][ int(str(self.type)[-1]) ] }"]

        # This is only here for redirectors that are activated by the laser at the very start
        self.outlined_image.blit(self.og_image, (0, 0))
        self.image = self.og_image

    def reset(self):
        # Used by drawLaserPath() when it has to reset all laser-affecting objects
        self.active = False

        # Update the og and outlined image
        self.og_image = Tiles.object_tiles[f"RED_r{ [0, 90, 180, -90][ int(str(self.type)[-1]) ] }"]

        self.refreshOutline()

    def rotate(self, direction):
        # Go to the next type depending on the direction of the rotation
        if   direction == "left":  self.type += 0.1
        elif direction == "right": self.type -= 0.1

        glb.sound_engine.playSound("redirector", 0.8)

        # Round to one decimal so shi like 4.199999999999999 dont happen
        self.type = round(self.type, 1)

        # For looping back around
        if   self.type < 4.0: self.type = 4.3
        elif self.type > 4.3: self.type = 4.0

        # Update the direction also on the tilemap, so the laser path can be redirected accordingly
        glb.engine.rm.current_room_map.tilemap[self.tile_pos[1]][self.tile_pos[0]] = self.type
        glb.engine.rm.current_room_map.drawLaserPath()

        self.refreshOutline()

        # Only if the room's final door is yet to be unlocked
        if glb.engine.rm.current_room_map.interactable_redirectors:
            # The player's mouse will 99% still be hovering
            self.image = self.outlined_image

class Blocker(TileObject):
    def __init__(self, type, scr_x, scr_y, tile_pos):
        # Get the correct rotation of the image based on the type (for example: 7.2 as string's last char is 2 and orientation at index 2 is 180
        super().__init__(scr_x, scr_y, tile_pos, self.changeState, Tiles.object_tiles[f"BLO_r{ [0, 90, 180, -90][ int(str(type)[-1]) ] }"])

        self.type = type # Can only be 7.0, 7.1, 7.2, 7.3
        self.active = False # If it is actively blocking the laser

    def activate(self):
        # Used by drawLaserPath() when the laser hits the Blocker
        # Update the og and outlined image
        self.og_image = Tiles.object_tiles[f"BLB_r{ [0, 90, 180, -90][ int(str(self.type)[-1]) ] }"]

        self.refreshOutline()

    def reset(self):
        # Used by drawLaserPath() when it has to reset all laser-affecting objects
        # Active needs to remain unchanged

        # Update the og and outlined image
        self.og_image = Tiles.object_tiles[f"BL{'A' if self.active else 'O'}_r{ [0, 90, 180, -90][ int(str(self.type)[-1]) ] }"]

        self.refreshOutline()

    def changeState(self):
        self.active = not self.active

        glb.sound_engine.playSound("blocker", 0.8)

        glb.engine.rm.current_room_map.drawLaserPath()

        self.refreshOutline()

        # Only if the room's final door is yet to be unlocked
        if glb.engine.rm.current_room_map.interactable_redirectors:
            # The player's mouse will 99% still be hovering
            self.image = self.outlined_image

class Locker(TileObject):
    def __init__(self, type, slots, scr_x, scr_y, tile_pos, rotation):
        super().__init__(scr_x, scr_y, tile_pos, self.useLocker, Tiles.object_tiles[f"LK{ int(str(type)[-1])+1 }_r{ rotation }"])

        # The item selection works similarly to Inventory's
        self.slots = [] # 4 item array of InterfaceItems

        for scrap_name in slots:
            if scrap_name == "": continue # If its an empty slot, dont do anything

            self.slots.append(InterfaceItem(scrap_name, "", Scraps.dictionary[scrap_name]))

        self.type = type # Can only be 9.0 (blue), 9.1 (green), 9.2 (reward)
        self.opened = False
        self.opened_ui_image = pygame.transform.rotate(utils.loadScaledAsset(f"assets/ui/locker_{ int(str(type)[-1])+1 }_opened.png").convert_alpha(), rotation)
        self.opened_ui_image.set_alpha(0)
        self.opened_ui_rect = self.opened_ui_image.get_rect()

        # Only the reward lockers will be locked
        self.unlocked = not type == 9.2

        # UI transition variables
        self.opening = False
        self.closing = False
        self.opened_ui_start_pos = (0, 0)
        self.opened_ui_end_pos = (0, 0)
        self.ui_alpha = 0

        ui_centered_x = scr_x - (self.opened_ui_image.get_width() - self.og_image.get_width()) // 2
        ui_centered_y = scr_y - (self.opened_ui_image.get_height() - self.og_image.get_height()) // 2

        # For correctly positioning the items when drawing
        self.slot_offset = (0, 0)

        # Set the UI transition start, end positions and the slot offset based on the rotation
        match rotation:
            case 0:
                self.opened_ui_start_pos = (ui_centered_x, scr_y - 8)
                self.opened_ui_end_pos = (ui_centered_x, scr_y - 84)
                self.slot_offset = (4, 8)

            case 90:
                self.opened_ui_start_pos = (scr_x - 8, ui_centered_y)
                self.opened_ui_end_pos = (scr_x - 84, ui_centered_y)
                self.slot_offset = (8, 4)

            case 180:
                self.opened_ui_start_pos = (ui_centered_x, scr_y + 4)
                self.opened_ui_end_pos = (ui_centered_x, scr_y + 80)
                self.slot_offset = (4, 4)

            case -90:
                self.opened_ui_start_pos = (scr_x + 4, ui_centered_y)
                self.opened_ui_end_pos = (scr_x + 80, ui_centered_y)
                self.slot_offset = (4, 4)

        self.opened_ui_rect.topleft = self.opened_ui_start_pos

    def useLocker(self):
        # If this is a locked reward locker, the player needs a key to open it
        if not self.unlocked:
            glb.engine.player.inventory.discard(pos=glb.engine.player.inventory.current_item_idx) # Remove the key from the player's inventory
            self.unlocked = True # So the player can use it freely once it has been unlocked

            data.score += 80

        if self.unlocked:
            self.image = self.outlined_image # Just to this to prevent flickering, bc by default ClickableItem sets the image back to og

            if not self.opening and not self.closing: # Make it only interactable when not transitioning
                self.opened = not self.opened

                self.opening = self.opened
                self.closing = not self.opened

                if self.opened: glb.sound_engine.playSound("locker_open", 1)
                else: glb.sound_engine.playSound("locker_close", 1)

    def input(self, input_stream):
        if self.unlocked or (glb.engine.player.inventory.current_item_idx != -1 and glb.engine.player.inventory.slots[glb.engine.player.inventory.current_item_idx].name == "locker key"):
            super().input(input_stream) # Still allow interaction

            if self.opened or self.opening:
                # Allow slot interaction, once it is opened
                if self.opened and not (self.opening or self.closing):
                    mouse_pos = input_stream.mouse.getPosition()

                    for index, item in enumerate(self.slots):

                        if item == "": continue # If its an empty slot, dont do anything

                        collides_with_cursor = False

                        # Quickly check if its rotated horizontally or vertically
                        if self.opened_ui_rect.width > self.opened_ui_rect.height: # Rotated horizontally
                            collides_with_cursor = glb.engine.camera.apply(
                                pygame.Rect(self.opened_ui_rect.x + self.slot_offset[0] + index * 64, self.opened_ui_rect.y + self.slot_offset[1], 64, 64)
                            ).collidepoint(mouse_pos)

                        else: # Rotated vertically
                            collides_with_cursor = glb.engine.camera.apply(
                                pygame.Rect(self.opened_ui_rect.x + self.slot_offset[0], self.opened_ui_rect.y + self.slot_offset[1] + index * 64, 64, 64)
                            ).collidepoint(mouse_pos)

                        if collides_with_cursor:
                            # If its clicked, add it to the player's inventory
                            if input_stream.mouse.isButtonPressed(0):
                                item.final_image = item.normal_image # Just so the selected image doesnt carry over to the inventory
                                glb.engine.player.inventory.collect(item)
                                self.slots[index] = "" # Empty the slot

                                break

                            else: item.final_image = item.selected_image

                        else: item.final_image = item.normal_image

                # Close the locker when the player is too far
                if not glb.engine.player.rect.colliderect(self.rect.inflate(96, 96)):
                    self.opened = self.opening = False
                    self.closing = True

                    glb.sound_engine.playSound("locker_close", 1)

    def draw(self, layer_1):
        if self.opening or self.closing:
            target_x, target_y = self.opened_ui_end_pos if self.opening else self.opened_ui_start_pos
            target_alpha = 255 if self.opening else 0

            # Move a fraction of the remaining distance each frame
            dx = target_x     - self.opened_ui_rect.x
            dy = target_y     - self.opened_ui_rect.y
            da = target_alpha - self.ui_alpha

            # 0.2 is for easing in/out effect
            self.opened_ui_rect.x += dx * 0.2
            self.opened_ui_rect.y += dy * 0.2
            self.ui_alpha         += da * 0.2

            # Stop when really close to target
            if abs(dx) < 3 and abs(dy) < 3:
                self.opened_ui_rect.topleft = (target_x, target_y)
                self.ui_alpha = target_alpha
                self.opening = self.closing = False

            self.opened_ui_image.set_alpha(int(self.ui_alpha))

            # Also apply the correct alpha to the slots
            for item in self.slots:
                if item == "": continue # If its an empty slot, dont change anything

                item.final_image.set_alpha(int(self.ui_alpha))

        if self.opened or self.closing: # Also draw the UI if its in the middle of closing
            layer_1.blit(self.opened_ui_image, glb.engine.camera.apply(self.opened_ui_rect))

            # Draw the items in slots too
            for index, item in enumerate(self.slots):

                if item == "": continue # If its an empty slot, dont draw anything

                # Quickly check if its rotated horizontally or vertically
                if self.opened_ui_rect.width > self.opened_ui_rect.height: # Rotated horizontally
                    layer_1.blit(item.final_image, glb.engine.camera.apply(
                        pygame.Rect(self.opened_ui_rect.x + self.slot_offset[0] + index * 64, self.opened_ui_rect.y + self.slot_offset[1], 64, 64)
                    ))

                else: # Rotated vertically
                    layer_1.blit(item.final_image, glb.engine.camera.apply(
                        pygame.Rect(self.opened_ui_rect.x + self.slot_offset[0], self.opened_ui_rect.y + self.slot_offset[1] + index * 64, 64, 64)
                    ))

class Splitter(BaseObject):
    # NOTE: Splitter objects are not interactable

    def __init__(self, type, scr_x, scr_y, tile_pos):
        super().__init__(scr_x, scr_y, "") # Still have to call this because of the pygame.sprite init

        self.image = Tiles.object_tiles[f"SPL_r{ [0, 90, 180, -90][ int(str(type)[-1]) ] }"]
        self.rect.size = self.image.get_size()
        self.mask = pygame.mask.from_surface(self.image)
        self.tile_pos = tile_pos # For keeping track of the position on the tilemap (tuple)

        self.type = type # Can only be 8.0, 8.1, 8.2, 8.3
        self.active = False # If it is actively splitting the laser

    def activate(self):
        # Used by drawLaserPath() when the laser hits the Splitter
        self.active = True

        # Update the image
        self.image = Tiles.object_tiles[f"SPA_r{ [0, 90, 180, -90][ int(str(self.type)[-1]) ] }"]

    def reset(self):
        # Used by drawLaserPath() when it has to reset all laser-affecting objects
        self.active = False

        # Update the image
        self.image = Tiles.object_tiles[f"SPL_r{ [0, 90, 180, -90][ int(str(self.type)[-1]) ] }"]

class GlassBox(TileObject):
    def __init__(self, item, scr_x, scr_y, tile_pos):
        super().__init__(scr_x, scr_y, tile_pos, self.collectLoot, Tiles.object_tiles["GBU"]) # Loading unlocked here so theres no need to generate an outlined version later

        self.og_image = Tiles.object_tiles["GBL"].copy()
        self.image = self.og_image

        self.unlocked = False # Gets unlocked when the laser hits it
        self.item = item # An InterfaceItem object

        # Collecting animation variables
        self.collecting = False
        self.anim_item = self.item
        self.anim_x = scr_x + (self.image.get_width() - self.anim_item.normal_image.get_width()) // 2
        self.anim_start_y = scr_y
        self.anim_end_y = scr_y - 85
        self.anim_current_y = self.anim_start_y
        self.anim_alpha = 0

        # 1 in 5 chance to have ricch
        self.has_ricch = random.randint(1, 5) == 1

        if self.has_ricch:
            self.anim_item = InterfaceItem("ricch", "", pygame.image.load("assets/ui/unused/ricch.png"))
            self.anim_x = scr_x + (self.image.get_width() - self.anim_item.normal_image.get_width()) // 2

    def collectLoot(self):
        self.item = None
        self.image = Tiles.object_tiles["GBE"].copy()

        # Start the animation
        self.collecting = True

        if self.has_ricch:
            glb.sound_engine.playSound("the_glass_box", 1)

        else:
            glb.sound_engine.playSound("glass_box", 1)

    def unlock(self):
        self.unlocked = True
        self.og_image = Tiles.object_tiles["GBU"].copy()
        self.image = self.og_image

        data.score += 100

    def draw(self, layer_1):
        if self.collecting:
            # Move a fraction of the remaining distance each frame
            dy = self.anim_end_y - self.anim_current_y
            da = 255             - self.anim_alpha

            # 0.5 is for easing in/out effect, and 0.05 is for general speed
            self.anim_current_y += (dy * 0.5) * (0.01 if self.has_ricch else 0.05)
            self.anim_alpha     += (da * 0.5) * (0.01 if self.has_ricch else 0.05)

            # Stop when really close to target
            if abs(dy) < (9 if self.has_ricch else 3):
                self.collecting = False

                if not self.has_ricch:
                    self.anim_current_y = self.anim_end_y
                    self.anim_alpha = 255

                    glb.engine.player.inventory.collect(self.anim_item)

            self.anim_item.normal_image.set_alpha(int(self.anim_alpha))

            layer_1.blit(self.anim_item.normal_image, glb.engine.camera.apply(pygame.Rect(self.anim_x, self.anim_current_y, 64, 64)))

# Main level class

class LevelRoom(Map):
    # NOTE: There can only be ONE regular laser reciever for unlocking and ONE regular laser reciever at the laser start (lets the laser in to the room)
    # NOTE: Other connections require a cartain access level and some of those also require a weak laser reciever (quick access)
    # NOTE: Redirectors are primarily objects, but they are also on the tilemap for the lasers to detect
    # NOTE: How entrances and recievers are numbered (start at top left (0), end at bottom right (7))
    #   0   1
    # 2 ##### 3
    #   #   #
    # 4 ##### 5
    #   6   7

    first_time = True

    def __init__(self, main_tilesheet_path, connections, laser_start, locker_items, glass_box_items=None):
        # General Map class init
        self.objects = pygame.sprite.Group()
        self.entities = pygame.sprite.Group()
        self.dropped_items = pygame.sprite.Group()

        # General level stuff
        self.reward_locker_key_dropped = False
        self.reward_locker_key_pos = (0, 0) # This gets updated by the last automaton that died
        self.locker_items = locker_items # Dictionary with keys as "most top-left locker tile coords" and values as 4 item arrays of scrap dictionary keys

        # Not every room has glass boxes btw
        self.glass_box_items = glass_box_items # Dictionary with keys as tile coords and values as InterfaceItems

        self.tilemap = [] # 2D array
        self.map_margin_x = self.map_margin_y = Tiles.size * 4 # In case the map is too small for the camera (but have a 2 tile margin around the entire map by default)

        self.connections = connections
        # Dictionary of all of the rooms this room connects to. The keys are the room names, and the values are tuples of:
        # - requred access level (0 = entrance connection, -X = unlocked with laser and X access level, all other values are general access card levels)
        # - tile position of the enterance tile

        self.laser = laser_start # Dictionary with "start" being a tuple of tile coords, and "direction" being a string
        self.interactable_redirectors = True

        self.assembleMap(main_tilesheet_path)

        # Laser path stuff
        self.laser_surf = pygame.Surface(self.map_image.get_size(), pygame.SRCALPHA)
        self.laser_surf_mask = pygame.mask.from_surface(self.laser_surf) # For collision detection with the player
        self.drawLaserPath()

    # Utility function
    def isFloor(self, i, j):
        # If the position is off of the tilemap it is automatically not floor
        if not (0 <= i < len(self.tilemap) and 0 <= j < len(self.tilemap[0])): return False

        return self.tilemap[i][j] == 1

    def drawLaserBranch(self, starting_x, starting_y, direction_1, direction_2):
        # No need to refresh the laser surface

        self.laserDrawingLogic(starting_x, starting_y, direction_1)
        self.laserDrawingLogic(starting_x, starting_y, direction_2)

    def drawLaserPath(self):
        self.laser_surf.fill((0, 0, 0, 0)) # Refresh the laser surface
        self.laser_surf_mask.clear() # Refresh the laser surface's mask

        # Deactivate ALL Redirectors, Blockers and Splitters (they will get reactivated if supposed to), in case they don't reflect after the update
        for object in self.objects:
            if type(object) == Redirector or type(object) == Blocker or type(object) == Splitter:
                object.reset()

        self.laserDrawingLogic(self.laser["start"][0], self.laser["start"][1], self.laser["direction"])

    def fillLaserBit(self, direction, tile_pos):
        # This function adds an additional pixel of laser to objects that are smaller than their image (a lot of them)
        bit_x = bit_y = 0

        accurate_x, accurate_y = tile_pos[0] * Tiles.size + self.map_margin_x / 2, tile_pos[1] * Tiles.size + self.map_margin_y / 2

        match direction:
            case "up":    bit_x, bit_y = accurate_x, accurate_y - 4 + Tiles.size
            case "down":  bit_x, bit_y = accurate_x, accurate_y
            case "left":  bit_x, bit_y = accurate_x - 4 + Tiles.size, accurate_y
            case "right": bit_x, bit_y = accurate_x, accurate_y

        self.laser_surf.blit(Tiles.other_tiles[f"LSB_r{0 if direction == 'left' or direction == 'right' else 90}"], (bit_x, bit_y))

    def laserDrawingLogic(self, current_x, current_y, direction):
        # Reset all of the weak laser recievers and the doors connected to them (regular recievers dont need this because they only get activated once)
        for i, row in enumerate(self.tilemap):
            for j, tile in enumerate(row):
                x = j * Tiles.size + self.map_margin_x / 2
                y = i * Tiles.size + self.map_margin_y / 2

                if tile == 6:
                    # Reset the weak reciever tile
                    if   self.isFloor(i+1, j): self.map_image.blit(Tiles.wall_tiles["WRC_r0"],   (x, y)) # Top
                    elif self.isFloor(i, j+1): self.map_image.blit(Tiles.wall_tiles["WRC_r90"],  (x, y)) # Left
                    elif self.isFloor(i-1, j): self.map_image.blit(Tiles.wall_tiles["WRC_r180"], (x, y)) # Bottom
                    elif self.isFloor(i, j-1): self.map_image.blit(Tiles.wall_tiles["WRC_r-90"], (x, y)) # Right

        # Find all secondary connections that get unlocked via a weak laser and reset them
        for room_name, (room_access, connection_tile_pos) in self.connections.items():
            if room_name[-2] == "_" and room_name[-1] == "5": # Check if it is a secondary room
                self.connections[room_name] = (-abs(room_access), connection_tile_pos) # Flip the number so its back to the original

                # Change the adjacent door texture to indicate that it can be accessed now
                door_x = connection_tile_pos[0] * Tiles.size + self.map_margin_x / 2
                door_y = connection_tile_pos[1] * Tiles.size + self.map_margin_y / 2

                # Reset the texture
                if   self.isFloor(connection_tile_pos[1]+1, connection_tile_pos[0]): self.map_image.blit(Tiles.wall_tiles["WDO_r0"],   (door_x, door_y)) # Top
                elif self.isFloor(connection_tile_pos[1], connection_tile_pos[0]+1): self.map_image.blit(Tiles.wall_tiles["WDO_r90"],  (door_x, door_y)) # Left
                elif self.isFloor(connection_tile_pos[1]-1, connection_tile_pos[0]): self.map_image.blit(Tiles.wall_tiles["WDO_r180"], (door_x, door_y)) # Bottom
                elif self.isFloor(connection_tile_pos[1], connection_tile_pos[0]-1): self.map_image.blit(Tiles.wall_tiles["WDO_r-90"], (door_x, door_y)) # Right

        # Repeat drawing the laser path until the laser hits a wall, an incorrect redirector, an active blocker or an incorrect splitter
        while True:
            # Convert the current direction to coord steps
            match direction:
                case "up":    x_direction_step, y_direction_step = (0, -1) # X stays the same, Y changes by -1 (goes up)
                case "down":  x_direction_step, y_direction_step = (0,  1) # X stays the same, Y changes by +1 (goes down)
                case "left":  x_direction_step, y_direction_step = (-1, 0) # X changes by -1 (goes left), Y stays the same
                case "right": x_direction_step, y_direction_step = (1,  0) # X changes by +1 (goes right), Y stays the same

            # This part of the while loop gets activated once the direction has been changed
            # So move one step in the current direction so the redirector isnt checked again below (since it has already redirected the laser last iteration)
            current_x += x_direction_step
            current_y += y_direction_step

            # Keep stepping in the current direction until a wall or a redirector is hit
            while 0 <= current_x < len(self.tilemap[0]) and 0 <= current_y < len(self.tilemap):
                tile = self.tilemap[current_y][current_x]

                # If the laser hits a wall tile or a door tile, exit the entire function
                if tile == 3 or tile == 2: return

                # Check if the current tile is a redirector tile (4.0, 4.1, 4.2, 4.3)
                if 4.0 <= tile <= 4.3:
                    # Check if the current redirector can redirect the laser, if so, change the direction and break out of the inner while loop
                    match (direction, tile):
                        # Up-Left redirector (4.0) can redirect a laser thats traveling right or downwards
                        case ("right", 4.0): direction = "up"
                        case ("down",  4.0): direction = "left"

                        # Down-Left redirector (4.1) can redirect a laser thats traveling right or upwards
                        case ("right", 4.1): direction = "down"
                        case ("up",    4.1): direction = "left"

                        # Down-Right redirector (4.2) can redirect a laser thats traveling left or upwards
                        case ("left",  4.2): direction = "down"
                        case ("up",    4.2): direction = "right"

                        # Up-Right redirector (4.3) can redirect a laser thats traveling left or downwards
                        case ("left",  4.3): direction = "up"
                        case ("down",  4.3): direction = "right"

                        # If the current laser direction and redirector type arent compatible (redirector cant redirect), exit the function
                        case _:
                            self.fillLaserBit(direction, (current_x, current_y))

                            return

                    # If the "case _: return" hasn't activated (the redirector is redirecting), change the current redirector's image to an active one
                    for object in self.objects:
                        if object.tile_pos == (current_x, current_y) and not object.active: # Just in case its not already active
                            object.activate() # No need to check for type because tile_pos takes care of that
                            break

                    break

                # If the laser hits the reciever, unlock the only entrance that is locked with it and activate the reciever, and exit the entire function
                if tile == 5:
                    # Find the connection that gets unlocked via laser
                    for room_name, (room_access, connection_tile_pos) in self.connections.items():
                        if (room_access < 0 and # If the access can be flipped AND if its adjacent to the current tile
                            current_x-1 <= connection_tile_pos[0] <= current_x+1 and
                            current_y-1 <= connection_tile_pos[1] <= current_y+1
                            ):
                            self.connections[room_name] = (-room_access, connection_tile_pos) # Flip the number so now only the access card level is required

                            # Change the adjacent door texture to indicate that it can be accessed now
                            door_x = connection_tile_pos[0] * Tiles.size + self.map_margin_x / 2
                            door_y = connection_tile_pos[1] * Tiles.size + self.map_margin_y / 2

                            if   self.isFloor(current_y+1, current_x): self.map_image.blit(Tiles.wall_tiles["WDA_r0"],   (door_x, door_y)) # Top
                            elif self.isFloor(current_y, current_x+1): self.map_image.blit(Tiles.wall_tiles["WDA_r90"],  (door_x, door_y)) # Left
                            elif self.isFloor(current_y-1, current_x): self.map_image.blit(Tiles.wall_tiles["WDA_r180"], (door_x, door_y)) # Bottom
                            elif self.isFloor(current_y, current_x-1): self.map_image.blit(Tiles.wall_tiles["WDA_r-90"], (door_x, door_y)) # Right

                            break

                    x = current_x * Tiles.size + self.map_margin_x / 2
                    y = current_y * Tiles.size + self.map_margin_y / 2

                    # Activate the reciever tile
                    if   self.isFloor(current_y+1, current_x): self.map_image.blit(Tiles.wall_tiles["RAC_r0"],   (x, y)) # Top
                    elif self.isFloor(current_y, current_x+1): self.map_image.blit(Tiles.wall_tiles["RAC_r90"],  (x, y)) # Left
                    elif self.isFloor(current_y-1, current_x): self.map_image.blit(Tiles.wall_tiles["RAC_r180"], (x, y)) # Bottom
                    elif self.isFloor(current_y, current_x-1): self.map_image.blit(Tiles.wall_tiles["RAC_r-90"], (x, y)) # Right

                    self.interactable_redirectors = False # The laser has reached its goal, so the redirectors can no longer be interacted with

                    glb.sound_engine.playSound("reciever", 1)

                    data.score += 100

                    # Set all redirectors to active and all blockers to inactive
                    for object in self.objects:
                        if type(object) == Redirector:
                            object.activate()
                            object.image = object.og_image

                        elif type(object) == Blocker:
                            object.reset()

                    return

                # Check if the current tile is a weak reciever tile
                if tile == 6:
                    # Find the connection that gets unlocked via a weak laser
                    for room_name, (room_access, connection_tile_pos) in self.connections.items():
                        if room_access < 0 and room_name[-2] == "_" and room_name[-1] == "5": # Additionally check if it is a secondary room
                            self.connections[room_name] = (-room_access, connection_tile_pos) # Flip the number so now only the access card level is required

                            # Change the adjacent door texture to indicate that it can be accessed now
                            door_x = connection_tile_pos[0] * Tiles.size + self.map_margin_x / 2
                            door_y = connection_tile_pos[1] * Tiles.size + self.map_margin_y / 2

                            if   self.isFloor(current_y+1, current_x): self.map_image.blit(Tiles.wall_tiles["WDA_r0"],   (door_x, door_y)) # Top
                            elif self.isFloor(current_y, current_x+1): self.map_image.blit(Tiles.wall_tiles["WDA_r90"],  (door_x, door_y)) # Left
                            elif self.isFloor(current_y-1, current_x): self.map_image.blit(Tiles.wall_tiles["WDA_r180"], (door_x, door_y)) # Bottom
                            elif self.isFloor(current_y, current_x-1): self.map_image.blit(Tiles.wall_tiles["WDA_r-90"], (door_x, door_y)) # Right

                            break

                    x = current_x * Tiles.size + self.map_margin_x / 2
                    y = current_y * Tiles.size + self.map_margin_y / 2

                    # Activate the weak reciever tile
                    if   self.isFloor(current_y+1, current_x): self.map_image.blit(Tiles.wall_tiles["WRA_r0"],   (x, y)) # Top
                    elif self.isFloor(current_y, current_x+1): self.map_image.blit(Tiles.wall_tiles["WRA_r90"],  (x, y)) # Left
                    elif self.isFloor(current_y-1, current_x): self.map_image.blit(Tiles.wall_tiles["WRA_r180"], (x, y)) # Bottom
                    elif self.isFloor(current_y, current_x-1): self.map_image.blit(Tiles.wall_tiles["WRA_r-90"], (x, y)) # Right

                    return

                # Check if the current tile is a blocker tile (7.0, 7.1, 7.2, 7.3)
                if 7.0 <= tile <= 7.3:
                    # Find the current blocker object
                    for object in self.objects:
                        if object.tile_pos == (current_x, current_y):
                            # Check if the blocker direction and laser direction oppose
                            if ((tile == 7.0 and direction == "down") or
                                (tile == 7.1 and direction == "right") or
                                (tile == 7.2 and direction == "up") or
                                (tile == 7.3 and direction == "left")):

                                # If the blocker is actively blocking, update its texture and exit the entire function
                                if object.active:
                                    object.activate()
                                    return

                                break # If the blocker is not actively blocking, break out of the inner while loop so the laser can continue

                            # The blocker is facing the wrong direction
                            else:
                                self.fillLaserBit(direction, (current_x, current_y))

                                return

                # Check if the current tile is a splitter tile (8.0, 8.1, 8.2, 8.3)
                if 8.0 <= tile <= 8.3:
                    # Figure out the two new branches
                    match tile:
                        case 8.0:
                            match direction:
                                case "up":    self.drawLaserBranch(current_x, current_y, "left", "up")
                                case "down":  self.drawLaserBranch(current_x, current_y, "left", "down")
                                case "left": 
                                    self.fillLaserBit(direction, (current_x, current_y))
                                    return # Dont make any new branches because the laser is hitting the wrong side
                                case "right": self.drawLaserBranch(current_x, current_y, "up", "down")

                        case 8.1:
                            match direction:
                                case "up":    self.drawLaserBranch(current_x, current_y, "left", "right")
                                case "down": 
                                    self.fillLaserBit(direction, (current_x, current_y))
                                    return # Dont make any new branches because the laser is hitting the wrong side
                                case "left":  self.drawLaserBranch(current_x, current_y, "left", "down")
                                case "right": self.drawLaserBranch(current_x, current_y, "right", "down")

                        case 8.2:
                            match direction:
                                case "up":    self.drawLaserBranch(current_x, current_y, "up", "right")
                                case "down":  self.drawLaserBranch(current_x, current_y, "down", "right")
                                case "left":  self.drawLaserBranch(current_x, current_y, "up", "down")
                                case "right": 
                                    self.fillLaserBit(direction, (current_x, current_y))
                                    return # Dont make any new branches because the laser is hitting the wrong side

                        case 8.3:
                            match direction:
                                case "up": 
                                    self.fillLaserBit(direction, (current_x, current_y))
                                    return # Dont make any new branches because the laser is hitting the wrong side
                                case "down":  self.drawLaserBranch(current_x, current_y, "left", "right")
                                case "left":  self.drawLaserBranch(current_x, current_y, "left", "up")
                                case "right": self.drawLaserBranch(current_x, current_y, "right", "up")

                    # Change the current splitter's image to an active one
                    for object in self.objects:
                        if object.tile_pos == (current_x, current_y) and not object.active: # Just in case its not already active
                            object.activate() # No need to check for type because tile_pos takes care of that
                            break

                    # The laser will continue in the form of two new branches (or not in certain cases)
                    return

                # If the laser hits a glass box, unlock it and stop the laser
                if tile == 11:
                    # Change the current splitter's image to an active one
                    for object in self.objects:
                        if object.tile_pos == (current_x, current_y) and not object.unlocked: # Just in case its not already unlocked
                            object.unlock() # No need to check for type because tile_pos takes care of that
                            break

                    self.fillLaserBit(direction, (current_x, current_y))

                    return

                # The if statements above always break the loop if True (either with break or return)
                # So if the current tile is NOT a redirector tile nor a wall, draw the laser and move a step further in the same direction
                self.laser_surf.blit(Tiles.other_tiles[f"LAS_r{0 if direction == 'left' or direction == 'right' else 90}"], (
                    current_x * Tiles.size + self.map_margin_x / 2,
                    current_y * Tiles.size + self.map_margin_y / 2
                ))

                # Also draw a laser mask on to the actual laser_surf_mask for the player's collision detection
                laser_beam_mask_x = 24 if direction == 'up' or direction == 'down' else 0
                laser_beam_mask_y = 24 if direction == 'left' or direction == 'right' else 0

                self.laser_surf_mask.draw( # The size of the laser beam scaled up
                    pygame.Mask((18 * 4, 6 * 4) if direction == 'left' or direction == 'right' else (6 * 4, 18 * 4), fill=True), 
                    (
                        current_x * Tiles.size + self.map_margin_x / 2 + laser_beam_mask_x,
                        current_y * Tiles.size + self.map_margin_y / 2 + laser_beam_mask_y
                    )
                )

                current_x += x_direction_step
                current_y += y_direction_step

    def assembleMap(self, main_tilesheet_path):
        # Convert tilesheet to the tilemap
        tilesheet = pygame.image.load(main_tilesheet_path).convert()

        for y in range(tilesheet.get_height()):
            row = []

            for x in range(tilesheet.get_width()):
                row.append(Tiles.dictionary[tuple(tilesheet.get_at((x, y)))])

            self.tilemap.append(row)

        # Construct/draw tiles to the map_image
        width, height = len(self.tilemap[0]) * Tiles.size, len(self.tilemap) * Tiles.size

        # If the tilemap is too small make it just big enough for the camera
        if width  + self.map_margin_x < glb.screen_width:  self.map_margin_x += glb.screen_width  - (width  + self.map_margin_x)
        if height + self.map_margin_y < glb.screen_height: self.map_margin_y += glb.screen_height - (height + self.map_margin_y)

        self.map_image = pygame.Surface((width + self.map_margin_x, height + self.map_margin_y))
        self.map_rect = self.map_image.get_rect()
        self.map_borders = (0, 0, 0, 0)

        # For wall drawing logic
        # Solid == 1: For checking if tile at i and j is solid (not empty, not wall, not entrance, not any reciever)
        # Solid == 0: For checking if tile at i and j is empty
        def isTile(i, j, solid):
            # If the position is off of the tilemap it is automatically empty/NOT solid
            if not (0 <= i < len(self.tilemap) and 0 <= j < len(self.tilemap[0])):
                return not solid

            if solid: return self.tilemap[i][j] not in (0, 3, 2, 5, 6)
            else: return self.tilemap[i][j] == 0

        # Drawing the checkerboard floor
        for i, row in enumerate(self.tilemap):
            # For a checkerboard pattern (0 and 1)
            if i % 4 == 0: current_floor_tile_type = 1
            else: current_floor_tile_type = 0

            # So it doesnt draw outside of the tile map
            if i + 1 == len(self.tilemap): break

            for j, tile in enumerate(row):
                x = j * Tiles.size + self.map_margin_x / 2
                y = i * Tiles.size + self.map_margin_y / 2

                # So it doesnt draw outside of the tile map
                if j + 1 == len(row): break

                # Place a new floor tile every two regular tiles
                if j % 2 == 0 and i % 2 == 0:
                    floor_tile_image = None

                    # Have a random chance to have a broken floor tile
                    if random.randint(1, 7) == 1: floor_tile_image = Tiles.floor_tiles[f"F{current_floor_tile_type + 1}B"]
                    else:                         floor_tile_image = Tiles.floor_tiles[f"FL{current_floor_tile_type + 1}"]

                    # Have a random chance to have the tile rotated
                    if random.randint(1, 15) == 1: floor_tile_image = pygame.transform.rotate(floor_tile_image, 180)

                    self.map_image.blit(floor_tile_image, (x, y))

                    current_floor_tile_type = 1 if current_floor_tile_type == 0 else 0 # Flip the type

        # Assemble the actual map_image
        for i, row in enumerate(self.tilemap):
            for j, tile in enumerate(row):
                x = j * Tiles.size + self.map_margin_x / 2
                y = i * Tiles.size + self.map_margin_y / 2

                match tile:
                    case 0:
                        # Drawing the void
                        pygame.draw.rect(self.map_image, (0, 0, 0), (x, y, Tiles.size, Tiles.size))

                    case 1:
                        pass # The floor tiles were already blitted above

                    case 2:
                        # Drawing doors
                        # If the door is adjacent to the laser start, make it active to signal the player can move through it
                        if (self.laser["start"][0] in range(j-1, j+2) and self.laser["start"][1] in range(i-1, i+2)):
                            adjacent_laser = True
                        else:
                            adjacent_laser = False

                        if   isTile(i+1, j, 1): self.map_image.blit(Tiles.wall_tiles[f"WD{'A' if adjacent_laser else 'O'}_r0"],   (x, y)) # Top
                        elif isTile(i, j+1, 1): self.map_image.blit(Tiles.wall_tiles[f"WD{'A' if adjacent_laser else 'O'}_r90"],  (x, y)) # Left
                        elif isTile(i-1, j, 1): self.map_image.blit(Tiles.wall_tiles[f"WD{'A' if adjacent_laser else 'O'}_r180"], (x, y)) # Bottom
                        elif isTile(i, j-1, 1): self.map_image.blit(Tiles.wall_tiles[f"WD{'A' if adjacent_laser else 'O'}_r-90"], (x, y)) # Right

                    case 3:
                        # Normal walls
                        if   isTile(i+1, j, 1): self.map_image.blit(Tiles.wall_tiles[f"WLN_r0"],   (x, y)) # Top
                        elif isTile(i, j+1, 1): self.map_image.blit(Tiles.wall_tiles[f"WLN_r90"],  (x, y)) # Left
                        elif isTile(i-1, j, 1): self.map_image.blit(Tiles.wall_tiles[f"WLN_r180"], (x, y)) # Bottom
                        elif isTile(i, j-1, 1): self.map_image.blit(Tiles.wall_tiles[f"WLN_r-90"], (x, y)) # Right

                        # Outer corners
                        if   isTile(i-1, j, 0) and isTile(i, j-1, 0): self.map_image.blit(Tiles.wall_tiles[f"WOC_r0"],   (x, y))
                        elif isTile(i+1, j, 0) and isTile(i, j-1, 0): self.map_image.blit(Tiles.wall_tiles[f"WOC_r90"],  (x, y))
                        elif isTile(i+1, j, 0) and isTile(i, j+1, 0): self.map_image.blit(Tiles.wall_tiles[f"WOC_r180"], (x, y))
                        elif isTile(i-1, j, 0) and isTile(i, j+1, 0): self.map_image.blit(Tiles.wall_tiles[f"WOC_r-90"], (x, y))

                        # Inner corners
                        if   isTile(i+1, j, 1) and isTile(i, j+1, 1) and isTile(i-1, j-1, 0): self.map_image.blit(Tiles.wall_tiles[f"WIC_r0"],   (x, y))
                        elif isTile(i-1, j, 1) and isTile(i, j+1, 1) and isTile(i+1, j-1, 0): self.map_image.blit(Tiles.wall_tiles[f"WIC_r90"],  (x, y))
                        elif isTile(i-1, j, 1) and isTile(i, j-1, 1) and isTile(i+1, j+1, 0): self.map_image.blit(Tiles.wall_tiles[f"WIC_r180"], (x, y))
                        elif isTile(i+1, j, 1) and isTile(i, j-1, 1) and isTile(i-1, j+1, 0): self.map_image.blit(Tiles.wall_tiles[f"WIC_r-90"], (x, y))

                    case 4.0 | 4.1 | 4.2 | 4.3: self.objects.add(Redirector(tile, x, y, (j, i))) # Redirectors

                    case 5:
                        # Drawing regular recievers
                        # If its at the same position as the laser start, make it appear active because that one lets the laser into the room
                        shining_laser = self.laser["start"] == (j, i)

                        if   isTile(i+1, j, 1): self.map_image.blit(Tiles.wall_tiles[f"R{'A' if shining_laser else 'E'}C_r0"],   (x, y)) # Top
                        elif isTile(i, j+1, 1): self.map_image.blit(Tiles.wall_tiles[f"R{'A' if shining_laser else 'E'}C_r90"],  (x, y)) # Left
                        elif isTile(i-1, j, 1): self.map_image.blit(Tiles.wall_tiles[f"R{'A' if shining_laser else 'E'}C_r180"], (x, y)) # Bottom
                        elif isTile(i, j-1, 1): self.map_image.blit(Tiles.wall_tiles[f"R{'A' if shining_laser else 'E'}C_r-90"], (x, y)) # Right

                    case 6:
                        # Drawing weak recievers
                        if   isTile(i+1, j, 1): self.map_image.blit(Tiles.wall_tiles[f"WRC_r0"],   (x, y)) # Top
                        elif isTile(i, j+1, 1): self.map_image.blit(Tiles.wall_tiles[f"WRC_r90"],  (x, y)) # Left
                        elif isTile(i-1, j, 1): self.map_image.blit(Tiles.wall_tiles[f"WRC_r180"], (x, y)) # Bottom
                        elif isTile(i, j-1, 1): self.map_image.blit(Tiles.wall_tiles[f"WRC_r-90"], (x, y)) # Right

                    case 7.0 | 7.1 | 7.2 | 7.3: self.objects.add(Blocker(tile, x, y, (j, i))) # Blockers

                    case 8.0 | 8.1 | 8.2 | 8.3: self.objects.add(Splitter(tile, x, y, (j, i))) # Splitters

                    case 9.0 | 9.1 | 9.2:
                        # Drawing lockers
                        # Check if there doesnt exist an adjacent locker tile that is more to the left or up (means the current one is the primary locker tile)
                        if self.tilemap[i][j-1] != tile and self.tilemap[i-1][j] != tile:
                            # Check in which direction is the non primary locker tile -- get the value of the current locker's slots with the current tile position

                            if self.tilemap[i][j+1] == tile: # Horizontal positioning
                                self.objects.add(Locker(tile, self.locker_items[(j ,i)], x, y, (j, i), 180 if isTile(i-1, j, 1) else 0))

                            elif self.tilemap[i+1][j] == tile: # Vertical positioning
                                self.objects.add(Locker(tile, self.locker_items[(j ,i)], x, y, (j, i), -90 if isTile(i, j-1, 1) else 90))

                    case 10: self.entities.add(Automaton(x, y, self)) # Automatons

                    case 11: self.objects.add(GlassBox(self.glass_box_items[(j ,i)], x, y, (j, i))) # Glass boxes

    def onEnter(self, entering_from):
        if LevelRoom.first_time:
            LevelRoom.first_time = False

            glb.engine.om.setObjective(ObjectivesManager.possible_objectives[7])

        for room_name, (room_access, connection_tile_pos) in self.connections.items():
            if room_name == entering_from:
                self.interaction = True

                x = connection_tile_pos[0]
                y = connection_tile_pos[1]

                # Check direct neighbor offsets (up, down, left, right)
                for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                    nx, ny = x + dx, y + dy

                    # Check tilemap bounds and if the current direct neighbor is floor
                    if 0 <= ny < len(self.tilemap) and 0 <= nx < len(self.tilemap[0]) and self.tilemap[ny][nx] == 1:
                        # Move the players position to the closest floor tile to the entrance
                        x, y = nx, ny
                        break

                player_x = x * Tiles.size + (Tiles.size + self.map_margin_x - glb.engine.player.rect.width) // 2
                player_y = y * Tiles.size + (Tiles.size + self.map_margin_y - glb.engine.player.rect.height) // 2

                # Spawn the player in the middle of the tile
                glb.engine.player.changeXY(
                    player_x + (player_x % 4), # Round up to the nearest multiple of 4 so the player is on the grid
                    player_y + (player_y % 4)
                )
                glb.engine.camera.update(glb.engine.player, False)

                break

    def update(self):
        if self.interaction:
            player = glb.engine.player

            # 1 = Up, 2 = Left, 3 = Down, 4 = Right
            match player.direction:
                case 1 | 3: inflated_player_rect = player.rect.inflate(0, 2)
                case 2 | 4: inflated_player_rect = player.rect.inflate(2, 0)

            for room_name, (room_access, connection_tile_pos) in self.connections.items():
                # Only enter if it is the entrance connection (already unlocked) or if the player has a high enough access level
                if room_access == 0 or (room_access > 0 and player.current_access_lvl >= room_access):
                    connection_tile_rect = pygame.Rect(
                        connection_tile_pos[0] * Tiles.size + self.map_margin_x // 2,
                        connection_tile_pos[1] * Tiles.size + self.map_margin_y // 2,
                        Tiles.size, Tiles.size
                    )

                    if connection_tile_rect.colliderect(inflated_player_rect):
                        self.interaction = False

                        glb.engine.rm.moveTo(room_name)

        # If the player doesnt have the reward locker key yet, and theres no more enemies left
        if not self.reward_locker_key_dropped and len(self.entities) == 0:
            self.dropped_items.add(PickupableItem("locker key", self.reward_locker_key_pos[0], self.reward_locker_key_pos[1], "assets/items/locker_key.png"))
            self.reward_locker_key_dropped = True
            self.interactable_redirectors = True
