import re


class PatternMatcher:

    def __init__(self):
        # Define patterns for different parts of URLs
        self.patterns = {
            'id': re.compile(r"/\d+"),  # Matches numeric IDs in paths
            'query_params': re.compile(r"(\?|\&)([^=]+)=([^&]+)"),  # Matches any query parameters
            'numeric_resource': re.compile(r"/\w+/\d+$"),  # Matches paths like "/resource/123"
            'nested_resource': re.compile(r"/\w+/\w+/\d+$")
            # Matches nested resource paths like "/category/resource/123"
        }

    def matches_any_pattern(self, path):
        # Check if the path matches any defined pattern
        for name, pattern in self.patterns.items():
            if pattern.search(path):
                return True
        return False

    def replace_parameters(self, path, param_placeholder="{{{param}}}"):
        # Replace numeric IDs and adjust query parameters in the path
        # Iterate over all patterns to apply replacements
        for pattern_name, pattern in self.patterns.items():
            if 'id' in pattern_name:  # Check for patterns that include IDs
                path = pattern.sub(r"/{id}", path)
            if 'query_params' in pattern_name:  # Check for query parameter patterns
                def replacement_logic(match):
                    # Extract the delimiter (? or &), parameter name, and value from the match
                    delimiter = match.group(1)
                    param_name = match.group(2)
                    param_value = match.group(3)

                    # Check if the parameter value is numeric
                    if param_value.isdigit():
                        # If numeric, replace the value with a placeholder using the lowercase parameter name
                        new_value = f"{{{param_name.lower()}}}"
                    else:
                        # If not numeric, use the original value
                        new_value = f"{{{param_name.lower()}}}"

                    # Construct the new parameter string
                    return f"{delimiter}{param_name}={new_value}"

                    # Apply the replacement logic to the entire path

                return pattern.sub(replacement_logic, path)
        return path

    def replace_according_to_pattern(self, path):
        if self.matches_any_pattern(path):
            return self.replace_parameters(path)
        return path

    def extract_query_params(self, path):
        # Extract query parameters from a path and return them as a dictionary
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
    print(f'{example_path}')

    print(f'extracted parameters: {matcher.extract_query_params(example_path)}')
    print(f'{example_nested_path}')

    print(f'extracted parameters: {matcher.extract_query_params(example_nested_path)}')
