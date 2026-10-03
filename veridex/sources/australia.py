from datetime import datetime, timezone

from .base import HtmlIndexAdapter, SourceSpec


def source_specs() -> list[SourceSpec]:
    year = datetime.now(timezone.utc).year
    return [
        SourceSpec(
            key="au-austrac-guidance",
            name="AUSTRAC latest guidance updates",
            jurisdiction="AU",
            regulator="AUSTRAC",
            index_url="https://www.austrac.gov.au/industry-and-business/obligations-and-guidance/latest-guidance-updates",
            include_keywords=("guidance", "obligation", "designated", "aml", "ctf", "report", "program", "customer", "risk"),
        ),
        SourceSpec(
            key="au-austrac-news",
            name="AUSTRAC news and regulatory updates",
            jurisdiction="AU",
            regulator="AUSTRAC",
            index_url="https://www.austrac.gov.au/news-and-media/news-and-media-releases",
            include_keywords=("news-and-media", "reform", "compliance", "enforcement", "obligation", "report", "aml", "ctf"),
        ),
        SourceSpec(
            key="au-apra-publications",
            name="APRA news and publications",
            jurisdiction="AU",
            regulator="APRA",
            index_url="https://www.apra.gov.au/news-and-publications",
            include_keywords=("prudential", "standard", "consult", "response", "amend", "report", "letter", "bank", "risk", "governance", "capital", "liquidity"),
        ),
        SourceSpec(
            key="au-apra-standards",
            name="APRA prudential and reporting standards",
            jurisdiction="AU",
            regulator="APRA",
            index_url="https://www.apra.gov.au/cross-industry/prudential-and-reporting-standards",
            include_keywords=("cps", "aps", "standard", "practice-guide", "prudential", "reporting"),
        ),
        SourceSpec(
            key="au-asic-regulatory-tracker",
            name=f"ASIC regulatory tracker {year}",
            jurisdiction="AU",
            regulator="ASIC",
            index_url=f"https://www.asic.gov.au/regulatory-resources/find-a-document/regulatory-document-updates/regulatory-tracker/regulatory-tracker-{year}",
            include_keywords=("regulatory", "instrument", "guide", "consult", "report", "information", "financial", "corporations", "asic"),
        ),
    ]


def adapters() -> list[HtmlIndexAdapter]:
    return [HtmlIndexAdapter(spec) for spec in source_specs()]
