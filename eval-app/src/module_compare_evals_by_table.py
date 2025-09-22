from shiny import reactive
from shiny.express import ui, module, render
from .utils import Config, loadYML
from .utils_eval import Evaluator
import pandas as pd
import re

@module
def mod_ui(input, output, session):

    with ui.div(class_="row gap-5"):
        with ui.div(class_="col d-flex justify-content-start align-items-center gap-2"):
            ui.input_select("select_eval_set", "Eval sets", choices=[])
        with ui.div(class_="col d-flex pb-1 justify-content-start align-items-end"):
            ui.input_checkbox("chk_hide_no_assertion_evals", "Hide unlabeled evals", value=True)

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
                return render.DataTable(
                    df.round(2),
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
    def getEvalSetToCompare():
        try:
            return loadYML(Config.DIR_CONFIG / 'compare.yaml')
        except:
            return {}
    
    @reactive.effect
    def loadEvalSets():
        eval_sets = getEvalSetToCompare()
        ui.update_select(id='select_eval_set', choices={'any': 'Any'} | {k: v['Name'] for k, v in eval_sets.items()})

    def hasAssertion(data, col_result):
        if data.empty: return False
        if len(data[col_result].unique()) == 0: return False
        return not (data[col_result].unique() == ['No assertion']).all()

    @reactive.calc
    @reactive.event(input.select_eval_set, input.chk_hide_no_assertion_evals)
    def getReport():
        
        eval_set_name = input.select_eval_set()

        eval_sets = getEvalSetToCompare()

        if input.select_eval_set() != 'any':
            eval_sets = {eval_set_name: eval_sets[eval_set_name]}

        df_report = pd.DataFrame()

        with ui.Progress(min=1, max=len(eval_sets)) as p:
            
            for i, eval_set_name in enumerate(eval_sets.keys()):
                
                if len(eval_sets) > 1:
                    p.set(i+1, message=f"Processing {eval_set_name}")
                else:
                    p.set(message=f"Processing {eval_set_name}")

                if input.chk_hide_no_assertion_evals() and 'assertion' not in eval_set_name: continue

                df_report_eval = pd.DataFrame()

                for [eval_name_key, eval_name] in eval_sets[eval_set_name]['Evals to compare']:

                    data = Evaluator.processResults(eval_name=eval_name)

                    if data.empty: continue

                    if not hasAssertion(data, 'Result'):
                        header = f'{eval_sets[eval_set_name]['Name']} (0)'
                        df_data_score = pd.DataFrame() 
                        df_data_score['Model'] = sorted(data['Model'].unique())
                        df_data_score[header] = 'No assertion'
                        df_data_score = df_data_score.set_index('Model')
                        df_data_score['Level'] = eval_name_key
                        df_report_eval = pd.concat([df_report_eval, df_data_score])
                        continue

                    total_assertions = data.query('Result != "No assertion"').groupby('Model')['Result'].count()
                    header = f'{eval_sets[eval_set_name]['Name']} ({int(total_assertions.iloc[0])})'

                    df_data_score = (data.query('Result != "No assertion"')
                                .groupby('Model')['Score']
                                .mean()
                                .reset_index(name=header)
                                .set_index('Model'))
                    
                    df_data_score['Level'] = eval_name_key
                    
                    df_report_eval = pd.concat([df_report_eval, df_data_score])
                
                if not df_report.empty and (df_report['Level'] == df_report_eval['Level']).all(): df_report = df_report.drop(columns='Level')
                df_report = pd.concat([df_report, df_report_eval], axis=1)

        return df_report.reset_index()