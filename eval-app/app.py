from shiny.express import ui
from pathlib import Path
import importlib
 
module_create_and_run_eval = importlib.import_module("app-modules.module_create_and_run_eval")
module_show_eval = importlib.import_module("app-modules.module_show_eval")
module_graph_eval = importlib.import_module("app-modules.module_graph_eval")

ui.include_css(Path(__file__).parent / "css" / "bootstrap.css", method='link_files')
ui.include_css(Path(__file__).parent / "css" / "custom.css", method='link_files')

ui.page_opts(title="Toxpipe Evaluation", fillable=True)

with ui.navset_pill(id="nav_id", selected='show'):
    with ui.nav_panel('Set Eval', value='set'):
        with ui.div(class_='app-container'):
            module_create_and_run_eval.mod_ui('set')
    with ui.nav_panel('Evals', value='show'):
        with ui.div(class_='app-container d-flex flex-column gap-2'):
            module_show_eval.mod_ui('show')
    with ui.nav_panel('Eval Graphs', value='graph'):
        with ui.div(class_='app-container'):
            module_graph_eval.mod_ui('graph')