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
import sprite

from graphix import make_texture

VOXEL_HEIGHT = 19.0;
VOXEL_Y_SIDE = 24.0;
VOXEL_X_SIDE = 48.0;

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
        self.sprite = sprite.Sprite('../art/guest.ini')
        self.sprite.set_pose('walk')
        self.sprite.turn_to(180)

    def init_gl(self):
        self.program = GlProgram(shaders.vertex_scene, shaders.fragment_scene)
        self.buffer = gl.GLuint(0)
        gl.glGenBuffers(1, pointer(self.buffer))
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.buffer)

        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        self.texture_map = make_texture('../art/map.png')
        self.texture_sprite = make_texture('../art/guest.png')


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

    def get_map_vertex_data(self):
        yield from (0.0, 0.0, 0.0, 0.0, 0.5, 1.0)
        yield from (1.0, 0.0, 0.0, 0.0, 1.0, 0.5)
        yield from (1.0, 1.0, 0.0, 0.0, 0.5, 0.0)
        yield from (0.0, 1.0, 0.0, 0.0, 0.0, 0.5)

        yield from (1.0, 0.0, 0.0, 0.0, 0.5, 1.0)
        yield from (2.0, 0.0, 0.0, 0.0, 1.0, 0.5)
        yield from (2.0, 1.0, 0.0, 0.0, 0.5, 0.0)
        yield from (1.0, 1.0, 0.0, 0.0, 0.0, 0.5)

    def get_sprite_vertex_data(self):
        r = self.sprite.get_coordinates(self.simulation.time)

        s = (0.4 * self.simulation.time) % 8

        if s < 2:
            x = 2.5 - s
            y = 0.3
            self.sprite.turn_to(180)
        elif s < 4:
            y = 0.3 + (s - 2)
            x = 0.5
            self.sprite.turn_to(90)
        elif s < 6:
            y = 2.3
            x = 0.5 + (s - 4)
            self.sprite.turn_to(0)
        else:
            y = 2.3 + (6 - s)
            x = 2.5
            self.sprite.turn_to(270)

        dx = self.sprite.offset_x / VOXEL_X_SIDE * 0.5
        dz_up = self.sprite.offset_y / VOXEL_HEIGHT
        dz_down = -self.sprite.frame_height / VOXEL_HEIGHT + dz_up

        yield from (x - dx, y + dx, dz_down, 0, r.left, r.bottom)
        yield from (x - dx, y + dx, dz_up, 0, r.left, r.top)
        yield from (x + dx, y - dx, dz_up, 0, r.right, r.top)
        yield from (x + dx, y - dx, dz_down, 0, r.right, r.bottom)

    def draw(self):
        if self.simulation is None:
            return
        now = self.simulation.current_datetime()
        self.label.text = 'Simulated date is {} + {:0.1f}'.format(format_date(now), now[3])

        self.program.use()
        self.program.vertex_attrib_pointer(self.buffer, b"position", 4, stride=6 * sizeof(gl.GLfloat))
        self.program.vertex_attrib_pointer(self.buffer, b"texcoord", 2, stride=6 * sizeof(gl.GLfloat), offset=4 * sizeof(gl.GLfloat))

        self.draw_map()
        self.draw_sprites()
        l = list(self.get_sprite_vertex_data())


    def draw_map(self):
        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_map)
        self.program.uniform1i(b"tex", 0)  # set to 0 because the texture is bound to GL_TEXTURE0

        data = list(self.get_map_vertex_data())
        data = (gl.GLfloat * len(data))(*data)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.buffer)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, sizeof(data), data, gl.GL_DYNAMIC_DRAW)

        gl.glDrawArrays(gl.GL_QUADS, 0, len(data) // 6)

    def draw_sprites(self):
        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_sprite)
        self.program.uniform1i(b"tex", 0)  # set to 0 because the texture is bound to GL_TEXTURE0

        data = list(self.get_sprite_vertex_data())
        data = (gl.GLfloat * len(data))(*data)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.buffer)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, sizeof(data), data, gl.GL_DYNAMIC_DRAW)

        gl.glDrawArrays(gl.GL_QUADS, 0, len(data) // 6)


    def on_resize(self, x, y):
        '''update the window manager when the opengl viewport is resized'''
        self.program.uniform2f(b'window_size', x, y)
