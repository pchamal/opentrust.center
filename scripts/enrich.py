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
from marks import apply_supersede, extract_certs_from_html, mark_blob  # noqa: E402
from merge_render import rescore  # noqa: E402
from processor_aliases import skip_processor  # noqa: E402

DATA = ROOT / "data"
CACHE = DATA / "cache"
SITE = ROOT / "site"
NOW_YEAR = 2026
UA = crawl.UA
WORKERS = 16
WIKI_WORKERS = 6
PROBE_BODY = 24576
# 1 MiB. WordPress first-party security HTML parks the hold past 196 KiB
# (languageio.com/security-commitment ISO 27001:2022 certificate at ~946 KiB).
# Not an unbounded fetch — still a hard cap.
TRUST_BODY = 1048576
PROCESSOR_BODY = 900000

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
SEC_TXT_SKIP_FIELDS = {
    "hiring", "encryption", "canonical", "expires", "preferred-languages",
    "privacy", "privacy policy", "acknowledgments",
}
SEC_TXT_LINE = re.compile(r"(?im)^\s*([A-Za-z][A-Za-z0-9 _-]*):\s*(\S+)")
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
    ("ENS", re.compile(r"\bENS\s+(?:MEDIUM|MEDIO|HIGH|ALTO)\b|\bEsquema Nacional de Seguridad\b", re.I), 8),
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
    ("twilio", "Twilio", "twilio.com", [r"\bTwilio\b(?!\s+Segment)"]),
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
    # Branch Metrics leftover. legal.branch.io is first-party of branch.io.
    # trust.branch.io is a Conveyor portal — not Official page, not a mark source.
    "branch-metrics": [
        ("https://legal.branch.io/saas/branch-saas-dpa/", "dpa"),
        ("https://legal.branch.io/saas/subprocessor-list/", "subprocessors"),
        ("https://legal.branch.io/saas/privacy-policy/", "privacy"),
    ],
    # vonage.com is Cloudflare 403. developer.vonage.com first-party HTML
    # titles "Regulatory Certifications" and prints "This page documents the
    # certifications held by Vonage". Not Official page (docs, not /security).
    "vonage": [
        (
            "https://developer.vonage.com/en/getting-started/concepts/regulatory-certifications",
            "security",
        ),
    ],
    # vultr.com is Cloudflare 403. docs.vultr.com first-party HTML names
    # independently audited SOC 2 Type II / ISO holds. Trust-center stays
    # unread. The DPA FAQ is request-only — not a published DPA.
    "vultr": [
        (
            "https://docs.vultr.com/support/platform/compliance/how-can-i-access-vultrs-compliance-reports",
            "security",
        ),
    ],
    # WordPress /security is a product lander; the hold is on this first-party page.
    "language-i-o": [
        ("https://languageio.com/security-commitment/", "security"),
    ],
    # /seguridad is a product lander (SSL / antivirus). Legal HTML names
    # first-party ISO / ENS certificates. About names the same holds.
    # Neither is Official page.
    "arsys": [
        ("https://www.arsys.es/legal/privacidad", "privacy"),
        ("https://www.arsys.es/quienes-somos", "security"),
    ],
    # /security and /trust 404. First-party /certifications HTML names
    # e2open's own ISO 27001 and SSAE18 SOC 1 / SOC 2 Type II reports.
    # Customer-security-policy is customer obligations, not Official page.
    # DPA redirects to wisetechglobal.com — not first-party.
    "e2open": [
        (
            "https://www.e2open.com/certifications/iso-27001-certification/",
            "security",
        ),
        (
            "https://www.e2open.com/certifications/ssae18-soc1-and-soc2/",
            "security",
        ),
    ],
}

_MONTH = (
    r"(?:january|february|march|april|may|june|july|august|september|"
    r"october|november|december)"
)
_YEAR_TOKEN = r"(1[6-9]\d{2}|20[0-2]\d)"
OFFICIAL_FOUNDED = re.compile(
    rf"""
    \b(?:
        (?:was\s+|were\s+|been\s+)?
        (?:founded|established|incorporated)
        (?:\s+(?:in|on))?
        |
        (?:year|date)\s+(?:founded|established|incorporated)
        |
        (?:founded|established|incorporated)\s*[:\-–—]\s*(?:year|date)?
        |
        founding\s+(?:year|date)
        |
        since\s+(?:our|its|the)\s+founding(?:\s+in)?
        |
        \best\.
    )
    \s*[:\-–—,]?\s*
    (?:the\s+year\s+)?
    (?:(?!(?:{_MONTH}|1[6-9]\d{{2}}|20[0-2]\d)\b)[A-Za-z][A-Za-z.'-]+(?:\s+(?!(?:{_MONTH}|1[6-9]\d{{2}}|20[0-2]\d|in|on)\b)[A-Za-z][A-Za-z.'-]+)?\s+(?:in|on)\s+)?
    (?:{_MONTH}\s+(?:\d{{1,2}}(?:st|nd|rd|th)?,?\s+)?)?
    ({_YEAR_TOKEN})
    \b
    """,
    re.I | re.X,
)
OFFICIAL_FOUNDED_REVERSE = re.compile(
    rf"\bin\s+({_YEAR_TOKEN})\b[^.]{{0,80}}?\b(?:was\s+|were\s+)?(?:founded|established|incorporated)\b",
    re.I,
)
# Timeline copy: "2012 Fivetran is founded out of Y Combinator"
# Milestone em-dash: "1985 — SFEIR is founded."
YEAR_THEN_FOUNDED = re.compile(
    rf"(?:^|[^\d])({_YEAR_TOKEN})\s*[-–—]?\s+(?:[A-Z][\w.&'-]*\s+){{0,8}}(?:is|was|were)\s+(?:founded|established|incorporated)\b",
)
FOUNDING_DATE_FIELD = re.compile(
    rf"""(?:foundingDate|founding_date|dateFounded|yearFounded)\s*"?\s*[=:]\s*"?({_YEAR_TOKEN})""",
    re.I,
)
# JSON-LD foundingDate is not a founding year when the same window is a
# rebrand, rename, or product launch (Airship 2019-06-01 class).
JSONLD_NOT_FOUNDING = re.compile(
    r"\b(re-?brand(?:ed|ing)?|formerly known as|renamed(?:\s+to)?|"
    r"product\s+launch|launched the product|unveiled)\b",
    re.I,
)
# Prose "established in YYYY, as a new name for X" is a rename, not founding
# (Cencora 2023 / AmerisourceBergen class).
PROSE_REBRAND = re.compile(
    r"\b(?:as a new name(?:\s+for)?|new name for|re-?brand(?:ed|ing)?|"
    r"formerly known as|renamed(?:\s+to)?|change(?:d)? its name)\b",
    re.I,
)
# Timeline copy: "2005 Fenrir Established 2008 Collaborative Development"
# The year after Established is the next beat, not founding.
# Also "2001 Keyhole founded 2004 Acquired by Google" (Niantic Spatial).
_YEAR_NC = r"(?:1[6-9]\d{2}|20[0-2]\d)"
_TIMELINE_NEXT_EVENT = re.compile(
    rf"\b({_YEAR_NC})\s+[A-Z][A-Za-z][\w.&'-]*"
    rf"(?:\s+[A-Z][A-Za-z][\w.&'-]*){{0,3}}\s+"
    rf"(?:[Ff]ounded|[Ee]stablished|[Ii]ncorporated)\s+({_YEAR_NC})\b"
)
COPYRIGHT_SPAN = re.compile(
    r"(?:©|&copy;|copyright)\s*(?:©\s*)?(?:19|20)\d{2}(?:\s*[-–—]\s*(?:19|20)\d{2})?",
    re.I,
)
NEWS_ARTICLE_PATH = re.compile(
    r"/(?:press|news|newsroom|blog|media|articles?)/.+"
    r"|/\d{4}/\d{1,2}/",
    re.I,
)
THIRD_PARTY_YEAR_HOSTS = {
    "wikipedia.org", "wikidata.org", "crunchbase.com", "techcrunch.com",
    "bloomberg.com", "forbes.com", "reuters.com", "wsj.com", "nytimes.com",
    "businesswire.com", "prnewswire.com", "yahoo.com", "linkedin.com",
    "medium.com", "glassdoor.com", "pitchbook.com", "cbinsights.com",
    "owler.com", "zoominfo.com", "tracxn.com", "dealroom.co",
    "theinformation.com", "protocol.com", "venturebeat.com",
}
ABOUT_PATHS = (
    "/about", "/about-us", "/about/company", "/about/us",
    "/company", "/company/about", "/company/our-story", "/company/history",
    "/our-story", "/our-company", "/our-history", "/who-we-are",
    "/about/our-story", "/about/history", "/en/about", "/en/company",
    "/en/company/history",
    "/press", "/newsroom", "/company/press",
)
ABOUT_HREF = re.compile(
    r"/(?:about(?:-us)?|our-story|our-company|our-history|who-we-are|newsroom|press)(?:/|$)"
    r"|/company(?:/(?:about|our-story|who-we-are|press|history))?/?$",
    re.I,
)
YEAR_PAGE_SKIP = re.compile(
    r"/(?:careers|jobs|login|signin|sign-up|signup|blog|customers|pricing|legal)(?:/|$)",
    re.I,
)
_CORP_SUFFIX = re.compile(
    r""",?\s+(?:inc\.?|llc|l\.l\.c\.?|ltd\.?|corp\.?|corporation|co\.?|"""
    r"""plc|gmbh|s\.?a\.?|n\.?v\.?|ag|ab|oy|k\.?k\.?|limited|company)$""",
    re.I,
)


# First-party DPA / processor-terms pages only. Privacy, cookies, and portal
# hosts are not a DPA. Product pages that say "data processing" are not a DPA.
PORTAL_VENDOR_HOSTS = {
    "safebase.io", "safebase.us", "safebase.com",
    "conveyor.com", "conveyorhq.com",
    "securitypal.com",
    "whistic.com",
    "secureframe.com",
    "secureframetrust.com",
    "sprinto.com",
    "trust.site",
    "vantatrust.com",
    "drata.com",
    "trustcloud.ai",
    "wolfia.com",
}
STATUS_PLATFORM_SUFFIXES = (
    ".statuspage.io",
    ".instatus.com",
    ".instatus.app",
    ".betteruptime.com",
    ".betterstack.com",
    ".statuscast.com",
    ".status.io",
    ".statuspal.io",
)
STATUS_MARKETING_HOSTS = {
    "statuspage.io",
    "www.statuspage.io",
    "instatus.com",
    "www.instatus.com",
    "betterstack.com",
    "www.betterstack.com",
    "betteruptime.com",
    "www.betteruptime.com",
    "status.io",
    "www.status.io",
    "statuspal.io",
    "www.statuspal.io",
}
SOCIAL_NEWS_HOSTS = {
    "twitter.com", "x.com", "t.co", "facebook.com", "linkedin.com",
    "medium.com", "youtube.com", "youtu.be", "reddit.com",
    "news.ycombinator.com", "techcrunch.com", "theverge.com", "wired.com",
    "reuters.com", "bloomberg.com", "nytimes.com", "wsj.com", "forbes.com",
    "cnn.com", "bbc.com", "bbc.co.uk", "theguardian.com", "cnbc.com",
    "businessinsider.com", "zdnet.com", "theregister.com",
}
STATUS_PATH_RE = re.compile(
    r"^/(?:[a-z]{2}(?:-[a-z]{2})?/)?(?:status|system-status|service-status|status-page)(?:/|\.html?)?$",
    re.I,
)
STATUS_DEAD_PATH_RE = re.compile(
    r"/(?:inactive|page-deleted|team-only|private-only|access/login|"
    r"admin(?:/|$)|sessions?/sign[_-]?in|(?:sign[_-]?in|log[_-]?in)(?:/|$|\?))",
    re.I,
)
STATUS_DEAD_BODY_RE = re.compile(
    r"\b(?:this page is (?:currently )?inactive|page (?:has been )?deleted|"
    r"no longer active|status page is inactive|this status page is (?:private|inactive)|"
    r"team[- ]only|page deleted)\b",
    re.I,
)
STATUS_GENERIC_PLATFORM_HOSTS = {
    "corporate.statuspage.io",
    "business.statuspage.io",
    "meta.statuspage.io",
    "manage.statuspage.io",
    "api.statuspage.io",
}
STATUS_TITLE_RE = re.compile(
    r"\b(?:status page|system status|service status|platform status|"
    r"current status|incident status|status dashboard)\b|"
    r"^\s*[\w .&'-]{2,40}\s+status\s*$",
    re.I,
)
STATUS_LINK_TEXT_RE = re.compile(
    r"\b(?:status page|system status|service status|platform status|"
    r"current status|incident status)\b",
    re.I,
)
STATUS_BODY_RE = re.compile(
    r"\b(?:all systems operational|system status|service status|status page|"
    r"current status|past incidents?|subscribe to updates|"
    r"degraded performance|scheduled maintenance)\b",
    re.I,
)
STATUS_MARKETING_RE = re.compile(
    r"\b(?:create (?:a |your )?status page|statuspage pricing|"
    r"get started with statuspage|atlassian statuspage|"
    r"the (?:best )?status page (?:software|product|tool))\b",
    re.I,
)
STATUS_URL_IN_HTML_RE = re.compile(
    r"https?://(?:status\.[^\s\"'<>]+|[^\s\"'<>]+\.statuspage\.io|"
    r"[^\s\"'<>]+-status\.[^\s\"'<>]+|[^\s\"'<>]+status\.[^\s\"'<>]+)",
    re.I,
)
STOP_TOKENS = {
    "inc", "llc", "ltd", "the", "and", "for", "com", "www", "app", "ai",
    "io", "co", "net", "org", "corp", "group", "holdings", "company",
    "software", "systems", "technologies", "technology", "labs", "lab",
}
DPA_PATH_RE = re.compile(
    r"(?:data[-_ ]?process(?:ing)?[-_ ]?(?:addendum|agreement|terms|annex)|"
    r"(?:^|/)dpa(?:/|\.pdf|$|\?|-)|"
    r"processor[-_ ](?:addendum|agreement|terms)|"
    r"processing[-_ ](?:addendum|agreement)|"
    r"gdpr[-_ ]?(?:dpa|addendum))",
    re.I,
)
DPA_STRONG_PATH_RE = re.compile(
    r"(?:data[-_ ]?process(?:ing)?[-_ ]?(?:addendum|agreement)|"
    r"processor[-_ ](?:addendum|agreement|terms)|"
    r"processing[-_ ](?:addendum|agreement)|"
    r"dpa[-_ ]?(?:addendum|agreement))",
    re.I,
)
DPA_TITLE_RE = re.compile(
    r"\b(?:data[- ]processing[- ](?:addendum|agreement|terms|annex)|"
    r"dpa(?:\s+addendum)?|"
    r"processor[- ](?:terms|addendum|agreement)|"
    r"processing[- ](?:addendum|agreement))\b",
    re.I,
)
DPA_BODY_RE = re.compile(
    r"\b(?:data[- ]processing[- ](?:addendum|agreement)|"
    r"this dpa|"
    r"article\s*28|"
    r"standard contractual clauses|"
    r"processor[- ](?:terms|addendum|agreement)|"
    r"sub-?process(?:or|ing))\b",
    re.I,
)
VENDOR_FACING_DPA_RE = re.compile(
    r"\b(?:for(?:\s+our)?\s+vendors?|vendor[- ]dpa|dpa for \w+ vendors?|"
    r"supplier[- ](?:dpa|addendum)|previous dpa)\b",
    re.I,
)
DPA_LINK_TEXT_RE = re.compile(
    r"\b(?:data[- ]processing[- ](?:addendum|agreement|terms|annex)|"
    r"dpa(?:\s+addendum)?|"
    r"processor[- ](?:terms|addendum|agreement)|"
    r"gdpr[- ](?:dpa|addendum))\b",
    re.I,
)
A_TAG_RE = re.compile(
    r"""<a\b[^>]*href\s*=\s*['"]([^"'#]+)['"][^>]*>(.*?)</a>""",
    re.I | re.S,
)
ITEM_UID_RE = re.compile(r"(?:[?&]|/)itemUid=|(?:[?&])itemName=", re.I)
DPA_WELL_KNOWN_PATHS = (
    "/dpa",
    "/legal/dpa",
    "/legal/data-processing-addendum",
    "/legal/data-processing-agreement",
    "/data-processing-addendum",
    "/data-processing-agreement",
    "/policies/data-processing-addendum",
    "/policies/data-processing-agreement",
    "/policies/dpa",
    "/terms/dpa",
    "/company/dpa",
    "/gdpr/dpa",
    "/legal/gdpr/dpa",
    "/privacy/dpa",
    "/legal/processor-terms",
    "/legal/data-processing",
    "/data-processing",
)
SUB_PATH_RE = re.compile(r"sub-?process|service-providers?", re.I)
SUB_LINK_TEXT_RE = re.compile(
    r"\b(?:sub-?processors?(?:\s+list)?|service providers?)\b",
    re.I,
)
SUBPROCESSOR_WELL_KNOWN_PATHS = (
    "/subprocessors",
    "/sub-processors",
    "/legal/subprocessors",
    "/legal/sub-processors",
    "/legal/service-providers",
    "/privacy/subprocessors",
    "/company/subprocessors",
    "/trust/subprocessors",
    "/legal/sub-processors-page",
)



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
    "anthropic.com": ["claude.com"],
    "episerver.com": ["optimizely.com"],
    "neon.tech": ["neon.com"],
    "payu.pl": ["poland.payu.com"],
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
    if not url or not str(url).strip().startswith("http") or ANNOTATED_URL_RE.search(url) or re.search(r"\s", url):
        return {
            "url": url, "ok": False, "status": 0, "final_url": url,
            "title": "", "text": "", "meta": "", "hrefs": [], "ctype": "",
            "fetched_at": utc_now(), "raw_head": "", "html": "",
        }
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
        "html": "",
    }
    if "security.txt" in url.lower():
        rec["text"] = html[:8000]
        rec["raw_head"] = html[:4000]
    elif re.search(r"sub-?process|service-providers?", url, re.I) or "<table" in html.lower():
        rec["html"] = html[:PROCESSOR_BODY]
        rec["text"] = strip_tags(html)[:80000]
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


def _name_core(s: str) -> str:
    s = re.sub(r"\s*\([^)]*\)\s*", " ", s or "")
    s = _CORP_SUFFIX.sub("", s)
    s = re.sub(r"[^\w\s&+.]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def title_close(wiki_title: str, name: str) -> bool:
    """Exact core-name match only. 'Manhattan' is not Manhattan Associates."""
    a, b = _name_core(wiki_title), _name_core(name)
    return bool(a and b and a == b)



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


PORTAL_PROCESSOR_IDS = {
    "safebase", "safe-base", "vanta", "conveyor", "wolfia", "drata",
    "securitypal", "secureframe", "whistic", "sprinto", "trustcloud", "vendict",
}
ITEM_UID_RE = re.compile(r"(?:[?&]|/)itemUid=|(?:[?&])itemName=", re.I)
ANNOTATED_URL_RE = re.compile(r"\s+\(")
TABLE_RE = re.compile(r"<table\b[^>]*>.*?</table>", re.I | re.S)
TR_RE = re.compile(r"<tr\b[^>]*>.*?</tr>", re.I | re.S)
CELL_RE = re.compile(r"<t[hd]\b[^>]*>.*?</t[hd]>", re.I | re.S)
NAME_HEADER_RE = re.compile(
    r"\b(name(?: of sub-?processors?)?|sub-?processors?|entity(?: name)?|"
    r"third[- ]party(?: entity)?|vendor|provider|company|processor|"
    r"organisation|organization|aws entity)\b",
    re.I,
)
NOT_NAME_HEADER_RE = re.compile(
    r"\b(location|country|region|purpose|description|processing|product|"
    r"service\(s\)|data|securit|categor|nature)\b",
    re.I,
)
LEGAL_SUFFIX_RE = re.compile(
    r"\b(inc|incorporated|ltd|llc|gmbh|corp|corporation|pbc|plc|s\.?a\.?|"
    r"b\.?v\.?|pty|limited|co|kg|oy|ab|ag|kk|nv)\b\.?",
    re.I,
)
GEO_NAME_RE = re.compile(
    r"^(united states|usa|u\.s\.a?\.?|uk|u\.k\.|united kingdom|ireland|"
    r"germany|france|australia|canada|india|japan|brazil|global|worldwide|"
    r"european union|europe|asia|emea|amer|apac|north america|south america|"
    r"eu|eea|switzerland|netherlands|singapore|israel|sweden|spain|italy|"
    r"belgium|finland|poland|austria|denmark|norway|new zealand|mexico|"
    r"south korea|korea|taiwan|hong kong|uae|saudi arabia|south africa|"
    r"oceania|usa\*?|"
    r"usa, eu|uk \(.*|aus)$",
    re.I,
)
PURPOSE_LEAD_RE = re.compile(
    r"^(personal data|prevention of|provision of|if |connectivity |"
    r"automation and|routing and|streaming and|speech |text to |"
    r"data storage|data analytics|scheduling and|outbound/|"
    r"infrastructure provider|vendor for|transcription |"
    r"phone numbers|system and event|operational monitoring|"
    r"hosting and|all services?\b)",
    re.I,
)
PRODUCTISH_RE = re.compile(
    r"\b(programmable|campaigns|channel|flex|verify|engage|reports|"
    r"whatsapp|applicable service|subject matter|nature and purpose|"
    r"location\(s\) of processing|external links|sendgrid services|"
    r"compliance reports|conversational intelligence|google rcs|"
    r"email \(|cdp \()\b",
    re.I,
)
HEADERISH_RE = re.compile(
    r"^(applicable cloud products|nature and purpose|categories of|"
    r"location of processing|security measures|user support|"
    r"hosting and infrastructure|affiliates?$|third[- ]part|"
    r"aws (entity|service|development entities)|entity$|name$|"
    r"service provider|data privacy|data security|cdp\b|"
    r"data center services)\b",
    re.I,
)
PROVIDER_SECTION_RE = re.compile(r"(service )?providers$", re.I)
SPLIT_CELL_RE = re.compile(r"\s*[—–-]{3,}\s*")
COPY_SMALL_RE = re.compile(
    r'<span class="copy-small">([^<]+)</span>',
    re.I,
)
CSSISH_RE = re.compile(r"[{}]|font-family|padding:|min-width|--zds")


def slugify_processor(name: str) -> str:
    s = LEGAL_SUFFIX_RE.sub(" ", name or "")
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:60]


UI_NAME_TAIL_RE = re.compile(
    r"\s+(?:"
    r"sub-?processor lists?\s*>?|"
    r"no subprocessors|"
    r"available upon request|"
    r"subprocessors?\s*>|"
    r"updated"
    r")\s*$",
    re.I,
)


def cell_text(raw: str) -> str:
    t = strip_tags(raw or "")
    t = re.sub(r"[*†‡]+", "", t)
    t = re.sub(r"\s+", " ", t).strip(" \t.,;:|")
    t = UI_NAME_TAIL_RE.sub("", t).strip(" \t.,;:|")
    t = re.sub(r"\b(\S+)(?:\s+\1)+\b", r"\1", t)
    return t


def looks_like_css(s: str) -> bool:
    return bool(CSSISH_RE.search(s or ""))


def is_portal_processor(pid: str, name: str) -> bool:
    blob = f"{pid} {name}".lower()
    if pid in PORTAL_PROCESSOR_IDS:
        return True
    return bool(VENDOR_WORDS.search(blob))


def is_self_processor(name: str, pid: str, company: dict) -> bool:
    slug = company.get("slug") or ""
    cname = (company.get("name") or "").strip().lower()
    n = (name or "").strip().lower()
    own = {slug}
    if slug == "new-relic":
        own.add("newrelic")
    if slug == "amazon-web-services":
        own.add("aws")
    if pid in own:
        return True
    if cname and (n == cname or n.startswith(cname + " ") or n.startswith(cname + ",") or n.startswith(cname + ".")):
        return True
    ns = slugify_processor(name)
    if ns and slug and (ns == slug or ns.startswith(slug + "-")):
        return True
    first = (cname.split() or [""])[0]
    if first and len(first) >= 3 and n.startswith(first) and LEGAL_SUFFIX_RE.search(n):
        return True
    return False


MONTH_NAME = (
    r"january|february|march|april|may|june|july|august|september|"
    r"october|november|december|jan|feb|mar|apr|jun|jul|aug|sept?|oct|nov|dec"
)
DATE_HEADER_RE = re.compile(r"^(date(?: of change)?|effective date)$", re.I)
DATE_NAME_RE = re.compile(
    rf"^(?:(?:19|20|21)\d{{2}}|\d{{4}}-\d{{2}}-\d{{2}}|"
    rf"\d{{1,2}}[./]\d{{1,2}}[./](?:\d{{2}}|\d{{4}})|"
    rf"\d{{1,2}}[\s.\-]+(?:{MONTH_NAME})[\s.\-]+\d{{4}}|"
    rf"(?:{MONTH_NAME})[\s.\-]+\d{{1,2}},?[\s.\-]+\d{{4}}|"
    rf"(?:{MONTH_NAME})[\s.\-]+\d{{4}})$",
    re.I,
)


def looks_like_date_name(name: str) -> bool:
    """Calendar dates and date-column headers are not processor names."""
    t = re.sub(r"\s+", " ", (name or "").strip())
    if not t:
        return False
    if DATE_HEADER_RE.match(t):
        return True
    if DATE_NAME_RE.match(t):
        return True
    spaced = re.sub(r"[-_]+", " ", t)
    if spaced != t and DATE_NAME_RE.match(spaced):
        return True
    return False


def looks_like_org_name(name: str) -> bool:
    t = (name or "").strip()
    if not t or looks_like_css(t) or looks_like_date_name(t):
        return False
    if len(t) < 2 or len(t) > 80:
        return False
    if GEO_NAME_RE.match(t):
        return False
    # Country lists ("Germany, Austria or Switzerland") are not organizations.
    geo_parts = [p for p in re.split(r"\s*(?:,|/|;|\bor\b)\s*", t, flags=re.I) if p]
    if len(geo_parts) >= 2 and all(GEO_NAME_RE.match(p) for p in geo_parts):
        return False
    if PURPOSE_LEAD_RE.search(t) or PRODUCTISH_RE.search(t) or HEADERISH_RE.search(t):
        return False
    if t.lower() in {"name", "entity", "vendor", "provider", "subprocessor", "sub-processor", "location"}:
        return False
    if PROVIDER_SECTION_RE.search(t) and not LEGAL_SUFFIX_RE.search(t):
        return False
    words = t.split()
    if len(words) > 8:
        return False
    if t.endswith(".") and not LEGAL_SUFFIX_RE.search(t):
        return False
    if not re.search(r"[A-Za-z]", t):
        return False
    return True


def match_processor(name: str, register: dict[str, dict] | None = None) -> tuple[str, str]:
    """Stable id plus the published name. Catalog when an alias hits; else slugify."""
    published = cell_text(name)
    for pid, catalog_name, _d, pats in PROC_COMPILED:
        if any(p.search(published) for p in pats):
            return pid, published
    low = published.lower()
    if register:
        for slug, row in register.items():
            cname = (row.get("name") or "").strip().lower()
            if not cname:
                continue
            if low == cname or re.match(
                re.escape(cname) + r"(,?\s+(inc|llc|ltd|gmbh|pbc|corp|limited)\b.*)?$",
                low,
                re.I,
            ):
                return slug, published
    pid = slugify_processor(published) or re.sub(r"[^a-z0-9]+", "-", published.lower()).strip("-")
    return pid, published


def name_column_index(headers: list[str]) -> int:
    for i, h in enumerate(headers):
        if NAME_HEADER_RE.search(h) and not NOT_NAME_HEADER_RE.search(h):
            return i
    for i, h in enumerate(headers):
        if re.fullmatch(r"(name|entity|sub-?processors?|vendor|provider|aws entity)s?", h.strip(), re.I):
            return i
    return 0


def names_from_tables(html: str) -> list[str]:
    found, seen = [], set()
    for table in TABLE_RE.findall(html or ""):
        rows = TR_RE.findall(table)
        if not rows:
            continue
        header_cells = [cell_text(c) for c in CELL_RE.findall(rows[0])]
        if header_cells and any(NAME_HEADER_RE.search(h) for h in header_cells):
            col = name_column_index(header_cells)
            data_rows = rows[1:]
        elif header_cells and not looks_like_css(header_cells[0]) and looks_like_org_name(header_cells[0]):
            col = 0
            data_rows = rows
        else:
            col = 0
            data_rows = rows[1:] if header_cells else rows
        for row in data_rows:
            cells = [cell_text(c) for c in CELL_RE.findall(row)]
            if not cells:
                continue
            # Section banners are one cell in an otherwise multi-column table.
            if len(cells) == 1 and len(header_cells) > 1:
                continue
            if len(cells) == 1 and not looks_like_org_name(cells[0]):
                continue
            raw = cells[col] if col < len(cells) else cells[0]
            parts = [cell_text(p) for p in SPLIT_CELL_RE.split(raw)] if SPLIT_CELL_RE.search(raw) else [raw]
            for part in parts:
                catalog_hit = any(any(p.search(part) for p in pats) for _i, _n, _d, pats in PROC_COMPILED)
                if looks_like_date_name(part):
                    continue
                if not looks_like_org_name(part) and not catalog_hit:
                    continue
                key = part.lower()
                if key not in seen:
                    seen.add(key)
                    found.append(part)
    return found


def names_from_labeled_spans(html: str) -> list[str]:
    found, seen = [], set()
    for raw in COPY_SMALL_RE.findall(html or ""):
        name = cell_text(raw)
        if not looks_like_org_name(name):
            continue
        if len(name.split()) > 4 and not LEGAL_SUFFIX_RE.search(name):
            continue
        key = name.lower()
        if key not in seen:
            seen.add(key)
            found.append(name)
    return found


def non_org_list_page_reason(title: str, text: str, html: str) -> str | None:
    """SCC annex / OneTrust cookie / CCPA data-category tables are not named lists.

    Concrete PR 263 failure signatures only. A DPA that also prints
    organization names (Clazar-style) is not refused.
    """
    blob = f"{title}\n{text[:20000]}\n{(html or '')[:12000]}".lower()
    if "my_onetrust_groups" in blob:
        return "cookie-table"
    if (
        "data category" in blob
        and "geolocation data" in blob
        and "commercial information" in blob
    ):
        return "data-category-table"
    if (
        "role (controller/processor)" in blob
        and "company number or equivalent" in blob
    ):
        return "legal-annex"
    return None


def cited_list_skip_reason(url: str, rec: dict, company: dict) -> str | None:
    if not url or not str(url).strip().startswith("http"):
        return "not-a-url"
    if ANNOTATED_URL_RE.search(url):
        return "annotated-url"
    if ITEM_UID_RE.search(url) or ITEM_UID_RE.search(rec.get("final_url") or ""):
        return "safebase-itemuid"
    ctype = (rec.get("ctype") or "").lower()
    if url.lower().endswith(".pdf") or "pdf" in ctype:
        return "pdf"
    if not rec.get("ok") or rec.get("status") != 200:
        return "fetch-failed"
    title, text = rec.get("title") or "", rec.get("text") or ""
    if looks_like_login_wall(title, text) or looks_dead(title, text):
        return "login-wall" if looks_like_login_wall(title, text) else "dead-page"
    if not is_first_party_list_url(url, rec.get("final_url") or url, company):
        return "not-first-party"
    html = rec.get("html") or ""
    if VENDOR_WORDS.search(title) and not TABLE_RE.search(html):
        if len(text) < 3000 or "manifestPreload" in html or JS_JUNK.search(html[:4000]):
            return "js-portal"
    if "manifestPreload" in html and not TABLE_RE.search(html) and len(text) < 2000:
        return "js-portal"
    page_skip = non_org_list_page_reason(title, text, html)
    if page_skip:
        return page_skip
    return None


def is_first_party_list_url(url: str, final_url: str, company: dict) -> bool:
    hosts = set(hosts_for(company))
    regs = {registrable(h) for h in hosts}
    for raw in (url, final_url):
        h = host_of(raw)
        if not h:
            continue
        if h in hosts or registrable(h) in regs:
            return True
        for known in hosts | regs:
            if h.endswith("." + known):
                return True
    return False


def keep_org_processor_rows(
    rows: list[tuple[str, str, str]],
) -> list[tuple[str, str, str]]:
    """Drop legal-annex / cookie / data-category headings. Refuse a junk-majority table."""
    if not rows:
        return []
    junk = sum(1 for pid, name, _ev in rows if skip_processor(pid, name))
    if junk >= 3 and junk * 2 >= len(rows):
        return []
    return [
        (pid, name, ev)
        for pid, name, ev in rows
        if not skip_processor(pid, name)
    ]


def published_processors_from_html(
    html: str,
    text: str,
    company: dict,
    register: dict[str, dict] | None = None,
) -> list[tuple[str, str, str]]:
    """Verbatim names from a first-party HTML list. Tables first; no invented edges."""
    names = names_from_tables(html)
    if not names:
        names = names_from_labeled_spans(html)
    if not names:
        return []
    out, seen = [], set()
    for raw in names:
        pid, published = match_processor(raw, register)
        if not pid or not published:
            continue
        if is_portal_processor(pid, published):
            continue
        if is_self_processor(published, pid, company):
            continue
        if pid in seen:
            continue
        seen.add(pid)
        out.append((pid, published, published))
    return keep_org_processor_rows(out)


def processors_from_company(
    company: dict,
    pages: dict,
    links: dict,
    register: dict[str, dict] | None = None,
) -> list[tuple[str, str, str]]:
    rec = pages.get("subprocessors")
    url = links.get("subprocessors")
    if not rec or not url:
        return []
    if not is_subprocessor_page(url, rec.get("title") or "", rec.get("text") or ""):
        if not re.search(r"sub-?process|service-providers?", url, re.I):
            return []
    reason = cited_list_skip_reason(url, rec, company)
    if reason:
        return []
    html = rec.get("html") or ""
    text = rec.get("text") or ""
    return published_processors_from_html(html, text, company, register)


def is_subprocessor_page(url: str, title: str, text: str) -> bool:
    blob = f"{url} {title} {text[:5000]}".lower()
    return bool(re.search(r"sub-?\s*process", blob))


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


def bounty_urls_from_security_txt(text: str) -> list[str]:
    """Program URLs named in security.txt. Hiring and encryption stay out."""
    out, seen = [], set()
    for m in SEC_TXT_LINE.finditer(text or ""):
        field, val = m.group(1).strip().lower(), m.group(2).strip()
        if field in SEC_TXT_SKIP_FIELDS or not val.startswith("http"):
            continue
        if val in seen:
            continue
        seen.add(val)
        out.append(val)
    return out


def bounty_from_security_txt(text: str):
    """Policy/Contact/Bug Bounty HTTP URLs. Strip HTML tails. Hiring stays out."""
    if not text:
        return None
    bounty_re = re.compile(
        r"hackerone|bugcrowd|yeswehack|intigriti|bug-?bounty|bugbounty|\bbounty\b|"
        r"responsible-?disclosure|vulnerabilit|bughunters|(?:^|/)(?:vdp|vrp|bounty)"
        r"|vdp\.|bounty\.|/\bvdp\b|\bvdp/|psirt|security-disclosure|disclosure-policy",
        re.I,
    )
    for pat in (SEC_POLICY, SEC_CONTACT):
        for m in pat.finditer(text):
            val = field_url(m.group(1))
            if val.startswith("http") and bounty_re.search(val):
                return val
    for m in SEC_TXT_LINE.finditer(text):
        field, raw = m.group(1).strip().lower(), m.group(2)
        if field in SEC_TXT_SKIP_FIELDS:
            continue
        val = field_url(raw)
        if not val.startswith("http"):
            continue
        if field in {"bug bounty", "bug-bounty", "bugbounty"} or bounty_re.search(val):
            return val
    return None


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


# First-party HTML list parsers (same rules as PR 21). Catalog text-scan is
# not used here — a portal chrome mention is not a named processor.
PORTAL_PROCESSOR_IDS = {
    "safebase", "safe-base", "vanta", "conveyor", "wolfia", "drata",
    "securitypal", "secureframe", "whistic", "sprinto", "trustcloud", "vendict",
}
ITEM_UID_RE = re.compile(r"(?:[?&]|/)itemUid=|(?:[?&])itemName=", re.I)
ANNOTATED_URL_RE = re.compile(r"\s+\(")
TABLE_RE = re.compile(r"<table\b[^>]*>.*?</table>", re.I | re.S)
TR_RE = re.compile(r"<tr\b[^>]*>.*?</tr>", re.I | re.S)
CELL_RE = re.compile(r"<t[hd]\b[^>]*>.*?</t[hd]>", re.I | re.S)
NAME_HEADER_RE = re.compile(
    r"\b(name(?: of sub-?processors?)?|sub-?processors?|entity(?: name)?|"
    r"third[- ]party(?: entity)?|vendor|provider|company|processor|"
    r"organisation|organization|aws entity)\b",
    re.I,
)
NOT_NAME_HEADER_RE = re.compile(
    r"\b(location|country|region|purpose|description|processing|product|"
    r"service\(s\)|data|securit|categor|nature)\b",
    re.I,
)
LEGAL_SUFFIX_RE = re.compile(
    r"\b(inc|incorporated|ltd|llc|gmbh|corp|corporation|pbc|plc|s\.?a\.?|"
    r"b\.?v\.?|pty|limited|co|kg|oy|ab|ag|kk|nv)\b\.?",
    re.I,
)
GEO_NAME_RE = re.compile(
    r"^(united states|usa|u\.s\.a?\.?|uk|u\.k\.|united kingdom|ireland|"
    r"germany|france|australia|canada|india|japan|brazil|global|worldwide|"
    r"european union|europe|asia|emea|amer|apac|north america|south america|"
    r"eu|eea|switzerland|netherlands|singapore|israel|sweden|spain|italy|"
    r"belgium|finland|poland|austria|denmark|norway|new zealand|mexico|"
    r"south korea|korea|taiwan|hong kong|uae|saudi arabia|south africa|"
    r"oceania|usa\*?|"
    r"usa, eu|uk \(.*|aus)$",
    re.I,
)
PURPOSE_LEAD_RE = re.compile(
    r"^(personal data|prevention of|provision of|if |connectivity |"
    r"automation and|routing and|streaming and|speech |text to |"
    r"data storage|data analytics|scheduling and|outbound/|"
    r"infrastructure provider|vendor for|transcription |"
    r"phone numbers|system and event|operational monitoring|"
    r"hosting and|all services?\b)",
    re.I,
)
PRODUCTISH_RE = re.compile(
    r"\b(programmable|campaigns|channel|flex|verify|engage|reports|"
    r"whatsapp|applicable service|subject matter|nature and purpose|"
    r"location\(s\) of processing|external links|sendgrid services|"
    r"compliance reports|conversational intelligence|google rcs|"
    r"email \(|cdp \()\b",
    re.I,
)
HEADERISH_RE = re.compile(
    r"^(applicable cloud products|nature and purpose|categories of|"
    r"location of processing|security measures|user support|"
    r"hosting and infrastructure|affiliates?$|third[- ]part|"
    r"aws (entity|service|development entities)|entity$|name$|"
    r"service provider|data privacy|data security|cdp\b|"
    r"data center services)\b",
    re.I,
)
PROVIDER_SECTION_RE = re.compile(r"(service )?providers$", re.I)
SPLIT_CELL_RE = re.compile(r"\s*[—–-]{3,}\s*")
COPY_SMALL_RE = re.compile(
    r'<span class="copy-small">([^<]+)</span>',
    re.I,
)
CSSISH_RE = re.compile(r"[{}]|font-family|padding:|min-width|--zds")
INSTRUMENT_LINK_KEYS = (
    "dpa", "subprocessors", "status", "privacy", "bug_bounty", "security_txt",
)


def slugify_processor(name: str) -> str:
    s = LEGAL_SUFFIX_RE.sub(" ", name or "")
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:60]


UI_NAME_TAIL_RE = re.compile(
    r"\s+(?:"
    r"sub-?processor lists?\s*>?|"
    r"no subprocessors|"
    r"available upon request|"
    r"subprocessors?\s*>|"
    r"updated"
    r")\s*$",
    re.I,
)


def cell_text(raw: str) -> str:
    t = strip_tags(raw or "")
    t = re.sub(r"[*†‡]+", "", t)
    t = re.sub(r"\s+", " ", t).strip(" \t.,;:|")
    t = UI_NAME_TAIL_RE.sub("", t).strip(" \t.,;:|")
    t = re.sub(r"\b(\S+)(?:\s+\1)+\b", r"\1", t)
    return t


def looks_like_css(s: str) -> bool:
    return bool(CSSISH_RE.search(s or ""))


def is_portal_processor(pid: str, name: str) -> bool:
    blob = f"{pid} {name}".lower()
    if pid in PORTAL_PROCESSOR_IDS:
        return True
    return bool(VENDOR_WORDS.search(blob))


def is_self_processor(name: str, pid: str, company: dict) -> bool:
    slug = company.get("slug") or ""
    cname = (company.get("name") or "").strip().lower()
    n = (name or "").strip().lower()
    own = {slug}
    if slug == "new-relic":
        own.add("newrelic")
    if slug == "amazon-web-services":
        own.add("aws")
    if pid in own:
        return True
    if cname and (n == cname or n.startswith(cname + " ") or n.startswith(cname + ",") or n.startswith(cname + ".")):
        return True
    ns = slugify_processor(name)
    if ns and slug and (ns == slug or ns.startswith(slug + "-")):
        return True
    first = (cname.split() or [""])[0]
    if first and len(first) >= 3 and n.startswith(first) and LEGAL_SUFFIX_RE.search(n):
        return True
    return False


MONTH_NAME = (
    r"january|february|march|april|may|june|july|august|september|"
    r"october|november|december|jan|feb|mar|apr|jun|jul|aug|sept?|oct|nov|dec"
)
DATE_HEADER_RE = re.compile(r"^(date(?: of change)?|effective date)$", re.I)
DATE_NAME_RE = re.compile(
    rf"^(?:(?:19|20|21)\d{{2}}|\d{{4}}-\d{{2}}-\d{{2}}|"
    rf"\d{{1,2}}[./]\d{{1,2}}[./](?:\d{{2}}|\d{{4}})|"
    rf"\d{{1,2}}[\s.\-]+(?:{MONTH_NAME})[\s.\-]+\d{{4}}|"
    rf"(?:{MONTH_NAME})[\s.\-]+\d{{1,2}},?[\s.\-]+\d{{4}}|"
    rf"(?:{MONTH_NAME})[\s.\-]+\d{{4}})$",
    re.I,
)


def looks_like_date_name(name: str) -> bool:
    """Calendar dates and date-column headers are not processor names."""
    t = re.sub(r"\s+", " ", (name or "").strip())
    if not t:
        return False
    if DATE_HEADER_RE.match(t):
        return True
    if DATE_NAME_RE.match(t):
        return True
    spaced = re.sub(r"[-_]+", " ", t)
    if spaced != t and DATE_NAME_RE.match(spaced):
        return True
    return False


def looks_like_org_name(name: str) -> bool:
    t = (name or "").strip()
    if not t or looks_like_css(t) or looks_like_date_name(t):
        return False
    if len(t) < 2 or len(t) > 80:
        return False
    if GEO_NAME_RE.match(t):
        return False
    # Country lists ("Germany, Austria or Switzerland") are not organizations.
    geo_parts = [p for p in re.split(r"\s*(?:,|/|;|\bor\b)\s*", t, flags=re.I) if p]
    if len(geo_parts) >= 2 and all(GEO_NAME_RE.match(p) for p in geo_parts):
        return False
    if PURPOSE_LEAD_RE.search(t) or PRODUCTISH_RE.search(t) or HEADERISH_RE.search(t):
        return False
    if t.lower() in {"name", "entity", "vendor", "provider", "subprocessor", "sub-processor", "location"}:
        return False
    if PROVIDER_SECTION_RE.search(t) and not LEGAL_SUFFIX_RE.search(t):
        return False
    words = t.split()
    if len(words) > 8:
        return False
    if t.endswith(".") and not LEGAL_SUFFIX_RE.search(t):
        return False
    if not re.search(r"[A-Za-z]", t):
        return False
    return True


def match_processor(name: str, register: dict[str, dict] | None = None) -> tuple[str, str]:
    """Stable id plus the published name. Catalog when an alias hits; else slugify."""
    published = cell_text(name)
    for pid, _catalog_name, _d, pats in PROC_COMPILED:
        if any(p.search(published) for p in pats):
            return pid, published
    low = published.lower()
    if register:
        for slug, row in register.items():
            cname = (row.get("name") or "").strip().lower()
            if not cname:
                continue
            if low == cname or re.match(
                re.escape(cname) + r"(,?\s+(inc|llc|ltd|gmbh|pbc|corp|limited)\b.*)?$",
                low,
                re.I,
            ):
                return slug, published
    pid = slugify_processor(published) or re.sub(r"[^a-z0-9]+", "-", published.lower()).strip("-")
    return pid, published


def name_column_index(headers: list[str]) -> int:
    for i, h in enumerate(headers):
        if NAME_HEADER_RE.search(h) and not NOT_NAME_HEADER_RE.search(h):
            return i
    for i, h in enumerate(headers):
        if re.fullmatch(r"(name|entity|sub-?processors?|vendor|provider|aws entity)s?", h.strip(), re.I):
            return i
    return 0


def names_from_tables(html: str) -> list[str]:
    found, seen = [], set()
    for table in TABLE_RE.findall(html or ""):
        rows = TR_RE.findall(table)
        if not rows:
            continue
        header_cells = [cell_text(c) for c in CELL_RE.findall(rows[0])]
        if header_cells and any(NAME_HEADER_RE.search(h) for h in header_cells):
            col = name_column_index(header_cells)
            data_rows = rows[1:]
        elif header_cells and not looks_like_css(header_cells[0]) and looks_like_org_name(header_cells[0]):
            col = 0
            data_rows = rows
        else:
            col = 0
            data_rows = rows[1:] if header_cells else rows
        for row in data_rows:
            cells = [cell_text(c) for c in CELL_RE.findall(row)]
            if not cells:
                continue
            # Section banners are one cell in an otherwise multi-column table.
            if len(cells) == 1 and len(header_cells) > 1:
                continue
            if len(cells) == 1 and not looks_like_org_name(cells[0]):
                continue
            raw = cells[col] if col < len(cells) else cells[0]
            parts = [cell_text(p) for p in SPLIT_CELL_RE.split(raw)] if SPLIT_CELL_RE.search(raw) else [raw]
            for part in parts:
                catalog_hit = any(any(p.search(part) for p in pats) for _i, _n, _d, pats in PROC_COMPILED)
                if looks_like_date_name(part):
                    continue
                if not looks_like_org_name(part) and not catalog_hit:
                    continue
                key = part.lower()
                if key not in seen:
                    seen.add(key)
                    found.append(part)
    return found


def names_from_labeled_spans(html: str) -> list[str]:
    found, seen = [], set()
    for raw in COPY_SMALL_RE.findall(html or ""):
        name = cell_text(raw)
        if not looks_like_org_name(name):
            continue
        if len(name.split()) > 4 and not LEGAL_SUFFIX_RE.search(name):
            continue
        key = name.lower()
        if key not in seen:
            seen.add(key)
            found.append(name)
    return found


def is_first_party_list_url(url: str, final_url: str, company: dict) -> bool:
    hosts = set(hosts_for(company))
    regs = {registrable(h) for h in hosts}
    for raw in (url, final_url):
        h = host_of(raw)
        if not h:
            continue
        if h in hosts or registrable(h) in regs:
            return True
        for known in hosts | regs:
            if h.endswith("." + known):
                return True
    return False


def cited_list_skip_reason(url: str, rec: dict, company: dict) -> str | None:
    if not url or not str(url).strip().startswith("http"):
        return "not-a-url"
    if ANNOTATED_URL_RE.search(url):
        return "annotated-url"
    if ITEM_UID_RE.search(url) or ITEM_UID_RE.search(rec.get("final_url") or ""):
        return "safebase-itemuid"
    ctype = (rec.get("ctype") or "").lower()
    if url.lower().endswith(".pdf") or "pdf" in ctype:
        return "pdf"
    if not rec.get("ok") or rec.get("status") != 200:
        return "fetch-failed"
    title, text = rec.get("title") or "", rec.get("text") or ""
    if looks_like_login_wall(title, text) or looks_dead(title, text):
        return "login-wall" if looks_like_login_wall(title, text) else "dead-page"
    if not is_first_party_list_url(url, rec.get("final_url") or url, company):
        return "not-first-party"
    html = rec.get("html") or ""
    if VENDOR_WORDS.search(title) and not TABLE_RE.search(html):
        if len(text) < 3000 or "manifestPreload" in html or JS_JUNK.search(html[:4000]):
            return "js-portal"
    if "manifestPreload" in html and not TABLE_RE.search(html) and len(text) < 2000:
        return "js-portal"
    page_skip = non_org_list_page_reason(title, text, html)
    if page_skip:
        return page_skip
    return None


def published_processors_from_html(
    html: str,
    text: str,
    company: dict,
    register: dict[str, dict] | None = None,
) -> list[tuple[str, str, str]]:
    """Verbatim names from a first-party HTML list. Tables first; no invented edges."""
    names = names_from_tables(html)
    if not names:
        names = names_from_labeled_spans(html)
    if not names:
        return []
    out, seen = [], set()
    for raw in names:
        pid, published = match_processor(raw, register)
        if not pid or not published:
            continue
        if is_portal_processor(pid, published):
            continue
        if is_self_processor(published, pid, company):
            continue
        if pid in seen:
            continue
        seen.add(pid)
        out.append((pid, published, published))
    return keep_org_processor_rows(out)


def published_processors_from_cited(
    company: dict,
    rec: dict,
    url: str,
    register: dict[str, dict] | None = None,
) -> list[tuple[str, str, str]]:
    """Named processors only from a cited first-party HTML list. Walls stay empty."""
    if not rec or not url:
        return []
    if not is_subprocessor_page(url, rec.get("title") or "", rec.get("text") or ""):
        if not re.search(r"sub-?process|service-providers?", url, re.I):
            return []
    if cited_list_skip_reason(url, rec, company):
        return []
    return published_processors_from_html(
        rec.get("html") or "", rec.get("text") or "", company, register
    )


def fetch_processor_page(url: str) -> dict:
    """Uncached GET that keeps HTML for first-party list parsing."""
    empty = {
        "url": url, "ok": False, "status": 0, "final_url": url,
        "title": "", "text": "", "meta": "", "hrefs": [], "ctype": "",
        "fetched_at": utc_now(), "raw_head": "", "html": "",
    }
    if not url or not str(url).strip().startswith("http") or ANNOTATED_URL_RE.search(url) or re.search(r"\s", url):
        return empty
    fetched = crawl.fetch(url, max_body=PROCESSOR_BODY)
    html = fetched.get("body") or ""
    title = crawl.extract_title(html) if html else ""
    return {
        "url": url,
        "ok": bool(fetched.get("ok")),
        "status": fetched.get("status") or 0,
        "final_url": fetched.get("final_url") or url,
        "title": title,
        "text": strip_tags(html)[:80000] if html else "",
        "meta": extract_meta_desc(html) if html else "",
        "hrefs": extract_hrefs(html, fetched.get("final_url") or url) if html else [],
        "ctype": (fetched.get("headers") or {}).get("content-type", ""),
        "fetched_at": utc_now(),
        "raw_head": "",
        "html": html[:PROCESSOR_BODY] if html else "",
    }


def has_public_page(company: dict) -> bool:
    return bool(company.get("found") and (company.get("trust_url") or company.get("final_url")))


def instrument_links(company: dict) -> dict:
    links = company.get("links") or {}
    return {k: links[k] for k in INSTRUMENT_LINK_KEYS if links.get(k)}


def resolve_year_one(company: dict) -> tuple[int, str] | None:
    """One-company Wikipedia/Wikidata year. Same checks as the batch path."""
    query = WIKI_HINTS.get(company.get("slug") or "", [company.get("name") or ""])[0]
    if not query:
        return None
    data = wiki_api({
        "action": "query", "list": "search", "srsearch": query,
        "srlimit": "5", "format": "json",
    })
    if not data:
        return None
    hosts = hosts_for(company)
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
        p31 = parse_p31(claims)
        if "Q4167410" in p31:
            continue
        sites = parse_p856(claims)
        # One-shot search cannot use the loose title prefix (Manhattan / Sage Publishing).
        # Official website must match the register domain.
        if not website_matches(sites, hosts):
            continue
        source = "https://en.wikipedia.org/wiki/" + title.replace(" ", "_")
        return year, source
    return None


def enrich_one(
    company: dict,
    *,
    resolve_year: bool = True,
    register: dict[str, dict] | None = None,
    probed: dict | None = None,
    year: tuple[int, str] | None = None,
) -> dict:
    """Enrich one found first-party page. Extra facts land only when published.

    Not-found / no-page rows should not call this. If the probe finds nothing
    new, the returned row keeps the caller's page/certs/summary as they were.
    """
    if not has_public_page(company):
        return company
    out = dict(company)
    out["links"] = dict(company.get("links") or {})
    try:
        rec = probed if probed is not None else probe_company(company)
    except Exception:
        return company
    rec = rec or {"links": {}, "pages": {}, "probed": 0}
    links = out["links"]
    for kind, url in (rec.get("links") or {}).items():
        if url:
            links.setdefault(kind, url)
    pages = dict(rec.get("pages") or {})
    if rec.get("probed"):
        out["probed"] = max(int(out.get("probed") or 0), int(rec.get("probed") or 0))

    live_certs = certs_from_pages(company, pages, links)
    if live_certs:
        out["certs"] = live_certs

    sub_url = links.get("subprocessors")
    sub_rec = pages.get("subprocessors")
    if sub_url and (not sub_rec or not sub_rec.get("html")):
        try:
            sub_rec = fetch_processor_page(sub_url)
        except Exception:
            sub_rec = sub_rec or {}
        pages["subprocessors"] = sub_rec
    procs = published_processors_from_cited(company, sub_rec or {}, sub_url or "", register)
    if procs and sub_url:
        out["subprocessors"] = [pid for pid, _n, _e in procs]
        out["_edges"] = [
            {"from": company["slug"], "to": pid, "source_url": sub_url, "evidence": ev}
            for pid, _n, ev in procs
        ]

    if resolve_year and not out.get("founded_year"):
        try:
            year_src = year if year is not None else resolve_year_one(company)
        except Exception:
            year_src = None
        if year_src:
            out["founded_year"] = year_src[0]
            out["founded_source"] = year_src[1]

    prior_links = company.get("links") or {}
    new_instrument = any(
        links.get(k) and links.get(k) != prior_links.get(k) for k in INSTRUMENT_LINK_KEYS
    )
    new_certs = bool(live_certs) and live_certs != list(company.get("certs") or [])
    new_year = bool(out.get("founded_year") and not company.get("founded_year"))
    new_procs = bool(procs)
    if not (new_instrument or new_certs or new_year or new_procs):
        out["links"] = {k: v for k, v in links.items() if v}
        out.pop("_edges", None)
        return out

    page_text = ""
    for key in ("trust", "security"):
        if pages.get(key):
            page_text = pages[key].get("meta") or pages[key].get("text") or ""
            break
    portal = True
    certs = out.get("certs") or []
    founded_year = out.get("founded_year")
    score, tier = score_row(portal, certs, links, founded_year)
    out["disclosure"] = {
        "score": score,
        "tier": tier,
        "factors": disclosure_factors(portal, certs, links, founded_year),
    }
    out["summary"] = clerk_summary(portal, certs, company.get("summary") or "", page_text)
    out["links"] = {k: v for k, v in links.items() if v}
    return out


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
    body.append("Subprocessor edges require a public first-party list URL. Published HTML table names are filed verbatim with that source_url. Catalog aliases only normalize ids. SafeBase itemUid, JS-only, PDF, and login-walled lists stay empty.")
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
        procs = processors_from_company(c, pages, links, {x["slug"]: x for x in companies})
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


def has_filed_names(company: dict, named_from: set[str]) -> bool:
    slug = company.get("slug") or ""
    if slug in named_from:
        return True
    procs = company.get("subprocessors") or []
    if not procs:
        return False
    if len(procs) == 1:
        only = procs[0]
        pid = only.get("id") if isinstance(only, dict) else only
        if is_self_processor(str(only.get("name") if isinstance(only, dict) else only), str(pid or ""), company):
            return False
    return True


def fetch_cited_processor_page(url: str) -> dict:
    rec = fetch_uncached(url, max_body=PROCESSOR_BODY)
    if not rec.get("html") and rec.get("ok"):
        # fetch_uncached already filled html for list URLs; keep a copy if the
        # path was unusual but the body is still a list.
        rec["html"] = rec.get("html") or ""
    return rec


def file_named_from_cited() -> int:
    """Fill empty Named processors tables from URLs already on the company file."""
    t0 = time.time()
    CACHE.mkdir(parents=True, exist_ok=True)
    enr = load_json(DATA / "enriched.json", {})
    subs = load_json(DATA / "subprocessors.json", {})
    companies = list(enr.get("companies") or [])
    register = {c["slug"]: c for c in companies if c.get("slug")}
    edges = list(subs.get("edges") or [])
    nodes = {n["id"]: n for n in (subs.get("nodes") or []) if n.get("id")}
    named_from = {e.get("from") for e in edges if e.get("source_url") and e.get("from")}
    existing_pairs = {(e.get("from"), e.get("to")) for e in edges}

    hole = []
    for c in companies:
        url = (c.get("links") or {}).get("subprocessors") or ""
        if url and not has_filed_names(c, named_from):
            hole.append(c)

    print(f"Cited lists with empty names: {len(hole)}", flush=True)
    filled, skipped = [], []

    def do_one(c):
        url = (c.get("links") or {}).get("subprocessors") or ""
        early = cited_list_skip_reason(
            url,
            {"ok": False, "status": 0, "final_url": url, "title": "", "text": "", "html": "", "ctype": ""},
            c,
        )
        if early in {"not-a-url", "annotated-url", "safebase-itemuid", "pdf", "not-first-party"}:
            return c["slug"], [], early
        try:
            rec = fetch_cited_processor_page(url)
        except Exception:
            return c["slug"], [], "fetch-failed"
        reason = cited_list_skip_reason(url, rec, c)
        if reason:
            return c["slug"], [], reason
        procs = processors_from_company(c, {"subprocessors": rec}, {"subprocessors": url}, register)
        if not procs:
            kind = "js-only" if not rec.get("html") or not TABLE_RE.search(rec.get("html") or "") else "no-published-names"
            if names_from_labeled_spans(rec.get("html") or ""):
                kind = "no-published-names"
            return c["slug"], [], kind
        return c["slug"], procs, None

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = {pool.submit(do_one, c): c for c in hole}
        done = 0
        for fut in as_completed(futs):
            c = futs[fut]
            slug, procs, reason = fut.result()
            done += 1
            if reason or not procs:
                skipped.append((slug, reason or "no-published-names"))
            else:
                filled.append((slug, procs, (c.get("links") or {}).get("subprocessors")))
            if done % 10 == 0 or done == len(futs):
                print(f"  lists {done}/{len(futs)}", flush=True)

    for slug, procs, src in filled:
        row = register[slug]
        row["subprocessors"] = [pid for pid, _n, _e in procs]
        named_from.add(slug)
        for pid, name, ev in procs:
            if (slug, pid) in existing_pairs:
                continue
            edges.append({
                "from": slug,
                "to": pid,
                "source_url": src,
                "evidence": ev,
            })
            existing_pairs.add((slug, pid))
            if pid not in nodes:
                if pid in register:
                    nodes[pid] = {
                        "id": pid,
                        "name": register[pid]["name"],
                        "domain": register[pid].get("domain") or "",
                        "kind": "company",
                        "in_register": True,
                    }
                else:
                    meta = next(((n, d) for i, n, d, _a in PROCESSORS if i == pid), None)
                    nodes[pid] = {
                        "id": pid,
                        "name": meta[0] if meta else name,
                        "domain": meta[1] if meta else "",
                        "kind": "processor",
                        "in_register": False,
                    }

    node_list = list(nodes.values())
    # keep register companies that already had nodes
    for c in companies:
        if c["slug"] not in nodes:
            nodes[c["slug"]] = {
                "id": c["slug"],
                "name": c["name"],
                "domain": c.get("domain") or "",
                "kind": "company",
                "in_register": True,
            }
    node_list = list(nodes.values())

    write_json(DATA / "enriched.json", enr)
    write_json(SITE / "data" / "enriched.json", enr)
    sub_out = {
        "generated_at": subs.get("generated_at") or utc_now(),
        "nodes": node_list,
        "edges": edges,
        "notes": subs.get("notes") or (
            "Filed from public first-party subprocessor lists only. "
            "This is not a complete supply chain. Login-gated lists are not on file."
        ),
    }
    write_json(DATA / "subprocessors.json", sub_out)
    write_json(SITE / "data" / "subprocessors.json", sub_out)

    print(f"filled={len(filled)} skipped={len(skipped)} edges={len(edges)} in {time.time()-t0:.1f}s", flush=True)
    for slug, procs, _src in sorted(filled):
        print(f"  + {slug} {len(procs)}", flush=True)
    for slug, reason in sorted(skipped):
        print(f"  - {slug} {reason}", flush=True)
    return 0


def path_is_privacy_or_cookie_only(path: str) -> bool:
    p = (path or "").lower()
    if DPA_PATH_RE.search(p):
        return False
    return bool(re.search(r"privacy|cookie", p))


def path_is_product_page(path: str) -> bool:
    p = (path or "").lower()
    if re.search(r"/solutions/|/products/", p) and not re.search(
        r"addendum|agreement|/dpa\b", p
    ):
        return True
    return "data-processing-unit" in p


def is_pdf_rec(url: str, rec: dict) -> bool:
    ctype = (rec.get("ctype") or "").lower()
    head = (rec.get("raw_head") or rec.get("text") or "")[:8]
    return "pdf" in ctype or (url or "").lower().endswith(".pdf") or head.startswith("%PDF")


def is_portal_vendor_host(url: str, company: dict) -> bool:
    h = host_of(url)
    if not h:
        return False
    own = {registrable(x) for x in hosts_for(company)}
    if company.get("domain"):
        own.add(registrable(company["domain"]))
    reg = registrable(h)
    if reg in own or h in own:
        return False
    if reg in PORTAL_VENDOR_HOSTS:
        return True
    return any(h.endswith("." + v) for v in PORTAL_VENDOR_HOSTS)


def is_first_party_url(url: str, company: dict | None) -> bool:
    if not company:
        return False
    if is_portal_vendor_host(url, company):
        return False
    hosts = set(hosts_for(company))
    for raw in (company.get("trust_url"), company.get("final_url"), company.get("domain")):
        h = host_of(raw) if raw and str(raw).startswith("http") else (raw or "")
        h = (h or "").lower().removeprefix("www.")
        if h:
            hosts.add(h)
    regs = {registrable(x) for x in hosts if x}
    h = host_of(url)
    if not h:
        return False
    if h in hosts or registrable(h) in regs:
        return True
    return any(h.endswith("." + known) or known.endswith("." + h) for known in (hosts | regs) if known)


def extract_dpa_candidates(html: str, base: str) -> list[str]:
    """Hrefs that look like a DPA, plus destinations whose link text names one."""
    out, seen = [], set()

    def add(u: str) -> None:
        u = (u or "").split("#")[0].strip()
        if not u.startswith("http") or u in seen:
            return
        if ITEM_UID_RE.search(u) and not DPA_PATH_RE.search(u):
            return
        seen.add(u)
        out.append(u)

    for href in extract_hrefs(html, base):
        if DPA_PATH_RE.search(href):
            add(href)
    for m in A_TAG_RE.finditer(html or ""):
        raw, inner = m.group(1).strip(), strip_tags(m.group(2))
        if raw.startswith(("javascript:", "mailto:", "tel:", "data:")):
            continue
        if DPA_LINK_TEXT_RE.search(inner) or re.fullmatch(r"dpa", inner.strip(), re.I):
            add(urljoin(base, raw))
    return out[:40]


def classify_as_dpa(url: str, rec: dict) -> bool:
    """True only when this URL is a published DPA / processor-terms page or PDF."""
    if not rec.get("ok") or rec.get("status") != 200:
        return False
    title, text = rec.get("title") or "", rec.get("text") or ""
    final = rec.get("final_url") or url
    if looks_dead(title, text) or looks_like_login_wall(title, text):
        return False
    if landed_on_home(url, final) and "status." not in host_of(url):
        return False
    path = path_of(final)
    if path_is_product_page(path):
        return False
    if VENDOR_FACING_DPA_RE.search(f"{title} {path} {text[:800]}"):
        return False
    if path_is_privacy_or_cookie_only(path) and not DPA_TITLE_RE.search(title):
        return False
    if ITEM_UID_RE.search(final) and not (DPA_PATH_RE.search(final) or DPA_TITLE_RE.search(title)):
        return False
    pdf = is_pdf_rec(final, rec)
    strong = bool(DPA_STRONG_PATH_RE.search(path) or DPA_STRONG_PATH_RE.search(final))
    weak = bool(re.search(r"(?:^|/)dpa(?:/|\.pdf|$|\?)", path, re.I) or DPA_PATH_RE.search(path))
    title_hit = bool(DPA_TITLE_RE.search(title))
    body_hit = bool(DPA_BODY_RE.search(text[:8000]) or DPA_TITLE_RE.search(text[:2000]))
    if pdf:
        return bool(strong or DPA_PATH_RE.search(path) or title_hit)
    if strong and (title_hit or body_hit):
        return True
    if weak and body_hit:
        return True
    if title_hit and body_hit and not path_is_privacy_or_cookie_only(path):
        return True
    return False


def dpa_probe_urls_for(company: dict) -> list[str]:
    pairs, seen = [], set()

    def add(url: str) -> None:
        u = (url or "").rstrip("/")
        key = u.lower()
        if u.startswith("http") and key not in seen:
            seen.add(key)
            pairs.append(u)

    for domain in hosts_for(company)[:2]:
        for path in DPA_WELL_KNOWN_PATHS:
            add(f"https://{domain}{path}")
    for url, hint in SPECIAL_URLS.get(company.get("slug") or "", []):
        if hint == "dpa":
            add(url)
    return pairs


def apply_dpa_to_row(row: dict, url: str) -> bool:
    """File a DPA URL and add the +8 factor. Leave other factors as they were."""
    links = dict(row.get("links") or {})
    if links.get("dpa"):
        return False
    links["dpa"] = url
    row["links"] = links
    disc = dict(row.get("disclosure") or {})
    factors = dict(disc.get("factors") or {})
    if not factors.get("dpa"):
        factors["dpa"] = 8
        score = min(100, int(disc.get("score") or 0) + 8)
        if not row.get("found"):
            tier = "silent"
        elif score >= 90:
            tier = "complete"
        elif score >= 70:
            tier = "substantial"
        elif score >= 40:
            tier = "on-file"
        else:
            tier = "thin"
        disc["score"] = score
        disc["tier"] = tier
        disc["factors"] = factors
        row["disclosure"] = disc
    return True


def extract_subprocessor_candidates(html: str, base: str) -> list[str]:
    """Hrefs that look like a printed subprocessor list. Portal itemUids stay out."""
    out, seen = [], set()

    def add(u: str) -> None:
        u = (u or "").split("#")[0].strip()
        if not u.startswith("http") or u in seen:
            return
        if ITEM_UID_RE.search(u):
            return
        seen.add(u)
        out.append(u)

    for href in extract_hrefs(html, base):
        if SUB_PATH_RE.search(href):
            add(href)
    for m in A_TAG_RE.finditer(html or ""):
        raw, inner = m.group(1).strip(), strip_tags(m.group(2))
        if raw.startswith(("javascript:", "mailto:", "tel:", "data:")):
            continue
        if SUB_LINK_TEXT_RE.search(inner):
            add(urljoin(base, raw))
    return out[:40]


def subprocessor_probe_urls_for(company: dict) -> list[str]:
    pairs, seen = [], set()

    def add(url: str) -> None:
        u = (url or "").rstrip("/")
        key = u.lower()
        if u.startswith("http") and key not in seen:
            seen.add(key)
            pairs.append(u)

    for domain in hosts_for(company)[:2]:
        for path in SUBPROCESSOR_WELL_KNOWN_PATHS:
            add(f"https://{domain}{path}")
    trust = company.get("trust_url") or ""
    th = host_of(trust)
    if th and not is_portal_vendor_host(trust, company):
        add(f"https://{th}/subprocessors")
        add(f"https://{th}/sub-processors")
    for url, hint in SPECIAL_URLS.get(company.get("slug") or "", []):
        if hint == "subprocessors":
            add(url)
    return pairs


def apply_subprocessors_to_row(row: dict, url: str) -> bool:
    """File a first-party list URL and add the +8 factor. Leave other factors."""
    links = dict(row.get("links") or {})
    if links.get("subprocessors"):
        return False
    links["subprocessors"] = url
    row["links"] = links
    disc = dict(row.get("disclosure") or {})
    factors = dict(disc.get("factors") or {})
    if not factors.get("subprocessors") and not factors.get("processors"):
        factors["subprocessors"] = 8
        score = min(100, int(disc.get("score") or 0) + 8)
        if not row.get("found"):
            tier = "silent"
        elif score >= 90:
            tier = "complete"
        elif score >= 70:
            tier = "substantial"
        elif score >= 40:
            tier = "on-file"
        else:
            tier = "thin"
        disc["score"] = score
        disc["tier"] = tier
        disc["factors"] = factors
        row["disclosure"] = disc
    return True


def apply_marks_to_row(row: dict, names: list[str]) -> list[str]:
    """File catalog marks the first-party page named. Leave other factors."""
    old = [x for x in (row.get("certs") or []) if isinstance(x, str)]
    incoming = [x for x in names if isinstance(x, str) and x.strip()]
    if not incoming:
        return []
    merged = apply_supersede(old + [x for x in incoming if x not in old])
    added = [x for x in merged if x not in old]
    if not added:
        return []
    row["certs"] = merged
    disc = dict(row.get("disclosure") or {})
    factors = dict(disc.get("factors") or {})
    old_w = int(factors.get("marks") or 0)
    new_w = cert_score(merged)
    if new_w != old_w:
        delta = new_w - old_w
        factors["marks"] = new_w
        score = min(100, max(0, int(disc.get("score") or 0) + delta))
        if not row.get("found"):
            tier = "silent"
        elif score >= 90:
            tier = "complete"
        elif score >= 70:
            tier = "substantial"
        elif score >= 40:
            tier = "on-file"
        else:
            tier = "thin"
        disc["score"] = score
        disc["tier"] = tier
        disc["factors"] = factors
        row["disclosure"] = disc
    if row.get("found"):
        cited = ", ".join(merged[:6])
        extra = f" +{len(merged) - 6}" if len(merged) > 6 else ""
        row["summary"] = f"Official page on file. Marks cited from public HTML: {cited}{extra}."
    return added


def fetch_seed_page(url: str) -> dict:
    fetched = crawl.fetch(url, max_body=TRUST_BODY)
    html = fetched.get("body") or ""
    title = crawl.extract_title(html) if html else ""
    rec = {
        "url": url,
        "ok": bool(fetched.get("ok")),
        "status": fetched.get("status") or 0,
        "final_url": fetched.get("final_url") or url,
        "title": title,
        "text": strip_tags(html)[:30000] if html else "",
        "meta": extract_meta_desc(html) if html else "",
        "hrefs": extract_hrefs(html, fetched.get("final_url") or url) if html else [],
        "ctype": (fetched.get("headers") or {}).get("content-type", ""),
        "fetched_at": utc_now(),
        "raw_head": html[:4000] if html else "",
        "html": html,
    }
    return rec

def file_published_dpas() -> int:
    """File first-party DPA URLs already published on pages that had none."""
    t0 = time.time()
    src = SITE / "data" / "enriched.json"
    if not src.exists():
        src = DATA / "enriched.json"
    payload = load_json(src, {})
    companies = list(payload.get("companies") or [])
    if not companies:
        print("no companies in enriched.json", flush=True)
        return 1
    before = sum(1 for c in companies if (c.get("links") or {}).get("dpa"))
    gaps = [c for c in companies if has_public_page(c) and not (c.get("links") or {}).get("dpa")]
    print(f"DPA on file: {before}. Pages with no DPA URL: {len(gaps)}", flush=True)

    filed: list[tuple[str, str]] = []
    checked = 0
    by_slug = {c["slug"]: c for c in companies}

    def seed_urls(c: dict) -> list[str]:
        links = c.get("links") or {}
        out, seen = [], set()
        for raw in (
            c.get("trust_url"),
            c.get("final_url"),
            links.get("trust"),
            links.get("security"),
            links.get("privacy"),
        ):
            u = (raw or "").strip()
            if u.startswith("http") and u.lower() not in seen:
                seen.add(u.lower())
                out.append(u)
        return out

    print(f"Phase 1: read {len(gaps)} found pages for a published DPA link…", flush=True)
    candidates: dict[str, list[str]] = {}
    seed_jobs = [(c["slug"], url) for c in gaps for url in seed_urls(c)]

    def do_seed(job):
        slug, url = job
        try:
            return slug, fetch_seed_page(url)
        except Exception:
            return slug, {"ok": False, "status": 0, "hrefs": [], "html": "", "final_url": url}

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = [pool.submit(do_seed, job) for job in seed_jobs]
        done = 0
        for fut in as_completed(futs):
            slug, rec = fut.result()
            done += 1
            if done % 40 == 0 or done == len(futs):
                print(f"  seed {done}/{len(futs)}", flush=True)
            row = by_slug.get(slug)
            if not row:
                continue
            html = rec.get("html") or ""
            base = rec.get("final_url") or rec.get("url") or ""
            found = extract_dpa_candidates(html, base)
            if rec.get("hrefs"):
                for href in rec["hrefs"]:
                    if DPA_PATH_RE.search(href) and href not in found:
                        found.append(href)
            if found:
                bucket = candidates.setdefault(slug, [])
                for u in found:
                    if u not in bucket:
                        bucket.append(u)

    need_probe = [c for c in gaps if c["slug"] not in candidates]
    print(f"  pages already linking a DPA-shaped URL: {len(candidates)}", flush=True)
    print(f"Phase 2: well-known first-party paths for {len(need_probe)} still blank…", flush=True)
    for c in need_probe:
        candidates[c["slug"]] = dpa_probe_urls_for(c)

    verify_jobs = []
    seen_verify = set()
    for slug, urls in candidates.items():
        row = by_slug.get(slug)
        if not row:
            continue
        for url in urls:
            key = (slug, url.lower())
            if key in seen_verify:
                continue
            if not is_first_party_url(url, row):
                continue
            seen_verify.add(key)
            verify_jobs.append((slug, url))
    print(f"Phase 3: verifying {len(verify_jobs)} candidate URLs…", flush=True)

    def do_verify(job):
        slug, url = job
        try:
            rec = fetch_uncached(url, PROBE_BODY if not url.lower().endswith(".pdf") else TRUST_BODY)
        except Exception:
            rec = {"ok": False, "status": 0, "final_url": url, "title": "", "text": ""}
        return slug, url, rec

    accepted: dict[str, str] = {}

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
                if done % 80 == 0 or done == len(futs):
                    print(f"  {label} {done}/{len(futs)}", flush=True)
                if slug in accepted:
                    continue
                row = by_slug.get(slug)
                if not row:
                    continue
                final = rec.get("final_url") or url
                if not is_first_party_url(final, row):
                    continue
                if classify_as_dpa(url, rec):
                    accepted[slug] = final

    take_hits(verify_jobs, "Phase 3")
    still = [c for c in gaps if c["slug"] not in accepted]
    fallback = []
    seen_fb = set(seen_verify)
    for c in still:
        for url in dpa_probe_urls_for(c):
            key = (c["slug"], url.lower())
            if key in seen_fb:
                continue
            if not is_first_party_url(url, c):
                continue
            seen_fb.add(key)
            fallback.append((c["slug"], url))
    take_hits(fallback, "Phase 4 fallback paths")

    checked = len(gaps)
    for slug, url in sorted(accepted.items()):
        row = by_slug[slug]
        if apply_dpa_to_row(row, url):
            filed.append((row.get("name") or slug, url))

    generated = utc_now()
    payload["generated_at"] = generated
    payload["companies"] = companies
    write_json(DATA / "enriched.json", payload)
    write_json(SITE / "data" / "enriched.json", payload)
    after = sum(1 for c in companies if (c.get("links") or {}).get("dpa"))
    print(f"Wrote {DATA / 'enriched.json'} and {SITE / 'data' / 'enriched.json'}", flush=True)
    print(f"checked={checked} filed={len(filed)} dpa {before} → {after} in {time.time() - t0:.1f}s", flush=True)
    for name, url in filed:
        print(f"  filed {name}: {url}", flush=True)
    return 0

def has_official_domain(company: dict) -> bool:
    return bool(hosts_for(company))


def is_third_party_year_host(url: str) -> bool:
    h = host_of(url)
    if not h:
        return True
    return any(h == d or h.endswith("." + d) for d in THIRD_PARTY_YEAR_HOSTS)


def is_news_article_url(url: str) -> bool:
    path = path_of(url)
    return bool(NEWS_ARTICLE_PATH.search(path))


def canon_source_url(url: str) -> str:
    p = urlparse(url)
    netloc = p.netloc.lower()
    if netloc.endswith(":443") and (p.scheme or "https") == "https":
        netloc = netloc[:-4]
    if netloc.endswith(":80") and p.scheme == "http":
        netloc = netloc[:-3]
    path = (p.path or "/").rstrip("/") or "/"
    return f"{p.scheme}://{netloc}{path}"


def is_official_year_source(url: str, company: dict) -> bool:
    """A year source must be the company's own site. Wikipedia and news are not."""
    if not url or not str(url).startswith("http"):
        return False
    if is_third_party_year_host(url):
        return False
    if is_news_article_url(url):
        return False
    if YEAR_PAGE_SKIP.search(path_of(url)):
        return False
    hosts = set(hosts_for(company))
    for raw in (company.get("trust_url"), company.get("final_url"), company.get("domain")):
        if not raw:
            continue
        h = host_of(raw) if str(raw).startswith("http") else str(raw).lower().removeprefix("www.")
        if h:
            hosts.add(h)
    if not hosts:
        return False
    h = host_of(url)
    regs = {registrable(x) for x in hosts if x}
    if h in hosts or registrable(h) in regs:
        return True
    return any(h.endswith("." + known) or known.endswith("." + h) for known in (hosts | regs) if known)


_OTHER_SUBJECT = re.compile(
    r"\b(program|programs|alliance|survey|foundation|committee|initiative|"
    r"award|partnership|subsidiary|division|campaign|academy|council|"
    r"works council|employee participation|university|campus|school|"
    r"college|scholarship)\b",
    re.I,
)
# "Temasek operates… Established in 1974, the company" is Temasek, not Orca.
_GENERIC_LEAD = {
    "the", "this", "our", "we", "in", "on", "since", "after", "from",
    "with", "through", "and", "for", "its", "their", "when", "where",
    "founded", "established", "incorporated", "year", "date", "new",
    "january", "february", "march", "april", "may", "june", "july",
    "august", "september", "october", "november", "december",
}


def _timeline_next_event(window: str, year: int) -> bool:
    """A later year after 'YYYY Name Established' is the next timeline beat."""
    for m in _TIMELINE_NEXT_EVENT.finditer(window or ""):
        first, second = int(m.group(1)), int(m.group(2))
        if year == second and first != second:
            return True
    return False


def _other_named_org_before_founding(window: str, company_core: str) -> bool:
    """Another named firm in the same window is not this company."""
    m = re.search(r"\b(?:founded|established|incorporated)\b", window or "", re.I)
    if not m:
        return False
    names = re.findall(
        r"\b([A-Z][A-Za-z]{2,})(?:\s+[A-Z][A-Za-z]{2,}){0,2}\b",
        window[: m.start()],
    )
    for name in names:
        parts = [p.lower() for p in name.split()]
        if all(p in _GENERIC_LEAD for p in parts):
            continue
        if company_core and company_core in _name_core(name):
            continue
        return True
    return False


def _window_about_this_company(window: str, company_name: str, structured: bool) -> bool:
    if structured:
        return True
    w = window or ""
    if _OTHER_SUBJECT.search(w):
        return False
    if re.search(r"\bco-founded\b", w, re.I):
        core = _name_core(company_name) if company_name else ""
        if not core or not re.search(
            rf"\bco-founded\s+{re.escape(company_name)}"
            rf"|{re.escape(company_name)}.{{0,40}}was\s+co-founded",
            w,
            re.I,
        ):
            return False
    if re.search(r"\b(?:we are|is|are)\s+part of\b.{0,80}\b(?:founded|established)\b", w, re.I):
        return False
    core = _name_core(company_name) if company_name else ""
    if core and core in _name_core(w):
        return True
    if re.search(r"\b(we|our company|our firm|our story|this company)\b", w, re.I):
        # Thriv Founded in 2018 … We connect — other firm, not this company.
        if core and _other_named_org_before_founding(w, core):
            return False
        return True
    if re.search(r"\bthe company\b", w, re.I) and not re.search(
        r"\b(?:selling|sold|left|joined|acquired|bought)\s+the company\b", w, re.I
    ):
        # Investor / other-firm copy: Temasek 1974 on Orca Security.
        if core and _other_named_org_before_founding(w, core):
            return False
        return True
    # A year without this company’s name (or we/our) is not enough — partner
    # hospitals and heritage footnotes stay off file.
    return False


def parse_official_founded_year(text: str, company_name: str = ""):
    """Return YYYY only from an explicit founded/established sentence or foundingDate."""
    if not text:
        return None
    cleaned = COPYRIGHT_SPAN.sub(" ", text)
    prose: list[int] = []
    structured: list[int] = []
    for pat, is_struct in (
        (OFFICIAL_FOUNDED, False),
        (OFFICIAL_FOUNDED_REVERSE, False),
        (YEAR_THEN_FOUNDED, False),
        (FOUNDING_DATE_FIELD, True),
    ):
        for m in pat.finditer(cleaned):
            year = int(m.group(1))
            if not (1600 <= year <= NOW_YEAR):
                continue
            window = cleaned[max(0, m.start() - 90): m.end() + 90]
            if not _window_about_this_company(window, company_name, is_struct):
                continue
            if is_struct and JSONLD_NOT_FOUNDING.search(window):
                continue
            if not is_struct and PROSE_REBRAND.search(window):
                continue
            if not is_struct and _timeline_next_event(window, year):
                continue
            (structured if is_struct else prose).append(year)
    # A later JSON-LD foundingDate is not the founding year when the same
    # page already names an earlier founded/established year.
    if prose and structured:
        earliest = min(prose)
        structured = [y for y in structured if y <= earliest]
    years = prose + structured
    if not years:
        return None
    uniq = sorted(set(years))
    if len(uniq) != 1:
        return None
    return uniq[0]


def about_urls_for(company: dict) -> list[str]:
    out, seen = [], set()

    def add(url: str) -> None:
        u = (url or "").split("#")[0].rstrip("/")
        if not u.startswith("http"):
            return
        key = u.lower()
        if key in seen:
            return
        seen.add(key)
        out.append(u)

    official = (company.get("official_url") or "").strip()
    add(official)
    for domain in hosts_for(company)[:1]:
        add(f"https://{domain}")
        # Apex often NXDOMAIN / times out while www serves the official site
        # (GRCS). Marks well-known paths already try www; years should too.
        if not domain.startswith("www."):
            add(f"https://www.{domain}")
        for path in ABOUT_PATHS:
            add(f"https://{domain}{path}")
    return out


def year_follow_urls(rec: dict, company: dict) -> list[str]:
    out = []
    for href in rec.get("hrefs") or []:
        if not ABOUT_HREF.search(path_of(href)):
            continue
        if is_news_article_url(href):
            continue
        if is_official_year_source(href, company):
            out.append(href)
    return out[:8]


def resolve_official_year(company: dict) -> tuple[int, str] | None:
    """File a year only when the company's own official website publishes one."""
    jobs = about_urls_for(company)
    seen = {u.lower() for u in jobs}
    found: list[tuple[int, str]] = []
    i = 0
    while i < len(jobs) and i < 24:
        url = jobs[i]
        i += 1
        rec = fetch_cached(url, max_body=TRUST_BODY)
        if not rec.get("ok") or rec.get("status") != 200:
            continue
        title, text = rec.get("title") or "", rec.get("text") or ""
        if looks_dead(title, text):
            continue
        final = rec.get("final_url") or url
        if not is_official_year_source(final, company):
            continue
        blob = " ".join(filter(None, [title, rec.get("meta") or "", text]))
        year = parse_official_founded_year(blob, company.get("name") or "")
        if year:
            found.append((year, final))
        if len(jobs) >= 24:
            continue
        for extra in year_follow_urls(rec, company):
            if extra.lower() in seen:
                continue
            seen.add(extra.lower())
            jobs.append(extra)
            if len(jobs) >= 24:
                break
    if not found:
        return None
    years = {y for y, _s in found}
    if len(years) != 1:
        return None
    year, source = found[0]
    return year, canon_source_url(source)


def apply_year_to_row(row: dict, year: int, source: str) -> bool:
    """File a founded year and add the longevity factor. Leave other facts as they were."""
    if row.get("founded_year"):
        return False
    if not is_official_year_source(source, row):
        return False
    row["founded_year"] = year
    row["founded_source"] = source
    disc = dict(row.get("disclosure") or {})
    factors = dict(disc.get("factors") or {})
    pts = min(10, (NOW_YEAR - int(year)) // 2)
    if pts and not factors.get("longevity"):
        factors["longevity"] = pts
        score = min(100, int(disc.get("score") or 0) + pts)
        if not (row.get("found") or (row.get("links") or {}).get("trust") or (row.get("links") or {}).get("security")):
            tier = "silent"
        elif score >= 90:
            tier = "complete"
        elif score >= 70:
            tier = "substantial"
        elif score >= 40:
            tier = "on-file"
        else:
            tier = "thin"
        disc["score"] = score
        disc["tier"] = tier
        disc["factors"] = factors
        row["disclosure"] = disc
    return True


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


def bounty_urls_from_security_txt(text: str) -> list[str]:
    """Program URLs named in security.txt. Hiring and encryption stay out."""
    out, seen = [], set()
    for m in SEC_TXT_LINE.finditer(text or ""):
        field, val = m.group(1).strip().lower(), m.group(2).strip()
        if field in SEC_TXT_SKIP_FIELDS or not val.startswith("http"):
            continue
        if val in seen:
            continue
        seen.add(val)
        out.append(val)
    return out


def bounty_from_security_txt(text: str):
    """Policy/Contact/Bug Bounty HTTP URLs. Strip HTML tails. Hiring stays out."""
    if not text:
        return None
    bounty_re = re.compile(
        r"hackerone|bugcrowd|yeswehack|intigriti|bug-?bounty|bugbounty|\bbounty\b|"
        r"responsible-?disclosure|vulnerabilit|bughunters|(?:^|/)(?:vdp|vrp|bounty)"
        r"|vdp\.|bounty\.|/\bvdp\b|\bvdp/|psirt|security-disclosure|disclosure-policy",
        re.I,
    )
    for pat in (SEC_POLICY, SEC_CONTACT):
        for m in pat.finditer(text):
            val = field_url(m.group(1))
            if val.startswith("http") and bounty_re.search(val):
                return val
    for m in SEC_TXT_LINE.finditer(text):
        field, raw = m.group(1).strip().lower(), m.group(2)
        if field in SEC_TXT_SKIP_FIELDS:
            continue
        val = field_url(raw)
        if not val.startswith("http"):
            continue
        if field in {"bug bounty", "bug-bounty", "bugbounty"} or bounty_re.search(val):
            return val
    return None


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
            # Title-only prefix hits (Manhattan / Sage Publishing) are not a source.
            # Wikipedia is not enough unless the official website matches.
            if not web_ok:
                continue
            if not name_ok and p31 and "Q5" in p31 and not (set(p31) & ORG_QIDS):
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
            if not web_ok:
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

    # Wikipedia lead text is not a source. Official-site years are filed later.
    return by_slug


LOGIN_WALL = re.compile(
    r"(please (?:log|sign) in|sign in to continue|login required|"
    r"you (?:must|need to) (?:log|sign) in|authentication required)",
    re.I,
)

def file_published_years() -> int:
    """File founded years already published on official sites, for rows that have none."""
    t0 = time.time()
    src = SITE / "data" / "enriched.json"
    if not src.exists():
        src = DATA / "enriched.json"
    payload = load_json(src, {})
    companies = list(payload.get("companies") or [])
    if not companies:
        print("no companies in enriched.json", flush=True)
        return 1
    before = sum(1 for c in companies if c.get("founded_year"))
    gaps = [
        c for c in companies
        if not c.get("founded_year")
        and (has_public_page(c) or has_official_domain(c))
    ]
    print(f"Years on file: {before}. Pages/domains with no year: {len(gaps)}", flush=True)

    filed: list[tuple[str, int, str]] = []
    checked = 0

    def do_one(c):
        try:
            return c["slug"], resolve_official_year(c)
        except Exception:
            return c["slug"], None

    by_slug = {c["slug"]: c for c in companies}
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = [pool.submit(do_one, c) for c in gaps]
        done = 0
        for fut in as_completed(futs):
            slug, hit = fut.result()
            done += 1
            checked += 1
            if done % 25 == 0 or done == len(futs):
                print(f"  checked {done}/{len(futs)}", flush=True)
            if not hit:
                continue
            year, source = hit
            row = by_slug.get(slug)
            if not row:
                continue
            if apply_year_to_row(row, year, source):
                filed.append((row.get("name") or slug, year, source))

    generated = utc_now()
    payload["generated_at"] = generated
    payload["companies"] = companies
    write_json(DATA / "enriched.json", payload)
    write_json(SITE / "data" / "enriched.json", payload)
    after = sum(1 for c in companies if c.get("founded_year"))
    print(f"Wrote {DATA / 'enriched.json'} and {SITE / 'data' / 'enriched.json'}", flush=True)
    print(
        f"checked={checked} filed={len(filed)} years {before} → {after} "
        f"in {time.time() - t0:.1f}s",
        flush=True,
    )
    for name, year, source in sorted(filed, key=lambda x: x[0].lower()):
        print(f"  filed {name}: {year} · {source}", flush=True)
    return 0

def official_page_urls(company: dict) -> list[str]:
    urls, seen = [], set()
    candidates = [
        company.get("trust_url"),
        (company.get("links") or {}).get("trust"),
        (company.get("links") or {}).get("security"),
    ]
    if company.get("found"):
        candidates.append(company.get("final_url"))
    for raw in candidates:
        if not raw or not str(raw).startswith("http"):
            continue
        key = str(raw).rstrip("/").lower()
        if key not in seen:
            seen.add(key)
            urls.append(str(raw).rstrip("/"))
    return urls


def marks_from_official_pages(company: dict) -> tuple[list[str], int]:
    """Live first-party HTML only. Login walls and dead pages are not read."""
    found: list[str] = []
    checked = 0
    for url in official_page_urls(company):
        rec = fetch_cached(url, max_body=TRUST_BODY)
        title, text = rec.get("title") or "", rec.get("text") or ""
        if not rec.get("ok") or rec.get("status") != 200:
            continue
        if looks_dead(title, text) or looks_like_login_wall(title, text):
            continue
        checked += 1
        html = rec.get("html") or ""
        if not html:
            fetched = crawl.fetch(url, max_body=TRUST_BODY)
            html = fetched.get("body") or ""
        blob = rec.get("mark_blob") or mark_blob(html, title, rec.get("meta") or "", text)
        found.extend(extract_certs_from_html(html, text=blob))
    return apply_supersede(found), checked


def file_marks() -> int:
    """Add marks named on the official page. Pages that name none stay unchanged."""
    t0 = time.time()
    CACHE.mkdir(parents=True, exist_ok=True)
    payload = load_json(DATA / "enriched.json", {})
    companies = payload.get("companies") or []
    if not companies:
        print("no companies in data/enriched.json", flush=True)
        return 1

    before_with = sum(1 for c in companies if c.get("certs"))
    before_total = sum(len(c.get("certs") or []) for c in companies)
    pages_checked = 0
    new_filings = 0
    samples: list[tuple[str, list[str]]] = []
    targets = [c for c in companies if official_page_urls(c)]
    print(f"Filing marks from {len(targets)} official pages ({len(companies)} on the register)", flush=True)

    results: dict[str, tuple[list[str], int]] = {}
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = {pool.submit(marks_from_official_pages, c): c["slug"] for c in targets}
        done = 0
        for fut in as_completed(futs):
            slug = futs[fut]
            try:
                results[slug] = fut.result()
            except Exception as exc:
                print(f"  skip {slug}: {exc}", flush=True)
                results[slug] = ([], 0)
            done += 1
            if done % 25 == 0 or done == len(futs):
                print(f"  read {done}/{len(futs)}", flush=True)

    generated_at = utc_now()
    for c in companies:
        live, checked = results.get(c["slug"], ([], 0))
        pages_checked += checked
        if not live:
            continue
        old = [x for x in (c.get("certs") or []) if isinstance(x, str)]
        merged = apply_supersede(old + [x for x in live if x not in old])
        added = [x for x in merged if x not in old]
        if not added:
            continue
        c["certs"] = merged
        new_filings += len(added)
        if c.get("found"):
            shown = ", ".join(merged[:8])
            more = " and others" if len(merged) > 8 else ""
            c["summary"] = f"Public trust center. On file: {shown}{more}."
        rescore(c)
        samples.append((c["name"], added))

    payload["generated_at"] = generated_at
    payload["notes"] = (
        payload.get("notes")
        or "Public pages only. Incomplete by nature. No invented URLs, years, certs, or processors."
    )
    write_json(DATA / "enriched.json", payload)
    write_json(SITE / "data" / "enriched.json", payload)

    after_with = sum(1 for c in companies if c.get("certs"))
    after_total = sum(len(c.get("certs") or []) for c in companies)
    elapsed = round(time.time() - t0, 1)
    print(f"Wrote {DATA / 'enriched.json'} and {SITE / 'data' / 'enriched.json'}", flush=True)
    print(
        f"pages_checked={pages_checked} new_filings={new_filings} "
        f"companies_with_marks {before_with}->{after_with} "
        f"mentions {before_total}->{after_total} in {elapsed}s",
        flush=True,
    )
    for name, added in samples[:12]:
        print(f"  {name}: +{', '.join(added)}", flush=True)

    log_path = DATA / "enrichment-log.md"
    if log_path.exists():
        extra = [
            "",
            "## Marks pass",
            "",
            f"Generated: {generated_at}",
            "",
            f"- pages checked: {pages_checked}",
            f"- new mark filings: {new_filings}",
            f"- companies with ≥1 mark: {before_with} → {after_with}",
            f"- mark mentions: {before_total} → {after_total}",
            "",
            "First-party trust/security HTML only. Login walls and pages that name no mark stayed unchanged.",
            "",
        ]
        log_path.write_text(log_path.read_text() + "\n".join(extra))
    return 0


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
            cert_blob_parts.append(tpage.get("mark_blob") or "")
            cert_blob_parts.append(tpage.get("title") or "")
            cert_blob_parts.append(tpage.get("meta") or "")
            cert_blob_parts.append((tpage.get("text") or "")[:20000])
        for kind in ("security", "trust"):
            if kind in hits:
                rec = hits[kind][1]
                cert_blob_parts.append(rec.get("mark_blob") or "")
                cert_blob_parts.append(rec.get("title") or "")
                cert_blob_parts.append((rec.get("text") or "")[:12000])
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

def company_tokens(company: dict) -> set[str]:
    out: set[str] = set()

    def add(raw: str) -> None:
        v = re.sub(r"[^a-z0-9]+", " ", (raw or "").lower()).strip()
        if not v:
            return
        compact = v.replace(" ", "")
        if len(compact) >= 3:
            out.add(compact)
        for part in v.split():
            if part in STOP_TOKENS:
                continue
            if len(part) >= 3:
                out.add(part)
            if len(part) >= 4:
                out.add(part.replace("-", ""))

    add(company.get("slug") or "")
    add(company.get("name") or "")
    add(company.get("domain") or "")
    for h in hosts_for(company):
        add(h)
        add(h.split(".")[0])
    return {t for t in out if t and t not in STOP_TOKENS}

def is_social_or_news(url: str) -> bool:
    h = host_of(url)
    if not h:
        return False
    if h in SOCIAL_NEWS_HOSTS:
        return True
    return any(h.endswith("." + n) for n in SOCIAL_NEWS_HOSTS)

def is_statuspage_marketing_url(url: str) -> bool:
    h = host_of(url)
    path = path_of(url).lower()
    if h in STATUS_MARKETING_HOSTS or h in STATUS_GENERIC_PLATFORM_HOSTS:
        return True
    if h in {"atlassian.com", "www.atlassian.com"} and "statuspage" in path:
        return True
    if h.endswith(".statuspage.io") and h.split(".")[0] in {"www", "meta", "manage", "api", "corporate", "business"}:
        return True
    return False

def is_status_path(path: str) -> bool:
    return bool(STATUS_PATH_RE.search(path or ""))

def is_platform_status_host(host: str) -> bool:
    h = (host or "").lower().removeprefix("www.")
    if not h or h in STATUS_MARKETING_HOSTS:
        return False
    return any(h.endswith(suf) for suf in STATUS_PLATFORM_SUFFIXES)

def status_host_matches_company(url: str, company: dict | None) -> bool:
    if not company:
        return False
    if is_first_party_url(url, company):
        return True
    h = host_of(url)
    tokens = company_tokens(company)
    compact = re.sub(r"[^a-z0-9]", "", h)
    if h.startswith("status."):
        rest = h[7:]
        return is_first_party_url("https://" + rest, company) or any(
            t in re.sub(r"[^a-z0-9]", "", rest) for t in tokens if len(t) >= 4
        )
    for suf in STATUS_PLATFORM_SUFFIXES:
        if h.endswith(suf):
            sub = h[: -len(suf)].split(".")[-1]
            sub_c = re.sub(r"[^a-z0-9]", "", sub)
            return any(t == sub_c or t in sub_c or sub_c in t for t in tokens if len(t) >= 3)
    if "status" in compact:
        return any(len(t) >= 4 and t in compact for t in tokens)
    return False

def is_status_branded_host(url: str, company: dict | None) -> bool:
    h = host_of(url)
    if not h or is_statuspage_marketing_url(url):
        return False
    if h.startswith("status."):
        return True
    if is_platform_status_host(h):
        return True
    compact = re.sub(r"[^a-z0-9]", "", h)
    if "status" in compact and company and status_host_matches_company(url, company):
        return True
    if company is None and re.search(r"status", h, re.I) and not is_social_or_news(url):
        return bool(re.search(r"(^status\.)|(status$)|(-status\.)", h, re.I))
    return False

def title_looks_status(title: str) -> bool:
    t = (title or "").strip()
    if not t or re.search(r"\b(?:trust center|security center|privacy|login|sign in)\b", t, re.I):
        return False
    return bool(STATUS_TITLE_RE.search(t))

def status_body_signals(title: str, text: str, path: str, host: str) -> bool:
    blob = f"{title} {text[:8000]}"
    return bool(STATUS_BODY_RE.search(blob))

def classify_as_status(url: str, rec: dict, company: dict | None = None) -> bool:
    """True only for a public first-party or first-party-branded status page."""
    if not rec.get("ok") or rec.get("status") != 200:
        return False
    title, text = rec.get("title") or "", rec.get("text") or ""
    final = rec.get("final_url") or url
    if looks_dead(title, text) or looks_like_login_wall(title, text):
        return False
    if is_social_or_news(final) or is_social_or_news(url):
        return False
    if is_statuspage_marketing_url(final) or is_statuspage_marketing_url(url):
        return False
    if ITEM_UID_RE.search(final) or ITEM_UID_RE.search(url):
        return False
    if STATUS_DEAD_PATH_RE.search(path_of(final)) or STATUS_DEAD_PATH_RE.search(path_of(url)):
        return False
    if STATUS_DEAD_BODY_RE.search(f"{title} {text[:4000]}"):
        return False
    if company and is_portal_vendor_host(final, company):
        return False
    host, path = host_of(final), path_of(final)
    if STATUS_MARKETING_RE.search(f"{title} {text[:2500]}") and not (
        is_status_branded_host(final, company) and status_body_signals(title, text, path, host)
    ):
        return False
    if landed_on_home(url, final) and not is_status_branded_host(final, company):
        return False
    req_host = host_of(url)
    if req_host.startswith("status.") and host != req_host:
        if not (is_status_branded_host(final, company) or is_status_path(path)):
            return False
    branded = is_status_branded_host(final, company)
    first_party = is_first_party_url(final, company) if company else (
        branded or host.startswith("status.") or is_status_path(path)
    )
    if company:
        matches = status_host_matches_company(final, company)
        titled_for_company = title_looks_status(title) and any(
            t in re.sub(r"[^a-z0-9]", "", f"{title} {host}")
            for t in company_tokens(company)
            if len(t) >= 4
        )
        if branded and not (matches or first_party or titled_for_company):
            return False
        if not (branded or first_party):
            return False
        if not (matches or first_party or titled_for_company):
            return False
    elif not (branded or first_party or is_status_path(path)):
        return False
    signals = status_body_signals(title, text, path, host)
    titled = title_looks_status(title)
    if branded and (signals or titled):
        return True
    if first_party and is_status_path(path) and (signals or titled):
        return True
    if first_party and titled and signals:
        return True
    return False

def is_followable_status_href(href: str, company: dict | None) -> bool:
    if not href or ITEM_UID_RE.search(href) or STATUS_DEAD_PATH_RE.search(path_of(href)):
        return False
    if is_social_or_news(href) or is_statuspage_marketing_url(href):
        return False
    h = host_of(href)
    if h.startswith("status."):
        return True
    if is_platform_status_host(h):
        return True
    if re.search(r"status", h, re.I) and (not company or status_host_matches_company(href, company)):
        return True
    if is_status_path(path_of(href)):
        return bool(not company or is_first_party_url(href, company))
    return False

def is_filed_status_valid(url: str, company: dict | None) -> bool:
    """Keep an already-filed URL only when it is still a status page, not a portal item."""
    if not url:
        return False
    if ITEM_UID_RE.search(url) or is_social_or_news(url) or is_statuspage_marketing_url(url):
        return False
    if STATUS_DEAD_PATH_RE.search(path_of(url)):
        return False
    if company and is_portal_vendor_host(url, company):
        return False
    h, path = host_of(url), path_of(url)
    if h.startswith("status."):
        return True
    if is_platform_status_host(h):
        return bool(not company or status_host_matches_company(url, company))
    if re.search(r"status", h, re.I) and (
        not company or status_host_matches_company(url, company) or is_first_party_url(url, company)
    ):
        return True
    if company and is_first_party_url(url, company) and re.search(r"status", path, re.I):
        return True
    return is_status_path(path)

def extract_status_candidates(html: str, base: str, company: dict | None = None) -> list[str]:
    """Hrefs and link text that point at a status page, not a tweet or portal item."""
    out, seen = [], set()

    def add(u: str) -> None:
        u = (u or "").split("#")[0].strip()
        if not u.startswith("http") or u.lower() in seen:
            return
        if ITEM_UID_RE.search(u) or is_social_or_news(u) or is_statuspage_marketing_url(u):
            return
        seen.add(u.lower())
        out.append(u)

    for href in extract_hrefs(html, base):
        if is_followable_status_href(href, company) or STATUS_PATH_RE.search(href):
            add(href)
    for m in A_TAG_RE.finditer(html or ""):
        raw, inner = m.group(1).strip(), strip_tags(m.group(2))
        if raw.startswith(("javascript:", "mailto:", "tel:", "data:")):
            continue
        if STATUS_LINK_TEXT_RE.search(inner):
            add(urljoin(base, raw))
    for m in STATUS_URL_IN_HTML_RE.finditer(html or ""):
        add(m.group(0).rstrip(").,;"))
    return out[:40]

def status_probe_urls_for(company: dict) -> list[str]:
    pairs, seen = [], set()

    def add(url: str) -> None:
        u = (url or "").rstrip("/")
        key = u.lower()
        if u.startswith("http") and key not in seen:
            seen.add(key)
            pairs.append(u)

    for domain in hosts_for(company)[:2]:
        add(f"https://status.{domain}")
        add(f"https://{domain}/status")
        add(f"https://{domain}/system-status")
        add(f"https://{domain}/service-status")
        add(f"https://{domain}/status-page")
    for url, hint in SPECIAL_URLS.get(company.get("slug") or "", []):
        if hint == "status":
            add(url)
    return pairs

def _retier(row: dict, disc: dict, score: int) -> None:
    if not row.get("found") and not (row.get("links") or {}).get("trust") and not (row.get("links") or {}).get("security"):
        tier = "silent"
    elif score >= 90:
        tier = "complete"
    elif score >= 70:
        tier = "substantial"
    elif score >= 40:
        tier = "on-file"
    else:
        tier = "thin"
    disc["score"] = min(100, max(0, score))
    disc["tier"] = tier

def status_url_rank(url: str, company: dict | None) -> tuple:
    """Lower is better. Prefer status.{domain} over a hosted page."""
    h, path = host_of(url), path_of(url)
    if STATUS_DEAD_PATH_RE.search(path) or is_statuspage_marketing_url(url):
        return (9, h)
    if h.startswith("status.") and (not company or is_first_party_url(url, company)):
        return (0, h)
    if company and is_first_party_url(url, company) and is_status_path(path):
        return (1, h)
    if "statuspage.io" not in h and re.search(r"status", h, re.I):
        return (2, h)
    if is_platform_status_host(h):
        return (3, h)
    return (4, h)

def apply_status_to_row(row: dict, url: str) -> bool:
    """File a status URL and add the +6 factor. Leave other factors as they were."""
    links = dict(row.get("links") or {})
    prev = links.get("status")
    if prev == url:
        return False
    links["status"] = url
    row["links"] = links
    disc = dict(row.get("disclosure") or {})
    factors = dict(disc.get("factors") or {})
    if not factors.get("status"):
        factors["status"] = 6
        _retier(row, disc, int(disc.get("score") or 0) + 6)
        disc["factors"] = factors
        row["disclosure"] = disc
    else:
        row["disclosure"] = disc
    return prev != url

def clear_status_from_row(row: dict) -> bool:
    """Unfile a URL that is not a status page. Do not invent a replacement."""
    links = dict(row.get("links") or {})
    if not links.get("status"):
        return False
    links.pop("status", None)
    row["links"] = links
    disc = dict(row.get("disclosure") or {})
    factors = dict(disc.get("factors") or {})
    if factors.get("status"):
        factors.pop("status", None)
        _retier(row, disc, int(disc.get("score") or 0) - 6)
        disc["factors"] = factors
        row["disclosure"] = disc
    return True

def file_published_status() -> int:
    """File first-party status URLs already published on pages that had none."""
    t0 = time.time()
    src = SITE / "data" / "enriched.json"
    if not src.exists():
        src = DATA / "enriched.json"
    payload = load_json(src, {})
    companies = list(payload.get("companies") or [])
    if not companies:
        print("no companies in enriched.json", flush=True)
        return 1
    before = sum(1 for c in companies if (c.get("links") or {}).get("status"))
    invalid = [
        c for c in companies
        if (c.get("links") or {}).get("status")
        and not is_filed_status_valid((c.get("links") or {}).get("status") or "", c)
    ]
    gaps = [
        c for c in companies
        if not (c.get("links") or {}).get("status")
        or c in invalid
    ]
    print(
        f"Status on file: {before}. Invalid filings: {len(invalid)}. "
        f"Pages with no valid status URL: {len(gaps)}",
        flush=True,
    )

    filed: list[tuple[str, str]] = []
    cleared: list[str] = []
    by_slug = {c["slug"]: c for c in companies}

    def seed_urls(c: dict) -> list[str]:
        links = c.get("links") or {}
        out, seen = [], set()
        for raw in (
            c.get("trust_url"),
            c.get("final_url"),
            links.get("trust"),
            links.get("security"),
        ):
            u = (raw or "").strip()
            if u.startswith("http") and u.lower() not in seen:
                seen.add(u.lower())
                out.append(u)
        return out

    print(f"Phase 1: read {len(gaps)} found pages for a published status link…", flush=True)
    candidates: dict[str, list[str]] = {}
    seed_jobs = [(c["slug"], url) for c in gaps for url in seed_urls(c)]
    pages_checked = 0

    def do_seed(job):
        slug, url = job
        try:
            return slug, fetch_seed_page(url)
        except Exception:
            return slug, {"ok": False, "status": 0, "hrefs": [], "html": "", "final_url": url}

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = [pool.submit(do_seed, job) for job in seed_jobs]
        done = 0
        for fut in as_completed(futs):
            slug, rec = fut.result()
            done += 1
            if rec.get("ok"):
                pages_checked += 1
            if done % 40 == 0 or done == len(futs):
                print(f"  seed {done}/{len(futs)}", flush=True)
            row = by_slug.get(slug)
            if not row:
                continue
            html = rec.get("html") or ""
            base = rec.get("final_url") or rec.get("url") or ""
            found = extract_status_candidates(html, base, row)
            if rec.get("hrefs"):
                for href in rec["hrefs"]:
                    if is_followable_status_href(href, row) and href not in found:
                        found.append(href)
            if found:
                bucket = candidates.setdefault(slug, [])
                for u in found:
                    if u not in bucket:
                        bucket.append(u)

    linked = len(candidates)
    print(f"  pages already linking a status-shaped URL: {linked}", flush=True)
    print(f"Phase 2: well-known first-party paths for remaining blanks…", flush=True)
    for c in gaps:
        extras = status_probe_urls_for(c)
        bucket = candidates.setdefault(c["slug"], [])
        for u in extras:
            if u not in bucket:
                bucket.append(u)

    verify_jobs = []
    seen_verify = set()
    for slug, urls in candidates.items():
        row = by_slug.get(slug)
        if not row:
            continue
        for url in urls:
            key = (slug, url.lower())
            if key in seen_verify:
                continue
            if is_social_or_news(url) or is_statuspage_marketing_url(url) or ITEM_UID_RE.search(url):
                continue
            if not (
                is_first_party_url(url, row)
                or is_followable_status_href(url, row)
                or is_status_branded_host(url, row)
            ):
                continue
            seen_verify.add(key)
            verify_jobs.append((slug, url))
    print(f"Phase 3: verifying {len(verify_jobs)} candidate URLs…", flush=True)

    def do_verify(job):
        slug, url = job
        try:
            rec = fetch_uncached(url, PROBE_BODY)
        except Exception:
            rec = {"ok": False, "status": 0, "final_url": url, "title": "", "text": ""}
        return slug, url, rec

    accepted: dict[str, list[str]] = {}

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = [pool.submit(do_verify, job) for job in verify_jobs]
        done = 0
        for fut in as_completed(futs):
            slug, url, rec = fut.result()
            done += 1
            if done % 80 == 0 or done == len(futs):
                print(f"  verify {done}/{len(futs)}", flush=True)
            row = by_slug.get(slug)
            if not row:
                continue
            final = rec.get("final_url") or url
            if classify_as_status(url, rec, row):
                accepted.setdefault(slug, []).append(final)

    chosen: dict[str, str] = {}
    for slug, urls in accepted.items():
        row = by_slug.get(slug)
        best = sorted(urls, key=lambda u: status_url_rank(u, row))[0]
        chosen[slug] = best
    accepted = chosen

    checked = len(gaps)
    for c in invalid:
        slug = c["slug"]
        if slug not in accepted:
            if clear_status_from_row(c):
                cleared.append(c.get("name") or slug)

    for slug, url in sorted(accepted.items()):
        row = by_slug[slug]
        if apply_status_to_row(row, url):
            filed.append((row.get("name") or slug, url))

    generated = utc_now()
    payload["generated_at"] = generated
    payload["companies"] = companies
    write_json(DATA / "enriched.json", payload)
    write_json(SITE / "data" / "enriched.json", payload)
    after = sum(1 for c in companies if (c.get("links") or {}).get("status"))
    print(f"Wrote {DATA / 'enriched.json'} and {SITE / 'data' / 'enriched.json'}", flush=True)
    print(
        f"pages_checked={pages_checked} candidates={len(verify_jobs)} "
        f"filed={len(filed)} cleared={len(cleared)} status {before} → {after} "
        f"in {time.time() - t0:.1f}s",
        flush=True,
    )
    for name, url in filed[:40]:
        print(f"  filed {name}: {url}", flush=True)
    if len(filed) > 40:
        print(f"  … {len(filed) - 40} more", flush=True)
    for name in cleared:
        print(f"  cleared invalid status on {name}", flush=True)
    # Stash a machine-readable summary for the PR report.
    summary = {
        "before": before,
        "after": after,
        "pages_checked": pages_checked,
        "candidates_verified": len(verify_jobs),
        "filed": [{"name": n, "url": u} for n, u in filed],
        "cleared": cleared,
        "linked_from_found_pages": linked,
        "elapsed_s": round(time.time() - t0, 1),
    }
    write_json(DATA / "status-file-summary.json", summary)
    print(f"Wrote {DATA / 'status-file-summary.json'}", flush=True)
    return 0

BOUNTY_WELL_KNOWN_PATHS = (
    "/bug-bounty",
    "/bugbounty",
    "/security/bug-bounty",
    "/responsible-disclosure",
    "/security/responsible-disclosure",
    "/responsible-disclosure-policy",
    "/security/responsible-disclosure-policy",
    "/vulnerability-disclosure",
    "/security/vulnerability-disclosure",
    "/security/vulnerability",
    "/vulnerability-disclosure-policy",
    "/vulnerability-reporting",
    "/report-a-vulnerability",
    "/security/report-a-vulnerability",
    "/legal/vulnerability-disclosure-policy",
    "/security/vulnerability-disclosure-policy",
    "/legal/responsible-disclosure",
    "/policies/vulnerability-disclosure",
        "/security/vdp",
    "/vdp",
    "/bounty",
    "/security/bounty",
    "/security/vulnerability-reporting",
)

BOUNTY_PATH_RE = re.compile(
    r"(?:bug-?bounty|bugbounty|responsible-?disclosure|"
    r"vulnerability-?disclosure|vulnerability-?report|"
    r"vulnerability-reward|report-a-vulnerability|report[-_]vulnerabilit|"
    r"vulnerability-reporting|coordinated-disclosure|"
    r"security-disclosure|white[-_]?hat|"
    r"/security/vulnerability(?:/|$|\?)|"
    r"(?:^|/)(?:vdp|vrp|bounty)(?:/|$|\?))",
    re.I,
)

BOUNTY_TITLE_RE = re.compile(
    r"\b(?:bug\s*bounty|responsible\s*disclosure|vulnerability\s*disclosure|"
    r"vulnerability\s*reporting|vulnerability\s*reward|"
    r"report\s+a\s+vulnerabilit|bounty\s+programs?|"
    r"coordinated\s*disclosure|security\s*disclosure(?:\s+policy)?|"
    r"vulnerability\s*disclosure\s*policy|\b(?:vdp|vrp)\b)\b",
    re.I,
)

BOUNTY_DASHBOARD_RE = re.compile(
    r"(disclosure dashboard|\bcve\s*id\b|vulnerabilities disclosed by|"
    r"track all vulnerabilities disclosed)",
    re.I,
)

BOUNTY_PROFILE_TITLE_RE = re.compile(r"^[\w.-]+\s*\([\w.-]+\)\s*$")

BOUNTY_HOST_PREFIXES = ("bughunters.", "bugbounty.", "bounty.", "vdp.", "msrc.")

SEC_TXT_SKIP_FIELDS = {
    "hiring", "encryption", "canonical", "expires", "preferred-languages",
    "privacy", "privacy policy", "acknowledgments",
}

SEC_TXT_LINE = re.compile(r"(?im)^\s*([A-Za-z][A-Za-z0-9 _-]*):\s*(\S+)")

BOUNTY_BODY_RE = re.compile(
    r"\b(?:report\s+(?:a\s+)?(?:security\s+)?vulnerabilit|"
    r"bug\s*bounty|responsible\s*disclosure|coordinated\s*disclosure|"
    r"submit\s+a\s+report|security\s+researchers?|"
    r"vulnerability\s*disclosure|out\s+of\s+scope)\b",
    re.I,
)

BOUNTY_LINK_TEXT_RE = re.compile(
    r"\b(?:bug\s*bounty|responsible\s*disclosure|vulnerability\s*disclosure|"
    r"report\s+a\s+vulnerabilit|vulnerability\s*reporting|"
    r"security\s+researchers?|coordinated\s*disclosure|\bvdp\b)\b",
    re.I,
)

BOUNTY_NEWS_PATH_RE = re.compile(r"/(?:blog|news|press|stories)/", re.I)

BOUNTY_ITEM_UID_RE = re.compile(r"(?:[?&]|/)itemUid=", re.I)

BOUNTY_PLATFORM_HOSTS = {
    "hackerone.com",
    "bugcrowd.com",
    "tracker.bugcrowd.com",
    "yeswehack.com",
    "intigriti.com",
    "app.intigriti.com",
}

H1_RESERVED = {
    "hackers", "directory", "opportunities", "hacktivity", "blog", "about",
    "signin", "login", "users", "reports", "jobs", "enterprise", "product",
    "solutions", "resources", "partners", "press", "security", "privacy",
    "terms", "contact", "support", "docs", "api", "changelog", "leaderboard",
    "programs", "companies", "researchers", "overview", "pricing",
    "customers", "platform",
}

BUGCROWD_RESERVED = {
    "crowd", "programs", "blog", "about", "login", "signup", "resources",
    "customers", "enterprise", "researchers", "jobs", "pricing", "partners",
    "platform", "why-bugcrowd", "contact",
}

BOUNTY_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
)

BOUNTY_PRIVATE_RE = re.compile(
    r"(this program is private|sign in to view this program|"
    r"you must be invited|program is not public)",
    re.I,
)

BOUNTY_MARKETING_RE = re.compile(
    r"(hacker-powered security|bug bounty platform|the (?:#1 |leading )?"
    r"(?:bug bounty|crowdsourced security) platform|"
    r"find your next (?:program|bounty))",
    re.I,
)

def bounty_urls_from_security_txt(text: str) -> list[str]:
    """Program URLs named in security.txt. Hiring and encryption stay out."""
    out, seen = [], set()
    for m in SEC_TXT_LINE.finditer(text or ""):
        field, val = m.group(1).strip().lower(), m.group(2).strip()
        if field in SEC_TXT_SKIP_FIELDS or not val.startswith("http"):
            continue
        if val in seen:
            continue
        seen.add(val)
        out.append(val)
    return out

def is_bounty_platform_host(host: str) -> bool:
    h = (host or "").lower().removeprefix("www.")
    return h in BOUNTY_PLATFORM_HOSTS

def bounty_platform_handle(url: str) -> str | None:
    """Program handle on a first-party-branded platform page, or None."""
    host = host_of(url)
    path = path_of(url).rstrip("/")
    parts = [p for p in path.split("/") if p]
    if host == "hackerone.com":
        if not parts or parts[0].lower() in H1_RESERVED:
            return None
        if BOUNTY_UUID_RE.match(parts[0]) or "embedded_submissions" in parts:
            return None
        return parts[0]
    if host in {"bugcrowd.com", "tracker.bugcrowd.com"}:
        if not parts:
            return None
        if parts[0].lower() == "engagements" and len(parts) >= 2:
            return parts[1]
        if parts[0].lower() in BUGCROWD_RESERVED:
            return None
        return parts[0]
    if host == "yeswehack.com":
        if len(parts) >= 2 and parts[0].lower() == "programs":
            return parts[1]
        return None
    if host in {"intigriti.com", "app.intigriti.com"}:
        if host == "app.intigriti.com" and len(parts) >= 2:
            return parts[0]
        if parts and parts[0].lower() == "programs" and len(parts) >= 2:
            return parts[1]
        return None
    return None

def _norm_name(s: str) -> str:
    t = re.sub(r"\b(inc|llc|ltd|corp|corporation|company|the|com)\b", " ", (s or "").lower())
    return re.sub(r"[^a-z0-9]+", " ", t).strip()

def bounty_page_names_company(title: str, text: str, company: dict, handle: str | None) -> bool:
    """True when the program page is clearly this company's, not a namesake."""
    name = company.get("name") or ""
    slug = (company.get("slug") or "").lower()
    domain = (company.get("domain") or "").lower()
    stem = domain.split(".")[0] if domain else ""
    title_n = _norm_name(title)
    blob_n = _norm_name(f"{title} {text[:2500]}")
    name_n = _norm_name(name)
    handle_n = _norm_name(handle or "")
    if name_n and name_n in title_n:
        return True
    if name_n and len(name_n) >= 5 and name_n in blob_n:
        return True
    tokens = [t for t in name_n.split() if len(t) >= 4]
    if tokens and all(t in title_n for t in tokens):
        return True
    candidates = {slug, stem}
    for raw in company.get("aliases") or []:
        h = host_of(raw) if str(raw).startswith("http") else str(raw or "").lower()
        h = h.removeprefix("www.").split("/")[0]
        if h:
            candidates.add(h.split(".")[0])
    candidates.discard("")
    if handle and (handle.lower() in candidates or (handle_n and handle_n == name_n)):
        return True
    if slug and slug.replace("-", " ") in title_n:
        return True
    # Short names (Box, Snap) need the handle or the title, not a body mention.
    if name_n and len(name_n) < 5:
        return bool(re.search(rf"\b{re.escape(name_n)}\b", title_n))
    return False

def classify_as_bounty(
    url: str, rec: dict, company: dict | None = None, *, published: bool = False
) -> bool:
    """True only for a public first-party VDP / branded platform program page."""
    if not rec.get("ok") or rec.get("status") != 200:
        return False
    title, text = rec.get("title") or "", rec.get("text") or ""
    final = rec.get("final_url") or url
    if looks_dead(title, text) or looks_like_login_wall(title, text):
        return False
    if BOUNTY_PRIVATE_RE.search(f"{title} {text[:1500]}"):
        return False
    if BOUNTY_DASHBOARD_RE.search(f"{title} {text[:2500]}"):
        return False
    if landed_on_home(url, final) and "status." not in host_of(url):
        return False
    path = path_of(final)
    host = host_of(final)
    if BOUNTY_NEWS_PATH_RE.search(path) or BOUNTY_NEWS_PATH_RE.search(urlparse(final).path or ""):
        return False
    if BOUNTY_ITEM_UID_RE.search(final) and not BOUNTY_PATH_RE.search(final):
        return False
    if BOUNTY_PROFILE_TITLE_RE.match((title or "").strip()):
        return False
    if is_bounty_platform_host(host):
        handle = bounty_platform_handle(final)
        if not handle:
            return False
        if BOUNTY_MARKETING_RE.search(f"{title} {text[:1200]}"):
            return False
        titled = bool(BOUNTY_TITLE_RE.search(title) or re.search(
            r"\b(?:hackerone|bugcrowd|yeswehack|intigriti)\b", title, re.I
        ))
        bodied = bool(BOUNTY_BODY_RE.search(text[:8000]) or BOUNTY_TITLE_RE.search(text[:2000]))
        if not (titled or bodied):
            return False
        if published:
            return True
        if company and not bounty_page_names_company(title, text, company, handle):
            return False
        return True
    path_hit = bool(BOUNTY_PATH_RE.search(path) or BOUNTY_PATH_RE.search(final))
    title_hit = bool(BOUNTY_TITLE_RE.search(title))
    body_hit = bool(BOUNTY_BODY_RE.search(text[:8000]) or BOUNTY_TITLE_RE.search(text[:2000]))
    bounty_host = host.startswith(BOUNTY_HOST_PREFIXES) or any(
        p in host for p in ("bugbounty", "bughunters", ".vdp.")
    )
    generic = path.rstrip("/") in {"/security", "/trust", "/docs/security"} or (
        host.startswith("security.") and path.rstrip("/") in {"", "/"}
    )
    if generic and not (title_hit and body_hit):
        return False
    if bounty_host and (title_hit or body_hit or (
        company and bounty_page_names_company(title, text, company, None)
    )):
        return True
    strong_title = bool(re.search(
        r"responsible disclosure|vulnerability disclosure|bug bounty|"
        r"vulnerability reward|bounty programs?",
        title, re.I,
    ))
    if path_hit and body_hit:
        return True
    if path_hit and strong_title:
        return True
    if title_hit and body_hit and not generic:
        return True
    return False

def extract_bounty_candidates(html: str, base: str) -> list[str]:
    """Hrefs that look like a VDP or branded platform program, plus named links."""
    out, seen = [], set()

    def add(u: str) -> None:
        u = (u or "").split("#")[0].strip()
        if not u.startswith("http") or u in seen:
            return
        if BOUNTY_ITEM_UID_RE.search(u) and not BOUNTY_PATH_RE.search(u):
            return
        seen.add(u)
        out.append(u)

    for href in extract_hrefs(html, base):
        host = host_of(href)
        if BOUNTY_PATH_RE.search(href) or is_bounty_platform_host(host):
            if is_bounty_platform_host(host) and not bounty_platform_handle(href):
                continue
            add(href)
    for m in A_TAG_RE.finditer(html or ""):
        raw, inner = m.group(1).strip(), strip_tags(m.group(2))
        if raw.startswith(("javascript:", "mailto:", "tel:", "data:")):
            continue
        if BOUNTY_LINK_TEXT_RE.search(inner):
            add(urljoin(base, raw))
    return out[:40]

def bounty_probe_urls_for(company: dict) -> list[str]:
    pairs, seen = [], set()

    def add(url: str) -> None:
        u = (url or "").rstrip("/")
        key = u.lower()
        if u.startswith("http") and key not in seen:
            seen.add(key)
            pairs.append(u)

    for domain in hosts_for(company)[:2]:
        for path in BOUNTY_WELL_KNOWN_PATHS:
            add(f"https://{domain}{path}")
        add(f"https://security.{domain}/responsible-disclosure")
        add(f"https://security.{domain}/vulnerability-disclosure")
        add(f"https://security.{domain}/vulnerability")
    for url, hint in SPECIAL_URLS.get(company.get("slug") or "", []):
        if hint == "bug_bounty":
            add(url)
    return pairs

def normalize_bounty_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if not host or parsed.port not in (80, 443, None):
            return url
        netloc = host
        if parsed.port and parsed.port not in (80, 443):
            netloc = f"{host}:{parsed.port}"
        return parsed._replace(netloc=netloc, fragment="").geturl()
    except Exception:
        return url

def unfile_bounty_row(row: dict) -> None:
    """Remove a bounty URL we should not have filed. Undo +6 only when we added it."""
    links = dict(row.get("links") or {})
    if "bug_bounty" not in links:
        return
    links.pop("bug_bounty", None)
    row["links"] = links
    disc = dict(row.get("disclosure") or {})
    factors = dict(disc.get("factors") or {})
    if links.get("security_txt"):
        disc["factors"] = factors
        row["disclosure"] = disc
        return
    if factors.get("disclosure") == 6:
        factors.pop("disclosure", None)
        score = max(0, int(disc.get("score") or 0) - 6)
        if not row.get("found"):
            tier = "silent"
        elif score >= 90:
            tier = "complete"
        elif score >= 70:
            tier = "substantial"
        elif score >= 40:
            tier = "on-file"
        else:
            tier = "thin"
        disc["score"] = score
        disc["tier"] = tier
        disc["factors"] = factors
        row["disclosure"] = disc

def apply_bounty_to_row(row: dict, url: str) -> bool:
    """File a bounty / VDP URL. +6 only when security.txt had not already paid it."""
    links = dict(row.get("links") or {})
    if links.get("bug_bounty"):
        return False
    links["bug_bounty"] = normalize_bounty_url(url)
    row["links"] = links
    disc = dict(row.get("disclosure") or {})
    factors = dict(disc.get("factors") or {})
    if factors.get("disclosure") or links.get("security_txt"):
        disc["factors"] = factors
        row["disclosure"] = disc
        return True
    factors["disclosure"] = 6
    score = min(100, int(disc.get("score") or 0) + 6)
    if not row.get("found"):
        tier = "silent"
    elif score >= 90:
        tier = "complete"
    elif score >= 70:
        tier = "substantial"
    elif score >= 40:
        tier = "on-file"
    else:
        tier = "thin"
    disc["score"] = score
    disc["tier"] = tier
    disc["factors"] = factors
    row["disclosure"] = disc
    return True

def file_published_bounties() -> int:
    """File first-party VDP / branded platform program URLs that were published but not stored."""
    t0 = time.time()
    src = SITE / "data" / "enriched.json"
    if not src.exists():
        src = DATA / "enriched.json"
    payload = load_json(src, {})
    companies = list(payload.get("companies") or [])
    if not companies:
        print("no companies in enriched.json", flush=True)
        return 1
    before = sum(1 for c in companies if (c.get("links") or {}).get("bug_bounty"))
    gaps = [c for c in companies if has_public_page(c) and not (c.get("links") or {}).get("bug_bounty")]
    print(f"Bounty on file: {before}. Pages with no bounty URL: {len(gaps)}", flush=True)

    filed: list[tuple[str, str]] = []
    by_slug = {c["slug"]: c for c in companies}

    def seed_urls(c: dict) -> list[str]:
        links = c.get("links") or {}
        out, seen = [], set()
        for raw in (
            c.get("trust_url"),
            c.get("final_url"),
            links.get("trust"),
            links.get("security"),
            links.get("security_txt"),
        ):
            u = (raw or "").strip()
            if u.startswith("http") and u.lower() not in seen:
                seen.add(u.lower())
                out.append(u)
        return out

    print(f"Phase 1: read {len(gaps)} found pages for a published program link…", flush=True)
    candidates: dict[str, list[str]] = {}
    seed_jobs = [(c["slug"], url) for c in gaps for url in seed_urls(c)]

    def do_seed(job):
        slug, url = job
        try:
            return slug, fetch_seed_page(url)
        except Exception:
            return slug, {"ok": False, "status": 0, "hrefs": [], "html": "", "final_url": url, "text": "", "raw_head": ""}

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = [pool.submit(do_seed, job) for job in seed_jobs]
        done = 0
        for fut in as_completed(futs):
            slug, rec = fut.result()
            done += 1
            if done % 40 == 0 or done == len(futs):
                print(f"  seed {done}/{len(futs)}", flush=True)
            row = by_slug.get(slug)
            if not row:
                continue
            html = rec.get("html") or ""
            base = rec.get("final_url") or rec.get("url") or ""
            found = extract_bounty_candidates(html, base)
            if rec.get("hrefs"):
                for href in rec["hrefs"]:
                    host = host_of(href)
                    if (BOUNTY_PATH_RE.search(href) or is_bounty_platform_host(host)) and href not in found:
                        if is_bounty_platform_host(host) and not bounty_platform_handle(href):
                            continue
                        found.append(href)
            if "security.txt" in (rec.get("url") or "").lower() or "security.txt" in (base or "").lower():
                for named in bounty_urls_from_security_txt(rec.get("raw_head") or rec.get("text") or ""):
                    if named not in found:
                        found.append(named)
            if found:
                bucket = candidates.setdefault(slug, [])
                for u in found:
                    if u not in bucket:
                        bucket.append(u)

    linked_keys = {(slug, u.lower()) for slug, urls in candidates.items() for u in urls}
    need_probe = [c for c in gaps if c["slug"] not in candidates]
    print(f"  pages already linking a program-shaped URL: {len(candidates)}", flush=True)
    print(f"Phase 2: well-known first-party paths for {len(need_probe)} still blank…", flush=True)
    for c in need_probe:
        candidates[c["slug"]] = bounty_probe_urls_for(c)

    verify_jobs = []
    seen_verify = set()
    for slug, urls in candidates.items():
        row = by_slug.get(slug)
        if not row:
            continue
        for url in urls:
            key = (slug, url.lower())
            if key in seen_verify:
                continue
            host = host_of(url)
            linked = key in linked_keys
            if not linked and not is_bounty_platform_host(host) and not host.startswith(BOUNTY_HOST_PREFIXES):
                own = {registrable(h) for h in hosts_for(row)}
                th = host_of(row.get("trust_url") or "")
                if th:
                    own.add(registrable(th))
                if registrable(host) not in own and not any(
                    host.endswith("." + h) or h.endswith("." + host) for h in own if host and h
                ):
                    continue
            seen_verify.add(key)
            verify_jobs.append((slug, url))
    print(f"Phase 3: verifying {len(verify_jobs)} candidate URLs…", flush=True)

    def do_verify(job):
        slug, url = job
        try:
            rec = fetch_uncached(url, PROBE_BODY)
        except Exception:
            rec = {"ok": False, "status": 0, "final_url": url, "title": "", "text": ""}
        return slug, url, rec

    accepted: dict[str, str] = {}

    def take_hits(jobs: list[tuple[str, str]], label: str, *, published: bool) -> None:
        if not jobs:
            return
        print(f"{label}: {len(jobs)} URLs…", flush=True)
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            futs = [pool.submit(do_verify, job) for job in jobs]
            done = 0
            for fut in as_completed(futs):
                slug, url, rec = fut.result()
                done += 1
                if done % 80 == 0 or done == len(futs):
                    print(f"  {label} {done}/{len(futs)}", flush=True)
                if slug in accepted:
                    continue
                row = by_slug.get(slug)
                if not row:
                    continue
                final = rec.get("final_url") or url
                was_published = published or ((slug, url.lower()) in linked_keys)
                if classify_as_bounty(url, rec, row, published=was_published):
                    accepted[slug] = normalize_bounty_url(final)

    take_hits(verify_jobs, "Phase 3", published=False)
    still = [c for c in gaps if c["slug"] not in accepted]
    fallback = []
    seen_fb = set(seen_verify)
    for c in still:
        for url in bounty_probe_urls_for(c):
            key = (c["slug"], url.lower())
            if key in seen_fb:
                continue
            seen_fb.add(key)
            fallback.append((c["slug"], url))
    take_hits(fallback, "Phase 4 fallback paths", published=False)

    checked = len(gaps)
    for slug, url in sorted(accepted.items()):
        row = by_slug[slug]
        if apply_bounty_to_row(row, url):
            filed.append((row.get("name") or slug, url))

    generated = utc_now()
    payload["generated_at"] = generated
    payload["companies"] = companies
    write_json(DATA / "enriched.json", payload)
    write_json(SITE / "data" / "enriched.json", payload)
    after = sum(1 for c in companies if (c.get("links") or {}).get("bug_bounty"))
    print(f"Wrote {DATA / 'enriched.json'} and {SITE / 'data' / 'enriched.json'}", flush=True)
    print(f"checked={checked} filed={len(filed)} bounty {before} → {after} in {time.time() - t0:.1f}s", flush=True)
    for name, url in filed:
        print(f"  filed {name}: {url}", flush=True)
    return 0

SEC_EXPIRES = re.compile(r"(?im)^\s*Expires\s*:\s*(\S+)")

SEC_CANONICAL = re.compile(r"(?im)^\s*Canonical\s*:\s*(\S+)")

SEC_FIELD = re.compile(r"(?im)^\s*(Contact|Policy|Expires|Canonical)\s*:\s*\S+")

def is_security_txt_path(url: str) -> bool:
    """RFC 9116 lives at /.well-known/security.txt or /security.txt. Not /security."""
    return "security.txt" in path_of(url or "").lower()

def field_url(val: str) -> str:
    """HTTP value from a security.txt field. Strip HTML tails. Do not invent."""
    val = (val or "").strip()
    val = re.sub(r"<[^>]+>.*$", "", val).strip()
    val = val.rstrip(".,;)]>")
    return val

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
    if not is_bounty_platform_host(host_of(url)):
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

CMP_VENDOR_HOSTS = {
    "onetrust.com", "onetrust.io", "cookielaw.org", "cookiepro.com",
    "privacymanager.io", "cookiebot.com", "trustarc.com", "osano.com",
    "usercentrics.com", "termly.io", "iubenda.com", "quantcast.com",
    "didomi.io", "securiti.ai", "evidon.com", "cookieinformation.com",
}

PRIVACY_STRONG_PATH_RE = re.compile(
    r"privacy[-_ ]?(?:policy|notice|statement|disclosures?)(?![-_]generator)",
    re.I,
)

PRIVACY_EXACT_PATH_RE = re.compile(
    r"(?:^|/)(?:legal|policies|policy|company|about|docs|help)?"
    r"(?:/en(?:-[a-z]{2})?)?/privacy(?:\.(?:html|htm|pdf)|/?)$",
    re.I,
)

PRIVACY_REJECT_PATH_RE = re.compile(
    r"(?:cookie-?notice|cookie-?settings|cookie-?preferences|"
    r"privacy-policy-generator|"
    r"terms-of-sale|"
    r"careers-privacy|/careers/|"
    r"privacy-notice-us-employees|[-_/]employees(?:[-_/]|$)|"
    r"workforce-privacy|candidate-privacy|candidates?-privacy|"
    r"impersonation|fraud-alert|"
    r"international-data-transfer|"
    r"consumer-health-data|/chd[-_/]|[-_/]chd(?:[-_/]|$)|"
    r"ccpa-privacy-notice|"
    r"california-privacy-notice|"
    r"session_sync|"
    r"/contact/?$)",
    re.I,
)

PRIVACY_DOC_LEAF_RE = re.compile(
    r"^(?:(?:global|online|website|group|external)[-_])?"
    r"(?:privacy(?:[-_](?:policy|notice|statement|practices))?|"
    r"privacypolicy|privacynotice|privacystatement|confidential)"
    r"(?:[-_](?:en|us|uk|english|global|riders-order-recipients|english))?$",
    re.I,
)

LOCALE_LEAF_RE = re.compile(
    r"^(?:en|us|uk|de|fr|es|it|nl|jp|ja|zh|pt|english|"
    r"en-[a-z]{2}|[a-z]{2}-[a-z]{2})$",
    re.I,
)

DISALLOWED_PRIVACY_LEAVES = {
    "contact", "cookies", "cookie-notice", "cookie-policy", "cookie-settings",
    "generator", "terms-of-sale", "terms-of-use", "terms",
}

PRIVACY_TITLE_RE = re.compile(
    r"\bprivacy[- ](?:policy|notice|statement)\b",
    re.I,
)

PRIVACY_BODY_RE = re.compile(
    r"\b(?:this privacy (?:policy|notice|statement)|"
    r"personal (?:data|information)|"
    r"information we collect|"
    r"we collect (?:personal )?(?:information|data)|"
    r"how we use (?:your )?(?:information|data)|"
    r"data protection officer|"
    r"privacy(?: policy)? describes)\b",
    re.I,
)

PRIVACY_LINK_TEXT_RE = re.compile(
    r"^\s*privacy(?:[- ](?:policy|notice|statement))?\s*$",
    re.I,
)

COOKIE_ONLY_PATH_RE = re.compile(
    r"(?:cookie(?:s|-policy|-notice|-settings|-preferences)|"
    r"your-?privacy-?choices|do-?not-?sell|ccpa-?opt-?out|"
    r"privacy-?choices|cookie-?declaration)",
    re.I,
)

NEWS_PATH_RE = re.compile(
    r"/(?:blog|news|press|articles?|insights|stories|media|resources)/",
    re.I,
)

PRIVACY_CENTER_PATH_RE = re.compile(
    r"privacy[-_](?:center|hub|program)(?:/|$)",
    re.I,
)

PRIVACY_CENTER_LEGAL_RE = re.compile(
    r"privacy[-_](?:center|hub).*(?:legal|policy|notice|statement)",
    re.I,
)

NOT_PRIVACY_INSTRUMENT_RE = re.compile(
    r"(?:sub-?process|service-providers?|bug-?bounty|"
    r"responsible-?disclosure|vulnerability-?disclosure|"
    r"/security(?:/|$)|privacy[-_]compliance)",
    re.I,
)

PRIVACY_WELL_KNOWN_PATHS = (
    "/privacy",
    "/privacy-policy",
    "/privacy-notice",
    "/privacy-statement",
    "/legal/privacy",
    "/legal/privacy-policy",
    "/legal/privacy-notice",
    "/legal/privacy-statement",
    "/policies/privacy",
    "/policies/privacy-policy",
    "/policies/privacy-notice",
    "/company/privacy",
    "/legal/privacynotice",
)

def _vendor_host_match(url: str, vendors: set[str]) -> bool:
    h = host_of(url)
    if not h:
        return False
    reg = registrable(h)
    if reg in vendors or h in vendors:
        return True
    return any(h.endswith("." + v) for v in vendors)

def is_cmp_vendor_host(url: str) -> bool:
    return _vendor_host_match(url, CMP_VENDOR_HOSTS)

def path_is_dpa(path: str) -> bool:
    return bool(DPA_PATH_RE.search(path or ""))

def path_is_cookie_only(path: str) -> bool:
    p = path or ""
    leaf = _privacy_leaf(p)
    if "cookie" in leaf and "privacy" not in leaf:
        return True
    if COOKIE_ONLY_PATH_RE.search(p) and not PRIVACY_DOC_LEAF_RE.search(leaf):
        return True
    return False

def _privacy_leaf(path: str) -> str:
    parts = [p for p in (path or "").lower().split("/") if p]
    if not parts:
        return ""
    leaf = re.sub(r"\.(html?|pdf|aspx)$", "", parts[-1].split("?")[0])
    if LOCALE_LEAF_RE.match(leaf) and len(parts) >= 2:
        return re.sub(r"\.(html?|pdf|aspx)$", "", parts[-2].split("?")[0])
    return leaf

def path_is_privacy_document(path: str) -> bool:
    leaf = _privacy_leaf(path)
    if not leaf or leaf in DISALLOWED_PRIVACY_LEAVES:
        return False
    if "generator" in leaf or ("cookie" in leaf and "privacy" not in leaf):
        return False
    if leaf == "legal" and PRIVACY_CENTER_LEGAL_RE.search(path or ""):
        return True
    parts = [p for p in (path or "").lower().split("/") if p]
    if leaf in {"policy", "notice", "statement"} and any(p == "privacy" for p in parts[:-1]):
        return True
    if PRIVACY_DOC_LEAF_RE.search(leaf) or PRIVACY_STRONG_PATH_RE.search(leaf):
        return True
    if any(PRIVACY_STRONG_PATH_RE.search(p) and "generator" not in p for p in parts):
        if re.match(r"^(?:n-\w+|[-_]|id\w+)$", leaf):
            return True
    return False

def path_is_news(path: str) -> bool:
    return bool(NEWS_PATH_RE.search(path or ""))

def path_is_privacy_center_marketing(path: str) -> bool:
    p = path or ""
    if not PRIVACY_CENTER_PATH_RE.search(p):
        return False
    return not PRIVACY_CENTER_LEGAL_RE.search(p)

def extract_privacy_candidates(html: str, base: str) -> list[str]:
    """Hrefs that look like a privacy policy, plus destinations whose link text names one."""
    out, seen = [], set()

    def add(u: str) -> None:
        u = (u or "").split("#")[0].strip()
        if not u.startswith("http") or u in seen:
            return
        path = path_of(u)
        if path_is_dpa(path) or path_is_cookie_only(path) or path_is_news(path):
            return
        if path_is_privacy_center_marketing(path):
            return
        if PRIVACY_REJECT_PATH_RE.search(path) or PRIVACY_REJECT_PATH_RE.search(u):
            return
        if NOT_PRIVACY_INSTRUMENT_RE.search(path) and not PRIVACY_STRONG_PATH_RE.search(path):
            return
        if not path_is_privacy_document(path) and not PRIVACY_EXACT_PATH_RE.search(path):
            return
        seen.add(u)
        out.append(u)

    for href in extract_hrefs(html, base):
        add(href)
    for m in A_TAG_RE.finditer(html or ""):
        raw, inner = m.group(1).strip(), strip_tags(m.group(2))
        if raw.startswith(("javascript:", "mailto:", "tel:", "data:")):
            continue
        if PRIVACY_LINK_TEXT_RE.search(inner) or PRIVACY_TITLE_RE.search(inner):
            add(urljoin(base, raw))
    return out[:40]

def classify_as_privacy(url: str, rec: dict) -> bool:
    """True only when this URL is a first-party privacy policy / notice / statement or PDF."""
    if not rec.get("ok") or rec.get("status") != 200:
        return False
    title, text = rec.get("title") or "", rec.get("text") or ""
    final = rec.get("final_url") or url
    if looks_dead(title, text) or looks_like_login_wall(title, text):
        return False
    if landed_on_home(url, final):
        return False
    if is_cmp_vendor_host(final):
        return False
    if host_of(final).startswith("app."):
        return False
    h = host_of(final)
    privacy_host = h.startswith("privacy.") or h.startswith("privacypolicy.")
    if PRIVACY_REJECT_PATH_RE.search(final) or PRIVACY_REJECT_PATH_RE.search(url):
        return False
    path = path_of(final)
    blob = f"{title} {path} {text[:2000]}"
    if path_is_dpa(path) and not PRIVACY_STRONG_PATH_RE.search(path):
        return False
    if path_is_cookie_only(path):
        return False
    if path_is_news(path):
        return False
    if path_is_privacy_center_marketing(path) and not PRIVACY_TITLE_RE.search(title):
        return False
    if NOT_PRIVACY_INSTRUMENT_RE.search(path) and not PRIVACY_STRONG_PATH_RE.search(path):
        return False
    if re.search(r"\b(?:cookie (?:policy|settings|preferences)|manage cookies)\b", title, re.I):
        if not PRIVACY_TITLE_RE.search(title):
            return False
    if (
        not path_is_privacy_document(path)
        and not PRIVACY_EXACT_PATH_RE.search(path)
        and not privacy_host
    ):
        return False
    pdf = is_pdf_rec(final, rec)
    strong = bool(path_is_privacy_document(path) and PRIVACY_STRONG_PATH_RE.search(_privacy_leaf(path)))
    exact = bool(PRIVACY_EXACT_PATH_RE.search(path) or _privacy_leaf(path) in {"privacy", "confidential"})
    title_hit = bool(PRIVACY_TITLE_RE.search(title))
    body_hit = bool(PRIVACY_BODY_RE.search(text[:8000]) or PRIVACY_TITLE_RE.search(text[:2500]))
    if pdf:
        return bool(strong or exact or title_hit)
    if strong and (title_hit or body_hit or "privacy" in blob.lower()):
        return True
    if exact and (title_hit or body_hit):
        return True
    if title_hit and body_hit and (path_is_privacy_document(path) or privacy_host):
        return True
    if privacy_host and (title_hit or body_hit) and path in {"/", ""}:
        return True
    return False

def privacy_probe_urls_for(company: dict, *, core_only: bool = False, legal_only: bool = False) -> list[str]:
    pairs, seen = [], set()

    def add(url: str) -> None:
        u = (url or "").rstrip("/")
        key = u.lower()
        if u.startswith("http") and key not in seen:
            seen.add(key)
            pairs.append(u)

    if legal_only:
        paths = (
            "/legal/privacy",
            "/legal/privacy-policy",
            "/legal/privacy-notice",
            "/legal/privacy-statement",
            "/policies/privacy",
            "/policies/privacy-policy",
        )
    elif core_only:
        paths = PRIVACY_WELL_KNOWN_PATHS[:4]
    else:
        paths = PRIVACY_WELL_KNOWN_PATHS
    for domain in hosts_for(company)[:1]:
        for path in paths:
            add(f"https://{domain}{path}")
            if not domain.startswith("www."):
                add(f"https://www.{domain}{path}")
    for url, hint in SPECIAL_URLS.get(company.get("slug") or "", []):
        if hint == "privacy":
            add(url)
    return pairs

def apply_privacy_to_row(row: dict, url: str) -> bool:
    """File a privacy-policy URL and add the +6 factor. Leave other factors as they were."""
    links = dict(row.get("links") or {})
    if links.get("privacy"):
        return False
    links["privacy"] = url
    row["links"] = links
    disc = dict(row.get("disclosure") or {})
    factors = dict(disc.get("factors") or {})
    if not factors.get("privacy"):
        factors["privacy"] = 6
        score = min(100, int(disc.get("score") or 0) + 6)
        if not row.get("found"):
            tier = "silent"
        elif score >= 90:
            tier = "complete"
        elif score >= 70:
            tier = "substantial"
        elif score >= 40:
            tier = "on-file"
        else:
            tier = "thin"
        disc["score"] = score
        disc["tier"] = tier
        disc["factors"] = factors
        row["disclosure"] = disc
    return True

def unfile_privacy_from_row(row: dict) -> bool:
    """Remove a privacy URL and the +6 factor. Leave other factors as they were."""
    links = dict(row.get("links") or {})
    if not links.get("privacy"):
        return False
    links.pop("privacy", None)
    row["links"] = links
    disc = dict(row.get("disclosure") or {})
    factors = dict(disc.get("factors") or {})
    if factors.get("privacy"):
        factors.pop("privacy", None)
        score = max(0, int(disc.get("score") or 0) - 6)
        if not row.get("found"):
            tier = "silent"
        elif score >= 90:
            tier = "complete"
        elif score >= 70:
            tier = "substantial"
        elif score >= 40:
            tier = "on-file"
        else:
            tier = "thin"
        disc["score"] = score
        disc["tier"] = tier
        disc["factors"] = factors
        row["disclosure"] = disc
    return True

def file_published_privacy() -> int:
    """File first-party privacy-policy URLs already published on pages that had none."""
    t0 = time.time()
    src = SITE / "data" / "enriched.json"
    if not src.exists():
        src = DATA / "enriched.json"
    payload = load_json(src, {})
    companies = list(payload.get("companies") or [])
    if not companies:
        print("no companies in enriched.json", flush=True)
        return 1
    before = sum(1 for c in companies if (c.get("links") or {}).get("privacy"))
    gaps = [c for c in companies if not (c.get("links") or {}).get("privacy")]
    print(f"Privacy on file: {before}. Rows with no privacy URL: {len(gaps)}", flush=True)

    filed: list[tuple[str, str]] = []
    by_slug = {c["slug"]: c for c in companies}

    def seed_urls(c: dict) -> list[str]:
        links = c.get("links") or {}
        out, seen = [], set()
        for raw in (
            c.get("trust_url"),
            c.get("final_url"),
            links.get("trust"),
            links.get("security"),
        ):
            u = (raw or "").strip()
            if u.startswith("http") and u.lower() not in seen:
                seen.add(u.lower())
                out.append(u)
        for domain in hosts_for(c)[:1]:
            home = f"https://{domain}/"
            if home.lower() not in seen:
                seen.add(home.lower())
                out.append(home)
        return out

    print(f"Phase 1: read {len(gaps)} pages for a published privacy-policy link…", flush=True)
    candidates: dict[str, list[str]] = {}
    seed_jobs = [(c["slug"], url) for c in gaps for url in seed_urls(c)]

    def do_seed(job):
        slug, url = job
        try:
            return slug, fetch_seed_page(url)
        except Exception:
            return slug, {"ok": False, "status": 0, "hrefs": [], "html": "", "final_url": url}

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = [pool.submit(do_seed, job) for job in seed_jobs]
        done = 0
        for fut in as_completed(futs):
            slug, rec = fut.result()
            done += 1
            if done % 40 == 0 or done == len(futs):
                print(f"  seed {done}/{len(futs)}", flush=True)
            row = by_slug.get(slug)
            if not row:
                continue
            html = rec.get("html") or ""
            base = rec.get("final_url") or rec.get("url") or ""
            found = extract_privacy_candidates(html, base)
            if rec.get("hrefs"):
                for href in rec["hrefs"]:
                    if href not in found:
                        path = path_of(href)
                        if (
                            PRIVACY_STRONG_PATH_RE.search(href)
                            or PRIVACY_EXACT_PATH_RE.search(path)
                        ) and not path_is_dpa(path) and not path_is_cookie_only(path):
                            found.append(href)
            if found:
                bucket = candidates.setdefault(slug, [])
                for u in found:
                    if u not in bucket:
                        bucket.append(u)

    need_probe = [c for c in gaps if c["slug"] not in candidates]
    print(f"  pages already linking a privacy-shaped URL: {len(candidates)}", flush=True)
    print(f"Phase 2: well-known first-party paths for {len(need_probe)} still blank…", flush=True)
    for c in need_probe:
        candidates[c["slug"]] = privacy_probe_urls_for(c, core_only=True)

    verify_jobs = []
    seen_verify = set()
    for slug, urls in candidates.items():
        row = by_slug.get(slug)
        if not row:
            continue
        for url in urls:
            key = (slug, url.lower())
            if key in seen_verify:
                continue
            if not is_first_party_url(url, row):
                continue
            seen_verify.add(key)
            verify_jobs.append((slug, url))
    print(f"Phase 3: verifying {len(verify_jobs)} candidate URLs…", flush=True)

    def do_verify(job):
        slug, url = job
        try:
            rec = fetch_uncached(url, PROBE_BODY if not url.lower().endswith(".pdf") else TRUST_BODY)
        except Exception:
            rec = {"ok": False, "status": 0, "final_url": url, "title": "", "text": ""}
        return slug, url, rec

    accepted: dict[str, str] = {}

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
                if done % 80 == 0 or done == len(futs):
                    print(f"  {label} {done}/{len(futs)}", flush=True)
                if slug in accepted:
                    continue
                row = by_slug.get(slug)
                if not row:
                    continue
                final = rec.get("final_url") or url
                if not is_first_party_url(final, row):
                    continue
                if classify_as_privacy(url, rec):
                    accepted[slug] = final

    take_hits(verify_jobs, "Phase 3")
    still = [c for c in gaps if c["slug"] not in accepted]
    fallback = []
    seen_fb = set(seen_verify)
    for c in still:
        for url in privacy_probe_urls_for(c, legal_only=True):
            key = (c["slug"], url.lower())
            if key in seen_fb:
                continue
            if not is_first_party_url(url, c):
                continue
            seen_fb.add(key)
            fallback.append((c["slug"], url))
    take_hits(fallback, "Phase 4 fallback paths")

    checked = len(gaps)
    for slug, url in sorted(accepted.items()):
        row = by_slug[slug]
        if apply_privacy_to_row(row, url):
            filed.append((row.get("name") or slug, url))

    generated = utc_now()
    payload["generated_at"] = generated
    payload["companies"] = companies
    write_json(DATA / "enriched.json", payload)
    write_json(SITE / "data" / "enriched.json", payload)
    after = sum(1 for c in companies if (c.get("links") or {}).get("privacy"))
    print(f"Wrote {DATA / 'enriched.json'} and {SITE / 'data' / 'enriched.json'}", flush=True)
    print(f"checked={checked} filed={len(filed)} privacy {before} → {after} in {time.time() - t0:.1f}s", flush=True)
    for name, url in filed:
        print(f"  filed {name}: {url}", flush=True)
    return 0

def is_first_party_url(url: str, company: dict) -> bool:
    if is_portal_vendor_host(url, company) or is_cmp_vendor_host(url):
        return False
    hosts = set(hosts_for(company))
    for raw in (company.get("trust_url"), company.get("final_url"), company.get("domain")):
        if not raw:
            continue
        h = host_of(raw) if str(raw).startswith("http") else str(raw)
        h = (h or "").lower().removeprefix("www.")
        if h:
            hosts.add(h)
    regs = {registrable(x) for x in hosts if x}
    h = host_of(url)
    if not h:
        return False
    if h in hosts or registrable(h) in regs:
        return True
    return any(
        h.endswith("." + known) or known.endswith("." + h)
        for known in (hosts | regs)
        if known
    )

if __name__ == "__main__":
    if "--named-processors" in sys.argv:
        raise SystemExit(file_named_from_cited())
    if "--file-dpas" in sys.argv:
        raise SystemExit(file_published_dpas())
    if "--file-years" in sys.argv:
        raise SystemExit(file_published_years())
    if "--file-marks" in sys.argv:
        raise SystemExit(file_marks())
    if "--file-status" in sys.argv:
        raise SystemExit(file_published_status())
    if "--file-bounties" in sys.argv:
        raise SystemExit(file_published_bounties())
    if "--file-security-txt" in sys.argv:
        raise SystemExit(file_published_security_txt())
    if "--file-privacy" in sys.argv:
        raise SystemExit(file_published_privacy())
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
