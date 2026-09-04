"""Stable processor-id → register-slug map.

Catalog ids and slugified legal names that are the same company as an
existing register row. Used when building the subprocessor graph so the
map and dossiers link to the existing file. Do not invent a second row
for AWS / Google / Microsoft / Mailgun / New Relic / Modal / Baseten /
Sierra / Cerebras / ElevenLabs / Oracle / Hetzner.

Portal vendors are never named and are never alias targets.
"""
from __future__ import annotations

from pathlib import Path

# First-party tables that print a name already in REGISTER_ALIASES but
# have no homepage / privacy href for that row. Keep the leftover map
# node. Cursor's SpaceXAI wire stays on xai (Wikidata P856 / prior fill).
UNALIASED_WIRES: set[tuple[str, str]] = {
    ("https://livekit.com/legal/sub-processors", "spacexai"),
}

# slug on the wire → existing register slug. Only applied when the
# destination is already on the register.
REGISTER_ALIASES: dict[str, str] = {
    "aws": "amazon-web-services",
    "gcp": "google",
    "azure": "microsoft",
    "mailgun-technologies": "mailgun",
    "google-workspace": "google",
    "google-analytics": "google",
    "newrelic": "new-relic",
    "modal-labs": "modal",
    "baseten-labs": "baseten",
    "baseten-labs-inc": "baseten",
    "sierra-technologies": "sierra",
    "cerebras-systems": "cerebras",
    "eleven-labs": "elevenlabs",
    "oracle-america": "oracle",
    # Expand filed hetzner-online. Do not invent a second Hetzner row.
    "hetzner": "hetzner-online",
    "hetzner-finland": "hetzner-online",
    "exa-labs": "exa",
    "recaptcha": "google",
    # Mailchimp legal entity. mailchimp is already on the register.
    "the-rocket-science-group": "mailchimp",
    "mail-chimp": "mailchimp",
    # Parallel Web Systems is the existing Parallel row (parallel.ai).
    "parallel-web-systems": "parallel",
    # Google products / regional entities.
    "google-gemini": "google",
    # Scoro prints Gemini as the employee AI assistant. google is on the register.
    "gemini": "google",
    "google-ireland": "google",
    "google-firebase": "google",
    "google-vertex-ai": "google",
    "google-resources": "google",
    "google-analytics-optional-sub-processor": "google",
    "google-firebase-google-analytics-google-gemini": "google",
    # Semrush names Google BigQuery next to Google Cloud Platform.
    "google-bigquery": "google",
    # Microsoft products / regional entities.
    "microsoft-clarity": "microsoft",
    "microsoft-ireland-operations": "microsoft",
    "microsoft-365-copilot": "microsoft",
    "microsoft-office": "microsoft",
    # Matterport names Microsoft Teams. microsoft is on the register.
    "microsoft-teams": "microsoft",
    # Forethought prints Microsoft Hosting Services. microsoft is on the register.
    "microsoft-hosting-services": "microsoft",
    # IBM legal name on the wire.
    "international-business-machines-ibm": "ibm",
    # Same-company legal / product ids already on the register.
    "gong-io": "gong",
    "pylon-labs": "pylon",
    "pylon-labs-inc": "pylon",
    "redis-labs": "redis",
    "decagon-ai": "decagon",
    "bandwidth": "bandwidth-inc",
    "gooddata": "gooddata-ai",
    "perplexity": "perplexity-ai",
    "modal-labs-inc": "modal",
    "ada-support": "ada",
    # Oracle Cloud is Oracle; NetSuite already has its own row.
    "oracle-cloud-infrastructure": "oracle",
    "oracle-cloud-infrastructure-oci": "oracle",
    "oracle-cloud": "oracle",
    "oracle-america-oracle": "oracle",
    "oracle-israel": "oracle",
    "oracle-eloqua": "oracle",
    # Infobip list prints Oracle Systems Limited (Olaya, Saudi Arabia).
    "oracle-systems-limited": "oracle",
    "oracle-systems-olaya-saudi-arabia": "oracle",
    "oracle-netsuite": "netsuite",
    "netsuite-oracle": "netsuite",
    # Zoom Video Communications regional entities. zoom is on the register.
    "zvc-australia": "zoom",
    "zvc-canada": "zoom",
    "zvc-france-sas": "zoom",
    "zvc-germany": "zoom",
    "zvc-india-pvt": "zoom",
    "zvc-japan-k-k": "zoom",
    "zvc-netherlands": "zoom",
    "zvc-singapore-pte": "zoom",
    "zvc-uk": "zoom",
    "zm-services-india-private": "zoom",
    # AWS products and Amazon Data Services regional entities.
    "amazon-bedrock": "amazon-web-services",
    "amazon-ses-optional-sub-processor": "amazon-web-services",
    "amazon-support-services-costa-rica-srl": "amazon-web-services",
    "amazon-technological-services-sas": "amazon-web-services",
    "amazon-data-services-argentina-s-r-l": "amazon-web-services",
    "amazon-data-services-bahrain-w-l-l": "amazon-web-services",
    "amazon-data-services-belgium-srl": "amazon-web-services",
    "amazon-data-services-costa-rica-s-r-l": "amazon-web-services",
    "amazon-data-services-czech-republic-s-r-o": "amazon-web-services",
    "amazon-data-services-denmark-aps": "amazon-web-services",
    "amazon-data-services-ecuador-amznecu-cia-ltda": "amazon-web-services",
    "amazon-data-services-estonia-o": "amazon-web-services",
    "amazon-data-services-france-sas": "amazon-web-services",
    "amazon-data-services-greece-single-member-ae": "amazon-web-services",
    "amazon-data-services-hungary-korl-tolt-felel-ss-g-t-rsas-g": "amazon-web-services",
    "amazon-data-services-italy-s-r-l": "amazon-web-services",
    "amazon-data-services-japan-g-k": "amazon-web-services",
    "amazon-data-services-malaysia-sdn-bhd": "amazon-web-services",
    "amazon-data-services-netherlands-n-v": "amazon-web-services",
    "amazon-data-services-norway-as": "amazon-web-services",
    "amazon-data-services-panama-s-de-r-l": "amazon-web-services",
    "amazon-data-services-portugal-lda": "amazon-web-services",
    "amazon-data-services-romania-s-r-l": "amazon-web-services",
    "amazon-data-services-spain-s-l-u": "amazon-web-services",
    "amazon-data-services-zagreb-d-o-o": "amazon-web-services",
    # Other verified same-company legal / product ids.
    "adobe-systems": "adobe",
    "adobe-e-sign": "adobe",
    "elevenlabs-io": "elevenlabs",
    "message-bird": "messagebird",
    "mongo-db": "mongodb",
    "full-story": "fullstory",
    "segment-i-o": "segment",
    "sendsafely-b2b": "sendsafely",
    "exa-labs-public-preview": "exa",
    "fireworks-ai-inc": "fireworks-ai",
    "fireworksai": "fireworks-ai",
    "glean-technologies": "glean",
    "slack-technologies-llc": "slack",
    "linkedin-ireland-unlimited-company": "linkedin",
    "linkedin-sales-navigator": "linkedin",
    "deepgram-inc": "deepgram",
    "deepl-se": "deepl",
    "mistral-ai-sas": "mistral-ai",
    "notion-labs-notion": "notion",
    "hashicorp-cloud": "hashicorp",
    # dbt Cloud is dbt Labs. dbt-labs is on the register.
    "dbt-cloud": "dbt-labs",
    "crusoe-cloud": "crusoe",
    "crusoe-energy-system-llc": "crusoe",
    "grafana-labs-raintank": "grafana-labs",
    "check-point-software-technologies": "check-point",
    "checkout-technology-ltd": "checkout",
    "box-com": "box",
    "brevo-sendinblue": "brevo",
    "backblaze-resources": "backblaze",
    "bitdefender-s-r-l": "bitdefender",
    "cognizant-worldwide": "cognizant",
    "genesys-telecommunications-laboratories": "genesys",
    "dropbox-international-unlimited-company": "dropbox",
    "equinix-france-sas": "equinix",
    "orca-security-uk": "orca-security",
    "sisense-sf": "sisense",
    "tenable-holdings": "tenable",
    "postmark-activecampaign": "postmark",
    "alibaba-cloud-us": "alibaba-cloud",
    "runway-ai": "runway",
    "lightricks-ltda-ai": "lightricks",
    "abbyy-finereader": "abbyy",
    "greenhouse": "greenhouse-software",
    "fal": "fal-ai",
    "creatify": "creatify-ai",
    "brave": "brave-software",
    "verint": "verint-systems",
    "sinch": "sinch-ab",
    "sumologic": "sumo-logic",
    "perimeter81": "check-point",
    "surveymonkey-momentive": "surveymonkey",
    # Adobe acquired Marketo. adobe is on the register.
    "marketo": "adobe",
    # SparkPost is Bird / MessageBird. messagebird is on the register.
    "sparkpost": "messagebird",
    # Zoom acquisitions and China engineering entities. zoom is on the register.
    # ZVC regional rows already land on zoom; do not invent a second dossier.
    "solvvy": "zoom",
    "keybase": "zoom",
    "saasbee-hefei": "zoom",
    "saasbee-software-hangzhou": "zoom",
    # Same-company leftovers after the last named-processor batch.
    "84codes-dba-cloudamqp": "84codes-cloudamqp",
    "appcues-com": "appcues",
    "iterable-com": "iterable",
    "firebase-google": "google",
    "gsuite-google": "google",
    "dyn-oracle": "oracle",
    "raintank-d-b-a-grafana-labs": "grafana-labs",
    "raintank-inc-grafana-labs": "grafana-labs",
    "raintank-known-as-grafana-labs": "grafana-labs",
    "the-constant-company-vultr": "vultr",
    "ovh-us-dba-ovhcloud": "ovhcloud",
    "meta-platforms-ireland": "meta",
    "jack-henry-associates": "jack-henry",
    "idera": "idera-inc",
    "ivanti-uk": "ivanti",
    "island-technology": "island",
    "dayzero-software-superblocks": "superblocks",
    "linear-orbit-inc": "linear",
    # ShopKeep POS is now ShopKeep by Lightspeed. shopkeep.com 301s to
    # lightspeedhq.com/shopkeep, titled "ShopKeep POS is Now ShopKeep by
    # Lightspeed". lightspeed-commerce is on the register. Vend / Ecwid /
    # Kounta / NuORDER / Payment Revolution already land here. Do not copy
    # Lightspeed's file onto the empty shopkeep shell.
    "shopkeep": "lightspeed-commerce",
    "shopkeep-com": "lightspeed-commerce",
    "concentrix-catalyst": "concentrix",
    "concentrix-cvg-customer-management-group": "concentrix",
    "palantir-federal-cloud-service-pfcs": "palantir",
    "workato-for-clickup-professional-services": "workato",
    "brave-search": "brave-software",
    "braintree": "paypal",
    "brandfolder": "smartsheet",
    "wso2-asgardeo": "wso2",
    "route-mobile-uk": "route-mobile",
    "persistent": "persistent-systems",
    "lumen": "lumen-technologies",
    "kaseya-us-previously-datto": "kaseya",
    "souq-com-for-e-commerce": "souq",
    "ibm-datastax": "ibm",
    # Verint acquired Calabrio; homepage now redirects to Verint.
    "calabrio": "verint-systems",
    # Check Point acquired Avanan.
    "avanan": "check-point",
    # Remaining Amazon Data Services regional shells.
    "pt-amazon-data-services-indonesia": "amazon-web-services",
    "servicios-amazon-data-services-chile-spa": "amazon-web-services",
    "servicios-amazon-data-services-peru-srl": "amazon-web-services",
    # Product / legal ids that land on rows filed in this increment.
    "aiven-apache-kafka": "aiven",
    "braintrust-data": "braintrust",
    "oracle-finland": "oracle",
    "ovh-sas": "ovhcloud",
    "censys-censys": "censys",
    "civilized-discourse-construction-kit": "discourse",
    # Same-company leftovers after the last named-processor batch.
    "a100-row": "amazon-web-services",
    "a100-row-servicos-de-dados-brasil-ltda": "amazon-web-services",
    "ads-turkey-veritaban-hizmetleri-irketi": "amazon-web-services",
    "amcs-sg-private-singapore": "amazon-web-services",
    "amcs-usa": "amazon-web-services",
    "data-services-saudi-arabia-one-person-company": "amazon-web-services",
    "elemental-technologies": "amazon-web-services",
    "formagrid-australia": "airtable",
    "formagrid-canada": "airtable",
    "formagrid-uk": "airtable",
    "ddog-singapore-pte": "datadog",
    "fair-isaac": "fico",
    "fair-isaac-aspac-pte": "fico",
    "fair-isaac-australia": "fico",
    "fair-isaac-australia-new-zealand-branch": "fico",
    "fair-isaac-brasil-do": "fico",
    "fair-isaac-canada": "fico",
    "fair-isaac-deutschland": "fico",
    "fair-isaac-espana-s-l": "fico",
    "fair-isaac-italy-s-r-l": "fico",
    "fair-isaac-japan-gk": "fico",
    "fair-isaac-lithuania-uab": "fico",
    "fair-isaac-mexico-de-c-v": "fico",
    "fair-isaac-nordics": "fico",
    "fair-isaac-services": "fico",
    "fair-isaac-software-india-private": "fico",
    "fair-isaac-south-africa": "fico",
    "fair-isaac-thailand": "fico",
    "fal-features-labels": "fal-ai",
    "features-labels-fal": "fal-ai",
    "cloudfare": "cloudflare",
    "cloudkarafka": "84codes-cloudamqp",
    "chorus": "zoominfo",
    "clickagy": "zoominfo",
    "arm-group-deltek": "deltek",
    "environmental-systems-research-institute": "esri",
    "byteplus-pte": "bytedance",
    "byteplus-sdn-bhd": "bytedance",
    "hi-bob": "hibob",
    "hi-bob-au": "hibob",
    "hi-bob-canada": "hibob",
    "hi-bob-de": "hibob",
    "hi-bob-nl": "hibob",
    "hi-bob-uk": "hibob",
    "hi-bob-unipessoal-lda": "hibob",
    "open-ai": "openai",
    "open-ai-l-l-c": "openai",
    "work-os": "workos",
    "x-ai": "xai",
    "sinch-america": "sinch-ab",
    "sinch-americas": "sinch-ab",
    "sinch-germany": "sinch-ab",
    "lambda-inc": "lambda",
    "lambda-labs": "lambda",
    "mistral-compute": "mistral-ai",
    # Forethought prints Mistral. mistral-ai is on the register.
    "mistral": "mistral-ai",
    "tanla-digital-labs-fz": "tanla-platforms",
    "bria-artificial-intelligence": "bria-ai",
    "vast": "vast-data",
    "hewlett-packard": "hp",
    "artefact-product-group-dba-10-000ft": "smartsheet",
    "drift-com": "salesloft",
    "ecwid": "lightspeed-commerce",
    "kounta": "lightspeed-commerce",
    "vend": "lightspeed-commerce",
    "ikentoo-france-sasu": "lightspeed-commerce",
    "cardtronics-usa-previously-ncr": "ncr-voyix",
    "cayan-tsys": "global-payments",
    "ekata": "mastercard",
    "intsights-cyber-intelligence": "rapid7",
    "catamorphic": "launchdarkly",
    "grabtaxi-holdings-pte": "grab",
    "freshservice": "freshworks",
    "mongo-db-atlas": "mongodb",
    "ovh": "ovhcloud",
    "ovh-us": "ovhcloud",
    "tray-io": "tray-ai",
    "tray-aiio": "tray-ai",
    "tray-io-optional-sub-processor": "tray-ai",
    "langsmith": "langchain",
    "sfdc-ireland": "salesforce",
    "safesforce": "salesforce",
    "incontact": "nice",
    "cognigy": "nice",
    "census": "fivetran",
    "census-sutro-labs": "fivetran",
    "npm": "github",
    "opsgenie-yaz-l-m-anonim-irketi": "atlassian",
    "pt-tdata-indonesia": "teradata",
    "tdata-malaysia-sdn-bhd": "teradata",
    "tdc-colombia-limitada": "teradata",
    "tps-unlimited": "inmoment",
    "tps-unlimited-formerly-wootric": "inmoment",
    # Wire ids that land on rows filed in this increment.
    "cartesia-ai": "cartesia",
    "cartesia-ai-inc": "cartesia",
    "discord-inc": "discord",
    "akenes-exoscale": "exoscale",
    "alphaai-technologies-dba-tavily": "tavily",
    "cantab-research-trading-as-speechmatics": "speechmatics",
    "capgemini-america": "capgemini",
    "descope-technologies-israel-2022": "descope",
    "frontapp": "front",
    # Same-company leftovers after the last named-processor batch.
    "pega-japan": "pegasystems",
    "habu": "liveramp",
    "sajari": "algolia",
    "sajari-a-k-a-search-io": "algolia",
    "sajari-usa": "algolia",
    "dns-made-easy": "digicert",
    "clumio": "commvault",
    # Wire ids that land on rows filed in this increment.
    "hex-technologies": "hex",
    "medidata-solutions": "dassault-systemes",
    "toa-technologies": "oracle",
    "rightnow-technologies": "oracle",
    "firebase": "google",
    "demandware": "salesforce",
    "clarity": "microsoft",
    "knock-labs": "knock",
    # Same-company leftovers after the last named-processor batch.
    "neverbounce": "zoominfo",
    "callinize-tenfold": "liveperson",
    "voicebase": "liveperson",
    "zecops-israel": "jamf",
    "workcanvas-workassests": "monday",
    "seedance-2-0": "bytedance",
    "nuorder": "lightspeed-commerce",
    # Neon, Inc (neon.tech) is its own register row. Do not map to Databricks.
    # Wire id that lands on the row filed in this increment.
    "pineapple-technology-incident-io": "incident-io",
    # Same-company leftovers after the last named-processor batch.
    "checkpoint": "check-point",
    # Varonis acquired SlashNext; slashnext.com now redirects to Varonis.
    "slashnext": "varonis",
    # Wire ids that land on rows filed in this increment.
    "readme-io": "readme",
    "reversing-labs-international": "reversing-labs",
    "wasabi-resources": "wasabi",
    "wasabi-technologies": "wasabi",
    # Same-company leftovers after the last named-processor batch.
    # Foundever Operating is already on the register (1659 expand).
    "foundever": "foundever-operating",
    # Kling is Kuaishou's video model. kwai is already on the register.
    "kling-ai-pte": "kwai",
    "kling": "kwai",
    "kling-3-0": "kwai",
    # Weavy AI now redirects to Figma Weave. figma is on the register.
    "weavy-ai": "figma",
    # Pinterest acquired tvScientific; homepage now prints Pinterest.
    "tvscientific": "pinterest",
    # Visa acquired Verifi (chargeback). visa is on the register.
    "verifi": "visa",
    # SMS-Magic prints product brands that are already on the register.
    "fresh-desk": "freshworks",
    "pardot": "salesforce",
    "quick-books": "intuit",
    # Wire ids that land on rows filed in this increment.
    "hotjar": "contentsquare",
    "zencoder": "brightcove",
    "castle-global": "hive",
    "castle-global-hive": "hive",
    "temporal-cloud": "temporal",
    "temporal-technologies": "temporal",
    "skilljar-for-clickup-university": "skilljar",
    "shoreline-labs-d-b-a-nightfall": "nightfall",
    "superpowered-labs-dba-vapi": "vapi",
    "here-north-america": "here",
    "tines-automation": "tines",
    "recall": "recall-ai",
    "transloadit-ii": "transloadit",
    # Same-company leftovers after the last named-processor batch.
    # Hyperdoc Inc. (Recall.ai) is the Recall.ai row already on the register.
    "hyperdoc-recall-ai": "recall-ai",
    # Outfit was acquired by Brandfolder; Brandfolder is Smartsheet.
    "on-brand-australia-dba-outfit": "smartsheet",
    "on-brand-holdings-dba-outfit": "smartsheet",
    "on-brand-investments-dba-outfit": "smartsheet",
    # Same-company leftovers after the last named-processor batch.
    # Hyperdoc Inc. is Recall.ai's legal name. recall-ai is on the register.
    "hyperdoc": "recall-ai",
    # LexisNexis Risk Solutions is the existing RELX / LexisNexis row.
    "lexisnexis-risk-solutions": "relx-d-b-a-lexisnexis",
    # LiveRamp acquired DataFleets and Data Plus Math. habu already lands here.
    "datafleets": "liveramp",
    "data-plus-math": "liveramp",
    # Payment Revolution is ShopKeep Payments by Lightspeed. lightspeed-commerce
    # is on the register; shopkeep already lands here.
    "payment-revolution": "lightspeed-commerce",
    # Same-company leftovers after the last named-processor batch.
    # Partner Hero (Atlassian) and PartnerHero (Airtable) are one BPO.
    "partner-hero": "partnerhero",
    # Qunifi is now Dstny Automate. dstny-automate-formerly-qunifi is filed
    # in this increment; qunifi.com redirects to dstny.com.
    "qunifi": "dstny-automate-formerly-qunifi",
    # Same-company leftovers after the last named-processor batch.
    # Lightspeed affiliates already listed on lightspeedhq.com/legal/subprocessors.
    # Payment Revolution / Vend / Ecwid / Kounta / NuORDER / ShopKeep / iKentoo
    # already land here.
    "alcmene-s-r-l": "lightspeed-commerce",
    "atelier35": "lightspeed-commerce",
    "simple-order": "lightspeed-commerce",
    # AudioCodes acquired Active Communications Europe in 2015. audiocodes is
    # on the register; ACE has no independent first-party homepage.
    "active-communications-europe": "audiocodes",
    # AudioCodes' own group-subprocessor table names Nuera Communications
    # Singapore PTE LTD next to AudioCodes regional entities. AudioCodes
    # acquired Nuera in 2006. Do not invent a second dossier.
    "nuera-communications-singapore-pte": "audiocodes",
    # LiveRamp acquired Diablo.ai in 2021. habu / datafleets already land here.
    "diablo-ai": "liveramp",
    # Same-company leftovers after the last named-processor batch.
    # OneTrust acquired Tugboat Logic; tugboatlogic.com redirects to onetrust.com.
    "tugboat-logic": "onetrust",
    # UST Xpanxion; xpanxion.com redirects to ust.com. ust is on the register.
    "xpanxion": "ust",
    # Transactel / TELUS International lands on the TELUS row filed earlier.
    "transactel-international-services-d-b-a-telus-international": "telus",
    # Same brand, two published legal names on first-party lists.
    "freepik-company-s-l-u": "freepik",
    "zight-formerly-cloudplus": "zight-formerly-cloudapp",
    "intouchcx-disrupt": "intouchcx",
    "transunion-canada": "transunion-formerly-neustar-information-services",
    "kiss-metrics-usage-analytics": "kiss-metrics",
    # Same-company leftovers from Wikipedia top-up this hour.
    "dell": "dell-technologies",
    "firebase": "google",
    "proofpoint-systems": "proofpoint",
    "link-motion-inc": "link-motion",
    # Rapid, Inc. is a Rapid7 group entity on Rapid7's own affiliate list
    # (same table as Rapid7 LLC / Rapid7 Ireland). Not RapidAPI. IntSights
    # already lands here. Do not invent a second Rapid7 dossier.
    "rapid": "rapid7",
    # MorphL R&D SRL is an Algolia Group affiliate on Algolia's own
    # infrastructure-and-sub-processors list (same table as Sajari).
    # morphl.io is dead. Sajari already lands here. Do not invent a
    # second Algolia dossier.
    "morphl-r-d-srl": "algolia",
    # Seekr names Pydantic Logfire. pydantic.dev prints Pydantic as the
    # company and Logfire as its product. Do not invent a second dossier.
    "pydantic-logfire": "pydantic",
    # Conga's own subprocessor list names AppExtremes, LLC dba Conga.
    "appextremes-dba-conga": "conga",
    # Same NetSuite legal id already mapped as oracle-netsuite.
    "oracle-america-netsuite": "netsuite",
    # Docebo NA is the existing Docebo row.
    "docebo-na": "docebo",
    # Metronome Holdings is the existing Metronome row (metronome.com).
    "metronome-holdings": "metronome",
    # Same-company leftovers after the last named-processor batch.
    # Validity acquired 250ok (2020); 250ok.com now prints Validity Everest.
    "250ok": "validity",
    # Checkout.com acquired ProcessOut (2020). checkout is on the register.
    "processout": "checkout",
    # SparkPost acquired Email Data Source / eDataSource; SparkPost is Bird.
    # sparkpost already lands on messagebird.
    "email-data-source": "messagebird",
    # TransUnion acquired Neustar Information Services. transunion-canada already
    # lands here.
    "neustar-info-services": "transunion-formerly-neustar-information-services",
    # Stripe names TELUS International; Transactel dba TELUS International already
    # lands on telus.
    "telus-international": "telus",
    # TSYS acquired ProPay; Global Payments acquired TSYS. cayan-tsys already lands
    # here. Lightspeed still publishes ProPay as a processor.
    "propay": "global-payments",
    # CDW acquired Sirius Computer Solutions; Sirius Federal is the federal
    # subsidiary on GitLab's professional-services list.
    "sirius-federal": "cdw",
    # Wire ids that land on rows filed in this increment.
    "solace-where-purchased-by-customer": "solace",
    "plansource-benefits-administration": "plansource",
    "ppro-payment-services": "ppro",
    # Microsoft adCenter Analytics is a Microsoft advertising product.
    "microsoft-adcenter-analytics": "microsoft",
    # IBM Tivoli Storage Manager is IBM Storage Protect. ibm is on the register.
    "ibm-tivoli-storage-manager": "ibm",
    # Windows Live OneCare is a Microsoft product.
    "windows-live-onecare": "microsoft",
    # Same-company leftovers after the last named-processor batch.
    # Harvey publishes SuSea, Inc (you.com). you.com prints You.com.
    "susea-you-com": "susea",
    # Stripe names TDCX (MY) SDN. BHD. tdcx.com prints TDCX.
    "tdcx-my": "tdcx",
    # Atlassian names the Brazilian legal entity. e-core.com prints e-Core.
    "e-core-solu-es-em-tecnologia-da-informa-iup-o-ltda": "e-core",
    # Crossbeam acquired Reveal (2024). Crossbeam's own list marks Reveal SAS
    # as Affiliate / France. crossbeam-systems is on the register.
    "reveal-sas": "crossbeam-systems",
    # Cloudinary's list names Amazon CloudFront. AWS is on the register.
    "amazon-cloudfront": "amazon-web-services",
    # Cloudinary names OpsGenie. Atlassian owns Opsgenie; the Turkish legal
    # id already lands here.
    "opsgenie": "atlassian",
    # Same-company leftovers after the last named-processor batch.
    # Cloudinary names Zooz (Payment Processing, Israel). PayU acquired Zooz
    # / PaymentsOS. payu is on the register.
    "zooz": "payu",
    # Cloudinary names Perception Point. perception-point.io now redirects
    # to Fortinet FortiMail Workspace Security. fortinet is on the register.
    "perception-point": "fortinet",
    # Recurly names Kount (fraud). Equifax acquired Kount. equifax is filed
    # in this increment.
    "kount": "equifax",
    # Rapid7 names Klarity. Klarity is Within. within is filed in this
    # increment.
    "klarity": "within",
    # Together.ai names Ori Industries. ori.co redirects to radiant.co and
    # prints Radiant. radiant is filed in this increment.
    "ori-industries": "radiant",
    # Conga names BCL Technologies with privacy@pdftron.com. The BCL brand
    # page now lives on Apryse (formerly PDFTron). apryse is filed in this
    # increment.
    "bcl-technologies": "apryse",
    # Cursor names SpaceXAI. Wikidata P856 for that published name is x.ai,
    # which is the existing xAI row. Do not invent a second dossier.
    "spacexai": "xai",
    # Same-company leftovers after the last named-processor batch.
    # Figma's own sub-processors list names Vmlapp Sweden AB as a Figma
    # Entity. Figma's S-1 subsidiary exhibit lists the same Swedish row.
    # weavy-ai already lands here. Do not invent a second Figma dossier.
    "vmlapp-sweden": "figma",
    # Powtoon prints Collosyan | Colossyan Inc. colossyan.com prints
    # Colossyan. Filed in this increment.
    "collosyan": "colossyan",
    # Conga names Ninja Partners, LLC with privacy contact @supportninja.com.
    # supportninja is already on the register. Do not invent a second dossier.
    "ninja-partners": "supportninja",
    # Meltwater names Launchboard Software Inc. with Salesforce's privacy URL
    # on that row. salesforce is on the register.
    "launchboard-software": "salesforce",
    # Vyond names Kuaishou Technology. kuaishou.com is the existing Kwai row
    # (security.kuaishou.com already on file). Kling already lands here.
    # Do not invent a second Kuaishou dossier.
    "kuaishou-technology": "kwai",
    # Teradata's own Group Entities table names TRDT Brasil Tecnologia Ltda
    # next to Teradata US / Teradata Canada / TDC Colombia. pt-tdata-indonesia,
    # tdata-malaysia-sdn-bhd, and tdc-colombia-limitada already land here.
    # Do not invent a second Teradata dossier.
    "trdt-brasil-tecnologia-ltda": "teradata",
    # Identity Automation acquired HealthCast. identity-automation-lp is on
    # the register (identityautomation.com still prints Identity Automation).
    # gohealthcast.com is 404. healthcast.com is a different/empty namesake.
    # Do not invent a second HealthCast dossier.
    "healthcast": "identity-automation-lp",
    # FICO's own subprocessors table now prints Eighth Intuition Sdn. Bhd as
    # a Malaysia Corporate Affiliate (same table as Fair Isaac Japan / Spain).
    # Prior increment left this leftover because that first-party HTML did
    # not name it. Do not invent a second FICO dossier.
    "eighth-intuition-sdn-bhd": "fico",
    # Runway names Nanonoble Pte. Ltd. MiniMax first-party terms on
    # minimax.io print Nanonoble Pte. Ltd. as the company operating those
    # services. minimax-group is on the register. hailuoai.video prints
    # Hailuo AI / MiniMax, not Nanonoble — do not file that product host.
    "nanonoble-pte": "minimax-group",
    # sendgrid.com 301s to twilio.com/en-us/sendgrid. Twilio first-party HTML
    # prints "Twilio SendGrid Email and Marketing Campaigns" and the title
    # "SendGrid Email API and Email Marketing Campaigns | Twilio".
    # twilio is on the register with a rich file. Do not invent a second
    # SendGrid ledger or copy Twilio marks onto the empty sendgrid shell.
    "sendgrid": "twilio",
    # looker.com 301s to cloud.google.com/looker. Google Cloud first-party
    # HTML titles "Looker business intelligence platform embedded analytics
    # | Google Cloud". Docs live at docs.cloud.google.com/looker/docs as
    # "Looker documentation | Google Cloud Documentation". google is on
    # the register. Do not copy Google's file onto the empty looker shell.
    "looker": "google",
    # Lightspeed names Popout, Inc. for shipping management. Popout, Inc.
    # d/b/a Shippo. Wikidata Q25303179 P856 is goshippo.com. Do not invent
    # a second Popout dossier.
    "popout": "shippo",
    # SAP acquired CallidusCloud. calliduscloud.com now serves SAP's
    # acquired-brands page titled "What is CallidusCloud | Sales Performance
    # Management". sap is on the register. Do not copy SAP's file onto the
    # empty calliduscloud shell.
    "calliduscloud": "sap",
    # GitHub acquired Semmle. semmle.com 301s to GitHub's first-party blog
    # titled "Welcoming Semmle to GitHub". github is on the register. Do not
    # copy GitHub's file onto the empty semmle shell.
    "semmle": "github",
    # Clari first-party HTML titles "Groove by Clari - Sales Engagement and
    # Prospecting | Clari" at www.clari.com/products/groove/. groove.co 200s
    # to that Clari homepage. clari is on the register. Do not copy Clari's
    # file onto the empty groove-networks-dba-groove shell.
    "groove-networks-dba-groove": "clari",
    # Check Point first-party HTML at sase.checkpoint.com titles
    # "Check Point SASE - Perimeter 81" and prints "Check Point SASE
    # (Formerly Perimeter 81)" in the meta description and JSON-LD.
    # check-point is on the register. Do not copy Check Point's file
    # onto the empty perimeter-81 shell.
    "perimeter-81": "check-point",
    # Responsive first-party HTML at www.responsive.io/about titles
    # "Driving Your Success Is Our Mission | Responsive" and prints
    # "We've always been Responsive. Now it's official." plus
    # "2015 RFPIO founded". rfpio.com 301s to www.responsive.io,
    # titled "#1 AI RFP Software & G2 Market Leader", which prints
    # RFPIO. DPA HTML names "RFPIO, Inc. d/b/a Responsive".
    # responsive is on the register. Do not copy Responsive's file
    # onto the empty rfpio shell.
    "rfpio": "responsive",
    # Responsive's first-party subprocessor table prints
    # "DeepL deepl.com". deepl is on the register.
    "deepl-deepl-com": "deepl",
    # LinkedIn customer-subprocessors table. Same-company legal /
    # regional ids already on the register.
    "microsoft-and-its-affiliates": "microsoft",
    "concentrix-international-europe": "concentrix",
    "message-systems-dba-sparkpost": "messagebird",
    "momentive-fka-surveymonkey": "surveymonkey",
    "oracle-china-software-system": "oracle",
    "code-42-software": "code42",
    "tdcx-digilab-india-private": "tdcx",
    "tdcx-information-consulting-shanghai": "tdcx",
    "tdcx-my-sdn-bhd": "tdcx",
    "tdcx-services-dba-tdcx-spain": "tdcx",
    "tdcx-services-dba-tdcx-portugal-unipessoal-lda": "tdcx",
    # LinkedIn names Tata Communications Ireland Ltd. Tata Communications'
    # first-party subsidiary list (tatacommunications.com) names
    # TATA COMMUNICATIONS (IRELAND) D.A.C. tata-communications is on the
    # register. Do not invent a second dossier.
    "tata-communications-ireland": "tata-communications",
    # LinkedIn names HCL America Inc. and HCL Technologies Corporate
    # Services Ltd. HCLTech first-party HTML prints HCL America Inc as a
    # wholly owned subsidiary of HCL Technologies, and hosts
    # "74 HCL Technologies Corporate Services Limited" on hcltech.com.
    # hcl-tech is on the register. Do not invent a second HCL dossier.
    "hcl-america": "hcl-tech",
    "hcl-technologies-corporate-services": "hcl-tech",
    # LinkedIn names Ypiresia 800 - Teleperformance Single Member S.A.
    # GLEIF parent is TELEPERFORMANCE SE. The existing Teleperformance
    # row is teleperformance-colombia (teleperformance.com). Do not invent
    # a second Teleperformance dossier.
    "ypiresia-800-teleperformance-single-member": "teleperformance-colombia",
    # Nylas first-party subprocessor table prints Apollo for Lead
    # Generation. apollo.io is the existing Apollo.io row.
    "apollo": "apollo-io",
    # LinkedIn names NSONE, Inc. for DNS. ns1.com now 301s to IBM's
    # first-party product page titled "IBM NS1 Connect". ibm is on the
    # register. Do not copy IBM's file onto an empty nsone shell.
    "nsone": "ibm",
    # Nylas prints Gravitational (Teleport). Official homepage
    # goteleport.com titles Teleport. Filed in this increment.
    "gravitational-teleport": "teleport",
    # LinkedIn names CRM Services India Private Limited. Teleperformance
    # first-party CSR page on tp.com prints "Teleperformance Global
    # Business Private Limited (TPGBPL) (formerly known as CRM Services
    # India Private Limited)". Ypiresia 800 already lands here. Do not
    # invent a second Teleperformance dossier.
    "crm-services-india-private": "teleperformance-colombia",
    # Plume names SamKnows LTD. samknows.com 301s to Cisco ThousandEyes
    # Connected Devices. Cisco first-party HTML titles "Cisco completes
    # SamKnows acquisition". Prior ookla target is stale — Cisco bought
    # SamKnows after Ookla. cisco is on the register. Do not copy Cisco's
    # file onto an empty samknows shell.
    "samknows": "cisco",
    # LinkedIn names EEG Enterprises, Inc for captioning. eegent.com 301s
    # to Ai-Media's first-party acquisition page titled "EEG Technologies
    # Proudly Part of AI-Media". Filed in this increment.
    "eeg-enterprises": "ai-media",
    # RingCentral names Textel. textel.net 301s to Capacity's first-party
    # SMS page titled "SMS AI Agents … Capacity" with company=textel.net.
    # Filed in this increment.
    "textel": "capacity",
    # Kentik names Deft. deft.com 301s to summithq.com, titled
    # "Summit | Cloud, Data Center, and IT Services". Summit first-party
    # legal HTML prints ServerCentral, LLC (“Summit”) for former Deft /
    # ServerCentral customers. Filed in this increment.
    "deft": "summit",
    # Twilio names Adaptive Mobile. adaptivemobile.com 301s to Enea's
    # first-party mobile-network-security page titled
    # "Mobile Network Security | Enea", which prints Adaptive Messaging
    # Firewall. Enea first-party press release: "Enea Completes
    # Acquisition of AdaptiveMobile Security". Prior csg-international
    # target is stale. Filed in this increment.
    "adaptive-mobile": "enea",
    # Fireworks names Gmi next to IREN / Era4. gmicloud.ai titles
    # "AI Cloud for Compute, Inference & Agents | GMI Cloud". Filed
    # in this increment.
    "gmi": "gmi-cloud",
    # Zapier and Nylas name MadKudu. HG Insights first-party /about
    # milestone prints "AUG – 2025 Acquires MadKudu". First-party
    # privacy HTML lists madkudu.com as a connected HG Insights
    # domain. Filed in this increment. Do not copy HG Insights' file
    # onto an empty madkudu shell.
    "madkudu": "hg-insights",
    # Dashlane names Intersections, LLC for VPN. Aura first-party
    # /about timeline prints "2018 … acquire Intersections Inc. and
    # Identity Guard" and "2019 Rebranded as Aura". Destination
    # aura-previously-pango-anchorfree is already on the register
    # (aura.com). Do not invent a second Aura dossier.
    "intersections": "aura-previously-pango-anchorfree",
    # Tropic first-party subprocessors table prints "Omni / Omni
    # Analytics, Inc. / https://omni.co/" for in-app dashboards.
    # omni-analytics is already on the register (omni.co). Prior hour
    # left the short name open because The Omni Group / others share
    # it; the destination row on that same Tropic list is now the
    # proof. Do not invent a second Omni dossier or alias to
    # the-omni-group / omnigroup.com.
    "omni": "omni-analytics",
    # Kickbox first-party subprocessors table prints "Sift Science"
    # (fraud and abuse prevention, 123 Mission St). Sift's own
    # homepage JSON-LD Organization names the company "Sift" with
    # alternateName "Sift Science", "Sift Science, Inc.", "Sift.com"
    # and url https://sift.com/. sift is already on the register
    # (sift.com). Do not invent a second Sift dossier.
    "sift-science": "sift",
    # Rootly first-party docs table prints these product / legal names.
    # Each destination is already on the register. Do not invent a
    # second dossier for Mailgun, Firebase, ClickHouse, AssemblyAI,
    # or Apple Push Notification service.
    "mailgun-sinch": "mailgun",
    "firebase-cloud-messaging": "google",
    "clickhouse-cloud": "clickhouse",
    "assemblyai-via-recall-ai": "assemblyai",
    "apple-push-notification-service": "apple",
    # Wikidata P856 for these leftover names is the existing register domain.
    # Do not invent a second dossier.
    "kaspersky": "kaspersky-lab",
    "magic-software-enterprises": "magic-software",
    "hcltech": "hcl-tech",
    "ibm-india": "ibm",
    "intuit-india": "intuit",
    "microsoft-india": "microsoft",
    "samsung-india-software-centre": "samsung-electronics",
    "qihoo-360": "360-security-technology",
    "tieto": "tietoevry",
    # P856 now the acquirer already on the register.
    "lumension-security": "ivanti",
    "moldflow": "autodesk",
    "google-security-operations": "chronicle-security",
    "nitrosecurity": "mcafee",
    "netscreen-technologies": "juniper-networks",
    "xcitium": "comodo-cybersecurity",
    "quintiq": "dassault-systemes",
    "mercury-interactive": "hp",
    "clarified-networks": "synopsys",
    "codenomicon": "synopsys",
    "netwitness": "emc-corporation",
    # Same-company leftovers after this hour's Wikipedia top-up.
    # Intel Ireland is Intel's Irish subsidiary; intel is on the register.
    "intel-ireland": "intel",
    # Hitachi Data Systems rebranded to Hitachi Vantara; hitachi is on the register.
    "hitachi-data-systems": "hitachi",
    # Samsung R&D Institute India-Bengaluru is a Samsung Electronics unit.
    "samsung-randd-institute-india-bengaluru": "samsung-electronics",
    # Short.io first-party subprocessors table prints these Google products
    # with policies.google.com privacy hrefs. google-gemini already lands
    # here. Do not invent a second Google dossier.
    "google-sign-in": "google",
    "google-ads": "google",
    "google-web-risk": "google",
    # Short.io prints Meta (WhatsApp) with whatsapp.com privacy href.
    # meta is on the register (meta.com). Do not invent a second dossier.
    "meta-whatsapp": "meta",
    "whatsapp": "meta",
    # Same-company leftovers after this hour's named-processor batch.
    # Rocketlane prints Apricity (US implementation). apricitygroup.com titles
    # "Apricity Group | Lead-to-Ledger CRM, PSA & ERP Consulting". Filed in
    # this increment.
    "apricity": "apricity-group",
    # Rocketlane prints Mako IT Lab Pvt Ltd. makoitlab.com titles
    # "Software Development Company in US - Mako IT Lab". Filed in this
    # increment.
    "mako-it-lab-pvt": "mako-it-lab",
    # Rocketlane prints SaasGenie. saasgenie.ai and saasgenie.com 301 to
    # fwddeploy.ai, titled "fwdDeploy | Post-Sale Revenue Engineering for
    # B2B Tech". First-party /about-us titles "Why saasgenie is now
    # fwdDeploy". Do not invent a second dossier.
    "saasgenie": "fwd-deploy",
    # Branch prints Software Minds, Inc (Poland engineering support).
    # softwareminds.com 301s to softwaremind.com, titled "Software
    # Engineering Company – Software Mind". Filed in this increment.
    "software-minds": "software-mind",
    # LinkedIn prints Regalix, Inc (Palo Alto campaign optimization).
    # MarketStar first-party /acquisition titles "Acquisition | Learn More
    # About Our Acquisition of Regalix". marketstar.com titles MarketStar.
    # Filed in this increment. Do not invent a second Regalix dossier.
    "regalix": "marketstar",
    # GitLab prints cc cloud GmbH. codecentric.de first-party GitLab
    # solutions page prints "cc cloud GmbH, a subsidiary of codecentric
    # AG". codecentric.de titles "codecentric AG | Creating the digital
    # future together." Filed in this increment.
    "cc-cloud": "codecentric",
    # Smartsheet prints Ujwal Inc (customer support). thelevel.ai/legal/msa
    # prints "Ujwal, Inc., a Delaware corporation doing business as Level
    # AI". thelevel.ai titles Level AI. Filed in this increment.
    "ujwal": "level-ai",
    # LinkedIn prints AI Data Innovation Corporation (Dallas data labelling).
    # aidatainnovations.com titles "Home - AI Data Innovations" and prints
    # the Dallas office. Filed in this increment.
    "ai-data-innovation": "ai-data-innovations",
    # Smartsheet prints Agile Management Experts (Germany professional
    # services). AMX first-party Delivery Hero case study prints "Agile
    # Management Experts (AMX), a Smartsheet Platinum Partner based in
    # Europe". amxconsulting.com titles AMX. Filed in this increment.
    "agile-management-experts": "amx",
    # SonicWall prints Avertech (marketing tool). averetek.com now serves
    # e2open's homepage titled "Supply Chain Software: The Connected Supply
    # Chain - e2open" (same title as e2open.com). e2open is already on the
    # register. Do not invent a second Averetek dossier.
    "avertech": "e2open",
    # Sophos prints Benjamin Mosse Consulting Pty Ltd (Australia
    # professional services). mosse-security.com titles "Mossé Security"
    # and prints ABN 89 145 033 441 on every first-party page. ABR for
    # that ABN names BENJAMIN MOSSE CONSULTING PTY. LTD. and lists the
    # business name Mosse Security (from 09 Aug 2013). Filed in this
    # increment. Do not invent a second dossier.
    "benjamin-mosse-consulting": "mosse-security",
    # Daily.co names BigQuery. google-bigquery already aliases; this is the
    # bare product id. google is on the register. Do not invent a second
    # BigQuery dossier.
    "bigquery": "google",
    # Clazar names Docker hub. docker-inc is on the register (docker.com).
    # Do not invent a second Docker Hub dossier.
    "docker-hub": "docker-inc",
    # Stream names Oracle (OCI). oracle-cloud-infrastructure already aliases
    # to oracle. oracle is on the register. Do not invent a second OCI dossier.
    "oracle-oci": "oracle",
    # Clazar names Redis Cloud. redis-labs already aliases to redis.
    # redis is on the register. Do not invent a second Redis Cloud dossier.
    "redis-cloud": "redis",
    # Front's own subprocessor list names FrontApp SARL (EU entity).
    # front is on the register (front.com). Do not invent a second Front dossier.
    "frontapp-sarl": "front",
    # Sigma prints G Suite for email. google-workspace already aliases;
    # this is the old product name. google is on the register.
    "g-suite": "google",
    # LambdaTest / TestMu prints Sales Force CRM next to SalesForce Service
    # Desk. salesforce is on the register. Do not invent a second CRM dossier.
    "sales-force-crm": "salesforce",
    # LambdaTest prints Ring Central. ringcentral is on the register.
    "ring-central": "ringcentral",
    # LambdaTest prints HashiCorp Vault. hashicorp-cloud already aliases;
    # this is the product name. hashicorp is on the register.
    "hashicorp-vault": "hashicorp",
    # LambdaTest prints Brightdata. bright-data is on the register
    # (brightdata.com). Do not invent a second Bright Data dossier.
    "brightdata": "bright-data",
    # Postmark prints Deft (formerly known as ServerCentral). deft already
    # aliases to summit (deft.com 301s to summithq.com). summit is on the
    # register. Do not invent a second Deft / ServerCentral dossier.
    "deft-formerly-known-as-servercentral": "summit",
    # Help Scout prints Pusher.io. pusher is on the register (pusher.com).
    # Do not invent a second Pusher dossier.
    "pusher-io": "pusher",
    # Shortcut prints Ketch Kloud. ketch is on the register (ketch.com).
    # Do not invent a second Ketch dossier.
    "ketch-kloud": "ketch",
    # Shortcut prints Not Just Tickets (Plain). plain is on the register
    # (plain.com). Do not invent a second Plain dossier.
    "not-just-tickets-plain": "plain",
    # Wrike prints Google (Vertex, Gemini). google-vertex-ai and
    # google-gemini already alias; this is the combined product cell.
    # google is on the register. Do not invent a second Google dossier.
    "google-vertex-gemini": "google",
    # Wrike prints Adtrib, Inc. (k/n/a/ MaestroQA). maestroqa is on the
    # register (maestroqa.com). Do not invent a second MaestroQA dossier.
    "adtrib-k-n-a-maestroqa": "maestroqa",
    # Productboard prints FoundryLabs. foundry-labs is on the register
    # (foundrylabs.com). Do not invent a second Foundry Labs dossier.
    "foundrylabs": "foundry-labs",
    # Contentsquare affiliate table prints Content Square / Hotjar / Loris
    # group entities. hotjar already aliases here. Regional leftovers land
    # on contentsquare. Do not invent a second dossier. Contentsquare's
    # own list drops these as self — aliases are for other companies.
    "content-square-sas": "contentsquare",
    "content-square": "contentsquare",
    "content-square-israel": "contentsquare",
    "content-square-singapore-pte": "contentsquare",
    "content-square-spain-s-l": "contentsquare",
    "content-square-canada": "contentsquare",
    "content-square-ltd": "contentsquare",
    "content-square-gmbh": "contentsquare",
    "hotjar-germany": "contentsquare",
    "hotjar-uk": "contentsquare",
    "hotjar-netherlands": "contentsquare",
    "hotjar-web-portugal-unipessoal-lda": "contentsquare",
    "hotjar-web-services-spain-s-l": "contentsquare",
    "loris-technologies": "contentsquare",
    # Uploadcare product / brand cells. meta / google / microsoft / qlik
    # are on the register. Talend homepage 301s to Qlik Talend.
    "facebook-for-business": "meta",
    "google-marketing-platform": "google",
    "microsoft-advertising": "microsoft",
    "talend": "qlik",
    # Accurx support article names TeamViewer UK Ltd / Intercom UK Ltd.
    # teamviewer and intercom are on the register. Do not invent a second
    # regional dossier.
    "teamviewer-uk": "teamviewer",
    "intercom-uk": "intercom",
    # Brightcove services-subprocessors table. Cloudfront is Amazon
    # CloudFront (amazon-cloudfront already aliases). Elastic Search is
    # Elasticsearch / Elastic. Google Ad Manager is Google. elastic,
    # amazon-web-services, and google are on the register. Do not invent
    # a second dossier.
    "cloudfront": "amazon-web-services",
    "elastic-search": "elastic",
    "google-ad-manager": "google",

}


# Published header garbage. Not a company. Do not file or alias.
# PR 263 review drops: SCC annex / DPA form fields, OneTrust cookie-category
# rows, and CCPA "Data Category" headings. Exact ids/names the extractor
# emitted. Do not add cloudflare / google / amazon-web-services — those
# are real orgs (Qualified's cookie table printed a Cloudflare purpose
# sentence; skip that sentence, not the Cloudflare dossier).
SKIP_PROCESSOR_IDS = {
    "entity-name",
    "n-a",
    "na",
    "it",
    "services-as-applicable",
    "talent-hire",
    "learning",
    "sales-solutions",
    "marketing-solutions",
    "customers-have-discretion-to-select-a-different-location",
    "bob-finance-module",
    "optional-features-for-the-bob-finance-module",
    "optional-features-for-the-uk-payroll-module",
    "optional-features-for-the-us-payroll-module",
    "uk-payroll-module",
    "us-payroll-module",
    # CloudAMQP DPA/ToS annex headings (not the data-center table)
    "topic",
    "processing-operations-and-purposes",
    "retention-period",
    # Arkose Labs legal-dpa — SCC annex headings
    "data-subjects",
    "special-category-personal-data-if-applicable",
    "nature-of-the-processing",
    "purposes-of-processing",
    "frequency-of-the-transfer",
    "start-date",
    "the-parties",
    "parties-details",
    "key-contact",
    "eu-sccs",
    "annex-1a-list-of-parties",
    "annex-2b-description-of-transfer",
    "uk-addendum",
    "appendix-information",
    "appropriate-safeguards",
    "approved-uk-addendum",
    "approved-eu-sccs",
    "ico",
    "ex-uk-transfer",
    "uk-data-protection-laws",
    "uk-gdpr",
    # incident.io DPA annex headings (wrong URL; real list is /legal/sub-processors)
    "details",
    "address",
    "company-number-or-equivalent",
    "role-controller-processor",
    "details-of-the-representative-in-the-european-union",
    "nature-and-description-of-processing-and-further-processing",
    "types-of-personal-data-being-processed-transferred",
    "types-of-data-subjects-whose-data-is-processed-transferred",
    "sensitive-data-processed-transferred-and-applied-restriction",
    "additional-instructions",
    # Mapbox — Data Category / CCPA table
    "data-category",
    "identifiers",
    "commercial-information",
    "internet-or-other-electronic-network-activity",
    "geolocation-data",
    # Qualified — OneTrust cookie names / CCPA categories (not org slugs)
    "qualified-session",
    "required-cookie-for-qualified-trust-site",
    "my-onetrust-groups",
    "gainsightconsent",
    "ga",
    "gd-visitor",
    "g2-com",
    "simplecast-com",
    "gcl-au",
    "doubleclick-net",
    "test-cookie",
    "pardot-com",
    "visitor-id",
    "linkedin-com",
    "lidc",
    "li-sugr",
    "cf-bm",
    "usermatchhistory",
    "bscookie",
    "analyticssynchistory",
    "ar-debug",
    "facebook-com",
    "events-distinct-id",
    "g2-session-id",
    "g2crowd-com",
    "6sc",
    "youtube-com",
    "visitor-info1-live",
    "ysc",
    "visitor-privacy-metadata",
    "stackadapt-com",
    "user-id-v2",
    "user-id-v3",
    "turn-com",
    "google-com",
    "innovid-com",
    "personal-information-pi-we-collect",
    "contact-data",
    "profile-data",
    "communications-data",
    "marketing-data",
    "online-activity-data",
    "data-derived-from-the-above",
    # Smarsh optional-feature product line (not an organization)
    "voci-medallia-vspark-cloud-optional-feature",
    # Accurx DPA annex / TOM headings (real list is the support article)
    "service-category",
    "core-services",
    "care-navigation-triage-services-and-workflow-management",
    "patient-communication-engagement-and-telephony-services",
    "consultation-documentation-and-coding-services",
    "ai-supported-processing-and-automation",
    "security-measure",
    "measures-for-user-identification-and-authorisation",
    "measures-for-the-protection-of-data-during-transmission",
    "measures-for-the-protection-of-data-during-storage",
    "measures-for-ensuring-events-logging",
    "measures-for-ensuring-system-configuration-including-default",
    "measures-for-certification-assurance-of-processes-and-produc",
    "measures-for-ensuring-data-minimisation",
    "measures-for-ensuring-data-quality",
    "measures-for-ensuring-data-retention",
    "measures-for-ensuring-accountability",
    "measures-for-allowing-data-portability-and-ensuring-erasure",
}
SKIP_PROCESSOR_NAMES = {
    "entity name",
    "n/a",
    "n.a.",
    "na",
    "it llc",
    "services (as applicable)",
    "talent/hire",
    "learning",
    "sales solutions",
    "marketing solutions",
    "customers have discretion to select a different location",
    "bob finance module",
    "optional features for the bob finance module",
    "optional features for the uk payroll module",
    "optional features for the us payroll module",
    "uk payroll module",
    "us payroll module",
    # CloudAMQP DPA/ToS annex headings
    "topic",
    "processing operations and purposes",
    "retention period",
    # Arkose Labs SCC annex headings
    "data subjects",
    "special category personal data (if applicable)",
    "nature of the processing",
    "purposes of processing",
    "frequency of the transfer",
    "start date",
    "the parties",
    "parties\u2019 details",
    "parties' details",
    "key contact",
    "eu sccs",
    "annex 1a: list of parties",
    "annex 2b: description of transfer",
    "uk addendum",
    "appendix information",
    "appropriate safeguards",
    "approved uk addendum",
    "approved eu sccs",
    "ico",
    "ex-uk transfer",
    "uk data protection laws",
    "uk gdpr",
    # incident.io DPA annex headings
    "details",
    "address",
    "company number or equivalent",
    "role (controller/processor)",
    "details of the representative in the european union",
    "nature and description of processing and further processing",
    "types of personal data being processed/transferred",
    "types of data subjects whose data is processed/transferred",
    "sensitive data processed/transferred and applied restrictions or safeguards",
    "additional instructions",
    # Mapbox Data Category table
    "data category",
    "identifiers",
    "commercial information",
    "internet or other electronic network activity",
    "geolocation data",
    # Qualified OneTrust cookie / CCPA category rows
    "qualified_session",
    "required cookie for qualified trust site",
    "this cookie is used by cloudflare for load balancing",
    "my_onetrust_groups",
    "gainsightconsent",
    "_ga",
    "_gd_visitor",
    "g2.com",
    "simplecast.com",
    "_gcl_au",
    "doubleclick.net",
    "test_cookie",
    "pardot.com",
    "visitor_id",
    "linkedin.com",
    "lidc",
    "li_sugr",
    "__cf_bm",
    "usermatchhistory",
    "bscookie",
    "analyticssynchistory",
    "ar_debug",
    "facebook.com",
    "events_distinct_id",
    "_g2_session_id",
    "g2crowd.com",
    "6sc.co",
    "youtube.com",
    "visitor_info1_live",
    "ysc",
    "visitor_privacy_metadata",
    "stackadapt.com",
    "sa-user-id-v2",
    "sa-user-id-v3",
    "sa user id v2",
    "sa user id v3",
    "turn.com",
    "google.com",
    "innovid.com",
    "personal information (\u201cpi\u201d) we collect",
    "personal information (\"pi\") we collect",
    "contact data",
    "profile data",
    "communications data",
    "marketing data",
    "online activity data",
    "data derived from the above",
    # Smarsh optional-feature product line (not an organization)
    "voci – medallia vspark cloud (optional feature)",
    "voci - medallia vspark cloud (optional feature)",
    # Accurx DPA annex / TOM headings
    "service category",
    "core services",
    "care navigation, triage services and workflow management",
    "patient communication, engagement and telephony services",
    "consultation, documentation and coding services",
    "ai-supported processing and automation",
    "security measure",
    "measures for user identification and authorisation",
    "measures for the protection of data during transmission",
    "measures for the protection of data during storage",
    "measures for ensuring events logging",
    "measures for ensuring system configuration, including default configuration",
    "measures for certification/assurance of processes and products",
    "measures for ensuring data minimisation",
    "measures for ensuring data quality",
    "measures for ensuring limited data retention",
    "measures for ensuring accountability",
    "measures for allowing data portability and ensuring erasure",
}


def register_slugs(register) -> set[str]:
    if register is None:
        return set()
    if isinstance(register, dict):
        return {str(k) for k in register if k}
    if isinstance(register, set):
        return {str(k) for k in register if k}
    out = set()
    for row in register:
        if isinstance(row, dict) and row.get("slug"):
            out.add(str(row["slug"]))
        elif isinstance(row, str) and row:
            out.add(row)
    return out


def active_aliases(register=None) -> dict[str, str]:
    """Alias map restricted to destinations that already have a register row."""
    slugs = register_slugs(register)
    return {src: dest for src, dest in REGISTER_ALIASES.items() if dest in slugs}


def canonical_processor_id(pid: str, register=None) -> str:
    """Return the register slug when this wire id is a known alias."""
    nid = str(pid or "").strip()
    if not nid:
        return nid
    dest = REGISTER_ALIASES.get(nid, nid)
    slugs = register_slugs(register)
    if dest in slugs:
        return dest
    if nid in slugs:
        return nid
    return nid


def skip_processor(nid: str = "", name: str = "") -> bool:
    if str(nid or "").strip().lower() in SKIP_PROCESSOR_IDS:
        return True
    if str(name or "").strip().lower() in SKIP_PROCESSOR_NAMES:
        return True
    return False


def apply_aliases_to_graph(subs: dict, register=None) -> dict:
    """Rewrite edges/nodes onto existing register slugs. Merge duplicate wires."""
    if not isinstance(subs, dict):
        return subs
    slugs = register_slugs(register)
    aliases = active_aliases(slugs)
    nodes = {n["id"]: dict(n) for n in (subs.get("nodes") or []) if n.get("id")}
    by_row = {}
    if isinstance(register, dict):
        by_row = register
    else:
        for row in register or []:
            if isinstance(row, dict) and row.get("slug"):
                by_row[row["slug"]] = row

    new_edges = []
    seen = set()
    for e in subs.get("edges") or []:
        frm = e.get("from") or e.get("company")
        to = e.get("to") or e.get("processor_slug") or e.get("processor")
        src = e.get("source_url")
        if not frm or not to or not src:
            continue
        dest = to if (src, to) in UNALIASED_WIRES else aliases.get(to, to)
        if skip_processor(dest, e.get("evidence") or ""):
            continue
        # Same dest can still carry two published names (Google Gemini and
        # Google Cloud Platform both land on google). Do not drop a sourced name.
        evidence = (e.get("evidence") or "").strip()
        key = (frm, dest, src, evidence)
        if key in seen:
            continue
        seen.add(key)
        edge = dict(e)
        edge["from"] = frm
        edge["to"] = dest
        new_edges.append(edge)

        if dest not in nodes:
            row = by_row.get(dest) or {}
            if dest in slugs:
                nodes[dest] = {
                    "id": dest,
                    "name": row.get("name") or dest,
                    "domain": row.get("domain") or "",
                    "kind": "company",
                    "in_register": True,
                }
            else:
                old = nodes.get(to) or {}
                nodes[dest] = {
                    "id": dest,
                    "name": old.get("name") or edge.get("evidence") or dest,
                    "domain": old.get("domain") or "",
                    "kind": old.get("kind") or "processor",
                    "in_register": dest in slugs,
                }

    live_dests = {e.get("to") for e in new_edges}
    for src, dest in aliases.items():
        if src != dest and src not in live_dests:
            nodes.pop(src, None)
        row = by_row.get(dest) or {}
        if dest in slugs:
            node = nodes.get(dest) or {
                "id": dest,
                "name": row.get("name") or dest,
                "domain": row.get("domain") or "",
                "kind": "company",
                "in_register": True,
            }
            node["id"] = dest
            node["name"] = row.get("name") or node.get("name") or dest
            if row.get("domain"):
                node["domain"] = row["domain"]
            node["kind"] = "company"
            node["in_register"] = True
            nodes[dest] = node

    for slug, row in by_row.items():
        if slug not in nodes:
            continue
        node = nodes[slug]
        node["in_register"] = True
        node["kind"] = "company"
        if row.get("name"):
            node["name"] = row["name"]
        if row.get("domain"):
            node["domain"] = row["domain"]

    live = {e.get("from") for e in new_edges} | {e.get("to") for e in new_edges}
    if slugs:
        for slug in slugs:
            if slug in nodes:
                continue
            # Keep register companies that already sat on the map; do not
            # dump the whole register onto the wire list.
            pass
    # Drop alias leftovers that no edge names. An unaliased wire (LiveKit
    # SpaceXAI) still occupies its leftover node.
    kept = []
    for nid, node in nodes.items():
        if nid in aliases and aliases[nid] != nid and nid not in live:
            continue
        if nid in live or node.get("in_register"):
            kept.append(node)

    subs["nodes"] = kept
    subs["edges"] = new_edges
    subs["aliases"] = aliases
    return subs


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(__import__("json").dumps(obj, indent=2) + "\n", encoding="utf-8")
