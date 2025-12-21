import pygame
import globals as glb
import settings
import engine
import random
import utils
import data
from PIL import Image

class SceneTransition:
    def __init__(self):
        self.fade_surface = pygame.Surface((glb.screen_width, glb.screen_height))
        self.fade_surface.fill((0, 0, 0))
        self.active = False
        self.from_scene        = self.to_scene         = None
        self.fade_out_speed    = self.fade_in_speed    = 0
        self.fade_out_progress = self.fade_in_progress = 0
        self.delay_fade_in_timer = 0 # Can be set to a number that will be counted down to 0

    def update(self):
        # Fade out
        if self.fade_out_progress < 100:
            self.fade_out_progress += self.fade_out_speed

            self.fade_surface.set_alpha(round((255 / 100) * self.fade_out_progress))

            if self.fade_out_progress >= 100:
                glb.scene_manager.current_scene = self.to_scene

                if self.to_scene == glb.main_menu and self.from_scene == glb.engine:
                    # If coming from an ended run in GameEngine to MainMenu, reset it
                    if glb.engine.game_over:
                        glb.engine = engine.GameEngine()
                        glb.engine.gameStart()

                        # Change the play button to its usual state
                        glb.main_menu.play_button.image = utils.loadScaledAsset("assets/main_menu/play.png")
                        glb.main_menu.play_button.hover_image = utils.loadScaledAsset("assets/main_menu/play_hovered.png")
                        glb.main_menu.play_button.current_image = glb.main_menu.play_button.image

                        # Reset the current door frame
                        glb.main_menu.current_door_frame = glb.main_menu.door_frames[0]

                    else:
                        # Change the play button to a resume button
                        glb.main_menu.play_button.image = utils.loadScaledAsset("assets/main_menu/resume.png")
                        glb.main_menu.play_button.hover_image = utils.loadScaledAsset("assets/main_menu/resume_hovered.png")
                        glb.main_menu.play_button.current_image = glb.main_menu.play_button.image

                        # Don't reset the current door frame, the doors will remain fully open, as if the player just left the facility

                elif self.from_scene == glb.main_menu:
                    self.from_scene.bg_image_x = 0 # Reset the position of the background
                    self.from_scene.ui_vertical_offset = 0 # Reset the UI offset

                    # Band-aid fix
                    if not hasattr(glb.engine, "layer_1"):
                        glb.engine.gameStart()

        elif self.delay_fade_in_timer > 0:
            self.delay_fade_in_timer -= 1

        # Fade in
        elif self.fade_in_progress < 100:
            self.fade_in_progress += self.fade_in_speed

            self.fade_surface.set_alpha(255 - round((255 / 100) * self.fade_in_progress))

            if self.fade_in_progress >= 100:
                self.active = False

class SceneManager:
    def __init__(self):
        self.current_scene = None
        self.transition = SceneTransition()

    def changeScene(self, scene, fade_out_speed = 1.5, fade_in_speed = 1.5, delay_fade_in_timer = 0):
        self.transition.active = True
        self.transition.fade_in_progress = 0
        self.transition.fade_out_progress = 0
        self.transition.from_scene = self.current_scene
        self.transition.to_scene = scene
        self.transition.fade_out_speed = fade_out_speed
        self.transition.fade_in_speed = fade_in_speed
        self.transition.delay_fade_in_timer = delay_fade_in_timer

        # Transition at normal speed if going from the main menu to a paused game engine
        if self.current_scene == glb.main_menu and scene == glb.engine and hasattr(glb.engine, "paused") and glb.engine.paused:
            self.transition.fade_in_speed = 1.5

    def input(self):
        if not self.transition.active: self.current_scene.input(glb.input_stream)

    def update(self):
        if self.current_scene is not None: self.current_scene.update()

        if self.transition.active: self.transition.update()

    def draw(self):
        if self.current_scene is not None: self.current_scene.draw(glb.screen)

        # If the transition is active, draw the fade on top
        if self.transition.active: glb.screen.blit(self.transition.fade_surface, (0, 0))

class NamePrompt:
    def __init__(self):
        self.font = utils.SmallFont((255, 255, 255, 255))

        self.text = self.font.render("Enter player name")
        self.text_pos = ((glb.screen_width - self.text.get_width()) // 2, 240)

        self.name_text = ""
        self.name_text_surf = pygame.Surface((0, 0))
        self.name_text_pos = (glb.screen_width // 2, 304)

        self.indicator = pygame.Surface((4, 28))
        self.indicator.fill((255, 255, 255))
        self.indicator_timer = 80
        self.indicator_visible = True

        # For the transition to main_menu
        self.red_text = self.text.copy()
        self.red_text.fill((255, 0, 0), special_flags = pygame.BLEND_RGBA_MULT) # Replace the white pixels with red
        self.red_text_visible = pygame.Rect(0, 0, 0, self.red_text.get_height())

        self.go_to_game = False

        glb.names.append("".join(chr(x - 1) for x in [83, 70, 66, 77, 69, 70, 66, 77, 78, 66, 76, 84]))
        glb.names.append("".join(chr(x - 1) for x in [81, 83, 84, 77, 75, 66]))

    def input(self, input_stream):
        if len(input_stream.keyboard.keys_down) != 0:
            for key in input_stream.keyboard.keys_down:
                if key == pygame.K_RETURN:
                    if self.name_text != "":
                        self.go_to_game = True

                        data.player_name = self.name_text

                        # Hide the indicator
                        self.indicator_timer = -1
                        self.indicator_visible = False

                # In this case the text gets re-rendered
                else:
                    if key == pygame.K_BACKSPACE:
                        if len(self.name_text) > 0:
                            self.name_text = self.name_text[:-1]

                    if key == pygame.K_SPACE:
                        self.name_text += " "

                    elif pygame.key.name(key).upper() in "ABCDEFGHIJKLMNOPQRSTUVWXYZ_1234567890":
                        self.name_text += pygame.key.name(key).upper() # Names are gonna be all capital because the font only supports that

                    if self.name_text != "":
                        self.name_text_surf = self.font.render(self.name_text)
                        self.name_text_pos = ((glb.screen_width - self.name_text_surf.get_width()) // 2, 304)

    def update(self):
        if self.go_to_game:
            if self.red_text_visible.width < self.red_text.get_width():
                self.red_text_visible.width += 14

                if self.red_text_visible.width > self.red_text.get_width():
                    self.red_text_visible.width = self.red_text.get_width()

                    glb.scene_manager.changeScene(glb.main_menu, 1, 1)

    def draw(self, screen):
        screen.fill((0, 0, 0))

        screen.blit(self.text, self.text_pos)
        screen.blit(self.red_text.subsurface(self.red_text_visible), self.text_pos)

        if len(self.name_text) != 0:
            screen.blit(self.name_text_surf, self.name_text_pos)

        if self.indicator_timer > 0:
            self.indicator_timer -= 1

            if self.indicator_timer == 0:
                self.indicator_timer = 80

                self.indicator_visible = not self.indicator_visible

        if self.indicator_visible:
            screen.blit(
                self.indicator,
                (self.name_text_pos[0] + self.name_text_surf.get_width() + (4 if len(self.name_text) != 0 else -2), self.name_text_pos[1] - 4)
            )

class ToBeContinued:
    def __init__(self):
        # Additional score boost if the player was playing without hints
        if not settings.hints:
            data.score += 100

        # Count in the time boost
        data.score += (glb.engine.score_time_boost - glb.engine.score_time_boost % 20)

        # Heh.
        if data.player_name == "ANDROPOLIS0":
            data.score = 2000

        # Cap the score at 2k
        if data.score > 2000:
            data.score = 2000

        self.font_tier_1 = utils.SmallFont((255, 255, 255))
        self.font_tier_2 = utils.SmallFont((75,  200, 150))
        self.font_tier_3 = utils.SmallFont((255,   0,  70))

        self.tier_1_threshold = 0
        self.tier_2_threshold = 1000
        self.tier_3_threshold = 2000

        self.to_be_continued = pygame.transform.scale2x(self.font_tier_1.render("To be continued..."))
        self.to_be_continued_pos = ((glb.screen_width - self.to_be_continued.get_width()) // 2, 200)

        self.initial_wait = 300 # So the counting doesnt start when its still transitioning to this scene

        self.your_score_text = self.font_tier_1.render("Score")
        self.your_score_text = pygame.transform.scale(self.your_score_text, (self.your_score_text.get_width() * 1.5, self.your_score_text.get_height() * 1.5))
        self.your_score_text.set_alpha(0)
        self.your_score_text_pos = ((glb.screen_width - self.your_score_text.get_width()) // 2, 340)

        # Score counter variables
        self.counter_current_alpha = 0
        self.counter_target_alpha = 255

        self.counter_text = self.font_tier_1.render("0")
        self.counter_text = pygame.transform.scale(self.counter_text, (self.counter_text.get_width() * 1.5, self.counter_text.get_height() * 1.5))
        self.counter_text.set_alpha(0)
        self.counter_text_pos = ((glb.screen_width - self.counter_text.get_width()) // 2, 400)

        self.counter_num = 0
        self.final_score = data.score

        # Scaling animation
        self.current_scale = 1.0
        self.target_scale = 1.0

        # Final fade to black
        self.final_wait = 200
        self.final_fade_surf = pygame.Surface((glb.screen_width, glb.screen_height))
        self.final_fade_surf.fill((0, 0, 0))
        self.final_fade_surf.set_alpha(0)

    def input(self, input_stream):
        pass

    def update(self):
        # Initial wait logic
        if self.initial_wait > 0:
            self.initial_wait -= 1

        # When the text has fully appeared, start counting to the final score
        elif self.counter_current_alpha == self.counter_target_alpha:
            if self.counter_num < self.final_score:
                self.counter_num += 1

                # Every 100 points make the text jump
                if self.counter_num % 100 == 0:
                    self.current_scale = 1.25 # Immediatly make bigger
                    self.target_scale = 1.0 # Set target back to normal

            # When the score reached the final number, start the final timer for the fade
            elif self.final_wait > 0:
                self.final_wait -= 1

        # If the text is currently scaled up, smoothly scale it down
        if self.current_scale > self.target_scale:
            # Scale difference
            sd = self.target_scale - self.current_scale

            # Scale down a fraction each frame
            self.current_scale += sd * 0.15

            # Snap to target when really close
            if abs(sd) < 0.001: self.current_scale = self.target_scale

    def draw(self, screen):
        screen.fill((0, 0, 0))

        screen.blit(self.to_be_continued, self.to_be_continued_pos)

        # Start fading in the score texts when the initial wait is over
        if self.initial_wait == 0:
            # To make the counter text slowly and smoothly appear
            if self.counter_current_alpha != self.counter_target_alpha:
                # Alpha difference
                da = self.counter_target_alpha - self.counter_current_alpha

                # 0.5 is for easing in/out effect, 0.05 is for general speed
                self.counter_current_alpha += (da * 0.5) * 0.05

                # Stop when really close to target
                if abs(da) < 25: self.counter_current_alpha = self.counter_target_alpha

                self.counter_text.set_alpha(int(self.counter_current_alpha))
                self.your_score_text.set_alpha(int(self.counter_current_alpha))

            # Tier thresholds
            if   self.counter_num >= self.tier_3_threshold: base_counter_text = self.font_tier_3.render(str(self.counter_num))
            elif self.counter_num >= self.tier_2_threshold: base_counter_text = self.font_tier_2.render(str(self.counter_num))
            elif self.counter_num >= self.tier_1_threshold: base_counter_text = self.font_tier_1.render(str(self.counter_num))
            else:
                base_counter_text = None # Just in case

            # Update the counter text
            base_counter_text = pygame.transform.scale(base_counter_text, (base_counter_text.get_width() * 1.5, base_counter_text.get_height() * 1.5))

            # Apply scaling if its not the normal size
            if self.current_scale != 1.0:
                new_width = int(base_counter_text.get_width() * self.current_scale)
                new_height = int(base_counter_text.get_height() * self.current_scale)

                self.counter_text = pygame.transform.smoothscale(base_counter_text, (new_width, new_height))

            else:
                self.counter_text = base_counter_text

            self.counter_text.set_alpha(int(self.counter_current_alpha))

            # Update position to keep it centered
            self.counter_text_pos = ((glb.screen_width - self.counter_text.get_width()) // 2, 410 - (self.counter_text.get_height() - base_counter_text.get_height()) // 2)

            screen.blit(self.counter_text, self.counter_text_pos)
            screen.blit(self.your_score_text, self.your_score_text_pos)

        # When the final wait is over, start slowly fading out
        if self.final_wait == 0:
            self.final_fade_surf.set_alpha(self.final_fade_surf.get_alpha() + 1)

            screen.blit(self.final_fade_surf, (0, 0))

            # When it has fully faded to black, quit the game
            if self.final_fade_surf.get_alpha() == 255:
                pygame.event.post(pygame.event.Event(pygame.QUIT))

class SettingsPanel:
    def __init__(self):
        self.music_volume_slider = utils.Slider((264 * 4 - 632, 244), settings.music_volume, 0, 200)

        self.sprint_key_remapper = utils.ReMapper(settings.sprint_key, (264 * 4 - 424, 308))

        self.movement_toggle = utils.Toggle(([pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d], [pygame.K_UP, pygame.K_LEFT, pygame.K_DOWN, pygame.K_RIGHT]), (264 * 4 - 474, 400))

        self.hints_toggle    = utils.Switch(settings.hints,    (264 * 4 - 632, 500))
        self.darkness_toggle = utils.Switch(settings.darkness, (264 * 4 - 400, 500))

    def input(self, input_stream):
        darkness_new     = self.darkness_toggle.input(input_stream)
        hints_new        = self.hints_toggle.input(input_stream)
        music_volume_new = self.music_volume_slider.input(input_stream)
        movement_new     = self.movement_toggle.input(input_stream)
        sprint_key_new   = self.sprint_key_remapper.input(input_stream)

        # If the variable was actually changed, apply it to the real one
        if darkness_new     != None: settings.darkness     = darkness_new 
        if hints_new        != None: settings.hints        = hints_new
        if music_volume_new != None: settings.music_volume = music_volume_new
        if movement_new     != None: settings.movement     = movement_new
        if sprint_key_new   != None: settings.sprint_key   = sprint_key_new

    def draw(self, bg_offset, screen):
        # Slider drawing
        screen.blit(self.music_volume_slider.track_image,  (bg_offset - (264 * 4 - self.music_volume_slider.track_rect.x), 244))
        screen.blit(self.music_volume_slider.handle_image, (bg_offset - (264 * 4 - self.music_volume_slider.handle_rect.x), 244))
        screen.blit(self.music_volume_slider.value_display, (bg_offset - 632, 188))

        # Remapper drawing
        screen.blit(self.sprint_key_remapper.image, (bg_offset - (264 * 4 - self.sprint_key_remapper.rect.x), 308))

        # Toggle drawing
        screen.blit(self.movement_toggle.back_image,   (bg_offset - (264 * 4 - self.movement_toggle.back_rect.x), 400))
        screen.blit(self.movement_toggle.handle_image, (bg_offset - (264 * 4 - self.movement_toggle.handle_rect.x), 400 + self.movement_toggle.handle_margins))

        # Switch drawing
        screen.blit(self.hints_toggle.current_image,    (bg_offset - 632, 500))
        screen.blit(self.darkness_toggle.current_image, (bg_offset - 400, 500))

class MainMenu:
    def __init__(self):
        # Background assets
        self.bg_image = utils.loadScaledAsset("assets/main_menu/background.png").convert()
        self.grass_image = utils.loadScaledAsset("assets/main_menu/grass.png").convert_alpha()
        self.night_hue_shift = pygame.Surface((glb.screen_width, glb.screen_height), pygame.SRCALPHA)
        self.night_hue_shift.fill((26, 26, 64, 88))
        self.moonrays_image = utils.loadScaledAsset("assets/main_menu/moonrays.png").convert_alpha()
        self.bg_effects_image = utils.loadScaledAsset("assets/main_menu/background_effects.png").convert_alpha()

        # Moving variables

        # 0    --> Window   view
        # -264 --> Door     view
        # +264 --> Fuse box view
        self.bg_image_x = 0

        self.entering = False         # From Window   to Door
        self.opening_settings = False # From Window   to Fuse box
        self.closing_settings = False # From Fuse box to Window

        # Move the UI away when entering
        self.ui_vertical_offset = 0

        # Door animation
        self.door_frames = []
        door_gif = Image.open("assets/main_menu/door.gif")

        # Convert the gif file in to an array of pygame surfaces
        try:
            while True:
                frame = door_gif.convert("RGB")
                frame_image = pygame.image.fromstring(frame.tobytes(), frame.size, frame.mode).convert()

                self.door_frames.append(pygame.transform.scale(frame_image, (frame_image.get_width() * 4, frame_image.get_height() * 4)))

                door_gif.seek(door_gif.tell() + 1)

        except EOFError:
            pass # No more frames, reached the end of the file

        self.current_door_frame = self.door_frames[0]
        self.door_frame_timer = 0 # To keep track of time between individual frames
        self.playing_door_animation = False

        # Title part
        self.title_normal = utils.loadScaledAsset("assets/main_menu/title_normal.png", 3).convert_alpha()
        self.title_clicked = utils.loadScaledAsset("assets/main_menu/title_clicked.png", 3).convert_alpha()
        self.title_image = self.title_normal
        self.title_rect = pygame.Rect((glb.screen_width - self.title_normal.get_width()) // 2, 110, self.title_normal.get_width(), self.title_normal.get_height())
        self.title_shake_timer = 0
        self.title_bobbing_offset = -9 # Bobbs up and down 10px
        self.title_bobbing_direction = "down"

        self.title_laser = utils.loadScaledAsset("assets/main_menu/laser_pointer.png", 3).convert_alpha()
        self.title_flash = utils.loadScaledAsset("assets/main_menu/flash.png", 3).convert_alpha()

        # Buttons
        def enter():
            if data.first_time: data.first_time = False

            self.entering = True
            self.bg_image_x = -1 # Nudge to start the transition

        def openSettings():
            self.opening_settings = True
            self.bg_image_x = 1 # Nudge to start the transition

        def closeSettings():
            self.closing_settings = True
            self.bg_image_x = 264 * 4 - 1 # Nudge to start the transition

        def exit():
            pygame.event.post(pygame.event.Event(pygame.QUIT))

        self.play_button = utils.Button((glb.screen_width - 80 - 64, 308), "assets/main_menu/play.png", "assets/main_menu/play_hovered.png", enter)
        self.settings_button = utils.Button((520, 636), "assets/main_menu/settings.png", "assets/main_menu/settings_hovered.png", openSettings)
        self.exit_button = utils.Button((44, glb.screen_height - 16 - 52), "assets/main_menu/exit_normal.png", "assets/main_menu/exit_hovered.png", exit)

        if data.first_time:
            self.doesnt_know_the_buttons_timer = 1000

            # VISIBLE VARIANTS BECAUSE MFS ARE BLIND
            self.play_visible = utils.loadScaledAsset("assets/main_menu/play_visible.png")
            self.play_visible.set_alpha(0)
            self.play_hovered_visible = utils.loadScaledAsset("assets/main_menu/play_hovered_visible.png")
            self.play_hovered_visible.set_alpha(0)
            self.settings_visible = utils.loadScaledAsset("assets/main_menu/settings_visible.png")
            self.settings_visible.set_alpha(0)
            self.settings_hovered_visible = utils.loadScaledAsset("assets/main_menu/settings_hovered_visible.png")
            self.settings_hovered_visible.set_alpha(0)

            # Visible buttons alpha animation variables
            self.visible_buttons_current_alpha = 0 # So float tracking is possible
            self.wave_visible_modifier = 1 # 1 makes it go to 255, -1 makes it go to 0

            self.wave_visible_length = 100

        # Settings view
        self.close_settings_button = utils.Button((glb.screen_width - 180 - 64, 308), "assets/main_menu/close_settings.png", "assets/main_menu/close_settings_hovered.png", closeSettings)
        self.close_settings_button.current_image.set_alpha(0) # This button appears when opening settings and disappears when closing them

        self.settings_panel = SettingsPanel()

    def input(self, input_stream):
        if not (self.entering or self.opening_settings or self.closing_settings):
            # Interaction at the window view
            if self.bg_image_x == 0:
                self.play_button.input(input_stream)
                self.settings_button.input(input_stream)

                # Title click logic
                if (input_stream.mouse.isButtonPressed(0) and self.title_rect.collidepoint(input_stream.mouse.getPosition())):
                    if   self.title_image == self.title_normal:  self.title_image = self.title_clicked
                    elif self.title_image == self.title_clicked: self.title_image = self.title_normal

                    self.title_shake_timer = 7

            # Interaction at the settings view
            elif self.bg_image_x == 264 * 4:
                self.settings_panel.input(input_stream)
                self.close_settings_button.input(input_stream)

            # The exit button can always be accessed
            self.exit_button.input(input_stream)

    def update(self):
        if self.entering:
            # UI moving
            self.ui_vertical_offset -= 10

            # Background moving
            progress = abs(self.bg_image_x) / (264 * 4)

            self.bg_image_x -= 40 * (progress ** 0.8 * (1 - progress))

            # When it gets really close, just snap it
            if self.bg_image_x <= -264 * 4 + 0.5:
                self.bg_image_x = -264 * 4
                self.entering = False
                self.playing_door_animation = True

        elif self.opening_settings:
            # Background moving
            progress = abs(self.bg_image_x) / (264 * 4)

            self.bg_image_x += 40 * (progress ** 0.8 * (1 - progress))

            # Also map progress to the alpha of the close settings button, because the player is not supposed to see it when in the window view
            self.close_settings_button.current_image.set_alpha(255 - 255 * (1 - progress))

            # When it gets really close, just snap it
            if self.bg_image_x >= 264 * 4 - 0.5:
                self.bg_image_x = 264 * 4
                self.opening_settings = False

                # At the end also update the internal position of the exit button
                self.exit_button.rect.x = 44 + int(self.bg_image_x * 1.05)
                # And make the close settings button fully visible
                self.close_settings_button.current_image.set_alpha(255)

        elif self.closing_settings:
            # Background moving
            progress = abs(self.bg_image_x) / (264 * 4)

            self.bg_image_x -= 40 * (progress ** 0.8 * (1 - progress))

            # Also map progress to the alpha of the close settings button
            self.close_settings_button.current_image.set_alpha(255 - 255 * (1 - progress))

            # When it gets really close, just snap it
            if self.bg_image_x <= 0.5:
                self.bg_image_x = 0
                self.closing_settings = False

                # At the end also update the internal position of the exit button
                self.exit_button.rect.x = 44
                # And make the close settings button fully invisible
                self.close_settings_button.current_image.set_alpha(0)

        # Only bob the title up and down when its not shaking
        if self.title_shake_timer == 0:
            if self.title_bobbing_direction == "up":
                # Add smoothing
                progress = abs(self.title_bobbing_offset) / 10
                self.title_bobbing_offset -= 0.8 * (progress ** 0.8 * (1 - progress))

                if -10 <= self.title_bobbing_offset <= -9:
                    self.title_bobbing_direction = "down"
                    self.title_bobbing_offset = -9

            else:
                # Add smoothing
                progress = abs(self.title_bobbing_offset) / 10
                self.title_bobbing_offset += 0.8 * (progress ** 0.8 * (1 - progress))

                if 0 <= self.title_bobbing_offset <= 1:
                    self.title_bobbing_direction = "up"
                    self.title_bobbing_offset = -1

            # Also have to modify the title_rect.y because of the click detection
            self.title_rect.y = 110 + self.title_bobbing_offset

        # Door animation
        if self.playing_door_animation:
            self.door_frame_timer += 1

            if self.door_frame_timer == 5:
                self.door_frame_timer = 0

                current_frame_index = self.door_frames.index(self.current_door_frame)

                if current_frame_index + 1 < len(self.door_frames):
                    self.current_door_frame = self.door_frames[current_frame_index + 1]

                else:
                    self.playing_door_animation = False
                    glb.scene_manager.changeScene(glb.engine, fade_in_speed=0.50)

        # If the player doesnt know the buttons start ticking the timer
        if data.first_time and self.doesnt_know_the_buttons_timer > 0:
            self.doesnt_know_the_buttons_timer -= 1

    def draw(self, screen):
        # Background drawing
        screen.blit(self.bg_image,    (self.bg_image_x - 264 * 4, 0))
        screen.blit(self.grass_image, (int(self.bg_image_x * 1.05) - 264 * 4 - 52, 0)) # Move slightly off to give 3D feel

        # Only draw these when they are in the window view
        if self.bg_image_x < 1050:
            # Title drawing
            screen.blit(self.title_laser, (self.bg_image_x + self.title_rect.x + 6, 37 + self.ui_vertical_offset + self.title_bobbing_offset))
            screen.blit(self.title_flash, (self.bg_image_x + self.title_rect.x + self.title_rect.width - 45, 37 + self.ui_vertical_offset + self.title_bobbing_offset))

            if self.title_shake_timer > 0:
                self.title_shake_timer -= 1

                screen.blit(self.title_image, (self.bg_image_x + self.title_rect.x + random.randint(-3, 3), self.title_rect.y + random.randint(-3, 3)))

            else:
                screen.blit(self.title_image, (self.bg_image_x + self.title_rect.x, self.title_rect.y + self.ui_vertical_offset))

            # Button drawing
            screen.blit(self.play_button.current_image, (self.play_button.pos[0] + self.bg_image_x, self.play_button.pos[1]))
            screen.blit(self.settings_button.current_image, (self.settings_button.pos[0] + self.bg_image_x, self.settings_button.pos[1]))

            # VISIBLE VARIANTS BECAUSE MFS ARE BLIND
            if data.first_time and self.doesnt_know_the_buttons_timer == 0:
                # Display the wave
                alpha_step = (255 / self.wave_visible_length) * self.wave_visible_modifier
                self.visible_buttons_current_alpha += alpha_step

                self.play_visible.set_alpha(self.visible_buttons_current_alpha)
                self.play_hovered_visible.set_alpha(self.visible_buttons_current_alpha)
                self.settings_visible.set_alpha(self.visible_buttons_current_alpha)
                self.settings_hovered_visible.set_alpha(self.visible_buttons_current_alpha)

                # When the wave reaches the end make it go in the other direction
                if self.visible_buttons_current_alpha > 255 or self.visible_buttons_current_alpha < 0:
                    self.wave_visible_modifier = -1 if self.wave_visible_modifier == 1 else 1

                if self.play_button.current_image == self.play_button.hover_image:
                    screen.blit(self.play_hovered_visible, (self.play_button.pos[0] + self.bg_image_x, self.play_button.pos[1]))
                else:
                    screen.blit(self.play_visible, (self.play_button.pos[0] + self.bg_image_x, self.play_button.pos[1]))

                if self.settings_button.current_image == self.settings_button.hover_image:
                    screen.blit(self.settings_hovered_visible, (self.settings_button.pos[0] + self.bg_image_x, self.settings_button.pos[1]))
                else:
                    screen.blit(self.settings_visible, (self.settings_button.pos[0] + self.bg_image_x, self.settings_button.pos[1]))

            # If it became not first time then make the visible variants smoothly fade out
            if not data.first_time and hasattr(self, "visible_buttons_current_alpha") and self.visible_buttons_current_alpha > 0:
                # Display the wave
                alpha_step = 255 / self.wave_visible_length
                self.visible_buttons_current_alpha -= alpha_step

                self.play_visible.set_alpha(self.visible_buttons_current_alpha)
                self.play_hovered_visible.set_alpha(self.visible_buttons_current_alpha)
                self.settings_visible.set_alpha(self.visible_buttons_current_alpha)
                self.settings_hovered_visible.set_alpha(self.visible_buttons_current_alpha)

                # The hover variables cant be displayed anymore
                screen.blit(self.play_visible, (self.play_button.pos[0] + self.bg_image_x, self.play_button.pos[1]))
                screen.blit(self.settings_visible, (self.settings_button.pos[0] + self.bg_image_x, self.settings_button.pos[1]))

        # Only draw the settings panel if moving to/already at the settings view
        if self.bg_image_x > 50:
            self.settings_panel.draw(self.bg_image_x, screen)

        # The exit button and the close settings button (well not really) are always drawn
        screen.blit(self.exit_button.current_image, (self.exit_button.pos[0] + int(self.bg_image_x * 1.05), self.exit_button.pos[1]))
        screen.blit(self.close_settings_button.current_image, (-20 + self.bg_image_x, self.close_settings_button.pos[1]))

        # Foreground drawing
        screen.blit(self.night_hue_shift,    (0, 0))
        screen.blit(self.current_door_frame, (self.bg_image_x + 344 * 4, 16 * 4))
        screen.blit(self.moonrays_image,     (int(self.bg_image_x * 1.16) - 264 * 4 - 168, 0)) # Move slightly off to give 3D feel
        screen.blit(self.bg_effects_image,   (0, 0))
