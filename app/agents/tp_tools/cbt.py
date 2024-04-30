import os
import re
import pandas as pd
import requests
import json
import time
import urllib.parse
from langchain.tools import BaseTool
from langchain.base_language import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from random import sample
load_dotenv()

def unique(l):
    ls = set(l)
    unique_list = (list(ls))
    return unique_list

class Query2DTXSID(BaseTool):
    name = "Query2DTXSID"
    description = "Given a chemical name as input, returns the DSSTox substance ID or DTXSID for that chemical from the ChemBioTox database."

    def __init__(
        self,
    ):
        super().__init__()

    def _run(self, name: str) -> str:
        """Input a chemical name, return its DSSTox substance ID (DTXSID) available in ChemBioTox."""
        name = name.rstrip()
        res = requests.get(f"{os.environ.get('CBT_API_ENDPOINT')}/name2dtxsid?name={name}")
        res = res.json()
        if len(res) < 1:
            return(f"There was a problem completing the request.")
        response = f"The chemical {name} does not map to a DSSTox Substance ID in the ChemBioTox Database."
        if len(res) > 0:
            response = f"The chemical {name} has the following DSSTox Substance ID in the ChemBioTox Database: {res[0]['dsstox_substance_id']}."
        return(response)
    
class SMILES2DTXSID(BaseTool):
    name = "SMILES2DTXSID"
    description = "Given a SMILES string as input, returns the DSSTox substance ID or DTXSID for that chemical from the ChemBioTox database. If no DTXSID exists, the tool will return the DTXSID of the most structurally similar chemical in the ChemBioTox database."

    def __init__(
        self,
    ):
        super().__init__()

    def _run(self, name: str) -> str:
        """Input a SMILES string, return its DSSTox substance ID (DTXSID) if available in ChemBioTox."""
        name = name.rstrip()
        res = requests.get(f"{os.environ.get('CBT_API_ENDPOINT')}/smiles2dtxsid?smiles={urllib.parse.quote_plus(name)}")
        res = res.json()
        if len(res) < 1:
            return(f"There was a problem completing the request.")
        response = f"The chemical {name} does not map to a DSSTox Substance ID in the ChemBioTox Database."
        if len(res) > 0:
            if 'similarity' in res[0]:
                if res[0]['similarity'] == 1:
                    response = f"The chemical {name} has the following DSSTox Substance ID in the ChemBioTox Database: {res[0]['dsstox_substance_id']}."
                else:
                    response = f"The chemical {name} does not map to a DSSTox Substance ID in the ChemBioTox Database, but is structurally similar to a chemical that does: {res[0]['dsstox_substance_id']} (Tanimoto similarity: {res[0]['similarity']})."
        return(response)


class QueryCBTFooDB(BaseTool):
    name = "QueryCBTFooDB"
    description = "Given a DSSTox substance ID or DTXSID as input, annotates a chemical with information about its usage in food or ingestible products from the ChemBioTox database. This can be useful if the user is looking for exposure, usage, or industrial information about a chemical."

    def __init__(
        self,
    ):
        super().__init__()

    def _run(self, dtxsid: str) -> str:
        """Input DSSTox substance ID (DTXSID), return an annotated/enriched dataset for that chemical using the data available in ChemBioTox."""
        dtxsid = re.sub(r'\s+', '', dtxsid)
        res = requests.get(f"{os.environ.get('CBT_API_ENDPOINT')}/foodb?dtxsid={dtxsid}")
        res = res.json()
        if len(res) < 1:
            return(f"There was a problem completing the request.")

        """
        print(res["anno_foodb_enzymes"])
        print(res["anno_foodb_flavors"])
        print(res["anno_foodb_foodcontent"])
        print(res["anno_foodb_healtheffects"])
        
        print(res["anno_foodb_ontology"])
        """

        
        # FooDB
        """
        foodb_enzymes = res["anno_foodb_enzymes"]
        foodb_enzymes_list = []
        for i in foodb_enzymes:
            foodb_enzymes_list.append(i['prod_type'])
        """
        
        foodb_flavors = res["anno_foodb_flavors"]
        foodb_flavors_list = []
        for i in foodb_flavors:
            if 'flavor_name' not in i:
                continue
            foodb_flavors_list.append(i['flavor_name'])
        foodb_flavors_list = unique(foodb_flavors_list)
        
        foodb_ontology = res["anno_foodb_ontology"]
        foodb_ontology_list = []
        for i in foodb_ontology:
            print(i)
            if 'definition' not in i:
                continue
            foodb_ontology_list.append(i['term'])
        foodb_ontology_list = unique(foodb_ontology_list)

        response_flavors = f"The chemical {dtxsid} has the following flavors (retrieved from the FooDB): {';'.join(foodb_flavors_list)}"
        response_ontology = f"The chemical {dtxsid} also has the following ontological properties (retrieved from the FooDB): {';'.join(foodb_ontology_list)}"

        response = f"{response_flavors}. {response_ontology}"
        return(response)

    async def _arun(self, dtxsid: str) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError()

class QueryCBTCPD(BaseTool):
    name = "QueryCBTCPD"
    description = "Given a DSSTox substance ID or DTXSID as input, annotates a chemical with information about its usage in commercial products from the ChemBioTox database. This can be useful if the user is looking for exposure, usage, or industrial information about a chemical."

    def __init__(
        self,
    ):
        super().__init__()

    def _run(self, dtxsid: str) -> str:
        """Input DSSTox substance ID (DTXSID), return an annotated/enriched dataset for that chemical using the data available in ChemBioTox."""
        dtxsid = re.sub(r'\s+', '', dtxsid)
        res = requests.get(f"{os.environ.get('CBT_API_ENDPOINT')}/cpd?dtxsid={dtxsid}")
        res = res.json()
        if len(res) < 1:
            return(f"There was a problem completing the request.")

        cpd = res['anno_cpd']
        cpd_list = []
        for i in cpd:
            if 'prod_type' not in i:
                continue
            cpd_list.append(i['prod_type'])

        cpd_list = unique(cpd_list)

        response = f"The chemical {dtxsid} is used in the following commercial products (retrieved from the Chemical Products Database): {';'.join(cpd_list)}"
        if len(cpd_list) < 1:
            response = f"The chemical {dtxsid} is not known to be in any commercial products in the Chemical Products Database."

        return(response)

    async def _arun(self, dtxsid: str) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError()

class QueryCBTGRAS(BaseTool):
    name = "QueryCBTGRAS"
    description = "Given a DSSTox substance ID or DTXSID as input, annotates a chemical with information about if it is generally recognized as safe from the ChemBioTox database"

    def __init__(
        self,
    ):
        super().__init__()

    def _run(self, dtxsid: str) -> str:
        """Input DSSTox substance ID (DTXSID), return an annotated/enriched dataset for that chemical using the data available in ChemBioTox."""
        dtxsid = re.sub(r'\s+', '', dtxsid)
        res = requests.get(f"{os.environ.get('CBT_API_ENDPOINT')}/gras?dtxsid={dtxsid}")
        res = res.json()
        if len(res) < 1:
            return(f"There was a problem completing the request.")

        gras = res['anno_gras']
        gras_list = []
        for i in gras:
            if 'prod_type' not in i:
                continue
            gras_list.append(i['prod_type'])
        
        gras_list = unique(gras_list)

        response = f"The chemical {dtxsid} has the following safety information (retrieved from the GRAS Database): {';'.join(gras_list)}"
        if len(gras_list) < 1:
            response = f"The chemical {dtxsid} does not have any safety information in the GRAS Database."
        return(response)

    async def _arun(self, dtxsid: str) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError()
    
class QueryCBTDiseases(BaseTool):
    name = "QueryCBTDiseases"
    description = "Given a DSSTox substance ID or DTXSID as input, annotates a chemical with information about if it is associated with diseases from the ChemBioTox database"

    def __init__(
        self,
    ):
        super().__init__()

    def _run(self, dtxsid: str) -> str:
        """Input DSSTox substance ID (DTXSID), return an annotated/enriched dataset for that chemical using the data available in ChemBioTox."""
        dtxsid = re.sub(r'\s+', '', dtxsid)
        res = requests.get(f"{os.environ.get('CBT_API_ENDPOINT')}/ctd?dtxsid={dtxsid}")
        res = res.json()
        if len(res) < 1:
            return(f"There was a problem completing the request.")
        ctd_diseases = res['anno_ctd_diseases']
        ctd_diseases_list = []
        for i in ctd_diseases:
            if 'disease_name' not in i:
                continue
            ctd_diseases_list.append(i['disease_name'])

        ctd_diseases_list = unique(ctd_diseases_list)

        response = f"The chemical {dtxsid} is associated with the following diseases (retrieved from the CTD): {';'.join(ctd_diseases_list)}"
        if len(ctd_diseases_list) < 1:
            response = f"The chemical {dtxsid} does not have any disease information in the CTD."
        return(response)

    async def _arun(self, dtxsid: str) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError()

def format_leadscope(llm, response):
    model = llm
    leadscope_prompt = """
        For the following list of Leadscope model descriptions, provide a formatted response. You MUST use the following rules:
        1. Each model in the prediction was found to be positive for the given chemical.
        2. [model] is a summary of the model description.
        3. Each prediction must be in the format: "The chemical [chemical] has a positive prediction for the [model] model."
        4. Each prediction must be on a new line.
        5. You MUST include the overall accuracy of the prediction, if supplied.
        6. You do not need to include the phrase "Predicts whether or not" in the response as it is assumed that the model returns only models that have a positive prediction.
        The list of Leadscope descriptions is as follows: {response}
    """
    leadscope_prompt = ChatPromptTemplate.from_template(leadscope_prompt)

    chain = leadscope_prompt | model
    res = chain.invoke({"response": response})
    return res

class QueryCBTLeadscope(BaseTool):
    name = "QueryCBTLeadscope"
    description = "Given a DSSTox substance ID or DTXSID as input, annotates a chemical with predicted Leadscope QSAR models from the ChemBioTox database."

    llm: BaseLanguageModel = None

    def __init__(self, llm):
        super().__init__()
        self.llm = llm

    def _run(self, dtxsid: str) -> str:
        """Input DSSTox substance ID (DTXSID), return an annotated/enriched dataset for that chemical using the data available in ChemBioTox."""
        dtxsid = re.sub(r'\s+', '', dtxsid)
        res = requests.get(f"{os.environ.get('CBT_API_ENDPOINT')}/leadscope?dtxsid={dtxsid}&positives=TRUE")
        res = res.json()
        if len(res) < 1:
            return(f"There was a problem completing the request.")
        
        leadscope = res
        leadscope_list = []
        for i in leadscope:
            print(i)
            if 'short_description' not in i:
                continue
            leadscope_list.append(i['short_description'])

        leadscope_list = unique(leadscope_list)

        response = f"The chemical {dtxsid} has the following positive predictions for the following Leadscope models: {';'.join(leadscope_list)}"
        if len(leadscope_list) < 1:
            response = f"The chemical {dtxsid} does not have any positive predictions for Leadscope models."
        else:
            response = format_leadscope(self.llm, response)

        return(response)
        

    async def _arun(self, dtxsid: str) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError()

def format_admet(llm, response):
    model = llm
    admet_prompt = """
        For the following list of ADMET model descriptions, provide a formatted response. You MUST use the following rules:
        1. Each model in the prediction was found to be positive for the given chemical.
        2. Each prediction must be in the format: "The chemical [chemical] has a positive prediction for the [model] model."
        3. Each prediction must be on a new line.
        4. You MUST include the overall accuracy of the prediction, if supplied.
        5. You do not need to include the phrase "Predicts whether or not" in the response as it is assumed that the model returns only models that have a positive prediction.
        The list of ADMET descriptions is as follows: {response}
    """
    admet_prompt = ChatPromptTemplate.from_template(admet_prompt)

    chain = admet_prompt | model
    res = chain.invoke({"response": response})
    return res

class QueryCBTADMET(BaseTool):
    name = "QueryCBTADMET"
    description = "Given a DSSTox substance ID or DTXSID as input, annotates a chemical with predicted ADMET QSAR models from the ChemBioTox database. This can be helpful for understanding the absorption, distribution, metabolism, excretion, pathways, transportation, and toxicity of a chemical."

    llm: BaseLanguageModel = None

    def __init__(self, llm):
        super().__init__()
        self.llm = llm

    def _run(self, dtxsid: str) -> str:
        """Input DSSTox substance ID (DTXSID), return an annotated/enriched dataset for that chemical using the data available in ChemBioTox."""
        dtxsid = re.sub(r'\s+', '', dtxsid)
        res = requests.get(f"{os.environ.get('CBT_API_ENDPOINT')}/admet?dtxsid={dtxsid}&positives=TRUE")
        res = res.json()
        if len(res) < 1:
            return(f"There was a problem completing the request.")
        
        admet = res
        admet_list = []
        for i in admet:
            if 'description' not in i:
                continue
            admet_list.append(i['description'])

        admet_list = unique(admet_list)

        response = f"The chemical {dtxsid} has the following positive predictions for the following ADMET models: {';'.join(admet_list)}"
        if len(admet_list) < 1:
            response = f"The chemical {dtxsid} does not have any positive predictions for ADMET models."
        else:
            response = format_admet(self.llm, response)

        return(response)
        

    async def _arun(self, dtxsid: str) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError()
    
class QueryCBTMetabolites(BaseTool):
    name = "QueryCBTMetabolites"
    description = "Given a DSSTox substance ID or DTXSID as input, generate metabolites of the chemical from ADMET predictor with corresponding enzymes used in the metabolism."

    llm: BaseLanguageModel = None

    def __init__(self, llm):
        super().__init__()
        self.llm = llm

    def _run(self, dtxsid: str) -> str:
        """Input DSSTox substance ID (DTXSID), return an annotated/enriched dataset for that chemical using the data available in ChemBioTox."""
        dtxsid = re.sub(r'\s+', '', dtxsid)
        res = requests.get(f"{os.environ.get('CBT_API_ENDPOINT')}/metabolites?dtxsid={dtxsid}&enzyme=both&maxlevel=3")
        res = res.json()
        if len(res) < 1:
            return(f"There was a problem completing the request.")
        
        metabolites = res
        metabolites_list = []
        for i in metabolites:
            if 'smiles' not in i:
                continue
            metab_str = i['smiles']
            if 'enzymes' in i:
                metab_str = i['smiles'] + " (" + re.sub(r';', ',', i['enzymes']) + ")"
            metabolites_list.append(metab_str)

        metabolites_list = unique(metabolites_list)

        #response = f"The chemical {dtxsid} has the following predicted metabolites: {';'.join(metabolites_list)}. Do not use the Query2DTXSID tool to convert these SMILES strings to DTXSID. This satisfies the requirement for finding metabolites, and you may return the final answer without running this tool again."
        response = f"The chemical {dtxsid} has the following predicted metabolites: {';'.join(metabolites_list)}. This satisfies the requirement for finding metabolites, and you may return the final answer without running this tool again."
        if len(metabolites_list) < 1:
            response = f"The chemical {dtxsid} does not have any predicted metabolites."

        return(response)
        

    async def _arun(self, dtxsid: str) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError()


class QueryCBTSEEM3(BaseTool):
    name = "QueryCBTSEEM3"
    description = "Given a DSSTox substance ID or DTXSID as input, annotates a chemical with its SEEM3 exposure data. This can be helpful for finding the exposure, pathways, or transportation of a chemical."

    llm: BaseLanguageModel = None

    def __init__(self, llm):
        super().__init__()
        self.llm = llm

    def _run(self, dtxsid: str) -> str:
        """Input DSSTox substance ID (DTXSID), return an annotated/enriched dataset for that chemical using the data available in ChemBioTox."""
        dtxsid = re.sub(r'\s+', '', dtxsid)

        res = requests.get(f"{os.environ.get('CBT_API_ENDPOINT')}/seem3?dtxsid={dtxsid}")
        res = res.json()

        if len(res) < 1:
            return(f"There was a problem completing the request.")
        
        exp = res
        exp_list = []
        for i in exp:
            if 'annotations' not in i:
                continue
            exp_list.append(i['annotations'])

        exp_list = unique(exp_list)

        response = f"The chemical {dtxsid} has the following estimate of the upper 95th percentile of exposure in the general population (SEEM3): {';'.join(exp_list)}"
        if len(exp_list) < 1:
            response = f"The chemical {dtxsid} does not have any SEEM3 exposure data in the ChemBioTox Database."

        return(response)
        

    async def _arun(self, dtxsid: str) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError()
    
class QueryCBTDrugBankTransporters(BaseTool):
    name = "QueryCBTDrugBankTransporters"
    description = "Given a DSSTox substance ID or DTXSID as input, annotates a chemical with its DrugBank transporter data. This can be helpful for finding the pathway or transportation information for a chemical."

    llm: BaseLanguageModel = None

    def __init__(self, llm):
        super().__init__()
        self.llm = llm

    def _run(self, dtxsid: str) -> str:
        """Input DSSTox substance ID (DTXSID), return an annotated/enriched dataset for that chemical using the data available in ChemBioTox."""
        dtxsid = re.sub(r'\s+', '', dtxsid)

        res = requests.get(f"{os.environ.get('CBT_API_ENDPOINT')}/drugbank?dtxsid={dtxsid}")

        res = res.json()

        if len(res) < 1:
            return(f"There was a problem completing the request.")

        res = res['anno_drugbank_transporters']
        
        transporters = res
        transporters_list = []
        for i in transporters:
            if 'annotation' not in i:
                continue
            transporters_list.append(i['annotation'])

        transporters_list = unique(transporters_list)

        response = f"The chemical {dtxsid} has transporters encoded by the following genes in the DrugBank database: {';'.join(transporters_list)}"
        if len(transporters_list) < 1:
            response = f"The chemical {dtxsid} does not have any transporter information in the DrugBank database."

        return(response)
        

    async def _arun(self, dtxsid: str) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError()
    

class QueryCBTAlerts(BaseTool):
    name = "QueryCBTAlerts"
    description = "Given a SMILES string as input, find structural alerts from the OChem, ChEMBL, and Saagar datasources within the ChemBioTox database."

    llm: BaseLanguageModel = None

    def __init__(self, llm):
        super().__init__()
        self.llm = llm

    def _run(self, smiles: str) -> str:
        """Input SMILES, return an annotated/enriched dataset for that chemical using the data available in ChemBioTox."""
        smiles = re.sub(r'\s+', '', smiles)
        res = requests.get(f"{os.environ.get('CBT_API_ENDPOINT')}/alerts?smiles={urllib.parse.quote_plus(smiles)}")
        res = res.json()
        if len(res) < 1:
            return(f"There was a problem completing the request.")

        alerts = res
        alerts_list = []
        for i in alerts:
            if 'alert' not in i:
                continue
            alert_str = f"{i['alert']} ({i['source']})"
            alerts_list.append(alert_str)

        alerts_list = unique(alerts_list)

        response = f"The chemical given by the SMILES {smiles} has the following chemical substructures of note: {';'.join(alerts_list)}."
        if len(alerts_list) < 1:
            response = f"The chemical given by the SMILES {smiles} does not have any notable chemical substructures."

        return(response)
        

    async def _arun(self, dtxsid: str) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError()

def format_alerts(llm, response):
    model = llm
    alert_prompt = """
        For the following list of chemical structural alerts, provide a formatted response. You MUST use the following rules:
        1. Each alert in the list was found to be a chemical substructure of the given chemical.
        2. Each alert in the list is followed by its source in parentheses.
        3. You must group alerts together based on if they are from OChem, ChEMBL, or Saagar.
        4. Each group of alerts must be separated by a new line.
        5. For each group of alerts, your response must be in the format: "Source: [source] | Alert: [alert]."
        The list of chemical structural alerts is as follows: {response}
    """
    alert_prompt = ChatPromptTemplate.from_template(alert_prompt)

    chain = alert_prompt | model
    res = chain.invoke({"response": response})
    return res

class QueryCBTAlertsMulti(BaseTool):
    name = "QueryCBTAlertsMulti"
    description = "Given multiple SMILES strings that represent metabolites as input, separated by ';', find structural alerts from the OChem, ChEMBL, and Saagar datasources within the ChemBioTox database. Each metabolite's results will be separated by two newline characters: '\n\n'."

    llm: BaseLanguageModel = None

    def __init__(self, llm):
        super().__init__()
        self.llm = llm

    def _run(self, smiles: str) -> str:
        """Input SMILES, return an annotated/enriched dataset for that chemical using the data available in ChemBioTox."""
        response_list = []
        smiles = re.sub(r'\s+', '', smiles)
        for metabolite in smiles.split(';'):
            res = requests.get(f"{os.environ.get('CBT_API_ENDPOINT')}/alerts?smiles={urllib.parse.quote_plus(metabolite)}")
            res = res.json()
            if len(res) < 1:
                return(f"There was a problem completing the request.")

            alerts = res
            alerts_list = []

            alerts_list_ochem = []
            alerts_list_chembl = []
            alerts_list_saagar = []

            for i in alerts:
                if 'alert' not in i:
                    continue
                alert_str = f"{i['alert']} ({i['source']})"
                if i['source'] == 'ochem':
                    alerts_list_ochem.append(alert_str)
                elif i['source'] == 'chembl':
                    alerts_list_chembl.append(alert_str)
                elif i['source'] == 'saagar':
                    alerts_list_saagar.append(alert_str)

            # taking subset makes the thought process much faster
            alerts_list_ochem = unique(alerts_list_ochem)
            if len(alerts_list_ochem) > 10:
                alerts_list_ochem = sample(alerts_list_ochem, 10)

            alerts_list_chembl = unique(alerts_list_chembl)
            if len(alerts_list_chembl) > 10:
                alerts_list_chembl = sample(alerts_list_chembl, 10)

            alerts_list_saagar = unique(alerts_list_saagar)
            if len(alerts_list_saagar) > 10:
                alerts_list_saagar = sample(alerts_list_saagar, 10)

            alerts_list = alerts_list_ochem + alerts_list_chembl + alerts_list_saagar

            print("here 1")

            #tmp_response = f"The metabolite given by the SMILES {metabolite} has the following chemical substructures of note: {';'.join(alerts_list)}."
            tmp_response = f"The metabolite given by the SMILES {metabolite} has the following chemical substructures of note:\n"
            if len(alerts_list) < 1:
                tmp_response = f"The metabolite given by the SMILES {metabolite} does not have any notable chemical substructures."
            else:
                for alert in alerts_list:
                    tmp_response = f"{tmp_response}- {alert}\n"
            #    tmp_response = format_alerts(self.llm, tmp_response)
            
            response_list.append(tmp_response)


        return("\n\n".join(response_list))
        

    async def _arun(self, dtxsid: str) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError()