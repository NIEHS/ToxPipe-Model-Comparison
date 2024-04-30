from dotenv import load_dotenv
from typing import List
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI
from langchain.chains import LLMChain
from langchain_core.runnables import RunnableParallel
from langchain_core.chat_history import BaseChatMessageHistory, BaseMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.memory import ChatMessageHistory
from langchain_community.chat_message_histories.redis import RedisChatMessageHistory
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.runnables import (
    RunnableLambda,
    ConfigurableFieldSpec,
    RunnablePassthrough,
)
import concurrent.futures
import pathos, multiprocess
from pathos.multiprocessing import ProcessingPool, ThreadPool
import dill
from .agent_toxpipe import ChatZeroShotAgent
from .executor_toxpipe import RetryAgentExecutor
import concurrent.futures
from .multi import *
import pickle, copyreg, ssl

from dotenv import load_dotenv
import os
import langfuse
from langfuse import Langfuse
from langfuse.callback import CallbackHandler
from langfuse.decorators import langfuse_context, observe

load_dotenv('./.env')

from .prompts_chem import FORMAT_INSTRUCTIONS, QUESTION_PROMPT, REPHRASE_TEMPLATE, SUFFIX
from .tools import make_tools


class InMemoryHistory(BaseChatMessageHistory, BaseModel):
    """In memory implementation of chat message history."""

    messages: List[BaseMessage] = Field(default_factory=list)

    def add_messages(self, messages: List[BaseMessage]) -> None:
        """Add a list of messages to the store"""
        self.messages.extend(messages)

    def clear(self) -> None:
        self.messages = []

# Chat history
store = {}
def get_session_history(
    user_id: str, conversation_id: str
) -> BaseChatMessageHistory:
    if (user_id, conversation_id) not in store:
        store[(user_id, conversation_id)] = InMemoryHistory()
    return store[(user_id, conversation_id)]

def _save_sslcontext(obj):
    return obj.__class__, (obj.protocol,)

def _make_llm(model, api_version, temp):
    llm = AzureChatOpenAI(
        openai_api_version=api_version,
        azure_deployment=model,
        temperature=temp,
        model_name=model
    )
    return llm

class ToxPipeAgent:
    """
    ToxPipeAgent is based on the ChemCrow agent that provides a simple interface for querying a LLM using the agent on a given prompt.
    """
    def __init__(
        self,
        model=os.environ.get("AZURE_OPENAI_MODEL"),
        api_version=os.environ.get("OPENAI_API_VERSION"),
        temp=0.1, # higher temperature creates more answer variance, but this is potentially better if we are doing a multi-agent approach
        max_iterations=40,
        n_agents=5, # number of parallel agents to run - set to 1 for no parallelism. Higher values better for more complicated queries to help reduce variance
        verbose=True
    ):
        langfuse_handler = CallbackHandler(
            secret_key=os.environ.get("LANGFUSE_SECRET_API_KEY"),
            public_key=os.environ.get("LANGFUSE_PUBLIC_API_KEY"),
            host=os.environ.get("LANGFUSE_HOST")
        )
        #print(langfuse_handler.auth_check())

        self.llm = _make_llm(model, api_version, temp)
        self.tools = make_tools(self.llm, verbose=verbose)
        self.n_agents = n_agents

        # Initialize agents
        self.agent_executor_chem = RetryAgentExecutor.from_agent_and_tools(
            tools=self.tools,
            agent=ChatZeroShotAgent.from_llm_and_tools(
                self.llm,
                self.tools,
                suffix=SUFFIX,
                format_instructions=FORMAT_INSTRUCTIONS,
                question_prompt=QUESTION_PROMPT,
            ),
            verbose=True,
            max_iterations=max_iterations,
        )

        self.agent_with_chat_history = RunnableWithMessageHistory(
            self.agent_executor_chem,
            get_session_history=get_session_history,
            input_messages_key="input",
            history_messages_key="history",
            history_factory_config=[
        ConfigurableFieldSpec(
            id="user_id",
            annotation=str,
            name="User ID",
            description="Unique identifier for the user.",
            default="",
            is_shared=True,
        ),
        ConfigurableFieldSpec(
            id="conversation_id",
            annotation=str,
            name="Conversation ID",
            description="Unique identifier for the conversation.",
            default="",
            is_shared=True,
        ),
    ],
        )


        rephrase = ChatPromptTemplate.from_template(REPHRASE_TEMPLATE)
        self.rephrase_chain = LLMChain(prompt=rephrase, llm=self.llm, callbacks=[langfuse_handler])


    def run(self, prompt):
        n_agents = self.n_agents
        proc = []
        res = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=n_agents) as executor:
            for i in range(0, n_agents):
                proc.append(executor.submit(run_parallel, self, prompt, i))
        i = 0    
        for future in concurrent.futures.as_completed(proc):
            res.append(f"{i}) {future.result()}")
            i += 1
        res = "\n".join(res)

        summary_prompt_template = """
        Previously, {n_agents} separate LLM agents were run to answer the following prompt from an end user:

        {prompt}

        The following are the raw results from each agent:

        {res}

        Using these responses, reformat the responses into a single response to be returned to the end user.
        IMPORTANT: you MUST follow the following steps when formulating your final response:
            1. This summary should contain the most relevant information from the raw results that answers the original prompt. Try to only include information that is relevant to the original prompt and avoid including any irrelevant information.
            2. If there are any discrepancies between the raw results, try to resolve them in the summary.
            3. If there are any contradictions between the raw results, try to explain why these contradictions exist and what the implications are for the end user.
            4. If there are any uncertainties in the raw results, try to explain why these uncertainties exist and what the implications are for the end user.
            5. If there are any limitations in the raw results, try to explain what these limitations are and how they affect the end user.
            6. If there are any other important details in the raw results that are relevant to the end user, try to include these in the summary as well.
            7. You MUST include a "confidence rating" for each piece of information in the summary that indicates how confident you are in that piece of information. This confidence rating should be the number of agents that returned that piece of information divided by the total number of agents, {n_agents} and formatted as a percentage.
            8. If there is information that is only present in a minority of the agent responses, explain that this information has a low confidence rating.
            9. Rank the information in descending order of confidence, with the most confident items at the top of the list.
            10. If they are available, you must include the source for ALL information returned in the summary. This includes the source for the raw results from each agent as well as the source for any additional information that you include in the summary.
            11. Maintain as much of the original information and formatting as possible from the raw results when creating the final response. This includes any lists, tables, sources, or other formatting that was present in the raw results.
            12. If asked to provide a list of chemicals, like metabolites, you must include the full list in the summary without summarizing or grouping the list.
        """
        summary_prompt = ChatPromptTemplate.from_template(summary_prompt_template)
        summary_chain = summary_prompt | self.llm
        summary = summary_chain.invoke({"n_agents": n_agents, "prompt": prompt, "res": res})

        return summary.content
