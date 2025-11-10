from shiny import reactive, ui as core_ui
from shiny.express import ui, render, module, expressify
import pandas as pd
import faicons as fa
from .common import mod_vars, hasAssertion
from .utils_eval import Evaluator
from .db import getRating, saveRating
import re

# -----------------------------------------------------------------------
def prettyTableUI(df, col_widths, style_dict={}):
    def format(text, col_name):
        if pd.isna(text): text = ''
        if col_name == 'Link': return ui.HTML(f"<a class='app-link' href='{text}'>{text}</a>")
        return text
    
    return core_ui.div(
        core_ui.div(
            *[core_ui.div(
                ui.HTML(f"<strong>{col}</strong>"),
                class_=f'col-{col_widths[j]} p-2 d-flex align-items-center app-table-col' + (' ' + style_dict[col] if col in style_dict else '')
            ) for j, col in enumerate(df.columns)],
            class_="row app-table-header"
        ),
        *[core_ui.div(         
            *[core_ui.div(
                format(row[col], col),
                class_=f'col-{col_widths[j]} p-2 d-flex align-items-center app-table-col' + (' ' + style_dict[col] if col in style_dict else '')
            ) for j, col in enumerate(df.columns)],
            class_=f'row' + (' ' + style_dict[f'row_{i}'] if f'row_{i}' in style_dict else '')
        ) for i, row in df.iterrows()],
        class_="app-table"
    )

@module
def mod_feedback(input, output, session, feedback):

    def getFeedbackIcon():
        if 'passed' not in feedback:
            cls = 'app-ico'
        elif feedback['passed'] == True:
            cls = 'app-ico-passed'
        else:
            cls = 'app-ico-failed'

        ico_type = 'regular' if 'passed' not in feedback else 'solid'
        return ui.span(fa.icon_svg("comment", ico_type, width="30px"), class_=cls)

    @reactive.effect
    @reactive.event(input.btn_submit, ignore_init=True)
    def submit():

        feedback['passed'] = (input.rad_pass() == 'Yes')
        feedback['comments'] = input.txt_reason()
    
        try:
            saveRating(feedback)
            ui.update_action_link(id='btn_feedback', label='', icon=getFeedbackIcon())
            ui.notification_show(core_ui.div("Rating saved", class_="app-notification"), duration=3, type="message")
        except Exception as err:
            print(str(err))
            ui.notification_show(core_ui.div("Rating was not saved", class_="app-notification"), duration=3, type="error")

        ui.update_popover("popover_feedback", show=False)

    @reactive.effect
    @reactive.event(input.btn_close)
    def close():
        ui.update_popover("popover_feedback", show=False)

    return core_ui.popover(
                core_ui.input_action_link(id="btn_feedback", label='', icon=getFeedbackIcon()),
                ui.div(
                    ui.div(
                        ui.input_radio_buttons(id='rad_pass', 
                                               label='Passed', choices=['Yes', 'No'], 
                                               selected= 'Yes' if 'passed' not in feedback else 'Yes' if feedback['passed'] else 'No', 
                                               inline=True),
                        ui.input_action_link(id='btn_close', label='', icon = fa.icon_svg("circle-xmark", "regular", width="25px"), class_='app-ico'),
                        class_='d-flex justify-content-between'
                    ),
                    ui.input_text_area(id='txt_reason', label='Reason', value=feedback['comments'] if 'comments' in feedback else ''),
                    ui.div(
                        ui.input_action_button(id='btn_submit', label='Submit'), 
                        class_='d-flex justify-content-center'
                    )
                ),
                placement="top",
                id=f"popover_feedback",

    )

@module
def mod_ui(input, output, session, reload_evals_flag):

    var_selected = reactive.value({})

    with ui.div(class_="d-flex gap-5"):
        ui.input_select("select_eval", "Evals", choices=[])
        ui.input_select("select_prompt", "Prompts", choices=[])
        @render.express
        def showVars():
            d_vars = loadVars()
            for k, v in d_vars.items():
                mod_vars(k, var_name=k, var_values=v, fn_reactive=selectVar)
        ui.input_select("select_model", "Models", choices=[], multiple=True)

    with ui.div(class_='d-flex flex-column gap-2'):
        with ui.div():
            "Prompt"
        with ui.div(class_='d-flex border rounded p-3 justify-content-center'):
            with ui.div(class_='prompt'):
                @render.express
                def showPrompt():
                    ui.markdown(getPrompt())

    @render.express
    def showPassScoreThresholdInput():

        data = loadResultsTask.result().copy()
        
        if not hasAssertion(data): return

        with ui.div(class_='results-top-bar gap-5'):

            with ui.div(class_='d-flex align-items-center gap-2'):
                ui.span('Pass score threshold')
                with ui.div():
                    ui.input_numeric(id='numeric_threshold', label='', min=0, max=1, step=0.1, value=1)

            with ui.div():
                ui.input_switch(id='switch_feedback', label='Add feedback', value=False)

    ui.busy_indicators.use(spinners=True, pulse=False, fade=False)
    
    @render.express
    def showReults():

        def getExplanationHTML(result):

            def resultStr(res):
                return f"<span class='passed'>{fa.icon_svg('circle-check')}</span>" if res else f"<span class='failed'>{fa.icon_svg('circle-xmark')}</span>"

            def getComponentExplanation(results):
                text = ''
                has_component = False
                for result in results:
                    if 'components' in result:
                        text += f"<strong>{result['reason']} {resultStr(result['pass'])}</strong>"
                        text += f"<ul>{getComponentExplanation(result['components'])}</ul>"
                        has_component = True

                if not has_component:
                    for result in results:
                        text += f"<li>{result['reason']} {resultStr(result['pass'])}</li>"
                        
                return text

            if not isinstance(result, list): return "No reason found"
            return getComponentExplanation(result)

        def addReason(x):

            @expressify
            def format():
                with ui.popover(placement="right", options={"trigger": "hover focus"}):
                    #with ui.div():
                    #   fa.icon_svg("square-check" if x['Result'] == 'Pass' else "square-xmark", "solid", width="30px"))
                    with ui.div(class_='score'):
                        with ui.div():
                            round(x['Score'], 2)
                    with ui.div(class_='p-3'):
                        ui.HTML(getExplanationHTML(x['Reason']))
                        
            with ui.hold() as content:
                format()

            return content
        
        def formatResponse(response):

            @expressify
            def format():
                with ui.div(class_='app-table-content'):
                    ui.markdown(response)

            with ui.hold() as content:
                format()

            return content

        match loadResultsTask.status():
            case 'initial':
                ui.div(ui.strong("Responses will show up here"))
                return
            case 'running':
                ui.div(ui.strong("Extracting responses..."))
                return

        data = loadResultsTask.result().copy()
        if data.empty: return

        style_dict = {'Model': 'justify-content-center', 'Score': 'justify-content-center', 'Feedback': 'justify-content-center'}

        if hasAssertion(data):
            threshold_pass = input.numeric_threshold()
            data['Result'] = data.apply(lambda x: 'Pass' if x['Score'] >= threshold_pass else 'Fail' if x['Result'] != 'No assertion' else x['Result'], axis=1)   

        if not data.empty:
            for i, row in data.iterrows():
                match row['Result']:
                    case 'Pass':
                        style_dict[f'row_{i}'] = 'app-table-row-pass'
                    case 'Fail':
                        style_dict[f'row_{i}'] = 'app-table-row-fail'
                    case _:
                        style_dict[f'row_{i}'] = 'app-table-row-no-assertion'

        data['Response'] = data['Response'].apply(lambda x: formatResponse(x))

        if (data['Result'] == 'No assertion').all():
            
            data = data[['Model', 'Response']]
            prettyTableUI(data, col_widths=[1, 11], style_dict=style_dict)
            return
        
        data['Score'] = data.apply(lambda x: addReason(x) if x['Result'] != 'No assertion' else x['Result'], axis=1)   

        eval_id = data['eval_id'].unique()[0]
        eval_name = input.select_eval()

        if input.switch_feedback():

            d_feedback = loadFeedbacks()
            data['Feedback'] = data.apply(lambda x: mod_feedback(f'{x.name}', d_feedback[x['Id']] if x['Id'] in d_feedback else {'eval_id': eval_id, 
                                                                                                                                'eval_name': eval_name, 
                                                                                                                                'test_id': x['Id']}), axis=1)
            data = data[['Model', 'Response', 'Score', 'Feedback']]
            prettyTableUI(data, col_widths=[1, 9, 1, 1], style_dict=style_dict)
            return

        data = data[['Model', 'Response', 'Score']]
        prettyTableUI(data, col_widths=[1, 10, 1], style_dict=style_dict)
    
    @reactive.calc
    @reactive.event(input.select_eval)
    def loadFeedbacks():
        eval_name = input.select_eval()
        eval_id = Evaluator.getEvalInfo(eval_name)['event_id']
        feedback = getRating(eval_id=eval_id)
        if feedback.empty: return feedback
        feedback['id'] = feedback['test_id']
        return feedback.set_index('id').to_dict(orient='index')

    @reactive.effect
    @reactive.event(reload_evals_flag)
    def loadEvals():
        ui.update_select(id='select_eval', choices=Evaluator.loadEvals())

    @reactive.effect
    @reactive.event(input.select_eval)
    def loadPromptsAndModels():
        eval_name = input.select_eval()
        var_selected.set({}) 
        prompts = Evaluator.getPrompts(eval_name)
        models = Evaluator.getProviders(eval_name)
        ui.update_select(id="select_prompt", choices=prompts)
        ui.update_select(id="select_model", choices=['Any'] + models)

    @reactive.calc
    @reactive.event(input.select_eval, input.select_prompt)
    def loadVars():
        eval_name = input.select_eval()
        prompt = input.select_prompt()
        if not (eval_name and prompt): return {}
        var_selected.set({}) 
        d_vars = Evaluator.getVars(eval_name)
        data = Evaluator.filterVarsByPrompt(d_vars, prompt)

        return data

    def selectVar(var_sel):
        var_selected.set({**var_selected.get(), **var_sel})

    @reactive.calc
    @reactive.event(input.select_prompt, var_selected)
    def getPrompt():

        prompt = input.select_prompt()
        
        if not prompt: return ''
        
        vars_prompt = set(re.findall(r"{(\w+)}", prompt))
        var_sel = var_selected.get()

        if len(vars_prompt) != len(var_sel): return ''

        try:
            prompt = prompt.format(**var_sel)
        except:
            prompt = ''

        return prompt

    @reactive.extended_task
    async def loadResultsTask(eval_name, prompt, model, var_sel):

        async def run():

            data = Evaluator.processResults(eval_name=eval_name, 
                                            prompt=prompt, 
                                            provider=None if model == 'Any' else model,
                                            d_vars=var_sel)
            if data.empty: return data

            cols = ["Id", "eval_id", "Model", "Response", "Score", "Result", "Reason"]

            if not model or 'Any' in model:
                res = data[cols].reset_index(drop=True).sort_values('Model')
            else:
                res = data[cols].reset_index(drop=True)

            return res
        
        return await run()

    @reactive.effect
    @reactive.event(input.select_eval, input.select_prompt, var_selected, input.select_model)
    def loadResultsByFilters():

        eval_name = input.select_eval()
        prompt = input.select_prompt()
        model = input.select_model()
        d_vars = loadVars()
        var_sel = var_selected.get()

        if not (eval_name and prompt and (not d_vars or var_sel)): return pd.DataFrame()

        loadResultsTask(eval_name, prompt, model, var_sel)