import pygame
import settings

class SoundEngine:
    def __init__(self):
        pygame.mixer.init()

        # Sounds can be played on top of eachother
        # Music can only play one at a time, repeats when it reaches the end, fades in and out

        self.sounds = {
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
            "game_of_love" : "assets/music/game_of_love.ogg",
            "test" : "assets/ui/unused/test.ogg",
            "u_music": "assets/ui/unused/music.ogg",
            "u2_music": "assets/ui/unused/music2.ogg"
        }

        self.current_music = None
        self.next_music = None

    def playSound(self, sound_name, sound_volume = 0.4, looping = False):
        self.sounds[sound_name].set_volume(sound_volume * (settings.music_volume / 100))
        self.sounds[sound_name].play(loops = 0 if not looping else -1)

    def stopSound(self, sound_name):
        self.sounds[sound_name].stop()

    def playMusic(self, music_name, music_volume = 1, fade_in_time = 100):
        self.current_music = music_name

        pygame.mixer.music.load(self.music[music_name])
        pygame.mixer.music.set_volume(music_volume)
        pygame.mixer.music.play(-1, fade_ms = fade_in_time)

    def switchMusic(self, music_name):
        pygame.mixer.music.fadeout(100)

        self.current_music = None
        self.next_music = music_name

    def update(self):
        if self.current_music is None and not pygame.mixer.music.get_busy() and self.next_music is not None:
            self.playMusic(self.next_music)

            self.next_music = None
