import json
import traceback
from shiny.types import SilentException
import pandas as pd
from pathlib import Path
import plotly.express as px

class Config:
    DIR_HOME = Path(__file__).parent
    DIR_TESTS = DIR_HOME /'tests'
    DIR_CODES = DIR_HOME /'codes'
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
            print(f'Error reading output from {dir_output}')
            print(f"Line number: {exp.__traceback__.tb_lineno}, Description: {exp}\n\n{traceback.format_exc()}")
            return pd.DataFrame()

    results = pd.DataFrame(results)
    results['eval_id'] = data['evalId']
    
    return results

def processResults1(dir_output):
        
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

def getNoDataPlot(title):
        
    fig = px.scatter(x=[0.5], y=[0.5], text=['No data found<br />or<br />Error in data extraction'], size=[0]) 
    fig.update_layout(
        title=title,
        **Config.CONFIG_PLOT
    )

    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
                        
    return fig