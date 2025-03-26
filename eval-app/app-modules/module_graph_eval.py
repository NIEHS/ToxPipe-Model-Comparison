from shiny import reactive
from shiny.express import ui, module, render
from shinywidgets import render_widget
import plotly.express as px
from utils import Config, getNoDataPlot
from .utils import Evaluator
from .module_common import mod_vars
import pandas as pd

@module
def module_graph(input, output, session, eval_name):

    var_selected = reactive.value({})

    with ui.div(class_='row border round mt-3 p-3'):
        with ui.div(class_='row'):
            with ui.div(class_='col'):
                ui.strong(eval_name)
            @render.express
            def showVars():
                data = loadEvalResults()
                if data.empty: return
                for col in data.columns[9:]:
                    with ui.div(class_='col'):
                        mod_vars(col, var_name=col, var_values=['Any'] + list(data[col].values), fn_reactive=selectVar)

        with ui.div(class_='row gap-1'):
            @render.express
            def showPlots():
                with ui.div(class_='col'):
                    with ui.card(fill=True):
                        @render_widget
                        def showPassFailStatPlot():
                            return plotPassFailStat()
                        
                with ui.div(class_='col'):
                    with ui.card(fill=True):
                        @render_widget
                        def showAssertionStatPlot():
                            return plotAssertionStat()
                        
                if eval_name.startswith('rag'):
                    with ui.div(class_='col'):
                        with ui.card(fill=True):
                            @render_widget
                            def showContextSearchStat():
                                return plotContextSearchStat()

                
    @reactive.calc
    def loadEvalResults():
        return Evaluator.processResults(eval_name)

    def selectVar(var_sel):
        var_selected.set({**var_selected.get(), **var_sel})

    def filterDataByVars(data, var_info):

        indices = None
        for var_name, var_value in var_info.items():
            if var_name in data.columns:
                if indices is None:
                    indices = set(data[data[var_name] == var_value].index if var_value != 'Any' else data.index)
                else:
                    indices &= set(data[data[var_name] == var_value].index if var_value != 'Any' else data.index)
        if indices is None: indices = []
        return data.loc[sorted(indices)]

    @reactive.calc
    @reactive.event(var_selected)
    def plotPassFailStat():

        data = loadEvalResults()
        data = filterDataByVars(data, var_selected.get())

        if data.empty: return getNoDataPlot(title='Correct Responses')

        df_plot = data.groupby('Model')['Result'].value_counts().reset_index()

        df_missing = []
        for m in df_plot['Model'].unique():
            for r in ['Pass', 'Fail']:
                if df_plot.query('(Model == @m) and (Result == @r)').shape[0] == 0:
                    df_missing.append({'Model': m, 'Result': r, 'count': 0})
        
        df_plot = pd.concat([df_plot, pd.DataFrame(df_missing)]).sort_values('Model')

        category_orders = {'Result':['Pass', 'Fail', 'No assertion']}
        category_colors = ['#7c8fe6', '#eb8c60', '#dbd8d0']

        fig = px.bar(df_plot, x='count', y='Model', color='Result', orientation='h', 
                     category_orders=category_orders, 
                     color_discrete_sequence=category_colors)

        fig.update_layout(
            title="Correct Responses",
            barmode='stack',
            **Config.CONFIG_PLOT
        )

        fig.update_xaxes(visible=False)

        return fig
    
    @reactive.calc
    @reactive.event(var_selected)
    def plotAssertionStat():

        data = loadEvalResults()
        data = filterDataByVars(data, var_selected.get())

        if data.empty: return getNoDataPlot(title='Correct Assertions in Responses')
            
        def getAssertionCount(reason, result):
            if result == 'No assertion': return (1, result, 1)
            if not isinstance(reason, list): return (0, result, 1)
            s = 0
            for y in reason:
                s += y['pass']
            return (s, 'Pass', len(reason))
        
        df_assertion_count = (data.apply(lambda x: getAssertionCount(x['Reason'], x['Result']), axis=1, result_type='expand')
                                .rename(columns={0: 'Count', 1: 'Result', 2: 'Total assertions'})
        )
        df_assertion_count['Model'] = data['Model']

        indices_no_assertion = (df_assertion_count['Result'] == 'No assertion')
        
        df_no_assertion = df_assertion_count[indices_no_assertion].reset_index(drop=True)
        df_pass = df_assertion_count[~indices_no_assertion].reset_index(drop=True)
        df_fail = pd.DataFrame({'Model': df_pass['Model'], 
                                     'Result': 'Fail', 
                                     'Count': df_pass['Total assertions'] - df_pass['Count']})
    
        df_plot = pd.concat([df_pass[['Model', 'Result', 'Count']], 
                             df_fail[['Model', 'Result', 'Count']],
                             df_no_assertion[['Model', 'Result', 'Count']]], axis=0)
        

        df_plot = df_plot.groupby(['Model', 'Result'])['Count'].sum().reset_index().sort_values('Model')

        category_orders = {'Result':['Pass', 'Fail', 'No assertion']}
        category_colors = ['#7c8fe6', '#eb8c60', '#dbd8d0']
        
        fig = px.bar(df_plot, x='Count', y='Model', color='Result', orientation='h',
                     category_orders=category_orders, 
                     color_discrete_sequence=category_colors)

        fig.update_layout(
            title="Correct Assertions in Responses",
            barmode='stack',
            **Config.CONFIG_PLOT
        )

        fig.update_xaxes(visible=False)

        return fig
    
    @reactive.calc
    @reactive.event(var_selected)
    def plotContextSearchStat():

        data = loadEvalResults()
        data = filterDataByVars(data, var_selected.get())

        if data.empty: return getNoDataPlot(title='Context search frequency')

        data['Used Context'] = data['Used Context'].apply(lambda x: 'From Resources' if x else 'From Training Data')
        df_plot = data.groupby('Model')['Used Context'].value_counts().reset_index().sort_values('Model')
        
        category_orders = {'Used Context':['From Resources', 'From Training Data']}
        category_colors = ['#7c8fe6', '#eb8c60']
        
        fig = px.bar(df_plot, x='count', y='Model', color='Used Context', orientation='h',
                     category_orders=category_orders, 
                     color_discrete_sequence=category_colors)

        fig.update_layout(
            title="Context search frequency",
            barmode='stack',
            **Config.CONFIG_PLOT
        )

        fig.update_xaxes(visible=False)

        return fig
    
@module
def mod_ui(input, output, session):

    with ui.div(class_="row gap-5"):
        with ui.div(class_="col d-flex justify-content-start align-items-center gap-2"):
            ui.input_select("select_level", "Levels", choices={'any': 'Any', 'base-model': 'Base model', 'rag': 'RAG', 'agentic': 'Agentic'})
            ui.input_select("select_prompt", "Prompts", choices={'any': 'Any', 'tox-type-assertion-prompt': 'Tox type prompts', 'abt-qa-assertion-prompts': 'ABT Q/A'})
            ui.input_select("select_species", "Species", choices={'any': 'Any', 'human': 'Human', 'rat': 'Rat'})
            ui.input_select("select_eval", "Evals", choices=[])
        with ui.div(class_="col d-flex pb-3 justify-content-end align-items-end"):
            @render.download(
                filename='eval_report.csv',
                label = 'Download Report'
            )
            async def downloadReport():

                d_eval_prompt = {'tox-type-assertion-prompts_human': 'Toxicity type prompts (Human)',
                                 'tox-type-assertion-prompts_rat': 'Toxicity type prompts (Rat)', 
                                'abt-qa-assertion-prompts_mixed': 'ABT Q/A prompts'}

                eval_name = input.select_eval()
                if eval_name == 'Any':
                    evals = getEvals()
                else:
                    evals = [eval_name]

                df_report = {}
                for eval_name in evals:
                    data = Evaluator.processResults(eval_name)
                    if data.empty: continue
                    total_assertions = data.query('Result != "No assertion"').groupby('Model')['Result'].count()
                    data_pass_perc = (data
                                        .groupby('Model')['Result']
                                        .value_counts()
                                        .reset_index()
                                        .pivot(index='Model', columns='Result', values='count'))
                    
                    if data_pass_perc.columns.isin(['Pass']).any(): 
                        data_pass_perc.loc[data_pass_perc['Pass'].isna(), 'Pass'] = 0
                    else:
                        data_pass_perc['Pass'] = 0
                    
                    data_pass_perc['Assertion'] =  data_pass_perc['Pass'] + data_pass_perc['Fail']
                    data_pass_perc['Perc'] = data_pass_perc['Pass'] * 100 / data_pass_perc['Assertion']
                    header = f'{d_eval_prompt['_'.join(eval_name.split('_')[1:])]} ({int(total_assertions.iloc[0])})'
                    data_pass_perc = data_pass_perc[['Perc']].rename(columns={'Perc': header}).to_dict()
                    for k, v in data_pass_perc.items():
                        df_report[k] = {**df_report.get(k, {}), **v}
                    
                df_report = pd.DataFrame(df_report)
                yield df_report.to_csv()

    @render.express
    def showPlots():
        loadResults()

    @reactive.calc
    @reactive.event(input.select_level, input.select_prompt, input.select_species)
    def getEvals():

        levels_allowed = ['base-model', 'rag', 'agentic']
        prompts_allowed = ['tox-type-assertion-prompts', 'abt-qa-assertion-prompts']
        species_allowed = ['human', 'rat', 'mixed']

        eval_dict = {eval_name: index for index, eval_name in enumerate([f'{f}_{p}_{s}' for f in levels_allowed for p in prompts_allowed for s in species_allowed])}
        
        level, prompt, species = input.select_level(), input.select_prompt(), input.select_species()

        evals = []
        for test in Config.DIR_TESTS.iterdir():
            if Evaluator.hasOutput(test.name):
                if level != 'any' and not test.name.startswith(level): continue
                if prompt != 'any' and prompt not in test.name: continue
                if species != 'any' and not test.name.endswith(level): continue
                if level == 'any': 
                    for l in levels_allowed:
                        if test.name.startswith(l):
                            break
                    else:
                        continue
                if prompt == 'any': 
                    for p in prompts_allowed:
                        if p in test.name:
                            break
                    else:
                        continue
                if species == 'any': 
                    for s in species_allowed:
                        if test.name.endswith(s):
                            break
                    else:
                        continue
                    
                evals.append(test.name)
        
        return sorted(evals, key=lambda x: eval_dict[x])

    @reactive.effect
    @reactive.event(input.select_level, input.select_prompt, input.select_species)
    def loadEvalMenu():
        evals = getEvals()
        ui.update_select(id='select_eval', choices=['Any'] + evals)

    @reactive.calc
    @reactive.event(input.select_level, input.select_prompt, input.select_species, input.select_eval)
    def loadResults():
        eval_name = input.select_eval()
        if eval_name == 'Any':
            evals = getEvals()
            return [module_graph(f'eval_{i}', ev) for i, ev in enumerate(evals)]
        return module_graph('eval_0', eval_name)    