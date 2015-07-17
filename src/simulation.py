'''
Created on 8 Jul 2015

@author: leonhard
'''

import enum
@enum.unique
class Terrain(enum.Enum):
    GRASS = 1

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

        self.persons = [('Leonhard', (0.3, 0.6, 0.0))]

        self.time = 0

    def update(self, delta_sim_seconds):
        self.time += delta_sim_seconds

    def current_datetime(self):
        return get_datetime(self.time)
