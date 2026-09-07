"""Live SerpApi Google Lens search plus transparent ranking."""
from __future__ import annotations
from urllib.parse import urlparse
from pathlib import Path
import os, requests

SOCIAL_DOMAINS = ("instagram.com", "x.com", "twitter.com", "linkedin.com", "facebook.com", "reddit.com")

def domain_for(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")

def rank_results(raw_results: list[dict]) -> list[dict]:
    """Boost social domains; retain every result, including high-ranked non-social pages."""
    ranked = []
    for item in raw_results:
        url = item.get("link") or item.get("source") or ""
        domain = domain_for(url)
        base = float(item.get("relevance") or item.get("score") or 0)
        bonus = 0.10 if any(domain == d or domain.endswith("." + d) for d in SOCIAL_DOMAINS) else 0
        ranked.append({"url": url, "title": item.get("title", ""), "snippet": item.get("snippet", ""),
                       "source_domain": domain, "image_url_if_available": item.get("thumbnail") or item.get("image"),
                       "score": base + bonus, "base_score": base, "social_bonus": bonus})
    return sorted(ranked, key=lambda result: result["score"], reverse=True)

def upload_image(image_path: str | Path, api_key: str) -> str:
    """Upload a local image to SerpApi and return its short-lived Google Lens image ID."""
    path = Path(image_path)
    if path.stat().st_size > 500 * 1024:
        raise ValueError("SerpApi accepts uploads up to 500 KB. Use a smaller JPG, PNG, or WebP image.")
    with path.open("rb") as image_file:
        response = requests.post("https://serpapi.com/image", data={"api_key": api_key}, files={"image": (path.name, image_file)}, timeout=45)
    response.raise_for_status(); payload = response.json()
    if payload.get("error") or not payload.get("image_id"):
        raise RuntimeError(f"SerpApi image upload failed: {payload.get('error', 'no image_id returned')}")
    return payload["image_id"]

def reverse_image_search(image_url: str | None = None, api_key: str | None = None, image_path: str | Path | None = None) -> list[dict]:
    """Make a genuine Lens search by public URL or a direct temporary SerpApi upload."""
    key = api_key or os.getenv("SERPAPI_KEY")
    if not key: raise RuntimeError("SERPAPI_KEY is missing. Put it in .env or your environment.")
    if not image_url and not image_path: raise RuntimeError("Provide an image URL or local image path for live reverse search.")
    params = {"engine": "google_lens", "api_key": key}
    if image_url: params["url"] = image_url
    else: params["image_id"] = upload_image(image_path, key)
    response = requests.get("https://serpapi.com/search.json", params=params, timeout=45)
    response.raise_for_status(); data = response.json()
    if data.get("error"): raise RuntimeError(f"SerpApi error: {data['error']}")
    # The dashboard prioritizes clarity: present the three strongest public, indexed results.
    max_web_results = int(os.getenv("MAX_WEB_RESULTS", "3"))
    return rank_results(data.get("visual_matches", []) + data.get("exact_matches", []))[:max_web_results]
