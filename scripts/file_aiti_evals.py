#!/usr/bin/env python3
"""File first-party AI evals and incidents for AITI. Probe only. Do not invent."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import crawl  # noqa: E402

SITE = ROOT / "site"
OUT = SITE / "data" / "aiti-evals-probe.json"
PAGES = SITE / "data" / "aiti-pages.json"
EVALS = SITE / "data" / "aiti-evals.json"
INCIDENTS = SITE / "data" / "aiti-incidents.json"

VENDOR_HOST_RE = re.compile(
    r"(^|\.)(safebase\.us|safebase\.com|vanta\.com|conveyor\.com|wolfia\.\w+|"
    r"securitypal\.com|drata\.com|secureframe\.com|whistic\.com|"
    r"sprinto\.com|trustcloud\.com)$",
    re.I,
)
LOGIN_RE = re.compile(r"\b(sign in|log in|login|create an account|powered by safebase)\b", re.I)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")

EVAL_PATH_RE = re.compile(
    r"system-?card|model-?card|safety-?evals?|eval(?:uation)?-?report|"
    r"(?:^|/)evals?(?:/|$)",
    re.I,
)
EVAL_TEXT_RE = re.compile(
    r"\b(system card|model card|safety eval(?:uation)?s?|evaluation report|"
    r"eval(?:uation)? tables?|benchmark results|mmlu|gpqa)\b",
    re.I,
)
EVAL_REJECT_TEXT_RE = re.compile(
    r"\b(what is a model card|write (?:a |your )?model card|"
    r"compare (?:models|benchmarks)|choose the right model|model garden)\b",
    re.I,
)
INCIDENT_PATH_RE = re.compile(
    r"ai-incidents?|safety-incidents?|transparency-incidents?|"
    r"(?:^|/)(?:ai[-/])?post-?mortems?(?:/|$)|(?:^|/)incidents?(?:/|$)",
    re.I,
)
INCIDENT_TEXT_RE = re.compile(
    r"\b(ai (?:safety )?incident|safety incident|post-?mortem|"
    r"incident (?:report|log|disclosure|transparency))\b",
    re.I,
)
INCIDENT_REJECT_RE = re.compile(
    r"\b(all systems operational|status page|incident response plan|"
    r"aiid|ai incident database)\b",
    re.I,
)

# Known first-party candidates. Still fetch-checked. Anthropic omitted on purpose.
EVAL_TRY = {
    "openai": [
        "https://cdn.openai.com/papers/gpt-4-system-card.pdf",
        "https://cdn.openai.com/gpt-4o-system-card.pdf",
    ],
    "xai": [
        "https://data.x.ai/2026-04-07-grok-4-20-model-card.pdf",
    ],
    "cohere": [
        "https://docs.cohere.com/docs/responsible-use",
        "https://docs.cohere.com/docs/command-r-plus",
        "https://docs.cohere.com/docs/command-r-plus-model-card",
    ],
    "ibm": [
        "https://www.ibm.com/docs/en/watsonx/w-and-w/2.1.0?topic=models-granite-30-2b-instruct-model-card",
        "https://www.ibm.com/granite/docs/models/granite",
        "https://www.ibm.com/docs/en/cloud-paks/cp-data/4.8.x?topic=models-granite-13b-chat-v2-model-card",
    ],
    "meta": [
        "https://llama.meta.com/docs/model-cards-and-prompt-formats/meta-LLaMA-3/",
        "https://ai.meta.com/static-resource/meta-llama-3-model-card",
        "https://ai.meta.com/research/publications/the-llama-3-herd-of-models/",
        "https://www.llama.com/docs/model-cards-and-prompt-formats/llama4/",
    ],
    "google": [
        "https://cloud.google.com/vertex-ai/generative-ai/docs/learn/models",
        "https://deepmind.google/models/model-cards/",
        "https://storage.googleapis.com/deepmind-media/Model-Cards/Gemini-3-Pro-Model-Card.pdf",
    ],
    "microsoft": [
        "https://learn.microsoft.com/en-us/azure/ai-foundry/responsible-ai/openai/transparency-note",
        "https://www.microsoft.com/en-us/research/wp-content/uploads/2024/12/P4TechReport.pdf",
    ],
    "amazon": [
        "https://docs.aws.amazon.com/bedrock/latest/userguide/model-cards.html",
        "https://docs.aws.amazon.com/ai/responsible-ai/nova-micro-lite-pro/overview.html",
    ],
    "deepseek": [
        "https://fe-static.deepseek.com/chat/transparency/deepseek-v3.2-model-card-0414-CN.pdf",
    ],
    "nvidia": [
        "https://build.nvidia.com/nvidia/nemotron-3-ultra-550b-a55b/modelcard",
        "https://developer.nvidia.com/topics/ai/nemotron",
    ],
    "apple": [
        "https://machinelearning.apple.com/research/apple-foundation-models-tech-report-2025",
    ],
    "mistral-ai": [
        "https://docs.mistral.ai/models",
    ],
    "ai21": [
        "https://docs.ai21.com/docs/jamba-1-5",
    ],
    "allen-institute-for-ai": [
        "https://allenai.org/olmo",
    ],
    "salesforce": [
        "https://compliance.salesforce.com/categories/salesforce-owned-model-cards",
        "https://help.salesforce.com/s/articleView?id=mktg.mktg_einstein_model_card_eef.htm&language=en_US&type=5",
        "https://developer.salesforce.com/docs/analytics/einstein-vision-language/guide/einstein-ocr-model-card.html",
    ],
    "gitlab": [
        "https://about.gitlab.com/direction/ai-powered/ai_framework/ai_evaluation/foundation_models/",
    ],
}

INCIDENT_TRY = {
    "openai": [
        "https://openai.com/incidents",
        "https://openai.com/safety/incidents",
        "https://openai.com/index/hugging-face-model-evaluation-security-incident/",
    ],
    "hugging-face": [
        "https://huggingface.co/postmortem",
        "https://huggingface.co/incidents",
    ],
    "microsoft": [
        "https://www.microsoft.com/en-us/ai/incidents",
    ],
    "google": [
        "https://ai.google/responsibility/incidents",
    ],
    "ibm": [
        "https://www.ibm.com/trust/incidents",
    ],
    "meta": [
        "https://ai.meta.com/incidents",
    ],
    "gitlab": [
        "https://about.gitlab.com/ai-transparency-center/incidents/",
    ],
}


def host_of(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower().removeprefix("www.")
    except Exception:
        return ""


def first_party(url: str, domain: str) -> bool:
    host = host_of(url)
    own = (domain or "").lower().removeprefix("www.")
    if not host or not own:
        return False
    if VENDOR_HOST_RE.search(host):
        return False
    return host == own or host.endswith("." + own)


def path_of(url: str) -> str:
    try:
        return urlparse(url).path or ""
    except Exception:
        return ""


def strip_tags(html: str) -> str:
    return unescape(TAG_RE.sub(" ", html or "")).replace("\xa0", " ")


def reject_wall(title: str, text: str, status: int) -> bool:
    if status in (401, 403):
        return True
    if LOGIN_RE.search(title or "") or LOGIN_RE.search((text or "")[:1500]):
        return True
    return False


def is_pdf(rec: dict) -> bool:
    body = rec.get("text") or rec.get("html") or ""
    final = rec.get("final_url") or ""
    return body.lstrip().startswith("%PDF") or path_of(final).lower().endswith(".pdf")


def looks_eval(url: str, title: str, text: str, rec: dict) -> bool:
    path = path_of(url)
    blob = f"{title} {text[:8000]}"
    if EVAL_REJECT_TEXT_RE.search(title or "") or EVAL_REJECT_TEXT_RE.search(blob[:2000]):
        return False
    if is_pdf(rec) and EVAL_PATH_RE.search(path or url):
        return True
    if not EVAL_TEXT_RE.search(blob) and not EVAL_TEXT_RE.search(title or ""):
        return False
    if EVAL_PATH_RE.search(path) or EVAL_PATH_RE.search(url):
        return True
    if re.search(r"\b(system card|model card|evaluation report|safety evals)\b", title or "", re.I):
        return True
    return False


def looks_incident(url: str, title: str, text: str) -> bool:
    path = path_of(url)
    blob = f"{title} {text[:4000]}"
    if INCIDENT_REJECT_RE.search(title or "") or INCIDENT_REJECT_RE.search(blob[:2000]):
        return False
    if not INCIDENT_TEXT_RE.search(blob) and not INCIDENT_TEXT_RE.search(title or ""):
        return False
    if INCIDENT_PATH_RE.search(path) or INCIDENT_PATH_RE.search(url):
        return True
    if re.search(r"\b(ai (?:safety )?incident|safety incident|post-?mortem)\b", title or "", re.I):
        return True
    return False


def get(url: str) -> dict:
    rec = crawl.fetch(url, max_body=48000)
    html = rec.get("body") or ""
    title_m = TITLE_RE.search(html)
    h1_m = H1_RE.search(html)
    title = unescape(TAG_RE.sub("", (title_m.group(1) if title_m else "")).strip())
    h1 = unescape(TAG_RE.sub("", (h1_m.group(1) if h1_m else "")).strip())
    return {
        "ok": bool(rec.get("ok")),
        "status": rec.get("status") or 0,
        "final_url": rec.get("final_url") or url,
        "title": title,
        "h1": h1,
        "text": strip_tags(html),
        "html": html,
    }


def accept_common(row: dict, rec: dict) -> str:
    if not rec.get("ok") or rec.get("status") != 200:
        return ""
    final = rec.get("final_url") or ""
    if not first_party(final, row.get("domain") or ""):
        return ""
    if reject_wall(rec.get("title") or "", rec.get("text") or "", rec.get("status") or 0):
        return ""
    path = path_of(final).rstrip("/")
    if path in ("", "/"):
        return ""
    title = rec.get("title") or ""
    if re.search(r"\b(page not found|not found|404|just a moment|attention required)\b", title, re.I):
        return ""
    return final


def accept_eval(row: dict, rec: dict) -> str:
    final = accept_common(row, rec)
    if not final:
        return ""
    if not looks_eval(final, rec.get("title") or "", rec.get("text") or "", rec):
        return ""
    if not is_pdf(rec) and len(rec.get("text") or "") < 400:
        return ""
    return final


def accept_incident(row: dict, rec: dict) -> str:
    final = accept_common(row, rec)
    if not final:
        return ""
    if not looks_incident(final, rec.get("title") or "", rec.get("text") or ""):
        return ""
    if len(rec.get("text") or "") < 400:
        return ""
    return final


def aiti_rows() -> list[dict]:
    slugs = json.loads(
        subprocess.check_output(
            [
                "node",
                "--input-type=module",
                "-e",
                "import { readFileSync } from 'node:fs'; import { selectAiFiles } from './site/lib.js';"
                "const d=JSON.parse(readFileSync('./site/data.json','utf8'));"
                "process.stdout.write(JSON.stringify(selectAiFiles(d.companies).map(r=>r.slug)));",
            ],
            cwd=ROOT,
        )
    )
    data = json.loads((SITE / "data.json").read_text())
    by_slug = {c["slug"]: c for c in data["companies"]}
    return [by_slug[s] for s in slugs if s in by_slug]


def stored_system_cards(rows: list[dict]) -> list[tuple[dict, str]]:
    pages = {}
    if PAGES.exists():
        pages = json.loads(PAGES.read_text()).get("pages") or {}
    out = []
    for row in rows:
        rec = pages.get(row["slug"]) or {}
        url = rec.get("url") if isinstance(rec, dict) else ""
        kind = str((rec.get("kind") if isinstance(rec, dict) else "") or "")
        if url and re.search(r"system-?card", kind + " " + url, re.I):
            out.append((row, url))
    return out


def add_jobs(jobs: list, seen: set, row: dict, url: str) -> None:
    key = (row["slug"], url)
    if key in seen or not url:
        return
    seen.add(key)
    jobs.append((row, url))


def main() -> int:
    rows = aiti_rows()
    by_slug = {r["slug"]: r for r in rows}
    evals = {}
    incidents = {}
    rejected = []
    notes = []
    eval_jobs = []
    inc_jobs = []
    seen_e = set()
    seen_i = set()

    for row, url in stored_system_cards(rows):
        add_jobs(eval_jobs, seen_e, row, url)
    for slug, urls in EVAL_TRY.items():
        row = by_slug.get(slug)
        if not row or slug == "anthropic":
            continue
        for url in urls:
            add_jobs(eval_jobs, seen_e, row, url)
    for slug, urls in INCIDENT_TRY.items():
        row = by_slug.get(slug)
        if not row or slug == "anthropic":
            continue
        for url in urls:
            add_jobs(inc_jobs, seen_i, row, url)

    print(f"eval jobs {len(eval_jobs)} incident jobs {len(inc_jobs)}", flush=True)

    def run(jobs, accept, bucket, kind):
        with ThreadPoolExecutor(max_workers=8) as pool:
            futs = {pool.submit(get, url): (row, url) for row, url in jobs}
            for fut in as_completed(futs):
                row, url = futs[fut]
                try:
                    rec = fut.result()
                except Exception as exc:
                    notes.append(f"{row['slug']} {url} err {exc}")
                    continue
                final = accept(row, rec)
                if final and row["slug"] not in bucket:
                    bucket[row["slug"]] = {
                        "url": final,
                        "host": host_of(final),
                        "title": rec.get("title") or "",
                        "via": "probe",
                        "from": url,
                        "kind": kind,
                    }
                    print("filed", kind, row["slug"], final, flush=True)
                elif rec.get("ok") and rec.get("status") == 200:
                    rejected.append(
                        {
                            "slug": row["slug"],
                            "url": rec.get("final_url") or url,
                            "kind": kind,
                            "status": rec.get("status"),
                            "title": rec.get("title") or "",
                            "reason": "200 but not a clear first-party eval/incident instrument",
                        }
                    )
                else:
                    rejected.append(
                        {
                            "slug": row["slug"],
                            "url": url,
                            "kind": kind,
                            "status": rec.get("status") or 0,
                            "title": rec.get("title") or "",
                            "reason": f"fetch {rec.get('status') or 0}",
                        }
                    )

    run(eval_jobs, accept_eval, evals, "evals")
    run(inc_jobs, accept_incident, incidents, "incidents")

    payload = {
        "generated_at": "2026-08-21T00:50:00Z",
        "rule": (
            "Probe only. The filed lists are site/data/aiti-evals.json and "
            "site/data/aiti-incidents.json. Evals fill only from a stored "
            "first-party model/system card with eval tables, official eval "
            "report, or safety evals page. Incidents fill only from the "
            "company's own AI incident/postmortem page. Anthropic stays open. "
            "Do not invent."
        ),
        "curated_evals": str(EVALS.relative_to(ROOT)),
        "curated_incidents": str(INCIDENTS.relative_to(ROOT)),
        "evals": evals,
        "incidents": incidents,
        "rejected": rejected,
        "notes": notes,
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote", OUT, "evals", len(evals), "incidents", len(incidents), "rejected", len(rejected))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
