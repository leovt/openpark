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
        self.view = SimulationView()
        self.wm = WindowManager()

        # creating test windows
        test_window = Window(self.wm.root, 10, 10, 100, 100)
        test_window.on_click = lambda:print('Test Click')
        Label(test_window, 'Test target', 15, 40)
        test_label = Label(self.wm.root, 'Hello World', 10, 150)
        test_label.on_click = lambda:print('Hello World')



        self.state = 'menu'
        self.speed = 1.0
        self.window = window
        logging.debug('The state is {}'.format(self.state))

    def update(self, dt):
        self.view.update(dt * self.speed)
        self.frame_no += 1

    def on_draw(self):
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        self.view.draw()
        self.wm.draw()

    def on_mouse_press(self, x, y, *args):
        self.wm.on_mouse_press(x, self.window.height - y, *args)

    def new_empty_simulation(self):
        simu = Simulation(30, 30)
        self.view.unload()
        self.view.load(simu)

    def start_background_simulation(self):
        # simu = load_background_simulation()
        self.view.unload()
        # self.view.load(simu)

    def on_key_press(self, symbol, modifiers):
        logging.debug('Key Press {} {}'.format(symbol, modifiers))
        if symbol == key.I:
            logging.info('FPS: {}'.format(pyglet.clock.get_fps()))
            logging.info('Frame-No: {}'.format(self.frame_no))

        if self.state == 'menu':
            if symbol == key.N:
                self.state = 'simu'
                logging.debug('The state is {}'.format(self.state))
                self.new_empty_simulation()
            if symbol == key.Q:
                pyglet.app.exit()
        elif self.state == 'simu':
            if symbol == key.Q:
                self.start_background_simulation()
                self.state = 'menu'
                logging.debug('The state is {}'.format(self.state))
            if symbol == key.SPACE:
                if self.speed:
                    self.speed = 0
                else:
                    self.speed = 1.0
        else:
            assert False

    def on_resize(self, x, y):
        logging.info('Window Resized to {}x{}'.format(x, y))
        gl.glViewport(0, 0, x, y)
        self.wm.on_resize(x, y)
