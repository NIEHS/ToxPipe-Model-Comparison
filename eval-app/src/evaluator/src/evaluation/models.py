from langchain_openai import ChatOpenAI
from .utils import Config

def createOpenAIModel(model_name, temperature=0, **kwargs):
    
    return ChatOpenAI(
        model=model_name,
        base_url=Config.env_config['AI_BASE_URL'],
        api_key=Config.env_config['AI_API_KEY'],
        temperature=temperature,
        max_tokens=None,
        timeout=None,
        max_retries=10,
        seed=1000,
        http_client=Config.http_client,
        **kwargs
        )