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
    check(canonical_processor_id("ovh", ovh_reg) == "ovhcloud", "OVH is OVHcloud")
    fico_reg = {**register, "fico": {"slug": "fico", "name": "FICO", "domain": "fico.com"}}
    check(canonical_processor_id("fair-isaac", fico_reg) == "fico", "Fair Isaac is FICO")
    check(canonical_processor_id("fair-isaac-deutschland", fico_reg) == "fico", "Fair Isaac Deutschland is FICO")
    air_reg = {**register, "airtable": {"slug": "airtable", "name": "Airtable", "domain": "airtable.com"}}
    check(canonical_processor_id("formagrid-uk", air_reg) == "airtable", "Formagrid is Airtable")
    bob_reg = {**register, "hibob": {"slug": "hibob", "name": "HiBob", "domain": "hibob.com"}}
    check(canonical_processor_id("hi-bob", bob_reg) == "hibob", "Hi Bob is HiBob")
    check(canonical_processor_id("open-ai", {**register, "openai": {"slug": "openai", "name": "OpenAI", "domain": "openai.com"}}) == "openai", "Open AI is OpenAI")
    five_reg = {**register, "fivetran": {"slug": "fivetran", "name": "Fivetran", "domain": "fivetran.com"}}
    check(canonical_processor_id("census", five_reg) == "fivetran", "Census is Fivetran")
    nice_reg = {**register, "nice": {"slug": "nice", "name": "NICE", "domain": "nice.com"}}
    check(canonical_processor_id("cognigy", nice_reg) == "nice", "Cognigy is NICE")
    check(canonical_processor_id("incontact", nice_reg) == "nice", "inContact is NICE")
    check(REGISTER_ALIASES["cloudfare"] == "cloudflare", "Cloudfare typo is Cloudflare")
    check(REGISTER_ALIASES["work-os"] == "workos", "Work OS is WorkOS")
    check(REGISTER_ALIASES["x-ai"] == "xai", "X.AI is xAI")
    tray_reg = {**register, "tray-ai": {"slug": "tray-ai", "name": "Tray.ai", "domain": "tray.ai"}}
    check(canonical_processor_id("tray-io", tray_reg) == "tray-ai", "Tray.io is Tray.ai")
    cart_reg = {**register, "cartesia": {"slug": "cartesia", "name": "Cartesia", "domain": "cartesia.ai"}}
    check(canonical_processor_id("cartesia-ai", cart_reg) == "cartesia", "Cartesia AI is Cartesia")
    pega_reg = {**register, "pegasystems": {"slug": "pegasystems", "name": "Pegasystems", "domain": "pega.com"}}
    check(canonical_processor_id("pega-japan", pega_reg) == "pegasystems", "Pega Japan is Pegasystems")
    ramp_reg = {**register, "liveramp": {"slug": "liveramp", "name": "LiveRamp", "domain": "liveramp.com"}}
    check(canonical_processor_id("habu", ramp_reg) == "liveramp", "Habu is LiveRamp")
    algo_reg = {**register, "algolia": {"slug": "algolia", "name": "Algolia", "domain": "algolia.com"}}
    check(canonical_processor_id("sajari-a-k-a-search-io", algo_reg) == "algolia", "Search.io is Algolia")
    check(canonical_processor_id("sajari", algo_reg) == "algolia", "Sajari is Algolia")
    digi_reg = {**register, "digicert": {"slug": "digicert", "name": "DigiCert", "domain": "digicert.com"}}
    check(canonical_processor_id("dns-made-easy", digi_reg) == "digicert", "DNS Made Easy is DigiCert")
    comm_reg = {**register, "commvault": {"slug": "commvault", "name": "Commvault", "domain": "commvault.com"}}
    check(canonical_processor_id("clumio", comm_reg) == "commvault", "Clumio is Commvault")
    hex_reg = {**register, "hex": {"slug": "hex", "name": "Hex", "domain": "hex.tech"}}
    check(canonical_processor_id("hex-technologies", hex_reg) == "hex", "Hex Technologies is Hex")
    knock_reg = {**register, "knock": {"slug": "knock", "name": "Knock", "domain": "knock.app"}}
    check(canonical_processor_id("knock-labs", knock_reg) == "knock", "Knock Labs is Knock")
    zoominfo_reg = {**register, "zoominfo": {"slug": "zoominfo", "name": "ZoomInfo", "domain": "zoominfo.com"}}
    check(canonical_processor_id("neverbounce", zoominfo_reg) == "zoominfo", "NeverBounce is ZoomInfo")
    live_reg = {**register, "liveperson": {"slug": "liveperson", "name": "LivePerson", "domain": "liveperson.com"}}
    check(canonical_processor_id("voicebase", live_reg) == "liveperson", "VoiceBase is LivePerson")
    check(canonical_processor_id("callinize-tenfold", live_reg) == "liveperson", "Tenfold is LivePerson")
    jamf_reg = {**register, "jamf": {"slug": "jamf", "name": "Jamf", "domain": "jamf.com"}}
    check(canonical_processor_id("zecops-israel", jamf_reg) == "jamf", "ZecOps is Jamf")
    monday_reg = {**register, "monday": {"slug": "monday", "name": "monday.com", "domain": "monday.com"}}
    check(canonical_processor_id("workcanvas-workassests", monday_reg) == "monday", "WorkCanvas is monday.com")
    byte_reg = {**register, "bytedance": {"slug": "bytedance", "name": "ByteDance", "domain": "bytedance.com"}}
    check(canonical_processor_id("seedance-2-0", byte_reg) == "bytedance", "Seedance is ByteDance")
    light_reg = {**register, "lightspeed-commerce": {"slug": "lightspeed-commerce", "name": "Lightspeed Commerce", "domain": "lightspeedhq.com"}}
    check(canonical_processor_id("nuorder", light_reg) == "lightspeed-commerce", "NuORDER is Lightspeed")
    db_reg = {**register, "databricks": {"slug": "databricks", "name": "Databricks", "domain": "databricks.com"}}
    check(canonical_processor_id("neon", db_reg) == "databricks", "Neon is Databricks")
    inc_reg = {**register, "incident-io": {"slug": "incident-io", "name": "incident.io", "domain": "incident.io"}}
    check(canonical_processor_id("pineapple-technology-incident-io", inc_reg) == "incident-io", "Pineapple Technology is incident.io")
    cp_reg2 = {**register, "check-point": {"slug": "check-point", "name": "Check Point", "domain": "checkpoint.com"}}
    check(canonical_processor_id("checkpoint", cp_reg2) == "check-point", "Checkpoint is Check Point")
    var_reg = {**register, "varonis": {"slug": "varonis", "name": "Varonis", "domain": "varonis.com"}}
    check(canonical_processor_id("slashnext", var_reg) == "varonis", "SlashNext is Varonis")
    readme_reg = {**register, "readme": {"slug": "readme", "name": "Readme", "domain": "readme.com"}}
    check(canonical_processor_id("readme-io", readme_reg) == "readme", "ReadMe.io is Readme")
    rl_reg = {**register, "reversing-labs": {"slug": "reversing-labs", "name": "Reversing Labs", "domain": "reversinglabs.com"}}
    check(canonical_processor_id("reversing-labs-international", rl_reg) == "reversing-labs", "Reversing Labs International is ReversingLabs")
    was_reg = {**register, "wasabi": {"slug": "wasabi", "name": "Wasabi", "domain": "wasabi.com"}}
    check(canonical_processor_id("wasabi-resources", was_reg) == "wasabi", "Wasabi Resources is Wasabi")
    check(canonical_processor_id("wasabi-technologies", was_reg) == "wasabi", "Wasabi Technologies is Wasabi")
    found_reg = {**register, "foundever-operating": {"slug": "foundever-operating", "name": "Foundever", "domain": "foundever.com"}}
    check(canonical_processor_id("foundever", found_reg) == "foundever-operating", "Foundever is Foundever Operating")
    kwai_reg = {**register, "kwai": {"slug": "kwai", "name": "Kwai", "domain": "kuaishou.com"}}
    check(canonical_processor_id("kling-ai-pte", kwai_reg) == "kwai", "Kling AI is Kuaishou")
    check(canonical_processor_id("kling", kwai_reg) == "kwai", "Kling is Kuaishou")
    fig_reg = {**register, "figma": {"slug": "figma", "name": "Figma", "domain": "figma.com"}}
    check(canonical_processor_id("weavy-ai", fig_reg) == "figma", "Weavy AI is Figma")
    pin_reg = {**register, "pinterest": {"slug": "pinterest", "name": "Pinterest", "domain": "pinterest.com"}}
    check(canonical_processor_id("tvscientific", pin_reg) == "pinterest", "tvScientific is Pinterest")
    visa_reg = {**register, "visa": {"slug": "visa", "name": "Visa", "domain": "corporate.visa.com"}}
    check(canonical_processor_id("verifi", visa_reg) == "visa", "Verifi is Visa")
    cs_reg = {**register, "contentsquare": {"slug": "contentsquare", "name": "Contentsquare", "domain": "contentsquare.com"}}
    check(canonical_processor_id("hotjar", cs_reg) == "contentsquare", "Hotjar is Contentsquare")
    bc_reg = {**register, "brightcove": {"slug": "brightcove", "name": "Brightcove", "domain": "brightcove.com"}}
    check(canonical_processor_id("zencoder", bc_reg) == "brightcove", "Zencoder is Brightcove")
    hive_reg = {**register, "hive": {"slug": "hive", "name": "Hive", "domain": "hive.com"}}
    check(canonical_processor_id("castle-global", hive_reg) == "hive", "Castle Global is Hive")
    check(canonical_processor_id("castle-global-hive", hive_reg) == "hive", "Castle Global Hive is Hive")
    temp_reg = {**register, "temporal": {"slug": "temporal", "name": "Temporal", "domain": "temporal.io"}}
    check(canonical_processor_id("temporal-technologies", temp_reg) == "temporal", "Temporal Technologies is Temporal")
    check(canonical_processor_id("temporal-cloud", temp_reg) == "temporal", "Temporal Cloud is Temporal")
    rec_reg = {**register, "recall-ai": {"slug": "recall-ai", "name": "Recall.ai", "domain": "recall.ai"}}
    check(canonical_processor_id("hyperdoc-recall-ai", rec_reg) == "recall-ai", "Hyperdoc Recall.ai is Recall.ai")
    sheet_reg2 = {**register, "smartsheet": {"slug": "smartsheet", "name": "Smartsheet", "domain": "smartsheet.com"}}
    check(canonical_processor_id("on-brand-holdings-dba-outfit", sheet_reg2) == "smartsheet", "Outfit is Smartsheet")
    check(canonical_processor_id("on-brand-australia-dba-outfit", sheet_reg2) == "smartsheet", "Outfit Australia is Smartsheet")
    check(canonical_processor_id("on-brand-investments-dba-outfit", sheet_reg2) == "smartsheet", "Outfit Investments is Smartsheet")
    rec_reg2 = {**register, "recall-ai": {"slug": "recall-ai", "name": "Recall.ai", "domain": "recall.ai"}}
    check(canonical_processor_id("hyperdoc", rec_reg2) == "recall-ai", "Hyperdoc Inc is Recall.ai")
    lex_reg = {**register, "relx-d-b-a-lexisnexis": {"slug": "relx-d-b-a-lexisnexis", "name": "LexisNexis", "domain": "lexisnexis.com"}}
    check(canonical_processor_id("lexisnexis-risk-solutions", lex_reg) == "relx-d-b-a-lexisnexis", "LexisNexis Risk is LexisNexis")
    ramp_reg2 = {**register, "liveramp": {"slug": "liveramp", "name": "LiveRamp", "domain": "liveramp.com"}}
    check(canonical_processor_id("datafleets", ramp_reg2) == "liveramp", "DataFleets is LiveRamp")
    check(canonical_processor_id("data-plus-math", ramp_reg2) == "liveramp", "Data Plus Math is LiveRamp")
    light_reg2 = {**register, "lightspeed-commerce": {"slug": "lightspeed-commerce", "name": "Lightspeed Commerce", "domain": "lightspeedhq.com"}}
    check(canonical_processor_id("payment-revolution", light_reg2) == "lightspeed-commerce", "Payment Revolution is Lightspeed")
    ph_reg = {**register, "partnerhero": {"slug": "partnerhero", "name": "PartnerHero", "domain": "partnerhero.com"}}
    check(canonical_processor_id("partner-hero", ph_reg) == "partnerhero", "Partner Hero is PartnerHero")
    dstny_reg = {**register, "dstny-automate-formerly-qunifi": {"slug": "dstny-automate-formerly-qunifi", "name": "Dstny", "domain": "dstny.com"}}
    check(canonical_processor_id("qunifi", dstny_reg) == "dstny-automate-formerly-qunifi", "Qunifi is Dstny Automate")
    light_reg3 = {**register, "lightspeed-commerce": {"slug": "lightspeed-commerce", "name": "Lightspeed Commerce", "domain": "lightspeedhq.com"}}
    check(canonical_processor_id("alcmene-s-r-l", light_reg3) == "lightspeed-commerce", "Alcmene is Lightspeed")
    check(canonical_processor_id("atelier35", light_reg3) == "lightspeed-commerce", "Atelier35 is Lightspeed")
    check(canonical_processor_id("simple-order", light_reg3) == "lightspeed-commerce", "Simple Order is Lightspeed")
    audio_reg = {**register, "audiocodes": {"slug": "audiocodes", "name": "AudioCodes", "domain": "audiocodes.com"}}
    check(canonical_processor_id("active-communications-europe", audio_reg) == "audiocodes", "Active Communications Europe is AudioCodes")
    ramp_reg3 = {**register, "liveramp": {"slug": "liveramp", "name": "LiveRamp", "domain": "liveramp.com"}}
    check(canonical_processor_id("diablo-ai", ramp_reg3) == "liveramp", "Diablo.ai is LiveRamp")
    r7_reg = {**register, "rapid7": {"slug": "rapid7", "name": "Rapid7", "domain": "rapid7.com"}}
    check(canonical_processor_id("rapid", r7_reg) == "rapid7", "Rapid, Inc. is Rapid7, not RapidAPI")
    algo_reg = {**register, "algolia": {"slug": "algolia", "name": "Algolia", "domain": "algolia.com"}}
    check(canonical_processor_id("morphl-r-d-srl", algo_reg) == "algolia", "MorphL R&D SRL is Algolia")
    check(skip_processor("customers-have-discretion-to-select-a-different-location", "Customers have discretion to select a different location"), "location discretion is garbage")
    check(skip_processor("bob-finance-module", "Bob Finance module"), "HiBob module is not a company")

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

    ot_reg = {**register, "onetrust": {"slug": "onetrust", "name": "OneTrust", "domain": "onetrust.com"}}
    check(canonical_processor_id("tugboat-logic", ot_reg) == "onetrust", "Tugboat Logic is OneTrust")
    ust_reg = {**register, "ust": {"slug": "ust", "name": "UST", "domain": "ust.com"}}
    check(canonical_processor_id("xpanxion", ust_reg) == "ust", "Xpanxion is UST")
    telus_reg = {**register, "telus": {"slug": "telus", "name": "TELUS", "domain": "telus.com"}}
    check(
        canonical_processor_id("transactel-international-services-d-b-a-telus-international", telus_reg) == "telus",
        "Transactel is TELUS",
    )
    freepik_reg = {**register, "freepik": {"slug": "freepik", "name": "Freepik", "domain": "freepik.com"}}
    check(canonical_processor_id("freepik-company-s-l-u", freepik_reg) == "freepik", "Freepik Company is Freepik")
    check(skip_processor("it", "IT LLC"), "it is garbage")
    dell_reg = {**register, "dell-technologies": {"slug": "dell-technologies", "name": "Dell Technologies", "domain": "delltechnologies.com"}}
    check(canonical_processor_id("dell", dell_reg) == "dell-technologies", "Dell is Dell Technologies")
    check(canonical_processor_id("firebase", {**register, "google": register["google"]}) == "google", "Firebase is Google")
    pp_reg = {**register, "proofpoint": {"slug": "proofpoint", "name": "Proofpoint", "domain": "proofpoint.com"}}
    check(canonical_processor_id("proofpoint-systems", pp_reg) == "proofpoint", "Proofpoint Systems is Proofpoint")
    lm_reg = {**register, "link-motion": {"slug": "link-motion", "name": "Link Motion", "domain": "link-motion.com"}}
    check(canonical_processor_id("link-motion-inc", lm_reg) == "link-motion", "Link Motion Inc is Link Motion")

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
