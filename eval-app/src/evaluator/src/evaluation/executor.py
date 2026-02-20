from .utils import Config
from .models import createOpenAIModel
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware
import threading
import requests
import truststore
from pathlib import Path
from pydantic import BaseModel
import asyncio

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
            queryFunc = getattr(self, self.model_info['func'])
            if self.model_info['func'] == 'queryToxPipeMCP':
                result = asyncio.run(queryFunc())
            else:
                result = queryFunc()
        except AttributeError:
            raise Exception(f'Could not access executor function {self.model_info['id']}')
        
        return dict(Response(**result))

    def queryLLM(self):

        from langchain_core.prompts import ChatPromptTemplate
        
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
        api_key = Config.env_config.get('TOXPIPE_API_API_KEY', '')
        headers = { "Authorization": f"Bearer {api_key}" } if api_key else {}
        response = requests.get(url=f"{url}?q={prompt}&{model_params}", headers=headers, verify=self.cert_path)
        if not response.ok: raise Exception(f'API url: {url}, query: {prompt}, Model params: {model_params}, Response status code: {response.status_code}, Response: {response.text}')
        res = response.json()

        return {'output': res.get('response', str(res)), 
                    'error': res.get('error', '')}
    
    async def queryToxPipeMCP(self):

        model = createOpenAIModel(self.model_info['id'].split(':')[-1], **self.model_info['config'])

        client = MultiServerMCPClient(
            {
                "ToxPipeMCPServers": {
                    "transport": "http",
                    "url": Config.env_config['TOXPIPE_MCP_SERVER_URL'],
                }
            }
        )
        
        try:
            tools = await asyncio.wait_for(client.get_tools(), timeout=Config.TIMEOUT_SHORT_TASK)
        except asyncio.TimeoutError:
            result = ''
            error = f'Error: MCP tools took too much time (> {Config.TIMEOUT_SHORT_TASK} seconds). Please check your connection with the MCP server.'
            return {"output": result, "error": error}

        user_prompt = self.prompt_info['user'].format(**self.vars_info)
        agent = create_agent(model=model, 
                             tools=tools, 
                             system_prompt=self.prompt_info['system'],
                             middleware=[
                                 ToolCallLimitMiddleware(
                                    run_limit=3,
                                    thread_limit=3
                                )
                            ]
                )
        
        try:
            result = await asyncio.wait_for(agent.ainvoke({'messages': [{'role': 'user', 'content': user_prompt}]}), timeout=Config.TIMEOUT_LONG_TASK)
            ai_messages = []
            for msg in result['messages'][:-1]: 
                if msg.type != 'ai': continue
                tool_messages = '\n'.join([f'[{i+1}] {msg_tool["name"]}, args: {", ".join([f"{k}: {v}" for k, v in msg_tool["args"].items()])}' for i, msg_tool in enumerate(msg.tool_calls)])
                ai_messages.append(f'{msg.content}\n\n*Tools called:*\n{tool_messages}')
            result = result['messages'][-1].content + '\n\n---\n\n**Agent Messages**\n\n' + '\n\n'.join(ai_messages)
            error = ''
        except asyncio.TimeoutError:
            result = ''
            error = f'Error: MCP agent took too much time (> {Config.TIMEOUT_LONG_TASK} seconds). Please check your connection with the MCP server.'
        except Exception as e:
            result = ''
            error = f"Error: query failed to run with message: {e}."

        return {"output": result, "error": error}

    def queryToxPipeAgentic(self):

        prompt = self.prompt_info['user'].format(**self.vars_info)

        with threading.Lock():
            
            model_params = '&'.join([f'{k}={v}' for k, v in self.model_info['config'].items()])
            url = f'{Config.env_config['TOXPIPE_API_HOST']}/agent/create/'

            response = requests.get(url=f"{url}?{model_params}", verify=self.cert_path, timeout=None)
            if not response.ok: raise Exception(response.text)
            
            agentid = response.json()['agentid']
            url = f'{Config.env_config['TOXPIPE_API_HOST']}/agent/query/?agentid={agentid}&q={prompt}'
            api_key = Config.env_config.get('TOXPIPE_API_API_KEY', '')
            headers = { "Authorization": f"Bearer {api_key}" } if api_key else {}
            response = requests.get(url=url, headers=headers, verify=self.cert_path, timeout=None)
            if not response.ok: raise Exception(f'API url: {url}, Model params: {model_params}, Response status code: {response.status_code}, Response: {response.text}')
            res = response.json()

            return {'output': res.get('response', str(res)), 
                    'error': res.get('error', '')}