"""Record operator-supplied CentralNJ acceptance observations, offline."""
import argparse
import json
from datetime import datetime, timezone
from sitdown_acceptance_report import acceptance_record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", default="not_run",
                        choices=("not_run", "transport_reachable",
                                 "protocol_connected", "two_way_verified"))
    parser.add_argument("--evidence", default="", help="Operator evidence; never enter credentials")
    args = parser.parse_args(argv)
    try:
        record = acceptance_record(args.result, evidence=args.evidence,
                                   observed_at=datetime.now(timezone.utc))
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
