import os

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

def initiate_rag():
    load_dotenv()

    # Define the persistent directory
    rag_storage_path = os.path.abspath(os.path.join("..", "..", "..", "rag_storage"))
    persistent_directory = os.path.join(rag_storage_path, "vector_storage", os.environ['rag_database_folder_name'])

    embeddings = OpenAIEmbeddings(model=os.environ['rag_embedding'], api_key=os.environ['openai_api_key'])

    if not os.path.exists(persistent_directory):
        doc_manager = DocumentManager(os.path.join(rag_storage_path, "GTFObinMarkdown"))
        doc_manager.load_documents()
        print(f"\n--- Creating vector store in {persistent_directory} ---")
        db = Chroma.from_documents(doc_manager.documents, embeddings, persist_directory=persistent_directory)
        print(f"--- Finished creating vector store in {persistent_directory} ---")
    else:
        print(f"Vector store {persistent_directory} already exists. No need to initialize.")
        db = Chroma(persist_directory=persistent_directory, embedding_function=embeddings)

    retriever = db.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 3},
    )

    return retriever

class DocumentManager:
    def __init__(self, directory_path, glob_pattern="./*.md"):
        self.directory_path = directory_path
        self.glob_pattern = glob_pattern
        self.documents = []

    def load_documents(self):
        loader = DirectoryLoader(self.directory_path, glob=self.glob_pattern, show_progress=True, loader_cls=TextLoader)
        self.documents = loader.load()

