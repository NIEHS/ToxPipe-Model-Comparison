import json
import traceback
from shiny.types import SilentException
import pandas as pd
from pathlib import Path

class Config:
    DIR_TESTS = Path(__file__).parent /'tests'
    DIR_CODES = Path(__file__).parent /'codes'
    RANDOM_STATE = 1000
    CONFIG_PLOT = dict(
                        template = 'simple_white',
                        font = dict(
                                    family="Times new roman",
                                    size=16,
                                    color="RebeccaPurple"
                                )
    )

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
                    'Response': item['response']['output'],
                    'Result': 'No assertion' if not item['testCase']['assert'] else 'Pass' if item['success'] else 'Fail',
                    'Variable': ', '.join([f'{k}:{v}' for k, v in item['testCase']['vars'].items()]), 
                    'Reason': getExplanation(item['gradingResult'])
                }
            )
        except Exception as exp:
            print(f"Line number: {exp.__traceback__.tb_lineno}, Description: {exp}\n\n{traceback.format_exc()}")
            raise SilentException()

    return pd.DataFrame(results)