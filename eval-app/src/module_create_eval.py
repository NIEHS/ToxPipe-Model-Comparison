
from shiny import reactive
from shiny.express import ui, render, module, expressify
from shiny.types import SilentException
import traceback
import json
import faicons as fa
import regex
from .utils import Config, loadYML
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

    expected_phrases = reactive.value({})
    test_vars = reactive.value({})

    @module
    def keywordContainer(input, output, session, index, keyphrase):

        with ui.hold() as content:
            with ui.div(class_='position-relative border rounded p-2', style='width:fit-content'):
                ui.input_action_link(id='btn_remove_kw', label='', icon=fa.icon_svg("circle-xmark", "regular"), 
                                                        style='position:absolute; top:-10px; right:-10px; background-color:#fff')
                with ui.div():
                    keyphrase
        
        @reactive.effect
        @reactive.event(input.btn_remove_kw, ignore_init=True)
        def removeKeyword():
            values = expected_phrases.get()
            expected_phrases.set({**values, **{index: values[index] - {keyphrase}}})

        return content
    
    @module
    def kpContainer(input, output, session, index):

        with ui.hold() as content:
            with ui.div(class_='d-flex flex-column gap-2 pt-3'):
                with ui.div(class_='d-flex'):
                    with ui.div(class_='d-flex justify-content-start'):
                        ui.input_text(id='text_keywords', label="Response key phrases (optional)")
                    with ui.div(class_='d-flex justify-content-start'):
                        with ui.tooltip(placement="right"):
                            ui.span(fa.icon_svg('circle-question'))
                            "Phrases that the response should contain. High similarity with these phrases will be used to rank a response."
                    with ui.div(class_='d-flex align-items-center pt-3'):
                        ui.input_action_button(id='btn_add_keyword', label="Add")

                if index in expected_phrases.get():
                    with ui.div(class_='d-flex flex-wrap gap-2'):
                        with ui.div(class_='d-contents'):
                            for v in expected_phrases.get()[index]:
                                keywordContainer(str(hash(v))[1:], index, v)

        @reactive.effect
        @reactive.event(input.text_keywords)
        def showAddButton():
            ui.update_action_button('btn_add_keyword', disabled=not input.text_keywords())

        @reactive.effect
        @reactive.event(input.btn_add_keyword, ignore_init=True)
        def addKeyword():
            kw = input.text_keywords().strip()
            ui.update_text(id='text_keywords', value='')
            if kw == '': return

            values = expected_phrases.get()
            
            if index not in values:
                expected_phrases.set({**values, **{index: {kw}}})
                return

            expected_phrases.set({**values, **{index: values[index] | {kw}}})

        return content
    
    @module
    def varKpContainer(input, output, session, index, var):

        with ui.hold() as content:
            with ui.div(class_='position-relative border rounded p-2', style='width:fit-content'):
                ui.input_action_link(id='btn_remove_var', label='', icon=fa.icon_svg("circle-xmark", "regular"), 
                                                    style='position:absolute; top:-10px; right:-10px; background-color:#fff')
                with ui.div():
                    var
                kpContainer(str(index), index), 

        @reactive.effect
        @reactive.event(input.btn_remove_var, ignore_init=True)
        def removeVar():
            values = test_vars.get()
            test_vars.set({k: v for k, v in values.items() if k != index})

            values = expected_phrases.get()
            expected_phrases.set({k: v for k, v in values.items() if k != index})
        
        return content

    with ui.div(class_="row error m-2"):
        @render.ui
        def showError():
            errors = validateFields()
            return ui.HTML(f'<ui>{"".join(["<li>" + e_text + "</li>" for e_text in errors])}</ui>')

    with ui.div(class_="row"):
        with ui.div(class_="d-flex flex-column col gap-2 border rounded p-5"):
            with ui.div(class_="row gap-2"):
                ui.input_text(id='txt_test', label='Name')
                ui.input_text_area(id='txt_desc', label='Description')

            with ui.div(class_="row gap-2"):

                with ui.div(class_='col-2'):
                    @render.express
                    def showModels():
                        model_options = loadModelSettings()
                        model_list = {i: item['label'] for i, item in enumerate(model_options)}
                        ui.input_select(id='select_models', label='Model list', choices=model_list, multiple=True)

                with ui.div(class_="col-9"):
                    @render.express
                    def showModelConfig():
                        model_options_sel = loadModelConfig()
                        with ui.div(class_='row'):
                            for index, model_options in model_options_sel:
                                model_name = model_options['label']

                                with ui.div(class_="col-3 col-5-sm"):
                                    with ui.card():
                                        ui.card_header(model_name)
                                        for k, v in model_options['config'].items():
                                            if isinstance(v['type'], list):
                                                ui.input_select(id=f'select_model_config_{index}_{k}', label=v['label'], choices=v['type'], selected=v['default'])
                                            elif v['type'] == 'int':
                                                if 'min' in v and 'max' in v:
                                                    ui.input_slider(id=f'txt_model_config_{index}_{k}', label=v['label'], min=int(v['min']), max=int(v['max']), value=int(v['default']), step=0.1)
                                                else:
                                                    ui.input_text(id=f'txt_model_config_{index}_{k}', label=v['label'], value=int(v['default']))
            
            with ui.div(class_='row gap-2'):

                with ui.div(class_='row'):
                    with ui.div(class_='col'):
                        ui.input_text_area(id='txt_prompt', label='Prompt', rows=5, width='100%', placeholder='What is the function of Aspirin?\nor\nWhat is the function of {chemname}?')
                    with ui.div(class_='col-auto'):
                        with ui.tooltip(placement="right"):
                            ui.span(fa.icon_svg('circle-question'))
                            "You can also use variable for a prompt using curly braces. e.g. What is the function of {chemname}?"

                with ui.div(class_='row'):
                    with ui.div(class_='col'):
                        @render.express
                        def showVars():
                            variables = validatePromptVars(extractPromptVars())

                            if not variables: return
                    
                            with ui.div(class_='row border rounded p-2 m-2'):
                                with ui.div(class_='row'):
                                    with ui.div(class_='col'):
                                        with ui.div(class_='row'):
                                            for v in variables:
                                                with ui.div(class_='col-3'):
                                                    ui.input_text(id=f'txt_var_{v}', label=v)
                                    with ui.div(class_='col-auto'):
                                        ui.input_action_button(id='btn_add_var', label="Add")

                                @render.express
                                def showKPPerVar():
                                    if not test_vars.get(): return
                                    with ui.div(class_='d-flex gap-2'):
                                        for i, var in test_vars.get().items():
                                            content = ui.HTML(f"<ul>{''.join([f"<li><strong>{k}:</strong><span class='ms-1'>{v}</span></li>" for k, v in var])}</ul>")
                                            with ui.div(style='width:400px'):
                                                varKpContainer(str(hash(var))[1:], i, content)

            with ui.div(class_='row'):
            
                @render.express
                def showKP():
                    variables = validatePromptVars(extractPromptVars())
                    if len(variables) > 0: return
                    
                    kpContainer('0', 0)

        with ui.div(class_='col-auto justify-content-center'):        
            ui.input_task_button(id="btn_create_eval", label="Create")

    def validatePromptVars(variables):
        p = regex.compile(r'[A-Za-z0-9\-\_]*')
        for val in variables:
            if not bool(p.fullmatch(val)): return []
        return variables

    @reactive.calc
    @reactive.event(input.txt_test, input.txt_desc, input.select_models, input.txt_prompt, input.btn_create_eval, ignore_init=True)
    def validateFields():
        errors = []

        val = input.txt_test()
        p = regex.compile(r'[A-Za-z0-9\-\_]+')
        if not bool(p.fullmatch(val)): errors.append('Name can only contain alphanumeric characters, "-" and "_"')
        elif val and EvalConfigDB(val).exists(): errors.append('Name already exists')

        val = input.txt_desc()
        p = regex.compile(r'[A-Za-z0-9 \-\_\,\;\(\)]+')
        if not bool(p.fullmatch(val)): errors.append('Description can only contain alphanumeric characters, space, "-", "_", ",", ";" and "()"')

        p = regex.compile(r'\d*')
        model_options = loadModelSettings()
        model_list = input.select_models()
        if len(model_list) == 0: errors.append('At least one model must be selected')
        for model_id in model_list:
            model_config = model_options[int(model_id)]['config']

            input_fields = [k for k in input.__dict__['_map'].keys() if k.startswith(f'set-create-select_model_config_{model_id}') or k.startswith(f'set-create-txt_model_config_{model_id}')]
            
            for in_field in input_fields:
                field_name = '_'.join(in_field.split('_')[4:])
                field_value = str(input[in_field.split('-')[-1]]()).strip()

                if model_config[field_name]['type'] == 'int' and not bool(p.fullmatch(field_value)): errors.append(f'{field_name} can only contain numeric values')
        
        val = input.txt_prompt()
        if len(val.strip()) == 0:
            errors.append('Prompt cannot be empty')

        prompt_vars = extractPromptVars()
        if prompt_vars and len(validatePromptVars(prompt_vars)) == 0: errors.append('Prompt variable can only contain alphanumeric characters, "-" and "_"') 

        return errors

    @reactive.calc
    def loadModelSettings():
        dir_output = Config.DIR_TESTS
        if (dir_output / 'providers.json').exists():
            with open(dir_output / 'providers.json') as f:
                return json.load(f)
        return []

    @reactive.calc
    @reactive.event(input.select_models)
    def loadModelConfig():
        model_options = loadModelSettings()
        if not model_options: return {}
        return [(i, model_options[int(i)]) for i in input.select_models()]
    
    @reactive.calc
    @reactive.event(input.txt_prompt)
    def extractPromptVars():
        prompt = input.txt_prompt()
        variables = regex.findall(rf'{Evaluator.PROMPT_VAR_FORMAT}', prompt)    
        test_vars.set({})
        return variables

    @reactive.effect
    @reactive.event(input.btn_add_var)
    def addVar():
        
        if len(test_vars.get()) == 0: expected_phrases.set({})
        
        field_names = [x.split('-')[-1] for x in sorted(input.__dict__['_map'].keys()) if x.startswith('set-create-txt_var_')]
        
        val = []
        for x in field_names:
            varname = '_'.join(x.split('_')[2:])
            varval = input[x]().strip()
            if varval == '': return
            val.append((varname, varval))
        
        val = tuple(val)

        for f in field_names:
            ui.update_text(id=f, value='')
        
        if val in test_vars.get().values(): return 
        id_= max(test_vars.get().keys()) + 1 if len(test_vars.get()) > 0 else 0
        test_vars.set({**test_vars.get(), **{id_: val}})
        
        if id_ not in expected_phrases.get():
            expected_phrases.set({**expected_phrases.get(), **{id_: set()}})

        print(test_vars.get())
        print(expected_phrases.get())
        
    @logexp
    @reactive.effect
    @reactive.event(input.btn_create_eval)
    def createEval():
        def getFieldValue(in_field, model_config):
            field_name = '_'.join(in_field.split('_')[4:])
            field_value = input[in_field.split('-')[-1]]()
            try:
                if model_config[field_name]['type'] == 'int':
                    field_value = int(field_value)
                elif model_config[field_name]['type'] == 'float':
                    field_value = float(field_value)
            except:
                field_value = 0

            return (field_name, field_value)
        
        if len(validateFields()) > 0: return

        model_options = loadModelSettings()
        eval_name = input.txt_test()
        description = input.txt_desc()
        model_list = input.select_models()
        variables = test_vars.get()
        providers = []
        for model_id in model_list:
            model_config = model_options[int(model_id)]
            input_fields = [k for k in input.__dict__['_map'].keys() if k.startswith(f'set-create-select_model_config_{model_id}') or k.startswith(f'set-create-txt_model_config_{model_id}')]
            providers.append(
                {
                    'id': model_config['id'],
                    'label': model_config['label'],
                    'config': dict(getFieldValue(in_field, model_config['config']) for in_field in input_fields)
                }
            )
    
        prompt = input.txt_prompt()

        defaulttest = {
            'options': { 
                'provider': { 
                    'embedding': {
                        'id': 'openai:embedding:text-embedding-ada-002'
                    }
                }
            }
        }

        prompt_system = loadYML(Config.DIR_TESTS / 'config' / 'system_prompt.yaml')

        prompts = {
            'system': prompt_system['system'] if prompt_system is not None and 'system' in prompt_system else '',
            'user': [f'''{prompt}''']
        }
        
        if not variables:
            if len(expected_phrases.get()) == 0:
                tests = [
                    {'vars': {'dummy': 'dummy'}}
                ]
            else:
                tests = [ 
                    {
                        'assert': [ 
                            {
                                'expected_phrases': list(expected_phrases.get().get(0, [])),
                            }
                        ]
                    }
                ]
        else:
            tests = []
            for i, var in variables.items():
                if len(expected_phrases.get()) == 0:
                    d_dict = {}
                else:
                    d_dict = {
                                'assert': [ 
                                    {
                                        'expected_phrases': list(expected_phrases.get().get(i, [])),
                                    }
                                ]
                    }
                d_dict['vars'] = {k: v for k, v in var}
                tests.append(d_dict)

        
        if Evaluator.createTest(
                        eval_name,
                        {
                            'eval_name': eval_name, 
                            'description': description, 
                            'defaulttest': defaulttest, 
                            'prompts': prompts, 
                            'providers': providers, 
                            'tests': tests
                        }
        ):
            ui.notification_show(f'"{eval_name}" was created successfully')
            reload_unrun_evals_flag.set(not reload_unrun_evals_flag.get())
        else:
            ui.notification_show(f'"{eval_name}" was not created successfully')
