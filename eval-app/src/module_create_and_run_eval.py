from shiny import reactive
from shiny.express import ui, module
from . import module_create_eval, module_run_eval, module_set_up_evals_comparison

@module
def mod_ui(input, output, session, reload_evals_flag):
    
    reload_unrun_evals_flag = reactive.value(True)

    with ui.navset_underline(id="nav_set_eval"):
        with ui.nav_panel('Create Eval'):
            module_create_eval.mod_ui("create", reload_unrun_evals_flag)
        with ui.nav_panel('Run Eval'):
            module_run_eval.mod_ui("run", reload_unrun_evals_flag, reload_evals_flag)
        with ui.nav_panel('Set up Eval set for comparison'):
            module_set_up_evals_comparison.mod_ui("set_up_compare", reload_evals_flag)