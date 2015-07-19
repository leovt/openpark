'''
Created on 18 Jul 2015

@author: leonhard
'''
import configparser
from collections import namedtuple
import PIL.Image
from textmanager import Rect
import logging

PoseInfo = namedtuple('PoseInfo', 'number_of_frames, first_frame')

class Sprite:
    def __init__(self, inifile):
        '''
        Constructor
        '''
        conf = configparser.SafeConfigParser()
        conf.read(inifile)

        # self.image = PIL.Image.open(conf.get('Sprite', 'filename'))

        self.frame_width = conf.getint('Sprite', 'frame_width')
        self.frame_height = conf.getint('Sprite', 'frame_height')
        self.frame_width_uv = self.frame_width / conf.getint('Sprite', 'tex_width')
        self.frame_height_uv = self.frame_height / conf.getint('Sprite', 'tex_height')

        self.start_deg = conf.getint('Sprite', 'start_deg')
        self.turn_deg = conf.getint('Sprite', 'turn_deg')
        self.offset_x = conf.getint('Sprite', 'offset_x')
        self.offset_y = conf.getint('Sprite', 'offset_y')

        self.fps = conf.getfloat('Sprite', 'fps')

        poses = [name.strip() for name in conf.get('Sprite', 'poses').split(',')]


        self.poses = {}
        for pose in poses:
            self.poses[pose] = PoseInfo(conf.getint(pose, 'number_of_frames'),
                                        conf.getint(pose, 'first_frame'))

        self.current_pose = self.poses[poses[0]]
        self.current_dir = 0

    def set_pose(self, pose):
        ''' set the pose to be displayed '''
        self.current_pose = self.poses[pose]

    def turn_to(self, degrees):
        ''' turn to the given angle in degrees '''
        if self.turn_deg > 0:
            self.current_dir = ((degrees - self.start_deg + 360) % 360) // self.turn_deg
        else:
            self.current_dir = ((-degrees + self.start_deg + 360) % 360) // (-self.turn_deg)
        # logging.debug('turn to {} ({})'.format(degrees, self.current_dir))

    def get_coordinates(self, time):
        ''' get texture coordinates for a quad as a Rect'''
        frame_no = int(time * self.fps) % self.current_pose.number_of_frames + self.current_pose.first_frame
        x0 = self.frame_width_uv * self.current_dir
        y0 = self.frame_height_uv * frame_no
        return Rect(x0, y0, x0 + self.frame_width_uv, y0 + self.frame_height_uv)
