"""Pure builders that derive a deeper candidate endpoint path from a base path.

Used by the detection/documentation exploration FSM to propose the next endpoint shape
(sub-resource, related-resource, multi-level). Extracted from ``PromptGenerationHelper`` (where
they were state-free ``_get_*_resource_endpoint`` methods); logic is unchanged.
"""
import random


def related_resource(path: str, common_endpoints) -> str:
    """Build a ``/resource/id/other_resource`` shaped endpoint from ``path``."""
    other_resource = random.choice(common_endpoints)

    if path.endswith("/1"):
        test_endpoint = f"{path}/{other_resource}"
    else:
        test_endpoint = f"{path}/1/{other_resource}"

    return test_endpoint.replace("//", "/")


def multi_level_resource(path: str, common_endpoints) -> str:
    """Build a ``/resource/other_resource/another_resource`` shaped endpoint from ``path``."""
    other_resource = random.choice(common_endpoints)
    another_resource = random.choice(common_endpoints)
    if other_resource == another_resource:
        another_resource = random.choice(common_endpoints)
    path = path.replace("{id}", "1")
    parts = [part.strip() for part in path.split("/") if part.strip()]

    multilevel_endpoint = path

    if len(parts) == 1:
        multilevel_endpoint = f"{path}/{other_resource}/{another_resource}"
    elif len(parts) == 2:
        path = [part.strip() for part in path.split("/") if part.strip()]
        if len(path) == 1:
            multilevel_endpoint = f"{path}/{other_resource}/{another_resource}"
        if len(path) >= 2:
            multilevel_endpoint = f"{path}/{another_resource}"
    else:
        if "/1" not in path:
            multilevel_endpoint = path

    return multilevel_endpoint.replace("//", "/")


def sub_resource(path: str, common_endpoints) -> str:
    """Build a ``/resource/other_resource`` shaped endpoint from ``path``."""
    filtered_endpoints = [resource for resource in common_endpoints if "id" not in resource]
    possible_resources = []
    for endpoint in filtered_endpoints:
        partz = [part.strip() for part in endpoint.split("/") if part.strip()]
        if len(partz) == 1 and "1" not in partz:
            possible_resources.append(endpoint)

    other_resource = random.choice(possible_resources)
    path = path.replace("{id}", "1")

    parts = [part.strip() for part in path.split("/") if part.strip()]

    multilevel_endpoint = path

    if len(parts) == 1:
        multilevel_endpoint = f"{path}/{other_resource}"
    elif len(parts) == 2:
        if "1" in parts:
            p = path.split("/1")
            new_path = ""
            for part in p:
                new_path = path.join(part)
            multilevel_endpoint = f"{new_path}/{other_resource}"
    else:
        if "1" not in path:
            multilevel_endpoint = path
    return multilevel_endpoint.replace("//", "/")
