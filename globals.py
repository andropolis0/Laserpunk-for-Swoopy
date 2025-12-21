import pygame
import inputstream
import dictionaries
import scene
import engine
import soundengine

# Global variables
screen_width = 1280
screen_height = 720
screen = pygame.display.set_mode((screen_width, screen_height))
clock = pygame.time.Clock()
input_stream = inputstream.InputStream()
scene_manager = scene.SceneManager()
main_menu = scene.MainMenu()
sound_engine = soundengine.SoundEngine()

names = []

# Load the textures/dictionaries for the engine
dictionaries.Crystals.loadCrystalTextures()
dictionaries.Scraps.loadScrapTextures()
dictionaries.AccessCards.loadCardTextures()
dictionaries.Tiles.loadTileTextures()

engine = engine.GameEngine()
