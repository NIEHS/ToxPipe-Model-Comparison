from pathlib import Path
from dotenv import dotenv_values

class Config():

    DIR_HOME = Path(__file__).parent.parent.parent
    
    env_config = dotenv_values(DIR_HOME / ".env")

    RANDOM_STATE = 1000

    NUM_THREADS = 2
    
    TIMEOUT_SHORT_TASK = 120 # 2 minute

    TIMEOUT_LONG_TASK = 240 # 4 minute