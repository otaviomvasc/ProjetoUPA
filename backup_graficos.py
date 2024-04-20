#arquivo para guardar códigos de gráficos não utilizados para consultar futuras


# filas por prioridade - formato 1: Cada prioridade de cenário junto no mesmo gráfico
# for df in [
# df_filas_por_prioridade.loc[df_filas_por_prioridade.prioridade == 1],
# df_filas_por_prioridade.loc[df_filas_por_prioridade.prioridade == 2],
# df_filas_por_prioridade.loc[df_filas_por_prioridade.prioridade == 3],
# df_filas_por_prioridade.loc[df_filas_por_prioridade.prioridade == 4],
# df_filas_por_prioridade.loc[df_filas_por_prioridade.prioridade == 5]
# ]:
#     fig = px.bar(df, x='Cenário',
#                  y='media_minutos',
#                  title=f'Média de tempo em fila de Pacientes Prioridade {list(df.prioridade)[0]}')
#     fig.layout.template = CHART_THEME
#     fig.update_yaxes(title=f'Média do Tempo em Fila (Min)', showgrid=False)
#     fig.update_xaxes(title='Cenário', showgrid=False)
#     fig.update_yaxes(showticklabels=False)
#     fig.update_layout(title_x=0.5)
#     for index, row in df.iterrows():
#         fig.add_annotation(
#             x=row['Cenário'],
#             y=row['media_minutos'],
#             xref="x",
#             yref="y",
#             text=f"<b> {row['media_minutos']} </b> ",
#             font=dict(
#                 family="Arial",
#                 size=12,
#             )
#         )
#     fig.show()


# utilização geral por recurso
# for rec in recursos:
#     df_aux = df_utilizacao_por_recurso.loc[df_utilizacao_por_recurso.recurso == rec]
#     fig = px.bar(df_aux, x='Cenário',
#                  y='utilizacao',
#                  title=f'Média de Utilização do Recurso {rec}')
#     fig.layout.template = CHART_THEME
#     fig.update_yaxes(title=f'Média de Utilização (%)', showgrid=False)
#     fig.update_xaxes(title='Cenário', showgrid=False)
#     fig.update_yaxes(showticklabels=False)
#     fig.update_layout(title_x=0.5)
#     for index, row in df_aux.iterrows():
#         fig.add_annotation(
#             x=row['Cenário'],
#             y=row['utilizacao'],
#             xref="x",
#             yref="y",
#             text=f"<b> {row['utilizacao']} </b> ",
#             font=dict(
#                 family="Arial",
#                 size=12,
#             )
#         )
#     fig.show()


#Utilização por subplots!
# rows2 = 2
# cols = 4
# fig = make_subplots(rows=rows2, cols=cols, subplot_titles=["% de Utilização de " + rec for rec in recursos], )
# fig.layout.template = CHART_THEME
# fig.update_traces(textposition='inside')
# fig.update_layout(height=700)  # , width=600)
# n_row = 1
# n_col = 1
# for rec in recursos:
#     df_aux = df_utilizacao_por_recurso.loc[df_utilizacao_por_recurso.recurso == rec]
#     fig.add_trace(go.Bar(x=df_aux.Cenário, y=df_aux.utilizacao, text=df_aux.utilizacao,
#                          textposition='inside'), row=n_row, col=n_col)
#     if n_col == cols:
#         n_col = 1
#         n_row += 1
#     else:
#         n_col += 1
# fig.show()


# total de atendimentos, tempo médio de fila geral - Referência: https://medium.com/@guilhermedatt/como-fazer-subplots-com-plotly-em-python-704b831405f2
# fig = make_subplots(rows=1, cols=3, subplot_titles=(
# "Pacientes Atendidos", "Média de Filas", "Utilização Média"))  # dois gráficos lado a lado!!
# fig.layout.template = CHART_THEME
# fig.update_traces(textposition='outside')
# fig.update_layout(height=480)
# fig.add_trace(
#     go.Bar(x=df_total_pacientes.Cenario, y=df_total_pacientes.Atendimentos, text=df_total_pacientes.Atendimentos,
#            textposition='outside'), row=1, col=1)
# fig.add_trace(
#     go.Bar(x=df_fila_media.Cenario, y=df_fila_media.Tempo_Médio_de_Fila, text=df_fila_media.Tempo_Médio_de_Fila,
#            textposition='outside'), row=1, col=2)
# fig.add_trace(
#     go.Bar(x=df_utilizacao_media.Cenario, y=df_utilizacao_media.Utilização, text=df_utilizacao_media.Utilização,
#            textposition='outside'), row=1, col=3)
#
# fig.update_yaxes(title_text='Total de Pacientes', row=1, col=1, showgrid=False, showticklabels=False)
# fig.update_yaxes(title_text='Tempo Médio de Fila (Min)', row=1, col=2, showgrid=False, showticklabels=False)
# fig.update_yaxes(title_text='Utilização (%)', row=1, col=3, showgrid=False, showticklabels=False)
#
# fig.update_xaxes(title_text='Cenário', row=1, col=1)
# fig.update_xaxes(title_text='Cenário', row=1, col=2)
# fig.update_xaxes(title_text='Cenário', row=1, col=3)
#
# for annotation in fig['layout']['annotations']:
#     annotation['y'] = 1.1
#
# fig.show()


# Fila por prioridade com subplots. Se modelo for aprovado, melhorar exibição.
# rows_total = 3
# cols = 2
# fig = make_subplots(rows=rows_total, cols=cols, row_heights=[.8, .8, .8], column_widths=[.5, .5],
#                     subplot_titles=["Pacientes com Prioridade " + str(pr) for pr in
#                                     pd.unique(df_filas_por_prioridade.prioridade)])
# fig.layout.template = CHART_THEME
# fig.update_traces(textposition='inside')
# fig.update_layout(height=700)  # , width=600)
# n_row = 1
# n_col = 1
# fig.update_yaxes(showgrid=False, showticklabels=False)
# fig.update_layout(title_text='Tempo Médio de Fila por Prioridade de Paciente (Min)', title_x=0.5, height=700)
# for pr in pd.unique(df_filas_por_prioridade.prioridade):
#     df_aux = df_filas_por_prioridade.loc[df_filas_por_prioridade.prioridade == pr]
#     fig.add_trace(go.Bar(x=df_aux.Cenário, y=df_aux.media_minutos, text=df_aux.media_minutos,
#                          textposition='inside'), row=n_row, col=n_col)
#     # fig.update_yaxes(title_text='Tempo Médio de Fila (Min)', row=n_row, col=n_col, showgrid=False, showticklabels=False)
#     if n_col == cols:
#         n_col = 1
#         n_row += 1
#     else:
#         n_col += 1
#fig.show()
