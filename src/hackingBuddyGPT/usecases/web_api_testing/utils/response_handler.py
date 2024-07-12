import json

from bs4 import BeautifulSoup


class ResponseHandler(object):
    def __init__(self, llm_handler):
        self.llm_handler = llm_handler

    def get_response_for_prompt(self, prompt):
        """
        Sends a prompt to OpenAI's API and retrieves the response.

        Args:
            prompt (str): The prompt to be sent to the API.

        Returns:
            str: The response from the API.
        """
        messages = [{"role": "user",
                     "content": [{"type": "text", "text": prompt}
                                 ]
                     }
                    ]


        response, completion = self.llm_handler.call_llm(messages)

        response_text = response.execute()

        return response_text
    def parse_http_status_line(self, status_line):
        if status_line == "Not a valid HTTP method":
            return status_line
        if status_line and " " in status_line:
            protocol, status_code, status_message = status_line.split(' ', 2)
            status_message = status_message.split("\r\n")[0]
            return f'{status_code} {status_message}'
        raise ValueError("Invalid HTTP status line")

    def extract_response_example(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')

        # Extract the JavaScript example code
        example_code = soup.find('code', {'id': 'example'})
        if example_code:
            example_text = example_code.get_text()
        else:
            return None

        # Extract the result placeholder for the response
        result_code = soup.find('code', {'id': 'result'})
        if result_code:
            result_text = result_code.get_text()
        else:
            return None

        # Format the response example
        return json.loads(result_text)

    def parse_http_response_to_openapi_example(self, openapi_spec, http_response, path, method):
        # Extract headers and body from the HTTP response
        headers, body = http_response.split('\r\n\r\n', 1)

        # Convert the JSON body to a Python dictionary
        #print(f'BOdy: {body}')
        try :
            body_dict = json.loads(body)
        except json.decoder.JSONDecodeError:
            return None, None, openapi_spec
        reference, object_name, openapi_spec = self.parse_http_response_to_schema(openapi_spec, body_dict, path)

        entry_dict = {}
        # Build the OpenAPI response example
        if len(body_dict) == 1:
            entry_dict["id"] = {"value": body_dict}
            self.llm_handler.add_created_object(entry_dict, object_name)

        else:
            for entry in body_dict:
                key = entry.get("title") or entry.get("name") or entry.get("id")
                entry_dict[key] = {"value": entry}
                self.llm_handler.add_created_object(entry_dict[key], object_name)

        return entry_dict, reference, openapi_spec
    def extract_description(self, note):
        return note.action.content

    def parse_http_response_to_schema(self, openapi_spec ,body_dict, path):
        # Create object name
        object_name = path.split("/")[1].capitalize()
        object_name = object_name[:len(object_name) - 1]

        # Parse body dict to types
        properties_dict = {}
        print(f'Body dict:{body_dict}')
        print(f'LKen Body dict:{len(body_dict)}')
        if len(body_dict) == 1:
            properties_dict["id"] = {"type": "int", "format": "uuid", "example": str(body_dict["id"])}
        else:
            for param in body_dict:
                for key, value in param.items():
                    if key == "id":
                        properties_dict[key] = {"type": str(type(value).__name__), "format": "uuid", "example": str(value)}
                    else:
                        properties_dict[key] = {"type": str(type(value).__name__), "example": str(value)}
                break

        object_dict = {"type": "object", "properties": properties_dict}

        if not object_name in openapi_spec["components"]["schemas"].keys():
            openapi_spec["components"]["schemas"][object_name] = object_dict

        schemas = openapi_spec["components"]["schemas"]
        self.schemas = schemas
        reference = "#/components/schemas/" + object_name
        return reference, object_name, openapi_spec
    def read_yaml_to_string(self, filepath):
        """
        Reads a YAML file and returns its contents as a string.

        :param filepath: Path to the YAML file.
        :return: String containing the file contents.
        """
        try:
            with open(filepath, 'r') as file:
                file_contents = file.read()
            return file_contents
        except FileNotFoundError:
            print(f"Error: The file {filepath} does not exist.")
            return None
        except IOError as e:
            print(f"Error reading file {filepath}: {e}")
            return None
    def extract_endpoints(self, note):
        # Define a dictionary to hold the endpoint data
        required_endpoints = {}

        # Use regular expression to find all lines with endpoint definitions
        pattern = r"(\d+\.\s+GET)\s(/[\w{}]+)"
        matches = re.findall(pattern, note)

        # Process each match to populate the dictionary
        for match in matches:
            method, endpoint = match
            method = method.split()[1]  # Split to get rid of the numbering and keep "GET"
            if endpoint in required_endpoints:
                if method not in required_endpoints[endpoint]:
                    required_endpoints[endpoint].append(method)
            else:
                required_endpoints[endpoint] = [method]

        return required_endpoints

