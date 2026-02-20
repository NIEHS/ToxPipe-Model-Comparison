from shiny import reactive, ui as core_ui
from shiny.express import ui, render, module, expressify
import pandas as pd
import faicons as fa
from .utils import Config, loadYML
from .utils_eval import Evaluator
from .common import mod_vars, hasAssertion
import re

# -----------------------------------------------------------------------
@expressify
def prettyTableUI(df, style_dict={}):
    def format(text, col_name):
        if pd.isna(text): text = ''
        if col_name == 'Link': return ui.HTML(f"<a class='app-link' href='{text}'>{text}</a>")
        return text
    
    n_cols = len(df.columns)

    with ui.tags.table(id='table-responses', class_='app-table resizable-table'):
        with ui.tags.thead(class_='app-table-header'):
            with ui.tags.tr():
                for col in df.columns:
                    with ui.tags.th(width=f'{100/n_cols}%', class_='p-2 text-center app-table-col'):
                        ui.strong(col)
        with ui.tags.tbody():
            for i, row in df.iterrows():
                with ui.tags.tr():
                    for j, col in enumerate(df.columns):
                        with ui.tags.td(width=f'{100/n_cols}%', class_=f'{style_dict.get(f'row_{i}_col_{j}', '')} p-2 text-center app-table-col'):
                            with ui.div(style="text-align:start"):
                                format(row[col], col)

@module
def mod_ui(input, output, session):

    var_selected = reactive.value({})
    models_selected = reactive.value({})

    @module
    def mod_select_model(input, output, session, eval_name, model_options):

        @render.express
        def renderModels():
            ui.input_select(id='select_model', label='', choices=model_options)
        
        @reactive.effect
        @reactive.event(input.select_model)
        def selectModel():
            models = models_selected.get().copy()
            models[eval_name] = input.select_model()
            models_selected.set(models)

    with ui.div(class_="d-flex gap-5"):
        ui.input_select("select_eval_set", "Eval sets", choices=[])
        ui.input_select("select_prompt", "Prompts", choices=[])
        @render.express
        def showVars():
            d_vars = loadVars()
            for k, v in d_vars.items():
                mod_vars(f'vars_{k}', var_name=k, var_values=list(v), fn_reactive=selectVar)

    with ui.div(class_='d-flex flex-column gap-2'):
        with ui.div():
            "Prompt"
        with ui.div(class_='d-flex border rounded p-3 justify-content-center'):
            with ui.div(class_='prompt'):
                @render.ui
                def showPrompt():
                    return core_ui.markdown(getPrompt())

        @render.express
        def showTopBar():

            eval_outputs = loadResultsTask.result().copy()
            if not eval_outputs: return
            for eval_name, data in eval_outputs.items():
                if hasAssertion(data): break
            else:
                return
            
            with ui.div(class_='results-top-bar gap-4'):
                with ui.div(class_='d-flex align-items-center gap-2'):
                    ui.span('Pass score threshold')
                    with ui.div():
                        ui.input_numeric(id='numeric_threshold', label='', min=0, max=1, step=0.1, value=1)

        @render.express
        def showModels():

            eval_outputs = loadResultsTask.result().copy()
            if not eval_outputs: return

            with ui.tags.table(id='table-responses', class_='app-table resizable-table'):
                with ui.tags.tbody():
                    with ui.tags.tr():
                        for i, (eval_name, data) in enumerate(eval_outputs.items()):
                            with ui.tags.td():
                                with ui.div(class_='d-flex justify-content-center'):
                                    if data.empty: return
                                    mod_select_model(id=f'select_model_{i}', eval_name=eval_name, model_options=list(data['Model'].unique()))
        @render.express
        def showResults():

            def getExplanationHTML(result):

                def resultStr(res):
                    return f"<span class='passed'>{fa.icon_svg('circle-check')}</span>" if res else f"<span class='failed'>{fa.icon_svg('circle-xmark')}</span>"

                def getComponentExplanation(results):
                    text = ''
                    has_component = False
                    for result in results:
                        if 'components' in result:
                            text += f"<strong>{result['reason']} {resultStr(result['pass'])}</strong>"
                            text += f"<ul>{getComponentExplanation(result['components'])}</ul>"
                            has_component = True

                    if not has_component:
                        for result in results:
                            text += f"<li>{result['reason']} {resultStr(result['pass'])}</li>"
                            
                    return text

                if not isinstance(result, list): return "No reason found"
                return getComponentExplanation(result)
            

            def formatResponse(x):

                @expressify
                def format():
                
                    if pd.isna(x[f'Response']): return ''
                    
                    with ui.popover(placement="right", options={"trigger": "hover focus"}):
                        with ui.div(class_='app-table-content'):
                            ui.markdown(x['Response'])
                        with ui.div(class_='p-2'):
                            ui.HTML(getExplanationHTML(x['Reason']) if x['Result'] != 'No assertion' else 'No assertion')

                with ui.hold() as content:
                    format()
                
                return content
            
            def getResultBasedOnScoreThreshold(score_val, result_val, threshold_pass):
                if score_val >= threshold_pass: return 'Pass'
                if not pd.isna(result_val) and result_val != 'No assertion': return 'Fail'
                return result_val
            
            match loadResultsTask.status():
                case 'initial':
                    ui.div(ui.strong("Responses will show up here"))
                    return
                case 'running':
                    ui.div(ui.strong("Extracting responses..."))
                    return

            eval_outputs = loadResultsTask.result().copy()
            if not eval_outputs: return

            eval_names = []
            data_combined = []
            for eval_name in eval_outputs:
                data = eval_outputs[eval_name]
                if data.empty: return

                model = models_selected.get().get(eval_name, None)
                if model: data = data.query('Model == @model').reset_index(drop=True)

                if hasAssertion(data):
                    threshold_pass = input.numeric_threshold()
                    data.loc[:, f'Result ({eval_name})'] = data.apply(lambda x: getResultBasedOnScoreThreshold(x['Score'], x['Result'], threshold_pass), axis=1)
                else:
                    data.loc[:, f'Result ({eval_name})'] = data['Result'].copy()
                    
                data.loc[:, f'Response ({eval_name})'] = data.apply(lambda x: formatResponse(x), axis=1)
                
                data_combined.append(data[[f'Response ({eval_name})', f'Result ({eval_name})']].copy())
                eval_names.append(eval_name)
                
            data_combined = pd.concat(data_combined, axis=1)
            
            style_dict={}
            if not data_combined.empty:
                for i, row in data_combined.iterrows():
                    for j, eval_name in enumerate(eval_names):
                        col_name = f'Result ({eval_name})'
                        match row[col_name]:
                            case 'Pass':
                                style_dict[f'row_{i}_col_{j}'] = 'app-table-row-pass'
                            case 'Fail':
                                style_dict[f'row_{i}_col_{j}'] = 'app-table-row-fail'
                            case _:
                                style_dict[f'row_{i}_col_{j}'] = 'app-table-row-no-assertion'

            prettyTableUI(data_combined[[f"Response ({eval_name})" for eval_name in eval_names]],
                          style_dict=style_dict)
        
    ui.include_js(Config.DIR_HOME / "www" / "js" / "table.js", method='inline')
    
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
        ui.update_select(id='select_eval_set', choices={k: v['Name'] for k, v in eval_sets.items()})

    @reactive.effect
    @reactive.event(input.select_eval_set)
    def loadPrompts():
        eval_set_name = input.select_eval_set()
        eval_sets = getEvalSetToCompare()
        prompts = []
        try:
            for eval_info in eval_sets[eval_set_name]['Evals to compare']:
                prompts += Evaluator.getPrompts(eval_name=eval_info['Eval Name'])
            prompts = sorted(set(prompts))
        except:
            return
        
        ui.update_select(id='select_prompt', choices=prompts)

    @reactive.calc
    @reactive.event(input.select_eval_set, input.select_prompt)
    def loadVars():
        eval_set_name = input.select_eval_set()
        prompt = input.select_prompt()

        if not (eval_set_name and prompt): return {}
        
        eval_sets = getEvalSetToCompare()
        
        var_selected.set({}) 
        
        d_vars = {}
        try:
            for eval_info in eval_sets[eval_set_name]['Evals to compare']:
                d_vars |= Evaluator.getVars(eval_name=eval_info['Eval Name'])
        except:
           return d_vars 
        
        data = Evaluator.filterVarsByPrompt(d_vars, prompt)
        
        return data
    
    @reactive.calc
    @reactive.event(input.select_prompt, var_selected)
    def getPrompt():
        
        prompt = input.select_prompt.get()
        if not prompt: return ''
        
        vars_prompt = set(re.findall(r"{(\w+)}", prompt))
        var_sel = var_selected.get()

        if len(vars_prompt) != len(var_sel): return ''
        
        try:
            prompt = prompt.format(**var_sel)
        except:
            prompt = ''
    
        return prompt
    
    @reactive.extended_task
    async def loadResultsTask(eval_set_name, prompt, var_sel, eval_sets):

        async def run():

            eval_outputs = {}
            for eval_info in eval_sets[eval_set_name]['Evals to compare']:
                eval_outputs[eval_info['Eval Name']] = Evaluator.processResults(eval_name=eval_info['Eval Name'], prompt=prompt, d_vars=var_sel)
            return eval_outputs
        
        return await run()
        
    @reactive.effect
    @reactive.event(input.select_eval_set, input.select_prompt, var_selected)
    def loadResults():
        
        eval_set_name = input.select_eval_set()
        prompt = input.select_prompt()
        d_vars = loadVars()
        var_sel = var_selected.get()
        eval_sets = getEvalSetToCompare()

        if not eval_set_name or not prompt or (d_vars and len(d_vars) != len(var_sel)): return

        loadResultsTask(eval_set_name, prompt, var_sel, eval_sets)

    def selectVar(var_sel):
        var_selected.set({**var_selected.get(), **var_sel})