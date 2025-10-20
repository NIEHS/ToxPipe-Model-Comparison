
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

def getModelResponse(model_info, prompt_info, vars_info):

    try:
        response = Executor(model_info, prompt_info, vars_info).execute()
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
    response['results'] = getEvaluationResponse(assert_info=assert_info, response=response, prompt=prompt_info['user'].format(**vars_info)) if len(assert_info) > 0 else {}

    return response

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

def resumeLastRun(db, skip_run, resume_eval):

    def run(eval_sets, descs, indices,
            eval_sets_eval, descs_eval, indices_eval):

        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            if eval_sets: 
                results = pool.map(getResponseAndEvaluate, *zip(*eval_sets))
                for i, res in enumerate(pbar := tqdm.tqdm(results, total=len(eval_sets), bar_format="{desc:<32.30}{percentage:3.0f}%|{bar:50}{r_bar}")):
                    pbar.set_description(descs[i])
                    db.update(filter={'_id': indices[i]}, value={'response': res})
            if eval_sets_eval:
                results = pool.map(getEvaluationResponse, *zip(*eval_sets_eval))
                for i, res in enumerate(pbar := tqdm.tqdm(results, total=len(eval_sets_eval), bar_format="{desc:<32.30}{percentage:3.0f}%|{bar:50}{r_bar}")):
                    pbar.set_description(descs_eval[i])
                    db.update(filter={'_id': indices_eval[i]}, value={'response.results': res})

    records_db = db.getAll().sort('_id', 1)

    first_record = True
    eval_sets, descs, indices = [], [], []
    eval_sets_eval, descs_eval, indices_eval = [], [], []
    threshold = 50

    for record in records_db:

        if first_record: 
            system_prompt = record['system_prompt']
            first_record = False
            continue
        
        is_response_error = (not skip_run) and (('error' in record['response'] and len(record['response']['error'].strip()) > 0) or
                            record['response']['output'].lower().startswith('error'))
                            
        is_eval_error =  (len(record['assert']) > 0 and ((not resume_eval) or 
                                                    'results' not in record['response'] or 
                                                    len(record['response']['results']) == 0 or 
                                                    'error' in record['response']['results']))
        if is_response_error or is_eval_error:
            
            model_info = record['provider']
            prompt = record['prompt']
            vars_info = record['vars']
            assert_info = record['assert']
            prompt_info = {'system': system_prompt, 'user': prompt}
            
            if is_response_error: 
                descs.append(f"{model_info['label']} - {prompt[:30]}")
                eval_sets.append([model_info, prompt_info, vars_info, assert_info])
                indices.append(record['_id'])      
            elif is_eval_error:
                descs_eval.append(f"{model_info['label']} - {prompt[:30]}")
                eval_sets_eval.append([assert_info, record['response']['output'], prompt_info['user'].format(**vars_info)])
                indices_eval.append(record['_id'])

        if record['_id'] % threshold: continue
        if not (len(eval_sets) or len(eval_sets_eval)): continue
        
        print(f'Processing from record id {record['_id'] - threshold + 1} to {record['_id']}')
        run(eval_sets, descs, indices, eval_sets_eval, descs_eval, indices_eval)
        eval_sets, descs, indices = [], [], []
        eval_sets_eval, descs_eval, indices_eval = [], [], []

    if len(eval_sets) or len(eval_sets_eval): 
        print(f'Processing upto record id {record['_id']}')
        run(eval_sets, descs, indices, eval_sets_eval, descs_eval, indices_eval)

def runTest(eval_name, resume=False, skip_run=False):

    db = EvalDB(eval_name)

    if not resume and not skip_run:

        db.drop()

        db_config = EvalConfigDB(eval_name)
        config = db_config.getAll()[0]

        event_id = str(datetime.now().timestamp())
        init = {'_id': 0, 'event_id': event_id, 'system_prompt': config['system_prompt']}
        db.add(init)
        tests = []
        index = 1
        for model_info in config['providers']:
            for pva in config['prompts_vars_asserts']:
                for test in pva['tests']:
                    vars_info = test.get('vars', {})
                    assert_info = test.get('assert', {})

                    tests.append({'_id': index, 
                                  'provider': model_info, 
                                  'prompt': pva['prompt'], 
                                  'vars': vars_info, 
                                  'assert': assert_info, 
                                  'response': {'output': '', 'error': 'Init mode: Response has not been generated yet.', 'results': {}}})
                    index += 1

                    if len(tests) >= 50:
                        db.add(tests)
                        tests = []

        if len(tests): db.add(tests)

    resumeLastRun(db, skip_run=skip_run, resume_eval=resume)