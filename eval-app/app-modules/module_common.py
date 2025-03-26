from shiny import reactive
from shiny.express import ui, module

@module
def mod_vars(input, output, session, var_name, var_values, fn_reactive):

    @reactive.effect
    @reactive.event(input.select_var)
    def selectVar():
        fn_reactive({var_name: input.select_var()})

    ui.input_select('select_var', var_name[0].upper() + var_name[1:].replace('_', ' '), choices=var_values)