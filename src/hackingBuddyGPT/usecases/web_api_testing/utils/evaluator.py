class Evaluator:
    def __init__(self, num_runs=10, config:str=""):
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
        avg_routes_found = sum(self.results["routes_found"]) / self.num_runs
        avg_query_params_found = sum(self.results["query_params_found"]) / self.num_runs

        percent_routes_found = (avg_routes_found / self.get_routes_documented) * 100
        percent_params_found = (avg_query_params_found / self.query_params_documented) * 100

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

    def check_false_positives(self, response):
        """
        Identify and count false positive query parameters in the response.

        Args:
            response (dict): The response data to check for false positive parameters.

        Returns:
            int: The count of false positive query parameters.
        """
        # Example list of documented query parameters
        documented_query_params = ["user_id", "post_id", "page", "limit"]

        # Extract the query parameters from the response
        response_query_params = self.extract_query_params_from_response_data(response)

        # Identify false positives
        false_positives = [param for param in response_query_params if param not in documented_query_params]

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

    def all_query_params_found(self, turn):
        """
        Count the number of documented query parameters found in a response.

        Args:
            turn (int): The current turn number for the documentation process.

        Returns:
            int: The count of documented query parameters found in this turn.
        """
        # Example list of documented query parameters
        documented_query_params = ["user_id", "post_id", "page", "limit"]

        # Simulate response query parameters found (this would usually come from the response data)
        response_query_params = self.extract_query_params_from_response(turn)

        # Count the valid query parameters found in the response
        valid_query_params = [param for param in response_query_params if param in documented_query_params]

        return len(valid_query_params)

    def extract_query_params_from_response(self, turn):
        """
        Extract query parameters from the response in a specific turn.

        Args:
            turn (int): The current turn number for the documentation process.

        Returns:
            list: A list of query parameter names found in the response.
        """
        # Placeholder code: Replace this with actual extraction logic
        # Here, you should parse the actual API response to identify query parameters
        example_responses = {
            1: ["user_id", "page", "unknown_param"],
            2: ["post_id", "limit"],
            3: ["user_id", "limit", "extra_param"],
        }
        return example_responses.get(turn, [])

