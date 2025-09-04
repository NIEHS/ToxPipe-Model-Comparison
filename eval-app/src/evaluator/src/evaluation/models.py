from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langsmith import traceable
import threading
from pathlib import Path
from .utils import Config
import requests

import httpx
import truststore
truststore.inject_into_ssl()
cert_path = str(Path(Config.DIR_HOME / 'certs/NIH-FULL.pem'))
client = httpx.Client(verify=cert_path)

def createOpenAIModel(model_name, temperature):
    
    return ChatOpenAI(
        model=model_name,
        base_url=Config.env_config['AI_BASE_URL'],
        api_key=Config.env_config['AI_API_KEY'],
        temperature=temperature,
        max_tokens=None,
        timeout=None,
        max_retries=10,
        seed=1000,
        http_client=client
    )

def createBaseModel(model_info):
    if model_info['id'].startswith('openai:chat'):
        return createOpenAIModel(model_info['id'].split(':')[-1], **model_info['config'])
    raise NotImplementedError(model_info['id'])

#@traceable
def queryBaseModel(model_info, prompt_info, vars_info):
    model = createBaseModel(model_info=model_info)
    prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", prompt_info['system']),
                    ("user", prompt_info['user'])
                ]
    )

    response = (prompt | model).invoke(vars_info).content
    
    return {'output': response}

def queryToxpipe(type, prompt, model_config):
    if type == 'rag':
        model_params = '&'.join([f'{k}={v}' for k, v in model_config.items()])
        url = f'{Config.env_config['TOXPIPE_API_HOST']}/rag/'
        
        response = requests.get(url=f"{url}?{model_params}&q={prompt}", verify=cert_path)
        if not response.ok: raise Exception(f'API url: {url}, Model params: {model_params}, Response status code: {response.status_code}, Response: {response.text}')
        res = response.json()['response']

        # From RAG: response is {'response': {'response': '', 'searched_keywords': '', 'steps_taken': '', 'error': ''}}
        for k in ['response', 'searched_keyphrases', 'steps_taken', 'error']:
            if k not in res:
                raise Exception(res)
        if len(res['error'].strip()) > 0:
            return {'output': res['response'], 
                    'error': f'Error from Toxpipe: {res['error']}', 
                    'searched_keyphrases': res['searched_keyphrases'],
                    'steps_taken': res['steps_taken']}
        
        return {'output': res['response'], 
                'searched_keyphrases': res['searched_keyphrases'],
                'steps_taken': res['steps_taken']}

    with threading.Lock():
        model_params = '&'.join([f'{k}={v}' for k, v in model_config.items()])
        url = f'{Config.env_config['TOXPIPE_API_HOST']}/agent/create/'
        response = requests.get(url=f"{url}?{model_params}", verify=cert_path, timeout=None)
        if not response.ok: raise Exception(response.text)
        agentid = response.json()['agentid']
        
        url = f'{Config.env_config['TOXPIPE_API_HOST']}/agent/query/?agentid={agentid}&q={prompt}'

        response = requests.get(url=url, verify=cert_path, timeout=None)
        if not response.ok: raise Exception(f'API url: {url}, Model params: {model_params}, Response status code: {response.status_code}, Response: {response.text}')
        res = response.json()['response']

        # From AGENTIC: response is {'response': ''}        
        return {'output': res}