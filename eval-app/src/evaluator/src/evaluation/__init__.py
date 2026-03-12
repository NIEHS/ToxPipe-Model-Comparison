
from langsmith import traceable
from .executor import Executor
from .evaluator import EvaluateResponse
import concurrent.futures
import tqdm
import traceback
import json
import yaml
from .db import EvalDB, EvalConfigDB
from datetime import datetime
from functools import partial
from .utils import Config

def execute(model_info, prompt_info, vars_info):

    try:
        response = Executor(model_info, prompt_info, vars_info).execute()
    except Exception as exp:
        error = f'Line number: {exp.__traceback__.tb_lineno}, Description: {exp}\n\n{traceback.format_exc()}'
        print(error)
        return {'output': '', 'error': error}
    
    return response

def evaluate(assert_info, response, prompt):
    
    try:
        return EvaluateResponse(assert_info=assert_info).getEvaluation(response=response, prompt=prompt)
    except Exception as exp:
        error = f'Line number: {exp.__traceback__.tb_lineno}, Description: {exp}\n\n{traceback.format_exc()}'
        print(error)
        return {'output': '', 'error': f'Error in evaluation: {error}'}

#@traceable 
def executeAndEvaluate(model_info, prompt_info, vars_info, assert_info, num_runs=1):

    responses = []
    for _ in range(num_runs):
        response = execute(model_info, prompt_info, vars_info)
        response['results'] = evaluate(assert_info=assert_info, response=response['output'], prompt=prompt_info['user'].format(**vars_info)) if len(assert_info) > 0 else {}
        responses.append(response)

    if num_runs == 1: return responses[0]
    return responses

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

    def runExecuteAndEvaluate(eval_sets, descs, indices, num_runs):
        
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results = pool.map(partial(executeAndEvaluate, num_runs=num_runs), *zip(*eval_sets))
            for i, res in enumerate(pbar := tqdm.tqdm(results, total=len(eval_sets), bar_format="{desc:<32.30}{percentage:3.0f}%|{bar:50}{r_bar}")):
                pbar.set_description(descs[i])
                db.update(filter={'_id': indices[i]}, value={'response': res})

    def runEvaluate(eval_sets_eval, descs_eval, indices_eval, indices_response_eval, num_runs):
        
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results = pool.map(evaluate, *zip(*eval_sets_eval))
            for i, res in enumerate(pbar := tqdm.tqdm(results, total=len(eval_sets_eval), bar_format="{desc:<32.30}{percentage:3.0f}%|{bar:50}{r_bar}")):
                pbar.set_description(descs_eval[i])
                if num_runs > 1:
                    db.update(filter={'_id': indices_eval[i]}, value={f'response.{indices_response_eval[i]}.results': res})
                else:
                    db.update(filter={'_id': indices_eval[i]}, value={'response.results': res})

    db = EvalDB(eval_name)

    record = db.getOne({"_id": 0})
    system_prompt = record['system_prompt']
    num_runs = record.get('num_runs', 1)

    threshold = 50
    db_size = len(db)
    start = 1
    
    while start < db_size:

        eval_sets, descs, indices = [], [], []
        eval_sets_eval, descs_eval, indices_eval, indices_response_eval = [], [], [], []

        records = [x for x in db.get({"_id": {"$in": list(range(start, start+threshold))}})]

        for record in records:

            model_info = record['provider']
            prompt = record['prompt']
            vars_info = record['vars']
            assert_info = record['assert']
            prompt_info = {'system': system_prompt, 'user': prompt}

            response_list = [record['response'].copy()] if num_runs == 1 else record['response'].copy()
            
            # Check for error in response to re-execute and re-evaluate
            for i, response in enumerate(response_list):
                
                is_response_error = (not skip_run) and (('error' in response and len(response['error'].strip()) > 0 and 
                                                         (response['error'].startswith('Line number: 18, Description: unhandled errors in a TaskGroup'))) or
                                                        response['output'].lower().startswith('error'))
                
                if not is_response_error: continue
                
                descs.append(f"{model_info['label']} - {prompt[:30]}")
                eval_sets.append([model_info, prompt_info, vars_info, assert_info])
                indices.append(record['_id'])

            # Check for error in evaluation to re-evaluate
            else:
                for i, response in enumerate(response_list):

                    if not len(record['assert']) > 0: continue 
                    
                    is_eval_error = False
                    if 'results' in response:
                        if isinstance(response['results'], dict):
                            if 'error' in response['results']: is_eval_error = True
                        else:
                            for res in response['results']:
                                if 'error' in res: 
                                    is_eval_error = True
                                    break

                    if not is_eval_error: continue
                    
                    descs_eval.append(f"{model_info['label']} - {prompt[:30]}")
                    eval_sets_eval.append([assert_info, response['output'], prompt_info['user'].format(**vars_info)])
                    indices_eval.append(record['_id'])
                    indices_response_eval.append(i)
            
        if not (len(eval_sets) or len(eval_sets_eval)): 
            start += threshold
            continue
        
        print(f'Processing from record id {start} to {start+threshold-1}')
        if eval_sets: runExecuteAndEvaluate(eval_sets, descs, indices, num_runs)
        if eval_sets_eval: runEvaluate(eval_sets_eval, descs_eval, indices_eval, indices_response_eval, num_runs)

        start += threshold
            

def runTest(eval_name, replace=False, skip_run=False):

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
                                        'results': {}}
                else:
                    response_init_value = [{'output': '', 
                                        'error': 'Init mode: Response has not been generated yet.', 
                                        'results': {}} for _ in range(num_runs)]
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
                        if not record['assert']:
                            if isinstance(record['response'], list):
                                for i in range(len(record['response'])):
                                    record['response'][i]['results'] = {}
                            else:
                                record['response']['results'] = {}
                        tests.append(filter_value | {'_id': index, 'response': record['response']})
                    else:
                        if isinstance(record['response'], list):
                            for i in range(len(record['response'])):
                                record['response'][i]['results'] = {}
                        else:
                            record['response']['results'] = {}

                        tests.append(filter_value | {'_id': index, 'response': record['response']})
                    
                index += 1

                if len(tests) >= 50:
                    db_temp.add(tests)
                    tests = []

    if len(tests): db_temp.add(tests)
    
    # Replace the original eval db with the temp db
    db_temp.collection.rename(eval_name, dropTarget=True)

    resumeLastRun(eval_name, skip_run=skip_run)