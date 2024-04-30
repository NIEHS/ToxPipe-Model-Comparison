# Example script for creating a ToxPipe agent and querying the LLM

from agents import toxpipe as tp

# Must put queries in a function to avoid recursive issue with multithreading
def main():
    # Initialize agent
    tpa = tp.ToxPipeAgent(temp=0.2, max_iterations=40, n_agents=5)
    # Parameters:
    # - temp = 0.0 for less variation, higher values may work better with more parallel agents for a wider berth of responses to summarize from
    # - n_agents - number of agents to run in parallel. Probably keep this at 5 or less to avoid running out of Azure tokens

    chem_res = ""
    chem_res2 = ""

    # Example 1: simple request on a single chemical that does not require ChemBioTox connectivity. Will use RDKit to calculate molecular weight and perform a literature search to find the action mechanism.
    #chem_res = tpa.run("What is the molecular weight and action mechanism of aspirin?")

    # Example 2: simple request on a single chemical that queries ChemBioTox.
    #chem_res = tpa.run("Can you annotate the chemical using the DTXSID DTXSID2020006? In particular, I would like to know if it is used in food or other commercial products and if it is recognized as safe. Include the source for this information.")

    # Example 3: complex request that queries ChemBioTox. First gets metabolites for a chemical, then checks for structural alerts in each metabolite.
    #chem_res = tpa.run("Can you tell me some metabolites for aspirin? For each metabolite in the list you find, could you check if it has any structural alerts?")

    # Example 4: request that queries ChemBioTox to reverse map a SMILES to the closest fit DTXSID If it can't find an exact match in ChemBioTox, it retrieves the DTXSID of the most structurally similar chemical. 
    chem_res = tpa.run("What is the DTXSID for the SMILES: C(=O)(Oc1c(C(=O)O)cc(O)cc1)C?")

    # Example 5: request to get the gene expression data for a gene in a specific tissue. DOes not query ChemBioTox, just uses a literature search or existing LLM knowledge.
    #chem_res = tpa.run("What is the gene expression data for the gene Exoc1 in the kidney?")

    # Example 6: Test memory by asking a followup question w/o the full context. Run both of these.
    #chem_res = tpa.run("Can you provide some information about the possible transporters for aspirin?")
    #chem_res2 = tpa.run("What about some of its metabolites?")

    print(chem_res)
    print(chem_res2)

if __name__ == "__main__":
    main()