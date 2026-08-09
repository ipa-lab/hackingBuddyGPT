"""Central home for target-specific quirks used by the web_api use-cases.

The documentation and testing agents special-case a handful of concrete
benchmark targets (CoinGecko/GBIF-style name ids, OpenBreweryDB, coincap, vAPI,
crapi, ballardtide, the OWASP API benchmark). Those checks and constant lists
used to be inlined and copy-pasted across several modules. They are collected
here so there is one place to read and change them. Behaviour is unchanged: each
predicate mirrors the exact string check it replaced.
"""
from typing import Dict, List, Optional

# Cryptocurrency names that appear as resource ids in the crypto benchmark APIs.
CRYPTO_NAMES: List[str] = [
    "bitcoin", "ethereum", "litecoin", "dogecoin",
    "cardano", "solana", "binance", "polkadot", "tezos",
]


def has_named_resource_ids(name: str) -> bool:
    """Targets whose instance ids are names rather than numbers (CoinGecko, GBIF)."""
    return "Coin" in name or "gbif" in name


def has_brew_style_ids(name: str) -> bool:
    """Targets that use search/autocomplete-style sub-resources (OpenBreweryDB, GBIF)."""
    return "brew" in name or "gbif" in name


def is_coincap(host: str) -> bool:
    """The coincap.io target (matched against the host)."""
    return "coincap" in host


def is_ballardtide(name: str) -> bool:
    """The ballardtide target, which expects a bare (non-Bearer) auth token."""
    return "ballardtide" in name


def is_owasp_api(name: str) -> bool:
    """The OWASP API benchmark, whose paths are capitalized."""
    return "OWASP API" in name


def auth_header_for(name: Optional[str], token: str) -> Dict[str, str]:
    """Return the Authorization header dict a given target expects for ``token``."""
    if name == "vAPI":
        return {"Authorization-Token": f"{token}"}
    if name == "crapi":
        return {"Authorization": f"Bearer {token}"}
    return {"Authorization-Token": f"Bearer {token}"}
