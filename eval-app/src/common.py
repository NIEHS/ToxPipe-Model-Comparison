from shiny import reactive
from shiny.express import ui, module
import faicons as fa
import plotly.express as px

from .utils import Config

@module
def mod_vars(input, output, session, var_name, var_values, fn_reactive):

    @reactive.effect
    @reactive.event(input.select_var)
    def selectVar():
        fn_reactive({var_name: input.select_var()})
        
    ui.input_select('select_var', var_name[0].upper() + var_name[1:].replace('_', ' '), choices=var_values)

def getNoDataPlot(title):
        
    fig = px.scatter(x=[0.5], y=[0.5], text=['No data found<br />or<br />Error in data extraction'], size=[0]) 
    fig.update_layout(
        title=title,
        **Config.CONFIG_PLOT
    )

    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
                        
    return fig

def hasAssertion(data, col_result='Result'):
    if data.empty: return False
    return bool((data[col_result] != 'No assertion').any())

def getExplanationHTML(result):

    def resultStr(res):
        return f"<span class='passed'>{fa.icon_svg('circle-check')}</span>" if res else f"<span class='failed'>{fa.icon_svg('circle-xmark')}</span>"

    def getComponentExplanation(results):
        text = ''
        has_component, has_multiple_eval_models = False, False
        for result in results:
            if 'components' in result:
                text += f"<strong>{result['reason']} {resultStr(result['pass'])}</strong>"
                text += f"<ul>{getComponentExplanation(result['components'])}</ul>"
                has_component = True
            if 'eval_model' in result:
                text += f"<strong>Model: {result['eval_model']}</strong>"
                text += f"<ul>{getComponentExplanation(result['reason'])}</ul>"
                has_multiple_eval_models = True

        if not (has_component or has_multiple_eval_models):
            for result in results:
                text += f"<li>{result['reason']} {resultStr(result['pass'])}</li>"
            
        return text

    if not isinstance(result, list): return "No reason found"
    return getComponentExplanation(result)