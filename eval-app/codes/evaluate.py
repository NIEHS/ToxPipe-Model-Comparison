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
from pydantic import BaseModel, Field
#from langsmith import traceable
from utils import Config
import json
from datetime import datetime
from uuid import uuid4
import sys

class SchemaForSemanticSimilarityEvaluation(BaseModel):
    '''
    Represents the response and reason for semantic similarity
    '''
    pass_: bool = Field(description="A boolean value to indicate if semantic similarity was found")
    reason: str = Field(description="Text to describe the reason for semantic similarity")

class CustomOutputParser(JsonOutputParser):

    def __init__(self, schema=SchemaForSemanticSimilarityEvaluation):
        super().__init__(pydantic_object=schema)

    def parseResponse(self, data):
        
        try:
            response = self.parse(data.content)
            if not isinstance(response['pass_'], bool):
                response = {'pass_': False, 'reason': 'Error in data processing'}
        except:
            return {
                'pass_': False,
                'reason': 'Error in data processing'
            }    
        
        return {
                'pass_': response['pass_'],
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
                "pass_": false,
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
        
        model = createBaseModel({'id': 'openai:chat:azure-gpt-4o', 'config': {'temperature': 0}})

        passed = True
        component_results = []
        for res_exp in self.assert_info[0]['expected_phrases']:
            res_ = dict((self.prompt_question | model.with_structured_output(SchemaForSemanticSimilarityEvaluation)).invoke(input={'query': prompt, 'answer': response, 'phrase': res_exp}))
            passed &= res_['pass_']
            component_results.append({'pass': res_['pass_'], 'reason': res_['reason']})

        response = {
            'pass': passed,
            'score': int(passed),
            'reason': 'All assertions passed' if passed else 'All assertions did not pass',
            'componentResults': component_results
        }
        
        return response

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

def createBaseModel(model_info):
    if model_info['id'].startswith('openai:chat'):
        return createOpenAIModel(model_info['id'].split(':')[-1], **model_info['config'])
    raise NotImplementedError(model_info['id'])

class SchemaForQueryResponse(BaseModel):
    '''
    Represents the response of user query
    '''
    response: str = Field(description="Text to represent the response to user query")

def queryBaseModel(model_info, prompt_info, vars_info):
    model = createBaseModel(model_info=model_info)
    prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", prompt_info['system']),
                    ("user", prompt_info['user'])
                ]
    )

    # Langchain still does not have structured output facility for Mistral and LLama models, so rolling back to
    # old code. Will use this later when Langchain adds the facilities. 
    #response = dict((prompt | model.with_structured_output(SchemaForQueryResponse)).invoke(vars_info))['response']
    response = (prompt | model).invoke(vars_info).content
    
    return {'output': response}

def queryToxpipe(type, prompt, model_config):
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
        res = response.json()

        # From RAG: response is {'response': {'response': '', 'error': '', 'searched_keywords': ''}}
        if type == 'rag':
            if len(res['response']['error'].strip()) > 0:
                return {'output': res['response']['response'], 
                        'error': f'Error from Toxpipe: {res['response']['error']}', 
                        'searched_keyphrases': res['response']['searched_keyphrases'],
                        'steps_taken': res['response']['steps_taken']}
            return {'output': res['response']['response'], 
                    'searched_keyphrases': res['response']['searched_keyphrases'],
                    'steps_taken': res['response']['steps_taken']}

        # From AGENTIC: response is {'response': ''}        
        return {'output': res['response']}

def getModelResponse(model_info, prompt_info, vars_info):

    try:
        if model_info['id'] not in ['agentic', 'rag']:
            response = queryBaseModel(model_info, prompt_info, vars_info)
        else:
            response = queryToxpipe(type=model_info['id'], model_config=model_info['config'], prompt=prompt_info['user'].format(**vars_info))
        
    except Exception as exp:
        error = f'Line number: {exp.__traceback__.tb_lineno}, Description: {exp}\n\n{traceback.format_exc()}'
        print(error)
        return {'output': '', 'error': error}
    
    return response

def getEvaluationResponse(assert_info, response, prompt):
    
    try:
        return EvaluateResponse(assert_info=assert_info).getEvaluation(response=response, prompt=prompt)
    except Exception as exp:
        error = f'Line number: {exp.__traceback__.tb_lineno}, Description: {exp}\n\n{traceback.format_exc()}'
        print(error)
        return {'output': '', 'error': f'Error in evaluation: {error}'}

#@traceable
def getResponseAndEvaluate(model_info, prompt_info, vars_info, assert_info):

    response = getModelResponse(model_info, prompt_info, vars_info)
    response['results'] = getEvaluationResponse(assert_info=assert_info, response=response, prompt=prompt_info['user']) if len(assert_info) > 0 else {}

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

    list_output_file_path = sorted(list(dir_output.glob('output_*.json')), key=lambda x: int(x.stem.split('_')[-1]))

    for output_partial_path in list_output_file_path:

        output = {}
        eval_sets, descs, indices = [], [], []
        eval_sets_eval, descs_eval, indices_eval = [], [], []

        with open(output_partial_path) as f:
            output = json.load(f)

        if 'tests' not in output: return {}

        for index, t in enumerate(output['tests']):
            is_response_error = (('error' in t['response'] and len(t['response']['error'].strip()) > 0) or 
                                (not isinstance(t['response']['output'], str)) or 
                                t['response']['output'].strip() == '' or 
                                t['response']['output'].lower().startswith('error'))
            is_eval_error = (len(t['assert']) > 0 and ('results' not in t['response'] or 
                                                            len(t['response']['results']) == 0 or 
                                                            'error' in t['response']['results']))
            
            if is_response_error or is_eval_error:
                
                model_info = t['provider']
                prompt = t['prompt']
                prompt_info = {'system': output['system_prompt'], 'user': prompt}
                vars_info = t['vars']
                assert_info = t['assert']
                
                if is_response_error: 
                    descs.append(f"{model_info['label']} - {prompt[:30]}")
                    eval_sets.append([model_info, prompt_info, vars_info, assert_info])
                    indices.append(index)      
                elif is_eval_error:
                    descs_eval.append(f"{model_info['label']} - {prompt[:30]}")
                    eval_sets_eval.append([assert_info, t['response']['output'], prompt_info['user']])
                    indices_eval.append(index)
        
        if not (len(eval_sets) or len(eval_sets_eval)): continue

        print(f'Processing {output_partial_path.name}')

        with concurrent.futures.ThreadPoolExecutor(20) as pool:
            if eval_sets: 
                results = pool.map(getResponseAndEvaluate, *zip(*eval_sets))
                for i, res in enumerate(pbar := tqdm.tqdm(results, total=len(eval_sets), bar_format="{desc:<32.30}{percentage:3.0f}%|{bar:50}{r_bar}")):
                    pbar.set_description(descs[i])
                    output['tests'][indices[i]]['response'] = res
            if eval_sets_eval:
                results = pool.map(getEvaluationResponse, *zip(*eval_sets_eval))
                for i, res in enumerate(pbar := tqdm.tqdm(results, total=len(eval_sets_eval), bar_format="{desc:<32.30}{percentage:3.0f}%|{bar:50}{r_bar}")):
                    pbar.set_description(descs_eval[i])
                    output['tests'][indices_eval[i]]['response']['results'] = res

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