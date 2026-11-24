"""FHWA NGSIM I-80 paired approach check. Python 3.10+ standard library."""
import argparse
import csv
import hashlib
import json
from collections import defaultdict, deque
from tempfile import NamedTemporaryFile
from concurrent.futures import ThreadPoolExecutor
from itertools import groupby
from pathlib import Path
from statistics import median
from urllib.parse import urlencode
from urllib.request import urlopen

SOURCE = "https://data.transportation.gov/resource/8ect-6jqj.csv"
FIELDS = "global_time,frame_id,vehicle_id,local_y,v_length,v_class,v_vel,lane_id,preceding,following"
START = 1113433135000  # time assigned to frame 1 of the first I-80 recording
FT = 0.3048
PARTS = 30
HERE = Path(__file__).resolve().parent


def query(i):
    lo = START + i * 30000
    params = {"$select": FIELDS, "$where": f"location='i-80' AND global_time >= {lo} AND global_time < {lo+30000}",
              "$order": "global_time,vehicle_id", "$limit": 300000}
    return SOURCE + "?" + urlencode(params)


def load_parts(cache, manifest):
    cache.mkdir(parents=True, exist_ok=True)
    def load(i):
        path = cache / f"{i:02}.csv"
        if path.exists():
            data = path.read_bytes()
        else:
            with urlopen(query(i), timeout=120) as response:
                data = response.read()
        digest = hashlib.sha256(data).hexdigest()
        if manifest[path.name] != digest:
            raise ValueError(f"Source bytes differ for {path.name}; see input-hashes.json.")
        if not path.exists():
            with NamedTemporaryFile(dir=cache, delete=False) as staging:
                staging.write(data)
            Path(staging.name).replace(path)
        return path
    with ThreadPoolExecutor(4) as pool:
        return list(pool.map(load, range(PARTS)))


def closure(gaps):
    """Difference of nonnegative full-window and endpoint closing displacements."""
    peak = gaps[0] - min(gaps)
    endpoint = max(0.0, gaps[0] - gaps[-1])
    return peak - endpoint


def analyse(paths):
    counts = defaultdict(int)
    histories = {}
    eligible = {}
    prev_time = None
    for i, path in enumerate(paths):
        with path.open(newline="") as stream:
            reader = csv.DictReader(stream)
            assert reader.fieldnames == FIELDS.split(",")
            n = 0
            for raw_time, raw_observations in groupby(reader, key=lambda row: int(row["global_time"])):
                assert START + i*30000 <= raw_time < START + (i+1)*30000
                assert prev_time is None or raw_time > prev_time
                prev_time = raw_time
                by_id = {}
                conflicts = set()
                for row in raw_observations:
                    n += 1
                    assert (int(row["frame_id"]) - 1)*100 == raw_time - START
                    v_id = int(row["vehicle_id"])
                    if v_id in by_id:
                        counts["duplicate_rows"] += 1
                        if by_id[v_id] != row:
                            conflicts.add(v_id)
                    by_id[v_id] = row
                counts["conflicting_id_frames"] += len(conflicts)
                for v_id in conflicts:
                    del by_id[v_id]
                for follower, f in by_id.items():
                    if follower in eligible or f["v_class"] != "2":
                        continue
                    lead = int(f["preceding"])
                    l = by_id.get(lead)
                    if not l or l["v_class"] != "2" or int(l["following"]) != follower or l["lane_id"] != f["lane_id"]:
                        continue
                    gap = FT * (float(l["local_y"]) - float(l["v_length"]) - float(f["local_y"]))
                    if gap <= 0.0:
                        continue
                    key = (lead, f["lane_id"])
                    if follower not in histories or histories[follower][:2] != (raw_time-100, key):
                        samples = deque(maxlen=61)
                    else:
                        samples = histories[follower][2]
                    fv, lv = FT*float(f["v_vel"]), FT*float(l["v_vel"])
                    samples.append((gap, fv, lv))
                    histories[follower] = raw_time, key, samples
                    if len(samples) != 61 or min(samples[0][1:]) < 1.0:
                        continue
                    window = list(samples)
                    if max(max(s[1:]) for s in window[-11:]) > 0.5:
                        continue
                    gaps = [s[0] for s in window]
                    smooth = [median(gaps[max(0,t-2):min(len(gaps),t+3)]) for t in range(len(gaps))]
                    eligible[follower] = (closure(gaps), closure(smooth), closure(gaps[:51]))
            assert 0 < n < 300000
            counts["source_rows"] += n
    panel = list(eligible.values())
    stats = {}
    for j, label in enumerate(("sampled", "five_sample_median", "near_stop_onset")):
        v = [x[j] for x in panel]
        stats[label] = {"over_1m": sum(d > 1 for d in v), "max_m": round(max(v),6),
                        "median_m": round(median(v),6), "over_0.1m": sum(d > .1 for d in v)}
    return {"frames_in_query": 9000, **dict(counts), "eligible_followers": len(panel), **stats}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    args = parser.parse_args()
    manifest_path = HERE / "input-hashes.json"
    manifest = json.loads(manifest_path.read_text())
    paths = load_parts(args.cache, manifest)
    report = analyse(paths)
    print(json.dumps(report, indent=2))
    expected = HERE / "observed-summary.json"
    if report != json.loads(expected.read_text()):
        raise ValueError("Results disagree with the distributed summary.")


if __name__ == "__main__":
    main()
