
from pathlib import Path
import plotly.express as px
import yaml

class Config:
    DIR_HOME = Path(__file__).parent
    DIR_TESTS = DIR_HOME /'tests1'
    DIR_CODES = DIR_HOME /'codes'
    RANDOM_STATE = 1000
    CONFIG_PLOT = dict(
                        template = 'simple_white',
                        font = dict(
                                    family="Times new roman",
                                    size=16,
                                    color="RebeccaPurple"
                                )
    )

def loadYML(file_path):
    data = None
    with open(file_path) as stream:
        try:
            data = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
    return data

def saveYML(data, file_path):
    
    class MyDumper(yaml.Dumper):
        def increase_indent(self, flow=False, indentless=False):
            return super(MyDumper, self).increase_indent(flow, False)
        
    with open(file_path, 'w') as outfile:
        yaml.dump(data, outfile, Dumper=MyDumper, default_flow_style=False)

def getNoDataPlot(title):
        
    fig = px.scatter(x=[0.5], y=[0.5], text=['No data found<br />or<br />Error in data extraction'], size=[0]) 
    fig.update_layout(
        title=title,
        **Config.CONFIG_PLOT
    )

    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
                        
    return fig