from .utils import Config
from .models import createOpenAIModel
import threading
import requests
import truststore
from pathlib import Path
from pydantic import BaseModel


class Response(BaseModel):
    output: str = ''
    error: str = ''

class Executor:

    def __init__(self, model_info, prompt_info, vars_info):

        self.model_info = model_info
        self.prompt_info = prompt_info
        self.vars_info = vars_info

        truststore.inject_into_ssl()
        self.cert_path = str(Path(Config.DIR_HOME / 'certs/NIH-FULL.pem'))

    def execute(self):
        
        try:
            queryFunc = getattr(self, f'{self.model_info['func']}')
        except AttributeError:
            raise Exception(f'Could not access executor function {self.model_info['id']}')
        
        return dict(Response(**queryFunc()))

    def queryLLM(self):

        from langchain_openai import ChatOpenAI
        from langchain.prompts import ChatPromptTemplate
        from .utils import Config
        import httpx

        http_client = httpx.Client(verify=self.cert_path)

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
                http_client=http_client
             )
        
        model = createOpenAIModel(self.model_info['id'].split(':')[-1], **self.model_info['config'])

        prompt = ChatPromptTemplate.from_messages(
                    [
                        ("system", self.prompt_info['system']),
                        ("user", self.prompt_info['user'])
                    ]
        )

        response = (prompt | model).invoke(self.vars_info).content

        return {'output': response, 'error': ''}

    def queryToxPipeRAG(self):

        prompt = self.prompt_info['user'].format(**self.vars_info)

        model_params = '&'.join([f'{k}={v}' for k, v in self.model_info['config'].items()])
        url = f'{Config.env_config['TOXPIPE_API_HOST']}/rag/'

        response = requests.get(url=f"{url}?q={prompt}&{model_params}", verify=self.cert_path)
        if not response.ok: raise Exception(f'API url: {url}, query: {prompt}, Model params: {model_params}, Response status code: {response.status_code}, Response: {response.text}')
        res = response.json()

        return {'output': res.get('response', str(res)), 
                    'error': res.get('error', '')}

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
            res = response.json()

            return {'output': res.get('response', str(res)), 
                    'error': res.get('error', '')}