from pathlib import Path
import dotenv
import yaml

class Config:
    DIR_HOME = Path(__file__).parent.parent
    DIR_TESTS = DIR_HOME /'tests'
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
    with open(file_path) as stream:
        try:
            data = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
    return data