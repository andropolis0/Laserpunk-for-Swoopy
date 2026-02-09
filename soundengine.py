import pygame
import settings

class SoundEngine:
    def __init__(self):
        pygame.mixer.init()

        # Sounds can be played on top of eachother
        # Music can only play one at a time, repeats when it reaches the end, fades in and out

        self.sounds = {
            "menu_button" : pygame.mixer.Sound("assets/sounds/menu_button.ogg"),
            "title_clicked" : pygame.mixer.Sound("assets/sounds/title_clicked.ogg"),
            "button" : pygame.mixer.Sound("assets/sounds/button.ogg"),
            "metal_1" : pygame.mixer.Sound("assets/sounds/metal_1.ogg"),
            "metal_2" : pygame.mixer.Sound("assets/sounds/metal_2.ogg"),
            "metal_3" : pygame.mixer.Sound("assets/sounds/metal_3.ogg"),
            "metal_4" : pygame.mixer.Sound("assets/sounds/metal_4.ogg"),
            "slash_1" : pygame.mixer.Sound("assets/sounds/slash_1.ogg"),
            "slash_2" : pygame.mixer.Sound("assets/sounds/slash_2.ogg"),
            "slash_3" : pygame.mixer.Sound("assets/sounds/slash_3.ogg"),
            "slash_4" : pygame.mixer.Sound("assets/sounds/slash_4.ogg"),
            "footsteps" : pygame.mixer.Sound("assets/sounds/footsteps.ogg"),
            "paper_open" : pygame.mixer.Sound("assets/sounds/paper_open.ogg"),
            "paper_close" : pygame.mixer.Sound("assets/sounds/paper_close.ogg"),
            "collect" : pygame.mixer.Sound("assets/sounds/collect.ogg"),
            "blocker" : pygame.mixer.Sound("assets/sounds/blocker.ogg"),
            "redirector" : pygame.mixer.Sound("assets/sounds/redirector.ogg"),
            "reciever" : pygame.mixer.Sound("assets/sounds/reciever.ogg"),
            "glass_box" : pygame.mixer.Sound("assets/sounds/glass_box.ogg"),
            "the_glass_box" : pygame.mixer.Sound("assets/sounds/the_glass_box.ogg"),
            "locker_open" : pygame.mixer.Sound("assets/sounds/locker_open.ogg"),
            "locker_close" : pygame.mixer.Sound("assets/sounds/locker_close.ogg")
        }

        self.music = {
            "main_theme" : "assets/music/main_theme.ogg",
            "ambience": "assets/music/ambience.ogg",
            "test" : "assets/ui/unused/test.ogg",
            "u_music": "assets/ui/unused/music.ogg",
            "u2_music": "assets/ui/unused/music2.ogg"
        }

        self.current_music = None
        self.next_music = None
        self.next_music_info = None

        self.fading_music_target_volume = -1
        self.current_music_volume_precise = -1

    def playSound(self, sound_name, sound_volume = 0.4, looping = False):
        self.sounds[sound_name].set_volume(sound_volume * (settings.music_volume / 100))
        self.sounds[sound_name].play(loops = 0 if not looping else -1)

    def stopSound(self, sound_name):
        self.sounds[sound_name].stop()

    def playMusic(self, music_name, music_volume = 1, fade_in_time = 100, start=0.0):
        self.current_music = music_name

        pygame.mixer.music.load(self.music[music_name])
        pygame.mixer.music.set_volume(music_volume * (settings.music_volume / 100))
        pygame.mixer.music.play(-1, start, fade_in_time)

    def switchMusic(self, music_name, music_volume = 1, fade_in_time = 100, fade_out_time=100, start=0.0):
        pygame.mixer.music.fadeout(fade_out_time)

        self.current_music = None
        self.next_music = music_name
        self.next_music_info = (music_volume, fade_in_time, start)

    def fadeMusicVolume(self, target_volume):
        self.fading_music_target_volume = target_volume
        self.current_music_volume_precise = pygame.mixer.music.get_volume()

    def update(self):
        if self.current_music is None and not pygame.mixer.music.get_busy() and self.next_music is not None:
            self.playMusic(self.next_music, *self.next_music_info)

            self.next_music = None
            self.next_music_info = None

        # Music volume fading
        if self.fading_music_target_volume != -1:
            current_volume = round(pygame.mixer.music.get_volume(), 1)

            if current_volume == self.fading_music_target_volume:
                # Just in case
                pygame.mixer.music.set_volume(self.fading_music_target_volume)

                self.fading_music_target_volume = -1
                self.current_music_volume_precise = -1

                return

            self.current_music_volume_precise += 0.005 if self.fading_music_target_volume > current_volume else -0.005
            self.current_music_volume_precise = round(self.current_music_volume_precise, 3)

            pygame.mixer.music.set_volume(round(self.current_music_volume_precise, 1))
