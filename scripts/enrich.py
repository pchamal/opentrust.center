#!/usr/bin/env python3
"""Enrich opentrust.center with public, verifiable security facts. No fabrication."""
from __future__ import annotations

import hashlib
import os
import json
import re
import ssl
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import crawl  # noqa: E402

DATA = ROOT / "data"
CACHE = DATA / "cache"
SITE = ROOT / "site"
NOW_YEAR = 2026
UA = crawl.UA
WORKERS = 16
WIKI_WORKERS = 6
PROBE_BODY = 24576
TRUST_BODY = 196608

VENDOR_WORDS = re.compile(
    r"\b(safebase|safe base|vanta|conveyor|wolfia|drata|securitypal|"
    r"secureframe|whistic|sprinto|trustcloud|vendict)\b", re.I)
VENDOR_TITLE_TAIL = re.compile(r"\s*[|\-–—]\s*powered by\s+\w+\s*$", re.I)
JS_JUNK = re.compile(
    r"(manifestPreload|windowObject|function\s*\(|var\s+\w+\s*=|entry-trust)", re.I)
HREF_RE = re.compile(r"""href\s*=\s*['"]([^"'#]+)['"]""", re.I)
META_DESC_RE = re.compile(
    r"""<meta[^>]+(?:name|property)\s*=\s*['"](?:description|og:description)['"][^>]*>""", re.I)
META_CONTENT_RE = re.compile(r"""content\s*=\s*['"]([^'"]+)['"]""", re.I)
SEC_CONTACT = re.compile(r"(?im)^\s*Contact\s*:\s*(\S+)")
SEC_POLICY = re.compile(r"(?im)^\s*Policy\s*:\s*(\S+)")
SEC_EXPIRES = re.compile(r"(?im)^\s*Expires\s*:\s*(\S+)")
SEC_CANONICAL = re.compile(r"(?im)^\s*Canonical\s*:\s*(\S+)")
SEC_FIELD = re.compile(r"(?im)^\s*(Contact|Policy|Expires|Canonical)\s*:\s*\S+")
BOUNTY_PLATFORM_HOSTS = (
    "hackerone.com",
    "bugcrowd.com",
    "yeswehack.com",
    "intigriti.com",
)
ABOUT_FOUNDED = re.compile(
    r"\b(?:founded|established)\s+(?:in\s+)?(?:the\s+year\s+)?"
    r"(?:january|february|march|april|may|june|july|august|september|"
    r"october|november|december)?\s*,?\s*(19[7-9]\d|20[0-2]\d)\b", re.I)

CERT_RULES = [
    ("SOC 2 Type II", re.compile(r"\bSOC\s*2\s*Type\s*(?:II|2)\b", re.I), 10),
    ("SOC 2 Type I", re.compile(r"\bSOC\s*2\s*Type\s*(?:I|1)\b", re.I), 4),
    ("SOC 2", re.compile(r"\bSOC\s*2\b", re.I), 4),
    ("SOC 1 Type II", re.compile(r"\bSOC\s*1\s*Type\s*(?:II|2)\b", re.I), 4),
    ("SOC 1", re.compile(r"\bSOC\s*1\b", re.I), 4),
    ("SOC 3", re.compile(r"\bSOC\s*3\b", re.I), 4),
    ("ISO 27001", re.compile(r"\bISO(?:/IEC)?\s*27001\b", re.I), 10),
    ("ISO 27017", re.compile(r"\bISO(?:/IEC)?\s*27017\b", re.I), 4),
    ("ISO 27018", re.compile(r"\bISO(?:/IEC)?\s*27018\b", re.I), 4),
    ("ISO 27701", re.compile(r"\bISO(?:/IEC)?\s*27701\b", re.I), 6),
    ("ISO 42001", re.compile(r"\bISO(?:/IEC)?\s*42001\b", re.I), 6),
    ("AIUC-1", re.compile(r"\bAIUC-1\b", re.I), 8),
    ("ISO 22301", re.compile(r"\bISO(?:/IEC)?\s*22301\b", re.I), 4),
    ("ISO 9001", re.compile(r"\bISO\s*9001\b", re.I), 4),
    ("FedRAMP High", re.compile(r"\bFedRAMP\s+High\b", re.I), 12),
    ("FedRAMP Moderate", re.compile(r"\bFedRAMP\s+Moderate\b", re.I), 12),
    ("FedRAMP", re.compile(r"\bFedRAMP\b", re.I), 12),
    ("HIPAA", re.compile(r"\bHIPAA\b", re.I), 6),
    ("PCI DSS", re.compile(r"\bPCI[\s-]?DSS\b", re.I), 8),
    ("HITRUST", re.compile(r"\bHITRUST\b", re.I), 8),
    ("GDPR", re.compile(r"\bGDPR\b", re.I), 3),
    ("CCPA", re.compile(r"\bCCPA\b|\bCPRA\b", re.I), 3),
    ("CSA STAR", re.compile(r"\bCSA\s*STAR\b", re.I), 4),
    ("TISAX", re.compile(r"\bTISAX\b", re.I), 4),
    ("IRAP", re.compile(r"\bIRAP\b", re.I), 4),
    ("StateRAMP", re.compile(r"\bStateRAMP\b", re.I), 4),
    ("TX-RAMP", re.compile(r"\bTX-?RAMP\b", re.I), 4),
    ("Cyber Essentials", re.compile(r"\bCyber\s*Essentials(?:\s*Plus)?\b", re.I), 4),
    ("NIST 800-53", re.compile(r"\bNIST\s*800-53\b", re.I), 4),
    ("NIST CSF", re.compile(r"\bNIST\s*CSF\b", re.I), 4),
    ("CMMC", re.compile(r"\bCMMC\b", re.I), 8),
    ("C5", re.compile(r"\b(?:BSI\s+)?C5\b", re.I), 4),
    ("ISMAP", re.compile(r"\bISMAP\b", re.I), 4),
    ("SOX", re.compile(r"\bSarbanes[-\s]?Oxley\b", re.I), 4),
]
CERT_SUPERSEDE = {
    "SOC 2": ["SOC 2 Type II", "SOC 2 Type I"],
    "SOC 1": ["SOC 1 Type II"],
    "FedRAMP": ["FedRAMP High", "FedRAMP Moderate"],
}
CERT_WEIGHT = {n: w for n, _p, w in CERT_RULES}

PROCESSORS = [
    ("aws", "Amazon Web Services", "aws.amazon.com", [r"amazon web services", r"\bAWS\b"]),
    ("gcp", "Google Cloud", "cloud.google.com", [r"google cloud platform", r"google cloud", r"\bGCP\b"]),
    ("azure", "Microsoft Azure", "azure.microsoft.com", [r"microsoft azure", r"\bAzure\b"]),
    ("cloudflare", "Cloudflare", "cloudflare.com", [r"\bCloudflare\b"]),
    ("twilio", "Twilio", "twilio.com", [r"\bTwilio\b"]),
    ("stripe", "Stripe", "stripe.com", [r"\bStripe\b"]),
    ("sendgrid", "SendGrid", "sendgrid.com", [r"\bSendGrid\b"]),
    ("datadog", "Datadog", "datadoghq.com", [r"\bDatadog\b"]),
    ("snowflake", "Snowflake", "snowflake.com", [r"\bSnowflake\b"]),
    ("databricks", "Databricks", "databricks.com", [r"\bDatabricks\b"]),
    ("okta", "Okta", "okta.com", [r"\bOkta\b"]),
    ("salesforce", "Salesforce", "salesforce.com", [r"\bSalesforce\b"]),
    ("zendesk", "Zendesk", "zendesk.com", [r"\bZendesk\b"]),
    ("slack", "Slack", "slack.com", [r"\bSlack\b"]),
    ("github", "GitHub", "github.com", [r"\bGitHub\b"]),
    ("gitlab", "GitLab", "gitlab.com", [r"\bGitLab\b"]),
    ("pagerduty", "PagerDuty", "pagerduty.com", [r"\bPagerDuty\b"]),
    ("atlassian", "Atlassian", "atlassian.com", [r"\bAtlassian\b"]),
    ("workday", "Workday", "workday.com", [r"\bWorkday\b"]),
    ("hubspot", "HubSpot", "hubspot.com", [r"\bHubSpot\b"]),
    ("segment", "Twilio Segment", "segment.com", [r"Twilio Segment", r"Segment\.io", r"segment\.com"]),
    ("openai", "OpenAI", "openai.com", [r"\bOpenAI\b"]),
    ("anthropic", "Anthropic", "anthropic.com", [r"\bAnthropic\b"]),
    ("mongodb", "MongoDB", "mongodb.com", [r"\bMongoDB\b"]),
    ("elastic", "Elastic", "elastic.co", [r"Elastic Cloud", r"\bElasticsearch\b"]),
    ("fastly", "Fastly", "fastly.com", [r"\bFastly\b"]),
    ("akamai", "Akamai", "akamai.com", [r"\bAkamai\b"]),
    ("vercel", "Vercel", "vercel.com", [r"\bVercel\b"]),
    ("netlify", "Netlify", "netlify.com", [r"\bNetlify\b"]),
    ("auth0", "Auth0", "auth0.com", [r"\bAuth0\b"]),
    ("stitch", "Stitch", "stitchdata.com", [r"Stitch Data", r"stitchdata"]),
    ("fivetran", "Fivetran", "fivetran.com", [r"\bFivetran\b"]),
    ("looker", "Looker", "looker.com", [r"\bLooker\b"]),
    ("tableau", "Tableau", "tableau.com", [r"\bTableau\b"]),
    ("zoom", "Zoom", "zoom.us", [r"\bZoom\b"]),
    ("docusign", "DocuSign", "docusign.com", [r"\bDocuSign\b"]),
    ("intercom", "Intercom", "intercom.com", [r"\bIntercom\b"]),
    ("freshworks", "Freshworks", "freshworks.com", [r"\bFreshworks\b", r"\bFreshdesk\b"]),
    ("servicenow", "ServiceNow", "servicenow.com", [r"\bServiceNow\b"]),
    ("splunk", "Splunk", "splunk.com", [r"\bSplunk\b"]),
    ("newrelic", "New Relic", "newrelic.com", [r"\bNew Relic\b"]),
    ("sentry", "Sentry", "sentry.io", [r"\bSentry\b"]),
    ("honeycomb", "Honeycomb", "honeycomb.io", [r"\bHoneycomb\b"]),
    ("launchdarkly", "LaunchDarkly", "launchdarkly.com", [r"\bLaunchDarkly\b"]),
    ("amplitude", "Amplitude", "amplitude.com", [r"\bAmplitude\b"]),
    ("mixpanel", "Mixpanel", "mixpanel.com", [r"\bMixpanel\b"]),
    ("pendo", "Pendo", "pendo.io", [r"\bPendo\b"]),
    ("fullstory", "FullStory", "fullstory.com", [r"\bFullStory\b"]),
    ("recaptcha", "Google reCAPTCHA", "google.com", [r"\breCAPTCHA\b", r"\breCaptcha\b"]),
    ("mailchimp", "Mailchimp", "mailchimp.com", [r"\bMailchimp\b", r"\bMailChimp\b"]),
    ("messagebird", "MessageBird", "messagebird.com", [r"\bMessageBird\b"]),
    ("vonage", "Vonage", "vonage.com", [r"\bVonage\b"]),
    ("nylas", "Nylas", "nylas.com", [r"\bNylas\b"]),
    ("heroku", "Heroku", "heroku.com", [r"\bHeroku\b"]),
]
PROC_COMPILED = [(i, n, d, [re.compile(a, re.I) for a in al]) for i, n, d, al in PROCESSORS]

# Title hints only — years still come from Wikidata P571 after a website or title check.
WIKI_HINTS = {
    "1password": ["1Password"],
    "abnormal-ai": ["Abnormal Security"],
    "adobe": ["Adobe Inc."],
    "akamai": ["Akamai Technologies"],
    "amazon-web-services": ["Amazon Web Services"],
    "amplitude": ["Amplitude (company)"],
    "anysphere": ["Cursor (code editor)", "Anysphere"],
    "apple": ["Apple Inc."],
    "arctic-wolf": ["Arctic Wolf Networks"],
    "asana": ["Asana, Inc."],
    "attentive": ["Attentive (company)"],
    "bill": ["Bill.com"],
    "block": ["Block, Inc."],
    "box": ["Box, Inc."],
    "braze": ["Braze (company)"],
    "carta": ["Carta (software)"],
    "character-ai": ["Character.ai"],
    "check-point": ["Check Point"],
    "checkout": ["Checkout.com"],
    "confluent": ["Confluent (company)"],
    "elastic": ["Elastic NV"],
    "figma": ["Figma (software)"],
    "glean": ["Glean (company)"],
    "gong": ["Gong.io"],
    "grafana-labs": ["Grafana Labs"],
    "gusto": ["Gusto (company)"],
    "harness": ["Harness (company)"],
    "harvey": ["Harvey AI"],
    "hugging-face": ["Hugging Face"],
    "intercom": ["Intercom (company)"],
    "island": ["Island (browser)"],
    "lambda": ["Lambda (company)"],
    "meta": ["Meta Platforms"],
    "miro": ["Miro (collaboration platform)"],
    "mistral-ai": ["Mistral AI"],
    "mongodb": ["MongoDB Inc."],
    "monday": ["Monday.com"],
    "motive": ["Motive (company)"],
    "new-relic": ["New Relic"],
    "notion": ["Notion (productivity software)"],
    "okta": ["Okta, Inc."],
    "oracle": ["Oracle Corporation"],
    "palantir": ["Palantir Technologies"],
    "palo-alto-networks": ["Palo Alto Networks"],
    "pendo": ["Pendo.io"],
    "perplexity-ai": ["Perplexity AI"],
    "plaid": ["Plaid (company)"],
    "postman": ["Postman (API platform)"],
    "ramp": ["Ramp (company)"],
    "runway": ["Runway AI"],
    "scale-ai": ["Scale AI"],
    "slack": ["Slack (software)"],
    "snowflake": ["Snowflake Inc."],
    "stability-ai": ["Stability AI"],
    "stripe": ["Stripe, Inc."],
    "synthesia": ["Synthesia (company)"],
    "tenable": ["Tenable, Inc."],
    "together-ai": ["Together AI"],
    "unity": ["Unity Technologies"],
    "vanta": ["Vanta (company)", "Vanta"],
    "vast-data": ["VAST Data"],
    "workday": ["Workday, Inc."],
    "writer": ["Writer (company)"],
    "xai": ["SpaceXAI", "xAI"],
    "zoom": ["Zoom Communications"],
    "zoho": ["Zoho Corporation"],
    "google": ["Google"],
    "deel": ["Deel, Inc."],
    "celonis": ["Celonis"],
    "grafana-labs": ["Grafana Labs", "Grafana"],
    "miro": ["Miro (collaboration platform)"],
    "rippling": ["Rippling (company)", "Rippling"],
    "carta": ["Carta (software company)", "Carta (software)"],
    "postman": ["Postman, Inc.", "Postman (software)"],
    "fivetran": ["Fivetran"],
    "gong": ["Gong.io"],
    "webflow": ["Webflow"],
    "personio": ["Personio"],
    "freshworks": ["Freshworks"],
    "confluent": ["Confluent (company)"],
    "samsara": ["Samsara (company)"],
    "proofpoint": ["Proofpoint"],
    "rapid7": ["Rapid7"],
    "sailpoint": ["SailPoint"],
    "checkr": ["Checkr"],
    "talkdesk": ["Talkdesk"],
    "alphasense": ["AlphaSense"],
    "netskope": ["Netskope"],
    "abnormal-ai": ["Abnormal Security"],
    "arctic-wolf": ["Arctic Wolf Networks"],
    "dialpad": ["Dialpad"],
    "checkout": ["Checkout.com"],
    "clio": ["Clio (company)"],
    "collibra": ["Collibra"],
    "workato": ["Workato"],
    "benchling": ["Benchling"],
    "axonius": ["Axonius"],
    "harness": ["Harness (company)"],
    "dbt-labs": ["Dbt Labs", "dbt Labs"],
    "launchdarkly": ["LaunchDarkly"],
    "claroty": ["Claroty"],
    "amplitude": ["Amplitude (company)"],
    "braze": ["Braze (company)"],
}

ORG_QIDS = {
    "Q4830453", "Q783794", "Q891723", "Q6881511", "Q1058914",
    "Q18388277", "Q167037", "Q43229", "Q163740", "Q1668024",
    "Q1331793", "Q110763261", "Q2006873", "Q35127", "Q2659904",
}

LINK_HINTS = (
    ("subprocessors", re.compile(r"sub-?process|service-providers?", re.I)),
    ("dpa", re.compile(r"data-?processing|(/|\.)dpa\b", re.I)),
    ("privacy", re.compile(r"privacy", re.I)),
    ("status", re.compile(r"status", re.I)),
    ("bug_bounty", re.compile(
        r"bug-?bounty|responsible-?disclosure|vulnerability-?disclosure|"
        r"hackerone|bugcrowd|yeswehack|intigriti", re.I)),
    ("security_txt", re.compile(r"security\.txt", re.I)),
    ("security", re.compile(r"security", re.I)),
    ("trust", re.compile(r"trust", re.I)),
)

# First-party path variants that differ from the generic probe list. Still live-checked.
SPECIAL_URLS = {
    "stripe": [
        ("https://stripe.com/legal/service-providers", "subprocessors"),
        ("https://status.stripe.com", "status"),
        ("https://stripe.com/legal/dpa", "dpa"),
    ],
    "openai": [("https://status.openai.com", "status"),
               ("https://openai.com/policies/privacy-policy", "privacy")],
    "notion": [("https://www.notion.so/help/subprocessors", "subprocessors")],
    "databricks": [("https://www.databricks.com/legal/subprocessors", "subprocessors"),
                   ("https://status.databricks.com", "status")],
    "slack": [("https://slack.com/trust/compliance/subprocessors", "subprocessors"),
              ("https://status.slack.com", "status")],
    "atlassian": [("https://www.atlassian.com/legal/sub-processors", "subprocessors"),
                  ("https://status.atlassian.com", "status")],
    "salesforce": [("https://www.salesforce.com/company/legal/infrastructure-and-subprocessors/", "subprocessors")],
    "amazon-web-services": [("https://aws.amazon.com/compliance/sub-processors/", "subprocessors")],
    "google": [("https://cloud.google.com/terms/subprocessors", "subprocessors"),
               ("https://status.cloud.google.com", "status")],
    "github": [("https://docs.github.com/en/site-policy/privacy-policies/github-subprocessors-and-cookies", "subprocessors"),
               ("https://www.githubstatus.com", "status")],
    "gitlab": [("https://about.gitlab.com/privacy/subprocessors/", "subprocessors")],
    "okta": [("https://www.okta.com/legal/subprocessors/", "subprocessors")],
    "cloudflare": [("https://www.cloudflare.com/gdpr/subprocessors/", "subprocessors"),
                   ("https://www.cloudflarestatus.com", "status")],
    "twilio": [("https://www.twilio.com/legal/sub-processors", "subprocessors")],
    "snowflake": [("https://www.snowflake.com/legal/snowflake-subprocessors/", "subprocessors")],
    "zoom": [("https://www.zoom.com/en/trust/privacy/subprocessors/", "subprocessors")],
    "docusign": [("https://www.docusign.com/legal/subprocessors", "subprocessors")],
    "box": [("https://www.box.com/legal/subprocessors", "subprocessors")],
    "hubspot": [("https://legal.hubspot.com/sub-processors-page", "subprocessors")],
    "mongodb": [("https://www.mongodb.com/legal/sub-processors", "subprocessors")],
    "datadog": [("https://www.datadoghq.com/legal/subprocessors/", "subprocessors")],
    "adobe": [("https://www.adobe.com/privacy/sub-processors.html", "subprocessors")],
    "workday": [("https://www.workday.com/en-us/legal/subprocessors.html", "subprocessors")],
    "1password": [("https://1password.com/legal/subprocessors", "subprocessors")],
    "intercom": [("https://www.intercom.com/legal/subprocessors", "subprocessors")],
    "vercel": [("https://vercel.com/legal/dpa", "dpa"), ("https://www.vercel-status.com", "status")],
    "canva": [("https://www.canva.com/policies/subprocessors/", "subprocessors")],
    "microsoft": [("https://status.cloud.microsoft", "status")],
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def cache_path(url: str) -> Path:
    h = hashlib.sha256(url.encode()).hexdigest()[:20]
    return CACHE / "http" / f"{h}.json"


def load_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text())
    return default


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(path)


def host_of(url: str) -> str:
    return urlparse(url).netloc.lower().split(":")[0].removeprefix("www.")


def path_of(url: str) -> str:
    return urlparse(url).path or "/"


def registrable(host: str) -> str:
    host = host.lower().removeprefix("www.")
    parts = host.split(".")
    if len(parts) >= 3 and parts[-2] in {"co", "com", "org", "net", "ac", "gov"}:
        return ".".join(parts[-3:])
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return host


DOMAIN_ALIASES = {
    "zoom.us": ["zoom.com"],
    "google.com": ["about.google"],
    "deel.com": ["letsdeel.com"],
    "anysphere.co": ["cursor.com"],
    "1password.com": ["1password.io"],
    "alpha-sense.com": ["alpha-sense.com", "alphasense.com"],
    "x.ai": ["x.ai"],
    "meta.com": ["facebook.com"],
}

def hosts_for(company: dict) -> list[str]:
    out, seen = [], set()
    extras = []
    for raw in [company.get("domain"), *(company.get("aliases") or [])]:
        extras.extend(DOMAIN_ALIASES.get((raw or "").lower(), []))
    for raw in [company.get("domain"), *(company.get("aliases") or []), *extras]:
        if not raw:
            continue
        h = raw.lower().strip()
        h = h.removeprefix("http://").removeprefix("https://").removeprefix("www.").rstrip("/")
        if h and h not in seen:
            seen.add(h)
            out.append(h)
    return out


def strip_tags(html: str) -> str:
    return unescape(re.sub(r"\s+", " ", crawl.TAG_RE.sub(" ", html))).strip()


def extract_meta_desc(html: str) -> str:
    for m in META_DESC_RE.finditer(html or ""):
        cm = META_CONTENT_RE.search(m.group(0))
        if cm:
            return strip_tags(cm.group(1))[:400]
    return ""


def extract_hrefs(html: str, base: str) -> list[str]:
    seen, out = set(), []
    for m in HREF_RE.finditer(html or ""):
        raw = m.group(1).strip()
        if not raw or raw.startswith(("javascript:", "mailto:", "tel:", "data:")):
            continue
        absu = urljoin(base, raw)
        if absu.startswith("http") and absu not in seen:
            seen.add(absu)
            out.append(absu)
    return out[:400]


def looks_dead(title: str, text: str) -> bool:
    blob = f"{title} {text[:2500]}"
    return bool(crawl.SOFT_404.search(blob) or crawl.PARKING.search(blob))


def landed_on_home(requested: str, final_url: str) -> bool:
    req_path = (path_of(requested) or "/").rstrip("/")
    fin_path = (path_of(final_url) or "/").rstrip("/") or "/"
    if not req_path:
        return False
    if fin_path == "/" and req_path not in {"", "/"}:
        host = host_of(final_url)
        if host.startswith(("trust.", "security.", "compliance.", "status.", "assurance.")):
            return False
        return True
    return False


def fetch_uncached(url: str, max_body: int) -> dict:
    fetched = crawl.fetch(url, max_body=max_body)
    html = fetched.get("body") or ""
    title = crawl.extract_title(html) if html else ""
    text = strip_tags(html)[:30000] if html else ""
    rec = {
        "url": url,
        "ok": bool(fetched.get("ok")),
        "status": fetched.get("status") or 0,
        "final_url": fetched.get("final_url") or url,
        "title": title,
        "text": text,
        "meta": extract_meta_desc(html) if html else "",
        "hrefs": extract_hrefs(html, fetched.get("final_url") or url) if html else [],
        "ctype": (fetched.get("headers") or {}).get("content-type", ""),
        "fetched_at": utc_now(),
        "raw_head": "",
    }
    if "security.txt" in url.lower():
        rec["text"] = html[:8000]
        rec["raw_head"] = html[:4000]
    return rec


def fetch_cached(url: str, max_body: int = PROBE_BODY) -> dict:
    path = cache_path(url)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    rec = fetch_uncached(url, max_body)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{os.getpid()}.{time.time_ns()}.tmp")
    tmp.write_text(json.dumps(rec, ensure_ascii=False))
    tmp.replace(path)
    return rec


def http_get_json(url: str, timeout: int = 20):
    path = cache_path("json:" + url)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    try:
        req = Request(url, headers={"User-Agent": UA, "Accept": "application/json", "Accept-Language": "en"})
        with urlopen(req, timeout=timeout, context=ssl.create_default_context()) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
    except (HTTPError, URLError, TimeoutError, ssl.SSLError, OSError, json.JSONDecodeError, ValueError):
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))
    return data


def load_register() -> list[dict]:
    site = load_json(SITE / "data.json", {})
    companies = list(site.get("companies") or [])
    seeds = {}
    for src in (ROOT / "companies.json", ROOT / "extra-companies.json"):
        for row in load_json(src, []):
            seeds[row["slug"]] = row
    for row in companies:
        seed = seeds.get(row["slug"], {})
        row.setdefault("aliases", seed.get("aliases") or [])
        if not row.get("source"):
            row["source"] = seed.get("source")
    return companies


def wiki_api(params: dict):
    return http_get_json("https://en.wikipedia.org/w/api.php?" + urlencode(params))


def wikidata_api(params: dict):
    return http_get_json("https://www.wikidata.org/w/api.php?" + urlencode(params))


def parse_p571(claims: dict):
    for stmt in claims.get("P571") or []:
        val = ((stmt.get("mainsnak") or {}).get("datavalue") or {}).get("value") or {}
        time = val.get("time") if isinstance(val, dict) else None
        if not time:
            continue
        m = re.search(r"([12]\d{3})", time)
        if m:
            year = int(m.group(1))
            if 1600 <= year <= NOW_YEAR:
                return year
    return None


def parse_p856(claims: dict) -> list[str]:
    out = []
    for stmt in claims.get("P856") or []:
        val = ((stmt.get("mainsnak") or {}).get("datavalue") or {}).get("value")
        if isinstance(val, str) and val.startswith("http"):
            out.append(val)
    return out


def parse_p31(claims: dict) -> list[str]:
    out = []
    for stmt in claims.get("P31") or []:
        val = ((stmt.get("mainsnak") or {}).get("datavalue") or {}).get("value") or {}
        if isinstance(val, dict) and val.get("id"):
            out.append(val["id"])
    return out


DOMAIN_EQUIV = {
    "zoom.us": {"zoom.com"},
    "google.com": {"about.google"},
    "anysphere.co": {"anysphere.inc", "cursor.com"},
    "gomotive.com": {"keeptruckin.com"},
    "guild.com": {"guildeducation.com"},
}


def website_matches(urls: list[str], hosts: list[str]) -> bool:
    hostset, regs = set(hosts), {registrable(h) for h in hosts}
    extra = set()
    for h in list(hostset):
        extra |= DOMAIN_EQUIV.get(h, set())
    hostset |= extra
    regs |= {registrable(h) for h in extra}
    for u in urls:
        h = host_of(u)
        if not h:
            continue
        if h in hostset or registrable(h) in regs:
            return True
        for known in hostset:
            if h.endswith("." + known) or known.endswith("." + h):
                return True
    return False


def title_close(wiki_title: str, name: str) -> bool:
    a = re.sub(r"\s*\([^)]*\)\s*", " ", wiki_title or "").strip().lower()
    b = name.strip().lower()
    if not a or not b:
        return False
    if a == b or a.startswith(b + ",") or a.startswith(b + " "):
        return True
    return b.startswith(a) and len(a) >= 4


def extract_certs(blob: str) -> list[str]:
    if not blob:
        return []
    found, seen = [], set()
    for name, pat, _w in CERT_RULES:
        if name not in seen and pat.search(blob):
            found.append(name)
            seen.add(name)
    out = []
    for name in found:
        supers = CERT_SUPERSEDE.get(name)
        if supers and any(s in seen for s in supers):
            continue
        out.append(name)
    return out


def cert_score(certs: list[str]) -> int:
    return min(40, sum(CERT_WEIGHT.get(c, 4) for c in certs))


def extract_processors(text: str) -> list[str]:
    hits, seen = [], set()
    for pid, _n, _d, pats in PROC_COMPILED:
        if any(p.search(text or "") for p in pats) and pid not in seen:
            seen.add(pid)
            hits.append(pid)
    return hits


def is_subprocessor_page(url: str, title: str, text: str) -> bool:
    blob = f"{url} {title} {text[:5000]}".lower()
    return bool(re.search(r"sub-?\s*process", blob))


def is_security_txt_path(url: str) -> bool:
    """RFC 9116 lives at /.well-known/security.txt or /security.txt. Not /security."""
    return "security.txt" in path_of(url or "").lower()


def is_valid_security_txt(text: str, ctype: str) -> bool:
    """RFC-shaped: a Contact, Policy, Expires, or Canonical field. Not an HTML page."""
    if not text or not str(text).strip():
        return False
    head = str(text)[:8000]
    stripped = head.lstrip()
    low = stripped.lower()
    if low.startswith("<script") or low.startswith("(function"):
        return False
    htmlish = "<html" in low or "<!doctype html" in low
    if htmlish and ("<body" in low or "<nav" in low or "<header" in low):
        return False
    if "html" in (ctype or "").lower() and htmlish:
        return False
    return bool(SEC_FIELD.search(head))


def classify_probe(url: str, rec: dict):
    if not rec.get("ok") or rec.get("status") != 200:
        return None
    title, text = rec.get("title") or "", rec.get("text") or ""
    final = rec.get("final_url") or url
    if looks_dead(title, text):
        return None
    if landed_on_home(url, final) and "status." not in host_of(url):
        return None
    path, host = path_of(final).lower(), host_of(final)
    low = f"{title} {text[:3500]} {path} {host}".lower()
    if "session_sync" in (final or "").lower() or "/signin" in path or host.startswith("app."):
        if "sub-process" in path or "subprocessor" in path:
            return None
    if is_security_txt_path(final) or is_security_txt_path(url):
        raw = rec.get("raw_head") or text
        return "security_txt" if is_valid_security_txt(raw, rec.get("ctype") or "") else None
    if re.search(r"sub-?process|service-providers?", path) and (
        is_subprocessor_page(final, title, text) or re.search(r"sub-?process", text[:6000], re.I)
    ):
        return "subprocessors"
    if re.search(r"(data-processing|/dpa\b|/dpa/)", path) or re.search(r"\bdpa\b", title, re.I):
        if re.search(r"data processing|sub-process|\bdpa\b", low):
            return "dpa"
    if host.startswith("status.") or path.rstrip("/") == "/status" or re.search(
        r"\b(status page|system status|service status)\b", title, re.I
    ):
        if re.search(r"status|uptime|incident|operational", low):
            return "status"
    if re.search(r"bug-?bounty|responsible-?disclosure|vulnerability-?disclosure", path) or re.search(
        r"\b(bug bounty|responsible disclosure|vulnerability disclosure)\b", title, re.I
    ):
        return "bug_bounty"
    if "privacy" in path or re.search(r"privacy policy", title, re.I):
        if "privacy" in low:
            return "privacy"
    if host.startswith("trust.") or "trust-center" in path or path.rstrip("/") in {"/trust", "/trust-center"}:
        return "trust"
    if host.startswith("security.") or path.rstrip("/") in {"/security", "/docs/security"}:
        return "security"
    return None


def probe_urls_for(company: dict) -> list[tuple[str, str]]:
    pairs, seen = [], set()

    def add(url: str, hint: str) -> None:
        u = url.rstrip("/")
        key = u.lower()
        if key not in seen:
            seen.add(key)
            pairs.append((u, hint))

    for domain in hosts_for(company)[:2]:
        add(f"https://{domain}/.well-known/security.txt", "security_txt")
        add(f"https://{domain}/security.txt", "security_txt")
        add(f"https://{domain}/privacy", "privacy")
        add(f"https://{domain}/privacy-policy", "privacy")
        add(f"https://{domain}/legal/privacy", "privacy")
        add(f"https://{domain}/subprocessors", "subprocessors")
        add(f"https://{domain}/sub-processors", "subprocessors")
        add(f"https://{domain}/legal/subprocessors", "subprocessors")
        add(f"https://{domain}/legal/sub-processors", "subprocessors")
        add(f"https://{domain}/legal/service-providers", "subprocessors")
        add(f"https://{domain}/dpa", "dpa")
        add(f"https://{domain}/legal/dpa", "dpa")
        add(f"https://{domain}/legal/data-processing-addendum", "dpa")
        add(f"https://{domain}/data-processing-addendum", "dpa")
        add(f"https://status.{domain}", "status")
        add(f"https://{domain}/status", "status")
        add(f"https://{domain}/bug-bounty", "bug_bounty")
        add(f"https://{domain}/responsible-disclosure", "bug_bounty")
        add(f"https://{domain}/security/responsible-disclosure", "bug_bounty")
        add(f"https://{domain}/vulnerability-disclosure", "bug_bounty")
        add(f"https://{domain}/security", "security")
        add(f"https://{domain}/trust", "trust")
    trust = company.get("trust_url") or ""
    if trust:
        th = host_of(trust)
        if th:
            add(f"https://{th}/subprocessors", "subprocessors")
            add(f"https://{th}/sub-processors", "subprocessors")
    for url, hint in SPECIAL_URLS.get(company["slug"], []):
        add(url, hint)
    return pairs


def accept_link(kind: str, url: str, rec: dict) -> bool:
    classified = classify_probe(url, rec)
    if classified == kind:
        return True
    if kind in {"trust", "security"} and rec.get("ok") and rec.get("status") == 200:
        if looks_dead(rec.get("title") or "", rec.get("text") or ""):
            return False
        return not landed_on_home(url, rec.get("final_url") or url)
    return False


def field_url(val: str) -> str:
    """HTTP value from a security.txt field. Strip HTML tails. Do not invent."""
    val = (val or "").strip()
    val = re.sub(r"<[^>]+>.*$", "", val).strip()
    val = val.rstrip(".,;)]>")
    return val


def bounty_from_security_txt(text: str):
    for pat in (SEC_POLICY, SEC_CONTACT):
        for m in pat.finditer(text or ""):
            val = field_url(m.group(1))
            if val.startswith("http") and re.search(
                r"hackerone|bugcrowd|yeswehack|intigriti|bug-?bounty|\bbounty\b|"
                r"responsible-?disclosure|vulnerabilit|/\bvdp\b|\bvdp/|psirt|"
                r"security-disclosure|disclosure-policy",
                val, re.I,
            ):
                return val
    return None


def is_bounty_platform_host(url: str) -> bool:
    h = host_of(url)
    return any(h == b or h.endswith("." + b) for b in BOUNTY_PLATFORM_HOSTS)


def is_first_party_url(url: str, company: dict) -> bool:
    h = host_of(url)
    if not h:
        return False
    for known in hosts_for(company):
        if h == known or h.endswith("." + known) or known.endswith("." + h):
            return True
        if registrable(h) == registrable(known):
            return True
    return False


def company_path_token(company: dict) -> list[str]:
    tokens = []
    slug = (company.get("slug") or "").lower().replace("-", "")
    if len(slug) >= 3:
        tokens.append(slug)
    host = host_of("https://" + (company.get("domain") or ""))
    sld = host.split(".")[0] if host else ""
    if len(sld) >= 3 and sld not in tokens:
        tokens.append(sld)
    name = re.sub(r"[^a-z0-9]+", "", (company.get("name") or "").lower())
    if len(name) >= 3 and name not in tokens:
        tokens.append(name)
    return tokens


def is_first_party_or_branded_bounty(url: str, company: dict) -> bool:
    if not (url or "").startswith("http"):
        return False
    if is_first_party_url(url, company):
        return True
    if not is_bounty_platform_host(url):
        return False
    path = path_of(url).lower().replace("-", "").replace("_", "")
    return any(t in path for t in company_path_token(company))


def accept_security_txt(url: str, rec: dict) -> str | None:
    """Live 200 + RFC-shaped body + security.txt path. A /security page is not enough."""
    if not rec.get("ok") or rec.get("status") != 200:
        return None
    final = rec.get("final_url") or url
    raw = rec.get("raw_head") or rec.get("text") or ""
    if not (is_security_txt_path(final) or is_security_txt_path(url)):
        return None
    if not is_valid_security_txt(raw, rec.get("ctype") or ""):
        return None
    if looks_dead(rec.get("title") or "", rec.get("text") or ""):
        return None
    if landed_on_home(url, final):
        return None
    if is_security_txt_path(final):
        return final
    if is_security_txt_path(url):
        return url
    return None


def security_txt_probe_urls(company: dict, *, well_known_only: bool = False) -> list[str]:
    out, seen = [], set()

    def add(u: str) -> None:
        key = u.lower()
        if key not in seen:
            seen.add(key)
            out.append(u)

    for host in hosts_for(company):
        add(f"https://{host}/.well-known/security.txt")
        if not host.startswith("www."):
            add(f"https://www.{host}/.well-known/security.txt")
        if well_known_only:
            continue
        add(f"https://{host}/security.txt")
        if not host.startswith("www."):
            add(f"https://www.{host}/security.txt")
    return out


def optional_links_from_security_txt(text: str, company: dict, links: dict) -> dict:
    """Contact/Policy HTTP URLs already in the file, first-party or branded bounty host."""
    extras = {}
    if not links.get("bug_bounty"):
        bounty = bounty_from_security_txt(text)
        if bounty and is_first_party_or_branded_bounty(bounty, company):
            extras["bug_bounty"] = bounty
    if not links.get("security"):
        for m in SEC_CONTACT.finditer(text or ""):
            val = field_url(m.group(1))
            if not val.startswith("http"):
                continue
            if not is_first_party_url(val, company):
                continue
            path = path_of(val).rstrip("/")
            if path in {"", "/"}:
                continue
            if re.search(r"(contact-us|/contact)$|my-settings|login|signin", path, re.I):
                continue
            extras["security"] = val
            break
    return extras


def disclosure_tier_for(row: dict, score: int) -> str:
    was = ((row.get("disclosure") or {}).get("tier") or "silent")
    if was == "silent" and not row.get("found"):
        return "silent"
    if score >= 90:
        return "complete"
    if score >= 70:
        return "substantial"
    if score >= 40:
        return "on-file"
    return "thin"


def apply_security_txt_to_row(row: dict, url: str) -> bool:
    """File the security.txt URL. +6 only when bounty had not already paid disclosure."""
    links = dict(row.get("links") or {})
    if links.get("security_txt"):
        return False
    links["security_txt"] = url
    row["links"] = links
    disc = dict(row.get("disclosure") or {})
    factors = dict(disc.get("factors") or {})
    if factors.get("disclosure") or links.get("bug_bounty"):
        disc["factors"] = factors
        row["disclosure"] = disc
        return True
    factors["disclosure"] = 6
    score = min(100, int(disc.get("score") or 0) + 6)
    disc["score"] = score
    disc["tier"] = disclosure_tier_for(row, score)
    disc["factors"] = factors
    row["disclosure"] = disc
    return True


def apply_optional_txt_links(row: dict, extras: dict) -> None:
    """Store first-party Contact/Policy URLs. Do not add a second disclosure point."""
    if not extras:
        return
    links = dict(row.get("links") or {})
    for key in ("bug_bounty", "security"):
        url = extras.get(key)
        if url and not links.get(key):
            links[key] = url
    row["links"] = links


def clerk_summary(found: bool, certs: list[str], old: str, page_text: str) -> str:
    if VENDOR_WORDS.search(old or "") or JS_JUNK.search(old or ""):
        old = ""
    if not found:
        return ""
    if certs:
        shown = ", ".join(certs[:8])
        more = " and others" if len(certs) > 8 else ""
        return f"Public trust center. On file: {shown}{more}."
    if old and not VENDOR_WORDS.search(old) and not JS_JUNK.search(old) and 40 <= len(old) <= 280:
        return re.sub(r"\s+", " ", old).strip()[:240]
    if page_text and not VENDOR_WORDS.search(page_text) and not JS_JUNK.search(page_text):
        m = re.search(r"([^.?!]{40,220}[.?!])", page_text)
        if m and re.search(r"trust|security|privacy|compliance", m.group(1), re.I):
            return m.group(1).strip()
    return "Public trust center on file."


def score_row(found: bool, certs: list[str], links: dict, founded_year):
    score = 20 if found else 0
    score += cert_score(certs)
    if links.get("dpa"):
        score += 8
    if links.get("subprocessors"):
        score += 8
    if links.get("status"):
        score += 6
    if links.get("bug_bounty") or links.get("security_txt"):
        score += 6
    if links.get("privacy"):
        score += 6
    if founded_year:
        score += min(10, (NOW_YEAR - founded_year) // 2)
    score = min(100, score)
    if not found:
        return score, "silent"
    if score >= 90:
        return score, "complete"
    if score >= 70:
        return score, "substantial"
    if score >= 40:
        return score, "on-file"
    return score, "thin"


def chunked(items, n):
    for i in range(0, len(items), n):
        yield items[i:i + n]


def clean_title(title: str, company_name: str = "") -> str:
    t = VENDOR_TITLE_TAIL.sub("", title or "").strip()
    t = re.sub(r"\s*[|\-–—]\s*Powered by \w+\s*$", "", t, flags=re.I)
    t = re.sub(r"(?i)\s*[|\-–—]?\s*powered by\s+\w+", "", t).strip(" |:-")
    vendors = {"vanta", "safebase", "conveyor", "wolfia", "drata", "securitypal", "secureframe", "whistic"}
    low = t.lower().strip()
    cname = (company_name or "").lower()
    if low in vendors and low not in cname:
        return ""
    return t


def resolve_founding_years(companies: list[dict], log: list[str]) -> dict:
    title_to_slugs = defaultdict(list)
    for c in companies:
        titles = [c["name"], *WIKI_HINTS.get(c["slug"], [])]
        seen = set()
        for t in titles:
            if t.lower() not in seen:
                seen.add(t.lower())
                title_to_slugs[t].append(c["slug"])
    qid_by_title, title_canon = {}, {}
    all_titles = list(title_to_slugs)
    print(f"  Wikipedia titles to resolve: {len(all_titles)}", flush=True)
    for batch in chunked(all_titles, 40):
        data = wiki_api({
            "action": "query", "prop": "pageprops", "ppprop": "wikibase_item",
            "redirects": "1", "titles": "|".join(batch), "format": "json",
        })
        if not data:
            log.append(f"Wikipedia batch failed for {batch[:2]}")
            continue
        q = data.get("query") or {}
        normalized = {n["from"]: n["to"] for n in q.get("normalized") or []}
        redirects = {n["from"]: n["to"] for n in q.get("redirects") or []}
        resolved = {}
        for page in (q.get("pages") or {}).values():
            if "missing" not in page:
                resolved[page.get("title", "")] = page
        for asked in batch:
            got = redirects.get(normalized.get(asked, asked), normalized.get(asked, asked))
            page = resolved.get(got)
            if not page:
                continue
            qid = (page.get("pageprops") or {}).get("wikibase_item")
            if qid:
                qid_by_title[asked] = qid
                title_canon[asked] = page.get("title") or got
    qids = sorted(set(qid_by_title.values()))
    print(f"  Wikidata entities: {len(qids)}", flush=True)
    entities = {}
    for batch in chunked(qids, 40):
        data = wikidata_api({
            "action": "wbgetentities", "ids": "|".join(batch),
            "props": "claims|labels|sitelinks", "languages": "en", "format": "json",
        })
        if not data:
            log.append(f"Wikidata batch failed for {batch[:2]}")
            continue
        entities.update(data.get("entities") or {})

    by_slug = {}
    for c in companies:
        hosts = hosts_for(c)
        cands = []
        titles = [c["name"], *WIKI_HINTS.get(c["slug"], [])]
        seen = set()
        for t in titles:
            if t.lower() in seen:
                continue
            seen.add(t.lower())
            qid = qid_by_title.get(t)
            if not qid or qid not in entities or entities[qid].get("missing"):
                continue
            ent = entities[qid]
            claims = ent.get("claims") or {}
            year = parse_p571(claims)
            if not year:
                continue
            sites = parse_p856(claims)
            p31 = parse_p31(claims)
            web_ok = website_matches(sites, hosts)
            wiki_title = title_canon.get(t) or t
            label = ((ent.get("labels") or {}).get("en") or {}).get("value") or ""
            name_ok = title_close(wiki_title, c["name"]) or title_close(label, c["name"])
            if "Q4167410" in p31:  # disambiguation
                continue
            if not web_ok and not name_ok:
                continue
            if not web_ok and p31 and "Q5" in p31 and not (set(p31) & ORG_QIDS):
                continue
            source = f"https://www.wikidata.org/wiki/{qid}"
            enwiki = ((ent.get("sitelinks") or {}).get("enwiki") or {}).get("title")
            if enwiki:
                source = "https://en.wikipedia.org/wiki/" + enwiki.replace(" ", "_")
            cands.append((year, source, web_ok))
        if cands:
            cands.sort(key=lambda x: (not x[2], x[0]))
            by_slug[c["slug"]] = (cands[0][0], cands[0][1])

    misses = [c for c in companies if c["slug"] not in by_slug]
    print(f"  title hits: {len(by_slug)}; search fallback for {len(misses)}", flush=True)

    def search_one(c):
        query = WIKI_HINTS.get(c["slug"], [c["name"]])[0]
        data = wiki_api({
            "action": "query", "list": "search", "srsearch": query,
            "srlimit": "5", "format": "json",
        })
        if not data:
            return c["slug"], None, None
        hosts = hosts_for(c)
        for hit in (data.get("query") or {}).get("search") or []:
            title = hit.get("title") or ""
            props = wiki_api({
                "action": "query", "prop": "pageprops", "ppprop": "wikibase_item",
                "titles": title, "format": "json",
            })
            if not props:
                continue
            qid = None
            for page in ((props.get("query") or {}).get("pages") or {}).values():
                qid = (page.get("pageprops") or {}).get("wikibase_item")
                if qid:
                    break
            if not qid:
                continue
            entd = wikidata_api({
                "action": "wbgetentities", "ids": qid,
                "props": "claims|labels|sitelinks", "languages": "en", "format": "json",
            })
            if not entd:
                continue
            ent = (entd.get("entities") or {}).get(qid) or {}
            claims = ent.get("claims") or {}
            year = parse_p571(claims)
            if not year:
                continue
            sites = parse_p856(claims)
            p31 = parse_p31(claims)
            if "Q4167410" in p31:
                continue
            web_ok = website_matches(sites, hosts)
            name_ok = title_close(title, c["name"])
            if not web_ok and not name_ok:
                continue
            source = "https://en.wikipedia.org/wiki/" + title.replace(" ", "_")
            return c["slug"], year, source
        return c["slug"], None, None

    with ThreadPoolExecutor(max_workers=WIKI_WORKERS) as pool:
        futs = [pool.submit(search_one, c) for c in misses]
        for i, fut in enumerate(as_completed(futs), 1):
            slug, year, source = fut.result()
            if year and source:
                by_slug[slug] = (year, source)
            if i % 25 == 0 or i == len(futs):
                print(f"  wiki search {i}/{len(futs)}", flush=True)

    # Lead-extract year when Wikidata has no P571 but the Wikipedia page is the company.
    still = [c for c in companies if c["slug"] not in by_slug]
    print(f"  extract fallback for {len(still)}", flush=True)
    year_lead = re.compile(
        r"\b(?:founded|established|launched|incorporated|started)\s+"
        r"(?:in\s+)?(?:the\s+year\s+)?"
        r"(?:january|february|march|april|may|june|july|august|september|"
        r"october|november|december)?\s*,?\s*(19[7-9]\d|20[0-2]\d)\b",
        re.I,
    )
    for c in still:
        titles = []
        for raw in [c["name"], *WIKI_HINTS.get(c["slug"], [])]:
            if raw not in titles:
                titles.append(raw)
        data = wiki_api({
            "action": "query", "prop": "extracts|pageprops", "exintro": "1",
            "explaintext": "1", "ppprop": "wikibase_item", "redirects": "1",
            "titles": "|".join(titles[:4]), "format": "json",
        })
        if not data:
            continue
        hosts = hosts_for(c)
        for page in ((data.get("query") or {}).get("pages") or {}).values():
            if "missing" in page:
                continue
            title = page.get("title") or ""
            extract = page.get("extract") or ""
            if not title_close(title, c["name"]) and not title_close(title, (WIKI_HINTS.get(c["slug"]) or [""])[0]):
                # still allow if extract names the company and a year
                if c["name"].split()[0].lower() not in (extract[:400] or "").lower():
                    continue
            m = year_lead.search(extract[:600] if extract else "")
            if not m:
                continue
            year = int(m.group(1))
            if 1970 <= year <= NOW_YEAR:
                source = "https://en.wikipedia.org/wiki/" + title.replace(" ", "_")
                by_slug[c["slug"]] = (year, source)
                break
    return by_slug


LOGIN_WALL = re.compile(
    r"(please (?:log|sign) in|sign in to continue|login required|"
    r"you (?:must|need to) (?:log|sign) in|authentication required)",
    re.I,
)


def looks_like_login_wall(title: str, text: str) -> bool:
    blob = f"{title} {text[:1200]}"
    if not LOGIN_WALL.search(blob):
        return False
    if re.search(r"trust center|privacy policy|sub-?process|data processing|status page", blob, re.I):
        return False
    return len(re.sub(r"\s+", " ", text or "")) < 600


def probe_company(company: dict) -> dict:
    links: dict[str, str] = {}
    pages: dict[str, dict] = {}
    extra_hits = 0
    pairs = probe_urls_for(company)
    trust = (company.get("trust_url") or "").rstrip("/")
    if trust:
        key = trust.lower()
        if key not in {u.lower() for u, _ in pairs}:
            pairs = [(trust, "trust"), *pairs]
    for url, hint in pairs:
        rec = fetch_cached(url, max_body=PROBE_BODY if hint not in {"trust", "security"} else TRUST_BODY)
        title, text = rec.get("title") or "", rec.get("text") or ""
        if looks_like_login_wall(title, text):
            continue
        kind = classify_probe(url, rec)
        if kind is None and hint in {"trust", "security"} and accept_link(hint, url, rec):
            kind = hint
        if kind and kind not in links:
            final = rec.get("final_url") or url
            links[kind] = final
            pages[kind] = rec
            extra_hits += 1
        if rec.get("ok") and rec.get("status") == 200 and hint == "trust" and "trust" not in links:
            if accept_link("trust", url, rec) and not looks_like_login_wall(title, text):
                links["trust"] = rec.get("final_url") or url
                pages["trust"] = rec
    # Follow obvious first-party instrument links from trust/security HTML.
    seed_pages = [pages[k] for k in ("trust", "security") if k in pages]
    for rec in seed_pages:
        base = rec.get("final_url") or ""
        for href in rec.get("hrefs") or []:
            hhost, rhost = host_of(href), host_of(base)
            if not hhost or not rhost:
                continue
            if registrable(hhost) != registrable(rhost) and not hhost.startswith("status."):
                continue
            for kind, pat in LINK_HINTS:
                if kind in links:
                    continue
                if not pat.search(href):
                    continue
                sub = fetch_cached(href, max_body=TRUST_BODY if kind in {"trust", "security", "subprocessors"} else PROBE_BODY)
                if looks_like_login_wall(sub.get("title") or "", sub.get("text") or ""):
                    continue
                classified = classify_probe(href, sub)
                if classified == kind or (kind in {"trust", "security"} and accept_link(kind, href, sub)):
                    links[kind] = sub.get("final_url") or href
                    pages[kind] = sub
                    break
    if "security_txt" in pages:
        bounty = bounty_from_security_txt(pages["security_txt"].get("raw_head") or pages["security_txt"].get("text") or "")
        if bounty and "bug_bounty" not in links:
            links["bug_bounty"] = bounty
    return {"links": links, "pages": pages, "probed": extra_hits}


def certs_from_pages(company: dict, pages: dict, links: dict) -> list[str]:
    blobs = []
    for key in ("trust", "security"):
        rec = pages.get(key)
        if rec:
            blobs.append(f"{rec.get('title') or ''} {rec.get('meta') or ''} {rec.get('text') or ''}")
    # Prefer live extraction. Keep a prior cert only if the same token appears on a live page.
    live = extract_certs(" \n ".join(blobs))
    return live


def processors_from_company(company: dict, pages: dict, links: dict) -> list[tuple[str, str, str]]:
    rec = pages.get("subprocessors")
    url = links.get("subprocessors")
    if not rec or not url:
        return []
    if not is_subprocessor_page(url, rec.get("title") or "", rec.get("text") or ""):
        # still accept if the path itself is a subprocessor path and we classified it
        if not re.search(r"sub-?process|service-providers?", url, re.I):
            return []
    text = rec.get("text") or ""
    ids = extract_processors(text)
    own = {company["slug"], "newrelic" if company["slug"] == "new-relic" else company["slug"]}
    out = []
    for pid in ids:
        if pid == company["slug"] or pid in own:
            continue
        name = next((n for i, n, _d, _a in PROCESSORS if i == pid), pid)
        # evidence: a short matching alias
        ev = name
        out.append((pid, name, ev))
    return out


def disclosure_factors(found: bool, certs: list[str], links: dict, founded_year) -> dict:
    factors = {}
    if found:
        factors["portal"] = 20
    cpts = cert_score(certs)
    if cpts:
        factors["certs"] = cpts
    if links.get("dpa"):
        factors["dpa"] = 8
    if links.get("subprocessors"):
        factors["subprocessors"] = 8
    if links.get("status"):
        factors["status"] = 6
    if links.get("bug_bounty") or links.get("security_txt"):
        factors["disclosure"] = 6
    if links.get("privacy"):
        factors["privacy"] = 6
    if founded_year:
        factors["longevity"] = min(10, (NOW_YEAR - founded_year) // 2)
    return factors


def build_nodes_and_edges(companies: list[dict], edges_raw: list[dict]):
    register = {c["slug"]: c for c in companies}
    proc_meta = {i: (n, d) for i, n, d, _a in PROCESSORS}
    node_ids = set()
    nodes = []

    def add_node(nid, name, domain, in_register, kind):
        if nid in node_ids:
            return
        node_ids.add(nid)
        nodes.append({
            "id": nid,
            "name": name,
            "domain": domain,
            "kind": kind,
            "in_register": bool(in_register),
        })

    for c in companies:
        add_node(c["slug"], c["name"], c["domain"], True, "company")
    for e in edges_raw:
        pid = e["to"]
        if pid in register:
            add_node(pid, register[pid]["name"], register[pid]["domain"], True, "company")
        elif pid in proc_meta:
            name, domain = proc_meta[pid]
            add_node(pid, name, domain, False, "processor")
        else:
            add_node(pid, e.get("evidence") or pid, "", False, "processor")
    return nodes, edges_raw


def write_log(path: Path, lines: list[str], stats: dict) -> None:
    body = ["# Enrichment log", "", f"Generated: {stats['generated_at']}", ""]
    body.append("## Coverage")
    body.append("")
    for k in (
        "companies", "years", "years_skipped", "probes_attempted", "portal_on_file",
        "certs_companies", "certs_total", "dpa", "subprocessor_pages", "subprocessor_edges",
        "status", "privacy", "security_txt", "bounty",
        "tier_silent", "tier_thin", "tier_on-file", "tier_substantial", "tier_complete",
    ):
        if k in stats:
            body.append(f"- {k}: {stats[k]}")
    body.append("")
    body.append("## Notes")
    body.append("")
    body.append("Years come from Wikidata P571 after a Wikipedia title resolve, only when the official website matches the register domain or the title/label is an unambiguous close match. Ambiguous names without a website match were omitted.")
    body.append("")
    body.append("Well-known paths were GET-probed for every domain. A hit is HTTP 200 that is not a soft 404, parked page, login wall, or homepage bounce.")
    body.append("")
    body.append("Certs were extracted from live trust/security HTML only. JavaScript-only portals often yield no cert tokens; those companies have an empty certs list rather than invented marks.")
    body.append("")
    body.append("Subprocessor edges require a public first-party list URL. Names are normalized against a known processor catalog. Unlisted names are not guessed.")
    body.append("")
    body.append("Portal host vendors (SafeBase, Vanta, Conveyor, Wolfia, Drata, SecurityPal) are not written into summaries.")
    body.append("")
    if lines:
        body.append("## Detail")
        body.append("")
        body.extend(f"- {ln}" for ln in lines)
        body.append("")
    path.write_text("\n".join(body) + "\n")


def main() -> int:
    t0 = time.time()
    CACHE.mkdir(parents=True, exist_ok=True)
    companies = load_register()
    print(f"Enriching {len(companies)} companies", flush=True)
    log: list[str] = []

    print("A. Founding years (Wikipedia / Wikidata)", flush=True)
    years = resolve_founding_years(companies, log)
    print(f"  verified years: {len(years)}/{len(companies)}", flush=True)
    for c in companies:
        if c["slug"] not in years:
            log.append(f"year omitted ({c['slug']}): no verified Wikidata/Wikipedia match")

    print("B. Well-known path probe", flush=True)
    probed: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = {pool.submit(probe_company, c): c["slug"] for c in companies}
        done = 0
        for fut in as_completed(futs):
            slug = futs[fut]
            try:
                probed[slug] = fut.result()
            except Exception as exc:
                log.append(f"probe failed ({slug}): {exc}")
                probed[slug] = {"links": {}, "pages": {}, "probed": 0}
            done += 1
            if done % 20 == 0 or done == len(futs):
                print(f"  probed {done}/{len(futs)}", flush=True)

    print("C–E. Certs, subprocessors, scores", flush=True)
    generated_at = utc_now()
    out_companies = []
    edges = []
    stats = Counter()
    stats["companies"] = len(companies)
    stats["years"] = len(years)
    stats["years_skipped"] = len(companies) - len(years)

    for c in companies:
        rec = probed.get(c["slug"]) or {"links": {}, "pages": {}, "probed": 0}
        links = rec["links"]
        pages = rec["pages"]
        stats["probes_attempted"] += rec.get("probed", 0)

        # Portal: original found URL still live, or /trust or /security hit.
        portal = False
        if c.get("found") and c.get("trust_url"):
            turl = c["trust_url"]
            tpage = fetch_cached(turl, max_body=TRUST_BODY)
            if tpage.get("ok") and tpage.get("status") == 200 and not looks_dead(tpage.get("title") or "", tpage.get("text") or ""):
                if not looks_like_login_wall(tpage.get("title") or "", tpage.get("text") or ""):
                    portal = True
                    pages.setdefault("trust", tpage)
                    links.setdefault("trust", tpage.get("final_url") or turl)
        if links.get("trust") or links.get("security"):
            portal = True

        certs = certs_from_pages(c, pages, links)
        procs = processors_from_company(c, pages, links)
        year_src = years.get(c["slug"])
        founded_year = year_src[0] if year_src else None
        founded_source = year_src[1] if year_src else None

        score, tier = score_row(portal, certs, links, founded_year)
        factors = disclosure_factors(portal, certs, links, founded_year)

        page_text = ""
        for key in ("trust", "security"):
            if pages.get(key):
                page_text = pages[key].get("meta") or pages[key].get("text") or ""
                break
        summary = clerk_summary(portal, certs, c.get("summary") or "", page_text)

        row = dict(c)
        row.pop("aliases", None)
        if founded_year and founded_source:
            row["founded_year"] = founded_year
            row["founded_source"] = founded_source
        row["certs"] = certs
        row["links"] = {k: v for k, v in links.items() if v}
        row["summary"] = summary
        row["subprocessors"] = [{"id": pid, "name": name} for pid, name, _e in procs]
        row["disclosure"] = {"score": score, "tier": tier, "factors": factors}
        if row.get("title"):
            row["title"] = clean_title(row["title"], c.get("name") or "")
        if VENDOR_WORDS.search(row.get("summary") or ""):
            row["summary"] = clerk_summary(portal, certs, "", page_text)
        out_companies.append(row)

        for pid, name, ev in procs:
            edges.append({
                "from": c["slug"],
                "to": pid,
                "source_url": links.get("subprocessors"),
                "evidence": ev,
            })

        if portal:
            stats["portal_on_file"] += 1
        if certs:
            stats["certs_companies"] += 1
            stats["certs_total"] += len(certs)
        if links.get("dpa"):
            stats["dpa"] += 1
        if links.get("subprocessors"):
            stats["subprocessor_pages"] += 1
        if links.get("status"):
            stats["status"] += 1
        if links.get("privacy"):
            stats["privacy"] += 1
        if links.get("security_txt"):
            stats["security_txt"] += 1
        if links.get("bug_bounty"):
            stats["bounty"] += 1
        stats[f"tier_{tier}"] += 1

    stats["subprocessor_edges"] = len(edges)
    nodes, edges = build_nodes_and_edges(companies, edges)

    enriched = {
        "generated_at": generated_at,
        "companies": out_companies,
    }
    write_json(DATA / "enriched.json", enriched)

    sub = {
        "generated_at": generated_at,
        "nodes": nodes,
        "edges": edges,
        "notes": (
            "Filed from public first-party subprocessor lists only. "
            "This is not a complete supply chain. Login-gated lists are not on file. "
            "Processor ids are normalized when the published name matches a known catalog entry."
        ),
    }
    write_json(DATA / "subprocessors.json", sub)

    stats_out = {k: int(v) if not isinstance(v, str) else v for k, v in stats.items()}
    stats_out["generated_at"] = generated_at
    stats_out["elapsed_s"] = round(time.time() - t0, 1)
    write_log(DATA / "enrichment-log.md", log, stats_out)

    print(f"Wrote {DATA / 'enriched.json'}", flush=True)
    print(f"Wrote {DATA / 'subprocessors.json'}", flush=True)
    print(f"Wrote {DATA / 'enrichment-log.md'}", flush=True)
    print(
        f"years={stats['years']} portal={stats['portal_on_file']} "
        f"certs={stats['certs_companies']} edges={stats['subprocessor_edges']} "
        f"in {stats_out['elapsed_s']}s",
        flush=True,
    )
    return 0


def file_published_security_txt() -> int:
    """File RFC 9116 security.txt URLs already published on domains that had none."""
    t0 = time.time()
    src = SITE / "data" / "enriched.json"
    if not src.exists():
        src = DATA / "enriched.json"
    payload = load_json(src, {})
    companies = list(payload.get("companies") or [])
    if not companies:
        print("no companies in enriched.json", flush=True)
        return 1
    before = sum(1 for c in companies if (c.get("links") or {}).get("security_txt"))
    gaps = [c for c in companies if c.get("domain") and not (c.get("links") or {}).get("security_txt")]
    print(f"security.txt on file: {before}. Domains with none: {len(gaps)}", flush=True)

    by_slug = {c["slug"]: c for c in companies}
    accepted: dict[str, tuple[str, str]] = {}

    def do_verify(job):
        slug, url = job
        try:
            rec = fetch_uncached(url, PROBE_BODY)
        except Exception:
            rec = {"ok": False, "status": 0, "final_url": url, "title": "", "text": "", "raw_head": "", "ctype": ""}
        return slug, url, rec

    def take_hits(jobs: list[tuple[str, str]], label: str) -> None:
        if not jobs:
            return
        print(f"{label}: {len(jobs)} URLs…", flush=True)
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            futs = [pool.submit(do_verify, job) for job in jobs]
            done = 0
            for fut in as_completed(futs):
                slug, url, rec = fut.result()
                done += 1
                if done % 100 == 0 or done == len(futs):
                    print(f"  {label} {done}/{len(futs)}", flush=True)
                if slug in accepted:
                    continue
                row = by_slug.get(slug)
                if not row:
                    continue
                filed = accept_security_txt(url, rec)
                if not filed:
                    continue
                raw = rec.get("raw_head") or rec.get("text") or ""
                accepted[slug] = (filed, raw)

    wave1 = []
    seen = set()
    for c in gaps:
        for url in security_txt_probe_urls(c, well_known_only=True):
            key = (c["slug"], url.lower())
            if key in seen:
                continue
            seen.add(key)
            wave1.append((c["slug"], url))
    take_hits(wave1, "Phase 1 well-known")

    wave2 = []
    for c in gaps:
        if c["slug"] in accepted:
            continue
        for url in security_txt_probe_urls(c, well_known_only=False):
            key = (c["slug"], url.lower())
            if key in seen:
                continue
            seen.add(key)
            wave2.append((c["slug"], url))
    take_hits(wave2, "Phase 2 /security.txt")

    filed: list[tuple[str, str]] = []
    for slug, (url, raw) in sorted(accepted.items()):
        row = by_slug[slug]
        if apply_security_txt_to_row(row, url):
            extras = optional_links_from_security_txt(raw, row, row.get("links") or {})
            apply_optional_txt_links(row, extras)
            filed.append((row.get("name") or slug, url))

    generated = utc_now()
    payload["generated_at"] = generated
    payload["companies"] = companies
    write_json(DATA / "enriched.json", payload)
    write_json(SITE / "data" / "enriched.json", payload)
    after = sum(1 for c in companies if (c.get("links") or {}).get("security_txt"))
    print(f"Wrote {DATA / 'enriched.json'} and {SITE / 'data' / 'enriched.json'}", flush=True)
    print(
        f"checked={len(gaps)} filed={len(filed)} security.txt {before} → {after} "
        f"in {time.time() - t0:.1f}s",
        flush=True,
    )
    for name, url in filed:
        print(f"  filed {name}: {url}", flush=True)
    return 0


if __name__ == "__main__":
    if "--file-security-txt" in sys.argv:
        raise SystemExit(file_published_security_txt())
    raise SystemExit(main())


def run() -> int:
    t0 = time.time()
    (CACHE / "http").mkdir(parents=True, exist_ok=True)
    log_notes: list[str] = []
    companies = load_register()
    print(f"Loaded {len(companies)} companies", flush=True)

    prior_certs = {}
    for c in companies:
        blob = " ".join(filter(None, [c.get("title"), c.get("summary")]))
        extracted = extract_certs(blob)
        old = [x for x in (c.get("certs") or []) if isinstance(x, str)]
        merged = []
        for item in extracted + old:
            if item not in merged:
                merged.append(item)
        if merged:
            prior_certs[c["slug"]] = merged

    print("Phase B: founding years via Wikipedia/Wikidata…", flush=True)
    years = resolve_founding_years(companies, log_notes)
    print(f"  verified founding years: {len(years)}", flush=True)

    jobs, seen_job = [], set()
    for c in companies:
        for url, hint in probe_urls_for(c):
            key = (c["slug"], url.lower())
            if key in seen_job:
                continue
            seen_job.add(key)
            jobs.append((c["slug"], url, hint))
    print(f"Phase C: probing {len(jobs)} URLs with {WORKERS} workers…", flush=True)
    probe_hits = defaultdict(dict)
    fail_zero = 0

    def do_probe(job):
        slug, url, hint = job
        return slug, url, hint, fetch_cached(url, max_body=PROBE_BODY)

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = [pool.submit(do_probe, job) for job in jobs]
        done = 0
        for fut in as_completed(futs):
            slug, url, hint, rec = fut.result()
            done += 1
            if done % 250 == 0 or done == len(futs):
                print(f"  probe {done}/{len(futs)}", flush=True)
            if rec.get("status") == 0:
                fail_zero += 1
            if accept_link(hint, url, rec):
                if hint not in probe_hits[slug]:
                    probe_hits[slug][hint] = (rec.get("final_url") or url, rec)
            else:
                kind = classify_probe(url, rec)
                if kind and kind not in probe_hits[slug]:
                    probe_hits[slug][kind] = (rec.get("final_url") or url, rec)

    trust_jobs = []
    for c in companies:
        url = c.get("trust_url") or c.get("final_url")
        if c.get("found") and url:
            trust_jobs.append((c["slug"], url))
    print(f"Phase D: fetching {len(trust_jobs)} trust pages…", flush=True)
    trust_pages = {}

    def do_trust(job):
        slug, url = job
        return slug, fetch_cached(url, max_body=TRUST_BODY)

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = [pool.submit(do_trust, job) for job in trust_jobs]
        done = 0
        for fut in as_completed(futs):
            slug, rec = fut.result()
            trust_pages[slug] = rec
            done += 1
            if done % 40 == 0 or done == len(futs):
                print(f"  trust {done}/{len(futs)}", flush=True)

    follow, follow_seen = [], set(seen_job)
    for c in companies:
        rec = trust_pages.get(c["slug"])
        if not rec:
            continue
        hosts = set(hosts_for(c))
        th = host_of(c.get("trust_url") or "")
        if th:
            hosts.add(th)
        for href in rec.get("hrefs") or []:
            h = host_of(href)
            first_party = any(h == x or h.endswith("." + x) or x.endswith("." + h) for x in hosts)
            if not first_party and not re.search(r"status|hackerone|bugcrowd|security\.txt", href, re.I):
                continue
            kind = None
            for name, pat in LINK_HINTS:
                if pat.search(href):
                    kind = name
                    break
            if not kind:
                continue
            clean = href.split("#")[0]
            key = (c["slug"], clean.lower())
            if key in follow_seen:
                continue
            follow_seen.add(key)
            follow.append((c["slug"], clean, kind))
    print(f"Phase E: following {len(follow)} discovered links…", flush=True)

    def do_follow(job):
        slug, url, hint = job
        body = TRUST_BODY if hint == "subprocessors" else PROBE_BODY
        return slug, url, hint, fetch_cached(url, max_body=body)

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = [pool.submit(do_follow, job) for job in follow]
        done = 0
        for fut in as_completed(futs):
            slug, url, hint, rec = fut.result()
            done += 1
            if done % 80 == 0 or done == len(futs):
                print(f"  follow {done}/{len(futs)}", flush=True)
            if accept_link(hint, url, rec) and hint not in probe_hits[slug]:
                probe_hits[slug][hint] = (rec.get("final_url") or url, rec)
            else:
                kind = classify_probe(url, rec)
                if kind and kind not in probe_hits[slug]:
                    probe_hits[slug][kind] = (rec.get("final_url") or url, rec)

    # About-page years only when Wikidata missed and the sentence is explicit.
    about_jobs = []
    for c in companies:
        if c["slug"] in years:
            continue
        for domain in hosts_for(c)[:1]:
            about_jobs.append((c["slug"], f"https://{domain}/about"))
            about_jobs.append((c["slug"], f"https://{domain}/about-us"))
            about_jobs.append((c["slug"], f"https://{domain}/company"))
    print(f"Phase E2: about pages for {len(about_jobs)//3} year-misses…", flush=True)

    def do_about(job):
        slug, url = job
        return slug, url, fetch_cached(url, max_body=PROBE_BODY)

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = [pool.submit(do_about, job) for job in about_jobs]
        for fut in as_completed(futs):
            slug, url, rec = fut.result()
            if slug in years:
                continue
            if not rec.get("ok") or rec.get("status") != 200:
                continue
            if looks_dead(rec.get("title") or "", rec.get("text") or ""):
                continue
            if landed_on_home(url, rec.get("final_url") or url):
                continue
            m = ABOUT_FOUNDED.search(rec.get("text") or "")
            if m:
                year = int(m.group(1))
                if 1970 <= year <= NOW_YEAR:
                    years[slug] = (year, rec.get("final_url") or url)

    print("Phase F: assemble…", flush=True)
    in_register = {c["slug"] for c in companies}
    domain_to_slug = {}
    for c in companies:
        for h in hosts_for(c):
            domain_to_slug[registrable(h)] = c["slug"]
    proc_meta = {pid: (name, dom) for pid, name, dom, _a in PROCESSORS}

    nodes = {}
    edges = []
    enriched = []
    skipped_vendor_summaries = 0
    retained_prior_certs = 0
    year_skipped = []

    for c in companies:
        slug = c["slug"]
        links = {}
        hits = probe_hits.get(slug) or {}
        for kind, (url, _rec) in hits.items():
            if kind in {"trust", "security", "privacy", "dpa", "subprocessors",
                        "status", "bug_bounty", "security_txt"} and url:
                links[kind] = url

        if c.get("found") and c.get("trust_url"):
            links.setdefault("trust", c["trust_url"])
            if "security" in (c.get("trust_url") or "").lower():
                links.setdefault("security", c["trust_url"])

        stxt = hits.get("security_txt")
        if stxt and "bug_bounty" not in links:
            bounty = bounty_from_security_txt(stxt[1].get("text") or stxt[1].get("raw_head") or "")
            if bounty:
                links["bug_bounty"] = bounty

        cert_blob_parts = []
        if c.get("title"):
            cert_blob_parts.append(c["title"])
        tpage = trust_pages.get(slug)
        if tpage and tpage.get("ok") and tpage.get("status") == 200:
            cert_blob_parts.append(tpage.get("title") or "")
            cert_blob_parts.append(tpage.get("meta") or "")
            cert_blob_parts.append((tpage.get("text") or "")[:20000])
        for kind in ("security", "trust"):
            if kind in hits:
                cert_blob_parts.append(hits[kind][1].get("title") or "")
                cert_blob_parts.append((hits[kind][1].get("text") or "")[:12000])
        certs = extract_certs(" ".join(cert_blob_parts))
        if not certs and slug in prior_certs:
            certs = list(prior_certs[slug])
            retained_prior_certs += 1

        founded_year, founded_source = None, None
        if slug in years:
            founded_year, founded_source = years[slug]
        else:
            year_skipped.append(c["name"])

        procs = []
        proc_source = None
        if "subprocessors" in hits:
            rec = hits["subprocessors"][1]
            if is_subprocessor_page(hits["subprocessors"][0], rec.get("title") or "", rec.get("text") or ""):
                procs = extract_processors(rec.get("text") or "")
                proc_source = hits["subprocessors"][0]
        if not procs and tpage:
            text = tpage.get("text") or ""
            m = re.search(r"sub-?processors?.{0,6000}", text, re.I)
            if m:
                section = m.group(0)
                procs = extract_processors(section)
                if procs:
                    proc_source = tpage.get("final_url") or c.get("trust_url")

        # do not list the company as its own subprocessor
        procs = [p for p in procs if p != slug and p != "s3" and p != "cloudfront"]
        # map cloudfront/s3 already excluded; aws stays if listed

        old_sum = c.get("summary") or ""
        if VENDOR_WORDS.search(old_sum) or VENDOR_WORDS.search(c.get("title") or ""):
            if VENDOR_WORDS.search(old_sum):
                skipped_vendor_summaries += 1
        page_text = ""
        if tpage and not VENDOR_WORDS.search(tpage.get("meta") or ""):
            page_text = tpage.get("meta") or (tpage.get("text") or "")[:500]
        summary = clerk_summary(bool(c.get("found")), certs, old_sum, page_text)

        portal = bool(c.get("found")) or bool(links.get("trust") or links.get("security"))
        score, tier = score_row(portal, certs, links, founded_year)
        factors = disclosure_factors(portal, certs, links, founded_year)
        proc_objs = []
        for pid in procs:
            pname = proc_meta.get(pid, (pid, ""))[0]
            proc_objs.append({"id": pid, "name": pname})

        row = {
            "rank": c.get("rank"),
            "name": c["name"],
            "slug": slug,
            "domain": c.get("domain"),
            "found": bool(c.get("found")),
            "trust_url": c.get("trust_url"),
            "final_url": c.get("final_url"),
            "vendor": c.get("vendor"),
            "title": clean_title(c.get("title") or "", c.get("name") or ""),
            "probed": c.get("probed"),
            "source": c.get("source"),
            "list": c.get("list"),
            "certs": certs,
            "links": links,
            "summary": summary,
            "subprocessors": proc_objs,
            "disclosure": {"score": score, "tier": tier, "factors": factors},
        }
        if founded_year and founded_source:
            row["founded_year"] = founded_year
            row["founded_source"] = founded_source
        enriched.append(row)

        nodes[slug] = {
            "id": slug,
            "name": c["name"],
            "domain": c.get("domain"),
            "kind": "company",
            "in_register": True,
        }
        if proc_source:
            for pid in procs:
                pname, pdom = proc_meta.get(pid, (pid, ""))
                if pid not in nodes:
                    nodes[pid] = {
                        "id": pid,
                        "name": pname,
                        "domain": pdom,
                        "kind": "company" if pid in in_register else "subprocessor",
                        "in_register": pid in in_register,
                    }
                else:
                    # already a register company
                    pass
                edges.append({
                    "from": slug,
                    "to": pid,
                    "source_url": proc_source,
                    "evidence": "listed on public subprocessors page",
                })

    generated = utc_now()
    site_src = load_json(SITE / "data.json", {})
    payload = {
        "generated_at": generated,
        "register_generated_at": site_src.get("generated_at"),
        "sources": site_src.get("sources") or [],
        "notes": "Public pages only. Incomplete by nature. No invented URLs, years, certs, or processors.",
        "companies": enriched,
    }
    write_json(DATA / "enriched.json", payload)

    graph = {
        "generated_at": generated,
        "nodes": sorted(nodes.values(), key=lambda n: (n["kind"] != "company", n["name"].lower())),
        "edges": edges,
        "notes": "Only public lists. Incomplete by nature.",
    }
    write_json(DATA / "subprocessors.json", graph)

    n_years = sum(1 for r in enriched if r["founded_year"])
    n_certs = sum(1 for r in enriched if r["certs"])
    n_cert_mentions = sum(len(r["certs"]) for r in enriched)
    n_edges = len(edges)
    n_sub_cos = sum(1 for r in enriched if r["subprocessors"])
    n_txt = sum(1 for r in enriched if r["links"].get("security_txt"))
    n_dpa = sum(1 for r in enriched if r["links"].get("dpa"))
    n_priv = sum(1 for r in enriched if r["links"].get("privacy"))
    n_stat = sum(1 for r in enriched if r["links"].get("status"))
    n_bug = sum(1 for r in enriched if r["links"].get("bug_bounty"))
    n_sublink = sum(1 for r in enriched if r["links"].get("subprocessors"))
    tiers = Counter(r["disclosure_tier"] for r in enriched)
    top_proc = Counter(e["to"] for e in edges).most_common(15)
    top_certs = Counter(c for r in enriched for c in r["certs"]).most_common(15)

    year_rows = [
        f"| {r['name']} | {r['founded_year']} | {r['founded_source']} |"
        for r in enriched if r["founded_year"]
    ]
    miss_years = ", ".join(year_skipped) if year_skipped else "(none)"
    proc_lines = "\n".join(f"| {pid} | {n} |" for pid, n in top_proc) or "| (none) | 0 |"
    cert_lines = "\n".join(f"| {n} | {c} |" for n, c in top_certs) or "| (none) | 0 |"

    md = f"""# Enrichment log

Generated: {generated} (UTC). Box clock is UTC; Pacific is UTC-7.

## Coverage

| Fact | Count |
|---|---|
| Companies in register | {len(enriched)} |
| Portals already on file | {sum(1 for r in enriched if r['found'])} |
| Founding years verified | {n_years} |
| Companies with ≥1 cert mention | {n_certs} |
| Cert mentions (total) | {n_cert_mentions} |
| Companies with a public subprocessor list we could read | {n_sub_cos} |
| Subprocessor edges | {n_edges} |
| security.txt (RFC-shaped, 200) | {n_txt} |
| DPA link | {n_dpa} |
| Privacy link | {n_priv} |
| Status link | {n_stat} |
| Bug bounty / disclosure link | {n_bug} |
| Subprocessors link | {n_sublink} |
| Probe attempts | {len(jobs)} |
| Discovered-link follows | {len(follow)} |
| Fetches that returned status 0 (timeout/DNS/TLS) | {fail_zero} |
| Vendor-tainted summaries rewritten or cleared | {skipped_vendor_summaries} |
| Cert lists retained from prior crawl (not re-seen on this pass) | {retained_prior_certs} |

Elapsed: {time.time() - t0:.1f}s

## Disclosure tiers

| Tier | Count |
|---|---|
| silent | {tiers.get('silent', 0)} |
| thin | {tiers.get('thin', 0)} |
| on-file | {tiers.get('on-file', 0)} |
| substantial | {tiers.get('substantial', 0)} |
| complete | {tiers.get('complete', 0)} |

## Method

1. Seed certs from stored titles / prior crawl text (only strings already on file).
2. Wikipedia `pageprops` + Wikidata `P571` / `P856`. A year is kept only when the official website matches the register domain, or the Wikipedia title matches the company name and the website does not contradict it. Source URL is the Wikipedia page when present, otherwise the Wikidata entity.
3. Probe well-known first-party paths for every company (`security.txt`, `/privacy`, `/subprocessors`, `/legal/subprocessors`, `/dpa`, `status.{{domain}}`, disclosure paths, `/security`, `/trust`). Extra first-party variants for large vendors are candidates only — recorded after a 200 and a content check.
4. Fetch each known `trust_url` and extract certs, hrefs, and any subprocessors section.
5. Follow first-party (or status/bounty) hrefs that look like privacy / DPA / subprocessors / status / disclosure.
6. About-page year fallback: only an explicit “founded/established … YYYY” sentence on `/about`, `/about-us`, or `/company`.
7. Subprocessor names are taken from a page that is actually a subprocessor list (or a labeled section). Common processors are normalized to stable ids. An edge exists only when that name appeared on the page.
8. Summaries are clerk voice. Vendor product names are stripped. If the old summary was portal marketing or script junk, it is replaced or left empty.
9. Score: +20 portal, cert weights capped at 40, +8 DPA, +8 subprocessors link, +6 status, +6 bounty or security.txt, +6 privacy, +min(10, floor((2026-year)/2)). Tiers: silent (no portal), thin <40, on-file 40–69, substantial 70–89, complete 90+.

What this is not: a complete crawl of every live page, a claim that missing facts do not exist, or a vendor-catalog. JS-only portals often hide certs and lists behind login or client rendering; those are omitted.

## Top cert mentions

| Certification | Companies |
|---|---|
{cert_lines}

## Top subprocessors (public lists only)

| Processor id | Edges |
|---|---|
{proc_lines}

## Founding years

| Company | Year | Source |
|---|---|---|
{chr(10).join(year_rows) if year_rows else '| (none) | | |'}

## Years skipped (no verified source)

{miss_years}

## Notes from this run

{chr(10).join('- ' + n for n in log_notes) if log_notes else '- No API batch failures recorded.'}

## Outputs

- `data/enriched.json`
- `data/subprocessors.json`
- `data/cache/http/` (URL cache so the script can be re-run without re-fetching)
"""
    (DATA / "enrichment-log.md").write_text(md)
    print(f"Wrote data/enriched.json ({len(enriched)} companies)", flush=True)
    print(f"Wrote data/subprocessors.json ({len(nodes)} nodes, {len(edges)} edges)", flush=True)
    print(f"Wrote data/enrichment-log.md", flush=True)
    print(f"Years={n_years} cert_cos={n_certs} edges={n_edges} in {time.time()-t0:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
