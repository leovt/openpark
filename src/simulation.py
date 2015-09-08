'''
Created on 8 Jul 2015

@author: leonhard
'''

import enum
import path_graph
from math import floor
from itertools import count

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
    def __init__(self, simu, name, x, y, t, palette):
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
        self.palette = palette


    def get_next_waypoint(self):
        X = floor(self.x)
        Y = floor(self.y)
        p = self.simu.path_graph.path.get((X, Y, 0))
        if p is None:  # we are not on a path
            return None
        if not p.neighbours:  # we are on an isolated path
            return None
        nbs = p.neighbours
        if len(nbs) > 1:
            nbs = [nb for nb in nbs if nb.pos != self.last]
        self.last = p.pos
        nb = random.choice(nbs)
        if nb.ptype < path_graph.TYPE_POI_XU:
            frac = random.uniform(0.2, 0.8)
        elif nb.ptype in (path_graph.TYPE_POI_XU, path_graph.TYPE_POI_YU):
            frac = 0.9
        else:
            frac = 0.1
        if nb.pos[0] == X:
            return self.x, nb.pos[1] + frac
        else:
            assert nb.pos[1] == Y
            return nb.pos[0] + frac, self.y

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
                if (floor(self.x), floor(self.y), 0) == self.simu.map_entrance:
                    # walked out, quit
                    self.simu.persons.remove(self)
                else:
                    self.next_waypoint = self.get_next_waypoint()

            if self.next_waypoint is None:
                self.action = 'wait'
                self.action_started = t
                return None

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
        self = Person(simu, data['name'], data['pos'][0], data['pos'][1], data['t'], data['pal'])
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
        self.map_dirty = True
        self.path_graph = path_graph.PathGraph()

        self.persons = []
        self.scene = []
        self.voxel = {}
        self.time = 0

        self.map_entrance = (5, -1, 0)
        self.path_graph.add_path_element(self.map_entrance, path_graph.TYPE_POI_YU, 'MapEntrance')

        self.add_shop(4, 4)
        self.add_entrance(5, 1)

        self.t_next_person = 1
        self.person_freq = 0.1  # on average 1 person every 10 sec
        self.person_ids = iter(count(1))

    def remove_scenery(self, x, y, z):
        obj = self.voxel.get((x, y, z), None)
        if obj:
            self.scene.remove(obj)
            delpos = [pos for pos, ob in self.voxel.items() if ob is obj]
            for pos in delpos:
                del self.voxel[pos]
        self.set_path(x, y, False)

    def set_path(self, column, row, path):
        self.map_dirty = True
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
            if self.time > self.t_next_person:
                self.t_next_person += random.expovariate(self.person_freq)
                pid = next(self.person_ids)
                dx = random.uniform(0.2, 0.8)
                pers = Person(self, 'Guest %d' % pid, self.map_entrance[0] + dx, 0, self.time, random.randrange(32))
                pers.next_waypoint = (self.map_entrance[0] + dx, random.uniform(0.2, 0.8))
                pers.action = 'walk'
                pers.last = self.map_entrance
                self.persons.append(pers)

            for person in self.persons:
                person.update(self.time, delta_sim_seconds)

    def current_datetime(self):
        return get_datetime(self.time)

    def add_shop(self, x, y):
        shop = Object(x=x, y=y, name='Shop', direction=180, type='shop')
        self.scene.append(shop)
        self.path_graph.add_path_element((x, y, 0), path_graph.TYPE_POI_XD, shop)
        self.voxel[x, y, 0] = shop
        self.voxel[x, y, 1] = shop

    def add_entrance(self, x, y):
        entr = Object(x=x, y=y, direction=90, type='entrance', name='Park Entrance')
        self.scene.append(entr)
        self.path_graph.add_path_element((x, y, 0), path_graph.TYPE_FLAT, entr)
        self.voxel[x, y, 0] = entr
        self.voxel[x, y, 1] = entr

    def serialize(self):
        return {'world_width': self.world_width,
                'world_height': self.world_height,
                'time': self.time,
                'map': [[tile.serialize() for tile in col] for col in self.map],
                'scene': [element.serialize() for element in self.scene],
                'persons': [pers.serialize() for pers in self.persons]}

    @staticmethod
    def deserialize(data):
        self = Simulation(data['world_width'], data['world_height'])
        self.map = [[Tile.deserialize(col, row, tile_data) for row, tile_data in enumerate(col_data)] for col, col_data in enumerate(data['map'])]
        for column in self.map:
            for tile in column:
                if tile.path is not None:
                    self.set_path(tile.column, tile.row, True)

        self.persons = [Person.deserialize(self, pers) for pers in data['persons']]
        self.time = data['time']
        return self



