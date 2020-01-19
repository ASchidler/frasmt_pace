from sys import maxsize

import bounds.upper_bounds as ub


def greedy(instance, bb=True, cfirst=True):
    # Build primal graph
    vertex_rank = {}

    for v in instance.hg.nodes():
        cnt = 0
        for e in instance.c_edges:
            ed = instance.hg.get_edge(e)
            if v in ed:
                cnt += 1
        vertex_rank[v] = cnt

    ordering = ub.compute_ordering(instance, criteria=lambda i, g: min((len(g[x]), sum(vertex_rank[n] for n in g[x]), x)
                                                                       for x in g.nodes)[2])
    bags, tree, root = ub.ordering_to_decomp(instance, ordering)
    ub.improve_scramble(instance, ordering, bound=max(len(b)-2 for b in bags.values()))

    # In case of HTD we require to not violate the special condition
    ub.simplify_decomp(bags, tree)
    edge_cover = cover_ghtd(instance, bags)

    c = max(sum(v for e, v in entries.items() if v > 0 and e in instance.c_edges) for entries in edge_cover.values())
    if bb:
        ub.bandb(instance, bags, edge_cover, subcall=lambda b, edges, cub: bandb_sub(instance, b, edges, cub, c, cfirst))
        c = max(
            sum(v for e, v in entries.items() if v > 0 and e in instance.c_edges) for entries in edge_cover.values())

    width = max(sum(v.values()) for v in edge_cover.values())
    return width, c, (tree, bags, edge_cover)


def cover_ghtd(instance, bags):
    edge_cover = {n: {e: 0 for e in instance.hg.edges().keys()} for n in instance.hg.nodes()}

    # Establish a rank for each vertex, i.e. in how many hyperedges it occurs
    vertex_rank = {}

    for v in instance.hg.nodes():
        cnt = 0
        for e, ed in instance.hg.edges().items():
            if v in ed:
                cnt += 1
        vertex_rank[v] = cnt

    # Cover bags
    for k, v in bags.items():
        remaining = set(v)

        # cover bag, minimize cost per covered vertex
        while len(remaining) > 0:
            c_best = (0, None, None, maxsize)

            for e, ed in instance.hg.edges().items():
                intersect_vertices = set(ed) & remaining
                intersect = len(intersect_vertices)

                if intersect > 0:
                    rank = sum(vertex_rank[v] for v in intersect_vertices)
                    if c_best[0] == 0 or \
                        (e not in instance.c_edges and (c_best[1] in instance.c_edges or intersect > c_best[0])) or \
                        (e in instance.c_edges and c_best[1] in instance.c_edges and intersect > c_best[0]) or \
                        (intersect == c_best[0] and rank < c_best[3] and (c_best[1] in instance.c_edges) == e in instance.c_edges):

                        c_best = (intersect, e, intersect_vertices, rank)

            _, e, ed, _ = c_best
            remaining -= ed
            edge_cover[k][e] = 1

    return edge_cover


def bandb_sub(instance, b, edges, ub_w, ub_c, cfirst=True):
    """Recursive function that computes the cover. Use pos=-1 and value False for call. Returns maxsize of no better
    solution could be found."""

    q = [(b, 0, 0, -1, False, [])]

    best_c = ub_c
    best_w = ub_w
    best_list = None

    while q:
        b, c_w, c_c, pos, val, e_list = q.pop()

        # Reached the end, but did not fill the bag, ignore solution
        if pos == len(edges):
            continue

        # If we should add the edge, add costs and remove from bag
        if val:
            e, ed = edges[pos]

            # Hyperedge does not contribute anything, adding it cannot be optimal
            if len(ed & b) == 0:
                continue

            c_w = c_w + 1
            if e in instance.c_edges:
                c_c = c_c + 1

            # Exceed upper bound -> suboptimal
            if (cfirst and (c_c > best_c or (c_c == best_c and c_w >= best_w))) or \
                    (not cfirst and (c_w > best_w or (c_w == best_w and c_c >= best_c))):
                continue

            b = b - ed
            # Copy list and add edge
            e_list = list(e_list)
            e_list.append(e)

            # Found a solution, store (we already know it's better than best from above)
            if len(b) == 0:
                best_w = c_w
                best_c = c_c
                best_list = e_list

        # "Subcalls"
        q.append((b, c_w, c_c, pos + 1, False, e_list))
        q.append((b, c_w, c_c, pos + 1, True, e_list))

    # Return result if better has been found, otherwise return default value
    if best_w < ub_w or best_c < ub_c:
        return best_w, best_list

    return maxsize, None