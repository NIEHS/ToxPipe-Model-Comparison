import json
import csv
from collections import defaultdict
import argparse

def load_model_info(csv_file):
    model_info = {}
    with open(csv_file, 'r', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        for row in reader:
            model_info[row['model']] = {
                'pretty_name': row['model_pretty'],
                'iconify': row['iconify']
            }
    return model_info

def generate_quarto_doc(json_file, output_file, model_csv):
    model_info = load_model_info(model_csv)

    with open(json_file, 'r') as file:
        data = json.load(file)

    with open(output_file, 'w') as file:
        # Write the header
        file.write('---\n')
        file.write('title: "ECSA GARA Challenge"\n')
        file.write(f'date: "{data["evalId"].split("T")[0]}"\n')
        file.write('callout-appearance: simple\n')
        file.write('callout-icon: false\n')
        file.write('---\n\n')

        file.write('## Summary\n\n')
        
        file.write('This document contains the results of the evaluation.\n\n')

        # Group the prompts by question
        prompts_by_question = defaultdict(list)
        # Calculate pass rate by model
        pass_rate_by_model = defaultdict(lambda: {'total': 0, 'passed': 0})
        for result in data['results']['results']:
            prompt = result['prompt']['raw']
            prompts_by_question[prompt].append(result)
            provider = result['provider']['id']
            pass_rate_by_model[provider]['total'] += 1
            if 'gradingResult' in result and result['gradingResult'].get('pass'):
                pass_rate_by_model[provider]['passed'] += 1

        # Write each prompt and its corresponding outputs
        for i, (question, outputs) in enumerate(prompts_by_question.items(), start=1):
            file.write(f'## Prompt {i}\n\n')
            file.write('::: {.callout-note collapse=false}\n\n')
            file.write('## User Prompt\n\n')
            file.write(f'{question}\n\n')
            file.write(':::\n\n')

            file.write('::: {.panel-tabset}\n\n')

            for output in outputs:
                provider_id = output['provider']['id']
                # Extract the model name without the prefix
                model_name = provider_id.split(':')[-1]
                
                if model_name in model_info:
                    pretty_name = model_info[model_name]['pretty_name']
                    icon = model_info[model_name]['iconify']
                else:
                    pretty_name = model_name.replace('-', ' ').title()
                    icon = ''

                if icon:
                    file.write(f'## {{{{< iconify {icon} >}}}} {pretty_name}\n\n')
                else:
                    file.write(f'## {pretty_name}\n\n')

                if 'response' in output and 'output' in output['response']:
                    file.write(f'{output["response"]["output"]}\n\n')
                else:
                    file.write("No response available.\n\n")

            file.write(':::\n\n')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate Quarto document from JSON and CSV files')
    parser.add_argument('json_file', help='Input JSON file')
    parser.add_argument('output_file', help='Output QMD file')
    parser.add_argument('model_csv', help='CSV file containing model information')
    args = parser.parse_args()

    generate_quarto_doc(args.json_file, args.output_file, args.model_csv)
