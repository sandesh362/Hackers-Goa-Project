from __future__ import annotations
import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
try:
    from .face_id import extract_face, save_encoding, save_search_crop
    from .web_search import reverse_image_search
    from .face_match import compare_candidate
    from .blockchain import submit_record, fetch_record_hash
    from .verify import verify_record
except ImportError:  # supports the README's `python pipeline/main.py` command
    from face_id import extract_face, save_encoding, save_search_crop
    from web_search import reverse_image_search
    from face_match import compare_candidate
    from blockchain import submit_record, fetch_record_hash
    from verify import verify_record

console = Console()
def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Face evidence → live search → Polygon tamper-evidence demo")
    parser.add_argument("--image", required=True); parser.add_argument("--image-url", default=os.getenv("INPUT_IMAGE_URL")); parser.add_argument("--output", default="output"); args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"); output = Path(args.output) / stamp; output.mkdir(parents=True)
    console.print("[cyan]1/5 Detecting exactly one face…[/cyan]"); face = extract_face(args.image); save_encoding(face, output); search_crop = save_search_crop(face, output)
    console.print("[cyan]2/5 Searching Google Lens with face-focused crop via SerpApi…[/cyan]"); results = reverse_image_search(image_path=search_crop)
    if not results: raise RuntimeError("No live reverse-image results were returned; no match has been fabricated.")
    console.print(f"[green]Top hit:[/green] {results[0]['url']}")
    console.print("[cyan]3/5 Comparing candidate face (advisory)…[/cyan]"); similarity = compare_candidate(face.encoding, results[0].get("image_url_if_available"))
    evidence = {"face_hash": face.face_hash, "matched_url": results[0]["url"], "snippet": results[0]["snippet"], "source_domain": results[0]["source_domain"], "similarity_score": similarity.get("distance"), "timestamp": datetime.now(timezone.utc).isoformat()}
    console.print("[cyan]4/5 Storing canonical evidence digest on-chain…[/cyan]"); chain = submit_record(evidence)
    if os.getenv("NETWORK", "amoy").lower() == "amoy": chain["explorer_url"] = f"https://amoy.polygonscan.com/tx/{chain['tx_hash']}"
    console.print("[cyan]5/5 Reading the stored digest back for independent verification…[/cyan]")
    verification = verify_record(evidence, fetch_record_hash(chain["record_id"]))
    report = {"evidence": evidence, "ranked_search_results": results, "similarity": similarity, "blockchain": chain, "verification": verification}
    path = output / f"report_{stamp}.json"; path.write_text(json.dumps(report, indent=2))
    console.print(f"[bold green]{verification['status']}:[/bold green] evidence digest agrees with chain.\n[bold green]Saved report:[/bold green] {path}\nRun: python pipeline/verify.py --report {path} --simulate-tamper")
if __name__ == "__main__": main()
