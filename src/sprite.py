'''
Created on 18 Jul 2015

@author: leonhard
'''
import configparser
from collections import namedtuple
from textmanager import Rect
import logging
import graphix
import os.path

from simulationview import VOXEL_HEIGHT, VOXEL_X_SIDE, VOXEL_Y_SIDE, zbuffer, ZMODE_CENTER

PoseInfo = namedtuple('PoseInfo', 'number_of_frames, first_frame')

class Sprite:
    def __init__(self, inifile):
        '''
        Constructor
        '''
        conf = configparser.SafeConfigParser()
        conf.read(inifile)

        self.inifile = inifile

        self.texture = graphix.make_texture(os.path.join(os.path.dirname(inifile), conf.get('Sprite', 'filename')), True)
        self.texture_pal = graphix.make_texture(os.path.join(os.path.dirname(inifile), conf.get('Sprite', 'palette')), False)

        self.frame_width = conf.getint('Sprite', 'frame_width')
        self.frame_height = conf.getint('Sprite', 'frame_height')
        self.frame_width_uv = self.frame_width / conf.getint('Sprite', 'tex_width')
        self.frame_height_uv = self.frame_height / conf.getint('Sprite', 'tex_height')

        self.start_deg = conf.getint('Sprite', 'start_deg')
        self.turn_deg = conf.getint('Sprite', 'turn_deg')
        self.offset_x = conf.getint('Sprite', 'offset_x')
        self.offset_y = conf.getint('Sprite', 'offset_y')

        directions = conf.getint('Sprite', 'offset_y')
        layers = conf.get('Sprite', 'layers').split()

        mode = {'auto': None, 'center': ZMODE_CENTER}

        self.layers = [(mode[layer], i * directions * self.frame_width_uv)
                       for i, layer in enumerate(layers)]


        if conf.has_section('Animation'):
            self.animated = True
            self.fps = conf.getfloat('Animation', 'fps')

            poses = [name.strip() for name in conf.get('Animation', 'poses').split(',')]


            self.poses = {}
            for pose in poses:
                self.poses[pose] = PoseInfo(conf.getint(pose, 'number_of_frames'),
                                            conf.getint(pose, 'first_frame'))

        else:
            self.animated = False
            self.poses = {None:PoseInfo(1, 0)}

    def __repr__(self):
        return 'Sprite(%s)' % self.inifile

    def vertex_data(self, time, x=0, y=0, z=0, direction=0, pose=None, palette=0, **_kw):
        r = self.get_coordinates(time, pose, direction)

        dx = self.offset_x / VOXEL_X_SIDE * 0.5
        dz_up = self.offset_y / VOXEL_HEIGHT
        dz_down = -self.frame_height / VOXEL_HEIGHT + dz_up

        for mode, u_offset in self.layers:
            zbuf = zbuffer(x, y, 0.0, mode)
            yield from (x - dx, y + dx, z + dz_down, zbuf, r.left + u_offset, r.bottom, palette, 0)
            yield from (x - dx, y + dx, z + dz_up, zbuf, r.left + u_offset, r.top, palette, 0)
            yield from (x + dx, y - dx, z + dz_up, zbuf, r.right + u_offset, r.top, palette, 0)
            yield from (x + dx, y - dx, z + dz_down, zbuf, r.right + u_offset, r.bottom, palette, 0)

    def get_coordinates(self, time, pose, direction):
        ''' get texture coordinates for a quad as a Rect'''
        current_pose = self.poses[pose]
        if self.turn_deg > 0:
            current_dir = ((direction - self.start_deg + 360) % 360) // self.turn_deg
        else:
            current_dir = ((-direction + self.start_deg + 360) % 360) // (-self.turn_deg)

        if self.animated:
            frame_no = int(time * self.fps) % current_pose.number_of_frames + current_pose.first_frame
        else:
            frame_no = 0

        x0 = self.frame_width_uv * current_dir
        y0 = self.frame_height_uv * frame_no
        return Rect(x0, y0, x0 + self.frame_width_uv, y0 + self.frame_height_uv)

