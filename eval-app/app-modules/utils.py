import json
import traceback
import pandas as pd
import subprocess
from codes.evaluate import runTest
from utils import Config, loadYML, saveYML
import shutil
from codes.create_promptfoo_config import createTest

# Promptfoo
class EvaluatorTemp:

    PROMPT_VAR_FORMAT = '\{\{(.*?)\}\}'
    CONFIG_FILE_NAME = 'promptfooconfig.yaml'

    def processConfig(dir_config):
        return loadYML(dir_config / 'promptfooconfig.yaml')

    def processResults(dir_output):
            
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
        
        results = []
        with open(dir_output / 'output.json') as f:
            data = json.load(f)
        
        for item in data['results']['results']:
            try:
                results.append(
                    {
                        'Id': f"{item['testIdx']}|{item['provider']['label']}",
                        'Prompt': item['prompt']['raw'], 
                        'Model': item['provider']['label'], 
                        'Response': item['response']['output'] if 'output' in item['response'] else item['response']['error'] if 'error' in item['response'] else '',
                        'Result': 'No assertion' if not item['testCase']['assert'] else 'Pass' if item['success'] else 'Fail',
                        'Variable': ', '.join([f'{k}:{v}' for k, v in item['testCase']['vars'].items()]), 
                        'Reason': getExplanation(item['gradingResult'])
                    }
                )
            except Exception as exp:
                print(f'Error reading output from {dir_output}')
                print(f"Line number: {exp.__traceback__.tb_lineno}, Description: {exp}\n\n{traceback.format_exc()}")
                return pd.DataFrame()

        results = pd.DataFrame(results)
        results['eval_id'] = data['evalId']
        
        return results
    
    def createTest(dir_test, info, has_toxpipe):

        try:
            dir_setup = dir_test / 'setup'
            dir_setup.mkdir(parents=True, exist_ok=True)

            config = {
                        'description': info['description'],
                        'prompts': 'prompts.yaml',
                        'providers': 'providers.yaml',
                        'tests': 'tests.yaml',
                        'defaultTest': 'defaulttest.yaml'
                    }

            saveYML(info['defaulttest'], dir_setup / 'defaulttest.yaml')
            saveYML(info['prompts'], dir_setup / 'prompts.yaml')
            saveYML(info['providers'], dir_setup / 'providers.yaml')
            saveYML(info['tests'], dir_setup / 'tests.yaml')
            saveYML(config, dir_setup / 'config.yaml')

            createTest(test_name=info['test_name'])

            dir_scripts = dir_test / 'scripts'
            dir_scripts.mkdir(parents=True, exist_ok=True)

            if has_toxpipe:
                dir_src = Config.DIR_CODES / 'providers.py'
                shutil.copy(dir_src, dir_scripts)

            dir_src = Config.DIR_CODES / 'tests.py'
            shutil.copy(dir_src, dir_scripts)
        except Exception as exp:
            print(f"Line number: {exp.__traceback__.tb_lineno}, Description: {exp}\n\n{traceback.format_exc()}")
            return False

        return True

    def runTest(dir_test):
        path_output = dir_test / 'output' / 'output.json'
        status = subprocess.run(['promptfoo', 'eval', '-c', str(dir_test), '-o', str(path_output)])
        return status.returncode == 0

# Custom evaluator
class Evaluator:

    PROMPT_VAR_FORMAT = '\{(.*?)\}'
    CONFIG_FILE_NAME = 'config.yaml'

    def processConfig(dir_config):
        return loadYML(dir_config / 'config.yaml')

    def processResults(dir_output):
            
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
        
        results = []
        with open(dir_output / 'output.json') as f:
            data = json.load(f)
        
        for item in data['tests']:
            try:
                results.append(
                    {
                        'Id': f"{data['id']}|{item['provider']['label']}",
                        'Prompt': item['prompt'].format(**item['vars']), 
                        'Model': item['provider']['label'], 
                        'Response': item['response']['output'],
                        'Result': 'No assertion' if not item['response']['results'] else 'Pass' if item['response']['results']['pass'] else 'Fail',
                        'Variable': ', '.join([f'{k}:{v}' for k, v in item['vars'].items()]), 
                        'Reason': getExplanation(item['response']['results'])
                    }
                )
            except Exception as exp:
                print(f'Error reading output from {dir_output}')
                print(f"Line number: {exp.__traceback__.tb_lineno}, Description: {exp}\n\n{traceback.format_exc()}")
                return pd.DataFrame()

        results = pd.DataFrame(results)
        results['eval_id'] = data['id']
        
        return results

    def runTest(dir_test):
        try:
            runTest(dir_test / 'config.yaml')
        except Exception as exp:
            print(f'Line number: {exp.__traceback__.tb_lineno}, Description: {exp}\n\n{traceback.format_exc()}')
            return False
        return True
    
    def createTest(dir_test, info, *args):

        try:
            dir_test.mkdir(parents=True, exist_ok=True)
            config = {
                'defaultTest': info['defaulttest'],
                'description': info['description'],
                'system_prompt': info['prompts']['system'],
                'prompts': info['prompts']['user'],
                'providers': info['providers'],
                'tests': info['tests']
            }
            saveYML(config, dir_test / 'config.yaml')
        except Exception as exp:
            print(f"Line number: {exp.__traceback__.tb_lineno}, Description: {exp}\n\n{traceback.format_exc()}")
            return False

        return True