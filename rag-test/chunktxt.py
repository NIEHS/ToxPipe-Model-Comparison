import os

OPENAI_API_KEY = "secretkey"
AZURE_OPENAI_ENDPOINT = "endpoint"

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


RETRIES = 10

def main():
    query_model = AzureOpenAI(
        model="gpt-4o",
        deployment_name="azure-gpt-4o",
        api_key=OPENAI_API_KEY,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_version="2023-07-01-preview",
    )

    # embedding model
    embed_model = AzureOpenAIEmbedding(
        model="text-embedding-ada-002",
        deployment_name="text-embedding-ada-002",
        api_key=OPENAI_API_KEY,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_version="2023-07-01-preview",
    )
    Settings.embed_model = embed_model

    #"""
    # Chroma vector store
    db = chromadb.PersistentClient(path="./chroma_db")
    chroma_collection = db.get_or_create_collection("quickstart")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    print("here 1")

    reader = SimpleDirectoryReader(input_dir="./reports")
    #documents = reader.load_data(show_progress=True, num_workers=16) # multicore
    documents = reader.load_data(show_progress=True)

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

    # was processing one doc at a time in a loop to bypass rate limit
    for d in documents:

        # run the pipeline
        try:
            nodes = pipeline.run(documents=[d], show_progress=False)

            print("! success!")
        except Exception as e:
            print("! error outer")
            print(e)
            for i in range(0, RETRIES):
                print(f"Retrying {i}")
                sleep(3)
                try:
                    nodes = pipeline.run(documents=[d], show_progress=True)
                    break
                except Exception as e2:
                    print("! error inner")
                    print(e2)
                    continue
            # If still doesn't work after retries, skip
            print("Skipping...")
            continue

    print("here 3")


    index = VectorStoreIndex.from_vector_store(vector_store, storage_context=storage_context, show_progress=True)


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
    response = query_engine.query("Does the chemical DTXSID20583385 function as an inhibitor? Give me the source for this information. Do not skip the source.")
    print(response)

    """

if __name__ == '__main__':
    freeze_support()
    main()