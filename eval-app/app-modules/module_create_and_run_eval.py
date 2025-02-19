from shiny import reactive
from shiny.express import ui, module
from . import module_create_eval, module_run_eval
from utils import Config
import importlib
utils = importlib.import_module(".utils", package="app-modules")

@module
def mod_ui(input, output, session):

    with ui.navset_underline(id="nav_set_eval"):
        with ui.nav_panel('Create Eval Setting'):
            module_create_eval.mod_ui("create")
        with ui.nav_panel('Run Eval'):
            module_run_eval.mod_ui("run")