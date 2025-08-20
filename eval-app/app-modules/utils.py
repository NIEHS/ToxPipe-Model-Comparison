import json
import traceback
import pandas as pd
import subprocess
from utils import Config, loadYML, saveYML
import shutil
from shiny.express import ui

# Custom evaluator
class Evaluator:

    PROMPT_VAR_FORMAT = r'\{(.*?)\}'
    CONFIG_FILE_NAME = 'config.yaml'

    def hasOutput(eval_name):
        return (Config.DIR_TESTS / eval_name / 'output' / 'output_0.json').exists()
    
    def hasEmbedding(eval_name):
        return (Config.DIR_TESTS / eval_name / 'output' / 'response_embeddings.json').exists()
    
    def loadEvals():
        return sorted([eval_name.name for eval_name in Config.DIR_TESTS.iterdir() if Evaluator.hasOutput(eval_name)])
    
    def loadEvalsToRun():
        return sorted([eval_name.name for eval_name in Config.DIR_TESTS.iterdir() if (Config.DIR_TESTS / eval_name / 'config.yaml').exists()])

    def processConfig(eval_name):
        return loadYML(Config.DIR_TESTS / eval_name / 'config.yaml')

    def processResults(eval_name):
            
        def getExplanation(result):

            def getComponentExplanation(results):
                d_results = []
                has_component = False
                for result in results:
                    if 'componentResults' in result:
                        d_results.append({
                                'pass': result['pass'],
                                'reason': result['reason'],
                                'components': getComponentExplanation(result['componentResults'])
                        })
                        has_component = True

                if not has_component:
                    for result in results:
                        d_results.append({
                                'pass': result['pass'],
                                'reason': result['reason'],
                        })

                return d_results

            if not result: return "No reason found"

            if 'componentResults' in result:
                d_results = getComponentExplanation(result['componentResults'])
            else:
                d_results = [{'pass': result['pass'],
                            'reason': result['reason'],
                }]
            return d_results
        
        if not Evaluator.hasOutput(eval_name): return pd.DataFrame()

        results = []
        dir_output = Config.DIR_TESTS / eval_name / 'output'
        list_output_file_path = sorted(list(dir_output.glob('output_*.json')), key=lambda x: int(x.stem.split('_')[-1]))
    
        for file_path in list_output_file_path:

            with open(file_path) as f:
                data = json.load(f)
            
            results_chunk = []
            for item in data['tests']:
                try:
                    results_chunk.append(
                        {
                            **{
                                'Id': f"{data['id']}|{item['provider']['label']}",
                                'eval_id': data['id'],
                                'Prompt': item['prompt'], 
                                'Model': item['provider']['label'], 
                                'Response': item['response']['output'],
                                'Result': 'No assertion' if not item['response']['results'] else 'Pass' if item['response']['results']['pass'] else 'Fail', 
                                'Reason': getExplanation(item['response']['results']),
                                'Used Context': ('steps_taken' in item['response']) and (item['response']['steps_taken'][-1] == 'query_with_context'),
                                'Searched Keyphrases': '\n'.join([f'- {x}' for x in item['response']['searched_keyphrases']]) if 'searched_keyphrases' in item['response'] else ''
                            },
                            **item['vars']
                        }
                    )
                except Exception as exp:
                    print(f'Error reading output from {file_path}')
                    print(f"Line number: {exp.__traceback__.tb_lineno}, Description: {exp}\n\n{traceback.format_exc()}")
                    continue
                
            results += results_chunk

        results = pd.DataFrame(results)

        return results
    
    def processEmbeddings(eval_name):
        if not Evaluator.hasEmbedding(eval_name): return None
        with open(Config.DIR_TESTS / eval_name / 'output' / 'response_embeddings.json') as f:
            embeddings = json.load(f)
        return embeddings
    
    def runTest(eval_name):

        from codes.evaluation import runTest
        import concurrent.futures
        from datetime import datetime
        from uuid import uuid4
    
        def resumeLastRun(output_path, resume):

            output = {}
            
            if not (resume and output_path.exists()): return output
            eval_sets, descs = [], []
            with open(output_path) as f:
                output = json.load(f)
                if 'tests' not in output: return output
                for t in output['tests']:
                    if 'error' in t['response']:
                        model_info = t['provider']
                        prompt = t['prompt']
                        prompt_info = {'system': output['system_prompt'], 'user': prompt}
                        vars_info = t['vars']
                        assert_info = t['assert']
                        descs.append(f"{model_info['label']} - {prompt[:30]}")
                        eval_sets.append([model_info, prompt_info, vars_info, assert_info])
                
                with concurrent.futures.ProcessPoolExecutor() as pool: 
                    results = pool.map(evaluate, *zip(*eval_sets))
                    with ui.Progress(min=1, max=len(eval_sets)) as p:
                        for i, res in enumerate(results):
                            p.set(i, message=f'Running test ({(i+1)*100//len(eval_sets)} %)')
                            output['tests'][i]['response'] = res

            return output

        def run(config_path, resume=False):

            output_path = (config_path.parent / 'output' / 'output.json')

            output = resumeLastRun(output_path, resume)

            if len(output) == 0:
                config = loadYML(config_path)
                eval_sets, descs = [], []
                for model_info in config['providers']:
                    for prompt in config['prompts']:
                        prompt_info = {'system': config['system_prompt'], 'user': prompt}
                        for test in config['tests']:
                            vars_info = test['vars']
                            assert_info = test['assert'] if 'assert' in test else {}
                            descs.append(f"{model_info['label']} - {prompt[:30]}")
                            eval_sets.append([model_info, prompt_info, vars_info, assert_info])

                eventid = datetime.now().strftime('%Y%m-%d%H-%M%S-') + str(uuid4())

                output = {'id': eventid, 'system_prompt': config['system_prompt'], 'tests': []}

                with concurrent.futures.ProcessPoolExecutor() as pool:
                    results = pool.map(evaluate, *zip(*eval_sets))
                    with ui.Progress(min=1, max=len(eval_sets)) as p:
                        for i, res in enumerate(results):
                            p.set(i, message=f'Running test ({(i+1)*100//len(eval_sets)} %)')
                            output['tests'].append({'provider': eval_sets[i][0], 'prompt': eval_sets[i][1]['user'], 'vars': eval_sets[i][2], 'assert': eval_sets[i][3], 'response': res})

            (config_path.parent / 'output').mkdir(parents=False, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(output, f)

        try:
            #run(Config.DIR_TESTS / eval_name / 'config.yaml')
            runTest(Config.DIR_TESTS / eval_name  / 'config.yaml', resume=False, skip_run=False)
        except Exception as exp:
            print(f'Line number: {exp.__traceback__.tb_lineno}, Description: {exp}\n\n{traceback.format_exc()}')
            return False
        return True
    
    def createTest(eval_name, info, *args):

        dir_eval = Config.DIR_TESTS / eval_name
        try:
            dir_eval.mkdir(parents=True, exist_ok=True)
            config = {
                'defaultTest': info['defaulttest'],
                'description': info['description'],
                'system_prompt': info['prompts']['system'],
                'prompts': info['prompts']['user'],
                'providers': info['providers'],
                'tests': info['tests']
            }
            saveYML(config, dir_eval / 'config.yaml')
        except Exception as exp:
            print(f"Line number: {exp.__traceback__.tb_lineno}, Description: {exp}\n\n{traceback.format_exc()}")
            return False

        return True