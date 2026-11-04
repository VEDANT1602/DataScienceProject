from argparse import ArgumentParser
import json
import os
from pathlib import Path


def main() -> None:
    # Limit this CLI process before importing NumPy/scikit-learn. Large detected
    # core counts can make this small CPU experiment slower through thread
    # oversubscription. Explicit caller choices take precedence; host settings
    # are never changed.
    for name in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS"):
        os.environ.setdefault(name,"1")
    parser = ArgumentParser(description="Reproduce an event-time risk experiment with synthetic data")
    sub = parser.add_subparsers(dest="command",required=True)
    demo = sub.add_parser("demo",help="generate data, replay events, evaluate models and write the report")
    demo.add_argument("--out",type=Path,default=Path("artifacts"))
    demo.add_argument("--events",type=int,default=12_000)
    demo.add_argument("--seed",type=int,default=19)
    demo.add_argument("--bootstrap-draws",type=int,default=200)
    report = sub.add_parser("report",help="regenerate narrative and charts from measured metrics.json")
    report.add_argument("--out",type=Path,default=Path("artifacts"))
    unpack = sub.add_parser("unpack-data",help="decompress the committed original synthetic dataset")
    unpack.add_argument("--out",type=Path,default=Path("data/unpacked-transactions.csv"))
    args = parser.parse_args()
    if args.command == "unpack-data":
        import gzip
        source = Path(__file__).resolve().parent.parent/"data"/"transactions.csv.gz"
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_bytes(gzip.decompress(source.read_bytes()))
        print(args.out.resolve())
        return
    from .report import render
    if args.command == "demo":
        from .experiment import run
        result = run(args.out,args.events,args.seed,args.bootstrap_draws)
    else:
        result = json.loads((args.out/"metrics.json").read_text(encoding="utf-8"))
    render(result,args.out)
    print(json.dumps({"artifacts":str(args.out.resolve()),"test":result["test"]},indent=2))


if __name__ == "__main__":
    main()
