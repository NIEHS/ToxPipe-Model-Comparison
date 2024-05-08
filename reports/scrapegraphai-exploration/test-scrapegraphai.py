from scrapegraphai.graphs import SmartScraperGraph

graph_config = {
    "llm": {
        "model": "ollama/mistral",
        "temperature": 0,
        "format": "json",  # Ollama needs the format to be specified explicitly
        "base_url": "http://localhost:11434",  # set Ollama URL
    },
    "embeddings": {
        "model": "ollama/nomic-embed-text",
        "base_url": "http://localhost:11434",  # set Ollama URL
    }
}

smart_scraper_graph = SmartScraperGraph(
    prompt="Grab all subpages from the provided page",
    # also accepts a string with the already downloaded HTML code
    source="https://hr.nih.gov/working-nih/competencies",
    config=graph_config
)

result = smart_scraper_graph.run()
print(result)