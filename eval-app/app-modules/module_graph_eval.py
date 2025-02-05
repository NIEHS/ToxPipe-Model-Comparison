from shiny import reactive
from shiny.express import ui, module, render
from shinywidgets import render_widget
import plotly.express as px
from utils import Config, processResults, getNoDataPlot
import pandas as pd

@module
def module_graph(input, output, session, eval_name):

    with ui.div(class_='row border round mt-3 p-3'):
        with ui.div(class_='row'):
            with ui.div(class_='col'):
                ui.strong(eval_name)
            with ui.div(class_='col'):
                ui.input_select("select_var", "Variables", choices=[])

        with ui.div(class_='row'):

            with ui.div(class_='col'):
                with ui.card(fill=True):
                    @render_widget
                    def showPassFailStatPlot():
                        return plotPassFailStatByTest()
                    
            with ui.div(class_='col'):
                with ui.card(fill=True):
                    @render_widget
                    def showAssertionStatPlot():
                        return plotAssertionStatByTest()
                
    @reactive.calc
    def loadResults():
        dir_output = Config.DIR_TESTS / eval_name / 'output'
        data = pd.DataFrame()
        if (dir_output / 'output.json').exists():
            data = processResults(dir_output)
        return data

    @reactive.effect
    def loadVars():
        data = loadResults()
        if data.empty: return
        ui.update_select(id="select_var", choices=['Any'] + sorted(data['Variable'].unique()))

    # @reactive.calc
    # @reactive.event(input.select_eval)
    # def loadVars():
    #     data = loadResults()
    #     if data.empty: return {}
    #     d_var = {}
    #     for val in data['Variable']:
    #         vars_ = val.split(', ')
    #         for v in vars_:
    #             var_name, var_value = v.split(':')
    #             d_var[var_name] = d_var.get(var_name, set()) | {var_value}
    #     return d_var
            
    @reactive.calc
    @reactive.event(input.select_var)
    def plotPassFailStatByTest():
        data = loadResults()
        
        var = input.select_var()
        if var == 'Any':
            data = data.copy()
        else:
            data = data.query('Variable == @var')

        return getPassFailStatPlot(data)
    
    @reactive.calc
    @reactive.event(input.select_var)
    def plotAssertionStatByTest():
        data = loadResults()
        var = input.select_var()
        if var == 'Any':
            data = data.copy()
        else:
            data = data.query('Variable == @var')

        return getAssertionStatPlot(data)

    def getPassFailStatPlot(data: pd.DataFrame):

        if data.empty: return getNoDataPlot(title='Correct Responses')

        df_plot = data.groupby('Model')['Result'].value_counts().reset_index()

        df_missing = []
        for m in df_plot['Model'].unique():
            for r in ['Pass', 'Fail']:
                if df_plot.query('(Model == @m) and (Result == @r)').shape[0] == 0:
                    df_missing.append({'Model': m, 'Result': r, 'count': 0})
        
        df_plot = pd.concat([df_plot, pd.DataFrame(df_missing)]).sort_values('Model')

        category_orders = {'Result':['Pass', 'Fail']}
        category_colors = ['#7c8fe6', '#eb8c60']

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
    
    def getAssertionStatPlot(data: pd.DataFrame):

        if data.empty: return getNoDataPlot(title='Correct Assertions in Responses')
            
        def getAssertionPassCount(reason):
            if not isinstance(reason, list): return (0, 'Pass', 1)
            if 'components' not in reason[0]: return (int(reason[0]['pass']), 'Pass', 1)
            s = 0
            for y in reason[0]['components']:
                s += y['pass']
            return (s, 'Pass', len(reason[0]['components']))
        
        df_plot_pass = (data.apply(lambda x: getAssertionPassCount(x['Reason']), axis=1, result_type='expand')
                                .rename(columns={0: 'Count', 1: 'Result', 2: 'Total assertions'})
        )
        df_plot_pass['Model'] = data['Model']
        df_plot_fail = pd.DataFrame({'Model': df_plot_pass['Model'], 
                                     'Result': 'Fail', 
                                     'Count': df_plot_pass['Total assertions'] - df_plot_pass['Count']})
    
        df_plot = pd.concat([df_plot_pass[['Model', 'Result', 'Count']], 
                             df_plot_fail[['Model', 'Result', 'Count']]], axis=0)

        df_plot = df_plot.groupby(['Model', 'Result'])['Count'].sum().reset_index().sort_values('Model')

        category_orders = {'Result':['Pass', 'Fail']}
        category_colors = ['#7c8fe6', '#eb8c60']
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

@module
def mod_ui(input, output, session):

    with ui.div(class_="d-flex gap-5"):
        ui.input_select("select_level", "Levels", choices={'any': 'Any', 'zero-shot': 'Zero-shot', 'rag': 'RAG', 'agentic': 'Agentic'})
        ui.input_select("select_prompt", "Prompts", choices={'any': 'Any', 'tox-type-assertion-prompt': 'Tox type prompts', 'abt-qa-assertion-prompts': 'ABT Q/A'})
        ui.input_select("select_species", "Species", choices={'any': 'Any', 'human': 'Human', 'rat': 'Rat'})
        ui.input_select("select_eval", "Evals", choices=[])

        # @module
        # def vars_ui(input, output, session, var_info, data, fn):

        #     @reactive.calc
        #     @reactive.event(input.select_eval, [input[f'select_var_{var_name}'] for var_name in var_info.keys])
        #     def loadPassFailStatPlot():
        #         fn(data)

        #     return [ui.input_select(f"select_var_{var_name}", var_name, choices=['Any'] + sorted(var_choices)) for var_name, var_choices in var_info.items()]
        
        # @render.ui
        # def showVars():
        #     var_info = loadVars()
        #     if not var_info: return
        #     data = loadResults()
        #     return [vars_ui(var_name, var_name=var_name, var_choices=var_choices, data=data, fn=plotPassFailStat) for var_name, var_choices in var_info.items()]
        #     #var_names = list(var_info.keys())
        #     #return [ui.input_select(f"select_var_{var_name}", var_name, choices=['Any'] + sorted(var_choices)) for var_name, var_choices in var_info.items()]
            
    @render.express
    def showPlots():
        loadResults()

    @reactive.calc
    @reactive.event(input.select_level, input.select_prompt, input.select_species)
    def getEvals():
        def sortKey(x):
            ai_frameworks = ['zero-shot', 'rag', 'agentic']
            prompts = ['tox-type-assertion-prompts', 'abt-qa-assertion-prompts']
            species = ['human', 'rat']
            evals = [f'{f}-{p}-{s}' for f in ai_frameworks for p in prompts for s in species]
            eval_dict = {v: len(evals)-i for i, v in enumerate(evals)}
            if x not in eval_dict: return 0
            return eval_dict[x]
        level, prompt, species = input.select_level(), input.select_prompt(), input.select_species()

        evals = []
        for test in Config.DIR_TESTS.iterdir():
            if test.is_dir() and (test / 'output' / 'output.json').exists():
                if level != 'any' and not test.name.startswith(level): continue
                if prompt != 'any' and prompt not in test.name: continue
                if species != 'any' and not test.name.endswith(level): continue
                evals.append(test.name)

        return sorted(evals, key=sortKey, reverse=True)

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
    