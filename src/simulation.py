'''
Created on 8 Jul 2015

@author: leonhard
'''

import enum
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

class Person:
    def __init__(self, simu, name, x, y):
        self.simu = simu
        self.name = name
        self.x = x
        self.y = y
        self.action = 'wait'
        self.pose = 'stand'
        self.action_started = 0
        self.target = (x, y)
        self.waypoints = []
        self.direction = 0
        self.speed = 0.35

    def update(self, t, dt):
        if self.action == 'wait':
            if self.waypoints:
                logging.debug('Person {} is at {:.1f},{:.1f} and plans to go {}'.format(self.name, self.x, self.y, [(t.column, t.row) for t in self.waypoints]))
                nextwp = self.waypoints.pop()
                self.target = (nextwp.column + 0.5, nextwp.row + 0.5)
                self.action = 'walk'
                self.action_started = t
            elif t >= self.action_started + 1.0:
                self.action = 'walk'
                self.action_started = t
                x, y = (random.uniform(0, 10), random.uniform(0, 10))
                logging.debug('Person {} has new target {:.1f},{:.1f}'.format(self.name, x, y))
                self.waypoints = self.simu.find_path(int(self.x), int(self.y), int(x), int(y))
                if self.waypoints is None:
                    logging.debug('Impossible to go there')
                    self.waypoints = []
                logging.debug('Person {} is at {:.1f},{:.1f} and plans to go {}'.format(self.name, self.x, self.y, [(t.column, t.row) for t in self.waypoints]))
        elif self.action == 'walk':
            if self.target[0] < self.x:
                self.x -= self.speed * dt
                self.x = max(self.x, self.target[0])
            elif self.target[0] > self.x:
                self.x += self.speed * dt
                self.x = min(self.x, self.target[0])
            elif self.target[1] < self.y:
                self.y -= self.speed * dt
                self.y = max(self.y, self.target[1])
            elif self.target[1] > self.y:
                self.y += self.speed * dt
                self.y = min(self.y, self.target[1])
            else:
                self.action = 'wait'
                self.action_started = t
        self.update_pose()

    def update_pose(self):
        if self.action == 'wait':
            self.pose = 'stand'
        elif self.action == 'walk':
            self.pose = 'walk'
            if self.target[0] < self.x:
                self.direction = 180
            elif self.target[0] > self.x:
                self.direction = 0
            elif self.target[1] < self.y:
                self.direction = 270
            elif self.target[1] > self.y:
                self.direction = 90
        else:
            assert False, 'unknown action ' + self.action


    def serialize(self):
        return {'name': self.name,
                'pos': (self.x, self.y),
                'action': self.action,
                'action_started': self.action_started,
                'target': self.target,
                'waypoints': [(t.column, t.row) for t in self.waypoints]}

    @staticmethod
    def deserialize(simu, data):
        self = Person(simu, data['name'], data['pos'][0], data['pos'][1])
        self.action = data['action']
        self.action_started = data['action_started']
        self.target = data['target']
        self.waypoints = [self.simu.map[c][r] for (c, r) in data['waypoints']]
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

        for i, col in enumerate([[3, 10, 9], [5, None, 5], [6, 9, 5], [2, 14, 12]]):
            for j, p in enumerate(col):
                self.map[i][j].path = p

        self.path_graph = {}
        self.make_path_graph()

        self.persons = [Person(self, i, i // 3, i % 3) for i in range(10)]

        self.time = 0

    def set_path(self, column, row, path):
        if path:
            self.map[column][row].path = 0
            if column < self.world_width - 1 and self.map[column + 1][row].path is not None:
                self.map[column][row].path |= 1
                self.map[column + 1][row].path |= 4
            if column > 0 and self.map[column - 1][row].path is not None:
                self.map[column][row].path |= 4
                self.map[column - 1][row].path |= 1
            if row < self.world_height - 1 and self.map[column][row + 1].path is not None:
                self.map[column][row].path |= 2
                self.map[column][row + 1].path |= 8
            if row > 0 and self.map[column][row - 1].path is not None:
                self.map[column][row].path |= 8
                self.map[column][row - 1].path |= 2

        else:
            self.map[column][row].path = None
            if column < self.world_width - 1 and self.map[column + 1][row].path is not None:
                self.map[column + 1][row].path &= 11
            if column > 0 and self.map[column - 1][row].path is not None:
                self.map[column - 1][row].path &= 14
            if row < self.world_height - 1 and self.map[column][row + 1].path is not None:
                self.map[column][row + 1].path &= 7
            if row > 0 and self.map[column][row - 1].path is not None:
                self.map[column][row - 1].path &= 13
        self.make_path_graph()


    def update(self, delta_sim_seconds):
        self.time += delta_sim_seconds
        if delta_sim_seconds > 0:
            for person in self.persons:
                person.update(self.time, delta_sim_seconds)

    def current_datetime(self):
        return get_datetime(self.time)

    def make_path_graph(self):
        self.path_graph.clear()
        mask = [1, 2, 4, 8]
        rmask = [4, 8, 1, 2]
        NB = [(-1, 0, 2), (0, 1, 1), (1, 0, 0), (0, -1, 3)]
        for i, col in enumerate(self.map):
            for j, tile in enumerate(col):
                neighbour_tiles = [(self.map[i + a][j + b], direction) for (a, b, direction) in NB if 0 <= i + a < self.world_width and 0 <= j + b < self.world_height]
                if tile.path is None:
                    self.path_graph[tile] = neighbour_tiles
                else:
                    self.path_graph[tile] = [(t, d) for (t, d) in neighbour_tiles if tile.path & mask[d] and t.path is not None and t.path & rmask[d]]

    def find_path(self, a, b, i, j):
        start = self.map[a][b]
        goal = self.map[i][j]

        def heuristic_cost_estimate(A, B):
            return abs(A.row - B.row) + abs(A.column - B.column)

        # A* Algorithm
        closedset = set()  # The set of nodes already evaluated.
        openset = {start}  # The set of tentative nodes to be evaluated, initially containing the start node
        came_from = {}  # The map of navigated nodes.

        g_score = {}
        g_score[start] = 0  # Cost from start along best known path.
        # Estimated total cost from start to goal through y.
        f_score = {}
        f_score[start] = g_score[start] + heuristic_cost_estimate(start, goal)

        while openset:
            current = min(openset, key=lambda A:f_score[A])  # the node in openset having the lowest f_score[] value
            if current is goal:
                path = []
                while current != start:
                    path.append(current)
                    current = came_from[current]
                return path

            openset.discard(current)
            closedset.add(current)
            for neighbor, _ in self.path_graph[current]:
                if neighbor in closedset:
                    continue
                tentative_g_score = g_score[current] + 1

                if neighbor not in openset or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = g_score[neighbor] + heuristic_cost_estimate(neighbor, goal)
                    openset.add(neighbor)

        return None  # no path found

    def serialize(self):
        return {'world_width': self.world_width,
                'world_height': self.world_height,
                'time': self.time,
                'map': [[tile.serialize() for tile in col] for col in self.map],
                'persons': [pers.serialize() for pers in self.persons]}

    @staticmethod
    def deserialize(data):
        self = Simulation(data['world_width'], data['world_height'])
        self.map = [[Tile.deserialize(col, row, tile_data) for row, tile_data in enumerate(col_data)] for col, col_data in enumerate(data['map'])]
        self.persons = [Person.deserialize(self, pers) for pers in data['persons']]
        self.make_path_graph()
        self.time = data['time']
        self.make_path_graph()
        return self



