# Toxpipe Evaluation Process and Results
Amlan Talukder
May 8, 2026

- [Description](#description)
- [Evaluation Sets](#evaluation-sets)
  - [Levels](#levels)
  - [Query sets](#query-sets)
  - [Chemicals](#chemicals)
  - [Number of queries](#number-of-queries)
- [Evaluation criteria](#evaluation-criteria)
- [Results](#results)

## Description

ToxPipe is evaluated in multiple levels with different sets of queries.
The response at each stage was evaluated based on semantic similarity
with the expected keywords or phrases.

## Evaluation Sets

### Levels

ToxPipe system is evaluated at three levels.

*Base model*

This level includes the following foundational models,

- o3
- GPT-5 (high reasoning)
- GPT-5 (low reasoning)
- GPT-5 Nano
- GPT-4o
- Claude 4.5 Haiku
- Claude 4.5 Sonnet
- Claude 3.7 Sonnet
- Gemini 2.5 Pro
- Gemini 2.5 Flash
- Llama 4 Scout 17B (Instruct)
- Mistral Large 2

*RAG*

In this level, the aforementioned foundational models are used with an
extra RAG (Retrieval Augmented Generation) step.

*MCP*

In this level, the LLMs are exposed to the tools that leverage the
internal databases of ToxPipe using MCP (Model-Chain-Prompt) approach.

<table>
<colgroup>
<col style="width: 6%" />
<col style="width: 93%" />
</colgroup>
<thead>
<tr>
<th style="text-align: left;">Name</th>
<th style="text-align: left;">Description</th>
</tr>
</thead>
<tbody>
<tr>
<td style="text-align: left;">literature_search</td>
<td style="text-align: left;">Given a query, return relevant academic
and scientific papers from PubMed. Use this tool if the user requests a
literature search.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Args:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">query: The query to perform a literature
search on. This should be a string of at least one character and at most
9999 characters. The query should be specific enough to yield relevant
results.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Returns:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">A string containing the results of the
literature search.</td>
</tr>
<tr>
<td style="text-align: left;">rag_search</td>
<td style="text-align: left;">Given a query, return relevant
toxicological information from publications from the National Toxicology
Program (NTP) at https://ntp.niehs.nih.gov/publications. These reports
are retrieved via retrieval-augmented generation (RAG). The publications
include chemical, toxicity, and technical reports. This tool should be
used if the user requests a literature search or a RAG search.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Args:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">query: The query to perform a RAG search
on. This should be a string of at least one character and at most 9999
characters. The query should be specific enough to yield relevant
results.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Returns:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">A string containing the results of the RAG
search, which may include information from the model’s training data
and/or from NTP publications.</td>
</tr>
<tr>
<td style="text-align: left;">is_valid_smiles</td>
<td style="text-align: left;">Given a SMILES string, return whether or
not it is a valid SMILES representation.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Args:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">smiles: A SMILES string representing a
chemical’s structure. This should be a string of at least one character
and at most 255 characters.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Returns:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">A boolean indicating whether or not the
given SMILES string is valid.</td>
</tr>
<tr>
<td style="text-align: left;">smiles_to_mol_weight</td>
<td style="text-align: left;">Given a SMILES string, return the average
molecular weight in g/mol of the chemical.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Args:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">smiles: A SMILES string representing a
chemical’s structure. This should be a string of at least one character
and at most 255 characters.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Returns:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">The average molecular weight in g/mol of
the chemical.</td>
</tr>
<tr>
<td style="text-align: left;">smiles_to_name</td>
<td style="text-align: left;">Given a chemical’s SMILES representation,
return its preferred name. If an exact mapping could not be found, the
most structurally similar chemical’s name is returned instead.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Args:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">smiles: A SMILES string representing a
chemical’s structure. This should be a string of at least one character
and at most 255 characters.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Returns:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">A list of strings, where each string is
structured as follows: chemical_name</td>
</tr>
<tr>
<td style="text-align: left;">casrn_to_name</td>
<td style="text-align: left;">Given a chemical’s CASRN, return its
preferred name.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Args:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">casrn: A string representing the CASRN
number for a chemical. This should be a string of at least one character
and at most 255 characters.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Returns:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">A string representing the preferred name
of the chemical corresponding to the given CASRN. If no chemical with
the given CASRN is found, a string indicating that no chemical name
could be obtained is returned instead.</td>
</tr>
<tr>
<td style="text-align: left;">name_to_canonical_smiles</td>
<td style="text-align: left;">Given the name of a chemical, return its
canonical SMILES representation.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Args:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">chemical_name: A string representing the
preferred name of a chemical. This should be a string of at least one
character and at most 255 characters.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Returns:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">A string representing the canonical SMILES
representation of the chemical corresponding to the given name. If no
chemical with the given name is found, a string indicating that no
SMILES could be obtained is returned instead.</td>
</tr>
<tr>
<td style="text-align: left;">ctd_chemical_to_genes</td>
<td style="text-align: left;">Given the name of a chemical and a
species, return that chemical’s associated gene interactions from the
Comparative Toxicogenomics database (CTD). This tool returns a list of
strings, where each string is an interaction for the given chemical in
the specified species passed to the tool.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Args:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">chemical_name: A string representing the
preferred name of a chemical. This should be a string of at least one
character and at most 255 characters.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">species: A string representing the species
for which gene interactions are requested. Must be exactly one of: Homo
sapiens, Mus musculus, Rattus norvegicus.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Returns:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">A list of strings, where each string is an
interaction for the given chemical in the specified species. If no
interactions are found for the given chemical in the specified species,
an empty list is returned.</td>
</tr>
<tr>
<td style="text-align: left;">ctd_chemical_to_diseases_direct</td>
<td style="text-align: left;">Given the name of a chemical, return that
chemical’s associated diseases with direct evidence (i.e., from a
marker) from the Comparative Toxicogenomics database (CTD).</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Args:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">chemical_name: A string representing the
preferred name of a chemical. This should be a string of at least one
character and at most 255 characters.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Returns:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">A list of strings, where each string is a
disease associated with the given chemical with direct evidence in CTD.
If no diseases with direct evidence associations are found for the given
chemical, an empty list is returned.</td>
</tr>
<tr>
<td style="text-align: left;">ctd_chemical_to_diseases_inferred</td>
<td style="text-align: left;">Given the name of a chemical, return that
chemical’s associated diseases with inferred evidence (i.e., from a
gene) from the Comparative Toxicogenomics database (CTD). The output
from this tool is a list of strings, with each string being of the
format: disease_name</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Args:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">chemical_name: A string representing the
preferred name of a chemical. This should be a string of at least one
character and at most 255 characters.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Returns:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">A list of strings, where each string is a
disease associated with the given chemical with inferred evidence in
CTD, along with the gene from which the association was inferred. If no
diseases with inferred evidence associations are found for the given
chemical, an empty list is returned.</td>
</tr>
<tr>
<td style="text-align: left;">ctd_chemical_to_go_biological_process</td>
<td style="text-align: left;">Given the name of a chemical, return that
chemical’s associated biological process GO terms from the Comparative
Toxicogenomics database (CTD).</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Args:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">chemical_name: A string representing the
preferred name of a chemical. This should be a string of at least one
character and at most 255 characters.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Returns:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">A list of strings, where each string is a
biological process GO term associated with the given chemical in CTD. If
no biological process GO terms are found for the given chemical, an
empty list is returned.</td>
</tr>
<tr>
<td style="text-align: left;">ctd_chemical_to_go_cellular_component</td>
<td style="text-align: left;">Given the name of a chemical, return that
chemical’s associated cellular component GO terms from the Comparative
Toxicogenomics database (CTD).</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Args:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">chemical_name: A string representing the
preferred name of a chemical. This should be a string of at least one
character and at most 255 characters.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Returns:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">A list of strings, where each string is a
cellular component GO term associated with the given chemical in CTD. If
no cellular component GO terms are found for the given chemical, an
empty list is returned.</td>
</tr>
<tr>
<td style="text-align: left;">ctd_chemical_to_go_molecular_function</td>
<td style="text-align: left;">Given the name of a chemical, return that
chemical’s associated molecular function GO terms from the Comparative
Toxicogenomics database (CTD).</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Args:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">chemical_name: A string representing the
preferred name of a chemical. This should be a string of at least one
character and at most 255 characters.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Returns:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">A list of strings, where each string is a
molecular function GO term associated with the given chemical in CTD. If
no molecular function GO terms are found for the given chemical, an
empty list is returned.</td>
</tr>
<tr>
<td style="text-align: left;">tox21_assay_predictions</td>
<td style="text-align: left;">Given the name of a chemical, return that
chemical’s predicted behavior(s) from Tox21 assays. Each item in the
output list contains the assay model name and if the chemical was
predicted to be active or inactive.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Args:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">chemical_name: A string representing the
preferred name of a chemical. This should be a string of at least one
character and at most 255 characters.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Returns:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">A list of strings, where each string
contains the assay model name and if the chemical was predicted to be
active or inactive. The assay model name and activity status are
formatted as follows: assay_model_name: active/inactive. If no Tox21
predictions are found for the given chemical, an empty list is
returned.</td>
</tr>
<tr>
<td style="text-align: left;">drugbank_genes</td>
<td style="text-align: left;">Given the name of a chemical, return that
chemical’s associated gene interactions as documented in DrugBank. This
tool returns a list of strings, where each entry is structured like the
following: gene_name</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Args:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">chemical_name: A string representing the
preferred name of a chemical. This should be a string of at least one
character and at most 255 characters.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Returns:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">A list of strings, where each string is a
gene interaction for the given chemical in DrugBank, structured like the
following: gene_name</td>
</tr>
<tr>
<td style="text-align: left;">drugbank_atccodes</td>
<td style="text-align: left;">Given the name of a chemical, return that
chemical’s therapeutic properties as documented in DrugBank. Use this
tool to retrieve a chemical’s organ interactions, therapeutic use, and
chemical properties.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Args:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">chemical_name: A string representing the
preferred name of a chemical. This should be a string of at least one
character and at most 255 characters.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Returns:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">A list of strings, where each string is a
therapeutic property for the given chemical in DrugBank. If no
therapeutic properties are found for the given chemical, an empty list
is returned.</td>
</tr>
<tr>
<td style="text-align: left;">genra_results</td>
<td style="text-align: left;">Given the name of a chemical, return
corresponding predicted organ interactions, protein interactions, health
effects, associated diseases and neoplasticity, developmental toxicity,
chronic toxicity, sub-chronic toxicity, subacute toxicity, and
reproductive toxicity from the EPA’s Generalized Read Across (GenRA)
tool.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">This tool outputs a list of strings. Each
string is formatted as follows:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">category:subcategory - effect</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Where category may be one of the
following:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">- SAC - Subacute Toxicity</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">- MGR - Multigenerational Reproductive
Toxicity</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">- REP - Reproductive Toxicity</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">- CHR - Chronic Toxicity</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">- DEV - Developmental Toxicity</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">- SUB - Sub-chronic Toxicity</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Args:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">chemical_name: A string representing the
preferred name of a chemical. This should be a string of at least one
character and at most 255 characters.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Returns:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">A list of strings, where each string is a
GenRA prediction for the given chemical, formatted as follows:
category:subcategory - effect. If no GenRA predictions are found for the
given chemical, an empty list is returned.</td>
</tr>
<tr>
<td style="text-align: left;">t3db_targets</td>
<td style="text-align: left;">Given the name of a chemical, return
corresponding targets as documented in the T3DB. This tool can provide
information that can help inform how genes and organs interact with a
chemical.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Args:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">chemical_name: A string representing the
preferred name of a chemical. This should be a string of at least one
character and at most 255 characters.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Returns:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">A list of strings, where each string is a
target associated with the given chemical in T3DB. If no targets are
found for the given chemical, an empty list is returned.</td>
</tr>
<tr>
<td style="text-align: left;">toxrefdb_cancer_effects</td>
<td style="text-align: left;">Given the name of a chemical, return that
chemical’s toxicological cancer-related effects as reported from studies
in ToxRefDB. This tool returns a list of strings, where each item is
formatted as follows:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">effect; toxicity type; species; sex; life
stage; target</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">The toxicity type may be one of the
following:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">- ACU - Acute Toxicity</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">- CHR - Chronic Toxicity</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">- DEV - Developmental Toxicity</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">- DNT - Developmental Neurotoxicity</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">- MGR - Multigenerational Reproductive
Toxicity</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">- NEU - Neurological</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">- OTH - Other</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">- REP - Reproductive Toxicity</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">- SAC - Subacute Toxicity</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">- SUB - Sub-chronic Toxicity</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Args:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">chemical_name: A string representing the
preferred name of a chemical. This should be a string of at least one
character and at most 255 characters.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Returns:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">A list of strings, where each string is a
cancer-related effect for the given chemical in ToxRefDB, formatted as
follows: effect; toxicity type; species; sex; life stage; target. If no
cancer-related effects are found for the given chemical, an empty list
is returned.</td>
</tr>
<tr>
<td style="text-align: left;">toxrefdb_non_cancer_effects</td>
<td style="text-align: left;">Given the name of a chemical, return that
chemical’s toxicological non-cancer-related effects as reported from
studies in ToxRefDB. This tool returns a list of strings, where each
item is formatted as follows:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">effect; study type; species; sex; life
stage; target</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">The study type may be one of the
following:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">- ACU - Acute Toxicity</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">- CHR - Chronic Toxicity</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">- DEV - Developmental Toxicity</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">- DNT - Developmental Neurotoxicity</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">- MGR - Multigenerational Reproductive
Toxicity</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">- NEU - Neurological</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">- OTH - Other</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">- REP - Reproductive Toxicity</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">- SAC - Subacute Toxicity</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">- SUB - Sub-chronic Toxicity</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Args:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">chemical_name: A string representing the
preferred name of a chemical. This should be a string of at least one
character and at most 255 characters.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Returns:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">A list of strings, where each string is a
non-cancer-related effect for the given chemical in ToxRefDB, formatted
as follows: effect; study type; species; sex; life stage; target. If no
non-cancer-related effects are found for the given chemical, an empty
list is returned.</td>
</tr>
<tr>
<td style="text-align: left;">structural_similarity</td>
<td style="text-align: left;">Given a chemical’s SMILES representation
and a Tanimoto similarity threshold, return structurally similar
chemicals with a Tanimoto similarity at or above the specified
threshold. Similarity is calculated using Morgan fingerprints.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Chemicals returned by this tool may be
structurally identical to the input chemical (i.e., synonyms of the
input chemical).</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Args:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">smiles: A SMILES string representing a
chemical’s structure. This should be a string of at least one character
and at most 255 characters.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">threshold: A float representing the
Tanimoto similarity threshold. Unless specified, the threshold is set to
a default value of 0.7. Only chemicals with a similarity at or above
this threshold will be returned.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Returns:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">A list of strings representing
structurally similar chemicals to the original input smiles, where each
string is structured as follows: chemical_name</td>
</tr>
<tr>
<td style="text-align: left;">structural_similarity_nonidentical</td>
<td style="text-align: left;">Given a chemical’s SMILES representation
and a Tanimoto similarity threshold, return structurally similar
chemicals with a Tanimoto similarity at or above the specified
threshold. Similarity is calculated using Morgan fingerprints.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Chemicals returned by this tool cannot be
structurally identical to the input chemical (i.e., no synonyms of the
input chemical).</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Args:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">smiles: A SMILES string representing a
chemical’s structure. This should be a string of at least one character
and at most 255 characters.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">threshold: A float representing the
Tanimoto similarity threshold. Unless specified, the threshold is set to
a default value of 0.7. Only chemicals with a similarity at or above
this threshold will be returned.</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Returns:</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">A list of strings representing
structurally similar chemicals to the original input smiles, where each
string is structured as follows: chemical_name</td>
</tr>
</tbody>
</table>

### Query sets

**Basic**

This query set consists of 27 questions (or prompts) regarding the
overall known or predicted functions and toxicological effects of a
chemical on human and rat biology.

**Toxicity types**

This query set contains the following question for 15 toxicity types
(listed below) and toxicokinetic parameters of a chemical on human and
rat.

*Question*

    List the {effect_type} of {chem_casrn} on human

*Effect Types*

Sub acute, Chronic, Developmental, Immune/lymphatic system, Reproductive
system, Nervous system/Neurological, Digestive system, Urinary system,
Integumentary system, Musculoskeletal system, Cardiovascular system,
Endocrine system, Respiratory system, Hematological system

[**ABT Q/A**](abt-question-ocr.qmd)

This query set contains the questions from American Board of Toxicology
(ABT) certification from the year 2000-2007. These questions have
multiple choices of answer. The questions, answer choices and correct
answers were extracted from exam sheets of respective years. After
filtering ambiguous and unknown answers, the total number of questions
(or prompts) is 474. More information about the extraction process of
ABT Q/A can be found [here](abt-question-ocr.qmd).

**Agent focused**

This query set contains 10 questions that are not likely to be answered
by an LLM without using the RAG step or tools that leverage the internal
databases of ToxPipe.

<table>
<colgroup>
<col style="width: 64%" />
<col style="width: 35%" />
</colgroup>
<thead>
<tr>
<th style="text-align: left;">Question</th>
<th style="text-align: left;">Answer</th>
</tr>
</thead>
<tbody>
<tr>
<td style="text-align: left;">What human drugs that are structural
analogs to CCC(C)(C)C(=O)O<span class="citation"
data-cites="H">[C@@H]</span>1C<a
href="C=C2%5BC@H%5D1%5BC@H%5D(%5BC@H%5D(C=C2)C)CC%5BC@@H%5D3C%5BC@H%5D(CC(=O)O3)O">C@H</a>C?</td>
<td style="text-align: left;">Simvastatin or Lovastatin or
Pravastatin</td>
</tr>
<tr>
<td style="text-align: left;">Identify the chemical is ToxRefDB with the
highest structural similarity to [H][C@]12<a
href="C%5BC@@H%5D(C)C=C1C=C%5BC@H%5D(C)%5BC@@H%5D2CC%5BC@@H%5D1C%5BC@@H%5D(O)CC(=O)O1">C@H</a>OC(=O)C(C)(C)CC.</td>
<td style="text-align: left;">Spirodiclofen</td>
</tr>
<tr>
<td style="text-align: left;">What is the Cramer Class of [H][C@]12<a
href="C%5BC@@H%5D(C)C=C1C=C%5BC@H%5D(C)%5BC@@H%5D2CC%5BC@@H%5D1C%5BC@@H%5D(O)CC(=O)O1">C@H</a>OC(=O)C(C)(C)CC?</td>
<td style="text-align: left;">Class III</td>
</tr>
<tr>
<td style="text-align: left;">What enzyme is inhibited by [H][C@]12<a
href="C%5BC@@H%5D(C)C=C1C=C%5BC@H%5D(C)%5BC@@H%5D2CC%5BC@@H%5D1C%5BC@@H%5D(O)CC(=O)O1">C@H</a>OC(=O)C(C)(C)CC?</td>
<td style="text-align: left;">HMGCoA Reductase</td>
</tr>
<tr>
<td style="text-align: left;">What are the most likely side effects of
C1CC1C(=O)NC2=CC=CC(=C2)NC3=NC=NC(=C3)NC4=CC=CC(=C4)C(F)(F)F?</td>
<td style="text-align: left;">Diarrhea, Rash</td>
</tr>
<tr>
<td style="text-align: left;">What is the most likely in vivo
molecular/pharmacological target of
C1CC1C(=O)NC2=CC=CC(=C2)NC3=NC=NC(=C3)NC4=CC=CC(=C4)C(F)(F)F?</td>
<td style="text-align: left;">EGFR</td>
</tr>
<tr>
<td style="text-align: left;">Which of these 3 chemicals would be likely
lower blood triglycerides:
C1=CC(=CC=C1C(=O)/C=C/C2=CC(=C(C=C2)Cl)Cl)OCC(=O)O or CNC1=CC=C(C=C1)O
or C[C@]12CC[C@H]3<a
href="%5BC@@H%5D1CCC2=O">C@H</a>CCC4=CC(=O)CC[C@]34CO?</td>
<td
style="text-align: left;">C1=CC(=CC=C1C(=O)/C=C/C2=CC(=C(C=C2)Cl)Cl)OCC(=O)O</td>
</tr>
<tr>
<td style="text-align: left;">Which of these 3 chemicals has a mode of
action that is genotoxic: CCNC1=C(C(=O)C2=C(C1=O)<a
href="%5BC@@%5D3(N2C%5BC@H%5D4%5BC@@H%5D3N4)OC">C@H</a>COC(=O)N)C or
C1=CC(=CC=C1C(=O)/C=C/C2=CC(=C(C=C2)Cl)Cl)OCC(=O)O or
CNC1=CC=C(C=C1)O?</td>
<td style="text-align: left;">CCNC1=C(C(=O)C2=C(C1=O)<a
href="%5BC@@%5D3(N2C%5BC@H%5D4%5BC@@H%5D3N4)OC">C@H</a>COC(=O)N)C</td>
</tr>
<tr>
<td style="text-align: left;">Which of these 4 chemicals are likely to
cross the blood brain barrier and be an effective neuroactive agent:
CC1=CC(=C(C=C1)C(C)C)O or CCNC1=C(C(=O)C2=C(C1=O)<a
href="%5BC@@%5D3(N2C%5BC@H%5D4%5BC@@H%5D3N4)OC">C@H</a>COC(=O)N)C or
C1=CC(=CC=C1C(=O)/C=C/C2=CC(=C(C=C2)Cl)Cl)OCC(=O)O or
CNC1=CC=C(C=C1)O?</td>
<td style="text-align: left;">CC1=CC(=C(C=C1)C(C)C)O</td>
</tr>
<tr>
<td style="text-align: left;">What chemical is most likely to be
exported from cells through MDR1/PGP (ie it is a high affinity subtrate
for MDR1): CC<a href="C">C@H</a><span class="citation"
data-cites="H">[C@@H]</span>1<a
href="CC%5BC@@%5D2(O1)C%5BC@@H%5D3C%5BC@H%5D(O2)C/C=C(/%5BC@H%5D(%5BC@H%5D(/C=C/C=C/4\CO%5BC@H%5D5%5BC@@%5D4(%5BC@@H%5D(CC(%5BC@H%5D5O)C)C(=O)O3)O)C)O%5BC@H%5D6C%5BC@@H%5D(%5BC@H%5D(%5BC@@H%5D(O6)C)O%5BC@H%5D7C%5BC@@H%5D(%5BC@H%5D(%5BC@@H%5D(O7)C)O)OC)OC)\C">C@H</a>C
or C1CCC(CC1)(CC(=O)[O-])C[NH3+] or CN(C)CCO?</td>
<td style="text-align: left;">CC<a href="C">C@H</a><span
class="citation" data-cites="H">[C@@H]</span>1<a
href="CC%5BC@@%5D2(O1)C%5BC@@H%5D3C%5BC@H%5D(O2)C/C=C(/%5BC@H%5D(%5BC@H%5D(/C=C/C=C/4\CO%5BC@H%5D5%5BC@@%5D4(%5BC@@H%5D(CC(%5BC@H%5D5O)C)C(=O)O3)O)C)O%5BC@H%5D6C%5BC@@H%5D(%5BC@H%5D(%5BC@@H%5D(O6)C)O%5BC@H%5D7C%5BC@@H%5D(%5BC@H%5D(%5BC@@H%5D(O7)C)O)OC)OC)\C">C@H</a>C</td>
</tr>
</tbody>
</table>

### Chemicals

The following 20 chemicals were tested with basic and toxicity types
prompts.

<table>
<colgroup>
<col style="width: 83%" />
<col style="width: 16%" />
</colgroup>
<thead>
<tr>
<th style="text-align: left;">Chemical</th>
<th style="text-align: left;">CASRN</th>
</tr>
</thead>
<tbody>
<tr>
<td style="text-align: left;">Aspirin</td>
<td style="text-align: left;">50-78-2</td>
</tr>
<tr>
<td style="text-align: left;">Paracetamol</td>
<td style="text-align: left;">103-90-2</td>
</tr>
<tr>
<td style="text-align: left;">Metformin</td>
<td style="text-align: left;">657-24-9</td>
</tr>
<tr>
<td style="text-align: left;">Atorvastatin</td>
<td style="text-align: left;">134523-00-5</td>
</tr>
<tr>
<td style="text-align: left;">Prednisone</td>
<td style="text-align: left;">53-03-2</td>
</tr>
<tr>
<td style="text-align: left;">Dioxin</td>
<td style="text-align: left;">1746-01-6</td>
</tr>
<tr>
<td style="text-align: left;">Benzene</td>
<td style="text-align: left;">71-43-2</td>
</tr>
<tr>
<td style="text-align: left;">Arsenite</td>
<td style="text-align: left;">15502-74-6</td>
</tr>
<tr>
<td style="text-align: left;">Methylmercury</td>
<td style="text-align: left;">16056-34-1</td>
</tr>
<tr>
<td style="text-align: left;">Vinylchloride</td>
<td style="text-align: left;">75-01-4</td>
</tr>
<tr>
<td style="text-align: left;">6PPQ
(N-(1,3-dimethylbutyl)-N’-phenyl-p-phenylenediamine)</td>
<td style="text-align: left;">2754428-18-5</td>
</tr>
<tr>
<td style="text-align: left;">Phenanthrene</td>
<td style="text-align: left;">85-01-8</td>
</tr>
<tr>
<td style="text-align: left;">TPHP (triphenylphosphate)</td>
<td style="text-align: left;">115-86-6</td>
</tr>
<tr>
<td style="text-align: left;">Lanthanum</td>
<td style="text-align: left;">7439-91-0</td>
</tr>
<tr>
<td style="text-align: left;">Galaxolide</td>
<td style="text-align: left;">1222-05-5</td>
</tr>
<tr>
<td style="text-align: left;">1,6-Dimethyl-3,4-dihydroisoquinoline</td>
<td style="text-align: left;">91753-09-2</td>
</tr>
<tr>
<td
style="text-align: left;">2-Methyl-4-(4-methylphenyl)-2,3-dihydro-1,5-benzothiazepine</td>
<td style="text-align: left;">74148-62-2</td>
</tr>
<tr>
<td
style="text-align: left;">N-Cyclopropylmethyl-10,11-dihydro-5H-dibenzo-(a,d)-cyclohepten-5-imine</td>
<td style="text-align: left;">59864-46-9</td>
</tr>
<tr>
<td
style="text-align: left;">4-Methyl-1,2-dihydrobenzo[f]isoquinoline</td>
<td style="text-align: left;">29248-42-8</td>
</tr>
<tr>
<td
style="text-align: left;">6-Methyl-2,5-diphenyl-6H-1,3,4-thiadiazine</td>
<td style="text-align: left;">62625-70-1</td>
</tr>
</tbody>
</table>

### Number of queries

The number of queries in an evaluation set is
`# base models x # prompts x # chemicals x # species`. For ABT Q/A, this
`# base models x # prompts`, as the prompts are not applicable for all
chemicals or species.

<table>
<colgroup>
<col style="width: 17%" />
<col style="width: 13%" />
<col style="width: 23%" />
<col style="width: 10%" />
<col style="width: 23%" />
<col style="width: 13%" />
</colgroup>
<thead>
<tr>
<th style="text-align: left;"></th>
<th style="text-align: left;">Human</th>
<th style="text-align: left;"></th>
<th style="text-align: left;">Rat</th>
<th style="text-align: left;"></th>
<th style="text-align: left;">Mixed</th>
</tr>
</thead>
<tbody>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;">Basic</td>
<td style="text-align: left;">Toxicity types</td>
<td style="text-align: left;">Basic</td>
<td style="text-align: left;">Toxicity types</td>
<td style="text-align: left;">ABT QA</td>
</tr>
<tr>
<td style="text-align: left;"># prompts</td>
<td style="text-align: left;">27</td>
<td style="text-align: left;">15</td>
<td style="text-align: left;">27</td>
<td style="text-align: left;">15</td>
<td style="text-align: left;">474</td>
</tr>
<tr>
<td style="text-align: left;">Base model</td>
<td style="text-align: left;">2700</td>
<td style="text-align: left;">1500</td>
<td style="text-align: left;">2700</td>
<td style="text-align: left;">1500</td>
<td style="text-align: left;">2370</td>
</tr>
<tr>
<td style="text-align: left;">RAG</td>
<td style="text-align: left;">2160</td>
<td style="text-align: left;">1200</td>
<td style="text-align: left;">2160</td>
<td style="text-align: left;">1200</td>
<td style="text-align: left;">1896</td>
</tr>
<tr>
<td style="text-align: left;">Agentic</td>
<td style="text-align: left;">2160</td>
<td style="text-align: left;">1200</td>
<td style="text-align: left;">2160</td>
<td style="text-align: left;">1200</td>
<td style="text-align: left;">1896</td>
</tr>
</tbody>
</table>

## Evaluation criteria

Not all queries have expected keywords or phrases (or assertions). A
response is evaluated by a separate LLM based on semantic similarity
with each of the assertions. A response is labeled as “Passed”, only if
it has semantic similarity with all the assertions.

## Results

Percentage of successful responses to queries in each evaluation sets by
each ToxPipe level. For each evaluation the number of queries with
assertion are mentioned in parenthesis.

<table>
<colgroup>
<col style="width: 27%" />
<col style="width: 10%" />
<col style="width: 15%" />
<col style="width: 19%" />
<col style="width: 18%" />
<col style="width: 8%" />
</colgroup>
<thead>
<tr>
<th style="text-align: left;">Model</th>
<th style="text-align: right;">ABT Q/A (474)</th>
<th style="text-align: right;">Agent focused Q/A (10)</th>
<th style="text-align: right;">Tox type prompts (Human) (57)</th>
<th style="text-align: right;">Tox type prompts (Rat) (12)</th>
<th style="text-align: left;">Eval Group</th>
</tr>
</thead>
<tbody>
<tr>
<td style="text-align: left;">Claude 3.7 Sonnet</td>
<td style="text-align: right;">0.84</td>
<td style="text-align: right;">0.8</td>
<td style="text-align: right;">0.82</td>
<td style="text-align: right;">0.5</td>
<td style="text-align: left;">Base</td>
</tr>
<tr>
<td style="text-align: left;">Claude 4.5 Haiku</td>
<td style="text-align: right;">0.8</td>
<td style="text-align: right;">0.6</td>
<td style="text-align: right;">0.77</td>
<td style="text-align: right;">0.39</td>
<td style="text-align: left;">Base</td>
</tr>
<tr>
<td style="text-align: left;">Claude 4.5 Sonnet</td>
<td style="text-align: right;">0.85</td>
<td style="text-align: right;">0.9</td>
<td style="text-align: right;">0.81</td>
<td style="text-align: right;">0.59</td>
<td style="text-align: left;">Base</td>
</tr>
<tr>
<td style="text-align: left;">GPT-4o</td>
<td style="text-align: right;">0.8</td>
<td style="text-align: right;">0.6</td>
<td style="text-align: right;">0.75</td>
<td style="text-align: right;">0.46</td>
<td style="text-align: left;">Base</td>
</tr>
<tr>
<td style="text-align: left;">GPT-5 (high reasoning)</td>
<td style="text-align: right;">0.87</td>
<td style="text-align: right;">0.7</td>
<td style="text-align: right;">0.81</td>
<td style="text-align: right;">0.46</td>
<td style="text-align: left;">Base</td>
</tr>
<tr>
<td style="text-align: left;">GPT-5 (low reasoning)</td>
<td style="text-align: right;">0.85</td>
<td style="text-align: right;">0.6</td>
<td style="text-align: right;">0.82</td>
<td style="text-align: right;">0.54</td>
<td style="text-align: left;">Base</td>
</tr>
<tr>
<td style="text-align: left;">GPT-5 Nano</td>
<td style="text-align: right;">0.79</td>
<td style="text-align: right;">0.7</td>
<td style="text-align: right;">0.65</td>
<td style="text-align: right;">0.42</td>
<td style="text-align: left;">Base</td>
</tr>
<tr>
<td style="text-align: left;">Gemini 2.5 Flash</td>
<td style="text-align: right;">0.85</td>
<td style="text-align: right;">0.9</td>
<td style="text-align: right;">0.75</td>
<td style="text-align: right;">0.56</td>
<td style="text-align: left;">Base</td>
</tr>
<tr>
<td style="text-align: left;">Gemini 2.5 Pro</td>
<td style="text-align: right;">0.84</td>
<td style="text-align: right;">0.9</td>
<td style="text-align: right;">0.81</td>
<td style="text-align: right;">0.52</td>
<td style="text-align: left;">Base</td>
</tr>
<tr>
<td style="text-align: left;">Llama 4 Scout 17B (Instruct)</td>
<td style="text-align: right;">0.78</td>
<td style="text-align: right;">0.2</td>
<td style="text-align: right;">0.75</td>
<td style="text-align: right;">0.43</td>
<td style="text-align: left;">Base</td>
</tr>
<tr>
<td style="text-align: left;">Mistral Large 2</td>
<td style="text-align: right;">0.7</td>
<td style="text-align: right;">0.4</td>
<td style="text-align: right;">0.71</td>
<td style="text-align: right;">0.44</td>
<td style="text-align: left;">Base</td>
</tr>
<tr>
<td style="text-align: left;">o3</td>
<td style="text-align: right;">0.89</td>
<td style="text-align: right;">0.55</td>
<td style="text-align: right;">0.82</td>
<td style="text-align: right;">0.49</td>
<td style="text-align: left;">Base</td>
</tr>
<tr>
<td style="text-align: left;">Claude 3.7 Sonnet</td>
<td style="text-align: right;">0.87</td>
<td style="text-align: right;">0.9</td>
<td style="text-align: right;">0.78</td>
<td style="text-align: right;">0.43</td>
<td style="text-align: left;">MCP</td>
</tr>
<tr>
<td style="text-align: left;">Claude 4.5 Haiku</td>
<td style="text-align: right;">0.83</td>
<td style="text-align: right;">0.8</td>
<td style="text-align: right;">0.61</td>
<td style="text-align: right;">0.28</td>
<td style="text-align: left;">MCP</td>
</tr>
<tr>
<td style="text-align: left;">Claude 4.5 Sonnet</td>
<td style="text-align: right;">0.86</td>
<td style="text-align: right;">0.9</td>
<td style="text-align: right;">0.67</td>
<td style="text-align: right;">0.33</td>
<td style="text-align: left;">MCP</td>
</tr>
<tr>
<td style="text-align: left;">GPT-4o</td>
<td style="text-align: right;">0.78</td>
<td style="text-align: right;">0.6</td>
<td style="text-align: right;">0.09</td>
<td style="text-align: right;">0.31</td>
<td style="text-align: left;">MCP</td>
</tr>
<tr>
<td style="text-align: left;">GPT-5 (high reasoning)</td>
<td style="text-align: right;">0.87</td>
<td style="text-align: right;">0.9</td>
<td style="text-align: right;">0.77</td>
<td style="text-align: right;">0.17</td>
<td style="text-align: left;">MCP</td>
</tr>
<tr>
<td style="text-align: left;">GPT-5 (low reasoning)</td>
<td style="text-align: right;">0.88</td>
<td style="text-align: right;">0.8</td>
<td style="text-align: right;">0.79</td>
<td style="text-align: right;">0.27</td>
<td style="text-align: left;">MCP</td>
</tr>
<tr>
<td style="text-align: left;">GPT-5 Nano</td>
<td style="text-align: right;">0.79</td>
<td style="text-align: right;">0.6</td>
<td style="text-align: right;">0.62</td>
<td style="text-align: right;">0.39</td>
<td style="text-align: left;">MCP</td>
</tr>
<tr>
<td style="text-align: left;">Gemini 2.5 Flash</td>
<td style="text-align: right;">0.8</td>
<td style="text-align: right;">0.7</td>
<td style="text-align: right;">0.19</td>
<td style="text-align: right;">0.24</td>
<td style="text-align: left;">MCP</td>
</tr>
<tr>
<td style="text-align: left;">Gemini 2.5 Pro</td>
<td style="text-align: right;">0.81</td>
<td style="text-align: right;">0.8</td>
<td style="text-align: right;">0.62</td>
<td style="text-align: right;">0.28</td>
<td style="text-align: left;">MCP</td>
</tr>
<tr>
<td style="text-align: left;">Llama 4 Scout 17B (Instruct)</td>
<td style="text-align: right;">0.74</td>
<td style="text-align: right;">0.6</td>
<td style="text-align: right;">0.02</td>
<td style="text-align: right;">0.12</td>
<td style="text-align: left;">MCP</td>
</tr>
<tr>
<td style="text-align: left;">Mistral Large 2</td>
<td style="text-align: right;">0.64</td>
<td style="text-align: right;">0.7</td>
<td style="text-align: right;">0.19</td>
<td style="text-align: right;">0.1</td>
<td style="text-align: left;">MCP</td>
</tr>
<tr>
<td style="text-align: left;">o3</td>
<td style="text-align: right;">0.88</td>
<td style="text-align: right;">0.8</td>
<td style="text-align: right;">0.72</td>
<td style="text-align: right;">0.38</td>
<td style="text-align: left;">MCP</td>
</tr>
<tr>
<td style="text-align: left;">Toxpipe (RAG) [Claude 3.7 Sonnet]</td>
<td style="text-align: right;">0.86</td>
<td style="text-align: right;">0.7</td>
<td style="text-align: right;">0.77</td>
<td style="text-align: right;">0.5</td>
<td style="text-align: left;">RAG</td>
</tr>
<tr>
<td style="text-align: left;">Toxpipe (RAG) [Claude 4.5 Haiku]</td>
<td style="text-align: right;">0.82</td>
<td style="text-align: right;">0.6</td>
<td style="text-align: right;">0.72</td>
<td style="text-align: right;">0.39</td>
<td style="text-align: left;">RAG</td>
</tr>
<tr>
<td style="text-align: left;">Toxpipe (RAG) [Claude 4.5 Sonnet]</td>
<td style="text-align: right;">0.86</td>
<td style="text-align: right;">0.75</td>
<td style="text-align: right;">0.77</td>
<td style="text-align: right;">0.54</td>
<td style="text-align: left;">RAG</td>
</tr>
<tr>
<td style="text-align: left;">Toxpipe (RAG) [GPT-4o]</td>
<td style="text-align: right;">0.84</td>
<td style="text-align: right;">0.4</td>
<td style="text-align: right;">0.74</td>
<td style="text-align: right;">0.5</td>
<td style="text-align: left;">RAG</td>
</tr>
<tr>
<td style="text-align: left;">Toxpipe (RAG) [GPT-5 High Reasoning]</td>
<td style="text-align: right;">0.88</td>
<td style="text-align: right;">0.7</td>
<td style="text-align: right;">0.77</td>
<td style="text-align: right;">0.45</td>
<td style="text-align: left;">RAG</td>
</tr>
<tr>
<td style="text-align: left;">Toxpipe (RAG) [GPT-5 Low Reasoning]</td>
<td style="text-align: right;">0.89</td>
<td style="text-align: right;">0.6</td>
<td style="text-align: right;">0.76</td>
<td style="text-align: right;">0.31</td>
<td style="text-align: left;">RAG</td>
</tr>
<tr>
<td style="text-align: left;">Toxpipe (RAG) [GPT-5 Nano]</td>
<td style="text-align: right;">0.77</td>
<td style="text-align: right;">0.45</td>
<td style="text-align: right;">0.55</td>
<td style="text-align: right;">0.31</td>
<td style="text-align: left;">RAG</td>
</tr>
<tr>
<td style="text-align: left;">Toxpipe (RAG) [Gemini 2.5 Flash]</td>
<td style="text-align: right;">0.76</td>
<td style="text-align: right;">0.7</td>
<td style="text-align: right;">0.67</td>
<td style="text-align: right;">0.44</td>
<td style="text-align: left;">RAG</td>
</tr>
<tr>
<td style="text-align: left;">Toxpipe (RAG) [Gemini 2.5 Pro]</td>
<td style="text-align: right;">0.79</td>
<td style="text-align: right;">0.55</td>
<td style="text-align: right;">0.73</td>
<td style="text-align: right;">0.45</td>
<td style="text-align: left;">RAG</td>
</tr>
<tr>
<td style="text-align: left;">Toxpipe (RAG) [Llama 4 Scout 17B
(Instruct)]</td>
<td style="text-align: right;">0.75</td>
<td style="text-align: right;">0.55</td>
<td style="text-align: right;">0.69</td>
<td style="text-align: right;">0.42</td>
<td style="text-align: left;">RAG</td>
</tr>
<tr>
<td style="text-align: left;">Toxpipe (RAG) [Mistral Large 2]</td>
<td style="text-align: right;">0.71</td>
<td style="text-align: right;">0.25</td>
<td style="text-align: right;">0.38</td>
<td style="text-align: right;">0.17</td>
<td style="text-align: left;">RAG</td>
</tr>
<tr>
<td style="text-align: left;">Toxpipe (RAG) [o3]</td>
<td style="text-align: right;">0.86</td>
<td style="text-align: right;">0.6</td>
<td style="text-align: right;">0.76</td>
<td style="text-align: right;">0.5</td>
<td style="text-align: left;">RAG</td>
</tr>
</tbody>
</table>
