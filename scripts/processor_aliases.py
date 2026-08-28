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
    "google-ireland": "google",
    "google-firebase": "google",
    "google-vertex-ai": "google",
    "google-resources": "google",
    "google-analytics-optional-sub-processor": "google",
    "google-firebase-google-analytics-google-gemini": "google",
    # Microsoft products / regional entities.
    "microsoft-clarity": "microsoft",
    "microsoft-ireland-operations": "microsoft",
    "microsoft-365-copilot": "microsoft",
    "microsoft-office": "microsoft",
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
    "perimeter81": "perimeter-81",
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
    "shopkeep-com": "shopkeep",
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
    # Databricks acquired Neon. databricks is on the register.
    "neon": "databricks",
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
}

# Published header garbage. Not a company. Do not file or alias.
SKIP_PROCESSOR_IDS = {
    "entity-name",
    "n-a",
    "na",
    "it",
    "customers-have-discretion-to-select-a-different-location",
    "bob-finance-module",
    "optional-features-for-the-bob-finance-module",
    "optional-features-for-the-uk-payroll-module",
    "optional-features-for-the-us-payroll-module",
    "uk-payroll-module",
    "us-payroll-module",
}
SKIP_PROCESSOR_NAMES = {
    "entity name",
    "n/a",
    "n.a.",
    "na",
    "it llc",
    "customers have discretion to select a different location",
    "bob finance module",
    "optional features for the bob finance module",
    "optional features for the uk payroll module",
    "optional features for the us payroll module",
    "uk payroll module",
    "us payroll module",
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
        dest = aliases.get(to, to)
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

    for src, dest in aliases.items():
        if src != dest:
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
    # Drop alias leftovers that no edge names.
    kept = []
    for nid, node in nodes.items():
        if nid in aliases and aliases[nid] != nid:
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
