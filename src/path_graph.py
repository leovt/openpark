TYPE_FLAT = 0
TYPE_UP_X = 1
TYPE_UP_Y = 2
TYPE_DN_X = 3
TYPE_DN_Y = 4
TYPE_POI_XU = 5
TYPE_POI_YU = 6
TYPE_POI_XD = 7
TYPE_POI_YD = 8

MASK_XU = 1
MASK_YU = 2
MASK_XD = 4
MASK_YD = 8

OPP_MASK = {MASK_XU: MASK_XD, MASK_XD: MASK_XU,
            MASK_YU: MASK_YD, MASK_YD: MASK_YU}

from collections import defaultdict

class PathElement:
    def __init__(self, pos, ptype):
        self.pos = pos
        self.ptype = ptype
        self.neighbours = []
        self.connection_bitfield = 0

    def __repr__(self):
        return str(self.pos)

    def attachment_points(self):
        x, y, z = self.pos

        # attach is a list of attachment points (grid edges) of the new path element
        if self.ptype == TYPE_FLAT:
            return [(('V', x, y, z), MASK_XD), (('V', x + 1, y, z), MASK_XU), (('H', x, y, z), MASK_YD), (('H', x, y + 1, z), MASK_YU)]
        elif self.ptype == TYPE_UP_X:
            return [(('V', x, y, z), MASK_XD), (('V', x + 1, y, z + 1), MASK_XU)]
        elif self.ptype == TYPE_UP_Y:
            return [(('H', x, y, z), MASK_YD), (('H', x, y + 1, z + 1), MASK_YU)]
        elif self.ptype == TYPE_DN_X:
            return [(('V', x, y, z + 1), MASK_XD), (('V', x + 1, y, z), MASK_XU)]
        elif self.ptype == TYPE_DN_Y:
            return [(('H', x, y, z + 1), MASK_YD), (('H', x, y + 1, z), MASK_YU)]
        elif self.ptype == TYPE_POI_XD:
            return [(('V', x, y, z), MASK_XD)]
        elif self.ptype == TYPE_POI_XU:
            return [(('V', x + 1, y, z), MASK_XU)]
        elif self.ptype == TYPE_POI_YD:
            return [(('H', x, y, z), MASK_YD)]
        elif self.ptype == TYPE_POI_YU:
            return [(('H', x, y + 1, z), MASK_YU)]
        else:
            assert False, 'illegal ptype %r' % self.ptype

class PathGraph:
    def __init__(self):
        self.path = {}
        self.edges = defaultdict(list)
        self.distance_to_poi = {}

    def add_path_element(self, pos, ptype, poi_ref=None):
        element = PathElement(pos, ptype)
        assert pos not in self.path
        self.path[pos] = element

        for attpt, mask in element.attachment_points():
            nbs = self.edges[attpt]
            if nbs:
                assert len(nbs) == 1, 'double edge'
                nb = nbs[0]
                element.neighbours.append(nb)
                element.connection_bitfield |= mask
                nb.neighbours.append(element)
                nb.connection_bitfield |= OPP_MASK[mask]
            nbs.append(element)

        for poi, distances in self.distance_to_poi.items():
            if poi == poi_ref:
                continue
            connected_neighbours = [nb for nb in element.neighbours if nb in distances]
            if not connected_neighbours:
                continue
            current_dist = 1 + min(distances[nb] for nb in connected_neighbours)
            current_nodes = [element]
            while current_nodes:
                next_nodes = []
                for n in current_nodes:
                    distances[n] = current_dist
                    next_nodes.extend(nb for nb in n.neighbours if nb in distances and distances[nb] > current_dist + 1)
                current_nodes = next_nodes
                current_dist += 1

        if ptype in (TYPE_POI_XU, TYPE_POI_YU, TYPE_POI_XD, TYPE_POI_YD):
            distances = {}
            current_dist = 0
            current_nodes = [element]
            while current_nodes:
                next_nodes = []
                for n in current_nodes:
                    distances[n] = current_dist
                    next_nodes.extend(nb for nb in n.neighbours if nb not in distances)
                current_nodes = next_nodes
                current_dist += 1

            self.distance_to_poi[poi_ref] = distances

    def remove_path_element(self, pos):
        element = self.path.pop(pos)

        for attpt, mask in element.attachment_points():
            nbs = self.edges[attpt]
            nbs.remove(element)
            if nbs:
                assert len(nbs) == 1, 'double edge'
                nb = nbs[0]
                nb.neighbours.remove(element)
                nb.connection_bitfield &= ~OPP_MASK[mask]
            else:
                del self.edges[attpt]

        for distances in self.distance_to_poi.values():
            if element in distances:
                current_nodes = [element]
                boundary = defaultdict(list)

                while current_nodes:
                    next_nodes = []
                    for n in current_nodes:
                        old_dist = distances[n]
                        del distances[n]
                        for nb in n.neighbours:
                            if nb in distances:
                                if distances[nb] > old_dist:
                                    next_nodes.append(nb)
                                elif n is not element:
                                    new_dist = 1 + distances[nb]
                                    boundary[new_dist].append(n)
                    current_nodes = next_nodes
                # now all invalidated distances have been removed from the distances dictionary
                # boundary contains all the nodes with a correct distance

                # starting at the boundary nodes with the lowest distance do a bfs to recalculate
                # the invalidated distances
                current_dist = min(boundary)
                current_nodes = boundary[current_dist]
                while current_nodes:
                    next_nodes = []
                    for n in current_nodes:
                        distances[n] = current_dist
                        next_nodes.extend(nb for nb in n.neighbours if nb not in distances)
                    current_nodes = next_nodes
                    current_dist += 1
                    current_nodes.extend(boundary[current_dist])
            assert element not in distances

    def get_distance_to_poi(self, poi_ref, pos):
        return self.distance_to_poi[poi_ref].get(self.path[pos], None)

def test():

    def assert_eq(a, b):
        assert a == b, '%s != %s' % (a, b)

    graph = PathGraph()

    # u-shape
    graph.add_path_element((0, 0, 0), TYPE_POI_XU, 'B')
    graph.add_path_element((1, 0, 0), TYPE_FLAT)
    graph.add_path_element((2, 0, 0), TYPE_FLAT)
    graph.add_path_element((3, 0, 0), TYPE_FLAT)
    graph.add_path_element((4, 0, 0), TYPE_FLAT)
    graph.add_path_element((4, 1, 0), TYPE_FLAT)
    graph.add_path_element((4, 2, 0), TYPE_FLAT)
    graph.add_path_element((4, 3, 0), TYPE_FLAT)
    graph.add_path_element((3, 3, 0), TYPE_FLAT)
    graph.add_path_element((2, 3, 0), TYPE_FLAT)
    graph.add_path_element((1, 3, 0), TYPE_FLAT)

    # path now looks like
    #  ---+
    #     |
    #     |
    # B---+

    assert_eq(graph.get_distance_to_poi('B', (1, 3, 0)), 10)

    graph.add_path_element((0, 3, 0), TYPE_POI_XU, 'A')

    # path now looks like
    # A---+
    #     |
    #     |
    # B---+

    assert_eq(graph.get_distance_to_poi('A', (1, 3, 0)), 1)
    assert_eq(graph.get_distance_to_poi('A', (0, 0, 0)), 11)

    graph.add_path_element((2, 1, 0), TYPE_FLAT)
    graph.add_path_element((2, 2, 0), TYPE_FLAT)

    # path now looks like
    # A-+-+
    #   | |
    #   | |
    # B-+-+

    assert_eq(graph.get_distance_to_poi('B', (1, 3, 0)), 6)
    assert_eq(graph.get_distance_to_poi('B', (3, 3, 0)), 6)

    graph.remove_path_element((2, 1, 0))

    # path now looks like
    # A-+-+
    #   | |
    #     |
    # B---+

    assert_eq(graph.get_distance_to_poi('A', (1, 3, 0)), 1)
    assert_eq(graph.get_distance_to_poi('A', (0, 0, 0)), 11)
    assert_eq(graph.get_distance_to_poi('B', (1, 3, 0)), 10)


if __name__ == '__main__':
    test()



