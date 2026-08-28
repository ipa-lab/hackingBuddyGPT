"""
Normalised "target surface" model shared by the web-API detection and testing phases.

A *target surface* is whatever describes the reachable request surface of a target:

* a REST API described by an OpenAPI specification, or
* a plain website described by a sitemap (``sitemap.xml``, a newline URL list, or crawled
  HTML with links and forms).

Both are normalised onto a single in-memory OpenAPI ``api_data`` document so that the
existing :class:`OpenAPISpecificationParser` machinery (endpoint listing, schema lookup,
security classification, structural categorisation) works unchanged for either input.
Consumers (``PenTestingInformation``, the prompt engine, the testing phase) depend only on
the :class:`TargetSurface` interface below, never on how the surface was obtained.

Explicit converters live here as ``*_to_openapi`` functions; the two concrete surface
classes are thin subclasses of the parser that differ only in their loader and in the
``is_sitemap`` flag consumers can use to warn about degraded (schema-less) coverage.
"""

from __future__ import annotations

import json
import os
import re
from html import unescape
from typing import Dict, List, Protocol, Union, runtime_checkable
from urllib.parse import parse_qs, urljoin, urlparse

import yaml

from hackingBuddyGPT.utils.openapi.openapi_parser import OpenAPISpecificationParser


@runtime_checkable
class TargetSurface(Protocol):
    """Read-only interface the detection and testing phases consume.

    :class:`OpenAPISpecificationParser` (and therefore both concrete surfaces below) already
    satisfies this structurally; it exists so consumers can be typed against the capability
    rather than the concrete OpenAPI parser.
    """

    api_data: Dict[str, Union[Dict, List]]

    def get_endpoints(self) -> Dict[str, Dict[str, Dict]]: ...

    def get_schemas(self) -> Dict[str, Dict]: ...

    def get_schema_for_endpoint(self, path: str, method: str): ...

    def classify_endpoints(self, name: str = "") -> Dict[str, List]: ...

    def categorize_endpoints(self, endpoints, query: dict) -> Dict[str, List]: ...


# --------------------------------------------------------------------------------------
# converters: anything -> an in-memory OpenAPI ``api_data`` document
# --------------------------------------------------------------------------------------

def _empty_openapi(host: str = "", title: str = "Imported surface", description: str = "") -> dict:
    return {
        "openapi": "3.0.0",
        "info": {"title": title, "version": "1.0", "description": description},
        "servers": [{"url": host}] if host else [],
        "paths": {},
        "components": {"schemas": {}},
    }


def _add_param(operation: dict, name: str, location: str, required: bool = False) -> None:
    params = operation.setdefault("parameters", [])
    if not any(p.get("name") == name and p.get("in") == location for p in params):
        params.append({"name": name, "in": location, "required": required, "schema": {"type": "string"}})


def _same_host(url_netloc: str, base_netloc: str) -> bool:
    return not base_netloc or not url_netloc or url_netloc == base_netloc


def _resolve_path(href: str, base_url: str) -> str | None:
    """Resolve an href/action to a same-host path, or ``None`` if it should be skipped."""
    if not href or href.startswith(("#", "mailto:", "javascript:", "tel:", "data:")):
        return None
    parsed = urlparse(urljoin(base_url, href))
    if base_url and not _same_host(parsed.netloc, urlparse(base_url).netloc):
        return None
    return parsed.path or "/"


def urls_to_openapi(urls, host: str = "", description: str = "") -> dict:
    """Convert a list of URLs into a synthetic OpenAPI document (all ``GET``)."""
    spec = _empty_openapi(host, title="Sitemap surface", description=description)
    paths = spec["paths"]
    for url in urls:
        parsed = urlparse(url)
        if host and not _same_host(parsed.netloc, urlparse(host).netloc):
            continue
        path = parsed.path or "/"
        operation = paths.setdefault(path, {}).setdefault("get", {"responses": {}})
        for name in parse_qs(parsed.query):
            _add_param(operation, name, "query")
    return spec


def html_to_openapi(html: str, base_url: str = "", host: str = "", description: str = "") -> dict:
    """Convert an HTML page into a synthetic OpenAPI document from its links and forms."""
    from bs4 import BeautifulSoup

    base = base_url or host
    spec = _empty_openapi(host or base, title="Sitemap surface", description=description)
    paths = spec["paths"]
    soup = BeautifulSoup(html, "html.parser")

    for anchor in soup.find_all("a", href=True):
        path = _resolve_path(anchor["href"], base)
        if path is not None:
            paths.setdefault(path, {}).setdefault("get", {"responses": {}})

    for form in soup.find_all("form"):
        method = (form.get("method") or "get").strip().lower()
        if method not in ("get", "post", "put", "delete", "patch"):
            method = "get"
        path = _resolve_path(form.get("action") or base, base)
        if path is None:
            continue
        operation = paths.setdefault(path, {}).setdefault(method, {"responses": {}})
        location = "query" if method == "get" else "formData"
        for field in form.find_all(["input", "textarea", "select"]):
            name = field.get("name")
            if name:
                _add_param(operation, name, location, required=field.has_attr("required"))
    return spec


_LOC_RE = re.compile(r"<loc>\s*(.*?)\s*</loc>", re.IGNORECASE | re.DOTALL)


def parse_sitemap_xml(text: str) -> List[str]:
    """Extract ``<loc>`` URLs from a ``sitemap.xml`` (or sitemap index).

    Uses plain text extraction rather than a full XML parse so an untrusted sitemap cannot
    trigger XML entity-expansion ("billion laughs") or external-entity (XXE) attacks — there
    is no DTD/entity processing at all, only the predefined XML entities are decoded.
    """
    return [unescape(match.strip()) for match in _LOC_RE.findall(text) if match.strip()]


def _common_host(urls) -> str:
    for url in urls:
        parsed = urlparse(url)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
    return ""


def sitemap_text_to_openapi(text: str, host: str = "") -> dict:
    """Convert sitemap text (XML, HTML, or a plain URL list) into a synthetic OpenAPI doc."""
    head = text.lstrip()[:2000].lower()
    if head.startswith("<?xml") or "<urlset" in head or "<sitemapindex" in head:
        urls = parse_sitemap_xml(text)
        return urls_to_openapi(urls, host or _common_host(urls))
    if "<html" in head or "<a " in head or "<form" in head or "<!doctype html" in head:
        return html_to_openapi(text, base_url=host, host=host)
    urls = [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")]
    return urls_to_openapi(urls, host or _common_host(urls))


# --------------------------------------------------------------------------------------
# concrete surfaces
# --------------------------------------------------------------------------------------

def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


class OpenAPISurface(OpenAPISpecificationParser):
    """Target surface backed by a real OpenAPI specification."""

    is_sitemap = False

    @classmethod
    def from_file(cls, path: str, host: str = None) -> "OpenAPISurface":
        text = _read_text(path)
        data = yaml.safe_load(text) if path.lower().endswith((".yaml", ".yml")) else json.loads(text)
        if host and not data.get("servers"):
            data["servers"] = [{"url": host}]
        return cls(filepath=path, api_data=data)


class SitemapSurface(OpenAPISpecificationParser):
    """Target surface synthesised from a website sitemap / URL list / crawled HTML.

    A sitemap carries no JSON request/response schemas and no documented security metadata,
    so schema-driven and ``security:``/response-code-driven classifications yield nothing;
    endpoint discovery and path-keyword classification still work. See ``is_sitemap``.
    """

    is_sitemap = True

    @classmethod
    def from_file(cls, path: str, host: str = None) -> "SitemapSurface":
        spec = sitemap_text_to_openapi(_read_text(path), host or "")
        return cls(filepath=path, api_data=spec)

    @classmethod
    def from_urls(cls, urls, host: str = "", filepath: str = "") -> "SitemapSurface":
        return cls(filepath=filepath, api_data=urls_to_openapi(urls, host))

    @classmethod
    def from_html(cls, html: str, base_url: str = "", host: str = "", filepath: str = "") -> "SitemapSurface":
        return cls(filepath=filepath, api_data=html_to_openapi(html, base_url=base_url, host=host))


def load_surface(path: str, host: str = None) -> TargetSurface:
    """Load a surface file, auto-detecting OpenAPI vs sitemap.

    A ``.json``/``.yaml``/``.yml`` file whose content looks like an OpenAPI document
    (``openapi``/``swagger``/``paths`` keys) becomes an :class:`OpenAPISurface`; anything
    else (``sitemap.xml``, a URL list, or an HTML page) becomes a :class:`SitemapSurface`.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Surface file not found at {path}")
    ext = os.path.splitext(path)[1].lower()
    if ext in (".yaml", ".yml", ".json"):
        try:
            text = _read_text(path)
            data = yaml.safe_load(text) if ext in (".yaml", ".yml") else json.loads(text)
        except (yaml.YAMLError, json.JSONDecodeError):
            data = None
        if isinstance(data, dict) and ("openapi" in data or "swagger" in data or "paths" in data):
            if host and not data.get("servers"):
                data["servers"] = [{"url": host}]
            return OpenAPISurface(filepath=path, api_data=data)
    return SitemapSurface.from_file(path, host=host)
