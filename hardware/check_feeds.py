"""Check arm-route symmetry and intended layer isolation in the emitted PCB.

This checks conductor geometry, not antenna impedance or RF isolation in dB.
"""
from pathlib import Path
from collections import defaultdict
import heapq
import json
import math
from shapely.geometry import LineString, Point

ROOT = Path(__file__).resolve().parents[1]


def path_length(board, net, start, end):
    tracks = [t for t in board['tracks'] if t[0] == net]
    nodes = set()
    for _, layer, a, b, _ in tracks:
        nodes.update([(layer, *a), (layer, *b)])
    vias = [(x, y) for n, x, y in board['vias'] if n == net]
    for x, y in vias:
        nodes.update([(0, x, y), (1, x, y)])
    graph = defaultdict(list)
    for _, layer, a, b, _ in tracks:
        line = LineString([a, b])
        on = sorted((line.project(Point(n[1:])), n) for n in nodes
                    if n[0] == layer and line.distance(Point(n[1:])) < 1e-7)
        for (da, na), (db, nb) in zip(on, on[1:]):
            graph[na].append((nb, db-da))
            graph[nb].append((na, db-da))
    for x, y in vias:
        a, b = (0, x, y), (1, x, y)
        # Include the through-board distance equally in both Y arms.
        graph[a].append((b, 1.6))
        graph[b].append((a, 1.6))
    queue = [(0., start)]
    best = {start: 0.}
    while queue:
        distance, node = heapq.heappop(queue)
        if distance != best[node]:
            continue
        if node == end:
            return distance
        for other, step in graph[node]:
            candidate = distance + step
            if candidate < best.get(other, math.inf):
                best[other] = candidate
                heapq.heappush(queue, (candidate, other))
    raise AssertionError(f'No arm-to-transformer path: {net}')


def main():
    board = json.loads((ROOT/'vhf/hardware/preamp_layout.json').read_text())
    endpoints = {
        'X_ANT_N': ((0, 5., 48.), (0, 45.46, 34.54)),
        'X_ANT_P': ((0, 91., 48.), (0, 50.54, 34.54)),
        'Y_ANT_N': ((1, 48., 5.), (0, 29.46, 45.46)),
        'Y_ANT_P': ((1, 48., 91.), (0, 29.46, 50.54)),
    }
    lengths = {net: path_length(board, net, *ends)
               for net, ends in endpoints.items()}
    for pol in 'XY':
        assert abs(lengths[pol+'_ANT_N']-lengths[pol+'_ANT_P']) < .01
    assert all(t[1] == 0 for t in board['tracks'] if t[0].startswith('X_ANT_'))
    assert sum(n.startswith('Y_ANT_') for n, _, _ in board['vias']) == 2
    parts = {p['ref']: p for p in board['parts']}
    assert parts['U102']['nets']['8'] == parts['U202']['nets']['8'] == 'V12'
    assert 'L104' in parts and 'L204' not in parts
    assert (parts['J102']['x'], parts['J102']['y']) == (90, 26)
    assert (parts['J202']['x'], parts['J202']['y']) == (90, 66)
    preferred=json.loads((ROOT/'simulation/filter_values.json').read_text())['preferred']
    for base in [100,200]:
        refs=[f'C{base+1}',f'L{base+1}',f'C{base+3}',f'L{base+2}',f'C{base+4}',f'C{base+5}',f'L{base+3}',f'C{base+6}',f'C{base+7}']
        actual=[float(parts[ref]['value'][:-1]) for ref in refs]
        assert actual==preferred,(actual,preferred)
        assert parts[f'C{base+2}']['value']==parts[f'C{base+1}']['value']
    result = {'filter_BOM_matches_simulation': True, 'arm_to_primary_conductor_length_mm': lengths,
              'within_pair_mismatch_limit_mm': .01,
              'measured_RF_isolation_dB': None}
    (ROOT/'vhf/manufacturing/feed_geometry_check.json').write_text(
        json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
