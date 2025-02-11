import requests
from typing import Optional, Dict, Any, Union, List
import dotenv
from pathlib import Path
import yaml
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import multiprocessing
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
import os

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

    def __init__(self, expected_phrases):
        self.expected_phrases = expected_phrases

    def getEvaluation(self, response: str, prompt: str) -> Union[bool, float, Dict[str, Any]]:
        
        model = createRawModel({'id': 'openai:chat:azure-gpt-4o', 'config': {'temperature': 0}})
        output_parser = CustomOutputParser()

        passed = True
        component_results = []
        for res_exp in self.expected_phrases:
            try:
                res_ = (self.prompt_question | model | output_parser.parseResponse).invoke(input={'query': prompt, 'answer': response, 'phrase': res_exp})
            except Exception as exp:
                print(f'Line number: {exp.__traceback__.tb_lineno}, Description: {exp}\n\n{traceback.format_exc()}')
                raise exp
            passed &= res_['pass']
            component_results.append(res_)

        response = {
            'pass': passed,
            'score': int(passed),
            'reason': 'All assertions passed' if passed else 'All assertions did not pass',
            'componentResults': component_results
        }
        
        return response

def callAgenticToxpipe(prompt, model_config):
    
    model_params = '&'.join([f'{k}={v}' for k, v in model_config.items()])

    url = f'{env_config['TOXPIPE_API_HOST']}/agent/create/'
    response = requests.get(url=f"{url}?{model_params}")
    if not response.ok: raise Exception(response.text)
    agentid = response.json()['agentid']

    url = f'{env_config['TOXPIPE_API_HOST']}/agent/query/?agentid={agentid}&q={prompt}'
    response = requests.get(url=url)
    if not response.ok: raise Exception(f'API url: {url}, Response: {response.text}')
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

    if model_info['id'] == 'file://scripts/providers.py':
        try:
            output = callAgenticToxpipe(model_config=model_info['config'], prompt=prompt_info['user'].format(**vars_info))
        except yaml.YAMLError as exp:
            print(f'Line number: {exp.__traceback__.tb_lineno}, Description: {exp}\n\n{traceback.format_exc()}')
            return {'output': '', 'error': str(exp)}
        return {'output': output}

    model = createRawModel(model_info=model_info)

    prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", prompt_info['system']),
                    ("user", prompt_info['user'])
                ]
    )

    try:
        output = (prompt | model).invoke(vars_info).content
    except Exception as exp:
        print(f'Line number: {exp.__traceback__.tb_lineno}, Description: {exp}\n\n{traceback.format_exc()}')
        return {'output': '', 'error': str(exp)}
    
    return {'output': output}

#@traceable
def evaluate(model_info, prompt_info, vars_info, expected_phrases):
    
    response = getModelResponse(model_info, prompt_info, vars_info)
    response['results'] = []
    if len(expected_phrases) > 0:
        prompt = prompt_info['user'].format(**vars_info)
        response['results'] = EvaluateResponse(expected_phrases=expected_phrases).getEvaluation(response=response, prompt=prompt)

    return response

def loadYML(file_path):
    data = None
    with open(file_path) as stream:
        try:
            data = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
    return data

def runTest(config_path):
    config = loadYML(config_path)
    eval_sets, descs = [], []
    for model_info in config['providers']:
        for prompt in config['prompts']:
            prompt_info = {'system': config['system_prompt'], 'user': prompt}
            for test in config['tests']:
                vars_info = test['vars']
                expected_phrases = test['assert'][0]['expected_phrases'] if 'assert' in test and 'expected_phrases' in test['assert'][0] else []
                descs.append(f"{model_info['label']} - {prompt[:30]}")
                eval_sets.append([model_info, prompt_info, vars_info, expected_phrases])


    eventid = datetime.now().strftime('%Y%m-%d%H-%M%S-') + str(uuid4())

    output = {'id': eventid, 'system_prompt': config['system_prompt'], 'tests': []}

    with concurrent.futures.ThreadPoolExecutor(10) as pool: 
        results = pool.map(evaluate, *zip(*eval_sets))
        for i, res in enumerate(pbar := tqdm.tqdm(results, total=len(eval_sets), bar_format="{desc:<32.30}{percentage:3.0f}%|{bar:50}{r_bar}")):
            pbar.set_description(descs[i])
            output['tests'].append({'provider': eval_sets[i][0], 'prompt': eval_sets[i][1]['user'], 'vars': eval_sets[i][2], 'response': res})

    (config_path.parent / 'output').mkdir(parents=False, exist_ok=True)

    with open(config_path.parent / 'output' / 'output.json', 'w') as f:
        json.dump(output, f)

def convertOutput(output_path):
    output_prev = loadYML(output_path)

    eventid = datetime.now().strftime('%Y%m-%d%H-%M%S-') + str(uuid4())

    output = {
        'id': eventid,
        'system_prompt': '''
            You are an expert toxicologist with extensive knowledge in chemical safety assessment, 
            toxicokinetics, and toxicodynamics. Your expertise includes:

            1. Interpreting chemical structures and properties
            2. Analyzing toxicological data from various sources (e.g., in vitro, in vivo, and in silico studies)
            3. Applying read-across and QSAR (Quantitative Structure-Activity Relationship) approaches
            4. Understanding mechanisms of toxicity and adverse outcome pathways
            5. Evaluating systemic availability based on ADME (Absorption, Distribution, Metabolism, Excretion) properties
            6. Assessing potential health hazards and risks associated with chemical exposure

            When providing toxicological evaluations:
            - Use reliable scientific sources and databases (e.g., PubChem, ECHA, EPA, IARC)
            - Consider both experimental data and predictive models
            - Explain your reasoning and cite relevant studies or guidelines
            - Acknowledge uncertainties and data gaps
            - Provide a balanced assessment, considering both potential hazards and mitigating factors
            - Use a weight-of-evidence approach when multiple data sources are available
            - Classify toxicodynamic activity and systemic availability as high, medium, or low based on 
            the available evidence and expert judgment
            - When using read-across, clearly state the basis for the analogy and any limitations

            Adhere to ethical standards in toxicology and maintain scientific objectivity in your assessments.''',
        'response': {
            'prompt': output['config']['prompts'],
            'provider': output['config']['providers'],
            'vars': '',
            'response': ''
        }
    }
    

env_config = dotenv.dotenv_values(Path(__file__).parent.parent / ".env")

if __name__ == '__main__':
    runTest(Config.DIR_TEST / sys.argv[1] / 'config.yaml')