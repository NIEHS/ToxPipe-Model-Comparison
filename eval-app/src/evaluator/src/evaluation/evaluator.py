
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain.output_parsers.fix import OutputFixingParser
from .models import createBaseModel
from pydantic import BaseModel, Field
from typing import Dict, Any, Union
    
class EvaluateResponseSchema(BaseModel):
    '''
    Returns the content to fill the provided outline section
    '''
    pass_: bool = Field(description='Evaluation response.')
    reason: str = Field(description='An appropriate reason.')

class EvaluateResponse:

    prompt_template = '''\
    <QUERY>
    {query}
    </QUERY>

    <ANSWER>
    {answer}
    </ANSWER>

    <PHRASE>
    {phrase}
    </PHRASE>
    '''

    prompt_question = ChatPromptTemplate.from_messages(
        [
            ("system", 
            """
            You are an expert in toxicology and the effects of chemicals on human health. You will be provided QUERY, a ANSWER to the QUERY and a PHRASE. 
            
            <Instructions>
            - Assess the QUERY, ANSWER and PHRASE. 
            - Check if the ANSWER is similar to the PHRASE and relevant to the QUERY. The PHRASE does not necessarily have to be in the ANSWER, but the PHRASE at least need to be semantically similar to the ANSWER.
            - Provide the output in the following format.
            {format_instructions}
            """),
            ("user", prompt_template)
        ]
    )

    def __init__(self, assert_info):
        self.assert_info = assert_info
        llm = createBaseModel({'id': 'openai:chat:azure-gpt-4o', 'config': {'temperature': 0}})
        parser = OutputFixingParser.from_llm(parser=PydanticOutputParser(pydantic_object=EvaluateResponseSchema), 
                                             llm=llm,
                                             max_retries=2)
        
        prompt = self.prompt_question.partial(format_instructions=parser.get_format_instructions())
        
        self.evaluation_chain = prompt | llm | parser

    def getEvaluation(self, response: str, prompt: str) -> Union[bool, float, Dict[str, Any]]:
        
        passed = True
        score = 0
        component_results = []
        expected_keyphrases = self.assert_info[0]['expected_phrases']
        for res_exp in expected_keyphrases:
            res_ = dict(self.evaluation_chain.invoke(input={'query': prompt, 'answer': response, 'phrase': res_exp}))
            passed &= res_['pass_']
            score += int(res_['pass_'])
            component_results.append({'pass': res_['pass_'], 'reason': res_['reason']})

        response = {
            'pass': passed,
            'score': score/len(expected_keyphrases),
            'reason': 'All assertions passed' if passed else 'All assertions did not pass',
            'componentResults': component_results
        }
        
        return response

class SchemaForQueryResponse(BaseModel):
    '''
    Represents the response of user query
    '''
    response: str = Field(description="Text to represent the response to user query")