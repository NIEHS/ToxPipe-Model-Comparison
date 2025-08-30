from shiny import reactive
from shiny.express import ui, module
from . import module_create_eval, module_run_eval

@module
def mod_ui(input, output, session, reload_evals_flag):
    
    reload_unrun_evals_flag = reactive.value(True)

    with ui.navset_underline(id="nav_set_eval"):
        with ui.nav_panel('Create Eval Setting'):
            module_create_eval.mod_ui("create", reload_unrun_evals_flag)
        with ui.nav_panel('Run Eval'):
            module_run_eval.mod_ui("run", reload_unrun_evals_flag, reload_evals_flag)