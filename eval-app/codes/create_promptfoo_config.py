import yaml
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))
from codes.utils import Config

class MyDumper(yaml.Dumper):

    def increase_indent(self, flow=False, indentless=False):
        return super(MyDumper, self).increase_indent(flow, False)


def loadYML(file_path):
    data = None
    with open(file_path) as stream:
        try:
            data = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
    return data

def createTest(test_name):

    dir_test = Config.DIR_TEST / test_name
    dir_setup = dir_test / 'setup'

    path_config = dir_setup / 'config.yaml'
    assert path_config.exists(), f"Config file not found in the provided directory path: ({path_config})"

    config = loadYML(path_config)
    description = config['description']
    prompts = loadYML(dir_setup / config['prompts'])
    providers = loadYML(dir_setup / config['providers'])
    tests = loadYML(dir_setup / config['tests'])

    defaulttest = ''
    if 'defaultTest' in config: 
        file_test_options = dir_setup / config['defaultTest']
        defaulttest = loadYML(file_test_options)

    assert isinstance(prompts['system'], str), "System prompt was not provided as a string"
    assert isinstance(prompts['user'], list), "User prompts were not provided as a list"

    with open(dir_test / '.env', 'w') as f:
        f.write(f"OPENAI_BASE_URL=\'{Config.env_config['OPENAI_BASE_URL']}\'\n" +
                f"OPENAI_API_KEY=\'{Config.env_config['OPENAI_API_KEY']}\'\n" +
                f"LANGFUSE_SECRET_KEY=\'{Config.env_config['LANGFUSE_SECRET_KEY']}\'\n" +
                f"LANGFUSE_PUBLIC_KEY=\'{Config.env_config['LANGFUSE_PUBLIC_KEY']}\'\n" +
                f"LANGFUSE_HOST=\'{Config.env_config['LANGFUSE_HOST']}\'\n" +
                f"TOXPIPE_API_HOST=\'{Config.env_config['TOXPIPE_API_HOST']}\'\n" + 
                f"REPLICATE_SYSTEM_PROMPT=\'{prompts['system']}\'\n")

    with open(dir_test / f'promptfooconfig.yaml', 'w') as outfile:
        data = {
            'description': description,
            'providers': providers,
            'prompts': prompts['user'],
            'tests': tests,
            'defaultTest': defaulttest
        }
        yaml.dump(data, outfile, Dumper=MyDumper, default_flow_style=False)

if __name__ == '__main__':
    createTest(sys.argv[1])