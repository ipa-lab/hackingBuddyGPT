import re

class PatternMatcher:
    """
    A utility class for matching and manipulating URL paths using regular expressions.

    This class supports:
    - Detecting specific patterns in URL paths (e.g., numeric IDs, nested resources).
    - Replacing numeric IDs and query parameters with placeholders.
    - Extracting query parameters into a dictionary.
    """

    def __init__(self):
        """
        Initialize the PatternMatcher with predefined regex patterns.
        """
        self.patterns = {
            'id': re.compile(r"/\d+"),  # Matches numeric segments in paths like "/123"
            'query_params': re.compile(r"(\?|\&)([^=]+)=([^&]+)"),  # Matches key=value pairs in query strings
            'numeric_resource': re.compile(r"/\w+/\d+$"),  # Matches paths like "/resource/123"
            'nested_resource': re.compile(r"/\w+/\w+/\d+$")  # Matches paths like "/category/resource/123"
        }

    def matches_any_pattern(self, path):
        """
        Check if the input path matches any of the defined regex patterns.

        Args:
            path (str): The URL path to evaluate.

        Returns:
            bool: True if any pattern matches; False otherwise.
        """
        for name, pattern in self.patterns.items():
            if pattern.search(path):
                return True
        return False

    def replace_parameters(self, path, param_placeholder="{{{param}}}"):
        """
        Replace numeric path segments and query parameter values with placeholders.

        Args:
            path (str): The URL path to process.
            param_placeholder (str): A template string for parameter placeholders (not currently used).

        Returns:
            str: The transformed path with placeholders.
        """
        for pattern_name, pattern in self.patterns.items():
            if 'id' in pattern_name:
                # Replace numeric path segments with "/{id}"
                return pattern.sub(r"/{id}", path)

            if 'query_params' in pattern_name:
                # Replace query parameter values with placeholders
                def replacement_logic(match):
                    delimiter = match.group(1)  # ? or &
                    param_name = match.group(2)
                    param_value = match.group(3)

                    # Replace value with a lowercase placeholder
                    new_value = f"{{{param_name.lower()}}}"
                    return f"{delimiter}{param_name}={new_value}"

                return pattern.sub(replacement_logic, path)

        return path

    def replace_according_to_pattern(self, path):
        """
        Apply replacement logic if the path matches known patterns.
        Also replaces hardcoded "/1" with "/{id}" as a fallback.

        Args:
            path (str): The URL path to transform.

        Returns:
            str: The transformed path.
        """
        if self.matches_any_pattern(path):
            return self.replace_parameters(path)

        # Fallback transformation
        if "/1" in path:
            path = path.replace("/1", "/{id}")
        return path

    def extract_query_params(self, path):
        """
        Extract query parameters from a URL into a dictionary.

        Args:
            path (str): The URL containing query parameters.

        Returns:
            dict: A dictionary of parameter names and values.
        """
        params = {}
        matches = self.patterns['query_params'].findall(path)
        for _, param, value in matches:
            params[param] = value
        return params


if __name__ == "__main__":
    # Example usage
    matcher = PatternMatcher()
    example_path = "/resource/456?param1=10&Param2=text&NumValue=123456"
    example_nested_path = "/category/resource/789?detail=42&Info2=moreText"

    # Replace parameters in paths
    modified_path = matcher.replace_parameters(example_path)
    modified_nested_path = matcher.replace_parameters(example_nested_path)

    print(modified_path)
    print(modified_nested_path)
    print(f'Original path: {example_path}')
    print(f'Extracted parameters: {matcher.extract_query_params(example_path)}')

    print(f'Original nested path: {example_nested_path}')
    print(f'Extracted parameters: {matcher.extract_query_params(example_nested_path)}')
