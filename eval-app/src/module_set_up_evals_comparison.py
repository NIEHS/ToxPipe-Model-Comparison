from shiny import reactive, ui as core_ui
from shiny.express import ui, render, module, expressify
from .utils import Config, loadYML, saveYML
from .utils_eval import Evaluator
from .db import EvalDB
import traceback
import datetime
import os
import re

@module
def mod_ui(input, output, session, reload_evals_flag):

    reload_eval_set_flag = reactive.value(True)
    errors = reactive.value([])

    @module
    def mod_eval_info(input, output, session, eval_name):
        with ui.div(class_="col-auto"):
            with ui.card():
                ui.card_header(eval_name)
                @render.express
                def renderEvalInfo():
                    getEvalInfo()

        def showKeyVal(k, v):
            return f"<strong>{k}:</strong><span class='ms-1'>{v}</span>"
        
        @reactive.calc
        @expressify
        def getEvalInfo():

            @expressify
            def getModelInfo(model_list):
                with ui.div(class_='row'):
                    for model in model_list:
                        html = f'<ul>{''.join([f'<li>{showKeyVal(k, v)}</li>' for k, v in model['config'].items()])}</ul>'
                        with ui.div(class_='col-auto'):
                            with ui.card():
                                ui.card_header(model['label']) 
                                ui.HTML(html)

            @expressify
            def getAssertInfo(asserts):
                with ui.div(class_='row'):
                    with ui.div(class_='col-auto'):
                        with ui.card():
                            ui.HTML(f'''<ul>{''.join([f'<li>{ep}</li>' for ep in asserts])}</ul>''')

            model_list = Evaluator.getProviderInfo(eval_name)
            prompts_and_asserts = Evaluator.getPromptsAndAsserts(eval_name)
            with ui.div(class_='row gap-2'):
                ui.strong('Model list')
                with ui.div(class_='border rounded pt-4 cards-container', style='height:200px'):
                    getModelInfo(model_list)
            with ui.div(class_='row gap-2'):
                ui.strong('Prompts')
                with ui.div(class_='border rounded pt-3 cards-container', style='height:200px'):
                    for prompt, *asserts in prompts_and_asserts:
                        ui.HTML(f"<ul><li>{prompt}</li></ul>")
                        if not asserts: continue
                        with ui.div(class_='row gap-2 m-2'):
                            ui.strong('Expected phrases')
                            getAssertInfo(asserts)

    with ui.div(class_="row error m-2"):
        @render.ui
        def showError():
            return ui.HTML(f'<ui>{"".join(["<li>" + e_text + "</li>" for e_text in errors.get()])}</ui>')
    with ui.div(class_='row'):
        with ui.div(class_='col gap-5 border rounded p-5'):
            with ui.div(class_='row'):
                ui.help_text('An eval set consists of multiple evals. Setting up an eval set will facilitate making comparison among the evals that the eval set consists of.')
            with ui.div(class_='row gap-2 mt-4'):
                ui.input_text(id='txt_eval_set_id', label='Eval set ID')
                ui.input_text(id='txt_eval_set_name', label='Eval set Name')
            with ui.div(class_='row'):
                with ui.div(class_='col-3'):
                    ui.input_select(id='select_evals', label='Select evals to compare', choices=[], multiple=True, width='500px', size=10)
                @render.express
                def showAddName():
                    evals = input.select_evals()
                    if not evals: return
                    with ui.div(class_='col-9 d-flex gap-2 p-4 align-items-center', style='overflow-x:auto'):
                        for i, eval_name in enumerate(evals):
                            mod_eval_info(id=f'eval_info_{i}', eval_name=eval_name)
            @render.express
            def showCommonPromptsAmongSelectedEvals():
                prompts_asserts = getCommonPromptsAmongSelectedEvals()
                if prompts_asserts is None:
                    return
                with ui.div(class_='row'):
                    ui.span(f'Selected evals have {len(prompts_asserts)} prompt{'s' if len(prompts_asserts) > 1 else ''} in common')
                                
        with ui.div(class_='col-auto d-flex flex-column gap-2'):
            with ui.div():        
                ui.input_task_button(id='btn_set_up_compare_evals', label='Set up comparison')

    with ui.div(class_='row gap-4 mt-4'):
        ui.strong('Saved eval sets:')
        @render.express
        def showCompareConfig():
            eval_sets = getEvalSetToCompare()

            if not eval_sets: "No eval sets have been set up yet"

            for eval_set_id, v in eval_sets.items():
                eval_set_name = v['Name']
                evals = v['Evals to compare']
                with ui.div(class_="col-3 col-5-sm"):
                    with ui.card():
                        ui.card_header(f'{eval_set_id} - {eval_set_name}')
                        ui.markdown('\n'.join([f'- {eval_name}' for eval_name in evals]))

    @reactive.effect
    @reactive.event(reload_evals_flag)
    def loadEvals():
        ui.update_select(id='select_evals', choices=Evaluator.loadEvalsToRun())

    @reactive.calc
    @reactive.event(reload_eval_set_flag)
    def getEvalSetToCompare():
        try:
            eval_sets = loadYML(Config.DIR_CONFIG / 'compare.yaml')
            assert isinstance(eval_sets, dict), "No eval sets were not set up for comparison"
            return eval_sets
        except:
            return {}
 
    def validateFields(ignore_empty=True):
        
        eval_sets = getEvalSetToCompare()

        errors = []

        val = input.txt_eval_set_id()
        if not (ignore_empty and not val):
            p = re.compile(r'[A-Za-z0-9\-\_]+')
            if not bool(p.fullmatch(val)): errors.append('ID can only contain alphanumeric characters, "-" and "_"')
            elif val and val in eval_sets: errors.append('ID already exists')

        val = input.txt_eval_set_name()
        if not (ignore_empty and not val):
            p = re.compile(r'[A-Za-z0-9 \-\_\,\;\(\)]+')
            if not bool(p.fullmatch(val)): errors.append('Name can only contain alphanumeric characters, space, "-", "_", ",", ";" and "()"')

        evals_sel = input.select_evals()

        if not ignore_empty and len(evals_sel) < 2: 
            errors.append('Please select at least two evals to compare')

        if len(evals_sel) > 2:
            prompts_common = getCommonPromptsAmongSelectedEvals()
            if len(prompts_common) == 0:
                errors.append('* Selected evals must have at least 1 prompt in common')
    
        return errors
    
    @reactive.effect
    @reactive.event(input.txt_eval_set_id, input.txt_eval_set_name, input.select_evals, ignore_init=True)
    def getValidationErrors():
        errors.set(validateFields())

    @reactive.calc
    @reactive.event(input.select_evals)
    def getCommonPromptsAmongSelectedEvals():
        prompts_common = None
        evals_sel = input.select_evals()
        if len(evals_sel) >= 2:
            for eval_name in evals_sel:
                prompts_and_asserts = Evaluator.getPromptsAndAsserts(eval_name)
                prompts_and_asserts = set([tuple(item) for item in prompts_and_asserts])
                if prompts_common is not None:
                    prompts_common &= prompts_and_asserts
                else:
                    prompts_common = prompts_and_asserts
        return prompts_common
    
    @reactive.effect
    @reactive.event(input.btn_set_up_compare_evals)
    def setUpCompareEvals():
        
        errors.set(validateFields(ignore_empty=False))
        if errors.get(): return
        
        eval_set_id = input.txt_eval_set_id()
        eval_set_name = input.txt_eval_set_name()
        
        eval_sets = getEvalSetToCompare()
        eval_sets |= {eval_set_id: {'Name': eval_set_name, 'Evals to compare': list(input.select_evals())}}

        try:
            saveYML(data=eval_sets, file_path=Config.DIR_CONFIG / 'compare.yaml')
            ui.notification_show(f'Comparison was set up successfully', type="message")
            reload_eval_set_flag.set(not reload_eval_set_flag.get())
        except Exception as exp:
            print(f'Line number: {exp.__traceback__.tb_lineno}, Description: {exp}\n\n{traceback.format_exc()}')
            ui.notification_show(f'Comparison was not set up successfully', type="error")