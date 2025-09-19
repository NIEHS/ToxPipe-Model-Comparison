from shiny import reactive, ui as core_ui
from shiny.express import ui, render, module
from shinywidgets import render_plotly
import pandas as pd
import faicons as fa
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity
#from umap import UMAP
import plotly.express as px
from .utils import Config, loadYML
from .utils_eval import Evaluator
from .module_common import mod_vars
from .db import getRating, saveRating
import re
import asyncio

# -----------------------------------------------------------------------
def prettyTableUI(df, col_widths, style_dict={}):
    def format(text, col_name):
        if pd.isna(text): text = ''
        if col_name == 'Link': return ui.HTML(f"<a class='app-link' href='{text}'>{text}</a>")
        return text
    
    header = '<tr>' + ''.join([f'<th width={"30%" if j != 0 else "10%"} class="p-2 text-center app-table-col"><strong>{col}</strong></th>' for j, col in enumerate(df.columns)]) + '</tr>'
    body = ''.join([f'<tr>{''.join([f'<td width={"30%" if j != 0 else "10%"} class="{style_dict.get(f'row_{i}_col_{j}', '')} p-2 text-center app-table-col"><div style="text-align:start">{format(row[col], col)}</div></td>' for j, col in enumerate(df.columns)])}</tr>' for i, row in df.iterrows()])
    
    return core_ui.HTML(
        f'''
        <table id='table-responses' class='app-table resizable-table'>
            <thead class='app-table-header'>
                {header}
            </thead>
            <tbody>
                {body}
            </tbody>
        </table>
        ''')

@module
def mod_ui(input, output, session):

    var_selected = reactive.value({})

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

            data = loadResultsTask.result().copy()
            
            eval_set_name = input.select_eval_set()
            eval_sets = getEvalSetToCompare()

            for eval_name_key, _ in eval_sets[eval_set_name]['Evals to compare']:
                if hasAssertion(data, f'Result ({eval_name_key})'): break
            else:
                return
            
            with ui.div(class_='results-top-bar gap-4'):
                with ui.div(class_='d-flex align-items-center gap-2'):
                    ui.span('Pass score threshold')
                    with ui.div():
                        ui.input_numeric(id='numeric_threshold', label='', min=0, max=1, step=0.1, value=1)
    
        @render.ui
        def showResults():
            def addReason(x, col_suffix, type, content):
                return core_ui.popover(
                            content,
                            core_ui.HTML(getExplanationHTML(x[f'Reason{col_suffix}']) if x['Result'] != 'No assertion' else 'No assertion'),
                            placement="right",
                            id=f"popover_result_reason_{type}_{x.name}",
                            options={"trigger": "hover focus"}
                )
            
            def formatResponse(x, col_suffix, type):
                
                if col_suffix == ' (RAG)':
                    return addReason(x, col_suffix, type, 
                                     core_ui.div(
                                        core_ui.div(f'[The following response was taken from {("RAG resources" if x[f'Used Context'] else "model's training knowledge")}]',
                                                    class_='fst-italic fw-bold mb-4'),
                                        core_ui.div(core_ui.markdown(x[f'Response{col_suffix}'])),
                                        class_='app-table-content'
                                    )
                    )
                #data.apply(lambda x: addReason(x) if x['Result'] != 'No assertion' else x['Result'], axis=1)
                return addReason(x, col_suffix, type, core_ui.div(core_ui.markdown(x[f'Response{col_suffix}']), class_='app-table-content'))
            
            def getResultBasedOnScoreThreshold(score_val, result_val, threshold_pass):
                if score_val >= threshold_pass: return 'Pass'
                if not pd.isna(result_val) and result_val != 'No assertion': return 'Fail'
                return result_val
            
            match loadResultsTask.status():
                case 'initial':
                    return ui.div(ui.strong("Responses will show up here"))
                case 'running':
                    return ui.div(ui.strong("Extracting responses..."))

            data = loadResultsTask.result().copy()
            if data.empty: return

            eval_set_name = input.select_eval_set()
            eval_sets = getEvalSetToCompare()
            
            eval_name_keys = []
            
            for eval_name_key, _ in eval_sets[eval_set_name]['Evals to compare']:
                data[f'Response ({eval_name_key})'] = data.apply(lambda x: formatResponse(x, col_suffix=f' ({eval_name_key})', type=eval_name_key.lower()), axis=1)
                
                col_result = f'Result ({eval_name_key})'

                if hasAssertion(data, col_result):
                    threshold_pass = input.numeric_threshold()
                    data[col_result] = data.apply(lambda x: getResultBasedOnScoreThreshold(x[f'Score ({eval_name_key})'], x[f'Result ({eval_name_key})'], threshold_pass), axis=1)

                eval_name_keys.append(eval_name_key)
                    
            style_dict={}
            if not data.empty:
                for i, row in data.iterrows():
                    style_dict[f'row_{i}_col_0'] = 'app-table-row-no-assertion'
                    for j, eval_name_key in enumerate(eval_name_keys):
                        col_name = f'Result ({eval_name_key})'
                        match row[col_name]:
                            case 'Pass':
                                style_dict[f'row_{i}_col_{j+1}'] = 'app-table-row-pass'
                            case 'Fail':
                                style_dict[f'row_{i}_col_{j+1}'] = 'app-table-row-fail'
                            case _:
                                style_dict[f'row_{i}_col_{j+1}'] = 'app-table-row-no-assertion'

            table = prettyTableUI(data[["Model"] + [f"Response ({eval_name_key})" for eval_name_key in eval_name_keys]], 
                                  col_widths=[1, 3, 5, 3], 
                                  style_dict=style_dict)

            return table
        
    ui.include_js(Config.DIR_HOME / "www" / "js" / "table.js", method='inline')

    def hasAssertion(data, col_result):
        if data.empty: return False
        if len(data[col_result].unique()) == 0: return False
        return not (data[col_result].unique() == ['No assertion']).all()
    
    @reactive.calc
    def getEvalSetToCompare():
        try:
            eval_sets = loadYML(Config.DIR_DATA / 'compare' / f'compare.yaml')
        except:
            return {}
        return eval_sets
    
    @reactive.effect
    def loadEvalSets():
        eval_sets = getEvalSetToCompare()
        ui.update_select(id='select_eval_set', choices={k: v['Name'] for k, v in eval_sets.items()})

    @reactive.effect
    @reactive.event(input.select_eval_set)
    def loadEvals():
        try:
            prompts = loadYML(Config.DIR_DATA / 'compare' / f'{input.select_eval_set()}.yaml')['prompts']
        except:
            return
        
        ui.update_select(id='select_prompt', choices=prompts)

    @reactive.calc
    @reactive.event(input.select_eval_set)
    def loadVars():
        try:
            tests = loadYML(Config.DIR_DATA / 'compare' / f'{input.select_eval_set()}_tests.yaml')['tests']    
        except:
            return {}
        
        d_vars = {}
        for test in tests:
            for k, v in test['vars'].items():
                d_vars[k] = d_vars.get(k, []) + [v]
        d_vars = {k: pd.unique(pd.Series(v)) for k, v in d_vars.items()}
        return d_vars
    
    @reactive.calc
    @reactive.event(input.select_prompt, var_selected)
    def getPrompt():
        
        prompt = input.select_prompt.get()
        d_vars = loadVars()
        var_sel = var_selected.get()

        if not prompt or (d_vars and len(d_vars) != len(var_sel)): return ''
        
        try:
            prompt = prompt.format(**var_sel)
        except:
            prompt = ''
    
        return prompt
    
    @reactive.extended_task
    async def loadResultsTask(eval_set_name, prompt, d_vars, var_sel, eval_sets):

        async def run():

            eval_outputs_to_compare = pd.DataFrame(columns=['Prompt', *list(d_vars.keys()), 'Model', 
                                                            'Response', 'Result', 'Score', 'Used Context', 
                                                            'Searched Keyphrases', 'Reason'])
            for [eval_name_key, eval_name] in eval_sets[eval_set_name]['Evals to compare']:
                eval_output= Evaluator.processResults(eval_name=eval_name, prompt=prompt, d_vars=var_sel)
                
                if eval_output.empty: return pd.DataFrame()
                
                eval_output['Model'] = eval_output['Model'].apply(lambda x: re.sub(r'(.* \[)(.*)(\])', repl=r'\2', string=x))
                eval_outputs_to_compare = pd.merge(left=eval_outputs_to_compare, right=eval_output, on=['Prompt', *list(d_vars.keys()), 'Model'], suffixes=[None, f' ({eval_name_key})'], how='outer')
            
            for col in eval_outputs_to_compare.columns:
                if col.startswith('Response'):
                    eval_outputs_to_compare.loc[eval_outputs_to_compare[col].isna(), col] = ''

            return eval_outputs_to_compare.sort_values('Model')
        
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

        loadResultsTask(eval_set_name, prompt, d_vars, var_sel, eval_sets)

    def selectVar(var_sel):
        var_selected.set({**var_selected.get(), **var_sel})