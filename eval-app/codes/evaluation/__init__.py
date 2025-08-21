
from langsmith import traceable
from .models import queryBaseModel, queryToxpipe
from .evaluator import EvaluateResponse
import concurrent.futures
import tqdm
import traceback
import json
import yaml
from datetime import datetime
from uuid import uuid4

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

def writeJSON(output_path, data):
    with open(output_path, 'w') as f:
        json.dump(data, f)

def resumeLastRun(dir_output, skip_run, resume_eval):

    list_output_file_path = sorted(list(dir_output.glob('output_*.json')), key=lambda x: int(x.stem.split('_')[-1]))

    for output_partial_path in list_output_file_path:

        output = {}
        eval_sets, descs, indices = [], [], []
        eval_sets_eval, descs_eval, indices_eval = [], [], []

        with open(output_partial_path) as f:
            output = json.load(f)

        if 'tests' not in output: return {}
    
        for index, t in enumerate(output['tests']):
            is_response_error = (not skip_run) and (('error' in t['response'] and len(t['response']['error'].strip()) > 0) or 
                                (not isinstance(t['response']['output'], str)) or 
                                t['response']['output'].strip() == '' or
                                t['response']['output'].lower().startswith('error'))
                                
            is_eval_error =  (len(t['assert']) > 0 and ((not resume_eval) or 
                                                        'results' not in t['response'] or 
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
                    eval_sets_eval.append([assert_info, t['response']['output'], prompt_info['user'].format(**vars_info)])
                    indices_eval.append(index)
        
        if not (len(eval_sets) or len(eval_sets_eval)): continue

        print(f'Processing {output_partial_path.name}')
        
        with concurrent.futures.ThreadPoolExecutor(10) as pool:
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

def runTest(config_path, resume=False, skip_run=False):

    dir_output = config_path.parent / 'output'
    dir_output.mkdir(parents=False, exist_ok=True)

    if not resume and not skip_run:

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

    resumeLastRun(dir_output, skip_run=skip_run, resume_eval=resume)