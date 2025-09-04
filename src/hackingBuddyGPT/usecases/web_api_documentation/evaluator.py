import copy

from hackingBuddyGPT.utils.web_api.pattern_matcher import PatternMatcher


class Evaluator:
    def __init__(self, num_runs=10, config=None):
        self._pattern_matcher = PatternMatcher()
        self.documented_query_params = config.get("query_params")
        self.num_runs = num_runs
        self.ids = []
        self.query_params_found = {}
        self.name = config.get("name")
        self.documented_routes = config.get("correct_endpoints")  # Example documented GET routes
        self.query_params_documented = len(config.get("query_params"))  # Example documented query parameters
        self.results = {
            "routes_found": [],
            "query_params_found": {},
            "false_positives": [],
        }

    def calculate_metrics(self):
        """
        Calculate evaluation metrics.
        """
        # Average percentages of documented routes and parameters found
        percent_params_found_values = 0
        percent_params_found_keys = 0

        self.results["routes_found"] = list(set(self.results["routes_found"]))
        # Calculate percentages
        percent_routes_found = self.get_percentage(self.results["routes_found"], self.documented_routes)
        if len(self.documented_query_params) > 0:
            percent_params_found_values = self.calculate_match_percentage(self.documented_query_params, self.results["query_params_found"])["Value Match Percentage"]
            percent_params_found_keys = self.calculate_match_percentage(self.documented_query_params, self.results["query_params_found"])["Key Match Percentage"]
        else:
            percent_params_found = 0

        # Average false positives
        avg_false_positives = len(self.results["false_positives"]) / self.num_runs


        # Best and worst for routes and parameters
        if len(self.results["routes_found"]) >0:

            r_best = max(self.results["routes_found"])
            r_worst = min(self.results["routes_found"])
        else:
            r_best = 0
            r_worst = 0
        self.documented_routes = list(set(self.documented_routes))

        metrics = {
            "Percent Routes Found": percent_routes_found,
            "Percent Parameters Values Found": percent_params_found_values,
            "Percent Parameters Keys Found": percent_params_found_keys,
            "Average False Positives": avg_false_positives,
            "Routes Best/Worst": (r_best, r_worst),
            "Additional_Params Best/Worst": set(
    tuple(value) if isinstance(value, list) else value for value in self.documented_query_params.values()
).difference(
    set(tuple(value) if isinstance(value, list) else value for value in self.query_params_found.values())
),
            "Additional_routes Found": set(self.results["routes_found"]).difference(set(self.documented_routes)),
            "Missing routes Found": set(self.documented_routes).difference(set(self.results["routes_found"])),
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
        return response.get("query_params", [])

    def all_query_params_found(self, path, response):
        """
        Count the number of documented query parameters found in a response.

        Args:
            turn (int): The current turn number for the documentation process.

        Returns:
            int: The count of documented query parameters found in this turn.
        """
        if response.action.query is not None:
            query = response.action.query.split("?")[0]
            path = path + "&"+ query
        # Simulate response query parameters found (this would usually come from the response data)
        response_query_params = self._pattern_matcher.extract_query_params(path)
        valid_query_params = []
        if "?" in path:
            ep = path.split("?")[0]  # Count the valid query parameters found in the response
            if response_query_params:
                for param, value in response_query_params.items():
                    if ep in self.documented_query_params.keys():
                        x = self.documented_query_params[ep]
                        if param in x:
                            valid_query_params.append(param)
                            if ep not in self.results["query_params_found"].keys():
                                self.results["query_params_found"][ep] = []
                            if param not in self.results["query_params_found"][ep]:
                                self.results["query_params_found"][ep].append(param)
                    if ep not in self.query_params_found.keys():
                        self.query_params_found[ep] = []
                    if param not in self.query_params_found[ep]:
                        self.query_params_found[ep].append(param)
        self.results["query_params_found"] = self.query_params_found

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

    def calculate_match_percentage(self, documented, result):
        total_keys = len(documented)
        matching_keys = 0
        value_matches = 0
        total_values = 0

        for key in documented:
            # Check if the key exists in the result
            if key in result:
                matching_keys += 1
                # Compare values as sets (ignoring order)
                documented_values = set(documented[key])
                result_values = set(result[key])

                # Count the number of matching values
                value_matches += len(documented_values & result_values)  # Intersection
                total_values += len(documented_values)  # Total documented values for the key
            else:
                total_values += len(documented[key])  # Add documented values for missing keys

        # Calculate percentages
        key_match_percentage = (matching_keys / total_keys) * 100
        value_match_percentage = (value_matches / total_values) * 100 if total_values > 0 else 0

        return {
            "Key Match Percentage": key_match_percentage,
            "Value Match Percentage": value_match_percentage,
        }

    def evaluate_response(self, response, routes_found, current_step, query_endpoints):
        query_params_found = 0
        routes_found = copy.deepcopy(routes_found)

        false_positives = 0
        for idx, route in enumerate(routes_found):
                routes_found = self.add_if_is_cryptocurrency(idx, route, routes_found, current_step)
        # Use evaluator to record routes and parameters found
        if response.action.__class__.__name__ != "RecordNote":
            for path in query_endpoints :
                self.all_query_params_found(path, response)  # This function should return the number found
                false_positives = self.check_false_positives(path)  # Define this function to determine FP count

            # Record these results in the evaluator
            self.results["routes_found"] += routes_found
            #self.results["query_params_found"].append(query_params_found)
            self.results["false_positives"].append(false_positives)

    def add_if_is_cryptocurrency(self, idx, path,routes_found,current_step):
        """
               If the path contains a known cryptocurrency name, replace that part with '{id}'
               and add the resulting path to `self.prompt_helper.found_endpoints`.
               """
        # Default list of cryptos to detect
        routes_found = list(set(routes_found))
        cryptos = ["bitcoin", "ethereum", "litecoin", "dogecoin",
                       "cardano", "solana", "binance", "polkadot", "tezos",]

        # Convert to lowercase for the match, but preserve the original path for reconstruction if you prefer
        lower_path = path.lower()

        parts = [part.strip() for part in path.split("/") if part.strip()]

        for crypto in cryptos:
            if crypto in lower_path:
                # Example approach: split by '/' and replace the segment that matches crypto
                parts = path.split('/')
                replaced_any = False
                for i, segment in enumerate(parts):
                    if segment.lower() == crypto:
                        parts[i] = "{id}"
                        replaced_any = True

                # Only join and store once per path
                if replaced_any:
                    replaced_path = "/".join(parts)
                    if path in routes_found:
                        for i, route in enumerate(routes_found):
                            if route == path:
                                routes_found[i] = replaced_path

                    else:
                        routes_found.append(replaced_path)
        if len(parts) == 3 and current_step == 4:
            if "/"+ parts[0] + "/{id}/" + parts[2] not  in routes_found:
                for i, route in enumerate(routes_found):
                    if route == path:
                        routes_found[i] = "/" + parts[0] + "/{id}/" + parts[2]
                        break
        if len(parts) == 2 and current_step == 2:
            if "/"+parts[0] + "/{id}" not in routes_found:
                for i, route in enumerate(routes_found):
                    if route == path:
                        routes_found[i] ="/"+parts[0] + "/{id}"
                        break

        if "/1" in path:
            if idx < len(routes_found):
                routes_found[idx] = routes_found[idx].replace("/1", "/{id}")
        return routes_found


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
            file.write(f"Percent Parameters Values Found: {metrics['Percent Parameters Values Found']:.2f}%\n")
            file.write(f"Percent Parameters Keys Found: {metrics['Percent Parameters Keys Found']:.2f}%\n")
            file.write(f"Average False Positives: {metrics['Average False Positives']}\n")
            file.write(
                f"Routes Found - Best: {metrics['Routes Best/Worst'][0]}, Worst: {metrics['Routes Best/Worst'][1]}\n")
            file.write(
                f"Additional Query Parameters Found - Best: {', '.join(map(str, metrics['Additional_Params Best/Worst']))}\n")
            file.write(f"Additional Routes Found: {', '.join(map(str, metrics['Additional_routes Found']))}\n")
            file.write(f"Missing Routes Found: {', '.join(map(str, metrics['Missing routes Found']))}\n")

            # Adding a summary or additional information
            total_documented_routes = len(self.documented_routes)
            total_additional_routes = len(metrics['Additional_routes Found'])
            total_missing_routes = len(metrics['Missing routes Found'])
            file.write("\nSummary:\n")
            file.write(f"Total Params Found: {self.query_params_found}\n")
            file.write(f"Total Documented Routes: {total_documented_routes}\n")
            file.write(f"Total Additional Routes Found: {total_additional_routes}\n")
            file.write(f"Total Missing Routes: {total_missing_routes}\n")
            file.write(f" Missing Parameters: {total_missing_routes}\n")

            # Optionally include a timestamp or other metadata
            from datetime import datetime
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            file.write(f"Metrics generated on: {current_time}\n")
