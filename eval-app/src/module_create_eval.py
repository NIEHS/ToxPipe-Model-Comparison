
from shiny import reactive, ui as core_ui
from shiny.express import ui, render, module, expressify
from shiny.types import SilentException
import traceback
import json
import faicons as fa
import re
from .utils import Config, loadYML, getUIID
from .utils_eval import Evaluator
from .db import EvalConfigDB

def logexp(func):
    def wrapper(*args, **kargs):
        try:
            ret = func(*args, **kargs)
        except Exception as exp:
            print(f'Line number: {exp.__traceback__.tb_lineno}, Description: {exp}\n\n{traceback.format_exc()}')
        except SilentException as exp:
            print(f'Line number: {exp.__traceback__.tb_lineno}, Description: {exp}\n\n{traceback.format_exc()}')
        return ret
    return wrapper

@module
def mod_ui(input, output, session, reload_unrun_evals_flag):

    model_info = reactive.value([])
    prompt_vars_kp = reactive.value([{'prompt': '', 'vars_kp': [], 'kp': set(), 'status': 'active'}])
    reload_prompts_flag = reactive.value(True)
    errors = reactive.value([])

    @module
    def showModelConfig(input, output, session, model_category_id, model_options):

        with ui.card():
            with ui.card_header():
                with ui.div(class_='d-flex justify-content-between align-items-center'):
                    with ui.div():
                        model_options['label']
                    with ui.div():
                        ui.input_action_button(id='btn_add_model', label='', icon=fa.icon_svg("plus", "solid"))
            with ui.div(class_='row'):
                with ui.div(class_='col-auto'):
                    ui.input_text(id='txt_model_label', label='Label', placeholder='Add a label')
                with ui.div(class_='col-auto'):
                    with ui.tooltip(placement="right"):
                        ui.span(fa.icon_svg('circle-question'))
                        "A distinct label helps to recognize this setting"
            for k, v in model_options['config'].items():
                if isinstance(v['type'], list):
                    ui.input_select(id=f'select_model_config_{k}', label=v['label'], choices=v['type'], selected=v['default'])
                elif v['type'] == 'int':
                    if 'min' in v and 'max' in v:
                        ui.input_slider(id=f'txt_model_config_{k}', label=v['label'], min=int(v['min']), max=int(v['max']), value=int(v['default']), step=0.1)
                    else:
                        ui.input_text(id=f'txt_model_config_{k}', label=v['label'], value=int(v['default']))

        @reactive.effect
        @reactive.event(input.btn_add_model, ignore_init=True)
        def addModel():

            if not input.txt_model_label(): 
                errors.set(['Model label is not provided.'])
                return
            
            new_model_config = {}
            for k, v in model_options['config'].items():
                if isinstance(v['type'], list):
                    new_model_config[k] = input[f'select_model_config_{k}']()
                elif v['type'] == 'int':
                    if 'min' in v and 'max' in v:
                        new_model_config[k] = input[f'txt_model_config_{k}']()
                    else:
                        new_model_config[k] = input[f'txt_model_config_{k}']
            
            val = model_info.get().copy()
            new_model = model_options.copy()
            new_model['id'] = model_category_id
            new_model['label'] = input.txt_model_label()
            new_model['config'] = new_model_config
            for m in val:
                if m == new_model: break
                if m['label'] == new_model['label']:
                    errors.set([f'Label {new_model['label']} is already used for another model.'])
                    return
            else:
                model_info.set(val + [new_model])
                errors.set([])

    @module
    def showSelectedModel(input, output, session, model):
        
        html = f'<ul>{''.join([f'<li><strong>{k}:</strong><span class="ms-1">{v}</span></li>' for k, v in model['config'].items()])}</ul>'
        with ui.div(class_='col-auto'):
            with ui.card():
                with ui.card_header():
                    with ui.div(class_='d-flex justify-content-between align-items-center'):
                        with ui.div():
                            model['label']
                        with ui.div(class_='position-relative'):
                            ui.input_action_button(id='btn_remove_model', label='', icon=fa.icon_svg("xmark", "solid"))
                ui.HTML(html)

        @reactive.effect
        @reactive.event(input.btn_remove_model, ignore_init=True)
        def removeModel():
            val = model_info.get().copy()
            model_info.set([m for m in val if m != model])

    @module
    def kpContainer(input, output, session, index_prompt, index_vars_kp, kp):

        with ui.div(class_='position-relative border rounded p-2', style='width:fit-content'):
            ui.input_action_link(id='btn_remove_kp', label='', icon=fa.icon_svg("circle-xmark", "regular"), class_='remove-ico small')
            with ui.div():
                kp
        
        @reactive.effect
        @reactive.event(input.btn_remove_kp, ignore_init=True)
        def removeKeyword():
            val = prompt_vars_kp.get().copy()
            if index_vars_kp < 0:
                val[index_prompt]['kp'].remove(kp)
            else:
                val[index_prompt]['vars_kp'][index_vars_kp]['kp'].remove(kp)
            prompt_vars_kp.set(val)
    
    @module
    def kpBoxContainer(input, output, session, index_prompt, kp_values=set(), index_vars_kp=-1):

        with ui.div(class_='d-flex flex-column gap-2 pt-3'):
            with ui.div(class_='d-flex'):
                with ui.div(class_='d-flex justify-content-start'):
                    ui.input_text(id='text_keyphrase', label="Expected phrases (optional)")
                with ui.div(class_='d-flex justify-content-start'):
                    with ui.tooltip(placement="right"):
                        ui.span(fa.icon_svg('circle-question'))
                        "Phrases that the response should contain. High similarity with these phrases will be used to rank a response."
                with ui.div(class_='d-flex align-items-center pt-3'):
                    ui.input_action_button(id='btn_add_keyword', label="Add")

            with ui.div(class_='d-flex flex-wrap gap-2'):
                with ui.div(class_='d-contents'):
                    for kp in sorted(kp_values):
                        kpContainer(id=getUIID('kp'), index_prompt=index_prompt, index_vars_kp=index_vars_kp, kp=kp)

        @reactive.effect
        @reactive.event(input.text_keyphrase, ignore_init=True)
        def showAddButton():
            ui.update_action_button('btn_add_keyword', disabled=not input.text_keyphrase())

        @reactive.effect
        @reactive.event(input.btn_add_keyword, ignore_init=True)
        def addKeyword():
            kp = input.text_keyphrase().strip()
            ui.update_text(id='text_keywords', value='')
            if kp == '': return

            val = prompt_vars_kp.get().copy()
            if index_vars_kp < 0:
                val[index_prompt]['kp'].add(kp)
            else:
                val[index_prompt]['vars_kp'][index_vars_kp]['kp'].add(kp)
            prompt_vars_kp.set(val)
    
    @module
    def varKpContainer(input, output, session, index_prompt, index_vars_kp, vars_kp_info):

        var_content = ui.HTML(f"<ul>{''.join([f"<li><strong>{k}:</strong><span class='ms-1'>{v}</span></li>" for k, v in vars_kp_info['vars']])}</ul>")
        with ui.div(style='width:400px'):
            with ui.div(class_='position-relative border rounded p-2', style='width:fit-content'):
                ui.input_action_link(id='btn_remove_var_kp', label='', icon=fa.icon_svg("circle-xmark", "regular"), class_='remove-ico small')
                with ui.div():
                    var_content
                kpBoxContainer(id=getUIID('kpbox'), index_prompt=index_prompt, index_vars_kp=index_vars_kp, kp_values=vars_kp_info['kp'])

        @reactive.effect
        @reactive.event(input.btn_remove_var_kp, ignore_init=True)
        def removeVar():
            val = prompt_vars_kp.get().copy()
            val[index_prompt]['vars_kp'][index_vars_kp]['status'] = 'deleted'
            prompt_vars_kp.set(val)
    
    @module
    def promptVarsAndKPContainer(input, output, session, index_prompt, prompt_text, reload_prompts_flag):

        with ui.div(class_='position-relative border rounded p-3'):
            if index_prompt > 0:
                ui.input_action_link(id='btn_remove_prompt', label='', icon=fa.icon_svg("circle-xmark", "regular"), class_='remove-ico large')
            
            with ui.div(class_='row'):
                with ui.div(class_='col'):
                    ui.input_text_area(id='txt_prompt', label='Prompt', value=prompt_text, rows=5, width='100%', 
                                    placeholder='What is the function of Aspirin?\nor\nWhat is the function of {chemname}?')
                with ui.div(class_='col-auto'):
                    with ui.tooltip(placement="right"):
                        ui.span(fa.icon_svg('circle-question'))
                        "You can also use variable for a prompt using curly braces. e.g. What is the function of {chemname}?"

            with ui.div(class_='row'):
                with ui.div(class_='col'):
                    @render.express
                    def showVars():
        
                        variables = extractPromptVars()
                        
                        val = prompt_vars_kp.get()[index_prompt]

                        if not variables:
                            kpBoxContainer(id=getUIID('kpbox'), index_prompt=index_prompt, kp_values=val['kp'])
                            return
                        
                        with ui.div(class_='row border rounded p-2 m-2'):
                            with ui.div(class_='row'):
                                with ui.div(class_='col'):
                                    with ui.div(class_='row'):
                                        for var_name in variables:
                                            with ui.div(class_='col-3'):
                                                ui.input_text(id=f'txt_var_{var_name}', label=var_name)

                                    if val['vars_kp']:
                                        with ui.div(class_='d-flex gap-2'):
                                            for index, vars_kp_info in enumerate(val['vars_kp']):
                                                if val['status'] == 'deleted': continue
                                                varKpContainer(id=getUIID('varkp'), index_prompt=index_prompt, index_vars_kp=index, vars_kp_info=vars_kp_info)
                                                
                                with ui.div(class_='col-auto'):
                                    ui.input_action_button(id='btn_add_var', label="Add")
                        
        def validatePromptVars(variables):
            p = re.compile(r'[A-Za-z0-9\-\_]+')
            return [val for val in variables if bool(p.fullmatch(val))]

        @reactive.calc
        @reactive.event(input.txt_prompt)
        def extractPromptVars():
            prompt = input.txt_prompt()
            variables = re.findall(rf'{Evaluator.PROMPT_VAR_FORMAT}', prompt) 
            return validatePromptVars(variables)
        
        @reactive.effect
        @reactive.event(input.txt_prompt, ignore_init=True)
        def addPromptVars():
            prompt = input.txt_prompt()
            val = prompt_vars_kp.get().copy()
            val[index_prompt] = {'prompt': prompt, 'vars_kp': [], 'kp': set(), 'status': 'active'} 
            prompt_vars_kp.set(val)
        
        @reactive.effect
        @reactive.event(input.btn_remove_prompt, ignore_init=True)
        def removePrompt():
            val = prompt_vars_kp.get().copy()
            val[index_prompt]['status'] = 'deleted'
            prompt_vars_kp.set(val)
            reload_prompts_flag.set(not reload_prompts_flag.get())

        @reactive.effect
        def showAddButton():
            variables = extractPromptVars()
            for var_name in variables:
                id_ = f'txt_var_{var_name}'
                var_val = input[id_]().strip()
                if var_val == '': 
                    ui.update_action_button('btn_add_var', disabled=True)
                    return
            ui.update_action_button('btn_add_var', disabled=False)

        @reactive.effect
        @reactive.event(input.btn_add_var, ignore_init=True)
        def addVarValues():

            variables = extractPromptVars()

            var_info = []

            for var_name in variables:
                id_ = f'txt_var_{var_name}'
                var_val = input[id_]().strip()
                if var_val == '': return
                ui.update_text(id=id_, value='')
                var_info.append((var_name, var_val))
            
            if not var_info: return

            val = prompt_vars_kp.get().copy()
            val[index_prompt]['vars_kp'].append({'vars': var_info, 'kp': set(), 'status': 'active'})
            prompt_vars_kp.set(val)

    with ui.div(class_="row error m-2"):
        @render.ui
        def showError():
            return ui.HTML(f'<ui>{"".join(["<li>" + e_text + "</li>" for e_text in errors.get()])}</ui>')

    with ui.div(class_="row"):
        with ui.div(class_="d-flex flex-column col gap-2 border rounded p-5"):
            with ui.div(class_="row gap-2"):
                ui.input_text(id='txt_eval_name', label='Eval ID')
                ui.input_text_area(id='txt_desc', label='Eval Description')

            with ui.div(class_='d-flex flex-column border rounded p-3'):
                with ui.div(class_="row gap-2"):

                    with ui.div(class_='col-lg-auto col-md-5 col-sm-4'):
                        @render.express
                        def showModels():
                            model_options = loadModelConfig()
                            model_list = {id_: options['label'] for id_, options in model_options.items()}
                            ui.input_select(id='select_models', label='Model list', choices=model_list, multiple=False, size=10)

                    with ui.div(class_="col-lg-auto col-md-6 col-sm-7"):
                        @render.express
                        def showModelOptions():
                            model_options = loadModelConfig()
                            id_ = input.select_models()
                            if not (id_ and id_ in model_options): return
                            showModelConfig(id=f'model_{id_}', model_category_id=id_, model_options=model_options[id_])

                @render.express 
                def showSelectedModels():
                    with ui.div(class_='row'):
                        for i, model in enumerate(model_info.get()):
                            showSelectedModel(id=f'show_model_{i}', model=model)    
                        
            with ui.div(class_='row gap-2'):
                with ui.div(class_='row'):
                    with ui.div(class_='col'):
                        @render.express
                        def showSystemPrompt():
                            config = loadConfig()
                            system_prompt = config.get('system_prompt', '')
                            ui.input_text_area(id='txt_prompt_system', label='System prompt', value=system_prompt, rows=5, width='100%')

            with ui.div(class_="row gap-2"):
                with ui.div(class_='d-flex justify-content-start'):
                    with ui.tooltip(placement="right"):
                        ui.input_action_button(id='btn_add_prompt', label='', icon=fa.icon_svg("plus", "solid"))
                        "Add prompt"
            
            @render.express
            def showPromptVarsAndKP():
                with ui.div(class_='row gap-3'):
                    prompt_vals = reloadPrompts()
                    for index_prompt, val in enumerate(prompt_vals):
                        if val['status'] == 'deleted': continue
                        promptVarsAndKPContainer(id=getUIID('prompt'), 
                                                 index_prompt=index_prompt, 
                                                 prompt_text=val['prompt'], 
                                                 reload_prompts_flag=reload_prompts_flag)

        with ui.div(class_='col-auto justify-content-center'):        
            ui.input_task_button(id="btn_create_eval", label="Create")

    @reactive.effect
    @reactive.event(input.btn_add_prompt)
    def addPrompt():
        val = prompt_vars_kp.get().copy()
        val.append({'prompt': '', 'vars_kp': [], 'kp': set(), 'status': 'active'})
        prompt_vars_kp.set(val)
        reload_prompts_flag.set(not reload_prompts_flag.get())
        
    @reactive.calc
    @reactive.event(reload_prompts_flag)
    def reloadPrompts():
        return prompt_vars_kp.get()

    def validateFields(ignore_empty=True):

        errors_ = []

        val = input.txt_eval_name()
        if not (ignore_empty and not val):
            p = re.compile(r'[A-Za-z0-9\-\_]+')
            if not bool(p.fullmatch(val)): errors_.append('Eval ID can only contain alphanumeric characters, "-" and "_"')
            elif val and EvalConfigDB(val).exists(): errors_.append('Eval ID already exists')

        val = input.txt_desc()
        if not (ignore_empty and not val):
            p = re.compile(r'[A-Za-z0-9 \-\_\,\;\(\)]+')
            if not bool(p.fullmatch(val)): errors_.append('Eval Description can only contain alphanumeric characters, space, "-", "_", ",", ";" and "()"')

        p = re.compile(r'\d*')
        model_list = model_info.get()
        model_options = loadModelConfig()
        if not ignore_empty and len(model_list) == 0: errors_.append('At least one model must be selected')
        for model in model_list:
            model_config = model_options[model['id']]['config']
            for k, v in model['config'].items():
                if model_config[k]['type'] == 'int' and not bool(p.fullmatch(str(v))): errors_.append(f'{k} can only contain numeric values')

        val = input.txt_prompt_system()
        if not ignore_empty and len(val.strip()) == 0:
            errors_.append('System prompt cannot be empty') 

        if not ignore_empty:
            counter = 1
            for val in prompt_vars_kp.get():
                if val['status'] == 'deleted': continue
                if len(val['prompt']) == 0:
                    errors_.append(f'Prompt {counter} cannot be empty')
                counter += 1 

        return errors_

    @reactive.effect
    @reactive.event(input.txt_eval_name, input.txt_desc, input.select_models, ignore_init=True)
    def getValidationErrors():
        errors.set(validateFields())

    @reactive.calc
    def loadConfig():
        try:
            config = loadYML(Config.DIR_CONFIG / 'config.yaml')
            assert isinstance(config, dict), "Config was not set up"
            return config
        except:
            return {}

    @reactive.calc
    def loadModelConfig():
        config = loadConfig()
        return config.get('providers', {})
        
    @logexp
    @reactive.effect
    @reactive.event(input.btn_create_eval)
    def createEval():
        
        errors.set(validateFields(ignore_empty=False))
        if errors.get(): return

        eval_name = input.txt_eval_name()
        description = input.txt_desc()
        prompt_system = input.txt_prompt_system()
        prompt_vars_kp_values = prompt_vars_kp.get()

        providers = model_info.get()
    
        prompts_vars_asserts = []
        for v in prompt_vars_kp_values:
            
            if v['status'] == 'deleted': continue

            pva = {'prompt': v['prompt']}

            # Record variables and expected phrases for prompt with variable
            tests = [] 
            vars_kp_found = False
            for vars_kp in v['vars_kp']:
                if vars_kp['status'] == 'deleted': continue
                vars_kp_found = True
                test = {'vars': dict(vars_kp['vars'])}
                if vars_kp['kp']:
                    test['assert'] = [
                        {
                            'expected_phrases': list(vars_kp['kp'])
                        }
                    ]
                tests.append(test)

            # Record expected phrases only for prompt without variables
            if not vars_kp_found:
                if v['kp']:
                    tests.append(
                        {
                            'assert': [
                                {
                                    'expected_phrases': list(v['kp'])
                                }
                            ]
                        }
                    )

            pva['tests'] = tests
            prompts_vars_asserts.append(pva)
        
        if Evaluator.createTest(
                        eval_name = eval_name,
                        config = {
                            'description': description,
                            'providers': providers,
                            'system_prompt': f'''{prompt_system}''',
                            'prompts_vars_asserts': prompts_vars_asserts
                        }
        ):
            ui.notification_show(f'"{eval_name}" was created successfully')
            reload_unrun_evals_flag.set(not reload_unrun_evals_flag.get())
        else:
            ui.notification_show(f'"{eval_name}" was not created successfully')
