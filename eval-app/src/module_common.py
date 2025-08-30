from shiny import reactive
from shiny.express import ui, module
from .utils_eval import Evaluator
from .utils import Config
import plotly.express as px

@module
def mod_vars(input, output, session, var_name, var_values, fn_reactive):

    @reactive.effect
    @reactive.event(input.select_var)
    def selectVar():
        fn_reactive({var_name: input.select_var()})

    ui.input_select('select_var', var_name[0].upper() + var_name[1:].replace('_', ' '), choices=var_values)

def getEvals(level, eval_set, species):

    levels_allowed = ['base-model', 'rag', 'agentic']
    prompts_allowed = ['basic-prompts', 'tox-type-assertion-prompts', 'abt-qa-assertion-prompts']
    species_allowed = ['human', 'rat', 'mixed']

    eval_dict = {eval_name: index for index, eval_name in enumerate([f'{f}_{p}_{s}' for f in levels_allowed for p in prompts_allowed for s in species_allowed])}

    evals = []
    for test in ['base-model_basic-prompts_human', 'base-model_basic-prompts_rat', 
                 'base-model_tox-type-assertion-prompts_human', 'base-model_tox-type-assertion-prompts_rat',
                 'base-model_abt-qa-assertion-prompts_mixed',
                 'rag_basic-prompts_human', 'rag_basic-prompts_rat',
                 'rag_tox-type-assertion-prompts_human', 'rag_tox-type-assertion-prompts_rat',
                 'rag_abt-qa-assertion-prompts_mixed',
                 'agentic_basic-prompts_human', 'agentic_basic-prompts_rat',
                 'agentic_tox-type-assertion-prompts_human', 'agentic_tox-type-assertion-prompts_rat',
                 'agentic_abt-qa-assertion-prompts_mixed']:
        if Evaluator.hasOutput(test):
            if level != 'any' and not test.startswith(level): continue
            if eval_set != 'any' and eval_set not in test: continue
            if species != 'any' and not test.endswith(level): continue
            if level == 'any': 
                for l in levels_allowed:
                    if test.startswith(l):
                        break
                else:
                    continue
            if eval_set == 'any': 
                for p in prompts_allowed:
                    if p in test:
                        break
                else:
                    continue
            if species == 'any': 
                for s in species_allowed:
                    if test.endswith(s):
                        break
                else:
                    continue
                
            evals.append(test)
    
    return sorted(evals, key=lambda x: eval_dict[x])

def getNoDataPlot(title):
        
    fig = px.scatter(x=[0.5], y=[0.5], text=['No data found<br />or<br />Error in data extraction'], size=[0]) 
    fig.update_layout(
        title=title,
        **Config.CONFIG_PLOT
    )

    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
                        
    return fig