import os
OPENAI_API_KEY = "secret-key"
AZURE_OPENAI_ENDPOINT = "endpoint"

# This forces chromadb to use the newer sqlite version provided by the package rather than the version on the machine
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
os.environ["AZURE_OPENAI_ENDPOINT"] = AZURE_OPENAI_ENDPOINT

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext
from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.extractors import TitleExtractor, SummaryExtractor, QuestionsAnsweredExtractor, KeywordExtractor
from llama_index.core.ingestion import IngestionPipeline, IngestionCache
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding
from llama_index.core import Settings
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb
from multiprocessing import freeze_support

from time import sleep

from sentence_transformers import SentenceTransformer

from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding

RETRIES = 10

def main():

    print("start")

    query_model = Ollama(model="qwen2:72b", request_timeout=999.9, base_url=AZURE_OPENAI_ENDPOINT)
    embed_model = OllamaEmbedding(model_name="mxbai-embed-large:latest", base_url=AZURE_OPENAI_ENDPOINT)

    print("models")

    Settings.embed_model = embed_model

    #"""

    # Chroma vector store
    db = chromadb.PersistentClient(path="./chroma_db")
    chroma_collection = db.get_or_create_collection("quickstart")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    print("here 1")

    reader = SimpleDirectoryReader(input_dir="./chembl_docs")
    documents = reader.load_data(show_progress=True, num_workers=32)
    print("here 2")

    print(len(documents))

    # create the pipeline with transformations
    pipeline = IngestionPipeline(
        transformations=[
            SentenceSplitter(chunk_size=1000, chunk_overlap=128),
            TitleExtractor(llm=query_model),
            SummaryExtractor(llm=query_model),
            QuestionsAnsweredExtractor(llm=query_model),
            KeywordExtractor(llm=query_model),
            embed_model,
        ],
        vector_store=vector_store,
    )


    # run the pipeline
    nodes = pipeline.run(documents=documents, show_progress=True, num_workers=32)

    print("here 3")

    index = VectorStoreIndex.from_vector_store(vector_store, storage_context=storage_context, show_progress=True)

    #print("===index===")
    #print(index)

    """

    # load from disk
    db2 = chromadb.PersistentClient(path="./chroma_db")
    chroma_collection = db2.get_or_create_collection("quickstart")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    index = VectorStoreIndex.from_vector_store(
        vector_store,
        embed_model=embed_model,
    )

    # Query Data from the persisted index
    query_engine = index.as_query_engine(
        llm=query_model
    )

    res = query_engine.query("What do you know about P-gp?")

    print(res)

    """

if __name__ == '__main__':
    freeze_support()
    main()
