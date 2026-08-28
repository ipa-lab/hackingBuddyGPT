import re

# Numeric path segments like "/123" — replaced with the "/{id}" placeholder when generalising a path.
_NUMERIC_SEGMENT = re.compile(r"/\d+")
# key=value pairs in a query string, capturing (delimiter, name, value).
_QUERY_PARAM = re.compile(r"(\?|\&)([^=]+)=([^&]+)")


class PatternMatcher:
    """Utilities for generalising URL paths: id-placeholder substitution and query extraction."""

    def replace_according_to_pattern(self, path: str) -> str:
        """Replace numeric path segments (e.g. ``/users/1``) with the ``/{id}`` placeholder."""
        return _NUMERIC_SEGMENT.sub("/{id}", path)

    def extract_query_params(self, path: str) -> dict:
        """Extract query parameters from a URL into a ``{name: value}`` dict."""
        return {name: value for _, name, value in _QUERY_PARAM.findall(path)}
