from shiny import reactive, ui as core_ui
from shiny.express import ui, render, module
from codes.create_promptfoo_config import loadYML
from codes.generate_response_embeddings import generateSimilarity
import subprocess
from utils import Config
import traceback
import datetime
import os

@module
def mod_ui(input, output, session):

    with ui.div(class_="row"):
        with ui.div(class_="col gap-5 border rounded p-5"):
            with ui.div(class_="row align-items-center justify-content-between"):
                with ui.div(class_="col"):
                    ui.input_select(id='select_eval', label='Name', choices=[])
                with ui.div(class_="col-auto"):
                    @render.ui
                    def showLastRunInfo():
                        info = loadLastRunTimestamp()
                        return ui.HTML(f'''<div class="row">
                                            <div>Last run time</div>
                                            <div class="col border rounded p-2">
                                                <div class="row gap-1">
                                                    <div class="col text-end"><strong>Eval:</strong></div>
                                                    <div class="col text-start">{info['test']}</div>
                                                </div>
                                                <div class="row gap-1">
                                                    <div class="col text-end"><strong>Response similarity:</strong></div>
                                                    <div class="col text-start">{info['sim']}</div>
                                                </div>
                                            </div>
                                        </div>''')
            with ui.div(class_="row"):
                @render.ui
                def showEvalInfo():

                    def showKeyVal(k, v):
                        return f"<strong>{k}:</strong><span class='ms-1'>{v}</span>"

                    def getModelInfo(model_list):
                        ui_elements = []
                        for model in model_list:
                            html = f'<ul>{''.join([f'<li>{showKeyVal(k, v)}</li>' for k, v in model['config'].items()])}</ul>'
                            ui_elements.append(core_ui.div(
                                                    core_ui.card(
                                                        core_ui.card_header(model['label']), 
                                                        core_ui.HTML(html)
                                                    ),
                                                    class_='col-3 col-4-sm'
                                                )
                            )
                        return core_ui.div(
                                    *ui_elements,
                                    class_='row'
                                )
                    
                    def getTestInfo(test_list):
                        ui_elements = []
                        for test in test_list:
                            html = f'''<ul>
                                        {''.join([f'<li>{showKeyVal(k, v)}</li>' for k, v in test['vars'].items()]) if 'vars' in test else ''}
                                        {f'<li>{showKeyVal('Response key phrases', ', '.join(test['assert'][0]['expected_phrases']))}</li>' if 'assert' in test else ''}
                                    </ul>'''
                            ui_elements.append(core_ui.div(
                                                    core_ui.card(
                                                        core_ui.HTML(html)
                                                    ),
                                                    class_='col-3 col-4-sm'
                                                )
                            )
                        return core_ui.div(
                                    *ui_elements,
                                    class_='row'
                                )
                    
                    info = loadEvalInfo()
                    ui_elements = [
                        core_ui.div(
                            core_ui.div(
                                'Description'
                            ),
                            core_ui.div(
                                info['description'],
                                class_='border rounded p-3'
                            ),
                            class_='row gap-2'
                        ),
                        core_ui.div(
                            core_ui.div(
                                'Model list'
                            ),
                            core_ui.div(
                                getModelInfo(info['providers']),
                                class_='border rounded pt-4 cards-container'
                            ), 
                            class_='row gap-2'
                        ),
                        core_ui.div(
                            core_ui.div(
                                'Prompts'
                            ),
                            core_ui.div(
                                core_ui.HTML(f"<ul>{''.join([f'<li>{p}</li>' for p in info['prompts']])}</ul>"),
                                class_='border rounded pt-3'
                            ), 
                            class_='row gap-2'
                        ),
                        core_ui.div(
                            core_ui.div(
                                'Tests'
                            ),
                            core_ui.div(
                                getTestInfo(info['tests']),
                                class_='border rounded pt-4 cards-container'
                            ),
                            class_='row gap-2'
                        )]
                    return core_ui.div(*ui_elements, class_="col d-flex flex-column gap-3 p-3")
            
        with ui.div(class_='col-auto d-flex flex-column gap-2'):
            with ui.div():        
                ui.input_task_button(id="btn_run_eval", label="Run eval")
            with ui.div():
                ui.input_task_button(id="btn_run_sim", label="Extract Response Similarity")

    @reactive.effect
    def loadEvals():
        tests = sorted([test.name for test in Config.DIR_TESTS.iterdir() if test.is_dir() and (test / 'promptfooconfig.yaml').exists()])
        ui.update_select(id='select_eval', choices=tests)

    @reactive.calc
    @reactive.event(input.select_eval)
    def loadEvalInfo():
        dir_eval = Config.DIR_TESTS / input.select_eval()
        return loadYML(dir_eval / 'promptfooconfig.yaml')
    
    @reactive.calc
    @reactive.event(input.select_eval)
    def loadLastRunTimestamp():
        dir_eval_output = Config.DIR_TESTS / input.select_eval() / 'output'
        timestamp_test = "Not created"
        timestamp_sim = "Not created"

        if (dir_eval_output / 'output.json').exists():
            timestamp_test = datetime.datetime.fromtimestamp(os.path.getmtime(dir_eval_output / 'output.json'))
        if (dir_eval_output / 'response_embeddings.json').exists():
            timestamp_sim = datetime.datetime.fromtimestamp(os.path.getmtime(dir_eval_output / 'response_embeddings.json'))

        return {'test': timestamp_test, 'sim': timestamp_sim}
    
    @reactive.effect
    @reactive.event(input.btn_run_eval)
    def runEval():
        test_name = input.select_eval()
        dir_test = Config.DIR_TESTS / test_name
        path_output = dir_test / 'output' / 'output.json'
        try:
            status = subprocess.run(['promptfoo', 'eval', '-c', str(dir_test), '-o', str(path_output)])
            if status.returncode == 1: 
                ui.notification_show(f'"{test_name}" did not run successfully', type="error")
            else:
                ui.notification_show(f'"{test_name}" ran successfully', type="message")

        except Exception as exp:
            ui.notification_show(f'"{test_name}" did not run successfully', type="error")


    @reactive.effect
    @reactive.event(input.btn_run_sim)
    def runSimilarityExtraction():
        test_name = input.select_eval()
        dir_test = Config.DIR_TESTS / test_name / 'output'
        if not (dir_test / 'output.json').exists():
            ui.notification_show(f'Please run {test_name} before similarity extraction', type="error")
            return
        try:
            generateSimilarity(dir_=dir_test)
            ui.notification_show(f'"{test_name}" response similarity extracted successfully', type="message")
        except Exception as exp:
            print(f'Line number: {exp.__traceback__.tb_lineno}, Description: {exp}\n\n{traceback.format_exc()}')
            ui.notification_show(f'"{test_name}" response similarity extraction did not run successfully', type="error")