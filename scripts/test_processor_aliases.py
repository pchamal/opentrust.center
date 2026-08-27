#!/usr/bin/env python3
"""Alias map reuses an existing register row. Do not invent a second AWS."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from processor_aliases import (  # noqa: E402
    REGISTER_ALIASES,
    apply_aliases_to_graph,
    canonical_processor_id,
    skip_processor,
)


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"fail: {msg}")


def main() -> int:
    register = {
        "amazon-web-services": {"slug": "amazon-web-services", "name": "Amazon Web Services", "domain": "aws.amazon.com"},
        "google": {"slug": "google", "name": "Google", "domain": "google.com"},
        "microsoft": {"slug": "microsoft", "name": "Microsoft", "domain": "microsoft.com"},
        "mailgun": {"slug": "mailgun", "name": "Mailgun", "domain": "mailgun.com"},
        "elevenlabs": {"slug": "elevenlabs", "name": "ElevenLabs", "domain": "elevenlabs.io"},
        "oracle": {"slug": "oracle", "name": "Oracle", "domain": "oracle.com"},
        "cribl": {"slug": "cribl", "name": "Cribl", "domain": "cribl.io"},
    }
    check(canonical_processor_id("aws", register) == "amazon-web-services", "aws → amazon-web-services")
    check(canonical_processor_id("gcp", register) == "google", "gcp → google")
    check(canonical_processor_id("azure", register) == "microsoft", "azure → microsoft")
    check(canonical_processor_id("google-workspace", register) == "google", "workspace → google")
    check(canonical_processor_id("eleven-labs", register) == "elevenlabs", "eleven-labs → elevenlabs")
    check(canonical_processor_id("oracle-america", register) == "oracle", "oracle-america → oracle")
    check(canonical_processor_id("sentry", register) == "sentry", "unknown id stays")
    hetz_reg = {**register, "hetzner-online": {"slug": "hetzner-online", "name": "Hetzner Online", "domain": "hetzner.com"}}
    check(canonical_processor_id("hetzner", hetz_reg) == "hetzner-online", "hetzner wires land on hetzner-online")
    check(canonical_processor_id("hetzner-online", hetz_reg) == "hetzner-online", "hetzner-online stays the filed row")
    stitch_reg = {**register, "stitch": {"slug": "stitch", "name": "Stitch", "domain": "stitchdata.com"}, "qlik": {"slug": "qlik", "name": "Qlik", "domain": "qlik.com"}}
    check(canonical_processor_id("stitch", stitch_reg) == "stitch", "stitch keeps its own expand dossier")
    google_reg = {**register, "google": {"slug": "google", "name": "Google", "domain": "google.com"}}
    check(canonical_processor_id("recaptcha", google_reg) == "google", "reCAPTCHA is Google")
    check(skip_processor("entity-name", "Entity Name"), "entity-name is garbage")
    check(REGISTER_ALIASES["baseten-labs-inc"] == "baseten", "baseten legal name aliases")
    mail_reg = {**register, "mailchimp": {"slug": "mailchimp", "name": "Mailchimp", "domain": "mailchimp.com"}}
    check(canonical_processor_id("the-rocket-science-group", mail_reg) == "mailchimp", "Rocket Science Group is Mailchimp")
    check(REGISTER_ALIASES["the-rocket-science-group"] == "mailchimp", "mailchimp legal name aliases")
    par_reg = {**register, "parallel": {"slug": "parallel", "name": "Parallel", "domain": "parallel.ai"}}
    check(canonical_processor_id("parallel-web-systems", par_reg) == "parallel", "Parallel Web Systems is Parallel")
    ibm_reg = {**register, "ibm": {"slug": "ibm", "name": "IBM", "domain": "ibm.com"}}
    check(canonical_processor_id("international-business-machines-ibm", ibm_reg) == "ibm", "IBM legal name aliases")
    ada_reg = {**register, "ada": {"slug": "ada", "name": "Ada", "domain": "ada.cx"}}
    check(canonical_processor_id("ada-support", ada_reg) == "ada", "Ada Support is Ada")
    check(REGISTER_ALIASES["google-gemini"] == "google", "Gemini is Google")
    check(REGISTER_ALIASES["oracle-netsuite"] == "netsuite", "Oracle NetSuite keeps the NetSuite row")
    adobe_reg = {**register, "adobe": {"slug": "adobe", "name": "Adobe", "domain": "adobe.com"}}
    check(canonical_processor_id("marketo", adobe_reg) == "adobe", "Marketo is Adobe")
    bird_reg = {**register, "messagebird": {"slug": "messagebird", "name": "MessageBird", "domain": "messagebird.com"}}
    check(canonical_processor_id("sparkpost", bird_reg) == "messagebird", "SparkPost is MessageBird")
    zoom_reg = {**register, "zoom": {"slug": "zoom", "name": "Zoom", "domain": "zoom.us"}}
    check(canonical_processor_id("solvvy", zoom_reg) == "zoom", "Solvvy is Zoom")
    check(canonical_processor_id("keybase", zoom_reg) == "zoom", "Keybase is Zoom")
    check(canonical_processor_id("saasbee-hefei", zoom_reg) == "zoom", "Saasbee Hefei is Zoom")
    check(canonical_processor_id("saasbee-software-hangzhou", zoom_reg) == "zoom", "Saasbee Hangzhou is Zoom")
    cloud_reg = {**register, "84codes-cloudamqp": {"slug": "84codes-cloudamqp", "name": "CloudAMQP", "domain": "cloudamqp.com"}}
    check(canonical_processor_id("84codes-dba-cloudamqp", cloud_reg) == "84codes-cloudamqp", "84codes dba CloudAMQP is CloudAMQP")
    check(REGISTER_ALIASES["firebase-google"] == "google", "Firebase is Google")
    pay_reg = {**register, "paypal": {"slug": "paypal", "name": "PayPal", "domain": "paypal.com"}}
    check(canonical_processor_id("braintree", pay_reg) == "paypal", "Braintree is PayPal")
    sheet_reg = {**register, "smartsheet": {"slug": "smartsheet", "name": "Smartsheet", "domain": "smartsheet.com"}}
    check(canonical_processor_id("brandfolder", sheet_reg) == "smartsheet", "Brandfolder is Smartsheet")
    verint_reg = {**register, "verint-systems": {"slug": "verint-systems", "name": "Verint Systems", "domain": "verint.com"}}
    check(canonical_processor_id("calabrio", verint_reg) == "verint-systems", "Calabrio is Verint")
    cp_reg = {**register, "check-point": {"slug": "check-point", "name": "Check Point", "domain": "checkpoint.com"}}
    check(canonical_processor_id("avanan", cp_reg) == "check-point", "Avanan is Check Point")
    vultr_reg = {**register, "vultr": {"slug": "vultr", "name": "Vultr", "domain": "vultr.com"}}
    check(canonical_processor_id("the-constant-company-vultr", vultr_reg) == "vultr", "Constant Company is Vultr")
    graf_reg = {**register, "grafana-labs": {"slug": "grafana-labs", "name": "Grafana Labs", "domain": "grafana.com"}}
    check(canonical_processor_id("raintank-d-b-a-grafana-labs", graf_reg) == "grafana-labs", "Raintank is Grafana Labs")
    aiven_reg = {**register, "aiven": {"slug": "aiven", "name": "Aiven", "domain": "aiven.io"}}
    check(canonical_processor_id("aiven-apache-kafka", aiven_reg) == "aiven", "Aiven Kafka is Aiven")
    check(canonical_processor_id("oracle-finland", register) == "oracle", "Oracle Finland is Oracle")
    ovh_reg = {**register, "ovhcloud": {"slug": "ovhcloud", "name": "OVHcloud", "domain": "ovhcloud.com"}}
    check(canonical_processor_id("ovh-sas", ovh_reg) == "ovhcloud", "OVH SAS is OVHcloud")

    subs = {
        "nodes": [
            {"id": "aws", "name": "Amazon Web Services", "domain": "aws.amazon.com", "kind": "processor", "in_register": False},
            {"id": "gcp", "name": "Google Cloud", "domain": "cloud.google.com", "kind": "processor", "in_register": False},
            {"id": "cribl", "name": "Cribl", "domain": "cribl.io", "kind": "company", "in_register": True},
            {"id": "entity-name", "name": "Entity Name", "kind": "processor", "in_register": False},
        ],
        "edges": [
            {"from": "cribl", "to": "aws", "source_url": "https://cribl.io/legal/sub-processors/", "evidence": "Amazon Web Services"},
            {"from": "cribl", "to": "gcp", "source_url": "https://cribl.io/legal/sub-processors/", "evidence": "Google Cloud"},
            {"from": "cribl", "to": "entity-name", "source_url": "https://example.com/sub", "evidence": "Entity Name"},
        ],
    }
    apply_aliases_to_graph(subs, register)
    ids = {n["id"] for n in subs["nodes"]}
    check("aws" not in ids, "aws node is not a second row")
    check("gcp" not in ids, "gcp node is not a second row")
    check("amazon-web-services" in ids, "aws wires land on amazon-web-services")
    check("google" in ids, "gcp wires land on google")
    aws_node = next(n for n in subs["nodes"] if n["id"] == "amazon-web-services")
    check(aws_node["in_register"] is True, "aliased AWS is on the register")
    check(aws_node["domain"] == "aws.amazon.com", "aliased AWS keeps the register domain")
    tos = {e["to"] for e in subs["edges"]}
    check(tos == {"amazon-web-services", "google"}, f"edges remapped, garbage dropped: {tos}")
    check(subs["aliases"]["aws"] == "amazon-web-services", "alias map is on the graph payload")

    # Two published Google names stay two sourced rows, both on google.
    two = {
        "nodes": [
            {"id": "google-gemini", "name": "Google Gemini", "kind": "processor", "in_register": False},
            {"id": "gcp", "name": "Google Cloud", "kind": "processor", "in_register": False},
            {"id": "anysphere", "name": "Anysphere", "kind": "company", "in_register": True},
        ],
        "edges": [
            {"from": "anysphere", "to": "google-gemini", "source_url": "https://trust.cursor.com/subprocessors", "evidence": "Google Gemini"},
            {"from": "anysphere", "to": "gcp", "source_url": "https://trust.cursor.com/subprocessors", "evidence": "Google Cloud Platform"},
        ],
    }
    apply_aliases_to_graph(two, google_reg)
    google_edges = [e for e in two["edges"] if e["to"] == "google"]
    check(len(google_edges) == 2, f"two Google names stay: {google_edges}")
    check({e["evidence"] for e in google_edges} == {"Google Gemini", "Google Cloud Platform"}, "published names stay")

    # expand/keep-building prefers named-processor-gap over leftover cursor walks.
    import expand_batch

    queue = {
        "companies": [
            {"slug": "wiki-leftover", "domain": "example.com", "source": "wikipedia-software-us"},
            {"slug": "sentry", "domain": "sentry.io", "source": expand_batch.GAP_SOURCE},
        ]
    }
    state = {"cursor": 0}
    # Pretend neither is on the register yet.
    expand_batch.load_json = lambda path, default=None: {"companies": []}
    picked = expand_batch.next_batch(queue, state, 1)
    check(picked and picked[0]["slug"] == "sentry", f"gap jumps the queue: {picked}")
    check(state["cursor"] == 0, "gap pick does not burn the leftover cursor")
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
