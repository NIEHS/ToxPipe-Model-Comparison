from shiny import reactive, ui as core_ui
from shiny.express import ui, render, module, expressify
from .utils import Config
from .utils_eval import Evaluator
from .db import EvalDB
import traceback
import datetime
import os

@module
def mod_ui(input, output, session, reload_unrun_evals_flag, reload_evals_flag):

    with ui.div(class_="row"):
        with ui.div(class_="col gap-5 border rounded p-5"):
            with ui.div(class_="row align-items-center justify-content-between"):
                with ui.div(class_="col"):
                    ui.input_select(id='select_eval', label='Name', choices=[])
                with ui.div(class_="col-auto"):
                    @render.express
                    def showLastRunInfo():
                        info = loadLastRunTimestamp()
                        with ui.div(class_="row"):
                            with ui.div():
                                "Last run time"
                            with ui.div(class_="col border rounded p-2"):
                                with ui.div(class_="row gap-1"):
                                    with ui.div(class_="col text-end"):
                                        ui.strong('Eval:')
                                    with ui.div(class_="col text-start"):
                                        f'{info['test']}'
                                # with ui.div(class_="row gap-1"):
                                #     with ui.div(class_="col text-end"):
                                #           ui.strong('Response similarity:')
                                #     with ui.div(class_="col text-start"):
                                #           f'{info['sim']}'
            with ui.div(class_="row"):
                @render.express
                def showEvalInfo():

                    def showKeyVal(k, v):
                        return f"<strong>{k}:</strong><span class='ms-1'>{v}</span>"

                    @expressify
                    def getModelInfo(model_list):
                        with ui.div(class_='row'):
                            for model in model_list:
                                html = f'<ul>{''.join([f'<li>{showKeyVal(k, v)}</li>' for k, v in model['config'].items()])}</ul>'
                                with ui.div(class_='col-3 col-4-sm'):
                                    with ui.card():
                                        ui.card_header(model['label']) 
                                        ui.HTML(html)
                    
                    @expressify
                    def getTestInfo(test_list):
                        with ui.div(class_='row'):
                            for test in test_list:
                                html = f'''<ul>
                                            {''.join([f'<li>{showKeyVal(k, v)}</li>' for k, v in test['vars'].items()]) if 'vars' in test else ''}
                                            {f'<li>{showKeyVal('Expected phrases', ', '.join(test['assert'][0]['expected_phrases']))}</li>' if 'assert' in test else ''}
                                        </ul>'''
                                with ui.div(class_='col-3 col-4-sm'):
                                    with ui.card():
                                        ui.HTML(html)
                    
                    config = loadEvalConfig()
                    
                    with ui.div(class_="col d-flex flex-column gap-3 p-3"):
                        with ui.div(class_='row gap-2'):
                            with ui.div():
                                'Description'
                                with ui.div(class_='border rounded p-3'):
                                    config['description']
                                    
                            with ui.div(class_='row gap-2'):
                                with ui.div():
                                    'Model list'
                                with ui.div(class_='border rounded pt-4 cards-container'):
                                    getModelInfo(config['providers'])

                            with ui.div(class_='row gap-2'):
                                with ui.div():
                                    'Prompts'    
                                with ui.div(class_='border rounded pt-3'):
                                    for pva in config['prompts_vars_asserts']:
                                        ui.HTML(f"<ul><li>{pva['prompt']}</li></ul>")
                                        if 'tests' in pva:
                                            with ui.div(class_='row gap-2 m-2'):
                                                getTestInfo(pva['tests'])
            
        with ui.div(class_='col-auto d-flex flex-column gap-2'):
            with ui.div():        
                ui.input_task_button(id="btn_run_eval", label="Run eval")
            # with ui.div():
            #     ui.input_task_button(id="btn_run_sim", label="Extract Response Similarity")

    @reactive.effect
    @reactive.event(reload_unrun_evals_flag)
    def loadEvals():
        ui.update_select(id='select_eval', choices=Evaluator.loadEvalsToRun())

    @reactive.calc
    @reactive.event(input.select_eval)
    def loadEvalConfig():
        return Evaluator.processConfig(input.select_eval())
    
    @reactive.calc
    @reactive.event(input.select_eval)
    def loadLastRunTimestamp():
        eval_name = input.select_eval()
        timestamp_test = "Not run yet"
        timestamp_sim = "Not run yet"

        if Evaluator.hasOutput(eval_name):
            timestamp_test = EvalDB(eval_name).getTimeStamp()
        #if Evaluator.hasEmbedding(eval_name):
        #    timestamp_sim = datetime.datetime.fromtimestamp(os.path.getmtime(Config.DIR_TESTS / eval_name / 'output' / 'response_embeddings.json'))

        return {'test': timestamp_test, 'sim': timestamp_sim}
    
    @reactive.effect
    @reactive.event(input.btn_run_eval)
    def runEval():
        eval_name = input.select_eval()
        try:
            if Evaluator.runEval(eval_name):
                ui.notification_show(f'"{eval_name}" ran successfully', type="message")
                reload_evals_flag.set(not reload_evals_flag.get())
            else: 
                ui.notification_show(f'"{eval_name}" did not run successfully', type="error")
        except Exception as exp:
            print(f'Line number: {exp.__traceback__.tb_lineno}, Description: {exp}\n\n{traceback.format_exc()}')
            ui.notification_show(f'"{eval_name}" did not run successfully', type="error")


    # @reactive.effect
    # @reactive.event(input.btn_run_sim)
    # def runSimilarityExtraction():
    #     eval_name = input.select_eval()
    #     if not Evaluator.hasOutput(eval_name):
    #         ui.notification_show(f'Please run {eval_name} before similarity extraction', type="error")
    #         return
    #     try:
    #         if Evaluator.runSimilarityExtraction(eval_name):
    #             ui.notification_show(f'"{eval_name}" response similarity extracted successfully', type="message")
    #         else:
    #             ui.notification_show(f'"{eval_name}" response similarity extraction did not run successfully', type="error")
    #     except Exception as exp:
    #         print(f'Line number: {exp.__traceback__.tb_lineno}, Description: {exp}\n\n{traceback.format_exc()}')
    #         ui.notification_show(f'"{eval_name}" response similarity extraction did not run successfully', type="error")