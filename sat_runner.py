import argparse
import os
import time

from networkx import Graph
from itertools import combinations
from networkx.algorithms.approximation import max_clique
from networkx.algorithms.clique import find_cliques
from pysat.solvers import Glucose3, Glucose4, Lingeling, Cadical, Minisat22, Maplesat

import bounds.upper_bounds as bnd
from lib.htd_validate.htd_validate.utils.hypergraph import Hypergraph
from sat_encoding import HtdSatEncoding

parser = argparse.ArgumentParser(description='Calculate the hypertree decomposition for a given hypergraph')
parser.add_argument('graph', metavar='graph_file', type=str,
                   help='The input file containing the hypergraph')
parser.add_argument('-g', dest='ghtd', action='store_true', default=False,
                    help='Compute a GHTD instead of a HTD')

parser.add_argument('-s', dest="solver", default='0', type=int, help='The solver to use')
parser.add_argument('-b', dest="sb", default=False, action='store_true', help="Activate symmetry breaking")
parser.add_argument('-i', dest="incr", default=False, action="store_true", help="Activate incremental solving")
parser.add_argument('-c', dest="card", default=6, type=int, help="The cardinality encoding to use for non-incremental solving")
parser.add_argument('-q', dest="clique", default=0, type=int, help="The clique mode (0: off, 1: approx, 2: max cliques)")

args = parser.parse_args()

# The solver to use
solvers = [
    lambda: Glucose4(incr=True),
    lambda: Glucose3(incr=True),
    Lingeling,
    Cadical,
    Minisat22,
    Maplesat
]
solver = solvers[args.solver]

input_file = args.graph
hypergraph_in = Hypergraph.from_file(input_file, fischl_format=False)
hypergraph2 = Hypergraph.from_file(input_file, fischl_format=True)

if hypergraph_in is None or (hypergraph2 is not None and len(hypergraph2.edges()) > len(hypergraph_in.edges())):
    hypergraph_in = hypergraph2

current_bound = bnd.greedy(hypergraph_in, False, bb=False)
timeout = 0
before_tm = time.time()

clique_mode = args.clique
cliques = None
if clique_mode > 0:
    pv = Graph()
    for e in hypergraph_in.edges():
        # PRIMAL GRAPH CONSTRUCTION
        for u, v in combinations(hypergraph_in.get_edge(e), 2):
            pv.add_edge(u, v)

    if clique_mode == 1:
        cliques = [max_clique(pv)]
    else:
        cliques = [max(find_cliques(pv), key=lambda x:len(x))]

encoder = HtdSatEncoding(hypergraph_in)
decomp = encoder.solve(current_bound, not args.ghtd, solver, sb=args.sb, incremental=args.incr, enc_type=args.card, clique=cliques)

print(f"Width : {decomp.size}")
print(f"Solved in: {time.time() - before_tm}")
