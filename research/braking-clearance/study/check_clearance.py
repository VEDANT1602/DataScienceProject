"""Independently integrate the braking phases and bracket velocity crossings.

Read-only examination of the previous release. Uses the Python standard library.
Run with --output to save the audit, otherwise print it. No source imports.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
TOL = 1e-9  # numerical agreement threshold in metres, well below either study threshold


@dataclass(frozen=True)
class Segment:
    start: float
    duration: float
    x: float
    v: float
    a: float
    jerk: float

    def state(self, elapsed):
        travel = elapsed * (self.v + elapsed * (self.a / 2 + self.jerk * elapsed / 6))
        speed = self.v + elapsed * (self.a + self.jerk * elapsed / 2)
        return self.x + travel, speed, self.a + self.jerk * elapsed


class Trajectory:
    def __init__(self, speed, cap, onset, delay=0.0):
        if not all(map(math.isfinite, (speed, cap, onset, delay))):
            raise ValueError("Finite inputs required")
        if speed < 0 or cap <= 0 or onset <= 0 or delay < 0:
            raise ValueError("Speed and delay must be nonnegative; cap and onset must be positive")
        self.parts = []
        self.times = [0.0]
        x, v = 0.0, speed
        ramp = min(cap / onset, math.sqrt(2 * speed / onset))
        tail = max(0.0, speed - onset * ramp**2 / 2) / cap
        for duration, accel, jerk in ((delay, 0.0, 0.0), (ramp, 0.0, -onset), (tail, -cap, 0.0)):
            if duration > 0 and v > 0:
                segment = Segment(self.times[-1], duration, x, v, accel, jerk)
                self.parts.append(segment)
                self.times.append(segment.start + duration)
                x, v, _ = segment.state(duration)
        self.distance = x

    def at(self, t):
        for segment in self.parts:
            if t < segment.start + segment.duration:
                return segment.state(t - segment.start)
        return self.distance, 0.0, 0.0


def max_closure(follower, leader):
    def difference(t, component):
        return follower.at(t)[component] - leader.at(t)[component]

    boundaries = sorted(set(follower.times + leader.times))
    monotone = set(boundaries)
    for left, right in zip(boundaries, boundaries[1:]):
        p = left + (right - left) / 3
        q = right - (right - left) / 3
        ap, aq = difference(p, 2), difference(q, 2)
        if ap != aq:
            zero_accel = p - ap * (q - p) / (aq - ap)
            if left < zero_accel < right:
                monotone.add(zero_accel)
    # On each resulting interval the relative velocity is monotone. Include
    # all endpoints, so tangential zeroes and constant-velocity ties are safe.
    points = sorted(monotone)
    candidates = points.copy()
    for left, right in zip(points, points[1:]):
        low_speed, high_speed = difference(left, 1), difference(right, 1)
        if low_speed * high_speed >= 0:
            continue
        for _ in range(53):
            middle = (left + right) / 2
            if (difference(middle, 1) > 0) == (low_speed > 0):
                left = middle
            else:
                right = middle
        candidates.append((left + right) / 2)
    return max(difference(t, 0) for t in candidates)


def read_csv(archive, name):
    with archive.open(f'results/{name}.csv') as raw:
        return list(csv.DictReader(io.TextIOWrapper(raw, encoding='utf-8', newline='')))


def record_order(grid):
    groups = {}
    worst_error = 0.0
    for row in grid:
        vf, vl, bf, bl, jf, jl, delay = (float(row[k]) for k in (
            'follower_speed_mps', 'leader_speed_mps', 'follower_decel_mps2', 'leader_decel_mps2',
            'follower_jerk_mps3', 'leader_jerk_mps3', 'follower_delay_s'))
        follower = Trajectory(vf, bf, jf, delay)
        leader = Trajectory(vl, bl, jl)
        peak = max_closure(follower, leader)
        endpoint = max(0.0, follower.distance - leader.distance)
        shortfall = max(0.0, peak - endpoint)
        worst_error = max(worst_error, abs(peak - float(row['full_gap_m'])),
                          abs(endpoint - float(row['endpoint_gap_m'])))
        key = ('F<=L' if bf <= bl else 'F>L', 'F<=L' if jf <= jl else 'F>L')
        groups.setdefault(key, []).append((shortfall, int(row['case'])))
    assert worst_error < TOL
    out = []
    for (cap, jerk), pairs in sorted(groups.items()):
        values = [x for x, _ in pairs]
        out.append(dict(cap_order=cap, onset_order=jerk, cases=len(values),
                        above_1mm=sum(x > .001 for x in values), above_1m=sum(x > 1 for x in values),
                        maximum_m=max(values), maximum_case=max(pairs)[1]))
    assert len(grid) == 2916 and sum(r['above_1m'] for r in out) == 236
    assert max(x for x, _ in groups['F<=L', 'F<=L']) < TOL
    return dict(groups=out, maximum_disagreement_m=worst_error,
                instant_above_1m=sum(float(r['instant_shortfall_m']) > 1 for r in grid),
                instant_excess_above_1m=sum(float(r['instant_excess_m']) > 1 for r in grid))


def check_uncertainty(rows):
    groups = {}
    worst_error = 0.0
    for row in rows:
        vf, vl = float(row['vf']), float(row['vl'])
        def pair(suffix):
            return (Trajectory(vf, float(row['bf_'+suffix]), float(row['jf_'+suffix]), float(row['tau_'+suffix])),
                    Trajectory(vl, float(row['bl_'+suffix]), float(row['jl_'+suffix])))
        measured = max_closure(*pair('actual'))
        nominal = max_closure(*pair('nom'))
        bounded = max_closure(Trajectory(vf, .8*float(row['bf_nom']), .8*float(row['jf_nom']), float(row['tau_nom'])+.15),
                              Trajectory(vl, 1.2*float(row['bl_nom']), 1.2*float(row['jl_nom'])))
        for result, field in ((measured, 'actual_gap_m'), (nominal, 'nominal_gap_m'), (bounded, 'bounded_gap_m')):
            worst_error = max(worst_error, abs(result-float(row[field])))
        flags = (measured > nominal+1, measured > bounded+1)
        assert flags == tuple(row[k] == 'True' for k in ('nominal_shortfall_after_1m_margin','bounded_shortfall_after_1m_margin'))
        if row['regime'] == 'inside_declared_bounds':
            assert measured <= bounded + TOL
        groups.setdefault(row['regime'], []).append((*flags, bounded-nominal))
    assert len(rows)==10000 and worst_error < TOL
    return dict(regimes={k: dict(cases=len(v), nominal_failures=sum(row[0] for row in v),
                                 corner_failures=sum(row[1] for row in v), average_increment_m=mean(row[2] for row in v))
                         for k,v in groups.items()}, maximum_disagreement_m=worst_error)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    hashes = json.loads((HERE/'source-hashes.json').read_text())['files']
    for filename in ('study.py', 'requirements.txt'):
        local = HERE / ('original-requirements.txt' if filename == 'requirements.txt' else filename)
        assert hashlib.sha256(local.read_bytes()).hexdigest() == hashes[filename]
    with ZipFile(HERE/'archived-results.zip') as archive:
        assert set(archive.namelist()) == {name for name in hashes if name.startswith('results/')}
        for filename in archive.namelist():
            assert hashlib.sha256(archive.read(filename)).hexdigest() == hashes[filename]
        report = {'factorial':record_order(read_csv(archive,'factorial')),
                  'uncertainty':check_uncertainty(read_csv(archive,'uncertainty'))}
    result = json.dumps(report, indent=2)+'\n'
    if args.output: args.output.write_text(result)
    else: print(result, end='')


if __name__ == '__main__':
    main()
