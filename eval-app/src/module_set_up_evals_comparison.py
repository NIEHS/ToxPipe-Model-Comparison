from shiny import reactive
from shiny.express import ui, render, module, expressify
import faicons as fa
from .utils import Config, loadYML, saveYML, getUIID
from .utils_eval import Evaluator
import traceback
import re

@module
def mod_ui(input, output, session, reload_evals_flag):

    eval_set_evals = reactive.value({})
    reload_eval_set_flag = reactive.value(True)
    errors = reactive.value([])
    selected_eval_set_id = reactive.value(None)

    @module
    def mod_eval_set(input, output, session, eval_set_id, eval_set_name, evals):
        with ui.div(class_="col-3 col-5-sm"):
            with ui.card():
                ui.card_header(
                    ui.div(f'{eval_set_id} - {eval_set_name}', 
                            ui.div(
                                ui.input_action_link(id='btn_edit_eval_set', label='', icon=fa.icon_svg('pen-to-square', style='solid')), 
                                ui.input_action_link(id='btn_remove_eval_set', label='', icon=fa.icon_svg('trash', style='solid')),
                                class_='d-flex gap-2'
                            ), 
                            class_='d-flex justify-content-between'
                    )
                )
                ui.markdown('\n'.join([f'- {eval_info['Eval Name']} (**{eval_info['Eval Group Name']}**)' for eval_info in evals]))

        @reactive.effect
        @reactive.event(input.btn_edit_eval_set)
        def selectEval():
            selected_eval_set_id.set(eval_set_id)

        @reactive.effect
        @reactive.event(input.btn_remove_eval_set)
        def removeEval():

            eval_sets = getEvalSetToCompare()
            eval_sets = {e_set_id: e_set for e_set_id, e_set in eval_sets.items() if e_set_id != eval_set_id}

            try:
                saveYML(data=eval_sets, file_path=Config.DIR_CONFIG / 'compare.yaml')
                ui.notification_show(f'Eval set was removed successfully', type="message")
                reload_eval_set_flag.set(not reload_eval_set_flag.get())
            except Exception as exp:
                print(f'Line number: {exp.__traceback__.tb_lineno}, Description: {exp}\n\n{traceback.format_exc()}')
                ui.notification_show(f'Eval set was not removed successfully', type="error")

    @module
    def mod_eval_info(input, output, session, eval_name, eval_group_name=''):

        with ui.div(style='min-width:500px'):
            with ui.card():
                ui.card_header(eval_name)
                with ui.div(class_='row gap-2 p-3'):
                    with ui.div(class_='col-auto'):
                        ui.input_text(id='txt_eval_group_name', label='Eval Group', value=eval_group_name)
                    with ui.div(class_='col-auto'):
                        with ui.tooltip(placement="right"):
                            ui.span(fa.icon_svg('circle-question'))
                            'Set the name of the eval group to categorize evals in the comparison report.'
                    
                @render.express
                def renderEvalInfo():
                    getEvalInfo()

        def showKeyVal(k, v):
            return f"<strong>{k}:</strong><span class='ms-1'>{v}</span>"
        
        @reactive.effect
        @reactive.event(input.txt_eval_group_name, ignore_init=True)
        def updateEvalGroupName():
            eval_set_evals.set(eval_set_evals.get() | {eval_name: input.txt_eval_group_name()})
        
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
            @render.express
            def showEditModeControls():
                if (eval_set_id := selected_eval_set_id.get()) is None or not (eval_sets := getEvalSetToCompare()): return
                eval_info = eval_sets[eval_set_id]
                with ui.div(class_='d-flex justify-content-between'):
                    with ui.strong():
                        f'Updating '
                        ui.tags.i(f'"{eval_set_id} - {eval_info['Name']}"')
                    ui.input_action_button(id='btn_cancel_update_eval_set', label='Cancel Update')

                    @reactive.effect
                    @reactive.event(input.btn_cancel_update_eval_set, ignore_init=True)
                    def cancelUpdate():
                        selected_eval_set_id.set(None)
                ui.hr()
            with ui.div(class_='row'):
                ui.help_text('An eval set consists of multiple evals. Setting up an eval set will facilitate making comparison among the evals that the eval set consists of.')
            with ui.div(class_='row gap-2 mt-4'):
                ui.input_text(id='txt_eval_set_id', label='Eval set ID')
                ui.input_text(id='txt_eval_set_name', label='Eval set Name')
            with ui.div(class_='row'):
                with ui.div(class_='col-3'):
                    ui.input_select(id='select_evals', label='Select evals to compare', choices=[], multiple=True, width='500px', size=10)
                @render.express
                def showSelectedEvals():
                    with ui.div(class_='col-9 d-flex gap-2 p-4 align-items-center', style='overflow-x:auto'):
                        for i, (eval_name, eval_group_name) in enumerate(eval_set_evals.get().items()):
                            mod_eval_info(id=getUIID(f'eval_info_{i}'), eval_name=eval_name, eval_group_name=eval_group_name)
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

            for i, (eval_set_id, eval_info) in enumerate(eval_sets.items()):
                eval_set_name = eval_info['Name']
                evals = eval_info['Evals to compare']
                mod_eval_set(id=getUIID(f'eval_set_{i}'), eval_set_id=eval_set_id, eval_set_name=eval_set_name, evals=evals)

    @reactive.effect
    @reactive.event(selected_eval_set_id, ignore_init=True, ignore_none=False)
    def changeSelectedEvalSet():

        eval_set_id = selected_eval_set_id.get()
        eval_sets = getEvalSetToCompare()

        if eval_set_id is None or not eval_sets:
            eval_set_id = ''
            eval_set_name = ''
            eval_names = []
        else:
            eval_info = eval_sets[eval_set_id]
            eval_set_name = eval_info['Name']
            eval_names = [x['Eval Name'] for x in eval_info['Evals to compare']]
        
        ui.update_text(id='txt_eval_set_id', value=eval_set_id)
        ui.update_text(id='txt_eval_set_name', value=eval_set_name)
        ui.update_select(id='select_evals', selected=eval_names)

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
            eval_set_id_selected = selected_eval_set_id.get()
            if not bool(p.fullmatch(val)): errors.append('ID can only contain alphanumeric characters, "-" and "_"')
            elif val and val in eval_sets and val != eval_set_id_selected: errors.append('ID already exists')

        val = input.txt_eval_set_name()
        if not (ignore_empty and not val):
            p = re.compile(r'[A-Za-z0-9 \-\_\\/,\;\(\)]+')
            if not bool(p.fullmatch(val)): errors.append('Name can only contain alphanumeric characters, space, "-", "_", ",", ";", "/" and "()"')

        evals_sel = input.select_evals()

        if not ignore_empty and len(evals_sel) < 2: 
            errors.append('Please select at least two evals to compare')

        if len(evals_sel) > 2:
            prompts_common = getCommonPromptsAmongSelectedEvals()
            if len(prompts_common) == 0:
                errors.append('* Selected evals must have at least 1 prompt in common')
    
        return errors
    
    @reactive.effect
    @reactive.event(input.select_evals)
    def loadSelectedEvals():

        evals = input.select_evals()
        if not evals:
            eval_set_evals.set({})
            return
        
        eval_set_id = selected_eval_set_id.get()
        eval_sets = getEvalSetToCompare()
        eval_set_evals_mapping_from_selected_eval_set = {}
        if eval_set_id is not None:
            eval_set_evals_mapping_from_selected_eval_set = {x['Eval Name']: x['Eval Group Name'] for x in eval_sets[eval_set_id]['Evals to compare']}
        
        eval_set_evals.set({eval_name: eval_set_evals_mapping_from_selected_eval_set.get(eval_name, '') for eval_name in evals})
                        
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
        evals_to_compare = [{'Eval Name': eval_name, 'Eval Group Name': eval_group_name} for eval_name, eval_group_name in eval_set_evals.get().items()]
    
        eval_set_id_selected =  selected_eval_set_id.get()
        eval_set_new = {eval_set_id: {'Name': eval_set_name, 'Evals to compare': evals_to_compare}}
    
        if eval_set_id_selected is not None and eval_set_id != eval_set_id_selected:
            eval_sets[eval_set_id] = eval_sets.pop(eval_set_id_selected)
        
        eval_sets |= eval_set_new
            
        try:
            saveYML(data=eval_sets, file_path=Config.DIR_CONFIG / 'compare.yaml')
            ui.notification_show(f'Comparison was set up successfully', type="message")
            reload_eval_set_flag.set(not reload_eval_set_flag.get())
        except Exception as exp:
            print(f'Line number: {exp.__traceback__.tb_lineno}, Description: {exp}\n\n{traceback.format_exc()}')
            ui.notification_show(f'Comparison was not set up successfully', type="error")