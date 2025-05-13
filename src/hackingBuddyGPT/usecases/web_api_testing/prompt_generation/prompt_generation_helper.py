import json
import random
import re
import uuid


class PromptGenerationHelper(object):
    """
        Assists in generating prompts for web API testing by managing endpoint data,
        tracking interactions, and providing utilities for analyzing and responding to API behavior.

        Attributes:
            found_endpoints (list): Endpoints that have been successfully interacted with.
            tried_endpoints (list): Endpoints that have been tested, regardless of the outcome.
            unsuccessful_paths (list): Endpoints that failed during testing.
            current_step (int): Current step in the testing or documentation process.
            document_steps (int): Total number of documentation steps processed.
            endpoint_methods (dict): Maps endpoints to the HTTP methods successfully used with them.
            unsuccessful_methods (dict): Maps endpoints to the HTTP methods that failed.
            endpoint_found_methods (dict): Maps HTTP methods to the endpoints where they were found successful.
            schemas (list): Definitions of data schemas used for constructing requests and validating responses.
        """

    def __init__(self, host, description):
        """
          Initializes the PromptGenerationHelper with an optional host and description.
          """
        self.counter = 0
        self.uuid =uuid.uuid4()
        self.bad_request_endpoints = []
        self.endpoint_examples = {}
        self.name = ""
        if "coin" in host.lower():
            self.name = "Coin"
        if "reqres" in host.lower():
            self.name = "reqres"

        self.current_sub_step = None
        self.saved_endpoints = []
        self.tried_endpoints_with_params = {}
        self.host = host
        self._description= description
        self.current_test_step = None
        self.current_category = "root_level"
        self.correct_endpoint_but_some_error = {}
        self.endpoints_to_try = []
        self.hint_for_next_round = ""
        self.schemas = []
        self.endpoints = []
        self.tried_endpoints = []
        self.found_endpoints = []
        self.query_endpoints_params = {}
        self.found_query_endpoints = []
        self.endpoint_methods = {}
        self.unsuccessful_methods = {}
        self.endpoint_found_methods = {}
        self.unsuccessful_paths = ["/"]
        self.current_step = 1
        self.document_steps = 0
        self.tried_methods_by_enpoint = {}
        self.accounts = []
        self.possible_instance_level_endpoints = []

        self.current_user = None


    def get_user_from_prompt(self,step, accounts) -> dict:
        """
            Extracts the user information after 'user:' from the given prompts.

            Args:
                prompts (list): A list of dictionaries representing prompts.

            Returns:
                list: A list of extracted user information.
            """
        user_info = {}
        step = step["step"]
        # Search for the substring containing 'user:'
        if "user:" in step:
            # Extract the part after 'user:' and add it to the user_info list
            data_string = step.split("user:")[1].split(".\n")[0]
            # Replace single quotes with double quotes for JSON compatibility

            data_string_json = data_string.replace("'", '"')
            data_string_json = data_string_json.replace("\"\" ", '" ')


            if "{" in data_string_json:
                data_string_json = data_string_json.replace("None", "null")

                # Parse the string into a dictionary
                user_info = json.loads(data_string_json)
            else:
                user_info = data_string_json
        counter =0
        for acc in accounts:
            for key in acc.keys():
                if key in user_info.keys():
                    if isinstance(acc[key], str) and "or 1=1--" in acc[key]:
                        acc[key] = "' or 1=1--"
                    if key != "x":
                        if acc[key] == user_info[key]:
                            counter +=1

            if "x" not in acc or acc["x"] == "":
                user_info["x"] = ""
            counter += 1
        return user_info

    def find_missing_endpoint(self, endpoints: list) -> str:
        """
        Identifies and returns the first missing endpoint path found.

        Args:
            endpoints (dict): A dictionary of endpoint paths (e.g., {'/resources': {...}, '/resources/:id': {...}}).

        Returns:
            str: The first missing endpoint path found.
                 Example: '/resources/:id' or '/products'
        """
        general_endpoints = set()
        parameterized_endpoints = set()

        # Extract resource names and categorize them using regex
        for endpoint in endpoints:
            # Match both general and parameterized patterns and categorize them
            match = re.match(r'^/([^/]+)(/|/{id})?$', endpoint)
            if match:
                resource = match.group(1)
                if match.group(2) == '/' or match.group(2) is None:
                    general_endpoints.add(resource)
                elif match.group(2) == '/:id':
                    parameterized_endpoints.add(resource)

        # Find missing endpoints during the comparison
        for resource in parameterized_endpoints:
            if resource not in general_endpoints:
                return f'/{resource}'
        for resource in general_endpoints:
            if resource not in parameterized_endpoints:
                if f'/{resource}/'+ '{id}' in self.unsuccessful_paths:
                    continue
                return f'/{resource}/'+ '{id}'

        # Return an empty string if no missing endpoints are found
        return ""

    def get_endpoints_needing_help(self, info=""):
        """
        Determines which endpoints need further testing or have missing methods.

        Args:
            info (str): Additional information to enhance the guidance.

        Returns:
            list: Guidance for missing endpoints or methods.
        """

        # Step 1: Check for missing endpoints
        missing_endpoint = self.find_missing_endpoint(endpoints=self.found_endpoints)

        if (missing_endpoint and not missing_endpoint in self.unsuccessful_paths
                and not 'GET' in self.unsuccessful_methods
                and missing_endpoint in self.tried_methods_by_enpoint.keys()
                and not 'GET' in self.tried_methods_by_enpoint[missing_endpoint]):
            formatted_endpoint = missing_endpoint.replace("{id}", "1") if "{id}" in missing_endpoint else missing_endpoint
            if missing_endpoint not in self.tried_methods_by_enpoint:
                self.tried_methods_by_enpoint[missing_endpoint] = []
            self.tried_methods_by_enpoint[missing_endpoint].append('GET')
            return [
                f"{info}\n",
                f"For endpoint {formatted_endpoint}, find this missing method: GET."
            ]

        # Step 2: Check for endpoints needing additional HTTP methods
        http_methods_set = {"GET", "POST", "PUT", "DELETE"}
        for endpoint, methods in self.endpoint_methods.items():
            missing_methods = http_methods_set - set(methods)
            if missing_methods and endpoint not in self.unsuccessful_paths:
                for needed_method in missing_methods:  # Iterate directly over missing methods
                    if endpoint not in self.tried_methods_by_enpoint:
                        self.tried_methods_by_enpoint[endpoint] = []

                    # Avoid retrying methods that were already unsuccessful
                    if (needed_method in self.unsuccessful_methods.get(endpoint, [])
                            or needed_method in self.tried_methods_by_enpoint[endpoint]):
                        continue

                    # Format the endpoint and append the method as tried
                    formatted_endpoint = endpoint.replace("{id}", "1") if "{id}" in endpoint else endpoint
                    self.tried_methods_by_enpoint[endpoint].append(needed_method)

                    return [
                        f"{info}\n",
                        f"For endpoint {formatted_endpoint}, find this missing method: {needed_method}."
                    ]

        unsuccessful_paths = [path for path in self.unsuccessful_paths if "?" not in path]
        return [
            f"Look for any endpoint that might be missing params, exclude endpoints from this list :{unsuccessful_paths}"]


    def get_initial_documentation_steps(self, strategy_steps):
        """
        Constructs a series of documentation steps to guide the testing and documentation of API endpoints.
        These steps are formulated based on the strategy specified and integrate common steps that are essential
        across different strategies. The function also sets the number of documentation steps and determines specific
        steps based on the current testing phase.


        Returns:
            list: A comprehensive list of documentation steps tailored to the provided strategy, enhanced with common steps and hints for further actions.

        Detailed Steps:
            - Updates the list of unsuccessful paths and found endpoints to ensure uniqueness.
            - Depending on the strategy, it includes specific steps tailored to either in-context learning, tree of thought, or other strategies.
            - Each step is designed to methodically explore different types of endpoints (root-level, instance-level, etc.),
              focusing on various aspects such as parameter inclusion, method testing, and handling of special cases like IDs.
            - The steps are formulated to progressively document and test the API, ensuring comprehensive coverage.
        """
        # Ensure uniqueness of paths and endpoints
        self.unsuccessful_paths = list(set(self.unsuccessful_paths))
        self.found_endpoints = list(set(self.found_endpoints))
        hint = self.get_hint()

        # Combine common steps with strategy-specific steps

        self.document_steps = len(strategy_steps)
        steps = strategy_steps[0] + strategy_steps[self.current_step] + [hint]

        return steps



    def _check_prompt(self, previous_prompt: list, steps: str) -> str:
        """
        Validates and shortens the prompt if necessary to ensure it does not exceed the maximum token count.

        Args:
            previous_prompt (list): The previous prompt content.
            steps (str): A list of steps to be included in the new prompt.
            max_tokens (int, optional): The maximum number of tokens allowed. Defaults to 900.

        Returns:
            str: The validated and possibly shortened prompt.
        """

        def validate_prompt(prompt):
            return prompt

        if previous_prompt is None:
            potential_prompt = str(steps) + "\n"
            return validate_prompt(potential_prompt)

        if steps is not None and previous_prompt is not None and not all(step in previous_prompt for step in steps):
            if isinstance(steps, list):
                potential_prompt = "\n".join(str(element) for element in steps)
            else:
                potential_prompt = str(steps) + "\n"
            return validate_prompt(potential_prompt)

        return validate_prompt(previous_prompt)

    def _get_endpoint_for_query_params(self):
        """
        Searches for an endpoint in the found endpoints list that has query parameters.

        Returns:
            str: The first endpoint that includes a query parameter, or None if no such endpoint exists.
        """
        query_endpoint = None
        endpoints = self.found_endpoints + self.saved_endpoints + list(self.endpoint_examples.keys())
        endpoints = list (set(endpoints))
        for endpoint in endpoints:
            if self.tried_endpoints.count(query_endpoint) > 3:
                continue
            if endpoint not in self.query_endpoints_params or self.tried_endpoints:
                self.query_endpoints_params[endpoint] = []
            if len(self.query_endpoints_params[endpoint]) == 0:
                return endpoint

        # If no endpoint with query parameters is found, generate one
        if len(self.saved_endpoints) != 0:
            query_endpoints = [endpoint  for endpoint in self.saved_endpoints]
            query_endpoint = random.choice(query_endpoints)

        else:
            query_endpoint = random.choice(self.found_endpoints)

        return query_endpoint
    def _get_instance_level_endpoint(self, name=""):
        """
        Retrieves an instance level endpoint that has not been tested or found unsuccessful.

        Returns:
            str: A templated instance level endpoint ready to be tested, or None if no such endpoint is available.
        """
        instance_level_endpoints = self._get_instance_level_endpoints(name)
        for endpoint in instance_level_endpoints:
            endpoint = endpoint.replace("//", "/")
            id = self.get_possible_id_for_instance_level_ep(endpoint)
            templated_endpoint = endpoint.replace(f"{id}", "{id}")
            if  (endpoint not in self.found_endpoints and templated_endpoint
                    not in self.found_endpoints and endpoint.replace("1", "{id}")
                    not in self.unsuccessful_paths and endpoint not in self.unsuccessful_paths
                    and templated_endpoint != "/1/1"):
                return endpoint
        return None

    def _get_instance_level_endpoints(self, name):
        """
        Generates a list of instance-level endpoints from the root-level endpoints by appending '/1'.

        Returns:
            list: A list of potentially testable instance-level endpoints derived from root-level endpoints.
        """
        instance_level_endpoints = []
        for endpoint in self._get_root_level_endpoints():
            new_endpoint = endpoint + "/1"
            new_endpoint = new_endpoint.replace("//", "/")
            if new_endpoint == "seasons_average":
                new_endpoint = r"season_averages\general"
            if new_endpoint != "/1/1" and (
                    endpoint + "/{id}" not in self.found_endpoints and
                    endpoint + "/1" not in self.unsuccessful_paths and
                    new_endpoint not in self.unsuccessful_paths and
                    new_endpoint not in self.found_endpoints
            ):

                id = self.get_possible_id_for_instance_level_ep(endpoint)
                if id:
                    new_endpoint = new_endpoint.replace("1", f"{id}")
                if new_endpoint not in self.unsuccessful_paths and new_endpoint not in self.found_endpoints:

                    if new_endpoint in self.bad_request_endpoints:
                        id = str(self.uuid)
                        new_endpoint = endpoint + f"/{id}"
                        instance_level_endpoints.append(new_endpoint)
                    else:
                        instance_level_endpoints.append(new_endpoint)
                    self.possible_instance_level_endpoints.append(new_endpoint)

        return instance_level_endpoints

    def get_hint(self):
        """
        Generates a hint based on the current step in the testing process, incorporating specific checks and conditions.

        Returns:
            str: A tailored hint that provides guidance based on the current testing phase and identified needs.
        """
        hint = ""
        if self.current_step == 2:
            instance_level_found_endpoints = [ep for ep in self.found_endpoints if "id" in ep]
            if "Missing required field: ids" in self.correct_endpoint_but_some_error:
                endpoints_missing_id_or_query = list(
                    set(self.correct_endpoint_but_some_error["Missing required field: ids"]))
                hint = f"ADD an id after these endpoints: {endpoints_missing_id_or_query} avoid getting this error again: {self.hint_for_next_round}"
            if "base62" in self.hint_for_next_round and "Missing required field: ids" not in self.correct_endpoint_but_some_error:
                hint += " Try an id like 6rqhFgbbKwnb9MLmUQDhG6"
            new_endpoint = self._get_instance_level_endpoint(self.name)
            if new_endpoint:
                hint += f" Create a GET request for this endpoint: {new_endpoint}"

        elif self.current_step == 3 and "No search query" in self.correct_endpoint_but_some_error:
            endpoints_missing_query = list(set(self.correct_endpoint_but_some_error['No search query']))
            hint = f"First, try out these endpoints: {endpoints_missing_query}"

        if self.current_step == 6:
            query_endpoint = self._get_endpoint_for_query_params()

            if query_endpoint == "season_averages":
                query_endpoint = "season_averages/general"
            if query_endpoint == "stats":
                query_endpoint = "stats/advanced"
            query_params = self.get_possible_params(query_endpoint)
            if query_params is None:
                query_params = ["limit", "page", "size"]

            self.tried_endpoints.append(query_endpoint)

            hint = f'Use this endpoint: {query_endpoint} and infer params from this: {query_params}'
            hint +=" and use appropriate query params like "

        if self.hint_for_next_round:
            hint += self.hint_for_next_round

        return hint

    def _get_root_level_endpoints(self):
        """
        Retrieves all root-level endpoints which consist of only one path component.

        Returns:
            list: A list of root-level endpoints.
        """
        root_level_endpoints = []
        for endpoint in self.found_endpoints:
            parts = [part for part in endpoint.split("/") if part]
            if len(parts) == 1 and not endpoint+ "/{id}" in self.found_endpoints :
                root_level_endpoints.append(endpoint)
        return root_level_endpoints

    def _get_related_resource_endpoint(self, path, common_endpoints, name):
        """
                Identify related resource endpoints that match the format /resource/id/other_resource.

                Returns:
                    dict: A mapping of identified endpoints to their responses or error messages.
                """

        if "ball" in name:
            common_endpoints = ["stats", "seasons_average", "history", "match", "suggest", "related", '/notifications',
                                    '/messages', '/files', '/settings', '/status', '/health',
                                    '/healthcheck',
                                    '/feedback',
                                    '/support', '/profile', '/account', '/reports', '/dashboard', '/activity', ]
        other_resource = random.choice(common_endpoints)

        # Determine if the path is a root-level or instance-level endpoint
        if path.endswith("/1"):
            # Root-level source endpoint
            test_endpoint = f"{path}/{other_resource}"
        else:
            # Instance-level endpoint
            test_endpoint = f"{path}/1/{other_resource}"

        if "Coin" in name or "gbif" in name:
            parts = [part.strip() for part in path.split("/") if part.strip()]

            id = self.get_possible_id_for_instance_level_ep(parts[0])
            if id:
                test_endpoint = test_endpoint.replace("1", f"{id}")

        # Query the constructed endpoint
        test_endpoint = test_endpoint.replace("//", "/")


        return test_endpoint

    def _get_multi_level_resource_endpoint(self, path, common_endpoints, name):
        """
                Identify related resource endpoints that match the format /resource/id/other_resource.

                Returns:
                    dict: A mapping of identified endpoints to their responses or error messages.
                """

        if "brew" in name or "gbif" in name:
            common_endpoints = ["autocomplete", "search",  "random","match", "suggest", "related"]
        if "Coin" in name :
            common_endpoints = ["markets", "search",  "history","match", "suggest", "related", '/notifications',
                                '/messages', '/files', '/settings', '/status', '/health',
                                 '/healthcheck',
                                 '/feedback',
                                 '/support', '/profile', '/account', '/reports', '/dashboard', '/activity',]


        other_resource = random.choice(common_endpoints)
        another_resource = random.choice(common_endpoints)
        if other_resource == another_resource:
            another_resource = random.choice(common_endpoints)
        path = path.replace("{id}", "1")
        parts = [part.strip() for part in path.split("/") if part.strip()]

        if "Coin" in name or "gbif" in name:
            id = self.get_possible_id_for_instance_level_ep(parts[0])
            if id:
                path = path.replace("1", f"{id}")

        multilevel_endpoint = path

        if len(parts) == 1:
            multilevel_endpoint = f"{path}/{other_resource}/{another_resource}"
        elif len(parts) == 2:
            path = [part.strip() for part in path.split("/") if part.strip()]
            if len(path) == 1:
                multilevel_endpoint = f"{path}/{other_resource}/{another_resource}"
            if len(path) >=2:
                multilevel_endpoint = f"{path}/{another_resource}"
        else:
            if "/1" not in path:
                multilevel_endpoint = path

        multilevel_endpoint = multilevel_endpoint.replace("//", "/")

        return multilevel_endpoint

    def _get_sub_resource_endpoint(self, path, common_endpoints, name):
        """
                Identify related resource endpoints that match the format /resource/other_resource.

                Returns:
                    dict: A mapping of identified endpoints to their responses or error messages.
                """
        if "brew" in name or "gbif" in name:

            common_endpoints = ["autocomplete", "search",  "random","match", "suggest", "related"]

        filtered_endpoints = [resource for resource in common_endpoints
                              if "id" not in resource ]
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
        if "Coin" in name or "gbif" in name:
            id = self.get_possible_id_for_instance_level_ep(parts[0])
            if id:
                multilevel_endpoint = multilevel_endpoint.replace("1", f"{id}")
        multilevel_endpoint = multilevel_endpoint.replace("//", "/")

        return multilevel_endpoint

    def get_possible_id_for_instance_level_ep(self, endpoint):
        if endpoint in self.endpoint_examples:
            example = self.endpoint_examples[endpoint]
            resource = endpoint.split("s")[0].replace("/", "")

            if example:
                for key in example.keys():
                    if key and isinstance(key, str):
                        check_key = key.lower()
                        if "id" in check_key and check_key.endswith("id"):
                            id =  example[key]
                            if isinstance(id, int) or (isinstance(id, str) and id.isdigit()):
                                pattern = re.compile(rf"^/{re.escape(endpoint)}/\d+$")
                                if any(pattern.match(e) for e in self.found_endpoints):
                                    continue
                            if key == "id":
                                if endpoint + f"/{id}" in self.found_endpoints or endpoint + f"/{id}" in self.unsuccessful_paths:
                                    continue
                                else:
                                    return example[key]
                            elif resource in key:
                                if endpoint + f"/{id}" in self.found_endpoints or endpoint + f"/{id}" in self.unsuccessful_paths:
                                    continue
                                else:
                                    return example[key]


        return None

    def get_possible_params(self, endpoint):
        if endpoint in self.endpoint_examples:
            example = self.endpoint_examples[endpoint]
            if "reqres" in self.name:
                for key, value in example.items():
                    if not key in self.query_endpoints_params[endpoint]:
                        return f'{key}: {example[key]}'
            elif "ballardtide" in self.name:
                for key, value in example.items():
                    if not key in self.query_endpoints_params[endpoint]:
                        return f'{key}: {example[key]}'
                if example is None:
                    example = {"season_type": "regular", "type": "base"}

            return example




