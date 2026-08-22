#!/usr/bin/env python3
"""File first-party AI-page URLs for AITI. Probe only. Do not invent."""
from __future__ import annotations

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import crawl  # noqa: E402

SITE = ROOT / "site"
OUT = SITE / "data" / "aiti-pages-probe.json"
CURATED = SITE / "data" / "aiti-pages.json"

VENDOR_HOST_RE = re.compile(
    r"(^|\.)(safebase\.us|safebase\.com|vanta\.com|conveyor\.com|wolfia\.\w+|"
    r"securitypal\.com|drata\.com|secureframe\.com|whistic\.com|"
    r"sprinto\.com|trustcloud\.com)$",
    re.I,
)
LOGIN_RE = re.compile(r"\b(sign in|log in|login|create an account|powered by safebase)\b", re.I)
HREF_RE = re.compile(r"""href\s*=\s*['"]([^"'#]+)['"]""", re.I)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")

# Path must say this is an AI instrument, not a generic trust page.
AI_PATH_RE = re.compile(
    r"responsible-ai|responsible_ai|responsible-scaling|ai-safety|ai_safety|"
    r"ai-governance|ai_governance|ai-principles|ethical-ai|model-?card|"
    r"system-?card|ai-transparency|transparency-report|"
    r"/ai-security(?:/|$)|/trust/ai(?:/|$)|/security/ai(?:/|$)|"
    r"/ai/security(?:/|$)|/ai/trust(?:/|$)|/ai/responsible|"
    r"our-approach-to-ai|approach-to-ai-safety",
    re.I,
)
# Soft /safety only if the page itself is clearly about AI systems.
AI_TEXT_RE = re.compile(
    r"\b(responsible ai|ai safety|ai governance|model card|system card|"
    r"responsible scaling|ai principles|artificial intelligence safety|"
    r"safety of (?:our )?(?:models|ai systems)|frontier (?:model|ai))\b",
    re.I,
)
GENERIC_PATH_RE = re.compile(
    r"/(trust|trust-center|security|privacy|status|subprocessors|dpa|"
    r"legal|terms|cookie|cookies|careers|blog|news|pricing|login|signin)(?:/|$)",
    re.I,
)

PATHS = (
    "/responsible-ai",
    "/responsible-ai/",
    "/ai-safety",
    "/ai-safety/",
    "/ai-governance",
    "/responsible-scaling-policy",
    "/model-card",
    "/system-card",
    "/ai-principles",
    "/ethical-ai",
    "/legal/responsible-ai",
    "/policies/responsible-ai",
    "/about/responsible-ai",
    "/company/responsible-ai",
    "/trust/responsible-ai",
    "/security/responsible-ai",
    "/trust/ai",
    "/security/ai",
)

# Extra first-party candidates to try. Still verified before filing.
CURATED_TRY = {
    "openai": [
        "https://openai.com/safety",
        "https://openai.com/safety-systems",
        "https://openai.com/index/gpt-4-system-card/",
    ],
    "anthropic": [
        "https://www.anthropic.com/responsible-scaling-policy",
        "https://www.anthropic.com/transparency",
        "https://www.anthropic.com/news/announcing-our-updated-responsible-scaling-policy",
    ],
    "cohere": [
        "https://cohere.com/responsible-use",
        "https://cohere.com/about/responsible-ai",
        "https://docs.cohere.com/docs/responsible-use",
    ],
    "mistral-ai": [
        "https://legal.mistral.ai/",
        "https://legal.mistral.ai/ai-governance/models",
        "https://mistral.ai/news/our-approach-to-ai-safety",
        "https://mistral.ai/safety",
        "https://legal.mistral.ai/terms/usage-policy",
    ],
    "xai": [
        "https://x.ai/safety",
        "https://data.x.ai/2026-04-07-grok-4-20-model-card.pdf",
    ],
    "sap": [
        "https://www.sap.com/products/artificial-intelligence/ai-ethics.html",
    ],
    "gitlab": [
        "https://about.gitlab.com/ai-transparency-center/",
    ],
    "palo-alto-networks": [
        "https://www.paloaltonetworks.com/legal-notices/trust-center/ai",
    ],
    "figma": [
        "https://www.figma.com/ai/our-approach/",
    ],
    "vanta": [
        "https://www.vanta.com/responsible-ai",
        "https://www.vanta.com/resources/ai-principles",
    ],
    "hugging-face": [
        "https://huggingface.co/huggingface/blog/ethical-ai",
    ],
    "stability-ai": [
        "https://stability.ai/safety",
        "https://stability.ai/responsible-ai",
        "https://stability.ai/news-updates/stability-ais-annual-integrity-transparency-report",
        "https://stability.ai/child-safety",
    ],
    "elevenlabs": [
        "https://elevenlabs.io/safety",
        "https://elevenlabs.io/responsible-ai",
        "https://elevenlabs.io/ai-transparency",
    ],
    "grammarly": [
        "https://www.grammarly.com/responsible-ai",
        "https://www.grammarly.com/ai-principles",
    ],
    "scale-ai": [
        "https://scale.com/legal/responsible-ai",
        "https://scale.com/responsible-ai",
    ],
    "writer": [
        "https://writer.com/responsible-ai",
        "https://writer.com/blog/responsible-ai",
        "https://writer.com/legal/global-ai-regulation/",
    ],
    "synthesia": [
        "https://www.synthesia.io/responsible-ai",
        "https://www.synthesia.io/legal/responsible-ai",
    ],
    "harvey": [
        "https://www.harvey.ai/responsible-ai",
        "https://www.harvey.ai/legal/ai-policy",
    ],
    "workday": [
        "https://www.workday.com/en-us/why-workday/innovation/responsible-ai.html",
    ],
    "slack": [
        "https://slack.com/trust/data-management/responsible-ai",
        "https://slack.com/trust/responsible-ai",
        "https://slack.com/trust/ai-principles",
    ],
    "uipath": [
        "https://www.uipath.com/legal/trust-and-security/responsible-ai",
        "https://www.uipath.com/responsible-ai",
        "https://www.uipath.com/ai/responsibility",
    ],
    "intercom": [
        "https://www.intercom.com/legal/responsible-ai",
        "https://www.intercom.com/help/en/articles/responsible-ai",
    ],
    "gong": [
        "https://www.gong.io/responsible-ai",
        "https://www.gong.io/the-edge/responsible-ai-approach-at-gong/",
    ],
    "clickup": [
        "https://clickup.com/legal/responsible-ai",
    ],
    "postman": [
        "https://www.postman.com/legal/responsible-ai/",
    ],
    "miro": [
        "https://miro.com/legal/responsible-ai/",
        "https://miro.com/ai/principles/",
        "https://miro.com/ai-trust/",
    ],
    "samsara": [
        "https://www.samsara.com/legal/responsible-ai",
    ],
    "workato": [
        "https://www.workato.com/legal/responsible-ai",
    ],
    "anysphere": [
        "https://cursor.com/responsible-ai",
    ],
    "microsoft": [
        "https://www.microsoft.com/en-us/ai/responsible-ai",
        "https://www.microsoft.com/en-us/ai/principles-and-approach",
    ],
    "google": [
        "https://cloud.google.com/responsible-ai",
    ],
    "amazon": [
        "https://aws.amazon.com/ai/responsible-ai/",
        "https://aws.amazon.com/ai/responsible-ai/policy/",
    ],
    "ibm": [
        "https://www.ibm.com/trust/responsible-technology",
        "https://www.ibm.com/trust/responsible-ai",
    ],
    "nvidia": [
        "https://www.nvidia.com/en-us/ai-trust-center/",
        "https://www.nvidia.com/en-us/ai-trust-center/trustworthy-ai/",
    ],
    "meta": [
        "https://ai.meta.com/static-resource/responsible-use-guide/",
        "https://ai.meta.com/responsible-ai/",
    ],
    "ai21": [
        "https://docs.ai21.com/docs/responsible-use-1",
        "https://www.ai21.com/research/ai-code-of-conduct/",
    ],
    "allen-institute-for-ai": [
        "https://allenai.org/responsible-use",
        "https://allenai.org/research-principles",
    ],
    "bria-ai": [
        "https://bria.ai/responsible-ai",
    ],
    "anam": [
        "https://anam.ai/ai-governance",
    ],
    "creatify-ai": [
        "https://creatify.ai/ai-ethics",
    ],
    "ellipsis-health": [
        "https://ellipsishealth.com/ethical-ai/",
    ],
    "alex": [
        "https://www.alex.com/ethical-ai",
    ],
    "midjourney": [
        "https://www.midjourney.com/responsible-ai",
        "https://docs.midjourney.com/docs/ai-safety",
    ],
    "character-ai": [
        "https://character.ai/safety",
        "https://character.ai/responsible-ai",
    ],
    "perplexity-ai": [
        "https://www.perplexity.ai/hub/legal/responsible-ai",
        "https://www.perplexity.ai/safety",
    ],
    "fireworks-ai": [
        "https://fireworks.ai/responsible-ai",
    ],
    "together-ai": [
        "https://www.together.ai/responsible-ai",
        "https://docs.together.ai/docs/safety",
    ],
    "runway": [
        "https://runwayml.com/responsible-ai",
        "https://runwayml.com/safety",
    ],
    "webflow": [
        "https://webflow.com/legal/responsible-ai",
        "https://webflow.com/ai/our-approach",
    ],
    "sierra": [
        "https://sierra.ai/responsible-ai",
    ],
    "groq": [
        "https://groq.com/responsible-ai",
        "https://console.groq.com/docs/legal/ai-policy",
        "https://groq.com/legal/ai-policy",
    ],
    "glean": [
        "https://www.glean.com/responsible-ai",
    ],
    "abridge": [
        "https://www.abridge.com/responsible-ai",
    ],
    "alphasense": [
        "https://www.alpha-sense.com/responsible-ai",
    ],
    "dialpad": [
        "https://www.dialpad.com/legal/responsible-ai/",
        "https://www.dialpad.com/responsible-ai",
        "https://www.dialpad.com/dialpad-ai/ai-principles/",
    ],
    "automation-anywhere": [
        "https://www.automationanywhere.com/responsible-ai",
    ],
    "checkr": [
        "https://checkr.com/responsible-ai",
    ],
    "clay": [
        "https://www.clay.com/responsible-ai",
    ],
    "dbt-labs": [
        "https://www.getdbt.com/legal/responsible-ai",
    ],
    "cloudflare": [
        "https://www.cloudflare.com/responsible-ai-principles/",
        "https://www.cloudflare.com/trust-hub/responsible-ai/",
    ],
    "inflection": [
        "https://inflection.ai/frontier-safety",
        "https://inflection.ai/safety",
        "https://inflection.ai/transparency-and-content-moderation",
    ],
    "tencent": [
        "https://www.tencent.com/our-actions/social/tencent-responsible-ai-principles/",
    ],
    "heygen": [
        "https://www.heygen.com/ethics",
        "https://www.heygen.com/trust-and-safety",
    ],
    "deepseek": [
        "https://cdn.deepseek.com/policies/en-US/model-algorithm-disclosure.html",
        "https://fe-static.deepseek.com/chat/transparency/deepseek-v3.2-model-card-0414-CN.pdf",
    ],
    "bytedance": [
        "https://seed.bytedance.com/en/direction/responsible_ai",
        "https://seed.bytedance.com/transparency",
    ],
    "apple": [
        "https://machinelearning.apple.com/research/apple-foundation-models-tech-report-2025",
    ],
    "notion": [
        "https://www.notion.com/help/ai-safety",
        "https://www.notion.so/help/ai-safety",
    ],
    "xiaomi": [
        "https://trust.mi.com/pdf/Xiaomi_Trustworthy_AI_White_Paper_2021_EN.pdf",
    ],
    "black-forest-labs": [
        "https://bfl.ai/legal/responsible-ai-development-policy",
        "https://bfl.ai/transparency",
    ],
    "alibaba": [
        "https://static.alibabagroup.com/manual-upload/Alibaba-Al-for-Good-Action-Report-2025.pdf",
    ],
    "reka": [
        "https://reka.ai/legal/responsibleai-ethics",
    ],
    "baidu": [
        "https://ai.baidu.com/ai-doc/REFERENCE/xk3dwjgfe",
    ],
    "suno": [
        "https://suno.com/safety",
    ],
    "seekr": [
        "https://www.seekr.com/responsible-ai-for-enterprises/",
    ],
}


def host_of(url: str) -> str:
    try:
        host = (urlparse(url).hostname or "").lower().removeprefix("www.")
        return host
    except Exception:
        return ""


def first_party(url: str, domain: str) -> bool:
    host = host_of(url)
    own = (domain or "").lower().removeprefix("www.")
    if not host or not own:
        return False
    if VENDOR_HOST_RE.search(host):
        return False
    if host == own or host.endswith("." + own):
        return True
    # docs/research/safety/trust on a related official host the company already uses
    own_root = own.split(".")[0]
    if own_root and own_root in host.split(".") and host.endswith(own.split(".", 1)[-1] if "." in own else own):
        return True
    return False


def path_of(url: str) -> str:
    try:
        return urlparse(url).path or ""
    except Exception:
        return ""


def strip_tags(html: str) -> str:
    return unescape(TAG_RE.sub(" ", html or "")).replace("\xa0", " ")


def looks_ai_instrument(url: str, title: str, text: str) -> bool:
    path = path_of(url)
    if GENERIC_PATH_RE.search(path) and not AI_PATH_RE.search(path):
        return False
    blob = f"{title} {text[:4000]}"
    # Path guess is not enough: require the page itself to name an AI instrument.
    if not AI_TEXT_RE.search(blob) and not AI_TEXT_RE.search(title or ""):
        return False
    if AI_PATH_RE.search(path) or AI_PATH_RE.search(url):
        return True
    if re.search(r"/(safety|transparency)(?:/|$)", path, re.I) and AI_TEXT_RE.search(blob):
        return True
    return False


def reject_wall(title: str, text: str, status: int) -> bool:
    if status in (401, 403):
        return True
    if LOGIN_RE.search(title or "") or LOGIN_RE.search((text or "")[:1500]):
        return True
    return False


def get(url: str) -> dict:
    rec = crawl.fetch(url, max_body=48000)
    html = rec.get("body") or ""
    title_m = TITLE_RE.search(html)
    h1_m = H1_RE.search(html)
    title = unescape(TAG_RE.sub("", (title_m.group(1) if title_m else "")).strip())
    h1 = unescape(TAG_RE.sub("", (h1_m.group(1) if h1_m else "")).strip())
    text = strip_tags(html)
    return {
        "ok": bool(rec.get("ok")),
        "status": rec.get("status") or 0,
        "final_url": rec.get("final_url") or url,
        "title": title,
        "h1": h1,
        "text": text,
        "html": html,
    }


def candidates_for(row: dict) -> list[str]:
    domain = (row.get("domain") or "").strip()
    slug = row.get("slug") or ""
    seen = []
    out = []

    def add(url: str) -> None:
        if not url or url in seen:
            return
        seen.append(url)
        out.append(url)

    for extra in CURATED_TRY.get(slug, []):
        add(extra)
    if domain:
        for path in PATHS:
            add(f"https://{domain}{path}")
            if not domain.startswith("www."):
                add(f"https://www.{domain}{path}")
    return out


def accept(row: dict, rec: dict) -> str:
    if not rec.get("ok") or rec.get("status") != 200:
        return ""
    final = rec.get("final_url") or ""
    if not first_party(final, row.get("domain") or ""):
        return ""
    if reject_wall(rec.get("title") or "", rec.get("text") or "", rec.get("status") or 0):
        return ""
    if not looks_ai_instrument(final, rec.get("title") or "", rec.get("text") or ""):
        return ""
    text = rec.get("text") or ""
    title = rec.get("title") or ""
    if len(text) < 400:
        return ""
    # Soft-404 / homepage bounce
    path = path_of(final).rstrip("/")
    if path in ("", "/"):
        return ""
    if re.search(r"\b(page not found|not found|404|just a moment|attention required)\b", title, re.I):
        return ""
    # Next.js / marketing shell that kept the homepage title
    if title.count("|") >= 1 and re.search(r"the best way to|connect your apps|leading enterprise", title, re.I):
        return ""
    # Hugging Face user/org pages are not first-party AI files
    if "huggingface.co" in host_of(final) and re.search(r"\([A-Z]{2,} .+\)", title):
        return ""
    return final


def hrefs(html: str, base: str) -> list[str]:
    out = []
    for m in HREF_RE.finditer(html or ""):
        href = m.group(1).strip()
        if href.startswith("mailto:") or href.startswith("javascript:"):
            continue
        out.append(urljoin(base, href))
    return out


def main() -> int:
    data = json.loads((SITE / "data.json").read_text())
    # Import membership from the published register using the same JS rules via a thin port.
    sys.path.insert(0, str(SITE))
    # Reuse the already-selected list by running the node helper would be heavier; port the rules.
    from pathlib import Path as P
    lib = (SITE / "lib.js").read_text()
    # Load via a small node dump if needed — instead filter with python clone already in tests.
    companies = data["companies"]

    # Ask node for the AITI slugs so membership cannot drift.
    import subprocess
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
    by_slug = {c["slug"]: c for c in companies}
    rows = [by_slug[s] for s in slugs if s in by_slug]

    filed = {}
    notes = []

    # Pass 1: follow AI hrefs already published on official pages we have.
    official = []
    for row in rows:
        for key in ("trust_url", "final_url"):
            if row.get(key):
                official.append((row, row[key]))
        inst = row.get("instruments") or {}
        for k in ("trust", "security"):
            rec = inst.get(k)
            url = rec.get("url") if isinstance(rec, dict) else rec
            if url:
                official.append((row, url))

    print(f"pass1 official pages {len(official)}", flush=True)
    seen_official = set()
    with ThreadPoolExecutor(max_workers=10) as pool:
        futs = {}
        for row, url in official:
            if (row["slug"], url) in seen_official:
                continue
            seen_official.add((row["slug"], url))
            futs[pool.submit(get, url)] = (row, url)
        for fut in as_completed(futs):
            row, src = futs[fut]
            try:
                rec = fut.result()
            except Exception as exc:
                notes.append(f"{row['slug']} official {src} err {exc}")
                continue
            if not rec.get("ok"):
                continue
            for href in hrefs(rec.get("html") or "", rec.get("final_url") or src):
                if not first_party(href, row.get("domain") or ""):
                    continue
                if not AI_PATH_RE.search(href):
                    continue
                if row["slug"] in filed:
                    continue
                try:
                    hit = get(href)
                except Exception:
                    continue
                final = accept(row, hit)
                if final:
                    filed[row["slug"]] = {
                        "url": final,
                        "host": host_of(final),
                        "title": hit.get("title") or "",
                        "via": "official-href",
                        "from": src,
                    }
                    print("filed", row["slug"], final, "via href", src, flush=True)

    # Pass 2: probe conservative paths / curated first-party candidates.
    jobs = []
    for row in rows:
        if row["slug"] in filed:
            continue
        for url in candidates_for(row):
            jobs.append((row, url))
    print(f"pass2 probes {len(jobs)} remaining {len(rows) - len(filed)}", flush=True)

    with ThreadPoolExecutor(max_workers=12) as pool:
        futs = {pool.submit(get, url): (row, url) for row, url in jobs}
        for fut in as_completed(futs):
            row, url = futs[fut]
            if row["slug"] in filed:
                continue
            try:
                rec = fut.result()
            except Exception as exc:
                notes.append(f"{row['slug']} {url} err {exc}")
                continue
            final = accept(row, rec)
            if final:
                filed[row["slug"]] = {
                    "url": final,
                    "host": host_of(final),
                    "title": rec.get("title") or "",
                    "via": "probe",
                    "from": url,
                }
                print("filed", row["slug"], final, flush=True)

    payload = {
        "generated_at": data.get("generated_at"),
        "rule": (
            "Probe only. The filed AITI page list is site/data/aiti-pages.json. "
            "Page fills only from a stored first-party AI-page URL. "
            "Generic trust/privacy/status pages do not count. "
            "No processors/evals/incidents invented."
        ),
        "curated": str(CURATED.relative_to(ROOT)),
        "count": len(filed),
        "pages": filed,
        "open": [r["slug"] for r in rows if r["slug"] not in filed],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote", OUT, "filed", len(filed), "open", len(payload["open"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
