
from shiny import reactive, ui as core_ui
from shiny.express import ui, render, module
from shiny.types import SilentException
import traceback
import json
import faicons as fa
import yaml
import regex
import shutil
from codes.create_promptfoo_config import createTest, MyDumper
from utils import Config

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
def mod_ui(input, output, session):

    question_circle_fill = ui.HTML(
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-question-circle-fill mb-1" viewBox="0 0 16 16"><path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0zM5.496 6.033h.825c.138 0 .248-.113.266-.25.09-.656.54-1.134 1.342-1.134.686 0 1.314.343 1.314 1.168 0 .635-.374.927-.965 1.371-.673.489-1.206 1.06-1.168 1.987l.003.217a.25.25 0 0 0 .25.246h.811a.25.25 0 0 0 .25-.25v-.105c0-.718.273-.927 1.01-1.486.609-.463 1.244-.977 1.244-2.056 0-1.511-1.276-2.241-2.673-2.241-1.267 0-2.655.59-2.75 2.286a.237.237 0 0 0 .241.247zm2.325 6.443c.61 0 1.029-.394 1.029-.927 0-.552-.42-.94-1.029-.94-.584 0-1.009.388-1.009.94 0 .533.425.927 1.01.927z"/></svg>'
    )

    expected_phrases = reactive.value({})
    test_vars = reactive.value({})

    @module
    def keywordContainer(input, output, session, index, content):

        # with ui.div(class_='position-relative border rounded p-2'):
        #     ui.input_action_link(id='btn_remove_kw', label='', icon=fa.icon_svg("circle-xmark", "regular"), 
        #                                             style='position:absolute; top:-10px; right:-10px; background-color:#fff')
        #     with ui.div():
        #         content
        
        @reactive.effect
        @reactive.event(input.btn_remove_kw, ignore_init=True)
        def removeKeyword():
            values = expected_phrases.get()
            expected_phrases.set({**values, **{index: values[index] - {content}}})

        return core_ui.div(
                ui.input_action_link(id='btn_remove_kw', label='', icon=fa.icon_svg("circle-xmark", "regular"), style='position:absolute; top:-10px; right:-10px; background-color:#fff'),
                core_ui.div(content),
                class_='position-relative border rounded p-2'
            )
    @module
    def keywordInputContainer(input, output, session, index):
        # with ui.div(class_='d-flex justify-content-start align-items-center column-gap-3'):
        #     with ui.div(class_='d-flex justify-content-start'):
        #         ui.input_text(id='text_keywords', label="Response key phrases (optional)")
        #         with ui.tooltip(placement="right", id="card_tooltip"):
        #             ui.span(question_circle_fill)
        #             "Phrases that the response should contain. High similarity with these phrases will be used to rank a response."
        #     with ui.div(class_='d-flex pt-3'):
        #         ui.input_action_button(id='btn_add_keyword', label="Add")
            
        #     @render.ui
        #     def showKeyPhraseInputUI():
        #         return core_ui.div(
        #                     *[keywordContainer(str(hash(v))[1:], k, v) for k, v in expected_phrases.get().items()],
        #                     class_='d-flex column-gap-2 pt-3'
        #         )

        ui_elements = [keywordContainer(str(hash(v))[1:], index, v) for v in expected_phrases.get()[index]] if index in expected_phrases.get() else ''

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

        return core_ui.div(
                core_ui.div(
                    core_ui.div(
                        core_ui.div(
                            ui.input_text(id='text_keywords', label="Response key phrases (optional)"),
                            class_='d-flex justify-content-start'
                        ),
                        core_ui.div(
                            core_ui.tooltip(
                                ui.span(question_circle_fill),
                                "Phrases that the response should contain. High similarity with these phrases will be used to rank a response.", 
                                placement="right", 
                                id="card_tooltip"
                            ),
                            class_='d-flex justify-content-start'
                        ),
                        class_='d-flex justify-content-start'
                    ),
                    core_ui.div(
                        ui.input_action_button(id='btn_add_keyword', label="Add"),
                        class_='d-flex align-items-center pt-3'
                    ),
                    class_='d-flex gap-3'
                ),
                core_ui.div(
                    core_ui.div(
                        *ui_elements,
                        class_='d-contents'
                    ),
                    class_='d-flex flex-wrap gap-2'
                ),
                class_='row gap-2 pt-3'
        )

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
                    @render.ui
                    def showModels():
                        model_options = loadModelSettings()
                        model_list = {i: item['label'] for i, item in enumerate(model_options)}
                        return ui.input_select(id='select_models', label='Model list', choices=model_list, multiple=True)

                with ui.div(class_="col-9"):
                    @render.ui
                    def showModelConfig():
                        model_options_sel = loadModelConfig()
                        ui_list = []
                        for index, model_options in model_options_sel:
                            model_name = model_options['label']
                            ui_list_per_model = []
                            for k, v in model_options['config'].items():
                                if isinstance(v['type'], list):
                                    ui_list_per_model.append(ui.input_select(id=f'select_model_config_{index}_{k}', label=v['label'], choices=v['type'], selected=v['default']))
                                elif v['type'] == 'int':
                                    if 'min' in v and 'max' in v:
                                        ui_list_per_model.append(ui.input_slider(id=f'txt_model_config_{index}_{k}', label=v['label'], min=int(v['min']), max=int(v['max']), value=int(v['default']), step=0.1))
                                    else:
                                        ui_list_per_model.append(ui.input_text(id=f'txt_model_config_{index}_{k}', label=v['label'], value=int(v['default'])))
                            ui_list.append(
                                core_ui.div(
                                    core_ui.card(
                                        core_ui.card_header(model_name),
                                        *ui_list_per_model
                                    ),
                                    class_="col-3 col-5-sm"
                                )
                            )

                        return core_ui.div(*ui_list, class_="row")
            
            
            with ui.div(class_='row gap-2'):

                with ui.div(class_='row'):
                    ui.input_text_area(id='txt_prompt', label='Prompt', rows=5, width='100%')
                @module
                def varContainer(input, output, session, index, content):

                    @reactive.effect
                    @reactive.event(input.btn_remove_var, ignore_init=True)
                    def removeVar():
                        values = test_vars.get()
                        test_vars.set({k: v for k, v in values.items() if k != index})

                        values = expected_phrases.get()
                        expected_phrases.set({k: v for k, v in values.items() if k != index})
                    
                    return core_ui.div(core_ui.input_action_link(id='btn_remove_var', label='', icon=fa.icon_svg("circle-xmark", "regular"), 
                                                                style='position:absolute; top:-10px; right:-10px; background-color:#fff'),
                                    core_ui.div(content),
                                    keywordInputContainer(str(index), index), 
                                    class_='position-relative border rounded p-2')
                with ui.div(class_='row'):
                    with ui.div(class_='col'):
                        @render.ui
                        def showVars():
                            def showAddedVars():
                                if not test_vars.get(): return
                                ui_list = []
                                for i, var in test_vars.get().items():
                                    content = core_ui.HTML(f"<ul>{''.join([f"<li><strong>{k}:</strong><span class='ms-1'>{v}</span></li>" for k, v in var])}</ul>")
                                    ui_list.append(
                                        core_ui.div(
                                            varContainer(str(hash(var))[1:], i, content),
                                            class_="col-3 col-5-sm"
                                        )
                                    )
                                return core_ui.div(*ui_list, class_='row')
                            variables = extractPromptVars()
                            if variables:
                                try:
                                    return core_ui.div(
                                            core_ui.div(
                                                core_ui.div(
                                                    core_ui.div(
                                                        *[core_ui.div(
                                                            ui.input_text(id=f'txt_var_{v}', label=v),
                                                            class_='col-3'
                                                        ) for v in variables],
                                                        class_='row'
                                                    ),
                                                    class_='col'
                                                ),
                                                core_ui.div(
                                                    ui.input_action_button(id='btn_add_var', label="Add"),
                                                    class_='col-auto'
                                                ),
                                                class_='row'
                                            ),
                                            showAddedVars(),
                                            class_='row border rounded p-2 m-2'
                                        ) 
                                except:
                                    return
                            else:
                                test_vars.set({})
                                expected_phrases.set({})

            with ui.div(class_='row'):
            
                @render.ui
                def showKeyPhraseUI():
                    variables = extractPromptVars()
                    if len(variables) == 0:
                        return keywordInputContainer('0', 0)

        with ui.div(class_='col-auto justify-content-center'):        
            ui.input_task_button(id="btn_create_eval", label="Create")

    @reactive.calc
    @reactive.event(input.txt_test, input.txt_desc, input.select_models, input.txt_prompt, input.btn_create_eval, ignore_init=True)
    def validateFields():
        errors = []

        val = input.txt_test()
        p = regex.compile(r'[A-Za-z0-9\-\_]+')
        if not bool(p.fullmatch(val)): errors.append('Name can only contain alphanumeric characters, "-" and "_"')
        elif val and (Config.DIR_TESTS / val).exists(): errors.append('Name already exists')

        val = input.txt_desc()
        p = regex.compile(r'[A-Za-z0-9 \-\_\,\;]+')
        if not bool(p.fullmatch(val)): errors.append('Description can only contain alphanumeric characters, space, "-", "_", "," and ";"')

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

        p = regex.compile(r'[A-Za-z0-9\-\_]*')
        variables = extractPromptVars()
        for val in variables:
            if not bool(p.fullmatch(val)): errors.append('Prompt variable can only contain alphanumeric characters, "-" and "_"') 

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
        variables = regex.findall(r'\{\{(.*?)\}\}', prompt)
        return variables

    @reactive.effect
    @reactive.event(input.btn_add_var)
    def addVar():
        
        if len(test_vars.get()) == 0: expected_phrases.set({})
        
        field_names = [x.split('-')[1] for x in sorted(input.__dict__['_map'].keys()) if x.startswith('set-create-txt_var_')]
        
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
        test_name = input.txt_test()
        description = input.txt_desc()
        model_list = input.select_models()
        variables = test_vars.get()
        providers = []
        has_toxpipe = False
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
            if model_config['id'] == "file://scripts/providers.py": has_toxpipe = True
    
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

        prompts = {
            'system': '''You are an expert toxicologist with extensive knowledge in chemical safety assessment, toxicokinetics, and toxicodynamics. Your expertise includes:

            1. Interpreting chemical structures and properties
            2. Analyzing toxicological data from various sources (e.g., in vitro, in vivo, and in silico studies)
            3. Applying read-across and QSAR (Quantitative Structure-Activity Relationship) approaches
            4. Understanding mechanisms of toxicity and adverse outcome pathways
            5. Evaluating systemic availability based on ADME (Absorption, Distribution, Metabolism, Excretion) properties
            6. Assessing potential health hazards and risks associated with chemical exposure

            When providing toxicological evaluations:
            - Use reliable scientific sources and databases (e.g., PubChem, ECHA, EPA, IARC)
            - Consider both experimental data and predictive models
            - Explain your reasoning and cite relevant studies or guidelines
            - Acknowledge uncertainties and data gaps
            - Provide a balanced assessment, considering both potential hazards and mitigating factors
            - Use a weight-of-evidence approach when multiple data sources are available
            - Classify toxicodynamic activity and systemic availability as high, medium, or low based on 
            the available evidence and expert judgment
            - When using read-across, clearly state the basis for the analogy and any limitations

            Adhere to ethical standards in toxicology and maintain scientific objectivity in your assessments.
            ''',

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
                                'type': 'python',
                                'value': 'file://scripts/tests.py'
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
                                        'type': 'python',
                                        'value': 'file://scripts/tests.py'
                                    }
                                ]
                    }
                d_dict['vars'] = {k: v for k, v in var}
                tests.append(d_dict)

        dir_setup = Config.DIR_TESTS / test_name / 'setup'
        dir_setup.mkdir(parents=True, exist_ok=True)

        with open(dir_setup / 'defaulttest.yaml', 'w') as outfile:
            yaml.dump(defaulttest, outfile, Dumper=MyDumper, default_flow_style=False)

        with open(dir_setup / 'prompts.yaml', 'w') as outfile:
            yaml.dump(prompts, outfile, Dumper=MyDumper, default_flow_style=False)

        with open(dir_setup / 'providers.yaml', 'w') as outfile:
            yaml.dump(providers, outfile, Dumper=MyDumper, default_flow_style=False)

        with open(dir_setup / 'tests.yaml', 'w') as outfile:
            yaml.dump(tests, outfile, Dumper=MyDumper, default_flow_style=False)

        with open(dir_setup / 'config.yaml', 'w') as outfile:
            config = {
                'description': description,
                'prompts': 'prompts.yaml',
                'providers': 'providers.yaml',
                'tests': 'tests.yaml',
                'defaultTest': 'defaulttest.yaml'
            }
            yaml.dump(config, outfile, Dumper=MyDumper, default_flow_style=False)

        createTest(test_name=test_name)

        dir_scripts = Config.DIR_TESTS / test_name / 'scripts'
        dir_scripts.mkdir(parents=True, exist_ok=True)

        if has_toxpipe:
            dir_src = Config.DIR_CODES / 'providers.py'
            shutil.copy(dir_src, dir_scripts)

        dir_src = Config.DIR_CODES / 'tests.py'
        shutil.copy(dir_src, dir_scripts)

        ui.notification_show(f'"{test_name}" was created successfully')