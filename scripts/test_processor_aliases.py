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
    check(canonical_processor_id("microsoft-teams", register) == "microsoft", "Microsoft Teams is Microsoft")
    check(canonical_processor_id("google-workspace", register) == "google", "workspace → google")
    check(canonical_processor_id("google-bigquery", register) == "google", "BigQuery is Google")
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
    check(skip_processor("n-a", "n/a"), "n/a is garbage")
    check(skip_processor("talent-hire", "Talent/Hire"), "LinkedIn DPA product line is garbage")
    check(skip_processor("learning", "Learning"), "LinkedIn Learning product line is garbage")
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
    check(canonical_processor_id("oracle-systems-olaya-saudi-arabia", register) == "oracle", "Oracle Systems Limited Olaya is Oracle")
    check(REGISTER_ALIASES["oracle-systems-limited"] == "oracle", "Oracle Systems Limited is Oracle")
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
    check(canonical_processor_id("neon", db_reg) == "neon", "Neon is not Databricks")
    check("neon" not in REGISTER_ALIASES, "neon must not alias to Databricks")
    neon_reg = {**register, "neon": {"slug": "neon", "name": "Neon", "domain": "neon.tech"}}
    check(canonical_processor_id("neon", neon_reg) == "neon", "Neon keeps its own register row")
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
    pyd_reg = {**register, "pydantic": {"slug": "pydantic", "name": "Pydantic", "domain": "pydantic.dev"}}
    check(canonical_processor_id("pydantic-logfire", pyd_reg) == "pydantic", "Pydantic Logfire is Pydantic")
    conga_reg = {**register, "conga": {"slug": "conga", "name": "Conga", "domain": "conga.com"}}
    check(canonical_processor_id("appextremes-dba-conga", conga_reg) == "conga", "AppExtremes dba Conga is Conga")
    check(canonical_processor_id("oracle-america-netsuite", {**register, "netsuite": {"slug": "netsuite", "name": "NetSuite", "domain": "netsuite.com"}}) == "netsuite", "Oracle America NetSuite is NetSuite")
    docebo_reg = {**register, "docebo": {"slug": "docebo", "name": "Docebo", "domain": "docebo.com"}}
    check(canonical_processor_id("docebo-na", docebo_reg) == "docebo", "Docebo NA is Docebo")
    metro_reg = {**register, "metronome": {"slug": "metronome", "name": "Metronome", "domain": "metronome.com"}}
    check(canonical_processor_id("metronome-holdings", metro_reg) == "metronome", "Metronome Holdings is Metronome")
    val_reg = {**register, "validity": {"slug": "validity", "name": "Validity", "domain": "validity.com"}}
    check(canonical_processor_id("250ok", val_reg) == "validity", "250ok is Validity")
    co_reg = {**register, "checkout": {"slug": "checkout", "name": "Checkout.com", "domain": "checkout.com"}}
    check(canonical_processor_id("processout", co_reg) == "checkout", "ProcessOut is Checkout.com")
    bird_reg2 = {**register, "messagebird": {"slug": "messagebird", "name": "MessageBird", "domain": "messagebird.com"}}
    check(canonical_processor_id("email-data-source", bird_reg2) == "messagebird", "Email Data Source is MessageBird")
    tu_reg = {**register, "transunion-formerly-neustar-information-services": {"slug": "transunion-formerly-neustar-information-services", "name": "TransUnion", "domain": "transunion.com"}}
    check(canonical_processor_id("neustar-info-services", tu_reg) == "transunion-formerly-neustar-information-services", "Neustar Info Services is TransUnion")
    telus_reg2 = {**register, "telus": {"slug": "telus", "name": "TELUS", "domain": "telus.com"}}
    check(canonical_processor_id("telus-international", telus_reg2) == "telus", "TELUS International is TELUS")
    gp_reg = {**register, "global-payments": {"slug": "global-payments", "name": "Global Payments", "domain": "globalpayments.com"}}
    check(canonical_processor_id("propay", gp_reg) == "global-payments", "ProPay is Global Payments")
    cdw_reg = {**register, "cdw": {"slug": "cdw", "name": "CDW", "domain": "cdw.com"}}
    check(canonical_processor_id("sirius-federal", cdw_reg) == "cdw", "Sirius Federal is CDW")
    check(canonical_processor_id("microsoft-adcenter-analytics", {**register, "microsoft": register["microsoft"]}) == "microsoft", "adCenter Analytics is Microsoft")
    ibm_reg2 = {**register, "ibm": {"slug": "ibm", "name": "IBM", "domain": "ibm.com"}}
    check(canonical_processor_id("ibm-tivoli-storage-manager", ibm_reg2) == "ibm", "Tivoli Storage Manager is IBM")
    check(canonical_processor_id("windows-live-onecare", {**register, "microsoft": register["microsoft"]}) == "microsoft", "OneCare is Microsoft")
    you_reg = {**register, "susea": {"slug": "susea", "name": "You.com", "domain": "you.com"}}
    check(canonical_processor_id("susea-you-com", you_reg) == "susea", "SuSea you.com is You.com")
    tdcx_reg = {**register, "tdcx": {"slug": "tdcx", "name": "TDCX", "domain": "tdcx.com"}}
    check(canonical_processor_id("tdcx-my", tdcx_reg) == "tdcx", "TDCX MY is TDCX")
    ecore_reg = {**register, "e-core": {"slug": "e-core", "name": "e-Core", "domain": "e-core.com"}}
    check(
        canonical_processor_id("e-core-solu-es-em-tecnologia-da-informa-iup-o-ltda", ecore_reg) == "e-core",
        "e-Core legal name is e-Core",
    )
    xb_reg = {**register, "crossbeam-systems": {"slug": "crossbeam-systems", "name": "Crossbeam", "domain": "crossbeam.com"}}
    check(canonical_processor_id("reveal-sas", xb_reg) == "crossbeam-systems", "Reveal SAS is Crossbeam")
    kiss_reg = {**register, "kiss-metrics": {"slug": "kiss-metrics", "name": "KISSmetrics", "domain": "kissmetrics.io"}}
    check(canonical_processor_id("kiss-metrics-usage-analytics", kiss_reg) == "kiss-metrics", "Kiss Metrics usage analytics is KISSmetrics")
    check(canonical_processor_id("amazon-cloudfront", {**register, "amazon-web-services": register["amazon-web-services"]}) == "amazon-web-services", "CloudFront is AWS")
    atl_reg = {**register, "atlassian": {"slug": "atlassian", "name": "Atlassian", "domain": "atlassian.com"}}
    check(canonical_processor_id("opsgenie", atl_reg) == "atlassian", "OpsGenie is Atlassian")
    payu_reg = {**register, "payu": {"slug": "payu", "name": "PayU", "domain": "payu.pl"}}
    check(canonical_processor_id("zooz", payu_reg) == "payu", "Zooz is PayU")
    fn_reg = {**register, "fortinet": {"slug": "fortinet", "name": "Fortinet", "domain": "fortinet.com"}}
    check(canonical_processor_id("perception-point", fn_reg) == "fortinet", "Perception Point is Fortinet")
    eq_reg = {**register, "equifax": {"slug": "equifax", "name": "Equifax", "domain": "equifax.com"}}
    check(canonical_processor_id("kount", eq_reg) == "equifax", "Kount is Equifax")
    within_reg = {**register, "within": {"slug": "within", "name": "Within", "domain": "within.ai"}}
    check(canonical_processor_id("klarity", within_reg) == "within", "Klarity is Within")
    rad_reg = {**register, "radiant": {"slug": "radiant", "name": "Radiant", "domain": "radiant.co"}}
    check(canonical_processor_id("ori-industries", rad_reg) == "radiant", "Ori Industries is Radiant")
    ap_reg = {**register, "apryse": {"slug": "apryse", "name": "Apryse", "domain": "apryse.com"}}
    check(canonical_processor_id("bcl-technologies", ap_reg) == "apryse", "BCL Technologies is Apryse")
    xai_reg = {**register, "xai": {"slug": "xai", "name": "xAI", "domain": "x.ai"}}
    check(canonical_processor_id("spacexai", xai_reg) == "xai", "SpaceXAI is xAI when the table href is x.ai")
    check(REGISTER_ALIASES["spacexai"] == "xai", "spacexai aliases to xai")
    fig_reg2 = {**register, "figma": {"slug": "figma", "name": "Figma", "domain": "figma.com"}}
    check(canonical_processor_id("vmlapp-sweden", fig_reg2) == "figma", "Vmlapp Sweden is Figma")
    colo_reg = {**register, "colossyan": {"slug": "colossyan", "name": "Colossyan", "domain": "colossyan.com"}}
    check(canonical_processor_id("collosyan", colo_reg) == "colossyan", "Collosyan is Colossyan")
    ninja_reg = {**register, "supportninja": {"slug": "supportninja", "name": "SupportNinja", "domain": "supportninja.com"}}
    check(canonical_processor_id("ninja-partners", ninja_reg) == "supportninja", "Ninja Partners is SupportNinja")
    sf_reg = {**register, "salesforce": {"slug": "salesforce", "name": "Salesforce", "domain": "salesforce.com"}}
    check(canonical_processor_id("launchboard-software", sf_reg) == "salesforce", "Launchboard is Salesforce")
    kwai_reg = {**register, "kwai": {"slug": "kwai", "name": "Kwai", "domain": "kuaishou.com"}}
    check(canonical_processor_id("kuaishou-technology", kwai_reg) == "kwai", "Kuaishou Technology is Kwai")
    tera_reg = {**register, "teradata": {"slug": "teradata", "name": "Teradata", "domain": "teradata.com"}}
    check(canonical_processor_id("trdt-brasil-tecnologia-ltda", tera_reg) == "teradata", "TRDT Brasil is Teradata")
    ia_reg = {**register, "identity-automation-lp": {"slug": "identity-automation-lp", "name": "Identity Automation", "domain": "identityautomation.com"}}
    check(canonical_processor_id("healthcast", ia_reg) == "identity-automation-lp", "HealthCast is Identity Automation")
    fico_reg2 = {**register, "fico": {"slug": "fico", "name": "FICO", "domain": "fico.com"}}
    check(canonical_processor_id("eighth-intuition-sdn-bhd", fico_reg2) == "fico", "Eighth Intuition is FICO")
    mm_reg = {**register, "minimax-group": {"slug": "minimax-group", "name": "MiniMax Group", "domain": "minimax.io"}}
    check(canonical_processor_id("nanonoble-pte", mm_reg) == "minimax-group", "Nanonoble is MiniMax")
    tw_reg = {**register, "twilio": {"slug": "twilio", "name": "Twilio", "domain": "twilio.com"}}
    check(canonical_processor_id("sendgrid", tw_reg) == "twilio", "SendGrid is Twilio")
    check(REGISTER_ALIASES["sendgrid"] == "twilio", "sendgrid aliases to twilio")
    check(canonical_processor_id("looker", {**register, "google": register["google"]}) == "google", "Looker is Google")
    check(REGISTER_ALIASES["looker"] == "google", "looker aliases to google")
    light_reg4 = {**register, "lightspeed-commerce": {"slug": "lightspeed-commerce", "name": "Lightspeed Commerce", "domain": "lightspeedhq.com"}}
    check(canonical_processor_id("shopkeep", light_reg4) == "lightspeed-commerce", "ShopKeep is Lightspeed")
    check(canonical_processor_id("shopkeep-com", light_reg4) == "lightspeed-commerce", "shopkeep.com is Lightspeed")
    check(REGISTER_ALIASES["shopkeep"] == "lightspeed-commerce", "shopkeep aliases to lightspeed-commerce")
    sap_reg = {**register, "sap": {"slug": "sap", "name": "SAP", "domain": "sap.com"}}
    check(canonical_processor_id("calliduscloud", sap_reg) == "sap", "CallidusCloud is SAP")
    check(REGISTER_ALIASES["calliduscloud"] == "sap", "calliduscloud aliases to sap")
    gh_reg = {**register, "github": {"slug": "github", "name": "GitHub", "domain": "github.com"}}
    check(canonical_processor_id("semmle", gh_reg) == "github", "Semmle is GitHub")
    check(REGISTER_ALIASES["semmle"] == "github", "semmle aliases to github")
    clari_reg = {**register, "clari": {"slug": "clari", "name": "Clari", "domain": "clari.com"}}
    check(canonical_processor_id("groove-networks-dba-groove", clari_reg) == "clari", "Groove is Clari")
    check(REGISTER_ALIASES["groove-networks-dba-groove"] == "clari", "groove-networks-dba-groove aliases to clari")
    cp_reg = {**register, "check-point": {"slug": "check-point", "name": "Check Point", "domain": "checkpoint.com"}}
    check(canonical_processor_id("perimeter-81", cp_reg) == "check-point", "Perimeter 81 is Check Point")
    check(canonical_processor_id("perimeter81", cp_reg) == "check-point", "perimeter81 is Check Point")
    check(REGISTER_ALIASES["perimeter-81"] == "check-point", "perimeter-81 aliases to check-point")
    check(REGISTER_ALIASES["perimeter81"] == "check-point", "perimeter81 aliases to check-point")
    resp_reg = {**register, "responsive": {"slug": "responsive", "name": "Responsive", "domain": "responsive.io"}}
    check(canonical_processor_id("rfpio", resp_reg) == "responsive", "RFPIO is Responsive")
    check(REGISTER_ALIASES["rfpio"] == "responsive", "rfpio aliases to responsive")
    deepl_reg = {**register, "deepl": {"slug": "deepl", "name": "DeepL", "domain": "deepl.com"}}
    check(canonical_processor_id("deepl-deepl-com", deepl_reg) == "deepl", "DeepL deepl.com is DeepL")
    check(REGISTER_ALIASES["deepl-deepl-com"] == "deepl", "deepl-deepl-com aliases to deepl")
    tata_reg = {**register, "tata-communications": {"slug": "tata-communications", "name": "Tata Communications", "domain": "tatacommunications.com"}}
    check(canonical_processor_id("tata-communications-ireland", tata_reg) == "tata-communications", "Tata Communications Ireland is Tata Communications")
    check(REGISTER_ALIASES["tata-communications-ireland"] == "tata-communications", "tata-communications-ireland aliases to tata-communications")
    hcl_reg = {**register, "hcl-tech": {"slug": "hcl-tech", "name": "HCL Technologies", "domain": "hcltech.com"}}
    check(canonical_processor_id("hcl-america", hcl_reg) == "hcl-tech", "HCL America is HCLTech")
    check(canonical_processor_id("hcl-technologies-corporate-services", hcl_reg) == "hcl-tech", "HCL Technologies Corporate Services is HCLTech")
    check(REGISTER_ALIASES["hcl-america"] == "hcl-tech", "hcl-america aliases to hcl-tech")
    check(REGISTER_ALIASES["hcl-technologies-corporate-services"] == "hcl-tech", "hcl-technologies-corporate-services aliases to hcl-tech")
    tp_reg = {**register, "teleperformance-colombia": {"slug": "teleperformance-colombia", "name": "Teleperformance", "domain": "teleperformance.com"}}
    check(
        canonical_processor_id("ypiresia-800-teleperformance-single-member", tp_reg) == "teleperformance-colombia",
        "Ypiresia 800 is Teleperformance",
    )
    check(REGISTER_ALIASES["ypiresia-800-teleperformance-single-member"] == "teleperformance-colombia", "ypiresia-800 aliases to teleperformance-colombia")
    ap_reg = {**register, "apollo-io": {"slug": "apollo-io", "name": "Apollo.io", "domain": "apollo.io"}}
    check(canonical_processor_id("apollo", ap_reg) == "apollo-io", "Nylas Apollo is Apollo.io")
    check(REGISTER_ALIASES["apollo"] == "apollo-io", "apollo aliases to apollo-io")
    ibm_ns1 = {**register, "ibm": {"slug": "ibm", "name": "IBM", "domain": "ibm.com"}}
    check(canonical_processor_id("nsone", ibm_ns1) == "ibm", "NSONE is IBM")
    check(REGISTER_ALIASES["nsone"] == "ibm", "nsone aliases to ibm")
    tel_reg = {**register, "teleport": {"slug": "teleport", "name": "Teleport", "domain": "goteleport.com"}}
    check(canonical_processor_id("gravitational-teleport", tel_reg) == "teleport", "Gravitational (Teleport) is Teleport")
    check(REGISTER_ALIASES["gravitational-teleport"] == "teleport", "gravitational-teleport aliases to teleport")
    tp_reg2 = {**register, "teleperformance-colombia": {"slug": "teleperformance-colombia", "name": "Teleperformance", "domain": "teleperformance.com"}}
    check(
        canonical_processor_id("crm-services-india-private", tp_reg2) == "teleperformance-colombia",
        "CRM Services India is Teleperformance",
    )
    check(REGISTER_ALIASES["crm-services-india-private"] == "teleperformance-colombia", "crm-services-india-private aliases to teleperformance-colombia")
    cisco_reg = {**register, "cisco": {"slug": "cisco", "name": "Cisco", "domain": "cisco.com"}}
    check(canonical_processor_id("samknows", cisco_reg) == "cisco", "SamKnows is Cisco")
    check(REGISTER_ALIASES["samknows"] == "cisco", "samknows aliases to cisco")
    check(REGISTER_ALIASES.get("samknows") != "ookla", "samknows must not map to ookla")
    aim_reg = {**register, "ai-media": {"slug": "ai-media", "name": "Ai-Media", "domain": "ai-media.tv"}}
    check(canonical_processor_id("eeg-enterprises", aim_reg) == "ai-media", "EEG Enterprises is Ai-Media")
    check(REGISTER_ALIASES["eeg-enterprises"] == "ai-media", "eeg-enterprises aliases to ai-media")
    cap_reg = {**register, "capacity": {"slug": "capacity", "name": "Capacity", "domain": "capacity.com"}}
    check(canonical_processor_id("textel", cap_reg) == "capacity", "Textel is Capacity")
    check(REGISTER_ALIASES["textel"] == "capacity", "textel aliases to capacity")
    sum_reg = {**register, "summit": {"slug": "summit", "name": "Summit", "domain": "summithq.com"}}
    check(canonical_processor_id("deft", sum_reg) == "summit", "Deft is Summit")
    check(REGISTER_ALIASES["deft"] == "summit", "deft aliases to summit")
    enea_reg = {**register, "enea": {"slug": "enea", "name": "Enea", "domain": "enea.com"}}
    check(canonical_processor_id("adaptive-mobile", enea_reg) == "enea", "Adaptive Mobile is Enea")
    check(REGISTER_ALIASES["adaptive-mobile"] == "enea", "adaptive-mobile aliases to enea")
    check(REGISTER_ALIASES.get("adaptive-mobile") != "csg-international", "adaptive-mobile must not map to csg-international")
    gmi_reg = {**register, "gmi-cloud": {"slug": "gmi-cloud", "name": "GMI Cloud", "domain": "gmicloud.ai"}}
    check(canonical_processor_id("gmi", gmi_reg) == "gmi-cloud", "Gmi is GMI Cloud")
    check(REGISTER_ALIASES["gmi"] == "gmi-cloud", "gmi aliases to gmi-cloud")
    hg_reg = {**register, "hg-insights": {"slug": "hg-insights", "name": "HG Insights", "domain": "hginsights.com"}}
    check(canonical_processor_id("madkudu", hg_reg) == "hg-insights", "MadKudu is HG Insights")
    check(REGISTER_ALIASES["madkudu"] == "hg-insights", "madkudu aliases to hg-insights")
    aura_reg = {**register, "aura-previously-pango-anchorfree": {"slug": "aura-previously-pango-anchorfree", "name": "Aura (Previously Pango, Anchorfree)", "domain": "aura.com"}}
    check(canonical_processor_id("intersections", aura_reg) == "aura-previously-pango-anchorfree", "Intersections is Aura")
    check(REGISTER_ALIASES["intersections"] == "aura-previously-pango-anchorfree", "intersections aliases to aura-previously-pango-anchorfree")
    check(REGISTER_ALIASES.get("intersections") != "aura", "intersections must not invent a second Aura slug")
    omni_reg = {**register, "omni-analytics": {"slug": "omni-analytics", "name": "Omni Analytics", "domain": "omni.co"}}
    check(canonical_processor_id("omni", omni_reg) == "omni-analytics", "Omni is Omni Analytics")
    check(REGISTER_ALIASES["omni"] == "omni-analytics", "omni aliases to omni-analytics")
    check(REGISTER_ALIASES.get("omni") != "the-omni-group", "omni must not map to The Omni Group")
    sift_reg = {**register, "sift": {"slug": "sift", "name": "Sift", "domain": "sift.com"}}
    check(canonical_processor_id("sift-science", sift_reg) == "sift", "Sift Science is Sift")
    check(REGISTER_ALIASES["sift-science"] == "sift", "sift-science aliases to sift")
    check(REGISTER_ALIASES.get("sift-science") != "sift-science", "sift-science must not keep a second dossier")
    check(REGISTER_ALIASES["mailgun-sinch"] == "mailgun", "mailgun-sinch aliases to mailgun")
    check(REGISTER_ALIASES["firebase-cloud-messaging"] == "google", "firebase-cloud-messaging aliases to google")
    check(REGISTER_ALIASES["clickhouse-cloud"] == "clickhouse", "clickhouse-cloud aliases to clickhouse")
    lc_reg = {**register, "langchain": {"slug": "langchain", "name": "LangChain", "domain": "langchain.com"}}
    check(canonical_processor_id("langsmith", lc_reg) == "langchain", "Langsmith is LangChain")
    check(REGISTER_ALIASES["langsmith"] == "langchain", "langsmith aliases to langchain")
    check(REGISTER_ALIASES["assemblyai-via-recall-ai"] == "assemblyai", "assemblyai-via-recall-ai aliases to assemblyai")
    check(REGISTER_ALIASES["apple-push-notification-service"] == "apple", "apple-push-notification-service aliases to apple")
    check("arsys" not in REGISTER_ALIASES, "Arsys is not aliased to IONOS")
    check(REGISTER_ALIASES.get("arsys") != "ionos", "arsys must not map to ionos")
    check("conversocial" not in REGISTER_ALIASES, "Conversocial is not aliased to Verint")
    check(REGISTER_ALIASES.get("conversocial") != "verint-systems", "conversocial must not map to verint-systems")
    check(REGISTER_ALIASES.get("conversocial") != "khoros", "conversocial must not map to khoros")
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

    # LiveKit prints SpaceXAI with no x.ai href. Do not force-alias that wire.
    live = {
        "nodes": [
            {"id": "spacexai", "name": "SpaceXAI", "kind": "processor", "in_register": False},
            {"id": "xai", "name": "xAI", "domain": "x.ai", "kind": "company", "in_register": True},
            {"id": "livekit", "name": "LiveKit", "kind": "company", "in_register": True},
            {"id": "anysphere", "name": "Anysphere", "kind": "company", "in_register": True},
        ],
        "edges": [
            {"from": "livekit", "to": "spacexai", "source_url": "https://livekit.com/legal/sub-processors", "evidence": "SpaceXAI"},
            {"from": "anysphere", "to": "spacexai", "source_url": "https://trust.cursor.com/subprocessors", "evidence": "SpaceXAI"},
        ],
    }
    apply_aliases_to_graph(live, xai_reg)
    live_edges = [e for e in live["edges"] if e["from"] == "livekit"]
    cursor_edges = [e for e in live["edges"] if e["from"] == "anysphere"]
    check(live_edges == [{"from": "livekit", "to": "spacexai", "source_url": "https://livekit.com/legal/sub-processors", "evidence": "SpaceXAI"}], f"LiveKit SpaceXAI stays leftover: {live_edges}")
    check(cursor_edges[0]["to"] == "xai", "Cursor SpaceXAI still lands on xAI")
    ids = {n["id"] for n in live["nodes"]}
    check("spacexai" in ids, "LiveKit leftover SpaceXAI node stays")
    check("xai" in ids, "xAI register node stays")

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
    ac_reg = {**register, "audiocodes": {"slug": "audiocodes", "name": "AudioCodes", "domain": "audiocodes.com"}}
    check(canonical_processor_id("nuera-communications-singapore-pte", ac_reg) == "audiocodes", "Nuera Singapore is AudioCodes")
    check(canonical_processor_id("active-communications-europe", ac_reg) == "audiocodes", "ACE is AudioCodes")
    ms_reg = {**register, "microsoft": register["microsoft"]}
    check(canonical_processor_id("microsoft-hosting-services", ms_reg) == "microsoft", "Microsoft Hosting Services is Microsoft")
    mis_reg = {**register, "mistral-ai": {"slug": "mistral-ai", "name": "Mistral AI", "domain": "mistral.ai"}}
    check(canonical_processor_id("mistral", mis_reg) == "mistral-ai", "Mistral is Mistral AI")
    check(
        canonical_processor_id("microsoft-and-its-affiliates", {**register, "microsoft": register["microsoft"]})
        == "microsoft",
        "Microsoft Corporation and its Affiliates is Microsoft",
    )
    conc_reg = {**register, "concentrix": {"slug": "concentrix", "name": "Concentrix", "domain": "concentrix.com"}}
    check(canonical_processor_id("concentrix-international-europe", conc_reg) == "concentrix", "Concentrix Europe is Concentrix")
    check(canonical_processor_id("message-systems-dba-sparkpost", bird_reg) == "messagebird", "Message Systems dba Sparkpost is MessageBird")
    sm_reg = {**register, "surveymonkey": {"slug": "surveymonkey", "name": "SurveyMonkey", "domain": "surveymonkey.com"}}
    check(canonical_processor_id("momentive-fka-surveymonkey", sm_reg) == "surveymonkey", "Momentive fka SurveyMonkey is SurveyMonkey")
    check(canonical_processor_id("oracle-china-software-system", {**register, "oracle": register["oracle"]}) == "oracle", "Oracle China is Oracle")
    c42_reg = {**register, "code42": {"slug": "code42", "name": "Code42", "domain": "code42.com"}}
    check(canonical_processor_id("code-42-software", c42_reg) == "code42", "Code 42 Software is Code42")
    tdcx_reg2 = {**register, "tdcx": {"slug": "tdcx", "name": "TDCX", "domain": "tdcx.com"}}
    check(canonical_processor_id("tdcx-my-sdn-bhd", tdcx_reg2) == "tdcx", "TDCX MY SDN BHD is TDCX")
    check(canonical_processor_id("tdcx-digilab-india-private", tdcx_reg2) == "tdcx", "TDCX Digilab India is TDCX")
    google_reg2 = {**register, "google": register["google"]}
    check(canonical_processor_id("google-sign-in", google_reg2) == "google", "Google Sign-In is Google")
    check(canonical_processor_id("google-ads", google_reg2) == "google", "Google Ads is Google")
    check(canonical_processor_id("google-web-risk", google_reg2) == "google", "Google Web Risk is Google")
    meta_reg = {**register, "meta": {"slug": "meta", "name": "Meta", "domain": "meta.com"}}
    check(canonical_processor_id("meta-whatsapp", meta_reg) == "meta", "Meta (WhatsApp) is Meta")
    check(canonical_processor_id("whatsapp", meta_reg) == "meta", "WhatsApp is Meta")
    apr_reg = {**register, "apricity-group": {"slug": "apricity-group", "name": "Apricity Group", "domain": "apricitygroup.com"}}
    check(canonical_processor_id("apricity", apr_reg) == "apricity-group", "Apricity is Apricity Group")
    check(REGISTER_ALIASES["apricity"] == "apricity-group", "apricity aliases to apricity-group")
    mako_reg = {**register, "mako-it-lab": {"slug": "mako-it-lab", "name": "Mako IT Lab", "domain": "makoitlab.com"}}
    check(canonical_processor_id("mako-it-lab-pvt", mako_reg) == "mako-it-lab", "Mako IT Lab Pvt Ltd is Mako IT Lab")
    check(REGISTER_ALIASES["mako-it-lab-pvt"] == "mako-it-lab", "mako-it-lab-pvt aliases to mako-it-lab")
    fwd_reg = {**register, "fwd-deploy": {"slug": "fwd-deploy", "name": "fwdDeploy", "domain": "fwddeploy.ai"}}
    check(canonical_processor_id("saasgenie", fwd_reg) == "fwd-deploy", "SaasGenie is fwdDeploy")
    check(REGISTER_ALIASES["saasgenie"] == "fwd-deploy", "saasgenie aliases to fwd-deploy")
    smind_reg = {**register, "software-mind": {"slug": "software-mind", "name": "Software Mind", "domain": "softwaremind.com"}}
    check(canonical_processor_id("software-minds", smind_reg) == "software-mind", "Software Minds is Software Mind")
    check(REGISTER_ALIASES["software-minds"] == "software-mind", "software-minds aliases to software-mind")
    mstar_reg = {**register, "marketstar": {"slug": "marketstar", "name": "MarketStar", "domain": "marketstar.com"}}
    check(canonical_processor_id("regalix", mstar_reg) == "marketstar", "Regalix is MarketStar")
    check(REGISTER_ALIASES["regalix"] == "marketstar", "regalix aliases to marketstar")
    cc_reg = {**register, "codecentric": {"slug": "codecentric", "name": "codecentric", "domain": "codecentric.de"}}
    check(canonical_processor_id("cc-cloud", cc_reg) == "codecentric", "cc cloud GmbH is codecentric")
    check(REGISTER_ALIASES["cc-cloud"] == "codecentric", "cc-cloud aliases to codecentric")
    level_reg = {**register, "level-ai": {"slug": "level-ai", "name": "Level AI", "domain": "thelevel.ai"}}
    check(canonical_processor_id("ujwal", level_reg) == "level-ai", "Ujwal Inc is Level AI")
    check(REGISTER_ALIASES["ujwal"] == "level-ai", "ujwal aliases to level-ai")
    adi_reg = {**register, "ai-data-innovations": {"slug": "ai-data-innovations", "name": "AI Data Innovations", "domain": "aidatainnovations.com"}}
    check(canonical_processor_id("ai-data-innovation", adi_reg) == "ai-data-innovations", "AI Data Innovation Corporation is AI Data Innovations")
    check(REGISTER_ALIASES["ai-data-innovation"] == "ai-data-innovations", "ai-data-innovation aliases to ai-data-innovations")
    amx_reg = {**register, "amx": {"slug": "amx", "name": "AMX", "domain": "amxconsulting.com"}}
    check(canonical_processor_id("agile-management-experts", amx_reg) == "amx", "Agile Management Experts is AMX")
    check(REGISTER_ALIASES["agile-management-experts"] == "amx", "agile-management-experts aliases to amx")
    e2_reg = {**register, "e2open": {"slug": "e2open", "name": "E2open", "domain": "e2open.com"}}
    check(canonical_processor_id("avertech", e2_reg) == "e2open", "Avertech is E2open")
    check(REGISTER_ALIASES["avertech"] == "e2open", "avertech aliases to e2open")
    mosse_reg = {**register, "mosse-security": {"slug": "mosse-security", "name": "Mossé Security", "domain": "mosse-security.com"}}
    check(canonical_processor_id("benjamin-mosse-consulting", mosse_reg) == "mosse-security", "Benjamin Mosse Consulting is Mossé Security")
    check(REGISTER_ALIASES["benjamin-mosse-consulting"] == "mosse-security", "benjamin-mosse-consulting aliases to mosse-security")
    check(canonical_processor_id("bigquery", register) == "google", "BigQuery is Google")
    check(REGISTER_ALIASES["bigquery"] == "google", "bigquery aliases to google")
    docker_reg = {**register, "docker-inc": {"slug": "docker-inc", "name": "Docker, Inc.", "domain": "docker.com"}}
    check(canonical_processor_id("docker-hub", docker_reg) == "docker-inc", "Docker Hub is Docker")
    check(REGISTER_ALIASES["docker-hub"] == "docker-inc", "docker-hub aliases to docker-inc")
    check(canonical_processor_id("oracle-oci", register) == "oracle", "Oracle OCI is Oracle")
    check(REGISTER_ALIASES["oracle-oci"] == "oracle", "oracle-oci aliases to oracle")
    redis_reg = {**register, "redis": {"slug": "redis", "name": "Redis", "domain": "redislabs.com"}}
    check(canonical_processor_id("redis-cloud", redis_reg) == "redis", "Redis Cloud is Redis")
    check(REGISTER_ALIASES["redis-cloud"] == "redis", "redis-cloud aliases to redis")
    front_reg = {**register, "front": {"slug": "front", "name": "Front", "domain": "front.com"}}
    check(canonical_processor_id("frontapp-sarl", front_reg) == "front", "FrontApp SARL is Front")
    check(REGISTER_ALIASES["frontapp-sarl"] == "front", "frontapp-sarl aliases to front")

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
