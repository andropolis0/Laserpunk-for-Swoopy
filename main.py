import pygame
import globals as glb
from scene import NamePrompt

pygame.init()
pygame.display.set_caption('Laserpunk')
pygame.display.set_icon(pygame.image.load("assets/icon.png"))

# Set the first scene
glb.scene_manager.changeScene(NamePrompt(), 100) # 100 skips the fade out

running = True
while running:
    # Pygame.event.get() clears the events once its called, so a copy will be sent to the InputStream
    events = pygame.event.get()

    glb.input_stream.general_events = events

    # Goes through all events and if *any* one of them is QUIT (returns true) "not" flips it in to False - exiting the loop
    running = not any(event.type == pygame.QUIT for event in events)

    glb.input_stream.processInput()

    glb.scene_manager.input()
    glb.scene_manager.update()
    glb.scene_manager.draw()

    glb.sound_engine.update()

    pygame.display.flip()

    pygame.display.set_caption(f'Laserpunk @ {int(glb.clock.get_fps())} FPS')

    glb.clock.tick(100)

pygame.quit()
