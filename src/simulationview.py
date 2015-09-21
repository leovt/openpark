'''
Created on 8 Jul 2015

@author: leonhard
'''
import logging
from ctypes import pointer, sizeof
from pyglet import gl
from pyglet.window import mouse, key
import os
import configparser

import shaders
from graphix import GlProgram
from windowmanager import Label

from graphix import make_texture
import ctypes
import math
from collections import defaultdict

VOXEL_HEIGHT = 24
VOXEL_Y_SIDE = 24
VOXEL_X_SIDE = VOXEL_Y_SIDE * 2

TEXTURE_WIDTH = 512
TEXTURE_HEIGHT = 256

MOUSE_SCROLL_BORDER_WIDTH = 20
MOUSE_SCROLL_SPEED = 150

DAY_NAMES = ['1', '8', '15', '22']
MONTH_NAMES = ['Mar', 'Apr', 'May', 'Jun',
               'Jul', 'Aug', 'Sep', 'Oct']
YEAR_OFFSET = 2000

def format_date(datetime):
    year, month, day, _ = datetime

    return '{} {}, {}'.format(MONTH_NAMES[month], DAY_NAMES[day], year + YEAR_OFFSET)

ZMODE_BACK = 6
ZMODE_BOTTOM = 7
ZMODE_SUBVOX_BACK = 5
ZMODE_CENTER = 4
ZMODE_SUBVOX_MIDDLE = 3
ZMODE_SUBVOX_FRONT = 2
ZMODE_TOP = 1
ZMODE_FRONT = 0

def zbuffer(x, y, z, mode, sub=None):
    ''' calculate a modified zbuffer value for the object at tile x,y '''

    # assume 24 bit buffer
    # bit |--------|--------|----|----|
    #       map xy   map z   mode sub
    # msb byte is the voxel (integer) position

    if sub is None:
        xf = x - int(x)
        yf = y - int(y)
        sub = (xf % 0.5 + yf % 0.5) * (VOXEL_Y_SIDE // 2)

    if mode is None:
        xf = x - int(x)
        yf = y - int(y)

        if xf >= 0.5 and yf >= 0.5:
            mode = ZMODE_SUBVOX_BACK
        elif xf < 0.5 and yf < 0.5:
            mode = ZMODE_SUBVOX_FRONT
        else:
            mode = ZMODE_SUBVOX_MIDDLE


    mapxy = int(x) + int(y)
    assert 0 <= mapxy < 256
    mapz = int(z)
    assert 0 <= mapz < 256
    assert 0 <= mode < 8
    assert 0 <= sub < 32

    return (sub + 0x20 * mode + 0x100 * mapz + 0x10000 * mapxy) / 0x1000000


def decode_zbuffer(value):
    value = int(value * 0x1000000 + 0.5)
    value, sub = divmod(value, 0x20)
    value, mode = divmod(value, 0x08)
    value, z = divmod(value, 0x100)
    return value, z, mode, sub


from sprite import Sprite

class tileset:
    def __init__(self, inifile):
        conf = configparser.SafeConfigParser()
        conf.read(inifile)
        self.filename = os.path.abspath(os.path.join(os.path.dirname(inifile), conf.get('Tiles', 'filename')))
        grid_width = conf.getint('Tiles', 'grid_width') / conf.getint('Tiles', 'tex_width')
        grid_height = conf.getint('Tiles', 'grid_height') / conf.getint('Tiles', 'tex_height')

        self.tiles = {}

        for sec in conf.sections():
            if sec == 'Tiles':
                continue
            x = conf.getint(sec, 'x')
            y = conf.getint(sec, 'y')
            flip = conf.get(sec, 'flip').strip()

            if flip in ('H', 'B'):
                dx = -1
            else:
                dx = 1

            if flip in ('V', 'B'):
                dy = -1
            else:
                dy = 1

            self.tiles[sec] = [(x * grid_width, (y + dy) * grid_height),
                               ((x + dx) * grid_width, y * grid_height),
                               (x * grid_width, (y - dy) * grid_height),
                               ((x - dx) * grid_width, y * grid_height)]


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
        self.screen_origin_x = 0
        self.screen_origin_y = 0
        self.mouse_x = 0
        self.mouse_y = 0
        self.speed = 1.0

        self.pers = defaultdict(list)
        self.scenery = defaultdict(list)

        self.sprite_pers = Sprite('../art/guest.ini')
        self.sprite_shop = Sprite('../art/shop.ini')
        self.sprite_entrance = Sprite('../art/entrance.ini')

        self.tiles = tileset('../art/map.ini')
        self.map_data_length = None
        self.init_gl()

    def create_fbo(self):
        if self.fbo:
            gl.glDeleteFramebuffers(1, pointer(self.fbo))
        if self.rendered_texture:
            gl.glDeleteTextures(1, pointer(self.rendered_texture))
        if self.depthrenderbuffer:
            gl.glGenRenderbuffers(1, pointer(self.depthrenderbuffer))


        gl.glGenFramebuffers(1, pointer(self.fbo))
        if not self.fbo:
            logging.error('failed fbo')
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.fbo)

        gl.glGenTextures(1, pointer(self.rendered_texture))
        if not self.rendered_texture:
            logging.error('failed rendered_texture')

        gl.glGenRenderbuffers(1, pointer(self.depthrenderbuffer))

        self.resize_fbo(1, 1)

    def resize_fbo(self, width, height):
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.fbo)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.rendered_texture)
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGB, width, height, 0, gl.GL_RGB, gl.GL_UNSIGNED_BYTE, 0)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST);
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST);

        gl.glBindRenderbuffer(gl.GL_RENDERBUFFER, self.depthrenderbuffer);
        gl.glRenderbufferStorage(gl.GL_RENDERBUFFER, gl.GL_DEPTH_COMPONENT, width, height);
        gl.glFramebufferRenderbuffer(gl.GL_FRAMEBUFFER, gl.GL_DEPTH_ATTACHMENT, gl.GL_RENDERBUFFER, self.depthrenderbuffer)
        gl.glFramebufferTexture2D(gl.GL_FRAMEBUFFER, gl.GL_COLOR_ATTACHMENT0, gl.GL_TEXTURE_2D, self.rendered_texture, 0)

        draw_buffers = (gl.GLenum * 1)(gl.GL_COLOR_ATTACHMENT0)
        gl.glDrawBuffers(1, draw_buffers);

        if gl.glCheckFramebufferStatus(gl.GL_FRAMEBUFFER) != gl.GL_FRAMEBUFFER_COMPLETE:
            logging.error('setting up fbo failed')

        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)


    def init_gl(self):
        self.fbo = gl.GLuint(0)
        self.rendered_texture = gl.GLuint(0)
        self.depthrenderbuffer = gl.GLuint(0)
        self.create_fbo()
        self.program = GlProgram(shaders.vertex_scene, shaders.fragment_scene)
        self.sprite_program = GlProgram(shaders.vertex_scene, shaders.fragment_sprite)
        self.copy_program = GlProgram(shaders.vertex_copy, shaders.fragment_copy)
        self.buffer = gl.GLuint(0)
        self.map_buffer = gl.GLuint(0)
        self.copy_buffer = gl.GLuint(0)
        gl.glGenBuffers(1, pointer(self.buffer))
        gl.glGenBuffers(1, pointer(self.map_buffer))
        gl.glGenBuffers(1, pointer(self.copy_buffer))

        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        self.texture_map = make_texture(self.tiles.filename)


    def load(self, simulation):
        assert self.simulation is None
        self.simulation = simulation
        self.label = Label(self.wm.root, '', 0, 0)
        self.scroll_to(self.screen_width // 2, self.screen_height)

    def unload(self):
        self.simulation = None
        self.wm.root.close()

    def update(self, dt):
        if self.simulation:
            self.simulation.update(dt * self.speed)
        if 0 <= self.mouse_x < MOUSE_SCROLL_BORDER_WIDTH:
            self.scroll(dt * MOUSE_SCROLL_SPEED, 0)
        if self.screen_width - MOUSE_SCROLL_BORDER_WIDTH <= self.mouse_x < self.screen_width:
            self.scroll(-dt * MOUSE_SCROLL_SPEED, 0)
        if 0 <= self.mouse_y < MOUSE_SCROLL_BORDER_WIDTH:
            self.scroll(0, -dt * MOUSE_SCROLL_SPEED)
        if self.screen_height - MOUSE_SCROLL_BORDER_WIDTH <= self.mouse_y < self.screen_height:
            self.scroll(0, dt * MOUSE_SCROLL_SPEED)


    def get_map_vertex_data(self):
        floor = self.tiles.tiles['Grass']
        points = [(0, 0), (1, 0), (1, 1), (0, 1)]

        pathtiles = {p:self.tiles.tiles['Road%d' % p] for p in range(16)}
        pathtiles[None] = [(0, 0), (0, 0), (0, 0), (0, 0)]

        z = 0.0

        for x, row in enumerate(self.simulation.map):
            for y, tile in enumerate(row):
                zbuf = zbuffer(x, y, z, ZMODE_BOTTOM)
                for (dx, dy), (u, v), (s, t) in zip(points, floor, pathtiles[tile.path]):
                    yield from (x + dx, y + dy, z, zbuf,
                                u, v, s, t)


    def get_sprite_vertex_data(self, sprite, objects):
        for i, obj in enumerate(objects):
            yield from sprite.vertex_data(self.simulation.time, **obj.__dict__)

#         if objects is (self.simulation.shops):
#             yield from passage_vtx(2, 5, 1)
#             yield from passage_vtx(7, 3, 2)


    def set_mouse_pos_world(self):
        depth = ctypes.c_float(0.0)
        gl.glReadPixels(self.mouse_x, self.mouse_y, 1, 1, gl.GL_DEPTH_COMPONENT, gl.GL_FLOAT, pointer(depth))  # print(depth, decode_zbuffer(depth.value * 2 - 1))
        xmy = math.floor((self.mouse_x - self.screen_origin_x) / VOXEL_X_SIDE)
        xpy, Z, mode, sub = decode_zbuffer(depth.value * 2 - 1)
        if (xmy + xpy) % 2 == 0:
            X = (xmy + xpy) // 2
            Y = (xpy - xmy) // 2
        else:
            X = (xmy + xpy + 1) // 2
            Y = (xpy - xmy - 1) // 2
        self.mouse_pos_world = X, Y, Z, mode, sub


    def draw(self):
        if self.simulation is None:
            return
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.fbo)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        gl.glEnable(gl.GL_DEPTH_TEST)
        now = self.simulation.current_datetime()
        self.label.text = 'Simulated date is {} + {:0.1f}'.format(format_date(now), now[3])

        self.program.use()
        self.program.vertex_attrib_pointer(self.map_buffer, b"position", 4, stride=8 * sizeof(gl.GLfloat))
        self.program.vertex_attrib_pointer(self.map_buffer, b"texcoord", 4, stride=8 * sizeof(gl.GLfloat), offset=4 * sizeof(gl.GLfloat))

        self.draw_map()

        self.sprite_program.use()
        self.sprite_program.vertex_attrib_pointer(self.buffer, b"position", 4, stride=8 * sizeof(gl.GLfloat))
        self.sprite_program.vertex_attrib_pointer(self.buffer, b"texcoord", 4, stride=8 * sizeof(gl.GLfloat), offset=4 * sizeof(gl.GLfloat))

        self.draw_scene()
        self.draw_persons()


        self.set_mouse_pos_world()

        gl.glDisable(gl.GL_DEPTH_TEST)

        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)

        self.copy_program.use()
        self.copy_program.vertex_attrib_pointer(self.copy_buffer, b"position", 4, stride=4 * sizeof(gl.GLfloat))

        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.rendered_texture)
        self.copy_program.uniform1i(b"tex", 0)

        data = (gl.GLfloat * 16)(-1, -1, 0, 0,
                                 - 1, 1, 0, 1,
                                  1, 1, 1, 1,
                                  1, -1, 1, 0)

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.copy_buffer)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, sizeof(data), data, gl.GL_DYNAMIC_DRAW)
        gl.glDrawArrays(gl.GL_QUADS, 0, 4)



    def draw_map(self):
        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_map)
        self.program.uniform1i(b"tex", 0)  # set to 0 because the texture is bound to GL_TEXTURE0

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.map_buffer)
        if self.simulation.map_dirty:
            data = list(self.get_map_vertex_data())
            data = (gl.GLfloat * len(data))(*data)
            self.simulation.map_dirty = False
            gl.glBufferData(gl.GL_ARRAY_BUFFER, sizeof(data), data, gl.GL_DYNAMIC_DRAW)
            self.map_data_length = len(data) // 8

        gl.glDrawArrays(gl.GL_QUADS, 0, self.map_data_length)

    def draw_persons(self):
        sprite = self.sprite_pers
        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, sprite.texture)
        self.sprite_program.uniform1i(b"tex", 0)  # set to 0 because the texture is bound to GL_TEXTURE0

        gl.glActiveTexture(gl.GL_TEXTURE1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, sprite.texture_pal)
        self.sprite_program.uniform1i(b"palette", 1)  # set to 1 because the texture is bound to GL_TEXTURE1

        self.pers.clear()
        for pers in self.simulation.persons:
            self.pers[math.floor(pers.x), math.floor(pers.y)].append(pers)

        data = []
        for lst in self.pers.values():
            lst.sort(key=lambda pers: pers.x + pers.y)
            for rank, pers in enumerate(lst):
                data.extend(sprite.vertex_data(self.simulation.time, rank=rank, mode=ZMODE_SUBVOX_MIDDLE, **pers.__dict__))


        data = []
        for pers in self.simulation.persons:
            data.extend(sprite.vertex_data(self.simulation.time, **pers.__dict__))

        data = (gl.GLfloat * len(data))(*data)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.buffer)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, sizeof(data), data, gl.GL_DYNAMIC_DRAW)

        gl.glDrawArrays(gl.GL_QUADS, 0, len(data) // 8)

    def draw_scene(self):
        sprite = self.sprite_shop
        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, sprite.texture)
        self.sprite_program.uniform1i(b"tex", 0)  # set to 0 because the texture is bound to GL_TEXTURE0

        gl.glActiveTexture(gl.GL_TEXTURE1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, sprite.texture_pal)
        self.sprite_program.uniform1i(b"palette", 1)  # set to 1 because the texture is bound to GL_TEXTURE1

        sprites = {'shop': self.sprite_shop, 'entrance': self.sprite_entrance}
        data = list(d for obj in self.simulation.scene for d in sprites[obj.type].vertex_data(self.simulation.time, **obj.__dict__))
        data = (gl.GLfloat * len(data))(*data)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.buffer)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, sizeof(data), data, gl.GL_DYNAMIC_DRAW)

        gl.glDrawArrays(gl.GL_QUADS, 0, len(data) // 8)




    def on_resize(self, x, y):
        '''update the window size when the opengl viewport is resized'''
        self.resize_fbo(x, y)
        self.program.uniform2f(b'window_size', x, y)
        self.sprite_program.uniform2f(b'window_size', x, y)
        self.screen_width = x
        self.screen_height = y
        self.scroll_to(x // 2, y // 2)
        self.mouse_x = x // 2
        self.mouse_y = y // 2

    def on_mouse_press(self, x, y, button, modifiers):
        logging.debug('SimulationView.on_mouse_press({}, {})'.format(x, y))

        otype, obj = self.get_pointed_object()

        if otype == 'pers':
            logging.debug('clicked Person %s', obj.name)

        else:
            X = self.mouse_pos_world[0]
            Y = self.mouse_pos_world[1]

            if (0 <= X < self.simulation.world_width and
                0 <= Y < self.simulation.world_height):

                if button == mouse.LEFT:
                    self.simulation.set_path(X, Y, True)
                elif button == mouse.RIGHT:
                    self.simulation.remove_scenery(X, Y, 0)

    def on_mouse_motion(self, x, y, dx, dy):
        self.mouse_x = x
        self.mouse_y = y

    def on_mouse_leave(self, x, y):
        self.mouse_x = x
        self.mouse_y = y

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if buttons == mouse.MIDDLE:
            self.scroll(dx, -dy)

    def on_key_press(self, symbol, modifiers):
        if symbol == key.UP:
            self.scroll(0, +20)
        if symbol == key.DOWN:
            self.scroll(0, -20)
        if symbol == key.LEFT:
            self.scroll(+20, 0)
        if symbol == key.RIGHT:
            self.scroll(-20, 0)
        if symbol == key.SPACE:
            if self.speed:
                self.speed = 0
            else:
                self.speed = 1.0
        if symbol == key.NUM_ADD:
            self.speed += 0.5
        if symbol == key.NUM_SUBTRACT:
            self.speed = max(0.0, self.speed - 0.5)

    def scroll(self, dx, dy):
        self.scroll_to(self.screen_origin_x + dx, self.screen_origin_y + dy)

    def scroll_to(self, x, y):
        self.program.uniform2f(b'screen_origin', x // 1, -y // 1)
        self.sprite_program.uniform2f(b'screen_origin', x // 1, -y // 1)
        self.screen_origin_x = x
        self.screen_origin_y = y

    def get_pointed_object(self):
        X, Y, Z, mode, rank = self.mouse_pos_world
        if mode == ZMODE_SUBVOX_MIDDLE:
            # currently only persons
            if len(self.pers[X, Y]) > rank:
                return ('pers', self.pers[X, Y][rank])

        elif mode in (ZMODE_CENTER, ZMODE_FRONT, ZMODE_BACK):
            if len(self.scenery[X, Y]) > rank:
                return ('scen', self.scen[X, Y][rank])

        return (None, None)
