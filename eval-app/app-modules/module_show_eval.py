from shiny import reactive, ui as core_ui
from shiny.express import ui, render, module
from shinywidgets import render_plotly
import pandas as pd
import faicons as fa
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity
from umap import UMAP
import plotly.express as px
from utils import Config
from .module_common import mod_vars
from .utils import Evaluator
from .db import getRating, saveRating

ico_check = """<span class='passed'><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-check-circle-fill" viewBox="0 0 16 16">
  <path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0m-3.97-3.03a.75.75 0 0 0-1.08.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-.01-1.05z"/>
</svg></span>"""

ico_cross = """<span class='failed'><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-x-circle-fill" viewBox="0 0 16 16">
  <path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0M5.354 4.646a.5.5 0 1 0-.708.708L7.293 8l-2.647 2.646a.5.5 0 0 0 .708.708L8 8.707l2.646 2.647a.5.5 0 0 0 .708-.708L8.707 8l2.647-2.646a.5.5 0 0 0-.708-.708L8 7.293z"/>
</svg></span>
"""

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

    def getExplanationHTML(result):

        def resultStr(res):
            return ico_check if res else ico_cross

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

    with ui.div(class_="d-flex gap-5"):
        ui.input_select("select_eval", "Evals", choices=[])
        ui.input_select("select_prompt", "Prompts", choices=[])
        @render.express
        def showVars():
            data, embeddings = loadResults()
            if data.empty: return
            for col in data.columns[Evaluator.NUM_NONVARS_COLS:]:
                mod_vars(col, var_name=col, var_values=list(data[col].values), fn_reactive=selectVar)
        ui.input_select("select_model", "Models", choices=[], multiple=True)

    with ui.div(class_='d-flex flex-column gap-2'):
        with ui.div():
            "Prompt"
        with ui.div(class_='d-flex border rounded p-3 justify-content-center'):
            with ui.div(class_='prompt'):
                @render.express
                def showPrompt():
                    prompt = input.select_prompt.get()
                    if prompt is None: return
                    try:
                        if var_selected.get():
                            prompt = prompt.format(**var_selected.get())
                    except:
                        prompt = ''
                    
                    ui.markdown(prompt)

    @render.express
    def showPassScoreThresholdInput():

        data = loadResultsByFilters().copy()
        
        if not hasAssertion(data): return

        with ui.div(class_='results-top-bar gap-5'):

            with ui.div(class_='d-flex align-items-center gap-2'):
                ui.span('Pass score threshold')
                with ui.div():
                    ui.input_numeric(id='numeric_threshold', label='', min=0, max=1, step=0.1, value=1)

            with ui.div():
                ui.input_switch(id='switch_feedback', label='Add feedback', value=False)

    @render.ui
    def showReults():
        def addReason(x):
            return core_ui.popover(
                        #core_ui.div(fa.icon_svg("square-check" if x['Result'] == 'Pass' else "square-xmark", "solid", width="30px")),
                        core_ui.div(core_ui.div(round(x['Score'], 2), class_='score')),
                        core_ui.HTML(getExplanationHTML(x['Reason'])),
                        placement="right",
                        id=f"popover_result_reason_{x.name}",
                        options={"trigger": "hover focus"}
            )
        
        def formatResponse(x):
            if 'Searched Keyphrases' in x.index:
                return core_ui.div(
                            core_ui.div(f'[The following response was taken from {("RAG resources" if x['Used Context'] else "model's training knowledge")}]',
                                        class_='fst-italic fw-bold mb-4'),
                            core_ui.div(core_ui.markdown(x['Response'])),
                            class_='app-table-content'
                        )
            
            return core_ui.div(core_ui.markdown(x['Response']), class_='app-table-content')

        data = loadResultsByFilters().copy()
        
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

            data['Response'] = data.apply(lambda x: formatResponse(x), axis=1)
    
        if 'Searched Keyphrases' in data.columns:
            data['Searched Keyphrases'] = data['Searched Keyphrases'].apply(lambda x: core_ui.div(core_ui.markdown(x), class_='app-table-content'))

        if (data['Result'] == 'No assertion').all():        
            if 'Searched Keyphrases' in data.columns:
                data = data[['Model', 'Response', 'Searched Keyphrases']]
                return prettyTableUI(data, col_widths=[1, 9, 2], style_dict=style_dict)
            
            data = data[['Model', 'Response']]
            return prettyTableUI(data, col_widths=[1, 11], style_dict=style_dict)
        
        data['Score'] = data.apply(lambda x: addReason(x) if x['Result'] != 'No assertion' else x['Result'], axis=1)   

        eval_id = data['eval_id'].unique()[0]
        eval_name = input.select_eval()

        if input.switch_feedback():

            d_feedback = loadFeedbacks()
            data['Feedback'] = data.apply(lambda x: mod_feedback(f'{x.name}', d_feedback[x['Id']] if x['Id'] in d_feedback else {'eval_id': eval_id, 
                                                                                                                                'eval_name': eval_name, 
                                                                                                                                'test_id': x['Id']}), axis=1)
        
            if 'Searched Keyphrases' in data.columns:
                data = data[['Model', 'Response', 'Searched Keyphrases', 'Score', 'Feedback']]
                return prettyTableUI(data, col_widths=[1, 7, 2, 1, 1], style_dict=style_dict)
            
            data = data[['Model', 'Response', 'Score', 'Feedback']]
            return prettyTableUI(data, col_widths=[1, 9, 1, 1], style_dict=style_dict)

        if 'Searched Keyphrases' in data.columns:
            data = data[['Model', 'Response', 'Searched Keyphrases', 'Score']]
            return prettyTableUI(data, col_widths=[1, 8, 2, 1], style_dict=style_dict)
        
        data = data[['Model', 'Response', 'Score']]
        return prettyTableUI(data, col_widths=[1, 10, 1], style_dict=style_dict)
    
    # with ui.navset_underline(id="tab", selected="res"):
    #     with ui.nav_panel(title='Responses', value="res"):

    #     with ui.nav_panel(title='Similarity of responses', value="sim"):

    #         ui.input_select("select_embedding", "Embeddings", choices=[])

    #         with ui.layout_columns(col_widths=[8, 4]):
    #             with ui.card():
    #                 with ui.layout_sidebar():
    #                     with ui.sidebar(title='Settings'):
    #                         ui.input_select('select_clustering_type', 'Select clustering algorithm', choices={'hierarchical': 'Hierarchical clustering', 'kmeans': 'KMeans'}, selected='hierarchical')
    #                         ui.input_slider('slide_n_clusters', 'Number of clusters', min=2, max=10, value=2)

    #                         ui.hr()

    #                         ui.input_select('select_projection_type', 'Select projection algorithm', choices={'umap': 'UMAP', 'tsne': 'TSNE'}, selected='umap')

    #                         with ui.panel_conditional("input.select_projection_type === 'tsne'"):
    #                             with ui.tooltip(placement='right'):
    #                                 ui.input_slider('slide_tsne_perplexity', 'TSNE perplexity', min=5, max=50, value=30)
    #                                 'The perplexity is related to the number of nearest neighbors in manifold learning algorithms.'

    #                     @render_plotly
    #                     def showSimilarityClusters():
    #                         return loadEmbeddingClusterPlot()
                    
    #             with ui.card():
    #                 @render_plotly
    #                 def showSimilarityHeatmap():
    #                     return loadEmbeddingHeatmapPlot()

    def hasAssertion(data):
        if data.empty: return False
        if len(data['Result'].unique()) == 0: return False
        return not (data['Result'].unique() == ['No assertion']).all()

    @reactive.effect
    @reactive.event(reload_evals_flag)
    def loadEvals():
        ui.update_select(id='select_eval', choices=Evaluator.loadEvals())

    @reactive.calc
    @reactive.event(input.select_eval)
    def loadResults():
        var_selected.set({})
        eval_name = input.select_eval()
        output = Evaluator.processResults(eval_name)
        embeddings = Evaluator.processEmbeddings(eval_name)
        return output, embeddings
    
    @reactive.calc
    def loadFeedbacks():
        output, _ = loadResults()
        eval_id = output['eval_id'].unique()[0]
        feedback = getRating(eval_id=eval_id)
        feedback['id'] = feedback['test_id']
        return feedback.set_index('id').to_dict(orient='index')

    @reactive.effect
    @reactive.event(input.select_eval)
    def loadModelsAndVars():
        data, embeddings = loadResults()
        if data.empty: return
        var_selected.set({})
        ui.update_select(id="select_model", choices=['Any'] + sorted(data['Model'].unique()))
        ui.update_select(id="select_prompt", choices=list(data['Prompt'].unique()))
        if not embeddings: return
        ui.update_select(id="select_embedding", choices=sorted(embeddings.keys()))

    def selectVar(var_sel):
        var_selected.set({**var_selected.get(), **var_sel})
        
    @reactive.calc
    @reactive.event(input.select_eval, input.select_prompt, var_selected, input.select_model)
    def loadResultsByFilters():
        data, _ = loadResults()
        if data.empty: return data

        # Check if vars exist for this eval set
        if data.shape[1] > Evaluator.NUM_NONVARS_COLS:

            indices = None
            if var_selected.get():
                for var_name, var_value in var_selected.get().items():
                    if var_name in data.columns:
                        if indices is None:
                            indices = set(data[data[var_name] == var_value].index)
                        else:
                            indices &= set(data[data[var_name] == var_value].index)
            if indices is None: indices = []
            data = data.loc[sorted(indices)]

        prompt, model = input.select_prompt(), input.select_model()
        if not prompt: return pd.DataFrame()

        cols = [col for col in ["Id", "eval_id", "Model", "Response", "Searched Keyphrases", "Score", "Result", "Reason", "Used Context"] if col in data.columns]

        if not model or 'Any' in model:
            res = data.query('Prompt == @prompt')[cols].reset_index(drop=True).sort_values('Model')
        else:
            res = data.query('(Prompt == @prompt) and (Model in @model)')[cols].reset_index(drop=True)

        return res

    # @reactive.calc
    # @reactive.event(input.select_eval, input.select_prompt, input.select_model, input.select_embedding)
    # def loadEmbeddings():
    #     data, embeddings = loadResults()
    #     if data.empty or not embeddings: return None, None
    #     prompt, model, embedding = input.select_prompt(), input.select_model(), input.select_embedding()
    #     if not model or 'Any' in model:
    #         ids = data.query('Prompt == @prompt')['Id'].values
    #     else:
    #         ids = data.query('(Prompt == @prompt) and (Model in @model)')['Id'].values 
        
    #     df_embed = pd.DataFrame({k: embeddings[embedding][k] for k in ids})

    #     if df_embed.shape[1] <= 1: return

    #     ui.update_slider('slide_n_clusters', min=2, max=df_embed.shape[1], value=2)
    #     ui.update_slider('slide_tsne_perplexity', min=1, max=df_embed.shape[1]-1, value=df_embed.shape[1]-1)
    #     if df_embed.shape[1] <= 3:
    #         ui.update_select('select_projection_type', choices={'tsne': 'TSNE'}, selected='tsne')

    #     cols = list(map(lambda x: x.split('|')[1], df_embed.columns))
    #     df_sim = pd.DataFrame(cosine_similarity(df_embed.T), columns=cols, index=cols)
        
    #     return df_embed, df_sim

    # @reactive.calc
    # @reactive.event(input.select_eval, input.select_prompt, input.select_model, input.select_embedding,
    #                 input.select_clustering_type, input.slide_n_clusters,
    #                 input.select_projection_type, input.slide_tsne_perplexity)
    # def loadEmbeddingClusterPlot():

    #     df_embed, df_sim = loadEmbeddings()

    #     if (df_embed is None) or (df_sim is None): return
        
    #     return plotEmbeddingClusters(df_embed = df_embed,
    #                             df_sim = df_sim,
    #                             clustering=input.select_clustering_type(),
    #                             n_clusters=input.slide_n_clusters(),
    #                             projection=input.select_projection_type(),
    #                             tsne_perplexity=input.slide_tsne_perplexity())

    # @reactive.calc
    # def loadEmbeddingHeatmapPlot():

    #     _, df_sim = loadEmbeddings()

    #     if df_sim is None: return

    #     return plotEmbeddingSimilarityHeatmap(df_sim=df_sim)

    # def plotEmbeddingClusters(df_embed:pd.DataFrame,
    #                     df_sim: pd.DataFrame,
    #                     clustering: str,
    #                     n_clusters: int,
    #                     projection: str,
    #                     tsne_perplexity: int,
    # ):

    #     scaler = StandardScaler()
    #     X_t = scaler.fit_transform(df_embed.values.T)
        
    #     if clustering == 'hierarchical':
    #         X_c = AgglomerativeClustering(n_clusters=n_clusters).fit(df_sim)
    #     else:
    #         X_t = scaler.fit_transform(df_embed.values.T)
    #         X_c = KMeans(n_clusters=n_clusters, max_iter=3000, random_state=Config.RANDOM_STATE, verbose=True).fit(X_t)

    #     if projection == 'umap':
    #         X_p = UMAP(n_neighbors=2, random_state=Config.RANDOM_STATE).fit_transform(X_t)
    #     else:
    #         X_p = TSNE(n_components=2, perplexity=tsne_perplexity, max_iter=1000, random_state=Config.RANDOM_STATE).fit_transform(X_t)

    #     df_plot = pd.DataFrame(X_p, columns=['X', 'Y'])
    #     df_plot['Cluster'] = list(map(str, X_c.labels_))
    #     df_plot['Model'] = list(map(lambda x: x.split('|')[1], df_embed.columns))

    #     fig = px.scatter(df_plot, 
    #                     x='X', 
    #                     y='Y', 
    #                     color='Cluster',
    #                     symbol='Model',
    #                     opacity=0.5,
    #                     hover_name='Model'
    #     )
    #     fig.update_traces(marker={'size': 15})

    #     fig.update_layout(
    #         title="Clusters",
    #         **Config.CONFIG_PLOT
    #     )

    #     return fig

    # def plotEmbeddingSimilarityHeatmap(df_sim: pd.DataFrame):

    #     df_sim = df_sim.round(2)
        
    #     fig = px.imshow(df_sim, text_auto=True)

    #     fig.update_layout(
    #         title="Similarity",
    #         **Config.CONFIG_PLOT
    #     )

    #     return fig