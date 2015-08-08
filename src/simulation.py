'''
Created on 8 Jul 2015

@author: leonhard
'''

import enum
import path_graph
@enum.unique
class Terrain(enum.Enum):
    GRASS = 1

import random
import logging

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
        self.path = None

    def __repr__(self):
        return 'T[{}][{}]'.format(self.column, self.row)

    def serialize(self):
        return {'p': self.path}

    @staticmethod
    def deserialize(col, row, data):
        self = Tile(Terrain.GRASS, row, col)
        self.path = data['p']
        return self

class Object:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def serialize(self):
        return self.__dict__

    @staticmethod
    def deserialize(data):
        return Object(**data)


class Person:
    def __init__(self, simu, name, x, y, t):
        self.simu = simu
        self.name = name
        self.x = x
        self.y = y
        self.action = 'wait'
        self.pose = 'stand'
        self.action_started = 0
        self.target = None
        self.next_waypoint = None
        self.last = None
        self.direction = 0
        self.speed = 0.45
        self.arrival_time = t

    def update(self, t, dt):
        if self.action == 'wait':
            if t >= self.action_started + 1.0:
                self.target = None
                self.next_waypoint = None
                self.last = None

                self.action = 'walk'
                self.action_started = t


        elif self.action == 'walk':
            if self.next_waypoint is None:
                if self.target:
                    assert False, 'Not yet implemented'
                else:
                    X = int(self.x)
                    Y = int(self.y)
                    p = self.simu.path_graph.path.get((X, Y, 0))
                    if p is None:
                        # we are not on a path
                        self.action = 'wait'
                        self.action_started = t
                        return
                    if not p.neighbours:
                        # we are on an isolated path
                        self.action = 'wait'
                        self.action_started = t
                        return
                    nbs = p.neighbours
                    if len(nbs) > 1:
                        nbs = [nb for nb in nbs if nb.pos != self.last]
                    self.last = p.pos
                    nb = random.choice(nbs)
                    if nb.ptype < path_graph.TYPE_POI_XU:
                        frac = random.uniform(0.2, 0.8)
                    else:
                        frac = 0.1

                    if nb.pos[0] == X:
                        self.next_waypoint = (self.x, nb.pos[1] + frac)
                    else:
                        assert nb.pos[1] == Y
                        self.next_waypoint = (nb.pos[0] + frac, self.y)

            if self.next_waypoint[0] < self.x:
                self.x -= self.speed * dt
                self.x = max(self.x, self.next_waypoint[0])
            elif self.next_waypoint[0] > self.x:
                self.x += self.speed * dt
                self.x = min(self.x, self.next_waypoint[0])
            elif self.next_waypoint[1] < self.y:
                self.y -= self.speed * dt
                self.y = max(self.y, self.next_waypoint[1])
            elif self.next_waypoint[1] > self.y:
                self.y += self.speed * dt
                self.y = min(self.y, self.next_waypoint[1])
            else:
                self.next_waypoint = None
        self.update_pose()

    def update_pose(self):
        if self.action == 'wait' or self.next_waypoint is None:
            self.pose = 'stand'
        elif self.action == 'walk':
            self.pose = 'walk'
            if self.next_waypoint[0] < self.x:
                self.direction = 180
            elif self.next_waypoint[0] > self.x:
                self.direction = 0
            elif self.next_waypoint[1] < self.y:
                self.direction = 270
            elif self.next_waypoint[1] > self.y:
                self.direction = 90
        else:
            assert False, 'unknown action ' + self.action


    def serialize(self):
        return {'name': self.name,
                'pos': (self.x, self.y),
                'action': self.action,
                'action_started': self.action_started,
                'target': self.target,
                'next_waypoint': self.next_waypoint}

    @staticmethod
    def deserialize(simu, data):
        self = Person(simu, data['name'], data['pos'][0], data['pos'][1])
        self.action = data['action']
        self.action_started = data['action_started']
        self.target = data['target']
        self.waypoints = data['next_waypoint']
        self.update_pose()
        return self


class Simulation:
    '''
    classdocs
    '''


    def __init__(self, world_width, world_height):
        '''
        Constructor
        '''
        self.world_width = world_width
        self.world_height = world_height
        self.map = [[Tile(Terrain.GRASS, row, col)
                     for row in range(world_height)] for col in range(world_width)]
        self.path_graph = path_graph.PathGraph()

        self.persons = [Person(self, i, i // 6 * 2 + 0.5, i % 6 * 2 + 0.5, random.uniform(0, 0.125)) for i in range(32)]
        self.shops = []
        self.time = 0
        self.add_shop(4, 4)

    def set_path(self, column, row, path):
        pos = (column, row, 0)
        if path:
            if pos in self.path_graph.path:
                return
            self.path_graph.add_path_element((column, row, 0), path_graph.TYPE_FLAT)
            self.map[column][row].path = self.path_graph.path[(column, row, 0)].connection_bitfield
            neighbours = self.path_graph.path[pos].neighbours
        else:
            if pos not in self.path_graph.path:
                return
            neighbours = self.path_graph.path[pos].neighbours
            self.map[column][row].path = None
            self.path_graph.remove_path_element((column, row, 0))
        for nb in neighbours:
            if nb.ptype < path_graph.TYPE_POI_XU:
                self.map[nb.pos[0]][nb.pos[1]].path = nb.connection_bitfield

    def update(self, delta_sim_seconds):
        self.time += delta_sim_seconds
        if delta_sim_seconds > 0:
            for person in self.persons:
                person.update(self.time, delta_sim_seconds)

    def current_datetime(self):
        return get_datetime(self.time)

    def add_shop(self, x, y):
        shop = Object(x=x, y=y, name='Shop')
        print ('Path = ', self.map[x][y].path)
        self.shops.append(shop)
        print (self.path_graph.path.get((x, y, 0), 'nada'))
        self.path_graph.add_path_element((x, y, 0), path_graph.TYPE_POI_XD, shop)


    def serialize(self):
        return {'world_width': self.world_width,
                'world_height': self.world_height,
                'time': self.time,
                'map': [[tile.serialize() for tile in col] for col in self.map],
                'shops': [shop.serialize() for shop in self.shops],
                'persons': [pers.serialize() for pers in self.persons]}

    @staticmethod
    def deserialize(data):
        self = Simulation(data['world_width'], data['world_height'])
        self.map = [[Tile.deserialize(col, row, tile_data) for row, tile_data in enumerate(col_data)] for col, col_data in enumerate(data['map'])]
        for column in self.map:
            for tile in column:
                if tile.path is not None:
                    self.set_path(tile.column, tile.row, True)
        for shop in data['shops']:
            shop = Object.deserialize(shop)
            self.add_shop(shop.x, shop.y)
        self.persons = [Person.deserialize(self, pers) for pers in data['persons']]
        self.time = data['time']
        return self



