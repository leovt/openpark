import logging

from simulationview import SimulationView
from simulation import Simulation

import pyglet
from pyglet import gl
from pyglet.window import key
from windowmanager import WindowManager, Window, Label

class Application:
    '''
    classdocs
    '''


    def __init__(self, window):
        '''
        Constructor
        '''
        self.frame_no = 0
        self.wm = WindowManager()
        self.view = SimulationView(self.wm)

        self.state = 'menu'
        self.speed = 1.0
        self.window = window
        logging.debug('The state is {}'.format(self.state))
        self.start_menu()

    def update(self, dt):
        self.view.update(dt * self.speed)
        self.frame_no += 1

    def on_draw(self):
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        self.view.draw()
        self.wm.draw()

    def on_mouse_press(self, x, y, *args):
        self.wm.on_mouse_press(x, self.window.height - y, *args)

    def show_menu(self):
        self.menu = Window(self.wm.root, 100, 100, 440, 280)
        Label(self.menu, 'OpenPark Main Menu', 10, 10)
        Label(self.menu, 'Leonhard Vogt 2015', 10, 40)

        Label(self.menu, '[ new empty simulation ]', 10, 100).on_click = self.menu_new
        Label(self.menu, '[ quit program ]', 10, 130).on_click = self.menu_quit

    def new_empty_simulation(self):
        self.menu.close()
        simu = Simulation(4, 3)
        self.view.unload()
        self.view.load(simu)

    def start_menu(self):
        # simu = load_background_simulation()
        self.view.unload()
        # self.view.load(simu)
        self.show_menu()

    def menu_new(self):
        self.state = 'simu'
        logging.debug('The state is {}'.format(self.state))
        self.new_empty_simulation()

    def menu_quit(self):
        pyglet.app.exit()

    def on_key_press(self, symbol, modifiers):
        logging.debug('Key Press {} {}'.format(symbol, modifiers))
        if symbol == key.I:
            logging.info('FPS: {}'.format(pyglet.clock.get_fps()))
            logging.info('Frame-No: {}'.format(self.frame_no))
            self.wm.textmanager.dump()

        if self.state == 'menu':
            if symbol == key.N:
                self.menu_new()
            if symbol == key.Q:
                self.menu_quit()

        elif self.state == 'simu':
            if symbol == key.Q:
                self.start_menu()
                self.state = 'menu'
                logging.debug('The state is {}'.format(self.state))
            if symbol == key.SPACE:
                if self.speed:
                    self.speed = 0
                else:
                    self.speed = 1.0
            if symbol == key.NUM_ADD:
                self.speed += 0.5
            if symbol == key.NUM_SUBTRACT:
                self.speed = max(0.0, self.speed - 0.5)

        else:
            assert False

    def on_resize(self, x, y):
        logging.info('Window Resized to {}x{}'.format(x, y))
        x = max(x, 1)
        y = max(y, 1)
        gl.glViewport(0, 0, x, y)
        self.wm.on_resize(x, y)
        self.view.on_resize(x, y)
