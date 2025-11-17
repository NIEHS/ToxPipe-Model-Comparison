from .utils import Config
from .db import EvalDB, EvalConfigDB
import json
import traceback
import pandas as pd
import re

# Custom evaluator
class Evaluator:

    PROMPT_VAR_FORMAT = r'\{(.*?)\}'
    NUM_NONVARS_COLS = 8

    def hasOutput(eval_name):
        if not eval_name: return False
        return EvalDB(eval_name).exists()
        return (Config.DIR_TESTS / eval_name / 'output' / 'output_0.json').exists()
    
    #def hasEmbedding(eval_name):
    #    return (Config.DIR_TESTS / eval_name / 'output' / 'response_embeddings.json').exists()
    
    def loadEvals():
        try:
            return EvalDB().listEvals()
            return sorted([eval_name.name for eval_name in Config.DIR_TESTS.iterdir() if Evaluator.hasOutput(eval_name)])
        except Exception as exp:
            print(exp)
            return []
    
    def loadEvalsToRun():
        try:
            return EvalConfigDB().listEvals()
            return sorted([eval_name.name for eval_name in Config.DIR_TESTS.iterdir() if (Config.DIR_TESTS / eval_name / 'config.yaml').exists()])
        except:
            return []

    def processConfig(eval_name):
        try:
            db = EvalConfigDB(eval_name)
            return db.getAll()[0]
            return loadYML(Config.DIR_TESTS / eval_name / 'config.yaml')
        except:
            return {}
        
    def getPrompts(eval_name: str):
        db = EvalConfigDB(eval_name)
        return db.collection.distinct('prompts_vars_asserts.prompt')
    
    def getPromptsAndAsserts(eval_name: str):
        db = EvalConfigDB(eval_name)
        prompts_vars_asserts = db.collection.distinct('prompts_vars_asserts')
        prompts_and_asserts = []
        for item in prompts_vars_asserts:
            for test in item['tests']:
                if 'vars' not in test:
                    prompt = item['prompt']
                else:
                    prompt = item['prompt'].format(**test['vars'])
                if 'assert' not in test or len(test['assert']) == 0:
                    expected_kp = []
                else:
                    expected_kp = test['assert'][0]['expected_phrases']
                prompts_and_asserts.append([prompt] + expected_kp)
        return prompts_and_asserts
    
    def getProviderInfo(eval_name: str):
        db = EvalConfigDB(eval_name)
        return db.collection.distinct('providers')
    
    def getProviders(eval_name: str):
        return sorted(map(lambda x: x['label'], Evaluator.getProviderInfo(eval_name)))
    
    def getVars(eval_name: str):
        db = EvalConfigDB(eval_name)
        var_list = [item['vars'] for item in db.collection.distinct('prompts_vars_asserts.tests') if 'vars' in item]
        d_vars = {}
        for d in var_list:
            for k, v in d.items():
                d_vars[k] = d_vars.get(k, []) + [v]
        return d_vars
    
    def filterVarsByPrompt(d_vars, prompt):
        vars_prompt = set(re.findall(r"{(\w+)}", prompt))
        return {k: v for k, v in d_vars.items() if k in vars_prompt}
    
    def getEvalInfo(eval_name: str):
        db = EvalDB(eval_name)
        return db.collection.find_one()
    
    def hasAssertion(eval_name: str):
        db = EvalDB(eval_name)
        return db.collection.find_one({'assert': {'$exists': True, '$ne': {}}}) is not None
        
    def processResults(eval_name: str, prompt: str = None, provider: str = None, d_vars: dict = None):
            
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

        eval_info = Evaluator.getEvalInfo(eval_name)
        event_id = eval_info['event_id']

        db = EvalDB(eval_name)
        query = {}
        if prompt:
            query = {'prompt': prompt}
        if provider:
            query |= {'provider.label': provider}
        if d_vars:
            query |= {f'vars.{k}': v for k, v in d_vars.items()}
        if query:
            records_db = db.collection.find(query)
        else:
            records_db = db.getAll().to_list()
            if not records_db: return pd.DataFrame()
            records_db = records_db[1:]

        for item in records_db:
            
            try:
                content = {
                    'Id': f"{event_id}|{item['_id']}",
                    'eval_id': event_id,
                    'Prompt': item['prompt'], 
                    'Model': item['provider']['label'], 
                    'Response': item['response']['output'],
                    'Result': 'No assertion' if not item['response']['results'] else 'Pass' if item['response']['results']['pass'] else 'Fail',
                    'Score':  float(item['response']['results']['score']) if item['response']['results'] else 0,
                    'Reason': getExplanation(item['response']['results'])
                } | item['vars']
                
                results.append(content)

            except Exception as exp:
                print(f'Error reading output from id={item['_id']}')
                print(f"Line number: {exp.__traceback__.tb_lineno}, Description: {exp}\n\n{traceback.format_exc()}")
                continue

        results = pd.DataFrame(results)

        return results
    
        if not Evaluator.hasOutput(eval_name): return pd.DataFrame()

        db = EvalDB(eval_name)

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
    
    # def processEmbeddings(eval_name):
    #     if not Evaluator.hasEmbedding(eval_name): return None
    #     with open(Config.DIR_TESTS / eval_name / 'output' / 'response_embeddings.json') as f:
    #         embeddings = json.load(f)
    #     return embeddings
    
    def runEval(eval_name):

        from src.evaluator.src.evaluation import runTest

        try:
            runTest(eval_name, resume=False, skip_run=False)
        except Exception as exp:
            print(f'Line number: {exp.__traceback__.tb_lineno}, Description: {exp}\n\n{traceback.format_exc()}')
            return False
        return True
    
    # def runSimilarityExtraction(eval_name):

    #     from .evaluator.src.evaluation.generate_response_embeddings import generateSimilarity
        
    #     try:
    #         dir_test = Config.DIR_TESTS / eval_name
    #         generateSimilarity(dir_=dir_test)
    #     except Exception as exp:
    #         print(f'Line number: {exp.__traceback__.tb_lineno}, Description: {exp}\n\n{traceback.format_exc()}')
    #         return False
    #     return True
    
    def createTest(eval_name, config):

        try:
            EvalConfigDB(eval_name).add(config)
            #dir_eval = Config.DIR_TESTS / eval_name
            #dir_eval.mkdir(parents=True, exist_ok=True)
            #saveYML(config, dir_eval / 'config.yaml')
        except Exception as exp:
            print(f"Line number: {exp.__traceback__.tb_lineno}, Description: {exp}\n\n{traceback.format_exc()}")
            return False

        return True