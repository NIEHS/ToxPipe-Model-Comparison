from shiny import reactive
from shiny.express import ui
from pathlib import Path
from utils import Config
import importlib
 
module_create_and_run_eval = importlib.import_module("app-modules.module_create_and_run_eval")
module_show_eval = importlib.import_module("app-modules.module_show_eval")
module_compare_evals_by_prompt = importlib.import_module("app-modules.module_compare_evals_by_prompt")
module_compare_evals_by_graph = importlib.import_module("app-modules.module_compare_evals_by_graph")
module_compare_evals_by_table = importlib.import_module("app-modules.module_compare_evals_by_table")

ui.include_css(Config.DIR_HOME / "www" / "css" / "bootstrap.css", method='link_files')
ui.include_css(Config.DIR_HOME / "www" / "css" / "custom.css", method='link_files')

ui.page_opts(title="Toxpipe Evaluation", fillable=True)

reload_evals_flag = reactive.value(True)

with ui.navset_pill(id="nav_main", selected='show'):
    with ui.nav_panel('Set Eval', value='set'):
        with ui.div(class_='app-container'):
            module_create_and_run_eval.mod_ui('set', reload_evals_flag)
    with ui.nav_panel('Evals', value='show'):
        with ui.div(class_='app-container d-flex flex-column gap-2'):
            module_show_eval.mod_ui('show', reload_evals_flag)
    with ui.nav_panel('Compare', value='compare'):
        with ui.div(class_='ps-4 pe-4'):
            with ui.navset_tab(id="nav_compare", selected='prompt'):
                with ui.nav_panel('Prompts', value='prompt'):
                    with ui.div(class_='app-container d-flex flex-column gap-2 mt-4'):
                        module_compare_evals_by_prompt.mod_ui('prompt')
                with ui.nav_panel('Graphs', value='graph'):
                    with ui.div(class_='app-container mt-4'):
                        module_compare_evals_by_graph.mod_ui('graph')
                with ui.nav_panel('Table', value='table'):
                    with ui.div(class_='app-container'):
                        module_compare_evals_by_table.mod_ui('table')