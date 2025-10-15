from shiny import reactive
from shiny.express import ui, module
from .utils import Config
import plotly.express as px

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