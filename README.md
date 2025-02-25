# ToxPipe LLM Model Testing

This repo documents various tests performed to evaluate the quality of different LLMs for use in the ToxPipe project.


|	Model |	Toxicity type prompts (Human) (57) | ABT Q/A prompts (474) | Toxicity type prompts (Rat) (2) |
|---------|------------------------------------|-----------------------|---------------------------------|
| Base model |	Claude 3.5 Sonnet |	90.93 |	54.39 |	50 |
|	| GPT-4o |	92.19 |	36.84 |	50 |
|	| Gemini 1.5 Pro | 94.51 |	40.35 |	50 |
|	| Llama 3.1 405B | 87.13 |	33.33 |	50 |
|	| Mistral Large 2 |	90.08 |	43.86 |	50 |
| RAG | Claude 3.5 Sonnet | | | |				
|     | GPT-4o | | | |				
|     | Gemini 1.5 Pro | | | |				
|     | Llama 3.1 405B | | | |		
|     | Mistral Large 2 | | | |				
| Agentic | Claude 3.5 Sonnet | | | |	
|     | GPT-4o | | | |				
|     | Gemini 1.5 Pro | | | |		
|     | Mistral Large 2 | | | |		