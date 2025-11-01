from pathlib import Path
import dotenv
import yaml
import uuid

class Config:
    DIR_HOME = Path(__file__).parent.parent
    DIR_CONFIG = DIR_HOME / 'config'
    DIR_CACHE = DIR_HOME / 'cache'
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
    with open(file_path) as fp:
        data = yaml.safe_load(fp)
    return data

def saveYML(data, file_path):

    class MyDumper(yaml.Dumper):
        def increase_indent(self, flow=False, indentless=False):
            return super(MyDumper, self).increase_indent(flow, False)

    with open(file_path, mode='w') as fp:
        yaml.dump(data, fp, Dumper=MyDumper, default_flow_style=False)

def getUIID(prefix):
    return f'{prefix}_{str(uuid.uuid4()).replace('-', '_')}'