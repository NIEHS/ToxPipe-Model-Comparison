from shiny import reactive
from shiny.express import ui, module, render
from .utils import Evaluator
from .module_common import getEvals
import pandas as pd

@module
def mod_ui(input, output, session):

    with ui.div(class_="row gap-5"):
        with ui.div(class_="col d-flex justify-content-start align-items-center gap-2"):
            ui.input_select("select_level", "Levels", choices={'any': 'Any', 'base-model': 'Base model', 'rag': 'RAG', 'agentic': 'Agentic'})
            ui.input_select("select_eval_set", "Eval set", choices={'any': 'Any', 'tox-type-assertion-prompt': 'Tox type prompts', 'abt-qa-assertion-prompts': 'ABT Q/A'})
            ui.input_select("select_species", "Species", choices={'any': 'Any', 'human': 'Human', 'rat': 'Rat'})
            ui.input_select("select_eval", "Evals", choices=[])

        with ui.div(class_="col d-flex pb-3 justify-content-end align-items-end"):
            @render.download(
                filename='eval_report.csv',
                label = 'Download Report'
            )
            async def downloadReport():
                df_report = getReport()
                yield df_report.to_csv()

    with ui.div(class_='row mt-4'):
        with ui.div(class_='col'):
            @render.data_frame
            def renderReport():
                df = getReport()
                return render.DataTable(
                    df.round(2).reset_index().rename(columns={'index': 'Models'}),
                    width='100%',
                    height='100%',
                    styles=[
                            {'rows': [0, 1, 2, 3, 4, 5, 6], 'style': {'background-color': '#f7e9e9'}},
                            {'rows': [7, 8, 9, 10, 11, 12, 13], 'style': {'background-color': "#e9f7ed"}},
                            {'rows': [14], 'style': {'background-color': "#ebe9f7"}},
                            {'cols': None, 'style': {'text-align': 'center'}}
                    ]
                )

    @reactive.calc
    @reactive.event(input.select_level, input.select_eval_set, input.select_species)
    def processEvals():
        return getEvals(level=input.select_level(), eval_set=input.select_eval_set(), species=input.select_species())

    @reactive.effect
    @reactive.event(input.select_level, input.select_eval_set, input.select_species)
    def loadEvalMenu():
        evals = processEvals()
        ui.update_select(id='select_eval', choices=['Any'] + evals)

    @reactive.calc
    @reactive.event(input.select_level, input.select_eval_set, input.select_species)
    def getReport():

        d_eval_prompt = {'tox-type-assertion-prompts_human': 'Toxicity type prompts (Human)',
                         'tox-type-assertion-prompts_rat': 'Toxicity type prompts (Rat)', 
                         'abt-qa-assertion-prompts_mixed': 'ABT Q/A prompts'}
        
        level_names = {'base-model': 'Base model', 'rag': 'RAG', 'agentic': 'Agentic'}

        eval_name = input.select_eval()
        if eval_name == 'Any':
            evals = processEvals()
        else:
            evals = [eval_name]

        level = ''

        df_report = pd.DataFrame()
        d_df_report = {}
        for eval_name in evals + ['dummy_assertion']:
            if 'assertion' not in eval_name: continue

            if level != '':
                if level != eval_name.split('_')[0]:
                    df_report_eval = pd.DataFrame(d_df_report)
                    df_report_eval['Level'] = level_names[level]
                    df_report = pd.concat([df_report, df_report_eval])
                    if eval_name == 'dummy_assertion': continue
                    level = eval_name.split('_')[0]
                    d_df_report = {}
            else:
                level = eval_name.split('_')[0]

            data = Evaluator.processResults(eval_name)
            if data.empty: continue
            total_assertions = data.query('Result != "No assertion"').groupby('Model')['Result'].count()
            data_pass_perc = (data
                                .groupby('Model')['Result']
                                .value_counts()
                                .reset_index()
                                .pivot(index='Model', columns='Result', values='count'))
            
            if data_pass_perc.columns.isin(['Pass']).any(): 
                data_pass_perc.loc[data_pass_perc['Pass'].isna(), 'Pass'] = 0
            else:
                data_pass_perc['Pass'] = 0
            
            data_pass_perc['Assertion'] =  data_pass_perc['Pass'] + data_pass_perc['Fail']
            data_pass_perc['Perc'] = data_pass_perc['Pass'] * 100 / data_pass_perc['Assertion']
            header = f'{d_eval_prompt['_'.join(eval_name.split('_')[1:])]} ({int(total_assertions.iloc[0])})'
            data_pass_perc = data_pass_perc[['Perc']].rename(columns={'Perc': header}).to_dict()

            for k, v in data_pass_perc.items():
                d_df_report[k] = {**d_df_report.get(k, {}), **v}

        return df_report