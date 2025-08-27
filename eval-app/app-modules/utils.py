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
    NUM_NONVARS_COLS = 10

    def hasOutput(eval_name):
        return (Config.DIR_TESTS / eval_name / 'output' / 'output_0.json').exists()
    
    def hasEmbedding(eval_name):
        return (Config.DIR_TESTS / eval_name / 'output' / 'response_embeddings.json').exists()
    
    def loadEvals():
        try:
            return sorted([eval_name.name for eval_name in Config.DIR_TESTS.iterdir() if Evaluator.hasOutput(eval_name)])
        except:
            return []
    
    def loadEvalsToRun():
        try:
            return sorted([eval_name.name for eval_name in Config.DIR_TESTS.iterdir() if (Config.DIR_TESTS / eval_name / 'config.yaml').exists()])
        except:
            return []

    def processConfig(eval_name):
        try:
            return loadYML(Config.DIR_TESTS / eval_name / 'config.yaml')
        except:
            return {}

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
                    content = {
                        'Id': f"{data['id']}|{item['provider']['label']}",
                        'eval_id': data['id'],
                        'Prompt': item['prompt'], 
                        'Model': item['provider']['label'], 
                        'Response': item['response']['output'],
                        'Result': 'No assertion' if not item['response']['results'] else 'Pass' if item['response']['results']['pass'] else 'Fail',
                        'Score':  float(item['response']['results']['score']) if item['response']['results'] else 0,
                        'Reason': getExplanation(item['response']['results'])
                    }
                    if 'steps_taken' in item['response']:
                        content |= {
                            'Used Context': (item['response']['steps_taken'][-1] == 'query_with_context')
                        }
                    if 'searched_keyphrases' in item['response']:
                        content |= {
                            'Searched Keyphrases': '\n'.join([f'- {x}' for x in item['response']['searched_keyphrases']])
                        }

                    # Vars columns must be added last to ensure ease of processing.
                    content |= item['vars']
                    
                    results_chunk.append(content)

                except Exception as exp:
                    print(f'Error reading output from {file_path}')
                    print(f"Line number: {exp.__traceback__.tb_lineno}, Description: {exp}\n\n{traceback.format_exc()}")
                    continue
                
            results += results_chunk

        results = pd.DataFrame(results)

        Evaluator.NUM_NONVARS_COLS = 10 if 'Used Context' in results.columns and 'Searched Keyphrases' in results.columns else 8

        return results
    
    def processEmbeddings(eval_name):
        if not Evaluator.hasEmbedding(eval_name): return None
        with open(Config.DIR_TESTS / eval_name / 'output' / 'response_embeddings.json') as f:
            embeddings = json.load(f)
        return embeddings
    
    def runTest(eval_name):

        from codes.evaluation import runTest

        try:
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