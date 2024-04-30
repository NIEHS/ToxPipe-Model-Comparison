import langchain
from langchain.base_language import BaseLanguageModel
from langchain.tools import BaseTool
from langchain_core.prompts import ChatPromptTemplate

from ..prompts_gene import GENE_PREFIX, GENE_FORMAT_INSTRUCTIONS, GENE_QUESTION_PROMPT, GENE_REPHRASE_TEMPLATE, GENE_SUFFIX


# ("Exoc1", "kidney")


def ge_search(llm, query: str):
    """
    Given a gene and tissue, query the LLM to find the gene expression.
    """
    gene_prompt = ChatPromptTemplate.from_template(f"{GENE_PREFIX}\n\n{GENE_FORMAT_INSTRUCTIONS}\n\n{GENE_QUESTION_PROMPT}\n\n{GENE_SUFFIX}")
    model = llm
    chain = gene_prompt | model
    res = chain.invoke({"query": query})
    return(res.content)


class GeneExpression(BaseTool):
    name = "GeneExpression"
    description = (
        "Given a gene and tissue, query the LLM to find the gene expression."
    )
    llm: BaseLanguageModel = None

    def __init__(self, llm):
        super().__init__()
        self.llm = llm

    def _run(self, query) -> str:
        return ge_search(self.llm, query)

    async def _arun(self, query) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError("this tool does not support async")