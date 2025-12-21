import pygame
import pygame.freetype

pygame.freetype.init() # For the Typer

# Returns the loaded image asset, scaled up 4 times, optionally rotated
# Intended to prevent having to manually scale up every pixel art image
def loadScaledAsset(image_path, scale=4, rotation=0):
    image = pygame.image.load(image_path)

    if rotation != 0: image = pygame.transform.rotate(image, rotation)

    width, height = image.get_size()

    return pygame.transform.scale(image, (width * scale, height * scale))

class SmallFont:
    # NOTE: These variables are at class level, so all SmallFont instances have the same ones

    BASE_SPACING = 16

    STANDARD_WIDTH = 16
    WIDE_WIDTH = 24
    WIDTH_ADJUST = { 'I': -8, '.': -8, '!': -8, 'M': 8, 'W': 8 }

    GLYPH_HEIGHT = 20
    LINE_HEIGHT = 28

    def __init__(self, color):
        stencil = loadScaledAsset("assets/fonts/small_font.png").convert()
        stencil.set_colorkey((255, 255, 255)) # Make the white color transparent

        self.image = pygame.Surface(stencil.get_size(), pygame.SRCALPHA)
        self.image.fill(color)
        self.image.blit(stencil, (0, 0)) # Blit the source with the old color colorkeyed off, which leaves glyph pixels
        self.image.set_colorkey((0, 0, 0)) # Make the color of the stencil (black) transparent

        # Dictionary with keys as characters and values as subsurfaces of the scaled up font image
        self.glyphs = {}

        # Extract number glyphs
        for i, ch in enumerate("1234567890_.!"):
            self.glyphs[ch] = self.image.subsurface((i * 16, 0, SmallFont.STANDARD_WIDTH, SmallFont.GLYPH_HEIGHT))

        # Extract letter glyphs
        for i, ch in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
            match ch:
                case 'M': self.glyphs[ch] = self.image.subsurface((368,    0,  SmallFont.WIDE_WIDTH,     SmallFont.GLYPH_HEIGHT))
                case 'W': self.glyphs[ch] = self.image.subsurface((392,    0,  SmallFont.WIDE_WIDTH,     SmallFont.GLYPH_HEIGHT))
                case _:   self.glyphs[ch] = self.image.subsurface((i * 16, 20, SmallFont.STANDARD_WIDTH, SmallFont.GLYPH_HEIGHT))

    def render(self, text):
        # Calculate height
        surf_height = (text.count("\n") + 1) * self.LINE_HEIGHT

        # Calculate width
        surf_width = 0
        rows = text.split('\n') if '\n' in text else [text]

        for row in rows:
            width = len(row) * SmallFont.BASE_SPACING - 4 # The last character leaves 4px free, so they have to be removed

            # Apply width adjustments if any of those letters are found
            width += sum(SmallFont.WIDTH_ADJUST.get(ch, 0) for ch in row.upper()) # get(ch, 0) returns 0 if the key doesnt exist

            if width > surf_width: surf_width = width

        # Create the actual text surface
        render_surf = pygame.Surface((surf_width, surf_height), pygame.SRCALPHA)

        x_pos = y_pos = 0
        prev_ch_upper = None

        for ch in text:
            # Handle spacing adjustments from the previous character
            if prev_ch_upper and prev_ch_upper in self.WIDTH_ADJUST:
                x_pos += self.WIDTH_ADJUST[prev_ch_upper]

            # Handle newline
            if ch == "\n":
                x_pos = 0
                y_pos += self.LINE_HEIGHT
                prev_ch_upper = None

                continue

            # Handle space
            if ch == " ":
                x_pos += self.BASE_SPACING
                prev_ch_upper = None

                continue

            # Get glyph from pre-extracted cache
            ch_upper = ch.upper()
            glyph = self.glyphs.get(ch_upper)

            if glyph is None:
                print(f"Unsupported character for SmallFont: \"{ch_upper}\"")
                prev_ch_upper = None

                continue

            # Blit the glyph
            render_surf.blit(glyph, (x_pos, y_pos))
            x_pos += self.BASE_SPACING
            prev_ch_upper = ch_upper

        return render_surf

class Button:
    def __init__(self, pos, image, hover_image, callback):
        self.image = loadScaledAsset(image)
        self.hover_image = loadScaledAsset(hover_image)
        self.current_image = self.image

        self.pos = pos
        self.rect = pygame.Rect(self.pos[0], self.pos[1], self.current_image.get_width(), self.current_image.get_height())

        self.callback = callback

    def input(self, input_stream):
        if self.rect.collidepoint(input_stream.mouse.getPosition()):
            self.current_image = self.hover_image
            self.rect.size = self.current_image.get_size()

            if input_stream.mouse.isButtonPressed(0):
                # Reset the visuals
                self.current_image = self.image
                self.rect.size = self.current_image.get_size()

                self.callback()

        else:
            self.current_image = self.image
            self.rect.size = self.current_image.get_size()

class Switch:
    default_on_image = loadScaledAsset("assets/ui/switch_on.png")
    default_on_hover_image = loadScaledAsset("assets/ui/switch_on_hovered.png")
    default_off_image = loadScaledAsset("assets/ui/switch_off.png")
    default_off_hover_image = loadScaledAsset("assets/ui/switch_off_hovered.png")

    def __init__(self, starting_value, pos, on_image="", on_hover_image="", off_image="", off_hover_image=""):
        self.on_image        = on_image        if on_image        != "" else Switch.default_on_image
        self.on_hover_image  = on_hover_image  if on_hover_image  != "" else Switch.default_on_hover_image
        self.off_image       = off_image       if off_image       != "" else Switch.default_off_image
        self.off_hover_image = off_hover_image if off_hover_image != "" else Switch.default_off_hover_image

        self.image       = self.on_image       if starting_value else self.off_image
        self.hover_image = self.on_hover_image if starting_value else self.off_hover_image

        self.current_image = self.image

        self.pos = pos
        self.rect = pygame.Rect(self.pos[0], self.pos[1], self.current_image.get_width(), self.current_image.get_height())

        self.current_value = starting_value # Boolean

    def input(self, input_stream):
        if self.rect.collidepoint(input_stream.mouse.getPosition()):
            self.current_image = self.hover_image
            self.rect.size = self.current_image.get_size()

            if input_stream.mouse.isButtonPressed(0):
                self.current_value = not self.current_value # Flip the current value

                self.image       = self.on_image       if self.current_value else self.off_image
                self.hover_image = self.on_hover_image if self.current_value else self.off_hover_image
                self.current_image = self.hover_image

                self.rect.size = self.current_image.get_size()

                return self.current_value

        else:
            self.current_image = self.image
            self.rect.size = self.current_image.get_size()

class Slider:
    def __init__(self, pos, initial_val, min_val, max_val):
        # Values
        self.min_val = min_val
        self.max_val = max_val
        self.current_val = initial_val

        # Images
        self.track_image   = loadScaledAsset("assets/ui/slider_track.png").convert_alpha()
        self.handle_image  = loadScaledAsset("assets/ui/slider_handle.png").convert_alpha()
        self.og_value_display = loadScaledAsset("assets/ui/slider_value_display.png").convert_alpha() # Value display will get refreshed with this every frame
        self.value_display = self.og_value_display.copy()
        self.value_display_overlay = loadScaledAsset("assets/ui/slider_value_display_overlay.png").convert_alpha()

        self.value_display_font = SmallFont((212, 0, 0, 255))

        # Display the initial value
        self.renderValue(str(self.current_val))
        self.value_display.blit(self.value_display_overlay, (0, 0))

        # Rects
        self.track_rect  = pygame.Rect(pos[0], pos[1], self.track_image.get_width(),  self.track_image.get_height())
        self.handle_rect = pygame.Rect(pos[0], pos[1], self.handle_image.get_width(), self.handle_image.get_height())

        self.left_right_margin = 8

        # Update the initial position of the handle
        normalized_val = (initial_val - self.min_val) / (self.max_val - self.min_val)
        handle_x = normalized_val * self.track_rect.width - self.handle_rect.width // 2

        self.handle_rect.x += handle_x

        self.handle_grabbed = False

    def renderValue(self, num_str):
        # Add buffers
        if len(num_str) < 3: num_str = f"0{num_str}"
        if len(num_str) < 3: num_str = f"0{num_str}"

        self.value_display.blit(self.value_display_font.render(num_str), (8, 12))

    def input(self, input_stream):
        if self.track_rect.collidepoint(input_stream.mouse.getPosition()):
            if input_stream.mouse.isButtonPressed(0):
                self.handle_grabbed = True

        if input_stream.mouse.isButtonReleased(0) and self.handle_grabbed:
            self.handle_grabbed = False

            # When the slider is released apply the current value
            return self.current_val

        # While the left button is down, move the slider to its position
        if self.handle_grabbed:
            previous_value = self.current_val
            pos_x = input_stream.mouse.getPosition()[0] # Get the x position

            # So the slider handle doesn't go over bounds
            if pos_x < self.track_rect.left + self.left_right_margin + self.handle_rect.width // 2:
                pos_x = self.track_rect.left  + self.left_right_margin + self.handle_rect.width // 2

            if pos_x > self.track_rect.right - self.left_right_margin - self.handle_rect.width // 2:
                pos_x = self.track_rect.right  - self.left_right_margin - self.handle_rect.width // 2

            self.handle_rect.centerx = pos_x

            # Update the new value
            rel_x = self.handle_rect.x - (self.track_rect.x + self.left_right_margin)
            usable_width = self.track_rect.width - 2 * self.left_right_margin - self.handle_rect.width
            normalized_val = rel_x / usable_width

            self.current_val = round(self.min_val + normalized_val * (self.max_val - self.min_val))

            # Only display the new value if its different
            if self.current_val != previous_value:
                self.value_display.blit(self.og_value_display, (0, 0))
                self.renderValue(str(self.current_val))
                self.value_display.blit(self.value_display_overlay, (0, 0))

class Toggle:
    def __init__(self, states, pos):
        self.back_image = loadScaledAsset("assets/ui/toggle_back.png").convert_alpha()
        self.handle_image = loadScaledAsset("assets/ui/toggle_handle.png").convert_alpha()

        self.handle_margins = 4

        self.back_rect   = pygame.Rect(pos[0], pos[1], self.back_image.get_width(),   self.back_image.get_height())
        self.handle_rect = pygame.Rect(pos[0] + self.handle_margins, pos[1] + self.handle_margins, self.handle_image.get_width(), self.handle_image.get_height())

        # NOTE: The default state is always the first one in the tuple

        self.states = states # A tuple of the two possible states
        self.current_state = self.states[0]

        # Transition variables
        self.going_left = False
        self.going_right = False

    def input(self, input_stream):
        if (self.handle_rect.collidepoint(input_stream.mouse.getPosition()) and input_stream.mouse.isButtonPressed(0)
            and (self.handle_rect.left == self.back_rect.left + self.handle_margins or self.handle_rect.right == self.back_rect.right - self.handle_margins)):
            # Handle is on the left side
            if self.handle_rect.left == self.back_rect.left + self.handle_margins:
                self.going_right = True
                self.going_left = False
                self.handle_rect.right += 1 # To kick off the transition

            # Handle is on the right side
            elif self.handle_rect.right == self.back_rect.right - self.handle_margins:
                self.going_left = True
                self.going_right = False
                self.handle_rect.left -= 1 # To kick off the transition

            # Flip the state and return it
            self.current_state = self.states[1] if self.current_state == self.states[0] else self.states[0]

            return self.current_state

        # Transition
        if self.going_left:
            progress = self.handle_rect.left / (self.handle_rect.left - self.back_rect.left + self.handle_margins)

            self.handle_rect.left += 0.2 * (progress ** 0.2 * (1 - progress))

            # When it gets really close, just snap it
            if self.handle_rect.left <= self.back_rect.left + self.handle_margins + 0.5:
                self.handle_rect.left = self.back_rect.left + self.handle_margins
                self.going_left = False

        elif self.going_right:
            progress = self.handle_rect.right / (self.back_rect.right - self.handle_margins - self.handle_rect.right)

            self.handle_rect.right -= 0.2 * (progress ** 0.2 * (1 - progress))

            # When it gets really close, just snap it
            if self.handle_rect.right >= self.back_rect.right - self.handle_margins - 0.5:
                self.handle_rect.right = self.back_rect.right - self.handle_margins
                self.going_right = False

class ReMapper:
    def __init__(self, initial_key, pos):
        self.og_image = loadScaledAsset("assets/ui/remapper.png").convert_alpha()
        self.image = self.og_image.copy()

        self.key_name_font = SmallFont((255, 255, 255, 255))

        self.rect = pygame.Rect(pos[0], pos[1], self.image.get_width(), self.image.get_height())

        self.current_key = initial_key
        self.listening = False
        self.blink_timer = 0
        self.blink_displayed = False

        self.renderKeyName(pygame.key.name(self.current_key))

    def renderKeyName(self, text):
        self.image = self.og_image.copy()

        render = self.key_name_font.render(text)

        self.image.blit(render, ((self.rect.width - render.get_width() + 4) // 2, 12)) # +4 because MOST glyphs have an empty pixel after them

    def input(self, input_stream):
        if input_stream.mouse.isButtonPressed(0):
            # If the player clicked on the remapper, start listening
            if self.rect.collidepoint(input_stream.mouse.getPosition()):
                self.listening = True

                # Start the blinking with the blink shown
                self.blink_displayed = True
                self.blink_timer = 0
                self.renderKeyName("___")

            # If the player clicked away while the remapper was listening, stop listening and fallback to the previous key
            elif self.listening:
                self.listening = False

                self.renderKeyName(pygame.key.name(self.current_key))

        if self.listening:
            # Blinking logic
            if self.blink_timer < 75:
                self.blink_timer += 1

                if self.blink_timer == 75:
                    self.blink_timer = 0
                    self.blink_displayed = not self.blink_displayed # Flip

                    if self.blink_displayed: self.renderKeyName("___")
                    else: self.image = self.og_image.copy()

            for event in input_stream.general_events:
                if event.type == pygame.KEYDOWN:
                    self.listening = False
                    self.current_key = event.key

                    self.renderKeyName(pygame.key.name(self.current_key))

                    return self.current_key

class Typer:
    def __init__(self, color):
        # General stuff
        self.active = False
        self.font = SmallFont(color)
        self.text_arr = []
        self.pos = (0, 0)

        # Character timing
        self.char_delay = 10
        self.char_timer = 0

        # Indexes
        self.char_idx = 0
        self.row_idx = 0

        self.callback = None

        # Variables for caching
        self.rendered_lines = []
        self.current_line_text = ""

    def startTyping(self, text, pos, callback, char_delay=10):
        self.active = True
        self.text_arr = text.split('\n')
        self.pos = pos

        # Character timing
        self.char_delay = char_delay
        self.char_timer = self.char_delay - 1

        # Reset indexes
        self.char_idx = 0
        self.row_idx = 0

        self.callback = callback

        # Reset cache
        self.rendered_lines = []
        self.current_line_text = ""

    def update(self):
        self.char_timer += 1

        # Quick timer logic
        if self.char_timer >= self.char_delay:
            self.char_timer = 0
            self.char_idx += 1

            current_line = self.text_arr[self.row_idx]

            # Check if the current line is finished
            if self.char_idx > len(current_line):
                # Store the completed line (no need to re-render it)
                self.rendered_lines.append(current_line)

                self.char_idx = 0
                self.row_idx += 1
                self.current_line_text = ""

                # Check if all of the lines are finished
                if self.row_idx >= len(self.text_arr):
                    self.active = False
                    self.text_arr = []
                    self.pos = (0, 0)

                    self.char_delay = 10
                    self.char_timer = 0

                    self.char_idx = 0
                    self.row_idx = 0

                    self.rendered_lines = []
                    self.current_line_text = ""

                    if self.callback:
                        self.callback()

            else:
                # Update current line text for rendering
                self.current_line_text = current_line[:self.char_idx]

    def draw(self, layer_1):
        # Draw all completed lines
        y_offset = self.pos[1] - SmallFont.LINE_HEIGHT  # Start one line higher

        for line_text in self.rendered_lines:
            layer_1.blit(self.font.render(line_text), (self.pos[0], y_offset))
            y_offset += SmallFont.LINE_HEIGHT

        # Draw the current line being typed
        if self.current_line_text:
            layer_1.blit(self.font.render(self.current_line_text), (self.pos[0], y_offset))
