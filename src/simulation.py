'''
Created on 8 Jul 2015

@author: leonhard
'''

import enum
@enum.unique
class Terrain(enum.Enum):
    GRASS = 1

import random

SECONDS_PER_DAY = 120
DAYS_PER_MONTH = 4
MONTHS_PER_YEAR = 8

def get_datetime(sec):
    day, time = divmod(sec, SECONDS_PER_DAY)
    day = int(day)
    month, day = divmod(day, DAYS_PER_MONTH)
    year, month = divmod(month, MONTHS_PER_YEAR)
    return (year, month, day, time)

class Tile:
    def __init__(self, terrain, row, column):
        self.row = row
        self.column = column
        self.terrain = terrain

class Person:
    def __init__(self, name, x, y):
        self.name = name
        self.x = x
        self.y = y
        self.action = 'wait'
        self.pose = 'stand'
        self.action_started = 0
        self.target = (x, y)
        self.direction = 0
        self.speed = 0.35

    def update(self, t, dt):
        if self.action == 'wait':
            if t >= self.action_started + 1.0:
                self.action = 'walk'
                self.pose = 'walk'
                self.action_started = t
                self.target = (random.uniform(0, 4), random.uniform(0, 3))
        elif self.action == 'walk':
            if self.target[0] < self.x:
                self.direction = 180
                self.x -= self.speed * dt
                self.x = max(self.x, self.target[0])
            elif self.target[0] > self.x:
                self.direction = 0
                self.x += self.speed * dt
                self.x = min(self.x, self.target[0])
            elif self.target[1] < self.y:
                self.direction = 270
                self.y -= self.speed * dt
                self.y = max(self.y, self.target[1])
            elif self.target[1] > self.y:
                self.direction = 90
                self.y += self.speed * dt
                self.y = min(self.y, self.target[1])
            else:
                self.action = 'wait'
                self.action_started = t
                self.pose = 'stand'


class Simulation:
    '''
    classdocs
    '''


    def __init__(self, world_width, world_height):
        '''
        Constructor
        '''

        self.map = [[Tile(Terrain.GRASS, row, col)
                     for row in range(world_height)] for col in range(world_width)]

        self.persons = [Person('Leonhard', 0.3, 0.6)]

        self.time = 0

    def update(self, delta_sim_seconds):
        self.time += delta_sim_seconds
        if delta_sim_seconds > 0:
            for person in self.persons:
                person.update(self.time, delta_sim_seconds)

    def current_datetime(self):
        return get_datetime(self.time)
