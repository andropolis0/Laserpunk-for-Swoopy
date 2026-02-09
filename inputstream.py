import pygame

class Keyboard:
    def __init__(self):
        self.current_key_states = None
        self.previous_key_states = None

        # For typing functionality
        self.keys_down = [] # Array of down keys in a given frame

    def processInput(self, general_events):
        self.previous_key_states = self.current_key_states
        self.current_key_states = pygame.key.get_pressed()

        self.keys_down = [event.key for event in general_events if event.type == pygame.KEYDOWN]

    def isKeyDown(self, key_code):
        if self.current_key_states is None or self.previous_key_states is None: return False
        else: return self.current_key_states[key_code] == True

    def isKeyPressed(self, key_code):
        if self.current_key_states is None or self.previous_key_states is None: return False
        else: return self.current_key_states[key_code] == True and self.previous_key_states[key_code] == False

    def isKeyReleased(self, key_code):
        if self.current_key_states is None or self.previous_key_states is None: return False
        else: return self.current_key_states[key_code] == False and self.previous_key_states[key_code] == True

class Mouse:
    def __init__(self):
        self.current_button_states = None
        self.previous_button_states = None
        self.current_position = (0, 0)
        self.previous_position = (0, 0)

    def processInput(self):
        self.previous_button_states = self.current_button_states
        self.current_button_states = pygame.mouse.get_pressed()
        self.previous_position = self.current_position
        self.current_position = pygame.mouse.get_pos()

    # 0 = left button, 1 = middle button, 2 = right button

    def isButtonDown(self, button):
        if self.current_button_states is None or self.previous_button_states is None: return False
        else: return self.current_button_states[button] == True

    def isButtonPressed(self, button):
        if self.current_button_states is None or self.previous_button_states is None: return False
        else: return self.current_button_states[button] == True and self.previous_button_states[button] == False

    def isButtonReleased(self, button):
        if self.current_button_states is None or self.previous_button_states is None: return False
        else: return self.current_button_states[button] == False and self.previous_button_states[button] == True

    def getPosition(self):
        return self.current_position

    def getDelta(self):
        return (self.current_position[0] - self.previous_position[0], self.current_position[1] - self.previous_position[1])

class InputStream:
    def __init__(self):
        self.general_events = None

        self.keyboard = Keyboard()
        self.mouse = Mouse()
    
    def processInput(self):
        self.keyboard.processInput(self.general_events)
        self.mouse.processInput()
