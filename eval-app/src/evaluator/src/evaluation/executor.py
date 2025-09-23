from .utils import Config
from .models import createOpenAIModel
from langchain.prompts import ChatPromptTemplate
from langsmith import traceable
import threading
import requests
import httpx
import truststore
from pathlib import Path

class Executor:

    def __init__(self, model_info, prompt_info, vars_info):

        self.model_info = model_info
        self.prompt_info = prompt_info
        self.vars_info = vars_info

        truststore.inject_into_ssl()
        self.cert_path = str(Path(Config.DIR_HOME / 'certs/NIH-FULL.pem'))

    def execute(self):
        
        if self.model_info['id'].startswith('llm'):
            return self.queryLLM()
        try:
            queryFunc = getattr(self, f'query{self.model_info['id']}')
        except AttributeError:
            raise Exception(f'Could not access executor function {self.model_info['id']}')
        
        return queryFunc()

    #@traceable
    def queryLLM(self):
        
        model = createOpenAIModel(self.model_info['id'].split(':')[-1], **self.model_info['config'])

        prompt = ChatPromptTemplate.from_messages(
                    [
                        ("system", self.prompt_info['system']),
                        ("user", self.prompt_info['user'])
                    ]
        )

        response = (prompt | model).invoke(self.vars_info).content
        
        return {'output': response}

    def queryToxPipeRAG(self):

        prompt = self.prompt_info['user'].format(**self.vars_info)

        model_params = '&'.join([f'{k}={v}' for k, v in self.model_info['config'].items()])
        url = f'{Config.env_config['TOXPIPE_API_HOST']}/rag/'
        
        response = requests.get(url=f"{url}?{model_params}&q={prompt}", verify=self.cert_path)
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

    def queryToxPipeAgentic(self):

        prompt = self.prompt_info['user'].format(**self.vars_info)

        with threading.Lock():
            
            model_params = '&'.join([f'{k}={v}' for k, v in self.model_info['config'].items()])
            url = f'{Config.env_config['TOXPIPE_API_HOST']}/agent/create/'
            response = requests.get(url=f"{url}?{model_params}", verify=self.cert_path, timeout=None)
            if not response.ok: raise Exception(response.text)
            agentid = response.json()['agentid']
            
            url = f'{Config.env_config['TOXPIPE_API_HOST']}/agent/query/?agentid={agentid}&q={prompt}'

            response = requests.get(url=url, verify=self.cert_path, timeout=None)
            if not response.ok: raise Exception(f'API url: {url}, Model params: {model_params}, Response status code: {response.status_code}, Response: {response.text}')
            res = response.json()['response']

            # From AGENTIC: response is {'response': ''}        
            return {'output': res}