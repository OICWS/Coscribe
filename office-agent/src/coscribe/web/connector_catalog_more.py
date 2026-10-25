"""More Discover entries, kept apart so `connector_catalog.py` stays under its size
limit. Each was checked against its live server on 2026-10-25: Exa answered a
real search without a sign-in; the others registered a client for a loopback sign-in
address. Their tool lists are left out because the servers list tools only after
sign-in; the connected connector reports them."""

from __future__ import annotations

from typing import Any


def _signin(
    name: str, title: str, site: str, category: str, description: str, about: str, url: str
) -> dict[str, Any]:
    return {
        "name": name,
        "title": title,
        "made_by": title,
        "homepage": site,
        "category": category,
        "description": description,
        "about": f"{about} coscribe sees only what the {title} account you sign in with can see.",
        "links": [{"label": "Website", "url": site}],
        "server_url": url,
        "auth": "oauth",
    }


EXTRA_CONNECTORS: list[dict[str, Any]] = [
    {
        "name": "exa",
        "title": "Exa",
        "made_by": "Exa",
        "homepage": "https://docs.exa.ai/reference/exa-mcp",
        "category": "Web search",
        "description": "Search the web and read pages with Exa.",
        "about": "Searches the live web and fetches the text of a page, for research, "
        "competitor and market questions. No sign-in; the free tier is rate-limited.",
        "tools": ["web_search_exa", "web_fetch_exa"],
        "links": [
            {"label": "Documentation", "url": "https://docs.exa.ai/reference/exa-mcp"},
            {"label": "Privacy policy", "url": "https://exa.ai/privacy-policy"},
        ],
        "server_url": "https://mcp.exa.ai/mcp",
    },
    _signin(
        "attio", "Attio", "https://attio.com", "Sales",
        "Search and update your Attio CRM.",
        "Look up companies, people and deals, and add notes and tasks in Attio.",
        "https://mcp.attio.com/mcp",
    ),
    _signin(
        "ramp", "Ramp", "https://ramp.com", "Finance",
        "Check spend, cards and expenses in Ramp.",
        "Ask about transactions, reimbursements, cards and budgets in Ramp.",
        "https://mcp.ramp.com/mcp",
    ),
    _signin(
        "tldv", "tl;dv", "https://tldv.io", "Meetings",
        "Search and read your tl;dv meeting recordings.",
        "Search meeting transcripts, summaries and highlights recorded by tl;dv.",
        "https://mcp.tldv.io/mcp",
    ),
    _signin(
        "similarweb", "Similarweb", "https://www.similarweb.com", "Analytics",
        "Research web traffic and competitors with Similarweb.",
        "Compare website traffic, audience and market trends for competitor and market research.",
        "https://mcp.similarweb.com/mcp",
    ),
]  # fmt: skip
