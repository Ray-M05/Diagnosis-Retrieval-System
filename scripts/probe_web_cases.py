"""Probe candidate clinical cases to find one poorly covered locally but where
web-retrieved chunks reach the final top after enrichment.

Run with the API up (default port 8127). Prints, per case: web docs/chunks added
and how many WEB chunks land in the raw hybrid top-k.
"""
from __future__ import annotations

import json
import urllib.request

API = "http://127.0.0.1:8127/pipeline"
OS = "http://localhost:9200"


def _os(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        OS + path, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    return json.load(urllib.request.urlopen(req, timeout=15))


def _web_doc_ids() -> set[str]:
    r = _os("/clinical_docs_web_v1/_search", {"size": 1000, "_source": []})
    return {h["_id"] for h in r["hits"]["hits"]}


def probe(query: str) -> dict:
    body = {"query": query, "k": 10,
            "stages": {"web_enrichment": True, "raw_hybrid": True}}
    req = urllib.request.Request(
        API, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    d = json.load(urllib.request.urlopen(req, timeout=300))
    web_ids = _web_doc_ids()
    rh = d.get("hybrid_chunks") or []
    web_top = [c for c in rh if str(c.get("doc_id") or "") in web_ids]
    we = d.get("web_enriched") or {}
    return {
        "docs_added": we.get("docs_added"),
        "chunks_added": we.get("chunks_added"),
        "api_retrieved": we.get("api_retrieved"),
        "raw_n": len(rh),
        "web_in_top": len(web_top),
        "web_top_detail": [
            (round(c.get("rerank_score") or 0, 2), c.get("vector_score"),
             str(c.get("title") or c.get("section_heading") or "")[:38],
             str(c.get("url") or "")[:48])
            for c in web_top
        ],
        "top3": [
            ("WEB" if str(c.get("doc_id") or "") in web_ids else "loc",
             round(c.get("rerank_score") or 0, 2),
             str(c.get("title") or c.get("section_heading") or "")[:32])
            for c in rh[:3]
        ],
    }


CASES = {
    "Erdheim-Chester": "Adult with bone pain in the legs, diabetes insipidus with excessive thirst and urination, bilateral exophthalmos, and perinephric fat infiltration described as hairy kidney on imaging; xanthelasma-like skin lesions",
    "POEMS": "Middle-aged adult with progressive peripheral neuropathy, enlarged liver and spleen, skin hyperpigmentation and thickening, excessive hair growth, and a monoclonal plasma cell disorder with elevated VEGF",
    "Whipple": "Adult with chronic diarrhea and weight loss, migratory joint pain for years, abdominal pain, low-grade fever, and skin darkening; small bowel biopsy shows PAS-positive macrophages",
    "Fabry": "Young man with episodes of burning pain in hands and feet, clusters of dark red skin spots around the navel and groin, decreased sweating, corneal whorl-like opacities, and progressive kidney impairment",
    "Castleman": "Adult with enlarged lymph nodes, fevers and night sweats, fatigue, fluid retention, low blood counts, and elevated inflammatory markers with high IL-6",
    "Susac": "Young woman with the triad of encephalopathy with confusion, branch retinal artery occlusions causing visual loss, and sensorineural hearing loss",
}


def main() -> None:
    print("=== Probing candidate cases (web-enrichment + raw_hybrid) ===\n")
    results = {}
    for name, q in CASES.items():
        try:
            r = probe(q)
            results[name] = r
            print(f"[{name}] docs+={r['docs_added']} chunks+={r['chunks_added']} "
                  f"api={r['api_retrieved']} | WEB in raw top-{r['raw_n']}: {r['web_in_top']}")
            for blk in r["web_top_detail"]:
                print(f"     WEB rr={blk[0]} vec={blk[1]} | {blk[2]} | {blk[3]}")
            print(f"     top3: {r['top3']}")
        except Exception as exc:  # noqa: BLE001
            print(f"[{name}] ERROR: {exc}")
        print()

    winners = {k: v for k, v in results.items() if (v.get("web_in_top") or 0) > 0}
    print("=== WINNERS (web chunks in final top) ===")
    for k, v in sorted(winners.items(), key=lambda kv: -kv[1]["web_in_top"]):
        print(f"  {k}: {v['web_in_top']} web chunk(s) in top")
    if not winners:
        print("  (none yet)")


if __name__ == "__main__":
    main()
