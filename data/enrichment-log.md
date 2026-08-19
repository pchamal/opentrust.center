# Enrichment log

Generated: 2026-08-19T04:49:11Z UTC (21:49 PT / America/Los_Angeles).

## Coverage

| Fact | Count |
|---|---|
| Companies in register | 183 |
| Portals on file (trust or security page) | 174 |
| Founding years verified | 146 |
| Years skipped (no verified Wikipedia/Wikidata source) | 37 |
| Companies with ≥1 cert seen in public HTML | 74 |
| Cert mentions (total) | 404 |
| Subprocessor edges | 82 |
| security.txt | 90 |
| DPA link | 56 |
| Privacy link | 149 |
| Status link | 120 |
| Bug bounty / disclosure link | 75 |
| Subprocessors link | 98 |

Well-known paths were GET-probed for all 183 domains. Hits are HTTP 200 that are not a soft 404, parked page, login wall, or homepage bounce.

## Disclosure tiers

| Tier | Count |
|---|---|
| silent | 9 |
| thin | 31 |
| on-file | 97 |
| substantial | 36 |
| complete | 10 |

Score (cap 100): +20 portal, cert weights cap 40, +8 DPA, +8 subprocessors link, +6 status, +6 bounty or security.txt, +6 privacy, +min(10, floor((2026−year)/2)). Silent = no public trust or security page on file.

## Method

1. Founding years: Wikipedia title resolve → Wikidata P571, kept when the official website matches the register domain or the title/label is an unambiguous close match. A few additional years come from an explicit “founded/established/launched YYYY” sentence on the matching Wikipedia lead. Each year has a source URL. Ambiguous names were omitted.
2. Path probe (parallel, 8s timeout): `/.well-known/security.txt`, `/security`, `/trust`, `/privacy`, `/legal/privacy`, `/legal/subprocessors`, `/subprocessors`, `/legal/dpa`, `/dpa`, `status.{domain}`, plus the existing `trust_url`.
3. Certs extracted from live trust/security HTML only. JS-only or login-gated portals often yield no tokens; empty `certs` means not seen, not “uncertified.”
4. Subprocessor edges only from a first-party public list that returned 200. Names normalized to a known catalog. Login-gated lists are not on file.
5. Summaries are clerk voice. SafeBase / Vanta / Conveyor / Wolfia / Drata / SecurityPal are not written into public summaries.

## What this is not

A complete crawl of every live page. A claim that a missing fact does not exist. A vendor catalog.

## Top cert mentions

| Certification | Companies |
|---|---|
| GDPR | 51 |
| SOC 2 Type II | 42 |
| ISO 27001 | 37 |
| HIPAA | 32 |
| CCPA | 28 |
| FedRAMP | 18 |
| SOC 3 | 17 |
| PCI DSS | 16 |
| SOC 2 | 14 |
| TX-RAMP | 14 |
| ISO 27701 | 13 |
| SOC 1 | 12 |
| TISAX | 12 |
| ISO 27017 | 11 |
| ISO 42001 | 11 |
| ISO 27018 | 10 |
| CSA STAR | 9 |
| ISMAP | 9 |
| C5 | 8 |
| HITRUST | 6 |

## Top subprocessors (public lists only)

| Processor id | Edges |
|---|---|
| github | 14 |
| aws | 11 |
| sentry | 6 |
| azure | 5 |
| slack | 4 |
| salesforce | 4 |
| zendesk | 4 |
| gcp | 4 |
| newrelic | 3 |
| splunk | 3 |
| zoom | 3 |
| snowflake | 3 |
| hubspot | 2 |
| datadog | 2 |
| intercom | 2 |

## Founding years

| Company | Year | Source |
|---|---|---|
| OpenAI | 2015 | https://en.wikipedia.org/wiki/OpenAI |
| Anthropic | 2021 | https://en.wikipedia.org/wiki/Anthropic |
| Stripe | 2010 | https://en.wikipedia.org/wiki/Stripe,_Inc. |
| Databricks | 2013 | https://en.wikipedia.org/wiki/Databricks |
| Canva | 2013 | https://en.wikipedia.org/wiki/Canva |
| Ramp | 2019 | https://en.wikipedia.org/wiki/Ramp_(company) |
| Navan | 2015 | https://en.wikipedia.org/wiki/Navan,_Inc. |
| Anysphere | 2022 | https://en.wikipedia.org/wiki/Cursor_(company) |
| Deel | 2019 | https://en.wikipedia.org/wiki/Deel,_Inc. |
| Notion | 2016 | https://en.wikipedia.org/wiki/Notion_(productivity_software) |
| Grammarly | 2009 | https://en.wikipedia.org/wiki/Grammarly |
| Celonis | 2011 | https://en.wikipedia.org/wiki/Celonis |
| Netskope | 2012 | https://en.wikipedia.org/wiki/Netskope |
| Gusto | 2011 | https://en.wikipedia.org/wiki/Gusto,_Inc. |
| Rippling | 2017 | https://en.wikipedia.org/wiki/Rippling_(company) |
| Tanium | 2007 | https://en.wikipedia.org/wiki/Tanium |
| Miro | 2011 | https://en.wikipedia.org/wiki/Miro_(collaboration_platform) |
| Attentive | 2016 | https://en.wikipedia.org/wiki/Attentive_(company) |
| Cohesity | 2013 | https://en.wikipedia.org/wiki/Cohesity |
| Arctic Wolf | 2012 | https://en.wikipedia.org/wiki/Arctic_Wolf_Networks |
| Flock Safety | 2017 | https://en.wikipedia.org/wiki/Flock_Safety |
| VAST Data | 2015 | https://en.wikipedia.org/wiki/VAST_Data |
| Perplexity AI | 2022 | https://en.wikipedia.org/wiki/Perplexity_AI |
| OneTrust | 2016 | https://en.wikipedia.org/wiki/OneTrust |
| Plaid | 2013 | https://en.wikipedia.org/wiki/Plaid_Inc. |
| Carta | 2012 | https://en.wikipedia.org/wiki/Carta_(software_company) |
| Postman | 2013 | https://en.wikipedia.org/wiki/Postman,_Inc. |
| Zoho | 1996 | https://en.wikipedia.org/wiki/Zoho_Corporation |
| Airtable | 2012 | https://en.wikipedia.org/wiki/Airtable |
| Dataiku | 2013 | https://en.wikipedia.org/wiki/Dataiku |
| Cribl | 2018 | https://en.wikipedia.org/wiki/Cribl.io |
| 1Password | 2006 | https://en.wikipedia.org/wiki/1Password |
| Checkout.com | 2009 | https://en.wikipedia.org/wiki/Checkout.com |
| Automation Anywhere | 2003 | https://en.wikipedia.org/wiki/Automation_Anywhere |
| Motive | 2013 | https://en.wikipedia.org/wiki/Motive_(company) |
| Vercel | 2015 | https://en.wikipedia.org/wiki/Vercel |
| Glean | 2019 | https://en.wikipedia.org/wiki/Glean_Technologies |
| Airwallex | 2015 | https://en.wikipedia.org/wiki/Airwallex |
| Clio | 2008 | https://en.wikipedia.org/wiki/Clio_(software_company) |
| Zapier | 2012 | https://en.wikipedia.org/wiki/Zapier |
| Brex | 2017 | https://en.wikipedia.org/wiki/Brex |
| Snyk | 2015 | https://en.wikipedia.org/wiki/Snyk |
| Intercom | 2011 | https://en.wikipedia.org/wiki/Intercom_(company) |
| Guild | 2015 | https://en.wikipedia.org/wiki/Guild_Education |
| HiBob | 2015 | https://en.wikipedia.org/wiki/HiBob |
| AppsFlyer | 2011 | https://en.wikipedia.org/wiki/AppsFlyer |
| Calendly | 2013 | https://en.wikipedia.org/wiki/Calendly |
| Workato | 2013 | https://en.wikipedia.org/wiki/Workato |
| Forter | 2013 | https://en.wikipedia.org/wiki/Forter |
| BrowserStack | 2011 | https://en.wikipedia.org/wiki/BrowserStack |
| Midjourney | 2022 | https://en.wikipedia.org/wiki/Midjourney |
| Personio | 2015 | https://en.wikipedia.org/wiki/Personio |
| ClickUp | 2016 | https://en.wikipedia.org/wiki/ClickUp |
| Automattic | 2005 | https://en.wikipedia.org/wiki/Automattic |
| ClickHouse | 2016 | https://en.wikipedia.org/wiki/ClickHouse |
| Algolia | 2012 | https://en.wikipedia.org/wiki/Algolia |
| DeepL | 2017 | https://en.wikipedia.org/wiki/DeepL_Translator |
| Hugging Face | 2016 | https://en.wikipedia.org/wiki/Hugging_Face |
| ElevenLabs | 2022 | https://en.wikipedia.org/wiki/ElevenLabs |
| Cato Networks | 2015 | https://en.wikipedia.org/wiki/Cato_Networks |
| Cyera | 2020 | https://en.wikipedia.org/wiki/Cyera |
| Runway | 2018 | https://en.wikipedia.org/wiki/Runway_(company) |
| Odoo | 2004 | https://en.wikipedia.org/wiki/Odoo |
| Papaya Global | 2016 | https://en.wikipedia.org/wiki/Papaya_Global |
| Synthesia | 2017 | https://en.wikipedia.org/wiki/Synthesia_(company) |
| Adobe | 1982 | https://en.wikipedia.org/wiki/Adobe_Inc. |
| Adyen | 2006 | https://en.wikipedia.org/wiki/Adyen |
| Akamai | 1998 | https://en.wikipedia.org/wiki/Akamai_Technologies |
| Amazon Web Services | 2006 | https://en.wikipedia.org/wiki/Amazon_Web_Services |
| Amplitude | 2014 | https://en.wikipedia.org/wiki/Amplitude,_Inc. |
| Apple | 1976 | https://en.wikipedia.org/wiki/Apple_Inc. |
| Asana | 2008 | https://en.wikipedia.org/wiki/Asana,_Inc. |
| Atlassian | 2002 | https://en.wikipedia.org/wiki/Atlassian |
| Autodesk | 1982 | https://en.wikipedia.org/wiki/Autodesk |
| Bill.com | 2006 | https://en.wikipedia.org/wiki/Bill.com |
| Block | 2009 | https://en.wikipedia.org/wiki/Block,_Inc. |
| Box | 2009 | https://en.wikipedia.org/wiki/Box,_Inc. |
| Braze | 2011 | https://en.wikipedia.org/wiki/Braze,_Inc. |
| Character.AI | 2022 | https://en.wikipedia.org/wiki/Character.ai |
| Check Point | 1993 | https://en.wikipedia.org/wiki/Check_Point |
| Cisco | 1984 | https://en.wikipedia.org/wiki/Cisco |
| Cloudflare | 2009 | https://en.wikipedia.org/wiki/Cloudflare |
| Cohere | 2019 | https://en.wikipedia.org/wiki/Cohere |
| Confluent | 2014 | https://en.wikipedia.org/wiki/Confluent |
| CoreWeave | 2017 | https://en.wikipedia.org/wiki/CoreWeave |
| Coupa | 2006 | https://en.wikipedia.org/wiki/Coupa |
| CrowdStrike | 2011 | https://en.wikipedia.org/wiki/CrowdStrike |
| CyberArk | 1999 | https://en.wikipedia.org/wiki/CyberArk |
| Datadog | 2010 | https://en.wikipedia.org/wiki/Datadog |
| DigitalOcean | 2011 | https://en.wikipedia.org/wiki/DigitalOcean |
| DocuSign | 2003 | https://en.wikipedia.org/wiki/Docusign |
| Dropbox | 2007 | https://en.wikipedia.org/wiki/Dropbox |
| Dynatrace | 2005 | https://en.wikipedia.org/wiki/Dynatrace |
| Elastic | 2012 | https://en.wikipedia.org/wiki/Elastic_NV |
| Fastly | 2011 | https://en.wikipedia.org/wiki/Fastly |
| Figma | 2012 | https://en.wikipedia.org/wiki/Figma |
| Fortinet | 2000 | https://en.wikipedia.org/wiki/Fortinet |
| Freshworks | 2010 | https://en.wikipedia.org/wiki/Freshworks |
| GitHub | 2007 | https://en.wikipedia.org/wiki/GitHub |
| GitLab | 2011 | https://en.wikipedia.org/wiki/GitLab |
| Google | 1998 | https://en.wikipedia.org/wiki/Google |
| Groq | 2016 | https://en.wikipedia.org/wiki/Groq |
| HashiCorp | 2012 | https://en.wikipedia.org/wiki/HashiCorp |
| HubSpot | 2006 | https://en.wikipedia.org/wiki/HubSpot |
| IBM | 1911 | https://en.wikipedia.org/wiki/IBM |
| Intuit | 1983 | https://en.wikipedia.org/wiki/Intuit |
| Klaviyo | 2012 | https://en.wikipedia.org/wiki/Klaviyo |
| Meta | 2004 | https://en.wikipedia.org/wiki/Meta_Platforms |
| Microsoft | 1975 | https://en.wikipedia.org/wiki/Microsoft |
| Mistral AI | 2023 | https://en.wikipedia.org/wiki/Mistral_AI |
| Mixpanel | 2009 | https://en.wikipedia.org/wiki/Mixpanel |
| monday.com | 2012 | https://en.wikipedia.org/wiki/Monday.com |
| MongoDB | 2007 | https://en.wikipedia.org/wiki/MongoDB_Inc. |
| Netlify | 2014 | https://en.wikipedia.org/wiki/Netlify |
| New Relic | 2008 | https://en.wikipedia.org/wiki/New_Relic |
| NVIDIA | 1993 | https://en.wikipedia.org/wiki/Nvidia |
| Okta | 2009 | https://en.wikipedia.org/wiki/Okta,_Inc. |
| Oracle | 1977 | https://en.wikipedia.org/wiki/Oracle_Corporation |
| PagerDuty | 2009 | https://en.wikipedia.org/wiki/PagerDuty |
| Palantir | 2003 | https://en.wikipedia.org/wiki/Palantir |
| Palo Alto Networks | 2005 | https://en.wikipedia.org/wiki/Palo_Alto_Networks |
| PayPal | 1998 | https://en.wikipedia.org/wiki/PayPal |
| Proofpoint | 2002 | https://en.wikipedia.org/wiki/Proofpoint |
| Qualys | 1999 | https://en.wikipedia.org/wiki/Qualys |
| Rapid7 | 2000 | https://en.wikipedia.org/wiki/Rapid7,_Inc. |
| Salesforce | 1999 | https://en.wikipedia.org/wiki/Salesforce |
| Samsara | 2015 | https://en.wikipedia.org/wiki/Samsara_(company) |
| SAP | 1972 | https://en.wikipedia.org/wiki/SAP |
| Scale AI | 2016 | https://en.wikipedia.org/wiki/Scale_AI |
| SentinelOne | 2013 | https://en.wikipedia.org/wiki/SentinelOne |
| ServiceNow | 2004 | https://en.wikipedia.org/wiki/ServiceNow |
| Shopify | 2006 | https://en.wikipedia.org/wiki/Shopify |
| Slack | 2013 | https://en.wikipedia.org/wiki/Slack_(software) |
| Smartsheet | 2006 | https://en.wikipedia.org/wiki/Smartsheet |
| Snowflake | 2012 | https://en.wikipedia.org/wiki/Snowflake_Inc. |
| Splunk | 2004 | https://en.wikipedia.org/wiki/Splunk |
| Stability AI | 2019 | https://en.wikipedia.org/wiki/Stability_AI |
| Tenable | 2002 | https://en.wikipedia.org/wiki/Tenable,_Inc. |
| Twilio | 2008 | https://en.wikipedia.org/wiki/Twilio |
| UiPath | 2005 | https://en.wikipedia.org/wiki/UiPath |
| Unity | 2004 | https://en.wikipedia.org/wiki/Unity_Technologies |
| Workday | 2005 | https://en.wikipedia.org/wiki/Workday,_Inc. |
| xAI | 2023 | https://en.wikipedia.org/wiki/SpaceXAI |
| Zendesk | 2007 | https://en.wikipedia.org/wiki/Zendesk |
| Zoom | 2011 | https://en.wikipedia.org/wiki/Zoom_Communications |
| Zscaler | 2008 | https://en.wikipedia.org/wiki/Zscaler |

## Years skipped (no verified source)

grafana-labs, abnormal-ai, alphasense, checkr, talkdesk, fivetran, dialpad, ninjaone, lambda, gong, collibra, abridge, komodo-health, pendo, vanta, webflow, benchling, axonius, harness, island, maintainx, fireworks-ai, together-ai, dbt-labs, fal-ai, mercor, launchdarkly, harvey, sierra, brightwheel, glossgenius, claroty, chainguard, clay, evenup, sailpoint, writer

## Outputs

- `data/enriched.json`
- `data/subprocessors.json`
- `scripts/enrich.py` (repeatable; HTTP cache under `data/cache/http/`)
