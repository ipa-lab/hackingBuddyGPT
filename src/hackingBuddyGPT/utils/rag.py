import os

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import MarkdownTextSplitter


def initiate_rag():
    load_dotenv()

    # Define the persistent directory
    rag_storage_path = os.path.abspath(os.path.join("..", "usecases", "rag", "rag_storage"))
    persistent_directory = os.path.join(rag_storage_path, "vector_storage", os.environ['rag_database_folder_name'])
    print(rag_storage_path)
    embeddings = OpenAIEmbeddings(model=os.environ['rag_embedding'], api_key=os.environ['openai_api_key'])

    markdown_splitter = MarkdownTextSplitter(chunk_size=1000, chunk_overlap=0)

    if not os.path.exists(persistent_directory):
        doc_manager_1 = DocumentManager(os.path.join(rag_storage_path, "GTFObinMarkdownFiles"))
        doc_manager_1.load_documents()

        doc_manager_2 = DocumentManager(os.path.join(rag_storage_path, "hacktricksMarkdownFiles"))
        doc_manager_2.load_documents()
        documents_hacktricks = markdown_splitter.split_documents(doc_manager_2.documents)

        all_documents = doc_manager_1.documents + documents_hacktricks
        print(f"\n--- Creating vector store in {persistent_directory} ---")
        db = Chroma.from_documents(all_documents, embeddings, persist_directory=persistent_directory)
        print(f"--- Finished creating vector store in {persistent_directory} ---")
    else:
        print(f"Vector store {persistent_directory} already exists. No need to initialize.")
        db = Chroma(persist_directory=persistent_directory, embedding_function=embeddings)

    retriever = db.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 10},
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

