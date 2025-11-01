from shiny import reactive
from shiny.express import ui, module, render
from .utils import Config, loadYML
from .utils_eval import Evaluator
import pandas as pd
import re

@module
def mod_ui(input, output, session):

    cache_reloaded_flag = reactive.Value(False)

    with ui.div(class_="row gap-5"):
        with ui.div(class_="col d-flex justify-content-start align-items-center gap-2"):
            ui.input_select("select_eval_set", "Eval sets", choices=[])
        with ui.div(class_="col d-flex pb-1 justify-content-center align-items-center"):
            ui.help_text("Only evals with assertions are shown in the report.")
        with ui.div(class_="col d-flex justify-content-center align-items-center"):
            ui.input_action_button("btn_reload_cache", "Reload cache")

        with ui.div(class_="col d-flex pb-3 justify-content-end align-items-end"):
            @render.download(
                filename='eval_report.csv',
                label = 'Download Report'
            )
            async def downloadReport():
                df_report = getReport()
                yield df_report.to_csv(index=None)

    with ui.div(class_='row mt-4'):
        with ui.div(class_='col'):
            @render.data_frame
            def renderReport():
                df = getReport()
            
                eval_groups = df['Eval Group'].unique()
                eval_group_colors = ['#f7e9e9', '#e9f7ed', '#ebe9f7', '#f7f3e9', '#f0e9f7', '#e9f7f3']
                
                return render.DataTable(
                    df.round(2),
                    width='100%',
                    height='100%',
                    styles=[*[{'rows': df[df['Eval Group'] == eval_group].index.tolist(), 
                               'style': {'background-color': eval_group_colors[i%len(eval_group_colors)]}} for i, eval_group in enumerate(eval_groups)],
                            {'cols': None, 'style': {'text-align': 'center'}}
                    ]
                )
            
    @reactive.calc
    def getEvalSetToCompare():
        try:
            eval_sets = loadYML(Config.DIR_CONFIG / 'compare.yaml')
            assert isinstance(eval_sets, dict), "No eval sets were not set up for comparison"
            return eval_sets
        except:
            return {}
    
    @reactive.effect
    def loadEvalSets():
        eval_sets = getEvalSetToCompare()
        ui.update_select(id='select_eval_set', choices={'any': 'Any'} | {k: v['Name'] for k, v in eval_sets.items() if Evaluator.hasAssertion(k)})

    def hasAssertion(data, col_result):
        if data.empty: return False
        return bool((data[col_result] != 'No assertion').any())

    def generateReport():
        
        eval_set_name = input.select_eval_set()

        eval_sets = getEvalSetToCompare()

        df_report = pd.DataFrame()

        with ui.Progress(min=1, max=len(eval_sets)) as p:
            
            for i, eval_set_name in enumerate(eval_sets.keys()):
                
                if len(eval_sets) > 1:
                    p.set(i+1, message=f"Processing {eval_set_name}")
                else:
                    p.set(message=f"Processing {eval_set_name}")

                df_report_eval = pd.DataFrame()

                for eval_name in eval_sets[eval_set_name]['Evals to compare']:

                    data = Evaluator.processResults(eval_name=eval_name)

                    if data.empty: continue

                    if not hasAssertion(data, 'Result'): continue

                    total_assertions = data.query('Result != "No assertion"').groupby('Model')['Result'].count()
                    header = f'{eval_sets[eval_set_name]['Name']} ({int(total_assertions.iloc[0])})'

                    df_data_score = (data.query('Result != "No assertion"')
                                .groupby('Model')['Score']
                                .mean()
                                .reset_index(name=header)
                                .set_index('Model'))
                    
                    df_data_score['Eval Group'] = eval_name.split('_')[0]
                    
                    df_report_eval = pd.concat([df_report_eval, df_data_score])
                
                if df_report_eval.empty: continue
                
                df_report_eval = df_report_eval.reset_index()

                if df_report.empty: df_report = df_report_eval.copy()
                else: df_report = pd.merge(left=df_report, right=df_report_eval, on=['Model', 'Eval Group'], how='outer')

        cols = ['Model'] + [col for col in df_report.columns if col not in ['Model', 'Eval Group']] + ['Eval Group']
        
        df_report = df_report[cols].sort_values(by=['Eval Group', 'Model']).reset_index(drop=True)
        df_report.to_csv(Config.DIR_CACHE / 'compare_evals_by_table.csv', index=None)

        cache_reloaded_flag.set(not cache_reloaded_flag.get())

    @reactive.effect
    @reactive.event(input.btn_reload_cache)
    def reloadCache():
        generateReport()

    @reactive.calc
    @reactive.event(cache_reloaded_flag, input.select_eval_set)
    def getReport():

        if input.select_eval_set() is None:
            return pd.DataFrame()

        cache_file_path = Config.DIR_CACHE / 'compare_evals_by_table.csv'

        if not cache_file_path.exists():
            generateReport()
        
        df = pd.read_csv(cache_file_path)
        if input.select_eval_set() != 'any':
            return df[input.select_eval_set()] 
        
        return df