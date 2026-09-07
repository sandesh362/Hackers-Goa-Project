# Face Blockchain Verify

Face Blockchain Verify is a hackathon proof-of-concept that detects one face in an input image, uses a live Google Lens request through SerpApi to discover related public pages, optionally compares a fetchable candidate face, and timestamps the complete evidence record on Polygon Amoy. It deliberately demonstrates both a successful verification and an altered-record failure.

```text
input photo → exactly-one-face encoding + crop SHA-256
            → live SerpApi / Google Lens results (social domains receive only a boost)
            → candidate embedding distance (advisory)
            → canonical evidence JSON → SHA-256 → Polygon Amoy record
            → recompute digest: MATCH
            → modify saved snippet: TAMPERED
```

## Setup

Use Python 3.11 (the `face_recognition` package uses dlib) and Node 18+.

```bash
python -m venv .venv
# Activate it, then:
pip install -r requirements.txt
npm install
cp .env.example .env
npx hardhat compile
```

## Browser interface

Start the premium local dashboard after configuration:

```bash
uvicorn app:app --reload --port 8000
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). The **Settings** panel writes the required values to this project's local `.env`, masking API and wallet secrets after save. Upload a consented local photo; a public URL is no longer required. The app temporarily uploads the image to SerpApi and Google Lens uses its 10-minute `image_id` to search. Supported uploads are JPG/JPEG, PNG, or WebP up to 500 KB. [SerpApi's Image API documentation](https://serpapi.com/image-api) describes this flow.

Create a [SerpApi](https://serpapi.com/) key and set `SERPAPI_KEY`. Google Lens needs a publicly reachable URL, so set `INPUT_IMAGE_URL` (or pass `--image-url`) for the same image you supply locally. The code makes a genuine SerpApi HTTP request; it never fabricates a hit if search returns no results.

For the live demo, request free Amoy test MATIC from a current Polygon faucet, set `WEB3_RPC_URL` and `PRIVATE_KEY`, then deploy:

```bash
npm run deploy:amoy
# Copy the printed CONTRACT_ADDRESS into .env
python pipeline/main.py --image path/to/your-consented-photo.jpg --image-url "$INPUT_IMAGE_URL"
```

Polygon Amoy is fast, free to use with faucet funds, and EVM-compatible—well suited to a live judge demo. For an offline network fallback, start `npm run node`, deploy with `npx hardhat run scripts/deploy.js --network localhost`, and set `WEB3_RPC_URL=http://127.0.0.1:8545`, its private key, and the resulting contract address.

The full run writes `output/<timestamp>/report_<timestamp>.json`. Verify it, then prove tamper detection:

```bash
python pipeline/verify.py --report output/<timestamp>/report_<timestamp>.json
python pipeline/verify.py --report output/<timestamp>/report_<timestamp>.json --simulate-tamper
./demo.sh
pytest
```

`--simulate-tamper` changes the snippet only in memory and compares its newly computed hash to the untouched on-chain value; it must print `TAMPERED`. No face photo is included in this repository: add a photo you own or have consent to use.

## What this does and doesn't prove

The on-chain SHA-256 proves that the full evidence record—crop hash, search result, similarity value, and timestamp—has not changed since submission. It is tamper evidence, not proof of identity. The face-crop SHA-256 only shows that exact crop bytes were unchanged after capture. The candidate comparison is a dlib `face_recognition` Euclidean embedding distance; `0.6` is the usual starting threshold. It is probabilistic and can produce false positives and negatives, so the UI and report label it advisory rather than an identity verdict.

## Limitations and ethics

Reverse search can miss private or unindexed accounts and return false positives. Candidate pages may not expose a usable image; testnets/RPCs can be flaky. This is a proof-of-concept, not a production identity system. Only use your own photos or images you are authorized to search—facial recognition and personal social content demand explicit care and consent.

## Demo capture placeholder

Add a short GIF or screenshot here showing: detected face → live result → Amoy transaction (link its hash at `https://amoy.polygonscan.com/tx/<tx-hash>`) → `MATCH` → `TAMPERED`.
