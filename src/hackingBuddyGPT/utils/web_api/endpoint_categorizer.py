"""Shared helper for grouping REST endpoint paths into structural buckets.

The documentation use-case, the OpenAPI parser and the response handler each
used to carry a near-identical copy of this categorisation logic. They now all
delegate to :func:`categorize_by_structure` and adapt its result to whatever
shape each call site expects.
"""
from typing import Dict, Iterable, List


def categorize_by_structure(endpoints: Iterable[str], id_token: str = "id") -> Dict[str, List[str]]:
    """Group endpoint paths into five structural buckets by path-segment count.

    Args:
        endpoints: Iterable of endpoint path strings (e.g. ``/users/{id}``).
        id_token: Token that marks an id path-parameter, matched as a substring
            of the full path. ``"id"`` reproduces the documentation/parser style;
            ``"{id}"`` reproduces the common-endpoints style used by the response
            handler. (For the fixed common-endpoints list a whole-path match is
            equivalent to the original per-segment check.)

    Returns:
        Dict with keys ``root_level``, ``instance_level``, ``subresource``,
        ``related_resource`` and ``multi_level_resource``.
    """
    root_level: List[str] = []
    instance_level: List[str] = []
    subresource: List[str] = []
    related_resource: List[str] = []
    multi_level_resource: List[str] = []

    for endpoint in endpoints:
        parts = [part for part in endpoint.split("/") if part]
        if len(parts) == 1:
            root_level.append(endpoint)
        elif len(parts) == 2:
            (instance_level if id_token in endpoint else subresource).append(endpoint)
        elif len(parts) == 3:
            (related_resource if id_token in endpoint else multi_level_resource).append(endpoint)
        else:
            multi_level_resource.append(endpoint)

    return {
        "root_level": root_level,
        "instance_level": instance_level,
        "subresource": subresource,
        "related_resource": related_resource,
        "multi_level_resource": multi_level_resource,
    }
