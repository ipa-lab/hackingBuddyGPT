from hackingBuddyGPT.usecases.web_api_testing.documentation.pattern_matcher import PatternMatcher


class Evaluator:
    def __init__(self, num_runs=10, config=None):
        self.pattern_matcher = PatternMatcher()
        self.documented_query_params = config.get("query_params")
        self.num_runs = num_runs
        self.get_routes_documented = 20  # Example documented GET routes
        self.query_params_documented = 12  # Example documented query parameters
        self.results = {
            "routes_found": [],
            "query_params_found": [],
            "false_positives": [],
        }

    def calculate_metrics(self):
        """
        Calculate evaluation metrics based on the simulated runs.
        """
        # Average percentages of documented routes and parameters found
        routes_found = len(self.results["routes_found"])
        query_params_found = len(self.results["query_params_found"])

        percent_routes_found = (routes_found / self.get_routes_documented) * 100
        percent_params_found = (query_params_found / self.query_params_documented) * 100

        # Average false positives
        avg_false_positives = sum(self.results["false_positives"]) / self.num_runs

        # Best and worst for routes and parameters
        r_best = max(self.results["routes_found"])
        r_worst = min(self.results["routes_found"])
        p_best = max(self.results["query_params_found"])
        p_worst = min(self.results["query_params_found"])

        metrics = {
            "Percent Routes Found": percent_routes_found,
            "Percent Parameters Found": percent_params_found,
            "Average False Positives": avg_false_positives,
            "Routes Best/Worst": (r_best, r_worst),
            "Params Best/Worst": (p_best, p_worst),
        }

        return metrics

    def check_false_positives(self, path):
        """
        Identify and count false positive query parameters in the response.

        Args:
            response (dict): The response data to check for false positive parameters.

        Returns:
            int: The count of false positive query parameters.
        """
        # Example list of documented query parameters
        # Extract the query parameters from the response
        response_query_params = self.pattern_matcher.extract_query_params(path).keys()

        # Identify false positives
        false_positives = [param for param in response_query_params if param not in self.documented_query_params]

        return len(false_positives)

    def extract_query_params_from_response_data(self, response):
        """
        Extract query parameters from the actual response data.

        Args:
            response (dict): The response data.

        Returns:
            list: A list of query parameter names found in the response.
        """
        # Placeholder code: Replace with actual logic to parse response and extract query parameters
        return response.get("query_params", [])

    def all_query_params_found(self, path):
        """
        Count the number of documented query parameters found in a response.

        Args:
            turn (int): The current turn number for the documentation process.

        Returns:
            int: The count of documented query parameters found in this turn.
        """
        # Example list of documented query parameters

        # Simulate response query parameters found (this would usually come from the response data)
        response_query_params = self.pattern_matcher.extract_query_params(path).keys()

        # Count the valid query parameters found in the response
        valid_query_params = [param for param in response_query_params if param in self.documented_query_params]

        return len(valid_query_params)

    def extract_query_params_from_response(self, path):
        """
        Extract query parameters from the response in a specific turn.

        Args:
            turn (int): The current turn number for the documentation process.

        Returns:
            list: A list of query parameter names found in the response.
        """
        # Placeholder code: Replace this with actual extraction logic
        return self.pattern_matcher.extract_query_params(path).keys()

    def evaluate_response(self, turn, response, routes_found):
        # Use evaluator to record routes and parameters found
        if response.__class__.__name__ != "RecordNote":
            path = response.action.path
            query_params_found = self.all_query_params_found(path)  # This function should return the number found
            false_positives = self.check_false_positives(path)  # Define this function to determine FP count

            # Record these results in the evaluator
            self.results["routes_found"].append(routes_found)
            self.results["query_params_found"].append(query_params_found)
            self.results["false_positives"].append(false_positives)
