#!/usr/bin/env python3
"""Cited URL + empty names → filed names. Walled/JS lists stay empty."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from enrich import (  # noqa: E402
    cited_list_skip_reason,
    has_filed_names,
    processors_from_company,
    published_processors_from_html,
)


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"fail: {msg}")


AIRTABLE_TABLE = """
<html><head><title>Airtable Subprocessors</title></head><body>
<h1>Airtable Subprocessors</h1>
<table>
  <tr><th>Entity</th><th>Description/Purpose</th><th>Countries</th></tr>
  <tr><td>Amazon Web Services, Inc</td><td>Cloud infrastructure</td><td>USA</td></tr>
  <tr><td>Mailgun Technologies, Inc</td><td>Transactional email</td><td>USA</td></tr>
  <tr><td>SafeBase</td><td>Trust portal host</td><td>USA</td></tr>
  <tr><td>Airtable, Inc</td><td>Ourselves</td><td>USA</td></tr>
  <tr><td>Support Service Providers</td><td></td><td></td></tr>
  <tr><td>250ok Inc. ——————————————— Email Data Source, Inc</td><td>Email</td><td>USA</td></tr>
</table>
</body></html>
"""

TWILIO_SPANS = """
<html><head><title>Twilio Sub-Processors</title></head><body>
<h1>Twilio Sub-Processors</h1>
<p><span class="copy-small">AWS</span></p>
<p><span class="copy-small">Datadog</span></p>
<p><span class="copy-small">Personal data contained in communications sent through the Twilio Services</span></p>
<p><span class="copy-small">USA</span></p>
<p><span class="copy-small">Programmable Voice</span></p>
<p><span class="copy-small">Microsoft Azure</span></p>
<p><span class="copy-small">Email (SendGrid)</span></p>
<p><span class="copy-small">Amazon Bedrock</span></p>
</body></html>
"""

VANTA_SHELL = """
<html><head><title>Algolia Trust Center</title></head>
<body>Algolia Trust Center
<script>var manifestPreload = document.createElement('link');</script>
<nav><ul><li>Home</li><li>Overview</li></ul></nav>
</body></html>
"""


def rec(url: str, html: str, title: str, status: int = 200, ctype: str = "text/html") -> dict:
    from enrich import strip_tags
    return {
        "ok": status == 200,
        "status": status,
        "final_url": url,
        "title": title,
        "text": strip_tags(html)[:80000],
        "html": html,
        "ctype": ctype,
    }


def main() -> int:
    airtable = {"slug": "airtable", "name": "Airtable", "domain": "airtable.com"}
    twilio = {"slug": "twilio", "name": "Twilio", "domain": "twilio.com"}
    algolia = {"slug": "algolia", "name": "Algolia", "domain": "algolia.com"}
    register = {
        "airtable": airtable,
        "twilio": twilio,
        "algolia": algolia,
        "amazon": {"slug": "amazon", "name": "Amazon", "domain": "amazon.com"},
    }

    url = "https://www.airtable.com/company/subprocessors"
    filed = processors_from_company(
        airtable,
        {"subprocessors": rec(url, AIRTABLE_TABLE, "Airtable Subprocessors")},
        {"subprocessors": url},
        register,
    )
    names = [n for _i, n, _e in filed]
    ids = [i for i, _n, _e in filed]
    check(any(i == "aws" for i in ids), f"aws id from table: {filed}")
    check(any("Amazon Web Services" in n for n in names), f"verbatim AWS: {names}")
    check(any("Mailgun" in n for n in names), f"verbatim Mailgun: {names}")
    check(not any("SafeBase" in n or i == "safebase" for i, n, _e in filed), f"no portal vendor: {filed}")
    check(not any("Airtable" in n for n in names), f"no self: {names}")
    check(not any("Service Providers" in n for n in names), f"no section header: {names}")
    check(any("250ok" in n for n in names) and any("Email Data Source" in n for n in names), f"split published cell: {names}")
    check(all(e == n for _i, n, e in filed), "evidence is the published name")

    # Focused hole: cited URL + empty names → filed names.
    empty_row = {"slug": "airtable", "name": "Airtable", "domain": "airtable.com", "subprocessors": []}
    check(not has_filed_names(empty_row, set()), "empty names is the hole")
    check(bool(filed), "cited URL + empty names files published rows")

    twilio_url = "https://www.twilio.com/en-us/legal/sub-processors"
    twilio_filed = published_processors_from_html(
        TWILIO_SPANS, "Twilio Sub-Processors AWS Datadog", twilio, register
    )
    twilio_names = [n for _i, n, _e in twilio_filed]
    check(any("AWS" in n or i == "aws" for i, n, _e in twilio_filed), f"twilio aws: {twilio_filed}")
    check(any("Datadog" in n for n in twilio_names), f"twilio datadog: {twilio_names}")
    check(any("Azure" in n or i == "azure" for i, n, _e in twilio_filed), f"twilio azure: {twilio_filed}")
    check(not any("Personal data" in n for n in twilio_names), f"no purpose sentence: {twilio_names}")
    check(not any(n == "USA" for n in twilio_names), f"no geo: {twilio_names}")
    check(not any("Programmable" in n for n in twilio_names), f"no product: {twilio_names}")
    check(not any("SendGrid" in n or i == "sendgrid" for i, n, _e in twilio_filed), f"no email product: {twilio_filed}")
    check(not any(i == "amazon" for i, n, _e in twilio_filed), f"bedrock is not the Amazon retailer: {twilio_filed}")
    check(any("Bedrock" in n for n in twilio_names), f"bedrock filed as published: {twilio_names}")

    wall = "https://security.attentive.com/?itemUid=e3fae2ca-94a9-416b-b577-5c90e382df57"
    check(
        cited_list_skip_reason(wall, rec(wall, "<html></html>", "Attentive"), twilio) == "safebase-itemuid",
        "itemUid stays empty",
    )
    vanta_url = "https://trust.algolia.com/subprocessors"
    vanta_rec = rec(vanta_url, VANTA_SHELL, "Algolia Trust Center")
    check(
        cited_list_skip_reason(vanta_url, vanta_rec, algolia) == "js-portal",
        f"vanta shell stays empty: {cited_list_skip_reason(vanta_url, vanta_rec, algolia)}",
    )
    check(
        processors_from_company(algolia, {"subprocessors": vanta_rec}, {"subprocessors": vanta_url}, register) == [],
        "js-only listed names stay empty",
    )
    dropbox = "https://trust.dropbox.com/ (Legal > Sub-processors item)"
    check(
        cited_list_skip_reason(dropbox, rec(dropbox, "", "Dropbox"), {"slug": "dropbox", "name": "Dropbox", "domain": "dropbox.com"}) == "annotated-url",
        "annotated URL stays empty",
    )
    pdf = "https://assets.confluent.io/m/227f69dc22168130/original/list.pdf"
    check(
        cited_list_skip_reason(pdf, rec(pdf, "", "PDF", ctype="application/pdf"), {"slug": "confluent", "name": "Confluent", "domain": "confluent.io"}) == "pdf",
        "pdf stays empty this cut",
    )
    other = "https://www.paloaltonetworks.com/resources/datasheets/palo-alto-networks-sub-processor-list"
    check(
        cited_list_skip_reason(
            other,
            rec(other, AIRTABLE_TABLE, "Sub-processor list"),
            {"slug": "cyberark", "name": "CyberArk", "domain": "cyberark.com"},
        ) == "not-first-party",
        "do not file another company's list",
    )
    aws_self = {"slug": "amazon-web-services", "name": "Amazon Web Services", "domain": "aws.amazon.com", "subprocessors": ["aws"]}
    check(not has_filed_names(aws_self, set()), "self-only aws row is still empty")
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
