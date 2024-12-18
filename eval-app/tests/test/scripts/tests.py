from typing import Dict, Any, Union
from sklearn.metrics.pairwise import cosine_similarity, cosine_distances, euclidean_distances
import requests
import dotenv
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from pydantic import BaseModel
from langchain_core.output_parsers import JsonOutputParser
from langfuse.decorators import observe
import pandas as pd
import json

env_config = dotenv.dotenv_values(Path(__file__).parent.parent / ".env")

prompt_template = '''
You will be provided a ANSWER to a QUERY and a PHRASE. Assess the QUERY, ANSWER and PHRASE. 
Check if the ANSWER is similar to the PHRASE and relevant to the QUERY. The PHRASE does not necessarily have to be in the ANSWER, but the PHRASE at least need to be semantically similar to the ANSWER.

Provide your ANSWER with boolean response and a reason with string format.

** Rules **
- DO NOT MAKE UP ANYTHING. USE ONLY THE QUERY, ANSWER AND PHRASE PROVIDED.

** QUERY **
{query}

** ANSWER **
{answer}

** PHRASE **
{phrase}
'''

prompt_question = ChatPromptTemplate.from_messages(
    [
        ("system", 
        """
        You are an expert in toxicology and the effects of chemicals on human health.

        ** RULES ** 
         - Make sure you return a valid JSON output
         - Always respond in the following JSON format:

        ```json
        {{
            "response": false,
            "reason": "An appropriate reason"
        }}
        ```
        """),
        ("user", prompt_template)
    ]
)

class SchemaForSimilaritySearch(BaseModel):
    response: bool

class CustomOutputParser(JsonOutputParser):

    def __init__(self, schema=SchemaForSimilaritySearch):
        super().__init__(pydantic_object=schema)

    def parseResponse(self, data):
        
        try:
            response = self.parse(data.content)
            if not isinstance(response['response'], bool):
                response = {'response': False, 'reason': 'Error in data processing'}
        except:
            return {
                'pass': False,
                'reason': 'Error in data processing'
            }    
        
        return {
                'pass': response['response'],
                'reason': response['reason']
        }

# --------------------------------------------------------------------------------------------
def getOpenAIModel(model_name: str, temperature: int = 0, is_litellm_available: bool = False) -> ChatOpenAI:
    """
    Initializes the OpenAI Chat LLM object based on the LLM name and temperature

    :param model_name: Name of the LLM
    :param temperature: Temperature
    :param is_litellm_available: Boolean flag to indicate if the litellm proxy is accessible
    :return: OpenAI Chat LLM
    """

    if not is_litellm_available:
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            max_tokens=None,
            timeout=None,
            max_retries=2,
            seed=1000
        )

    return ChatOpenAI(
        model=model_name,
        base_url=env_config['OPENAI_BASE_URL'],
        api_key=env_config['OPENAI_API_KEY'],
        temperature=temperature,
        max_tokens=None,
        timeout=None,
        max_retries=2,
        seed=1000
    )

def reqEmbedding(text, embedding):

    response = requests.post(
                url="https://litellm.toxpipe.niehs.nih.gov/embeddings",
                headers={
                    "Authorization": f"Bearer {env_config['OPENAI_API_KEY']}",
                    "Content-Type": "application/json"},
                json={
                    "input": text,
                    "model": embedding,
                    "encoding_format": "float"}
    )

    if response.ok: return response.json()['data'][0]['embedding']
    print(response.text)

@observe
def get_assert(output: str, context) -> Union[bool, float, Dict[str, Any]]:
    
    res_exp_list = context['test']['assert'][0]['expected_phrases']
    
    if not res_exp_list:
        return {'pass': False,
                'score': 0,
                'reason': f'Expected phrases not found {res_exp_list}',
                'componentResults': []
                }
    
    model = getOpenAIModel('azure-gpt-4o', is_litellm_available=True)
    output_parser = CustomOutputParser()

    passed = True
    component_results = []
    for res_exp in res_exp_list:
        res_ = (prompt_question | model | output_parser.parseResponse).invoke(input={'query': context['prompt'], 'answer': output, 'phrase': res_exp})
        passed &= res_['pass']
        component_results.append(res_)

    response = {
        'pass': passed,
        'score': int(passed),
        'reason': 'All assertions passed' if passed else 'All assertions did not pass',
        'componentResults': component_results
    }
    
    return response

def get_assert_distance(output: str, context) -> Union[bool, float, Dict[str, Any]]:
    
    res_exp = ''
    for test_assert in context['test']['assert']['expected_phrases']:
        if test_assert['type'] == 'python':
            res_exp = test_assert['expected']
    
    if not res_exp:
        return {'pass': False,
                'score': 0,
                'reason': 'Expected value not found'
                }
    
    embedding = 'text-embedding-ada-002'
    emb_prompt = reqEmbedding(context['prompt'], embedding)
    emb_res_ret = reqEmbedding(output, embedding)
    emb_res_exp = reqEmbedding(res_exp, embedding)
    
    dist_exp = euclidean_distances([emb_prompt], [emb_res_exp])[0][0]
    dist_ret = euclidean_distances([emb_prompt], [emb_res_ret])[0][0]

    passed = (dist_exp >= dist_ret)

    return {
      'pass': (True if passed else False),
      'score': int(passed),
      'reason': (f'Similar with {res_exp} [Exp: {dist_exp}, Ret: {dist_ret}]\n{context['prompt']}\n{output}\n{res_exp}' if passed else f"Not similar with {res_exp}")
    }