from shiny.express import ui, module
import importlib
module_create_eval = importlib.import_module(".module_create_eval", package="app-modules")
module_run_eval = importlib.import_module(".module_run_eval", package="app-modules")

@module
def mod_ui(input, output, session):

    with ui.navset_underline(id="nav_set_eval"):
        with ui.nav_panel('Create Eval Setting'):
            module_create_eval.mod_ui("create")
        with ui.nav_panel('Run Eval'):
            module_run_eval.mod_ui("run")
            
        