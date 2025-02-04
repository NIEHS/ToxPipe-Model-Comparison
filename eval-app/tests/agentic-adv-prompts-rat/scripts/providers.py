import requests
from typing import Optional, Dict, Any, Union, List
import dotenv
from pathlib import Path

env_config = dotenv.dotenv_values(Path(__file__).parent.parent / ".env")

class TokenUsage:
    total: int
    prompt: int
    completion: int

class ProviderResponse:
    output: Optional[Union[str, Dict[str, Any]]]
    error: Optional[str]
    tokenUsage: Optional[TokenUsage]
    cost: Optional[float]
    cached: Optional[bool]
    logProbs: Optional[List[float]]

def call_toxpipe_api(prompt, model, temp=0, max_iterations=10, summarize='false', **kargs):
    
    url = f'{env_config['TOXPIPE_API_HOST']}/agent/create/'
    response = requests.get(url=f"{url}?model={model}&temp={temp}&max_iterations={max_iterations}&summarize={summarize}")
    if not response.ok: raise Exception(response.text)
    agentid = response.json()['agentid']

    url = f'{env_config['TOXPIPE_API_HOST']}/agent/query/'
    response = requests.get(url=f"{url}?agentid={agentid}&q={prompt}")
    if not response.ok: raise Exception(response.text)
    return response.json()['response']

def call_api(prompt: str, options:Dict[str, Any], context:Dict[str, Any]) -> ProviderResponse:

    config = options.get('config', None)
    
    try:
        output = call_toxpipe_api(prompt=prompt, **config)
    except Exception as exp:
        return {'output': '', 'error': str(exp)}
    
    return {'output': output}