from pathlib import Path
from dotenv import dotenv_values, load_dotenv

class Config():

    DIR_HOME = Path(__file__).parent.parent
    DIR_DATA = (DIR_HOME / 'data')
    DIR_RESULTS = (DIR_HOME / 'results')

    env_config = dotenv_values(".env")