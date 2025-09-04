from utils import Config
from tqdm import tqdm
import re
from pydantic import BaseModel
import json
import pandas as pd
import boto3

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_community.document_loaders import AmazonTextractPDFLoader

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
        base_url=Config.env_config['AI_BASE_URL'],
        api_key=Config.env_config['AI_API_KEY'],
        temperature=temperature,
        max_tokens=None,
        timeout=None,
        max_retries=2,
        seed=1000
    )

# --------------------------------------------------------------------------------------------
class SchemaEntryForQuestionsWithOptions(BaseModel):
    Question: str
    Options: list[str]

class SchemaForQuestionsWithOptions(BaseModel):
    response: list[SchemaEntryForQuestionsWithOptions]

class SchemaEntryForAnswersFromTable(BaseModel):
    Guess: str
    Actual: str

class SchemaForAnswersFromTable(BaseModel):
    response: SchemaEntryForQuestionsWithOptions

class CustomOutputParser(JsonOutputParser):

    def __init__(self, schema=SchemaForQuestionsWithOptions):
        super().__init__(pydantic_object=schema)

    def parseQuestions(self, data):
        try:
            response = self.parse(data.content)
        except:
            response = json.dumps({'Question':data.content, 'Options': []})

        for q in response:
            q['Options'] = ', '.join(q['Options'])
        
        return pd.DataFrame(response)
    
    def parseAnswersInTable(self, data):
        try:
            response = self.parse(data.content)
        except:
            print(data.content)
            response = json.dumps({})
        
        response = pd.DataFrame(response)
        if response.empty: return response
        return response.T.reset_index().rename(columns={'index': 'Questions'})
    
# --------------------------------------------------------------------------------------------
replace = False
model = getOpenAIModel('azure-gpt-4o', is_litellm_available=True)

prompt_template_question_user = '''
Find questions from the text provided below. Each question has multiple choice options. Return the questions with the list of options in JSON format. Always follow the rules below.

** Rules **
- DO NOT MAKE UP ANYTHING. FIND THE QUESTIONS AND THE OPTIONS FROM THE PROVIDED TEXT ONLY.
- Each question must start with a number
- Each option must start with a option number (example: 1, 2, 3, ... or A, B, C, ...)

** Text **
{text}
'''

prompt_question = ChatPromptTemplate.from_messages(
    [
        ("system", 
        """
        You are an assistant that extracts exam questions.
         
        Always respond in the following JSON format:
         ```json
        [
            {{
                "Questions": "",
                "Options": []
            }}
        ]
        ```
         """),
        ("user", prompt_template_question_user)
    ]
)

prompt_template_answer_table_user = '''
There are answers for 100 questions. The question number are listed from 1 to 100. Some of the questions has answer values. Find the guess and actual from the text provided below. Output in JSON format.

** Text **
{text}
'''

prompt_answer_table = ChatPromptTemplate.from_messages(
    [
        ("system", 
         """
         You are an assistant that extracts exam question answers.

         Always respond in the following JSON format:
         ```json
        {{
            "Number": {{
                "Guess": "",
                "Actual": ""
            }}
        }}
        ```
         """),
        ("user", prompt_template_answer_table_user)
    ]
)

output_parser_questions = CustomOutputParser()
output_parser_answers_table = CustomOutputParser(SchemaForAnswersFromTable)

# --------------------------------------------------------------------------------------------
def useAmazonTextract():

    bucket = 'toxpipe-eval-qa-s3-bucket'
    prefix = 'pdf_qa/'  
    session = boto3.session.Session(aws_access_key_id=Config.env_config['AWS_ACCESS_KEY'], aws_secret_access_key=Config.env_config['AWS_SECRET_KEY'])
    client_s3 = session.client('s3')
    result = client_s3.list_objects(Bucket=bucket, Prefix=prefix, Delimiter='/', )

    client_textract = session.client('textract')

    dir_output = Config.DIR_RESULTS / 'amazontextract'
    dir_output.mkdir(parents=True, exist_ok=True)
    
    for obj in result['Contents']:

        file_path = f"s3://{bucket}/{obj['Key']}"
        file_name = file_path.split('/')[-1].split('.')[0]

        if (not replace) and len([_ for _ in (Config.DIR_RESULTS / 'amazontextract').glob(f"{file_name}*.csv")]) > 0: continue

        print("Processing", file_name)
        
        loader = AmazonTextractPDFLoader(file_path, client=client_textract)
        documents = loader.load()

        # extract text
        pages_with_question_headers, pages_with_questions, pages_with_answer_headers, pages_with_answers_table, df_answers = [], [], [], [], pd.DataFrame()
        for doc in tqdm(documents):
            text = doc.page_content
            if text.__contains__('Your results'):
                text_header_answer = re.findall(r'EXAM\s+TAKEN:\s+([\S\ ]+)', text)[0] 
                text_with_answers = re.findall(r'(0\s*(\-\s*)+50\s+(\S{10}\s+){5}key)', text)
                if len(text_with_answers) > 1: print(f"Found multiple answer strings, {text_with_answers}, considering the first one")
                try:
                    answers = list(re.sub(r'\-{2,}', '-', re.sub(r'\s', '', text_with_answers[0][0]))[4:-3])
                except:
                    breakpoint()
                df_answers = pd.concat([df_answers, pd.DataFrame({'Exam': [text_header_answer] * len(answers), 'Answers': answers})])
            elif text.__contains__('ABT Sample Exam Answer Form'):
                text_with_answers_in_table = re.split(r'.*(ABT\ +Sample\ +Exam\ +Answer\ +Form\s+)([\s\S]+)(Exam\ +booklet\ +page\ +no.\ +(\d\ *){4}\S)', text)
                if len(text_with_answers_in_table) < 3: continue
                pages_with_answer_headers.append(text_with_answers_in_table[3])
                pages_with_answers_table.append(text_with_answers_in_table[2])
            else:
                text_with_questions = re.split(r'.*((Recertification((\ )+Exam)?(\ )+\d{4}(\ )+Part(\ )*[A-Z]((\ )*Version(\ )*.)?)|(American Board of Toxicology Sample Examination)|(VERSION . OF EXAM ABT6RB))', text)
                if len(text_with_questions) < 2: continue
                keys = [r'\s+Key\ +for\ +the\ +following\ +questions', r'\s+Choose\ +the\ +single\ +most\ +appropriate\ +answer', 
                        r'\s+Choose\ +[A-Z]\)\ +if\ +((([12](,2)?\ +and)|only)\ +[34])|(all\ +four\ +answers\ +)\ +(is|are)\ +correct']
                text_with_questions[-1] = re.sub(rf'{'|'.join(keys)}', '', text_with_questions[-1])
                pages_with_question_headers.append(text_with_questions[1])
                pages_with_questions.append(text_with_questions[-1])

        if not df_answers.empty: 
            df_answers = df_answers.reset_index().rename(columns={'index': 'Questions'})
            df_answers['Questions'] += 1
            df_answers.to_csv(Config.DIR_RESULTS / 'amazontextract' / f"{file_name}_answers.csv")

        print("Num pages with answer table:", len(pages_with_answers_table))

        df_answers_table = pd.DataFrame()
        for text, header in tqdm(list(zip(pages_with_answers_table, pages_with_answer_headers))):
            df_llm_res = (prompt_answer_table | model | output_parser_answers_table.parseAnswersInTable).invoke(text)
            df_llm_res['Exam'] = header
            df_answers_table = pd.concat([df_answers_table, df_llm_res], ignore_index=True)

        if not df_answers_table.empty:
            df_answers_table[['Exam', 'Questions', 'Guess', 'Actual']].to_csv(Config.DIR_RESULTS / 'amazontextract' / f"{file_name}_answers_table.csv")

        print("Num pages with questions:", len(pages_with_questions))

        df_questions = pd.DataFrame()
        for text, header in tqdm(list(zip(pages_with_questions, pages_with_question_headers))):
            df_llm_res = (prompt_question | model | output_parser_questions.parseQuestions).invoke(text)
            df_llm_res['Exam'] = header
            df_questions = pd.concat([df_questions, df_llm_res], ignore_index=True)

        if not df_questions.empty:
            df_questions[['Exam', 'Questions', 'Options']].reset_index(drop=True).to_csv(Config.DIR_RESULTS / 'amazontextract' / f"{file_name}.csv")

if __name__ == '__main__':
    useAmazonTextract()