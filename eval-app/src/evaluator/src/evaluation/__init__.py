
from langsmith import traceable
from .executor import Executor
from .evaluator import Evaluator
import concurrent.futures
import tqdm
import traceback
import json
import yaml
from .db import EvalDB, EvalConfigDB
from datetime import datetime
from functools import partial
from .utils import Config

eval_models = [
    {
        'id': 'azure-gpt-5.5',
        'config': {
            'temperature': 0,
            'reasoning_effort': 'low'
        }
    },
    {
        'id': 'claude-4.5-haiku',
        'config': {
            'temperature': 0
        }                  
    },
    {
        'id': 'gemini-3.5-flash',
        'config': {
            'temperature': 0            
        }
    }
]

def execute(model_info, prompt_info, vars_info):

    try:
        response = Executor(model_info, prompt_info, vars_info).execute()
    except Exception as exp:
        error = f'Line number: {exp.__traceback__.tb_lineno}, Description: {exp}\n\n{traceback.format_exc()}'
        print(error)
        response = {'output': '', 'error': error}
    
    return response

def evaluate(prompt, response, assert_info, eval_model_info, index_group=None):
    
    try:
        response = Evaluator(response_query=prompt, response=response, assert_info=assert_info).evaluate(config={'eval_model': eval_model_info})
    except Exception as exp:
        error = f'Line number: {exp.__traceback__.tb_lineno}, Description: {exp}\n\n{traceback.format_exc()}'
        print(error)
        response = {'output': '', 'error': f'Error in evaluation: {error}'}

    return response | {'eval_model': eval_model_info}, index_group

#@traceable 
def executeAndEvaluate(model_info, prompt_info, vars_info, assert_info, record_id, num_runs=1):

    responses = []
    for _ in range(num_runs):
        response = execute(model_info, prompt_info, vars_info)
        prompt = prompt_info['user'].format(**vars_info)
        if len(eval_models) > 1:
            response['results'] = [evaluate(prompt=prompt,
                                            response=response['output'],
                                            assert_info=assert_info, 
                                            eval_model_info=eval_model_info)[0] if len(assert_info) > 0 else [] for eval_model_info in eval_models]
        else:
            response['results'] = evaluate(prompt=prompt, 
                                           response=response['output'],
                                           assert_info=assert_info, 
                                           eval_model_info=eval_models[0])[0] if len(assert_info) > 0 else {}
        responses.append(response)

    if num_runs == 1: return responses[0], record_id
    return responses, record_id

def loadYML(file_path):
    data = None
    with open(file_path) as stream:
        try:
            data = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
    return data

def readJSON(path):
    with open(path) as f:
        return json.load(f)

def writeJSON(output_path, data):
    with open(output_path, 'w') as f:
        json.dump(data, f)

def resumeLastRun(eval_name, skip_run):

    def runExecuteAndEvaluate(eval_sets, descs, num_runs):
        
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results = pool.map(partial(executeAndEvaluate, num_runs=num_runs), *zip(*eval_sets))
            for i, (res, record_id) in enumerate(pbar := tqdm.tqdm(results, total=len(eval_sets), bar_format="{desc:<32.30}{percentage:3.0f}%|{bar:50}{r_bar}")):
                pbar.set_description(descs[i])
                db.update(filter={'_id': record_id}, value={'response': res})

    def runEvaluate(eval_sets_eval, descs_eval, num_runs):
        
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results = pool.map(evaluate, *zip(*eval_sets_eval))
            for i, (res, (record_id, index_response, index_eval_model)) in enumerate(pbar := tqdm.tqdm(results, total=len(eval_sets_eval), bar_format="{desc:<32.30}{percentage:3.0f}%|{bar:50}{r_bar}")):
                pbar.set_description(descs_eval[i])
                if len(eval_models) > 1:
                    if num_runs > 1:
                        db.update(filter={'_id': record_id}, value={f'response.{index_response}.results.{index_eval_model}': res})
                    else:
                        db.update(filter={'_id': record_id}, value={f'response.results.{index_eval_model}': res})
                else:
                    if num_runs > 1:
                        db.update(filter={'_id': record_id}, value={f'response.{index_response}.results': res})
                    else:
                        db.update(filter={'_id': record_id}, value={'response.results': res})

    db = EvalDB(eval_name)

    record = db.getOne({"_id": 0})
    system_prompt = record['system_prompt']
    num_runs = record.get('num_runs', 1)

    threshold = 50
    db_size = len(db)
    start = 1
    
    while start < db_size:

        eval_sets, descs = [], []
        eval_sets_eval, descs_eval = [], []

        records = [x for x in db.get({"_id": {"$in": list(range(start, start+threshold))}})]

        for record in records:

            model_info = record['provider']
            prompt = record['prompt']
            vars_info = record['vars']
            assert_info = record['assert']
            prompt_info = {'system': system_prompt, 'user': prompt}

            response_list = [record['response'].copy()] if num_runs == 1 else record['response'].copy()
            
            # Check for error in response to re-execute and re-evaluate
            for index_response, response in enumerate(response_list):
                
                is_response_error = (not skip_run) and (('error' in response and len(response['error'].strip()) > 0) or
                                                        response['output'].lower().startswith('error'))
                
                if not is_response_error: continue
                
                descs.append(f"{model_info['label']} - {prompt[:30]}")
                eval_sets.append([model_info, prompt_info, vars_info, assert_info, record['_id']])

            # Check for error in evaluation to re-evaluate
            else:
                for index_response, response in enumerate(response_list):

                    if not len(record['assert']) > 0: continue 

                    is_eval_error = 'results' not in response

                    if len(eval_models) == 1:
                        if isinstance(response['results'], dict) or not response['results'] or 'error' in response['results']:
                            descs_eval.append(f"{model_info['label']} - {prompt[:30]}")
                            eval_sets_eval.append([prompt_info['user'].format(**vars_info), response['output'], assert_info, eval_model_info, (record['_id'], index_response, -1)])
                    else:
                        is_eval_error = is_eval_error or (not isinstance(response['results'], list)) or (len(response['results']) != len(eval_models))
                        for index_eval_model, eval_model_info in enumerate(eval_models):
                            if is_eval_error or (not response['results'][index_eval_model]) or 'error' in response['results'][index_eval_model]:
                                descs_eval.append(f"{model_info['label']} - {prompt[:30]}")
                                eval_sets_eval.append([prompt_info['user'].format(**vars_info), response['output'], assert_info, eval_model_info, (record['_id'], index_response, index_eval_model)])
                    
        if not (len(eval_sets) or len(eval_sets_eval)): 
            start += threshold
            continue
        
        print(f'Processing from record id {start} to {start+threshold-1} [multiplied by number of runs ({num_runs}) x eval models ({len(eval_models)})]')
        if eval_sets: runExecuteAndEvaluate(eval_sets, descs, num_runs)
        if eval_sets_eval: runEvaluate(eval_sets_eval, descs_eval, num_runs)

        start += threshold

def runTest(eval_name, replace=False, skip_run=False):

    def setEvalResults():

        if len(eval_models) > 1:
            return [{} for _ in eval_models]
        return {}

    assert len(eval_models), f'No evaluator model was configured, {eval_models=}'

    # The original eval db
    db = EvalDB(eval_name)

    # Temporary eval db to store new test results
    db_temp = EvalDB(f'{eval_name}_temp')
    db_temp.drop()

    db_config = EvalConfigDB(eval_name)
    config = db_config.getAll()[0]

    event_id = str(datetime.now().timestamp())
    num_runs = config.get('num_runs', 1)
    db_temp.add({'_id': 0, 'event_id': event_id, 'system_prompt': config['system_prompt'], 'num_runs': num_runs})

    tests = []
    index = 1

    print('Scanning for tests to run...')

    for model_info in tqdm.tqdm(config['providers']):
        for pva in config['prompts_vars_asserts']:
            for test in pva['tests']:
                vars_info = test.get('vars', {})
                assert_info = test.get('assert', {})
                filter_value = {'provider': model_info, 
                                'prompt': pva['prompt'], 
                                'vars': vars_info, 
                                'assert': assert_info
                } 
                
                if num_runs == 1:
                    response_init_value = {'output': '', 
                                        'error': 'Init mode: Response has not been generated yet.', 
                                        'results': setEvalResults()}
                else:
                    response_init_value = [{'output': '', 
                                        'error': 'Init mode: Response has not been generated yet.', 
                                        'results': setEvalResults()} for _ in range(num_runs)]
                if not skip_run:
                    if replace:
                        tests.append(filter_value | {'_id': index, 'response': response_init_value})
                    else:
                        record = db.collection.find_one(filter_value)
                        if record is None:
                            tests.append(filter_value | {'_id': index, 'response': response_init_value})
                        else:
                            tests.append(filter_value | {'_id': index, 'response': record['response']})

                else:
                    record = db.collection.find_one(filter_value)
                    if record is None:
                        tests.append(filter_value | {'_id': index, 'response': response_init_value})
                    elif not replace:
                        if record['assert']:
                            if isinstance(record['response'], list):
                                for i in range(len(record['response'])):
                                    record['response'][i]['results'] = setEvalResults()
                            else:
                                record['response']['results'] = setEvalResults()
                        tests.append(filter_value | {'_id': index, 'response': record['response']})
                    else:
                        if isinstance(record['response'], list):
                            for i in range(len(record['response'])):
                                record['response'][i]['results'] = setEvalResults()
                        else:
                            record['response']['results'] = setEvalResults()

                        tests.append(filter_value | {'_id': index, 'response': record['response']})
                    
                index += 1

                if len(tests) >= 50:
                    db_temp.add(tests)
                    tests = []

    if len(tests): db_temp.add(tests)
    
    # Replace the original eval db with the temp db
    db_temp.collection.rename(eval_name, dropTarget=True)

    resumeLastRun(eval_name, skip_run=skip_run)