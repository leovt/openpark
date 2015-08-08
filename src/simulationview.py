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
import sprite

from graphix import make_texture
from textmanager import Rect

VOXEL_HEIGHT = 19;
VOXEL_Y_SIDE = 24;
VOXEL_X_SIDE = VOXEL_Y_SIDE * 2;

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

        self.sprite = sprite.Sprite('../art/guest.ini')
        self.sprite.set_pose('walk')
        self.sprite.turn_to(180)
        self.tiles = tileset('../art/map.ini')
        self.init_gl()

    def init_gl(self):
        self.program = GlProgram(shaders.vertex_scene, shaders.fragment_scene)
        self.sprite_program = GlProgram(shaders.vertex_scene, shaders.fragment_sprite)
        self.buffer = gl.GLuint(0)
        gl.glGenBuffers(1, pointer(self.buffer))
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.buffer)

        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        self.texture_map = make_texture(self.tiles.filename)
        self.texture_sprite = make_texture('../art/guest.png', indexed=True)
        self.texture_sprite_pal = make_texture('../art/guest_pal.png')


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

        du = VOXEL_X_SIDE / TEXTURE_WIDTH
        dv = VOXEL_Y_SIDE / TEXTURE_HEIGHT

        uv = [((1 + 2 * (n % 4)) * du, (2 + 2 * (n // 4)) * dv) for n in range(16)]


        floor = self.tiles.tiles['Grass']
        points = [(0, 0), (1, 0), (1, 1), (0, 1)]

        pathtiles = {p:self.tiles.tiles['Road%d' % p] for p in range(16)}
        pathtiles[None] = [(0, 0), (0, 0), (0, 0), (0, 0)]

        for x, row in enumerate(self.simulation.map):
            for y, tile in enumerate(row):
                for (dx, dy), (u, v), (s, t) in zip(points, floor, pathtiles[tile.path]):
                    yield from (x + dx, y + dy, 0.0, 1.0,
                                u, v, s, t)


    def get_sprite_vertex_data(self):
        for shop in self.simulation.shops:
            dz_down = -VOXEL_Y_SIDE / VOXEL_HEIGHT
            dz_up = (96 - VOXEL_Y_SIDE) / VOXEL_HEIGHT
            r = Rect(0, 416 / 512, 96 / 1024, 512 / 512)
            yield from (shop.x, shop.y + 1, dz_down, 0, r.left, r.bottom, 0, 0)
            yield from (shop.x + 1, shop.y, dz_down, 0, r.right, r.bottom, 0, 0)
            yield from (shop.x + 1, shop.y, dz_up, 0, r.right, r.top, 0, 0)
            yield from (shop.x, shop.y + 1, dz_up, 0, r.left, r.top, 0, 0)


        for i, person in enumerate(self.simulation.persons):
            self.sprite.set_pose(person.pose)
            self.sprite.turn_to(person.direction)
            r = self.sprite.get_coordinates(self.simulation.time - person.arrival_time)

            dx = self.sprite.offset_x / VOXEL_X_SIDE * 0.5
            dz_up = self.sprite.offset_y / VOXEL_HEIGHT
            dz_down = -self.sprite.frame_height / VOXEL_HEIGHT + dz_up

            yield from (person.x - dx, person.y + dx, dz_down, 0, r.left, r.bottom, i, 0)
            yield from (person.x - dx, person.y + dx, dz_up, 0, r.left, r.top, i, 0)
            yield from (person.x + dx, person.y - dx, dz_up, 0, r.right, r.top, i, 0)
            yield from (person.x + dx, person.y - dx, dz_down, 0, r.right, r.bottom, i, 0)

    def draw(self):
        if self.simulation is None:
            return
        now = self.simulation.current_datetime()
        self.label.text = 'Simulated date is {} + {:0.1f}'.format(format_date(now), now[3])

        self.program.use()
        self.program.vertex_attrib_pointer(self.buffer, b"position", 4, stride=8 * sizeof(gl.GLfloat))
        self.program.vertex_attrib_pointer(self.buffer, b"texcoord", 4, stride=8 * sizeof(gl.GLfloat), offset=4 * sizeof(gl.GLfloat))

        self.draw_map()

        self.sprite_program.use()
        self.sprite_program.vertex_attrib_pointer(self.buffer, b"position", 4, stride=8 * sizeof(gl.GLfloat))
        self.sprite_program.vertex_attrib_pointer(self.buffer, b"texcoord", 4, stride=8 * sizeof(gl.GLfloat), offset=4 * sizeof(gl.GLfloat))

        self.draw_sprites()


    def draw_map(self):
        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_map)
        self.program.uniform1i(b"tex", 0)  # set to 0 because the texture is bound to GL_TEXTURE0

        data = list(self.get_map_vertex_data())
        data = (gl.GLfloat * len(data))(*data)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.buffer)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, sizeof(data), data, gl.GL_DYNAMIC_DRAW)

        gl.glDrawArrays(gl.GL_QUADS, 0, len(data) // 8)

    def draw_sprites(self):
        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_sprite)
        self.sprite_program.uniform1i(b"tex", 0)  # set to 0 because the texture is bound to GL_TEXTURE0

        gl.glActiveTexture(gl.GL_TEXTURE1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_sprite_pal)
        self.sprite_program.uniform1i(b"palette", 1)  # set to 1 because the texture is bound to GL_TEXTURE1

        data = list(self.get_sprite_vertex_data())
        data = (gl.GLfloat * len(data))(*data)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.buffer)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, sizeof(data), data, gl.GL_DYNAMIC_DRAW)

        gl.glDrawArrays(gl.GL_QUADS, 0, len(data) // 8)


    def on_resize(self, x, y):
        '''update the window manager when the opengl viewport is resized'''
        self.program.uniform2f(b'window_size', x, y)
        self.sprite_program.uniform2f(b'window_size', x, y)
        self.screen_width = x
        self.screen_height = y
        self.scroll_to(x // 2, y // 2)
        self.mouse_x = x // 2
        self.mouse_y = y // 2

    def on_mouse_press(self, x, y, button, modifiers):
        logging.debug('SimulationView.on_mouse_press({}, {})'.format(x, y))
        tile = self.find_tile_at(x - self.screen_origin_x, self.screen_origin_y - y)
        if not tile:
            return
        if button == mouse.LEFT:
            self.simulation.set_path(tile[0], tile[1], True)
        elif button == mouse.RIGHT:
            self.simulation.set_path(tile[0], tile[1], False)

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

    def find_tile_at(self, x, y):
        ''' x,y screen coordinates'''

        # for now we know that the map is at Z=0, so we can directly transform
        # screen coordinates into voxel coordinates.

        X = int((x + 2 * y) // (4 * VOXEL_Y_SIDE))  # integer division ensures rounding down instead of towards zero
        Y = int((2 * y - x) // (4 * VOXEL_Y_SIDE))

        logging.debug('({}, {}) -> ({}, {})'.format(x, y, X, Y))
        if (0 <= X < self.simulation.world_width and
            0 <= Y < self.simulation.world_height):
            return X, Y
        else:
            return None

