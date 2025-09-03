from openai import OpenAI


class YamlFileAssistant:
    """
    YamlFileAssistant is a class designed to interact with a YAML file using OpenAI's API.

    Attributes:
        yaml_file (str): The path to the YAML file that the assistant will analyze.
        client (OpenAI): The OpenAI client used to interact with the OpenAI API.
    """

    def __init__(self, yaml_file: str, client: OpenAI):
        """
        Initializes the YamlFileAssistant with a specified YAML file and OpenAI client.

        Args:
            yaml_file (str): The path to the YAML file to be analyzed.
            client (OpenAI): The OpenAI client used to interact with the OpenAI API.
        """
        self.yaml_file: str = yaml_file
        self.client: OpenAI = client

    def run(self, recorded_note: str) -> None:
        """
        Runs the assistant to analyze the YAML file based on a recorded note.

        This method would typically interact with OpenAI's API to create an assistant,
        upload the YAML file, analyze its contents, and generate responses. However, the
        actual implementation is currently commented out.

        Args:
            recorded_note (str): A string containing the note or instructions for analysis.

        Note:
            The current implementation is commented out and serves as a placeholder for
            integrating with OpenAI's API. Uncomment and modify the code as needed.
        """
        assistant = self.client.beta.assistants.create(
            name="Yaml File Analysis Assistant",
            instructions="You are an OpenAPI specification analyst. Use your knowledge to check "
                         f"if the following information is contained in the provided yaml file. Information: {recorded_note}",
            model="gpt-4o",
            tools=[{"type": "file_search"}],
        )

        # Create a vector store called "Financial Statements"
        vector_store = self.client.beta.vector_stores.create(name="Financial Statements")

        # Ready the files for upload to OpenAI
        file_streams = [open(self.yaml_file, "rb")]

        # Use the upload and poll SDK helper to upload the files, add them to the vector store,
        # and poll the status of the file batch for completion.
        file_batch = self.client.beta.vector_stores.file_batches.upload_and_poll(
            vector_store_id=vector_store.id, files=file_streams
        )

        # You can print the status and the file counts of the batch to see the result of this operation.
        print(file_batch.status)
        print(file_batch.file_counts)

        assistant = self.client.beta.assistants.update(
            assistant_id=assistant.id,
            tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
        )

        # Upload the user-provided file to OpenAI
        message_file = self.client.files.create(
            file=open("edgar/aapl-10k.pdf", "rb"), purpose="assistants"
        )

        # Create a thread and attach the file to the message
        thread = self.client.beta.threads.create(
            messages=[
                {
                    "role": "user",
                    "content": "How many shares of AAPL were outstanding at the end of October 2023?",
                    # Attach the new file to the message.
                    "attachments": [
                        {"file_id": message_file.id, "tools": [{"type": "file_search"}]}
                    ],
                }
            ]
        )

        # The thread now has a vector store with that file in its tool resources.
        print(thread.tool_resources.file_search)