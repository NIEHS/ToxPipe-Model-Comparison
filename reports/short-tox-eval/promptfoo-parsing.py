import json
from collections import defaultdict

def generate_quarto_doc(json_file, output_file):
    with open(json_file, 'r') as file:
        data = json.load(file)

    with open(output_file, 'w') as file:
        # Write the header
        file.write('---\n')
        file.write('title: "Initial Prompt Testing"\n')
        file.write('author: "Trey Saddler"\n')
        file.write('date: "2024-03-29"\n')
        file.write('callout-appearance: simple\n')
        file.write('callout-icon: false\n')
        file.write('---\n\n')

        file.write('## Summary\n\n')
        
        file.write('This document contains the results of the evaluation.\n\n')

        # Group the prompts by question
        prompts_by_question = defaultdict(list)
        # Calculate pass rate by model - This can be simplified by grabbing from the data['head'] object
        pass_rate_by_model = defaultdict(lambda: {'total': 0, 'passed': 0})
        for item in data['body']:
            for output in item['outputs']:
                provider = output['provider'].split(':')[-1].replace('-', ' ').title()
                pass_rate_by_model[provider]['total'] += 1
                if output['pass']:
                    pass_rate_by_model[provider]['passed'] += 1

        # Write the pass rate data
        file.write('## Pass Rate by Model\n\n')
        file.write('| Model | Pass Rate |\n')
        file.write('|-------|----------|\n')
        for model, rate_data in pass_rate_by_model.items():
            pass_rate = rate_data['passed'] / rate_data['total'] * 100
            file.write(f'| {model} | {pass_rate:.2f}% |\n')

        file.write('\n')
        
        for item in data['body']:
            for output in item['outputs']:
                prompts_by_question[output['prompt']].append(output)

        # Write each prompt and its corresponding outputs
        for i, (question, outputs) in enumerate(prompts_by_question.items(), start=1):
            file.write(f'## Prompt {i}\n\n')
            file.write('::: {.callout-note collapse=false}\n\n')
            file.write('## User Prompt\n\n')
            file.write(f'{question}\n\n')
            file.write(':::\n\n')

            file.write('::: {.panel-tabset}\n\n')

            for output in outputs:
                provider_name = output['provider'].split(':')[-1].replace('-', ' ').title()
                # file.write(f'## {{{{< iconify logos {provider_name.lower().replace(" ", "-")}-icon >}}}} {provider_name}\n\n')
                file.write(f'## {provider_name}\n\n')

                # Remove error text from output: "Expected output to contain all of \"liver, hemangiosarcoma\"\n---\n"
                if 'Expected output' in output['text']:
                    output['text'] = output['text'].split('---')[1].strip()
                    
                file.write(f'{output["text"]}\n\n')

            file.write(':::\n\n')

if __name__ == '__main__':
    json_file = 'eval-2024-05-15T18_35_37-table.json'
    output_file = 'promptfoo-output-test.qmd'
    generate_quarto_doc(json_file, output_file)