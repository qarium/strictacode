from collections import defaultdict


class DiGraph:
    def __init__(self):
        self._edges = defaultdict(set)
        self._nodes = set()

    @property
    def nodes(self):
        return self._nodes

    @property
    def edges(self):
        return self._edges

    def add_node(self, n):
        self._nodes.add(n)

    def add_edge(self, a, b):
        self._nodes.add(a)
        self._nodes.add(b)
        self._edges[a].add(b)

    def neighbors(self, n):
        return self._edges.get(n, set())

    def reverse(self):
        graph = DiGraph()

        for n in self._nodes:
            graph.add_node(n)

        for a in self._edges:
            for b in self._edges[a]:
                graph.add_edge(b, a)

        return graph

    def number_of_nodes(self):
        return len(self._nodes)

    def number_of_edges(self):
        return sum(len(v) for v in self._edges.values())
