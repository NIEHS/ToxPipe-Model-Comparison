from pathlib import Path
from dotenv import dotenv_values, load_dotenv

class Config():

    DIR_HOME = Path(__file__).parent.parent.parent
    DIR_TEST = (DIR_HOME / 'tests')

    env_config = dotenv_values(DIR_HOME / ".env")
    load_dotenv(DIR_HOME / ".env")

    RANDOM_STATE = 1000