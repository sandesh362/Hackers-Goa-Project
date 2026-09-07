#!/usr/bin/env bash
set -euo pipefail
python pipeline/main.py --image "${FACE_IMAGE:?Set FACE_IMAGE to a consented local photo}" --image-url "${INPUT_IMAGE_URL:?Set INPUT_IMAGE_URL to a public image URL}"
REPORT=$(find output -name 'report_*.json' -print | sort | tail -n 1)
python pipeline/verify.py --report "$REPORT"
python pipeline/verify.py --report "$REPORT" --simulate-tamper
