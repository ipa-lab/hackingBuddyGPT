from itertools import chain

from hackingBuddyGPT.usecases.web_api_testing.documentation.pattern_matcher import PatternMatcher


class Evaluator:
    def __init__(self, num_runs=10, config=None):
        self._pattern_matcher = PatternMatcher()
        self.documented_query_params = config.get("query_params")
        self.num_runs = num_runs
        self.documented_routes = config.get("correct_endpoints") #Example documented GET routes
        self.query_params_documented = len(config.get("query_params"))  # Example documented query parameters
        self.results = {
            "routes_found": [],
            "query_params_found": [],
            "false_positives": [],
        }

    def calculate_metrics(self):
        """
        Calculate evaluation metrics.
        """
        # Average percentages of documented routes and parameters found



        # Calculate percentages
        percent_routes_found = self.get_percentage(self.results["routes_found"], self.documented_routes)
        if len(self.documented_query_params) > 0:
            percent_params_found = self.get_percentage(self.results["query_params_found"], self.documented_query_params)
        else:
            percent_params_found = 0

        # Average false positives
        avg_false_positives = len(self.results["false_positives"]) / self.num_runs

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
            "Additional_routes Found":  set(self.results["routes_found"]).difference(set(self.documented_routes)),
            "Missing routes Found":  set(self.documented_routes).difference(set(self.results["routes_found"])),
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
        response_query_params = self._pattern_matcher.extract_query_params(path).keys()

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
        response_query_params = self._pattern_matcher.extract_query_params(path)
        x = self.documented_query_params.values()
        # Count the valid query parameters found in the response
        valid_query_params = []
        if response_query_params:
            for param, value in response_query_params.items():
                if value in x:
                    valid_query_params.append(value)

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
        return self._pattern_matcher.extract_query_params(path).keys()

    def evaluate_response(self, response, routes_found):
        query_params_found = 0
        false_positives = 0
        # Use evaluator to record routes and parameters found
        if response.action.__class__.__name__ != "RecordNote":
            path = response.action.path
            if path.__contains__('?'):
                query_params_found = self.all_query_params_found(path)  # This function should return the number found
                false_positives = self.check_false_positives(path)  # Define this function to determine FP count

            # Record these results in the evaluator
            self.results["routes_found"] += routes_found
            self.results["query_params_found"].append(query_params_found)
            self.results["false_positives"].append(false_positives)

    def get_percentage(self, param, documented_param):
        found_set = set(param)
        documented_set = set(documented_param)

        common_items = documented_set.intersection(found_set)
        common_count = len(common_items)
        percentage = (common_count / len(documented_set)) * 100

        return percentage

    def finalize_documentation_metrics(self, file_path):
        """Calculate and log the final effectiveness metrics after documentation process is complete."""
        metrics = self.calculate_metrics()
        # Specify the file path

        print(f'Appending metrics to {file_path}')

        # Appending the formatted data to a text file
        with open(file_path, 'a') as file:  # 'a' is for append mode
            file.write("\n\nDocumentation Effectiveness Metrics:\n")
            file.write(f"Percent Routes Found: {metrics['Percent Routes Found']:.2f}%\n")
            file.write(f"Percent Parameters Found: {metrics['Percent Parameters Found']:.2f}%\n")
            file.write(f"Average False Positives: {metrics['Average False Positives']}\n")
            file.write(
                f"Routes Found - Best: {metrics['Routes Best/Worst'][0]}, Worst: {metrics['Routes Best/Worst'][1]}\n")
            file.write(
                f"Query Parameters Found - Best: {metrics['Params Best/Worst'][0]}, Worst: {metrics['Params Best/Worst'][1]}\n")
            file.write(f"Additional Routes Found: {', '.join(map(str, metrics['Additional_routes Found']))}\n")
            file.write(f"Missing Routes Found: {', '.join(map(str, metrics['Missing routes Found']))}\n")

            # Adding a summary or additional information
            total_documented_routes = len(self.documented_routes)
            total_additional_routes = len(metrics['Additional_routes Found'])
            total_missing_routes = len(metrics['Missing routes Found'])
            file.write("\nSummary:\n")
            file.write(f"Total Documented Routes: {total_documented_routes}\n")
            file.write(f"Total Additional Routes Found: {total_additional_routes}\n")
            file.write(f"Total Missing Routes: {total_missing_routes}\n")

            # Optionally include a timestamp or other metadata
            from datetime import datetime
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            file.write(f"Metrics generated on: {current_time}\n")

