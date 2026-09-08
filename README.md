# The Acers — Face Blockchain Verify

The Acers is a local visual-discovery and tamper-evidence proof of concept for consented images. Upload an authorized photo, optionally select one person when multiple people are detected, perform a live Google Lens visual search through SerpApi, optionally compare candidate faces using face embeddings, and anchor the evidence record to a blockchain.

> **Important:** This project is a proof of concept for consented images and publicly indexed results. It does not prove identity, search private accounts, or guarantee that a matching image exists online.

## Features

* Premium local browser dashboard
* Full uploaded-image preview
* Manual person selection when multiple faces are detected
* Face-focused crop for visual search
* Live Google Lens search through SerpApi
* Results grouped into:

  * **Most Similar**
  * **Relevant**
  * **Similar**
* Advisory face-embedding comparison
* SHA-256 evidence hashing
* Local Hardhat blockchain support
* Polygon Amoy testnet support
* On-chain evidence verification
* `MATCH` verification
* `TAMPERED` demonstration
* Saved JSON evidence reports
* Offline pytest test suite

## Core Pipeline

```text
Consent-based input image
        ↓
Face detection
        ↓
Select person (if multiple faces)
        ↓
Face-focused crop
        ↓
Crop SHA-256
        ↓
SerpApi / Google Lens
        ↓
Most Similar / Relevant / Similar
        ↓
Optional face-embedding comparison
        ↓
Canonical evidence record
        ↓
SHA-256 evidence digest
        ↓
Blockchain storage
        ↓
Recompute digest
        ↓
MATCH / TAMPERED
```

## Requirements

* Python 3.11+
* Node.js 18+
* npm
* A SerpApi account and API key
* Internet connection for live Google Lens search

The project uses `face_recognition` and `dlib`; Python 3.11 is recommended.

## Installation

Open PowerShell in the project folder:

```powershell
cd D:\AD\MLBC

python -m venv .venv
.venv\Scripts\Activate.ps1

pip install -r requirements.txt

npm install

Copy-Item .env.example .env

npx hardhat compile
```

## SerpApi Setup

Create a SerpApi account:

[https://serpapi.com/users/sign_up](https://serpapi.com/users/sign_up)

Copy your API key and configure:

```env
SERPAPI_KEY=YOUR_SERPAPI_KEY
```

The dashboard **Settings** panel can also save the configuration to the local `.env` file.

The application uses a genuine SerpApi request and does not fabricate results when no visual match is returned.

## Image Upload Limit

The browser dashboard currently supports:

* JPG / JPEG
* PNG
* WEBP

Maximum upload size:

```text
500 KB
```

Images larger than 500 KB must be compressed or resized before upload.

## Start the Dashboard

```powershell
cd D:\AD\MLBC
.venv\Scripts\Activate.ps1

uvicorn app:app --reload --port 8000
```

Open:

[http://127.0.0.1:8000](http://127.0.0.1:8000)

## Dashboard Settings

Configure the required values in **Settings**.

### Local Hardhat

```text
SERPAPI_KEY
YOUR_SERPAPI_KEY

NETWORK
local

WEB3_RPC_URL
http://127.0.0.1:8545

PRIVATE_KEY
Temporary Hardhat private key

CONTRACT_ADDRESS
Deployed contract address

MAX_WEB_RESULTS
10
```

### Polygon Amoy

```text
SERPAPI_KEY
YOUR_SERPAPI_KEY

NETWORK
amoy

WEB3_RPC_URL
YOUR_POLYGON_AMOY_RPC_URL

PRIVATE_KEY
TEST_WALLET_PRIVATE_KEY

CONTRACT_ADDRESS
DEPLOYED_AMOY_CONTRACT_ADDRESS

MAX_WEB_RESULTS
10
```

Secrets are stored locally in `.env` and masked in the dashboard.

> Never commit `.env` or expose a real wallet private key.

## Local Hardhat Blockchain

Start the local blockchain:

```powershell
cd D:\AD\MLBC
npx hardhat node
```

Keep this terminal open.

Deploy the contract from a second terminal:

```powershell
cd D:\AD\MLBC
npx hardhat run scripts/deploy.js --network localhost
```

Copy the contract address printed by the deployment script into your settings.

A fresh Hardhat node commonly uses:

```text
0x5FbDB2315678afecb367f032d93F642f64180aa3
```

Always use the address actually printed by your deployment script.

> Restarting `npx hardhat node` resets the local blockchain state. Deploy the contract again after restarting.

## Polygon Amoy

For a public blockchain demonstration:

1. Use a dedicated test wallet.
2. Obtain test MATIC from a current Polygon Amoy faucet.
3. Configure an Amoy RPC endpoint.
4. Deploy the contract.
5. Copy the deployed contract address into `.env`.

Deploy:

```powershell
npm run deploy:amoy
```

Then run the pipeline using the configured Amoy network.

> Use testnet credentials only. Never use a production wallet private key.

## Run a Search

1. Open `http://127.0.0.1:8000`
2. Open **Settings** and verify the configuration.
3. Upload a consented image.
4. Make sure it is **500 KB or smaller**.
5. If multiple people are detected, select the intended person.
6. Click **Find top matches**.
7. Review:

   * **Most Similar**
   * **Relevant**
   * **Similar**
8. Scroll to the blockchain verification section.
9. Verify the evidence status.

## Face Embedding Comparison

When a usable candidate face is available, the application can calculate an advisory face-embedding distance using `face_recognition` / dlib.

A distance around `0.6` is commonly used as a starting reference, but it is not a universal identity threshold.

Face similarity is probabilistic and can produce false positives and false negatives. The application therefore treats this result as **advisory**, not as proof of identity.

## Evidence Record

Each completed search creates a canonical evidence record containing information such as:

```text
Face/image crop hash
Matched URL
Source domain
Search snippet
Similarity value, when available
Timestamp
```

The evidence record is converted into a canonical representation and hashed with SHA-256.

```text
Evidence Record
      ↓
Canonical Representation
      ↓
SHA-256
      ↓
Evidence Digest
```

## Blockchain Verification

When blockchain settings are configured, the application:

1. Creates the evidence record.
2. Calculates its SHA-256 digest.
3. Stores the digest in `FaceVerification.sol`.
4. Records the blockchain transaction.
5. Reads the stored value back.
6. Recomputes the local digest.
7. Compares both values.

A matching digest produces:

```text
MATCH
```

The dashboard can display:

```text
Verification Status
Contract Address
Transaction Hash
Block Number
Evidence SHA-256
Network
```

## Tamper Demonstration

Click:

**Run tamper check**

The application modifies an evidence field in memory and recomputes the SHA-256 digest.

Because the modified record produces a different hash, the verification result becomes:

```text
TAMPERED
```

The original blockchain record is not modified.

This demonstrates that changes to the anchored evidence can be detected.

## Terminal Pipeline

Run the pipeline directly:

```powershell
python pipeline/main.py --image "C:\path\to\your-consented-photo.jpg"
```

If the configured implementation requires an image URL:

```powershell
python pipeline/main.py `
  --image "C:\path\to\your-consented-photo.jpg" `
  --image-url "https://example.com/image.jpg"
```

Reports are saved under:

```text
output/<timestamp>/report_<timestamp>.json
```

## Verify a Report

```powershell
python pipeline/verify.py `
  --report "output\<timestamp>\report_<timestamp>.json"
```

## Simulate Tampering

```powershell
python pipeline/verify.py `
  --report "output\<timestamp>\report_<timestamp>.json" `
  --simulate-tamper
```

Expected result:

```text
TAMPERED
```

## Tests

Run the offline test suite:

```powershell
pytest -q
```

## What This Proves

The blockchain record provides tamper evidence for the anchored evidence record.

If any hashed evidence field changes, the resulting SHA-256 digest changes.

```text
Original Evidence
      ↓
SHA-256 A
      ↓
Blockchain

Modified Evidence
      ↓
SHA-256 B

SHA-256 A ≠ SHA-256 B
      ↓
TAMPERED
```

## What This Does Not Prove

This project does not:

* Prove a person's legal or real-world identity
* Guarantee that a visual match belongs to a particular person
* Guarantee that a matching result exists online
* Search private or restricted social-media accounts
* Search unindexed content
* Guarantee that Google Lens results are correct
* Guarantee that face embedding results are correct
* Eliminate false positives or false negatives
* Establish legal ownership of an image

The blockchain verifies the integrity of the stored evidence record; it does not independently prove that the evidence itself is true.

## Privacy and Ethics

Only use images you own or have explicit permission to search.

Do not use this project to:

* Track people without consent
* Profile individuals
* Identify strangers without authorization
* Search private accounts
* Bypass access controls
* Process personal images without appropriate permission

Reverse-image search and facial similarity can produce incorrect results. Human review and appropriate authorization are required.

## Project Structure

```text
The-Acers/
│
├── app.py
├── requirements.txt
├── package.json
├── hardhat.config.js
├── .env.example
├── README.md
│
├── contracts/
│   └── FaceVerification.sol
│
├── scripts/
│   └── deploy.js
│
├── pipeline/
│   ├── main.py
│   └── verify.py
│
├── output/
│
└── tests/
```

## Hackathon Demo Flow

```text
1. Start Hardhat node
2. Deploy FaceVerification.sol
3. Start the dashboard
4. Open Settings
5. Show masked configuration
6. Upload a consented image
7. Select a face if multiple people are detected
8. Run visual search
9. Show Most Similar / Relevant / Similar results
10. Show Evidence SHA-256
11. Show blockchain transaction
12. Show MATCH
13. Click Run tamper check
14. Show TAMPERED
```

For Polygon Amoy transactions:

```text
https://amoy.polygonscan.com/tx/<TX_HASH>
```

## Troubleshooting

### Dashboard does not start

Activate the virtual environment:

```powershell
.venv\Scripts\Activate.ps1
```

Then:

```powershell
uvicorn app:app --reload --port 8000
```

### Hardhat connection fails

Make sure the node is running:

```powershell
npx hardhat node
```

and verify:

```env
WEB3_RPC_URL=http://127.0.0.1:8545
```

### Contract not found

Deploy again after restarting Hardhat:

```powershell
npx hardhat run scripts/deploy.js --network localhost
```

Update the contract address in your configuration.

### Image upload rejected

Check that the image is:

```text
JPG / JPEG / PNG / WEBP
≤ 500 KB
```

### No Google Lens result

A public visual match may not exist or may not be returned. The application does not fabricate results.

### Polygon Amoy transaction fails

Check:

* RPC URL
* Wallet/test private key
* Test MATIC balance
* Contract address
* Network configuration

## Git Commands

After updating the README:

```powershell
git add README.md
git commit -m "Improve project README"
git push
```

## Ethical Use Statement

> **The Acers is intended for authorized, consented, and responsible use only.**
>
> The system combines visual search, advisory face similarity, cryptographic hashing, and blockchain anchoring to demonstrate tamper-evident evidence handling. It is not a production identity-verification system.

## Limitations

The Acers is a proof-of-concept system and has several technical and practical limitations.

### Image Limitations

- The dashboard accepts JPG, JPEG, PNG, and WEBP images only.
- The current maximum upload size is **500 KB**.
- Low-resolution, heavily compressed, blurred, poorly lit, or partially obstructed faces may reduce detection and matching quality.
- Multiple faces may require manual person selection.
- The system cannot guarantee successful face detection in every image.

### Visual Search Limitations

- Google Lens / SerpApi results depend on what is publicly indexed and available at the time of the search.
- Private, restricted, deleted, or unindexed pages may not be discovered.
- Search engines may return visually similar but unrelated images.
- Results can change over time.
- A lack of search results does not mean that no related image exists online.
- The system does not fabricate results when the visual search returns no usable match.

### Face Comparison Limitations

- Face embedding comparison is **advisory**, not an identity decision.
- Accuracy can be affected by lighting, pose, occlusion, image quality, facial expression, age, and camera conditions.
- Similarity thresholds are not universal and may require calibration for different datasets.
- Both false positives and false negatives are possible.

### Blockchain Limitations

- Blockchain anchoring proves the integrity of the stored evidence record, not the truth or authenticity of the evidence itself.
- A `MATCH` means the recomputed evidence hash matches the anchored blockchain hash; it does not mean that a person has been positively identified.
- Local Hardhat state is temporary and is reset when the Hardhat node is restarted.
- Polygon Amoy is a test network and may experience RPC, faucet, or network availability issues.
- Blockchain verification depends on correct RPC, wallet, network, and contract configuration.

### Privacy and Legal Limitations

- The project should only be used with images that the user owns or is authorized to process.
- Public availability does not automatically mean that personal content can be used for identification or profiling.
- The system does not bypass authentication, access controls, or private-account restrictions.
- Users are responsible for complying with applicable privacy, data-protection, and platform requirements.

### Operational Limitations

- Live Google Lens searches require an internet connection and a working SerpApi configuration.
- Third-party search results and APIs may change their behavior, availability, or response format.
- Candidate pages may not contain a usable face image for comparison.
- The system is designed for demonstration and research purposes and is not a production-grade identity-verification platform.

## License

This project is a hackathon proof of concept. Review the repository license and the terms of any third-party services used before distributing or deploying the project beyond the intended demonstration environment.
