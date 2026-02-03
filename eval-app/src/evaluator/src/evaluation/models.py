from langchain_openai import ChatOpenAI
from .utils import Config
import truststore
from pathlib import Path
import httpx

truststore.inject_into_ssl()
cert_path = str(Path(Config.DIR_HOME / 'certs/NIH-FULL.pem'))
http_client = httpx.Client(verify=cert_path)

def createOpenAIModel(model_name, temperature=0, **kwargs):
    
    return ChatOpenAI(
        model=model_name,
        base_url=Config.env_config['AI_BASE_URL'],
        api_key=Config.env_config['AI_API_KEY'],
        temperature=temperature,
        max_tokens=99999,
        timeout=None,
        max_retries=10,
        seed=1000,
        http_client=http_client,
        **kwargs
        )