from __future__ import annotations
import argparse, json
from pathlib import Path
try:
    from .blockchain import evidence_hash, fetch_record_hash
except ImportError:  # supports `python pipeline/verify.py`
    from blockchain import evidence_hash, fetch_record_hash

def verify_record(record: dict, on_chain_hash: str, simulate_tamper: bool = False) -> dict:
    candidate = dict(record)
    if simulate_tamper: candidate["snippet"] = "ALTERED AFTER SUBMISSION"
    computed = evidence_hash(candidate)
    return {"status": "MATCH" if computed.lower() == on_chain_hash.lower() else ("TAMPERED" if simulate_tamper else "MISMATCH"), "computed_hash": computed, "on_chain_hash": on_chain_hash}

def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True); parser.add_argument("--simulate-tamper", action="store_true"); args = parser.parse_args()
    report = json.loads(Path(args.report).read_text()); on_chain = fetch_record_hash(int(report["blockchain"]["record_id"]))
    print(json.dumps(verify_record(report["evidence"], on_chain, args.simulate_tamper), indent=2))
if __name__ == "__main__": main()
