from strictacode.graph import DiGraph


class TestDiGraphInit:
    def test_empty_graph(self):
        g = DiGraph()
        assert g.number_of_nodes() == 0
        assert g.number_of_edges() == 0
        assert len(g.nodes) == 0


class TestAddNode:
    def test_add_single_node(self):
        g = DiGraph()
        g.add_node("A")
        assert "A" in g.nodes
        assert g.number_of_nodes() == 1

    def test_add_duplicate_node(self):
        g = DiGraph()
        g.add_node("A")
        g.add_node("A")
        assert g.number_of_nodes() == 1


class TestAddEdge:
    def test_add_edge_adds_both_nodes(self):
        g = DiGraph()
        g.add_edge("A", "B")
        assert g.number_of_nodes() == 2
        assert "A" in g.nodes
        assert "B" in g.nodes

    def test_add_edge_creates_neighbor(self):
        g = DiGraph()
        g.add_edge("A", "B")
        assert "B" in g.neighbors("A")
        assert "A" not in g.neighbors("B")

    def test_add_duplicate_edge(self):
        g = DiGraph()
        g.add_edge("A", "B")
        g.add_edge("A", "B")
        assert g.number_of_edges() == 1

    def test_number_of_edges(self):
        g = DiGraph()
        g.add_edge("A", "B")
        g.add_edge("A", "C")
        assert g.number_of_edges() == 2


class TestSelfLoop:
    def test_self_loop(self):
        g = DiGraph()
        g.add_edge("A", "A")
        assert g.number_of_nodes() == 1
        assert g.number_of_edges() == 1
        assert "A" in g.neighbors("A")


class TestNeighbors:
    def test_node_with_edges(self, simple_graph):
        neighbors = simple_graph.neighbors("A")
        assert neighbors == {"B", "C"}

    def test_leaf_node_no_outgoing(self, simple_graph):
        neighbors = simple_graph.neighbors("B")
        assert neighbors == set()

    def test_nonexistent_node(self, simple_graph):
        # Текущее поведение: возвращает пустой set для несуществующего узла.
        # Если изменить на KeyError, этот тест нужно обновить.
        neighbors = simple_graph.neighbors("Z")
        assert neighbors == set()


class TestReverse:
    def test_reverse_creates_new_graph(self, simple_graph):
        original_nodes = simple_graph.number_of_nodes()
        original_edges = simple_graph.number_of_edges()
        rev = simple_graph.reverse()
        assert rev is not simple_graph
        assert rev.number_of_nodes() == original_nodes
        assert rev.number_of_edges() == original_edges
        assert simple_graph.number_of_nodes() == original_nodes
        assert simple_graph.number_of_edges() == original_edges

    def test_reverse_flips_direction(self, simple_graph):
        rev = simple_graph.reverse()
        assert rev.number_of_edges() == 2
        assert "A" in rev.neighbors("B")
        assert "A" in rev.neighbors("C")
        assert rev.neighbors("A") == set()

    def test_reverse_linear_chain(self):
        g = DiGraph()
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        rev = g.reverse()
        assert "B" in rev.neighbors("C")
        assert "A" in rev.neighbors("B")
        assert rev.neighbors("A") == set()
