from pipeline.blockchain import canonical_json, evidence_hash
from pipeline.verify import verify_record

RECORD = {"face_hash": "a", "matched_url": "https://example.test", "snippet": "original", "source_domain": "example.test", "similarity_score": .3, "timestamp": "2026-01-01T00:00:00Z"}

def test_canonicalization_is_order_independent():
    assert evidence_hash(RECORD) == evidence_hash(dict(reversed(list(RECORD.items()))))
    assert canonical_json(RECORD).startswith('{"face_hash"')

def test_tamper_is_detected():
    digest = evidence_hash(RECORD)
    assert verify_record(RECORD, digest)["status"] == "MATCH"
    assert verify_record(RECORD, digest, simulate_tamper=True)["status"] == "TAMPERED"
