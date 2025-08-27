from shiny import reactive, ui as core_ui
from shiny.express import ui, render, module
from shinywidgets import render_plotly
import pandas as pd
import faicons as fa
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity
from umap import UMAP
import plotly.express as px
from utils import Config, loadYML
from .module_common import mod_vars
from .utils import Evaluator
from .db import getRating, saveRating
import re
import asyncio

ico_check = """<span class='passed'><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-check-circle-fill" viewBox="0 0 16 16">
  <path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0m-3.97-3.03a.75.75 0 0 0-1.08.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-.01-1.05z"/>
</svg></span>"""

ico_cross = """<span class='failed'><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-x-circle-fill" viewBox="0 0 16 16">
  <path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0M5.354 4.646a.5.5 0 1 0-.708.708L7.293 8l-2.647 2.646a.5.5 0 0 0 .708.708L8 8.707l2.646 2.647a.5.5 0 0 0 .708-.708L8.707 8l2.647-2.646a.5.5 0 0 0-.708-.708L8 7.293z"/>
</svg></span>
"""

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

    var_selected = reactive.value(None)

    def getExplanationHTML(result):

        def resultStr(res):
            return ico_check if res else ico_cross

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
        ui.input_select("select_eval_set", "Eval set", choices={'basic-prompts_human': 'Basic prompts (Human)', 
                                                                'basic-prompts_rat': 'Basic prompts (Rat)',
                                                                'tox-type-assertion-prompts_human': 'Tox type prompts (Human)', 
                                                                'tox-type-assertion-prompts_rat': 'Tox type prompts (Rat)',
                                                                'abt-qa-assertion-prompts_mixed': 'ABT Q/A'})
        ui.input_select("select_prompt", "Prompts", choices=[])
        @render.express
        def showVars():
            d_vars = loadVars()
            for k, v in d_vars.items():
                mod_vars(f'vars_{k}', var_name=k, var_values=v, fn_reactive=selectVar)

    with ui.div(class_='d-flex flex-column gap-2'):
        with ui.div():
            "Prompt"
        with ui.div(class_='d-flex border rounded p-3 justify-content-center'):
            with ui.div(class_='prompt'):
                @render.ui
                def showPrompt():
                    prompt = input.select_prompt()
                    vars = {} if var_selected.get() is None else var_selected.get()
                    try:
                        prompt = prompt.format(**vars)
                    except:
                        prompt = ''
                    return core_ui.markdown(prompt)

        @render.express
        def showTopBar():

            data = loadResultsByFilters().copy()
            
            if not hasAssertion(data): return

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
                                        core_ui.div(f'[The following response was taken from {("RAG resources" if x[f'Used Context{col_suffix}'] else "model's training knowledge")}]',
                                                    class_='fst-italic fw-bold mb-4'),
                                        core_ui.div(core_ui.markdown(x[f'Response{col_suffix}'])),
                                        class_='app-table-content'
                                    )
                    )
                #data.apply(lambda x: addReason(x) if x['Result'] != 'No assertion' else x['Result'], axis=1)
                return addReason(x, col_suffix, type, core_ui.div(core_ui.markdown(x[f'Response{col_suffix}']), class_='app-table-content'))
            
            data = loadResultsByFilters().copy()
            
            if data.empty: return
            
            data['Response'] = data.apply(lambda x: formatResponse(x, col_suffix='', type='base'), axis=1)
            data['Response (RAG)'] = data.apply(lambda x: formatResponse(x, col_suffix=' (RAG)', type='rag'), axis=1)
            data['Response (Agentic)'] = data.apply(lambda x: formatResponse(x, col_suffix=' (Agentic)', type='agentic'), axis=1)

            if hasAssertion(data):
                
                threshold_pass = input.numeric_threshold()

                data['Result'] = data.apply(lambda x: 'Pass' if x['Score'] >= threshold_pass else 'Fail' if not pd.isna(x['Result']) and x['Result'] != 'No assertion' else x['Result'], axis=1) 
                data['Result (RAG)'] = data.apply(lambda x: 'Pass' if x['Score (RAG)'] >= threshold_pass else 'Fail' if not pd.isna(x['Result (RAG)']) and x['Result (RAG)'] != 'No assertion' else x['Result (RAG)'], axis=1) 
                data['Result (Agentic)'] = data.apply(lambda x: 'Pass' if x['Score (Agentic)'] >= threshold_pass else 'Fail' if not pd.isna(x['Result (Agentic)']) and x['Result (Agentic)'] != 'No assertion' else x['Result (Agentic)'], axis=1) 

            style_dict={}
            if not data.empty:
                for i, row in data.iterrows():
                    style_dict[f'row_{i}_col_0'] = 'app-table-row-no-assertion'
                    for j, col_name in [(1, 'Result'), (2, 'Result (RAG)'), (3, 'Result (Agentic)')]:
                        match row[col_name]:
                            case 'Pass':
                                style_dict[f'row_{i}_col_{j}'] = 'app-table-row-pass'
                            case 'Fail':
                                style_dict[f'row_{i}_col_{j}'] = 'app-table-row-fail'
                            case _:
                                style_dict[f'row_{i}_col_{j}'] = 'app-table-row-no-assertion'

            table = prettyTableUI(data[["Model", "Response", "Response (RAG)", "Response (Agentic)"]], col_widths=[1, 3, 5, 3], style_dict=style_dict)

            return table
        
    ui.include_js(Config.DIR_HOME / "www" / "js" / "table.js", method='inline')

    def hasAssertion(data):
        if data.empty: return False
        if len(data['Result'].unique()) == 0: return False
        return not (data['Result'].unique() == ['No assertion']).all()

    @reactive.effect
    @reactive.event(input.select_eval_set)
    def loadEvals():
        try:
            prompts = loadYML(Config.DIR_TESTS / 'config' / f'{input.select_eval_set()}.yaml')['prompts']
        except:
            return
        ui.update_select(id='select_prompt', choices=prompts)

    @reactive.calc
    @reactive.event(input.select_eval_set)
    def loadVars():
        try:
            tests = loadYML(Config.DIR_TESTS / 'config' / f'{input.select_eval_set()}_tests.yaml')['tests']    
        except:
            return {}
        d_vars = {}
        for test in tests:
            for k, v in test['vars'].items():
                d_vars[k] = d_vars.get(k, []) + [v]
        return d_vars

    @reactive.calc
    @reactive.event(input.select_eval_set)
    def loadResults():
        d_vars = loadVars()
        eval_set_name = input.select_eval_set()
        output_base = Evaluator.processResults(f'base-model_{eval_set_name}')
        output_rag = Evaluator.processResults(f'rag_{eval_set_name}')
        output_agentic = Evaluator.processResults(f'agentic_{eval_set_name}')
        
        if output_base.empty or output_rag.empty or output_agentic.empty:
            return pd.DataFrame()
        
        output_rag['Model'] = output_rag['Model'].apply(lambda x: re.sub(r'(Toxpipe \(RAG\) \[)(.*)(\])', repl=r'\2', string=x))
        output_agentic['Model'] = output_agentic['Model'].apply(lambda x: re.sub(r'(Toxpipe \(Agentic\) \[)(.*)(\])', repl=r'\2', string=x))
        output = (pd.merge(left=output_base, right=output_rag, on=['Prompt', *list(d_vars.keys()), 'Model'], suffixes=[None, ' (RAG)'], how='outer')
                    .merge(right=output_agentic, on=['Prompt', *list(d_vars.keys()), 'Model'], suffixes=[None, ' (Agentic)'], how='outer'))
        
        for col in output.columns:
            if col.startswith('Response'):
                output.loc[output[col].isna(), col] = ''
        return output
    
    @reactive.calc
    @reactive.event(input.select_eval_set, input.select_prompt, var_selected, ignore_none=True)
    def loadResultsByFilters():
        data = loadResults()
        if data.empty: return data
        if not var_selected.get(): return pd.DataFrame()

        indices = None
        for var_name, var_value in var_selected.get().items():
            if var_name in data.columns:
                if indices is None:
                    indices = set(data[data[var_name] == var_value].index)
                else:
                    indices &= set(data[data[var_name] == var_value].index)
        if indices is None: indices = []
        data = data.loc[sorted(indices)]
        
        cols = ["Model", "Response", "Response (RAG)", "Response (Agentic)", 
                "Result", "Result (RAG)", "Result (Agentic)", 
                "Score", "Score (RAG)", "Score (Agentic)",
                "Used Context (RAG)", "Searched Keyphrases (RAG)",
                "Reason", "Reason (RAG)", "Reason (Agentic)"]

        prompt = input.select_prompt()
        res = data.query('Prompt == @prompt')[cols].reset_index(drop=True).sort_values('Model')

        return res

    def selectVar(var_sel):
        vars = {} if var_selected.get() is None else var_selected.get()
        var_selected.set({**vars, **var_sel})