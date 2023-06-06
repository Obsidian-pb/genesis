import pytest

import osmnx as ox
# import networkx as nx
# import numpy as np

from genesis.models import Environment


@pytest.fixture()
def load_G():
    return ox.load_graphml("tests/data/test_rng.ml")

def test_environment_creation(load_G):
    E = Environment(load_G)
    assert isinstance(E, Environment)