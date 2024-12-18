import sys
import json
import requests
from tqdm import tqdm
from codes.utils import Config

def reqEmbedding(text, embedding):

    response = requests.post(
                url="https://litellm.toxpipe.niehs.nih.gov/embeddings",
                headers={
                    "Authorization": f"Bearer {Config.env_config['OPENAI_API_KEY']}",
                    "Content-Type": "application/json"},
                json={
                    "input": text,
                    "model": embedding,
                    "encoding_format": "float"}
    )

    if response.ok: return response.json()['data'][0]['embedding']
    print(response.text)

def generateSimilarity(dir_):

    with open(dir_ / 'output.json', 'r') as f:
        config = json.load(f)

    results = {}
    embedding_models = ['text-embedding-ada-002', 'text-embedding-3-small', 'ollama-nomic-embed-text']
    for embedding in embedding_models:
        print(embedding)
        results[embedding] = {f"{item['testIdx']}|{item['provider']['label']}": reqEmbedding(item['response']['output'], embedding=embedding) for item in tqdm(config['results']['results'])}

    with open(dir_ / 'response_embeddings.json', 'w') as outfile:
        json.dump(results, outfile)

if __name__ == '__main__':
    dir_ = Config.DIR_TEST / sys.argv[1]
    generateSimilarity(dir_)