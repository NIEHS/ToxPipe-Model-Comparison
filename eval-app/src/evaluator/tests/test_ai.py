import pytest
from src.evaluation.executor import Executor

@pytest.fixture(scope='session')
def shared_dataset():
    
    prompt_info = {
        'system': '''You are an expert toxicologist with extensive knowledge in chemical safety assessment, toxicokinetics, and toxicodynamics. Your expertise includes:
1. Interpreting chemical structures and properties 2. Analyzing toxicological data from various sources (e.g., in vitro, in vivo, and in silico studies) 3. Applying read-across and QSAR (Quantitative Structure-Activity Relationship) approaches 4. Understanding mechanisms of toxicity and adverse outcome pathways 5. Evaluating systemic availability based on ADME (Absorption, Distribution, Metabolism, Excretion) properties 6. Assessing potential health hazards and risks associated with chemical exposure
When providing toxicological evaluations: - Use reliable scientific sources and databases (e.g., PubChem, ECHA, EPA, IARC) - Consider both experimental data and predictive models - Explain your reasoning and cite relevant studies or guidelines - Acknowledge uncertainties and data gaps - Provide a balanced assessment, considering both potential hazards and mitigating factors - Use a weight-of-evidence approach when multiple data sources are available - Classify toxicodynamic activity and systemic availability as high, medium, or low based on  the available evidence and expert judgment - When using read-across, clearly state the basis for the analogy and any limitations
Adhere to ethical standards in toxicology and maintain scientific objectivity in your assessments.''',
        'user': 'Answer the following question with a list of string. List the {effect_type} of {chemical_and_CASRN} on human'
    }
    vars_info = {
        'chemical_and_CASRN': 'Arsenite (CAS number: 15502-74-6)', 
        'effect_type': 'Sub acute toxicity'
    }

    return prompt_info, vars_info

def run_and_validate_executor(model_info, prompts_info, vars_info):
    
    response = Executor(model_info, prompts_info, vars_info).execute()

    assert isinstance(response, dict), f'Response is not in correct format, expected "dict", found response: {response}'
    assert 'output' in response and 'error' in response, f'Response is expected to have "output" and "error, found response: {response}'
    assert isinstance(response['output'], str), f'Response output is not in the correct format, expect "str", found response["output"]: {response['output']}'
    assert isinstance(response['error'], str), f'Response error is not in the correct format, expect "str", found response["error"]: {response['error']}'
    assert response['error'].strip() == '', f'Response has errors, response["error"]: {response['error']}'

def test_agent_base(shared_dataset):

    model_info = {
                        'id': 'azure-gpt-5.5',
                        'label': 'GPT-5.5 (high reasoning)',
                        'func': 'queryLLM',
                        'config': {
                            'temperature': 0,
                            'reasoning_effort': 'high'
                        }
                    }

    prompts_info, vars_info = shared_dataset
    run_and_validate_executor(model_info, prompts_info, vars_info)

def test_agent_rag(shared_dataset):

    model_info = {
                        'id': 'azure-gpt-5.5',
                        'label': 'GPT-5.5 (high reasoning)',
                        'func': 'queryToxPipeRAG',
                        'config': {
                            'temperature': 0,
                            'reasoning_effort': 'high'
                        }
                    }
    
    prompts_info, vars_info = shared_dataset
    run_and_validate_executor(model_info, prompts_info, vars_info)

def test_agent_mcp(shared_dataset):

    model_info = {
                    'id': 'azure-gpt-5.5',
                    'label': 'GPT-5.5 (high reasoning)',
                    'func': 'queryToxPipeMCP',
                    'config': {
                        'temperature': 0,
                        'reasoning_effort': 'high'
                    }
                }

    prompts_info, vars_info = shared_dataset
    run_and_validate_executor(model_info, prompts_info, vars_info)