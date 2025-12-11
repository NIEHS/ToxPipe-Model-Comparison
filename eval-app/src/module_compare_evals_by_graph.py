from shiny import reactive
from shiny.express import ui, module, render
from shinywidgets import render_plotly
import plotly.express as px
from .utils import Config, loadYML, getUIID
from .utils_eval import Evaluator
from .common import mod_vars, getNoDataPlot
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
                data = loadEvalResults().copy()
                if data.empty: return
                for col in data.columns[Evaluator.NUM_NONVARS_COLS:]:
                    with ui.div(class_='col'):
                        mod_vars(col, var_name=col, var_values=['Any'] + list(data[col].values), fn_reactive=selectVar)

        with ui.div(class_='row gap-1'):
    
            with ui.div(class_='col'):
                with ui.card(fill=True):
                    with ui.div(class_='d-flex justify-content-center align-items-center'):
                        @render_plotly
                        def showPassFailStatPlot():
                            return plotPassFailStat()
                    
            with ui.div(class_='col'):
                with ui.card(fill=True):
                    with ui.div(class_='d-flex justify-content-center align-items-center'):
                        @render_plotly
                        def showAssertionStatPlot():
                            return plotAssertionStat()
                    
            # @render.express
            # def showPlots():
            #     if eval_name.startswith('rag'):
            #         with ui.div(class_='col'):
            #             with ui.card(fill=True):
            #                 @render_widget
            #                 def showContextSearchStat():
            #                     return plotContextSearchStat()
                
    @reactive.calc
    def loadEvalResults():
        return Evaluator.processResults(eval_name)
    
    def selectVar(var_sel):
        var_selected.set({**var_selected.get(), **var_sel})

    def filterDataByVars(data, var_info):

        if not var_info: return data

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

        if not var_selected.get(): return

        data = loadEvalResults().copy()
        data = filterDataByVars(data, var_selected.get())

        if data.empty: return getNoDataPlot(title='Correct Responses')

        df_plot = data.query('Result != "No assertion"')[['Score', 'Model']].sort_values('Model')
        
        fig = px.violin(df_plot, x='Score', y='Model', orientation='h', box=True)

        fig.update_layout(
            title="Correct Responses",
            barmode='stack',
            **Config.CONFIG_PLOT
        )

        return fig
    
    @reactive.calc
    @reactive.event(var_selected)
    def plotAssertionStat():

        def getAssertionCount(reason, result):
            if result == 'No assertion': return (1, result, 1)
            if not isinstance(reason, list): return (0, result, 1)
            s = 0
            for y in reason:
                s += y['pass']
            return (s, 'Pass', len(reason))

        if not var_selected.get(): return

        data = loadEvalResults().copy()
        data = filterDataByVars(data, var_selected.get())

        if data.empty: return getNoDataPlot(title='Correct Assertions in Responses')
       
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
        category_colors = ["#b2cdff", "#f8adad", '#dbd8d0']
        
        fig = px.bar(df_plot, x='Count', y='Model', color='Result', orientation='h',
                     category_orders=category_orders, 
                     color_discrete_sequence=category_colors,
                     text_auto=True)

        fig.update_layout(
            title="Correct Assertions in Responses",
            barmode='stack',
            **Config.CONFIG_PLOT
        )

        fig.update_xaxes(visible=False)

        return fig
    
    # @reactive.calc
    # @reactive.event(var_selected)
    # def plotContextSearchStat():

    #     #if not var_selected.get(): return

    #     data = loadEvalResults().copy()
    #     data = filterDataByVars(data, var_selected.get())

    #     if data.empty: return getNoDataPlot(title='Context search frequency')

    #     breakpoint()

    #     data['Used Context'] = data['Used Context'].apply(lambda x: 'From Resources' if x else 'From Training Data')
    #     df_plot = data.groupby('Model')['Used Context'].value_counts().reset_index().sort_values('Model')
        
    #     category_orders = {'Used Context':['From Resources', 'From Training Data']}
    #     category_colors = ['#7c8fe6', '#eb8c60']
        
    #     fig = px.bar(df_plot, x='count', y='Model', color='Used Context', orientation='h',
    #                  category_orders=category_orders, 
    #                  color_discrete_sequence=category_colors)

    #     fig.update_layout(
    #         title="Context search frequency",
    #         barmode='stack',
    #         **Config.CONFIG_PLOT
    #     )

    #     fig.update_xaxes(visible=False)

    #     return fig
    
@module
def mod_ui(input, output, session):

    with ui.div(class_="row gap-5"):
        with ui.div(class_="col d-flex justify-content-start align-items-center gap-2"):
            ui.input_select("select_eval_set", "Eval sets", choices=[])
        with ui.div(class_="col d-flex pb-1 justify-content-start align-items-end"):
            ui.help_text("Only evals with assertions are shown in the report.")

    @render.express
    def showPlots():
        evals = loadEvals()
        for i, eval_name in enumerate(evals):
            module_graph(getUIID(f'eval_{i}'), eval_name=eval_name)

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
        eval_sets_with_assertions = {k: v['Name'] for k, v in eval_sets.items() if any(Evaluator.hasAssertion(eval_info['Eval Name']) for eval_info in v['Evals to compare'])}
        ui.update_select(id='select_eval_set', choices=eval_sets_with_assertions)

    @reactive.calc
    @reactive.event(input.select_eval_set)
    def loadEvals():
        eval_set_name = input.select_eval_set()

        if eval_set_name is None: return []

        eval_sets = {eval_set_name: getEvalSetToCompare()[eval_set_name]}

        evals = []
        for eval_set_name in eval_sets:
            for eval_info in eval_sets[eval_set_name]['Evals to compare']:
                if not Evaluator.hasAssertion(eval_info['Eval Name']): continue
                evals.append(eval_info['Eval Name'])

        return evals