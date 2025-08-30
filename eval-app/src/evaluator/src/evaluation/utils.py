from pathlib import Path
from dotenv import dotenv_values, load_dotenv

class Config():

    DIR_HOME = Path(__file__).parent.parent
    
    env_config = dotenv_values(DIR_HOME / ".env")

    RANDOM_STATE = 1000