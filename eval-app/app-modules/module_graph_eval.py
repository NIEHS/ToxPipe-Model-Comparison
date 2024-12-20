from shiny import reactive
from shiny.express import ui, module
from shinywidgets import render_widget
import plotly.express as px
from utils import Config, processResults
import pandas as pd

@module
def mod_ui(input, output, session):

    with ui.div(class_="d-flex gap-5"):
        ui.input_select("select_eval", "Evals", choices=[])
        ui.input_select("select_var", "Variables", choices=[])

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

    with ui.div(class_='row'):
        with ui.div(class_='col'):
            with ui.card(fill=True):
                @render_widget
                def showPassFailStatPlot():
                    return plotPassFailStat()
                
        with ui.div(class_='col'):
            with ui.card(fill=True):
                @render_widget
                def showPassFailStatByVarPlot():
                    return plotPassFailStatByTest()
        

    @reactive.effect
    def loadEvals():
        ui.update_select(id='select_eval', choices=[test.name for test in Config.DIR_TESTS.iterdir() if test.is_dir() and (test / 'promptfooconfig.yaml').exists()])

    @reactive.calc
    @reactive.event(input.select_eval)
    def loadResults():
        dir_output = Config.DIR_TESTS / input.select_eval() / 'output'
        output = None
        if (dir_output / 'output.json').exists():
            output = processResults(dir_output)
        return output

    @reactive.effect
    @reactive.event(input.select_eval)
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
    @reactive.event(input.select_eval, input.select_var)
    def plotPassFailStat():
        data = loadResults()
        
        var = input.select_var()
        if var == 'Any':
            df_plot = data.copy()
        else:
            df_plot = data.query('Variable == @var')

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
    
    @reactive.calc
    @reactive.event(input.select_eval, input.select_var)
    def plotPassFailStatByTest():
        data = loadResults()
        var = input.select_var()
        if var == 'Any':
            df_plot = data.copy()
        else:
            df_plot = data.query('Variable == @var')

        def getAssertionPassCount(reason):
            if not isinstance(reason, list): return (0, 'Pass', 1)
            if 'components' not in reason[0]: return (int(reason[0]['pass']), 'Pass', 1)
            s = 0
            for y in reason[0]['components']:
                s += y['pass']
            return (s, 'Pass', len(reason[0]['components']))
        
        df_plot_pass = (df_plot.apply(lambda x: getAssertionPassCount(x['Reason']), axis=1, result_type='expand')
                                .rename(columns={0: 'Count', 1: 'Result', 2: 'Total assertions'})
        )
        df_plot_pass['Model'] = df_plot['Model']
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