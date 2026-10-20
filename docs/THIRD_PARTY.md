# Third-Party Components

Versions are constrained in `requirements.txt`; installed transitive versions should be captured in the final submission environment.

| Component | Purpose | License |
|---|---|---|
| Python | Runtime | PSF License |
| Pydantic | Typed validation | MIT |
| PyYAML | YAML scenario/evaluation files | MIT |
| Streamlit | Demo UI | Apache-2.0 |
| Requests | Frankfurter and Wise HTTP client | Apache-2.0 |
| openpyxl | Offline World Bank snapshot builder only | MIT |
| Anthropic Python SDK | Optional swappable LLM adapter | MIT |
| pytest | Test runner | MIT |
| pytest-cov / coverage.py | Coverage reporting | MIT / Apache-2.0 |

## Public datasets

| Dataset | Use | Source |
|---|---|---|
| UNESCO UIS indicator 26637, February 2026 release | Reproducible top-50 study-destination catalog | https://api.uis.unesco.org/api/public/data/indicators?indicator=26637&geoUnitType=NATIONAL |
| Frankfurter public API v2 | Live reference FX and bundled offline snapshot | https://frankfurter.dev/ |
| World Bank Remittance Prices Worldwide, 2025 Q3 | Historical corridor cost benchmarks; CC BY 4.0 | https://datacatalog.worldbank.org/search/dataset/0037898/remittance-prices-worldwide |
| UN Security Council Consolidated List | Dated preliminary name-screening snapshot | https://main.un.org/securitycouncil/en/content/un-sc-consolidated-list |
| Wise quote API | Live unauthenticated provider estimates; not executable or rate-locked | https://docs.wise.com/guides/product/send-money/quotes |

The application source is MIT licensed. Provider names, terms, beneficiaries and receipts in the separate Safe execution demo are fictional.

