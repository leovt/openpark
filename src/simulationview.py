'''
Created on 8 Jul 2015

@author: leonhard
'''
import logging
from ctypes import pointer, sizeof
from pyglet import gl

import shaders
from graphix import GlProgram
from windowmanager import Label


DAY_NAMES = ['1', '8', '15', '22']
MONTH_NAMES = ['Mar', 'Apr', 'May', 'Jun',
               'Jul', 'Aug', 'Sep', 'Oct']
YEAR_OFFSET = 2000

def format_date(datetime):
    year, month, day, _ = datetime

    return '{} {}, {}'.format(MONTH_NAMES[month], DAY_NAMES[day], year + YEAR_OFFSET)

class SimulationView:
    '''
    classdocs
    '''


    def __init__(self, wm):
        '''
        Constructor
        '''
        self.wm = wm
        self.simulation = None
        self.orientation = 0
        self.view_x = 0
        self.view_y = 0
        self.init_gl()

    def init_gl(self):
        self.program = GlProgram(shaders.vertex_scene, shaders.fragment_scene)
        self.buffer = gl.GLuint(0)
        gl.glGenBuffers(1, pointer(self.buffer))
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.buffer)
        data = (gl.GLfloat * 6)(-0.6, -0.6, -0.6, 0.6, 0.6, 0.0)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, sizeof(data), data, gl.GL_DYNAMIC_DRAW)


    def load(self, simulation):
        assert self.simulation is None
        self.simulation = simulation
        self.label = Label(self.wm.root, '', 0, 0)

    def unload(self):
        self.simulation = None
        self.wm.root.close()

    def update(self, dt):
        if self.simulation:
            self.simulation.update(dt)

    def draw(self):
        if self.simulation is None:
            return
        now = self.simulation.current_datetime()
        self.label.text = 'Simulated date is {} + {:0.1f}'.format(format_date(now), now[3])

        self.program.use()
        self.program.vertex_attrib_pointer(self.buffer, b"position", 2)
        gl.glDrawArrays(gl.GL_TRIANGLE_STRIP, 0, 3)
