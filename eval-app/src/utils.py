from pathlib import Path
import dotenv
import yaml

class Config:
    DIR_HOME = Path(__file__).parent.parent
    DIR_DATA = DIR_HOME / 'data'
    RANDOM_STATE = 1000
    CONFIG_PLOT = dict(
                        template = 'simple_white',
                        font = dict(
                                    family="Times new roman",
                                    size=16,
                                    color="RebeccaPurple"
                                )
    )

    env_config = dotenv.dotenv_values(DIR_HOME / '.env')

def loadYML(file_path):
    data = None
    try:
        with open(file_path) as stream:
            data = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)
    return data

def saveYML(data, file_path):

    class MyDumper(yaml.Dumper):
        def increase_indent(self, flow=False, indentless=False):
            return super(MyDumper, self).increase_indent(flow, False)

    with open(file_path, mode='w') as fp:
        yaml.dump(data, fp, Dumper=MyDumper, default_flow_style=False)