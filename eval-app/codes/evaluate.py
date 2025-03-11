import requests
from typing import Dict, Any, Union
import dotenv
from pathlib import Path
import yaml
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import threading
import concurrent.futures
import tqdm
import traceback
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel
#from langsmith import traceable
from utils import Config
import json
from datetime import datetime
from uuid import uuid4
import sys

class SchemaForSimilaritySearch(BaseModel):
    response: bool

class CustomOutputParser(JsonOutputParser):

    def __init__(self, schema=SchemaForSimilaritySearch):
        super().__init__(pydantic_object=schema)

    def parseResponse(self, data):
        
        try:
            response = self.parse(data.content)
            if not isinstance(response['response'], bool):
                response = {'response': False, 'reason': 'Error in data processing'}
        except:
            return {
                'pass': False,
                'reason': 'Error in data processing'
            }    
        
        return {
                'pass': response['response'],
                'reason': response['reason']
        }

class EvaluateResponse:

    prompt_template = '''
    You will be provided a ANSWER to a QUERY and a PHRASE. Assess the QUERY, ANSWER and PHRASE. 
    Check if the ANSWER is similar to the PHRASE and relevant to the QUERY. The PHRASE does not necessarily have to be in the ANSWER, but the PHRASE at least need to be semantically similar to the ANSWER.

    Provide your ANSWER with boolean response and a reason with string format.

    ** Rules **
    - DO NOT MAKE UP ANYTHING. USE ONLY THE QUERY, ANSWER AND PHRASE PROVIDED.

    ** QUERY **
    {query}

    ** ANSWER **
    {answer}

    ** PHRASE **
    {phrase}
    '''

    prompt_question = ChatPromptTemplate.from_messages(
        [
            ("system", 
            """
            You are an expert in toxicology and the effects of chemicals on human health.

            ** RULES ** 
            - Make sure you return a valid JSON output
            - Always respond in the following JSON format:

            ```json
            {{
                "response": false,
                "reason": "An appropriate reason"
            }}
            ```
            """),
            ("user", prompt_template)
        ]
    )

    def __init__(self, assert_info):
        self.assert_info = assert_info

    def getEvaluation(self, response: str, prompt: str) -> Union[bool, float, Dict[str, Any]]:
        
        model = createRawModel({'id': 'openai:chat:azure-gpt-4o', 'config': {'temperature': 0}})
        output_parser = CustomOutputParser()

        passed = True
        component_results = []
        for res_exp in self.assert_info[0]['expected_phrases']:
            res_ = (self.prompt_question | model | output_parser.parseResponse).invoke(input={'query': prompt, 'answer': response, 'phrase': res_exp})
            passed &= res_['pass']
            component_results.append(res_)

        response = {
            'pass': passed,
            'score': int(passed),
            'reason': 'All assertions passed' if passed else 'All assertions did not pass',
            'componentResults': component_results
        }
        
        return response

def callAgenticToxpipe(type, prompt, model_config):
    with threading.Lock():
        model_params = '&'.join([f'{k}={v}' for k, v in model_config.items()])
        
        url = f'{env_config['TOXPIPE_API_HOST']}/agent/create/'
        response = requests.get(url=f"{url}?{model_params}")
        if not response.ok: raise Exception(response.text)
        agentid = response.json()['agentid']
        
        if type == 'rag':
            url = f'{env_config['TOXPIPE_API_HOST']}/agent/rag/?agentid={agentid}&q={prompt}'
        else:
            url = f'{env_config['TOXPIPE_API_HOST']}/agent/query/?agentid={agentid}&q={prompt}'
        response = requests.get(url=url)
        if not response.ok: raise Exception(f'API url: {url}, Response status code: {response.status_code}, Response: {response.text}')
        return response.json()['response']

def createOpenAIModel(model_name, temperature):

    return ChatOpenAI(
        model=model_name,
        base_url=env_config['OPENAI_BASE_URL'],
        api_key=env_config['OPENAI_API_KEY'],
        temperature=temperature,
        max_tokens=None,
        timeout=None,
        max_retries=10,
        seed=1000
    )

def createRawModel(model_info):
    if model_info['id'].startswith('openai:chat'):
        return createOpenAIModel(model_info['id'].split(':')[-1], **model_info['config'])
    raise NotImplementedError(model_info['id'])

def getModelResponse(model_info, prompt_info, vars_info):

    try:
        if model_info['id'] in ['agentic', 'rag']:
            output = callAgenticToxpipe(type=model_info['id'], model_config=model_info['config'], prompt=prompt_info['user'].format(**vars_info))
        else:
            model = createRawModel(model_info=model_info)
            prompt = ChatPromptTemplate.from_messages(
                        [
                            ("system", prompt_info['system']),
                            ("user", prompt_info['user'])
                        ]
            )
            output = (prompt | model).invoke(vars_info).content
        
    except Exception as exp:
        print(f'Line number: {exp.__traceback__.tb_lineno}, Description: {exp}\n\n{traceback.format_exc()}')
        return {'output': '', 'error': str(exp)}
    
    return {'output': output}

#@traceable
def evaluate(model_info, prompt_info, vars_info, assert_info):
    
    response = getModelResponse(model_info, prompt_info, vars_info)
    response['results'] = []
    if len(assert_info) > 0:
        prompt = prompt_info['user'].format(**vars_info)
        try:
            response['results'] = EvaluateResponse(assert_info=assert_info).getEvaluation(response=response, prompt=prompt)
        except Exception as exp:
            print(f'Line number: {exp.__traceback__.tb_lineno}, Description: {exp}\n\n{traceback.format_exc()}')
            response['results'] = {'output': '', 'error': f'Error in evaluation: {exp}'}

    return response

def loadYML(file_path):
    data = None
    with open(file_path) as stream:
        try:
            data = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
    return data

def writeJSON(output_path, data):
    with open(output_path, 'w') as f:
        json.dump(data, f)

def resumeLastRun(dir_output):

    for output_partial_path in dir_output.glob('output_*.json'):

        output, eval_sets, descs, indices = {}, [], [], []

        with open(output_partial_path) as f:
            output = json.load(f)

        if 'tests' not in output: return {}

        for index, t in enumerate(output['tests']):
            if 'error' in t['response'] or t['response']['output'].strip() == '':
                model_info = t['provider']
                prompt = t['prompt']
                prompt_info = {'system': output['system_prompt'], 'user': prompt}
                vars_info = t['vars']
                assert_info = t['assert']
                descs.append(f"{model_info['label']} - {prompt[:30]}")
                eval_sets.append([model_info, prompt_info, vars_info, assert_info])
                indices.append(index)
        
        if not len(eval_sets): continue

        with concurrent.futures.ProcessPoolExecutor() as pool: 
            results = pool.map(evaluate, *zip(*eval_sets))
            for i, res in enumerate(pbar := tqdm.tqdm(results, total=len(eval_sets), bar_format="{desc:<32.30}{percentage:3.0f}%|{bar:50}{r_bar}")):
                pbar.set_description(descs[i])
                output['tests'][indices[i]]['response'] = res

        writeJSON(output_path=output_partial_path, data=output)

def runTest(config_path, resume=False):

    dir_output = config_path.parent / 'output'
    dir_output.mkdir(parents=False, exist_ok=True)

    if not resume:

        for f in dir_output.glob('output_*.json'):
            f.unlink()

        config = loadYML(config_path)

        index = 0
        eventid = datetime.now().strftime('%Y%m-%d%H-%M%S-') + str(uuid4())
        output = {'id': eventid, 'system_prompt': config['system_prompt'], 'tests': []}

        for model_info in config['providers']:
            for prompt in config['prompts']:
                prompt_info = {'system': config['system_prompt'], 'user': prompt}
                for test in config['tests']:
                    vars_info = test['vars']
                    assert_info = test['assert'] if 'assert' in test else {}

                    output['tests'].append({'provider': model_info, 'prompt': prompt_info['user'], 'vars': vars_info, 'assert': assert_info, 'response': {'output': ''}})

                    if len(output['tests']) >= 50:
                        writeJSON(output_path=dir_output / f'output_{index}.json', data=output)
                        output = {'id': eventid, 'system_prompt': config['system_prompt'], 'tests': []}
                        index += 1

        if len(output['tests']):
            writeJSON(output_path=dir_output / f'output_{index}.json', data=output)

    resumeLastRun(dir_output)

env_config = dotenv.dotenv_values(Path(__file__).parent.parent / ".env")

if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[2] == 'r':
        runTest(Config.DIR_TEST / sys.argv[1] / 'config.yaml', resume=True)
    else:
        runTest(Config.DIR_TEST / sys.argv[1] / 'config.yaml', resume=False)