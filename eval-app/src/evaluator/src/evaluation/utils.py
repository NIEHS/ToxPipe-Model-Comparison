from pathlib import Path
from dotenv import dotenv_values
from langfuse.langchain import CallbackHandler

import ssl
import httpx

class Config():

    DIR_HOME = Path(__file__).parent.parent.parent
    
    env_config = dotenv_values(DIR_HOME / ".env")

    RANDOM_STATE = 1000

    NUM_THREADS = 1
    
    TIMEOUT_SHORT_TASK = 120 # 2 minute

    TIMEOUT_LONG_TASK = 240 # 4 minute

    langfuse_handler = CallbackHandler(public_key=env_config['LANGFUSE_PUBLIC_KEY']) if bool(env_config.get('LANGFUSE_TRACING', False)) else None

    cert_path = DIR_HOME / "certs" / "NIH-FULL.pem"
    if cert_path.exists():
        context = ssl.create_default_context(cafile=cert_path)
        httpx_client = httpx.Client(verify=context)
    else:
        httpx_client = httpx.Client()
