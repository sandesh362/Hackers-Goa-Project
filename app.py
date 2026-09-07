"""Local browser dashboard for the face-evidence demonstration pipeline."""
from __future__ import annotations
import os, shutil, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from PIL import Image
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv, set_key
from web3 import Web3

ROOT = Path(__file__).parent
ENV_FILE, OUTPUT = ROOT / ".env", ROOT / "output"
load_dotenv(ENV_FILE)
app = FastAPI(title="The Acers", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
RUNS: dict[str, dict[str, Any]] = {}
SETTINGS = ("SERPAPI_KEY", "WEB3_RPC_URL", "PRIVATE_KEY", "CONTRACT_ADDRESS", "NETWORK", "INPUT_IMAGE_URL", "SIMILARITY_THRESHOLD", "MAX_WEB_RESULTS")
SECRET_SETTINGS = {"SERPAPI_KEY", "PRIVATE_KEY"}

@app.middleware("http")
async def disable_browser_caching(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, max-age=0"
    return response

def _masked(name: str, value: str) -> str:
    if name in SECRET_SETTINGS and value: return "••••••••" + value[-4:]
    return value

@app.get("/")
def dashboard(): return FileResponse(ROOT / "static" / "index.html")

@app.get("/api/settings")
def get_settings():
    return {key: _masked(key, os.getenv(key, "")) for key in SETTINGS} | {"configured": {key: bool(os.getenv(key)) for key in SETTINGS}}

@app.post("/api/settings")
def save_settings(values: dict[str, str]):
    ENV_FILE.touch(exist_ok=True)
    for key, value in values.items():
        if key not in SETTINGS: continue
        # Empty secret fields mean "keep existing", so a settings save cannot erase them accidentally.
        if key in SECRET_SETTINGS and not value: continue
        set_key(str(ENV_FILE), key, value)
        os.environ[key] = value
    return {"ok": True}

@app.post("/api/settings/autoconfigure-local")
def autoconfigure_local():
    """Connect the UI to a running fresh local Hardhat deployment."""
    rpc = "http://127.0.0.1:8545"
    web3 = Web3(Web3.HTTPProvider(rpc))
    if not web3.is_connected():
        raise HTTPException(503, "Hardhat is not running. Start it with: npx hardhat node")
    address = "0x5FbDB2315678afecb367f032d93F642f64180aa3"
    if not web3.eth.get_code(Web3.to_checksum_address(address)):
        raise HTTPException(404, "Contract not found. Deploy it with: npx hardhat run scripts/deploy.js --network localhost")
    ENV_FILE.touch(exist_ok=True)
    for key, value in {"NETWORK": "local", "WEB3_RPC_URL": rpc, "CONTRACT_ADDRESS": address}.items():
        set_key(str(ENV_FILE), key, value); os.environ[key] = value
    return {"ok": True, "address": address}

def run_pipeline(run_id: str, image_path: Path, image_url: str):
    state = RUNS[run_id]
    try:
        from pipeline.face_id import extract_face, save_encoding, save_search_crop
        from pipeline.web_search import reverse_image_search
        from pipeline.face_match import compare_candidate
        from pipeline.blockchain import submit_record, fetch_record_hash
        from pipeline.verify import verify_record
        state.update(status="running", stage="Detecting one face")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"); folder = OUTPUT / stamp; folder.mkdir(parents=True, exist_ok=True)
        face = extract_face(image_path); save_encoding(face, folder); search_crop = save_search_crop(face, folder)
        state.update(face_detection=face.detection_method)
        state.update(stage="Searching with a face-focused crop")
        # Send the face-focused crop to Lens so clothing/background do not dominate visual matches.
        results = reverse_image_search(image_path=search_crop)
        if not results: raise RuntimeError("No live reverse-image results were returned. No match was fabricated.")
        state.update(stage="Comparing the top candidate (advisory)")
        similarity = compare_candidate(face.encoding, results[0].get("image_url_if_available"))
        evidence = {"face_hash": face.face_hash, "matched_url": results[0]["url"], "snippet": results[0]["snippet"], "source_domain": results[0]["source_domain"], "similarity_score": similarity.get("distance"), "timestamp": datetime.now(timezone.utc).isoformat()}
        chain, verification = {"available": False}, {"status": "SEARCH COMPLETE"}
        blockchain_ready = all(os.getenv(key) for key in ("WEB3_RPC_URL", "PRIVATE_KEY", "CONTRACT_ADDRESS"))
        if blockchain_ready:
            state.update(stage="Anchoring evidence on-chain")
            chain = submit_record(evidence)
            chain["available"] = True
            if os.getenv("NETWORK", "amoy").lower() == "amoy": chain["explorer_url"] = f"https://amoy.polygonscan.com/tx/{chain['tx_hash']}"
            state.update(stage="Re-verifying the stored digest")
            verification = verify_record(evidence, fetch_record_hash(chain["record_id"]))
        else:
            chain["message"] = "Search results are ready. Add RPC URL, private key, and contract address in Settings to enable the optional blockchain receipt."
        report = {"evidence": evidence, "face_detection": face.detection_method, "ranked_search_results": results, "similarity": similarity, "blockchain": chain, "verification": verification}
        report_path = folder / f"report_{stamp}.json"; report_path.write_text(__import__("json").dumps(report, indent=2))
        state.update(status="complete", stage="Complete", report=report, report_path=str(report_path))
    except BaseException as exc:
        state.update(status="error", stage="Stopped", error=str(exc) or exc.__class__.__name__)

def crop_to_selected_person(image_path: Path, focus_x: float, focus_y: float) -> Path:
    """Create a generous crop centered on the user-selected person, using normalized coordinates."""
    with Image.open(image_path) as source:
        image = source.convert("RGB")
        width, height = image.size
        crop_width, crop_height = int(width * 0.66), int(height * 0.70)
        center_x, center_y = int(width * focus_x), int(height * focus_y)
        left = min(max(center_x - crop_width // 2, 0), width - crop_width)
        top = min(max(center_y - crop_height // 2, 0), height - crop_height)
        selected = image.crop((left, top, left + crop_width, top + crop_height))
        path = image_path.with_name(image_path.stem + "_selected.jpg")
        selected.save(path, "JPEG", quality=90, optimize=True)
    return path

@app.post("/api/runs")
async def start_run(background_tasks: BackgroundTasks, image: UploadFile = File(...), image_url: str = Form(""), focus_x: str = Form(""), focus_y: str = Form("")):
    if not image.filename: raise HTTPException(400, "Upload a JPG, PNG, or WEBP image.")
    if image_url and not image_url.startswith(("http://", "https://")): raise HTTPException(400, "The optional image URL must start with http:// or https://.")
    upload_dir = OUTPUT / "uploads"; upload_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(image.filename).suffix.lower() or ".jpg"; path = upload_dir / f"{uuid.uuid4().hex}{suffix}"
    with path.open("wb") as destination: shutil.copyfileobj(image.file, destination)
    selected = False
    if focus_x and focus_y:
        try:
            x, y = float(focus_x), float(focus_y)
            if not (0 <= x <= 1 and 0 <= y <= 1): raise ValueError
            path = crop_to_selected_person(path, x, y); selected = True
        except ValueError:
            raise HTTPException(400, "The selected-person coordinates were invalid. Click the preview again.")
    run_id = uuid.uuid4().hex[:10]; RUNS[run_id] = {"id": run_id, "status": "queued", "stage": "Preparing selected person" if selected else "Preparing your evidence run", "manual_selection": selected}
    background_tasks.add_task(run_pipeline, run_id, path, image_url)
    return RUNS[run_id]

@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    if run_id not in RUNS: raise HTTPException(404, "Run not found")
    return RUNS[run_id]

@app.post("/api/runs/{run_id}/tamper")
def tamper_check(run_id: str):
    if run_id not in RUNS or RUNS[run_id].get("status") != "complete": raise HTTPException(409, "Complete a run first.")
    from pipeline.verify import verify_record
    report = RUNS[run_id]["report"]; return verify_record(report["evidence"], report["blockchain"]["evidence_hash"], simulate_tamper=True)
