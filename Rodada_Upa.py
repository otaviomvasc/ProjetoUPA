import copy

import pandas as pd
import simpy
import random
import numpy as np
import scipy
import matplotlib
import matplotlib.pyplot as plt
from random import expovariate, seed, normalvariate
from scipy import stats
from plotly.subplots import make_subplots
import plotly.graph_objects as go

from Modelos import *

"""
Cálculos preliminares com dados do slide:

total de pacientes: 4951 + 1801 = 6752

1 - tipo de atendimento (clinica e pediatria
    pediatria = 1801 / 6752 = 0.26
    clinica =  4951 / 6752 = 0.74
    
2 - Prioridade de atendimentos:
Total = 132 + 1066 + 6178 + 8 + 246 = 7630 
    Laranja = 1 - 132 / 7630 = 0.017
    Amarelo = 2 - 1066 / 7630 = 0.139
    Verde = 3 - - 6178 / 7630 = 0.80129
    Azul = 4 -    8 / 7630 = 0.001
    Branco = 5 - 246 / 7630 = 0.032
    

3 - Taxa de Chegada:
    media_de_chegadas = (4900 + 1604 + 4951 + 1801 + 5104 + 1782) / 3 = 6714.0
    segundos_no_mes = 30 * 24 * 60 * 60 = 2592000
    media_chegadas / segundo = 6714.0 / 2592000 = 0.026
 
"""



if __name__ == "__main__":

    #Dados e parâmetros default em todos os cenários:
    ordem_processo = {
        "Ficha": "Triagem",
        "Triagem": ["decide_atendimento"],
        "Clínico": ["decisao_apos_clinico"],
        "Pediatra": ["decisao_apos_pediatra"],
        "Aplicar Medicação": "Tomar Medicação",
        "Tomar Medicação": ["decisao_apos_medicacao"],
        "Exame de Urina": ["decisao_apos_urina"],
        "Exame de Sangue": ["decisao_apos_exame_sangue"],
        "Análise de Urina": "medico",
        "Raio-x": ["decisao_apos_raio_x"],
        "Eletro": ["decisao_apos_eletro"]
    }
    tempo = 24 * 60 * 60 * 30
    necessidade_recursos = {"Ficha": ["Secretária"],
                            "Triagem": ["Enfermeira de Triagem"],
                            "Clínico": ["Clínico"],
                            "Pediatra": ["Pediatra"],
                            "Raio-x" : ["Raio-x"],
                            "Exame de Urina" : [],
                            "Exame de Sangue": ["Técnica de Enfermagem"],
                            "Análise de Sangue Externo": [],
                            "Análise de Sangue Interno": [],
                            "Análise de Urina": [],
                            "Aplicar Medicação": ["Técnica de Enfermagem", "Espaço para tomar Medicação"],
                            "Tomar Medicação" : [],
                            "Eletro": ["Eletro"]
                            }

    liberacao_recursos = {"Ficha": ["Secretária"],
                            "Triagem": ["Enfermeira de Triagem"],
                            "Clínico": ["Clínico"],
                            "Pediatra": ["Pediatra"],
                            "Raio-x" : ["Raio-x"],
                            "Exame de Urina" : [],
                            "Exame de Sangue": ["Técnica de Enfermagem"],
                            "Análise de Sangue Externo": [],
                            "Análise de Sangue Interno": [],
                            "Análise de Urina": [],
                            "Aplicar Medicação": ["Técnica de Enfermagem"],
                            "Tomar Medicação" : ["Espaço para tomar Medicação"], #TODO: pensar em como fazer para liberar apenas 1 requests para liberar apenas a medicação!
                            "Eletro": ["Eletro"]
                            }

    atribuicoes_processo = {"Triagem": "prioridade",
                            "Exame de Sangue": "tempo_resultado_exame_sangue",
                            "Exame de Urina": "tempo_resultado_exame_urina"
                        }

    prioridades = {
        "Ficha": None,
        "Triagem": None,
        "Clínico": "prioridade",
        "Pediatra": "prioridade"
    }
    def calcula_distribuicoes_prob():
        def calcula(dados):
            inicio = 0
            list_aux = []
            for dado in dados:
                list_aux.append([inicio, inicio + dado[1], dado[0]])
                inicio = inicio + dado[1]
            return list_aux

            # 1 - clinico e 2 -  pediatra

        classificacao_clinico_pediatra = [["Clínico", 0.74],
                                          ["Pediatra", 0.26]]
        # 5 - menos grave e 1 - mais grave
        classificacao_prioridade = [[5, 0.032],
                                    [4, 0.001],
                                    [3, 0.70129],
                                    [2, 0.150],
                                    [1, 0.117]]

        #saida do sistema após o clinico
        decisao_apos_clinico = [["Saída", 0.4],
                                      ["Aplicar Medicação", 0.2],
                                      ["Raio-x", 0.1],
                                      ["Eletro", 0.1],
                                      ["Exame de Urina", 0.1],
                                      ["Exame de Sangue", 0.1]]

        decisao_apos_pediatra = [["Saída", 0.4],
                                      ["Aplicar Medicação", 0.2],
                                      ["Raio-x", 0.1],
                                      ["Eletro", 0.1],
                                      ["Exame de Urina", 0.1],
                                      ["Exame de Sangue", 0.1]]

        decisao_apos_medicacao = [["Saída", 0.4],
                                  ["medico", 0.2], #TODO: E O PACIENTE QUE VEM DO PEDIATRA E TOMA MEDICAÇÃO? COMO ELE VAI VOLTAR PARA LÁ?
                                  ["Raio-x", 0.1],
                                  ["Eletro", 0.1],
                                  ["Exame de Urina", 0.1],
                                  ["Exame de Sangue", 0.1]
                                  ]

        decisao_apos_urina = [["medico", 0.7],
                              ["Raio-x", 0.1],
                              ["Eletro", 0.1],
                              ["Exame de Sangue", 0.1]
                              ]

        decisao_apos_exame_sangue = [["medico", 0.7],
                              ["Raio-x", 0.1],
                              ["Eletro", 0.1],
                              ["Exame de Urina", 0.1]
                              ]

        decisao_apos_raio_x = [["medico", 0.7],
                             ["Exame de Sangue", 0.1],
                             ["Eletro", 0.1],
                             ["Exame de Urina", 0.1]]

        decisao_apos_eletro = [["medico", 0.7],
                             ["Exame de Sangue", 0.1],
                             ["Raio-x", 0.1],
                             ["Exame de Urina", 0.1]]

        #Decisao para tempo de espera do resultado do exame de sangue!!!!
        analise_de_sangue = [[0.5 * 60 * 60, 0.5],
                             [0.25 * 60 * 60, 0.5]]

        analise_urina = [[0.25 * 60 * 60, 1]]


        dict_atr = {"decide_atendimento": calcula(classificacao_clinico_pediatra),
                    "prioridade": calcula(classificacao_prioridade),
                    "decisao_apos_clinico": calcula(decisao_apos_clinico),
                    "decisao_apos_pediatra": calcula(decisao_apos_pediatra),
                    "decisao_apos_raio_x":calcula(decisao_apos_raio_x),
                    "decisao_apos_eletro": calcula(decisao_apos_eletro),
                    "decisao_apos_urina": calcula(decisao_apos_urina),
                    "decisao_apos_exame_sangue": calcula(decisao_apos_exame_sangue),
                    "decisao_apos_medicacao": calcula(decisao_apos_medicacao),
                    "tempo_resultado_exame_sangue": calcula(analise_de_sangue),
                    "tempo_resultado_exame_urina": calcula(analise_urina),
                    }

        return dict_atr

    distribuicoes_probabilidade = calcula_distribuicoes_prob()

    warmup = 50000
    replicacoes = 5


    #Unicos pontos que iremos alterar a principio na geração de cenários será os recursos e tempos de processo!

    def distribuicoes(processo, slot="None"):
        coef_processos = 60 #Conversão para minutos!!
        coef_chegadas = 60
        coef_checkin = 60
        dados = {"Chegada":expovariate(0.0029),
                 "Ficha": random.triangular(2*2.12*coef_chegadas, 7*2.12*coef_chegadas, 4*2.12*coef_chegadas),
                 "Triagem": random.triangular(4*1.6*coef_chegadas, 9 * 1.6 * coef_chegadas, 7 * 1.6 * coef_chegadas),
                 "Clínico": random.triangular(10*1*coef_chegadas, 20 * 1* coef_chegadas, 15 * 1* coef_chegadas),
                 "Pediatra": random.triangular(8*coef_chegadas, 20 * coef_chegadas, 15 * coef_chegadas),
                 "Raio-x": 5 * coef_chegadas, #Cinco minutos
                 "Eletro": 12 * coef_chegadas,
                 "Exame de Urina": 2 * coef_chegadas,
                 "Exame de Sangue": 3 * coef_chegadas,
                 "Análise de Sangue Externo":  0.25 * 60 * coef_chegadas, #Quatro horas, mas reduzi pra meia ho
                 "Análise de Sangue Interno": 0.1 * 60 * coef_chegadas,
                 "Análise de Urina": 2 * 60 * coef_chegadas,
                 "Aplicar Medicação": random.triangular(10*coef_chegadas, 60 * coef_chegadas, 40 * coef_chegadas),
                 "Tomar Medicação": random.triangular(5*coef_chegadas, 40 * coef_chegadas, 15 * coef_chegadas),
                 }

        return dados[processo]


    def distribuicoes_cen4(processo, slot="None"):
        coef_processos = 60  # Conversão para minutos!!
        coef_chegadas = 60
        coef_checkin = 60
        dados = {"Chegada": expovariate(0.0029),
                 "Ficha": random.triangular(1 * 2.12 * coef_chegadas, 3.5 * 2.12 * coef_chegadas,
                                            2 * 2.12 * coef_chegadas),  # Diminui a metade!
                 "Triagem": random.triangular(4 * 1.6 * coef_chegadas, 9 * 1.6 * coef_chegadas,
                                              7 * 1.6 * coef_chegadas),
                 "Clínico": random.triangular(10 * 1 * coef_chegadas, 20 * 1 * coef_chegadas, 15 * 1 * coef_chegadas),
                 "Pediatra": random.triangular(8 * coef_chegadas, 20 * coef_chegadas, 15 * coef_chegadas),
                 "Raio-x": 5 * coef_chegadas,  # Cinco minutos
                 "Eletro": 12 * coef_chegadas,
                 "Exame de Urina": 2 * coef_chegadas,
                 "Exame de Sangue": 3 * coef_chegadas,
                 "Análise de Sangue Externo": 0.25 * 60 * coef_chegadas,  # Quatro horas, mas reduzi pra meia ho
                 "Análise de Sangue Interno": 0.1 * 60 * coef_chegadas,
                 "Análise de Urina": 2 * 60 * coef_chegadas,
                 "Aplicar Medicação": random.triangular(10 * coef_chegadas, 60 * coef_chegadas, 40 * coef_chegadas),
                 "Tomar Medicação": random.triangular(5 * coef_chegadas, 40 * coef_chegadas, 15 * coef_chegadas),
                 }

        return dados[processo]

    cenarios = {
        "Cenário Default" : {"recursos": {"Secretária": [2, False],
                                          "Enfermeira de Triagem": [3, False],
                                          "Clínico": [3, True],
                                          "Pediatra": [2, True],
                                          "Raio-x": [1, True],
                                          "Eletro": [1, True],
                                          "Técnica de Enfermagem": [2, True],
                                          "Espaço para tomar Medicação": [8, True]} ,
                             "distribuicoes" : distribuicoes},
        #Cenario 1: Aumento de uma secretária!!
        "Cenário 1" : {"recursos":  {"Secretária": [3, False], #aumento de 2 para 3
                                          "Enfermeira de Triagem": [3, False],
                                          "Clínico": [3, True],
                                          "Pediatra": [2, True],
                                          "Raio-x": [1, True],
                                          "Eletro": [1, True],
                                          "Técnica de Enfermagem": [2, True],
                                          "Espaço para tomar Medicação": [8, True]} ,
                             "distribuicoes" : distribuicoes},

        # Cenario 2: Aumento de uma secretária e uma enfermeira triagem!!
        "Cenário 2": {"recursos": {"Secretária": [3, False],  # aumentei de 2 para 3
                      "Enfermeira de Triagem": [4, False], # aumentei de 3 para 4
                      "Clínico": [3, True],
                      "Pediatra": [2, True],
                      "Raio-x": [1, True],
                      "Eletro": [1, True],
                      "Técnica de Enfermagem": [2, True],
                      "Espaço para tomar Medicação": [8, True]
                      }, "distribuicoes" : distribuicoes},

        # Cenário 3:  Aumento de uma enfermeira triagem, secretária e um clínico
        "Cenário 3": {"recursos": {"Secretária": [3, False],  # aumentei de 2 para 3
                      "Enfermeira de Triagem": [4, False], # aumentei de 3 para 4
                      "Clínico": [4, True], # aumentei de 3 para 4
                      "Pediatra": [2, True],
                      "Raio-x": [1, True],
                      "Eletro": [1, True],
                      "Técnica de Enfermagem": [2, True],
                      "Espaço para tomar Medicação": [8, True]
                      }, "distribuicoes" : distribuicoes},

        #Diminuindo o tempo da ficha pela metade e aumentando 1 na triagem
        "Cenário 4": {"recursos": {"Secretária": [2, False],
                "Enfermeira de Triagem": [4,False],
                "Clínico": [3,True],
                "Pediatra": [2,True],
                "Raio-x": [1, True],
                "Eletro": [1, True],
                "Técnica de Enfermagem": [2, True],
                "Espaço para tomar Medicação": [8, True]
                },
                "distribuicoes": distribuicoes_cen4}}

    estatisticas_finais = dict()
    corridas = list()
    for cen in cenarios:
        simulacao_cenario = Simulacao(distribuicoes=cenarios[cen]["distribuicoes"],
                          imprime=False,
                          recursos=cenarios[cen]["recursos"],
                          dist_prob=distribuicoes_probabilidade,
                          tempo=tempo,
                          necessidade_recursos=necessidade_recursos,
                          ordem_processo=ordem_processo,
                          atribuicoes=atribuicoes_processo,
                          liberacao_recurso=liberacao_recursos,
                          warmup = warmup,
                          )


        CorridaSimulacao_cenario = CorridaSimulacao(
            replicacoes=replicacoes,
            simulacao=simulacao_cenario,
            duracao_simulacao=tempo,
            periodo_warmup=warmup,
            plota_histogramas=True
        )
        corridas.append(copy.deepcopy((CorridaSimulacao_cenario)))
        CorridaSimulacao_cenario.roda_simulacao()
        CorridaSimulacao_cenario.fecha_estatisticas_experimento()
        estatisticas_finais[cen] = {"Atendimentos":CorridaSimulacao_cenario.numero_atendimentos,
                                    "utilizacao_media": CorridaSimulacao_cenario.utilizacao_media,
                                    "utilizacao_media_por_recurso": CorridaSimulacao_cenario.utilizacao_media_por_recurso,
                                    "media_tempo_fila_geral": CorridaSimulacao_cenario.media_em_fila_geral,
                                    "media_fila_por_prioridade": CorridaSimulacao_cenario.df_media_fila_por_prioridade,
                                    "dados_hist_entidades": CorridaSimulacao_cenario.dados }


    #Formatação dos dataframes para plots - Formato 1!!
    df_total_pacientes = pd.DataFrame({"Cenario": [cen for cen in cenarios], "Atendimentos": [estatisticas_finais[cen]["Atendimentos"] for cen in cenarios]})
    df_total_pacientes['Atendimentos'] = round(df_total_pacientes['Atendimentos'])
    df_utilizacao_media = pd.DataFrame({"Cenario": [cen for cen in cenarios], "Utilização": [estatisticas_finais[cen]["utilizacao_media"] for cen in cenarios]})
    df_utilizacao_media["Utilização"] = round(df_utilizacao_media["Utilização"],2)
    df_fila_media = pd.DataFrame({"Cenario": [cen for cen in cenarios], "Tempo_Médio_de_Fila": [estatisticas_finais[cen]["media_tempo_fila_geral"][0] for cen in cenarios]})
    df_fila_media["Tempo_Médio_de_Fila"] = round(df_fila_media["Tempo_Médio_de_Fila"],2)
    df_utilizacao_por_recurso = pd.DataFrame()

    for cen in cenarios:
        df_aux = estatisticas_finais[cen]['utilizacao_media_por_recurso']
        df_aux['Cenário'] = cen
        df_utilizacao_por_recurso = pd.concat([df_utilizacao_por_recurso, df_aux])

    df_filas_por_prioridade = pd.DataFrame()
    for cen in cenarios:
        df_aux = estatisticas_finais[cen]['media_fila_por_prioridade']
        df_aux['Cenário'] = cen
        df_filas_por_prioridade = pd.concat([df_filas_por_prioridade, df_aux])

    df_filas_por_prioridade = df_filas_por_prioridade.loc[df_filas_por_prioridade.prioridade != 'Nao Passou da Triagem'].reset_index()
    df_filas_por_prioridade.media_minutos = round(df_filas_por_prioridade.media_minutos,2)
    df_utilizacao_por_recurso.utilizacao = round(df_utilizacao_por_recurso.utilizacao * 100)



    #df_entidades para geração de histogramas!!!
    list_cen = [c for c in cenarios]
    df_entidades_hist = pd.DataFrame()
    for cor in corridas:
        for sim in cor.simulacoes:
            df_aux = sim.entidades.df_entidades
            #df_aux['Cenário'] = list_cen[corridas.index(cor)]
            df_entidades_hist = pd.concat([df_entidades_hist, df_aux])




    #Geração final dos gráficos
    #Filas

    CHART_THEME = 'plotly_white'
    #total de atendimentos, tempo médio de fila geral - Referência: https://medium.com/@guilhermedatt/como-fazer-subplots-com-plotly-em-python-704b831405f2
    fig = make_subplots(rows=1, cols=3, subplot_titles=("Pacientes Atendidos", "Média de Filas", "Utilização Média")) #dois gráficos lado a lado!!
    fig.layout.template = CHART_THEME
    fig.update_traces(textposition='outside')
    fig.update_layout(height=480)
    fig.add_trace(go.Bar(x=df_total_pacientes.Cenario, y= df_total_pacientes.Atendimentos, text=df_total_pacientes.Atendimentos,
                         textposition='outside'), row=1, col=1)
    fig.add_trace(go.Bar(x=df_fila_media.Cenario, y=df_fila_media.Tempo_Médio_de_Fila, text=df_fila_media.Tempo_Médio_de_Fila,
                         textposition='outside'), row=1, col=2)
    fig.add_trace(go.Bar(x=df_utilizacao_media.Cenario, y=df_utilizacao_media.Utilização, text=df_utilizacao_media.Utilização,
                         textposition='outside'), row=1, col=3)

    fig.update_yaxes(title_text='Total de Pacientes', row=1, col=1, showgrid=False, showticklabels=False)
    fig.update_yaxes(title_text='Tempo Médio de Fila (Min)', row=1, col=2, showgrid=False, showticklabels=False)
    fig.update_yaxes(title_text='Utilização (%)', row=1, col=3, showgrid=False, showticklabels=False)

    fig.update_xaxes(title_text='Cenário', row=1, col=1)
    fig.update_xaxes(title_text='Cenário', row=1, col=2)
    fig.update_xaxes(title_text='Cenário', row=1, col=3)

    for annotation in fig['layout']['annotations']:
        annotation['y'] = 1.1


    fig.show()

    #filas por prioridade - formato 1: Cada prioridade de cenário junto no mesmo gráfico
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

    #Fila por prioridade com subplots. Se modelo for aprovado, melhorar exibição.
    rows_total = 3
    cols = 2
    fig = make_subplots(rows=rows_total, cols=cols, row_heights=[.8 , .8, .8], column_widths=[.5, .5],
                        subplot_titles=["Pacientes com Prioridade " + str(pr) for pr in pd.unique(df_filas_por_prioridade.prioridade)])
    fig.layout.template = CHART_THEME
    fig.update_traces(textposition='inside')
    fig.update_layout(height=700)#, width=600)
    n_row = 1
    n_col = 1
    fig.update_yaxes(showgrid=False, showticklabels=False)
    fig.update_layout(title_text='Tempo Médio de Fila por Prioridade de Paciente (Min)', title_x=0.5, height=700)
    for pr in pd.unique(df_filas_por_prioridade.prioridade):
        df_aux = df_filas_por_prioridade.loc[df_filas_por_prioridade.prioridade == pr]
        fig.add_trace(go.Bar(x=df_aux.Cenário, y= df_aux.media_minutos, text=df_aux.media_minutos,
                             textposition='inside'), row=n_row, col=n_col)
        #fig.update_yaxes(title_text='Tempo Médio de Fila (Min)', row=n_row, col=n_col, showgrid=False, showticklabels=False)
        if n_col == cols:
            n_col = 1
            n_row += 1
        else:
            n_col += 1
    fig.show()

    #Utilização geral média
    fig = px.bar(df_utilizacao_media, x='Cenario', y='Utilização')
    fig.show()

    recursos = pd.unique(df_utilizacao_por_recurso.recurso)
    #utilização geral por recurso
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
    rows2 = 2
    cols = 4
    fig = make_subplots(rows=rows2, cols=cols,subplot_titles=["% de Utilização de " + rec for rec in recursos],)
    fig.layout.template = CHART_THEME
    fig.update_traces(textposition='inside')
    fig.update_layout(height=700)#, width=600)
    n_row = 1
    n_col = 1
    for rec in recursos:
        df_aux = df_utilizacao_por_recurso.loc[df_utilizacao_por_recurso.recurso == rec]
        fig.add_trace(go.Bar(x=df_aux.Cenário, y= df_aux.utilizacao, text=df_aux.utilizacao,
                              textposition='inside'), row=n_row, col=n_col)
        if n_col == cols:
            n_col = 1
            n_row += 1
        else:
            n_col += 1
    fig.show()


    #eixo x = recurso, cenário
    fig = px.bar(df_utilizacao_por_recurso, x='recurso', y='utilizacao', color='Cenário', barmode='group', text='utilizacao', title='Comparativo de Utilização de Recursos em Diferentes Cenários')  #text="nation"
    fig.update_traces(texttemplate='%{text:.2s}')
    fig.layout.template = CHART_THEME
    fig.update_traces(textposition='outside')
    fig.update_yaxes(title='Utilização Média (%)', showgrid=False)
    fig.update_xaxes(title='Recurso', showgrid=False)
    fig.update_yaxes(showticklabels=False)
    fig.update_layout(title_x=0.5)

    fig.show()

    #eixo x = cenário
    fig = px.bar(df_utilizacao_por_recurso, x='Cenário', y='utilizacao', color='recurso', barmode='group' , text_auto=True, text="utilizacao",  title='Comparativo de Utilização de Recursos em Diferentes Cenários')
    fig.update_traces(texttemplate='%{text:.2s}')
    fig.layout.template = CHART_THEME
    fig.update_traces(textposition='outside')
    fig.update_yaxes(title='Utilização Média (%)', showgrid=False)
    fig.update_xaxes(title='Recurso', showgrid=False)
    fig.update_yaxes(showticklabels=False)
    fig.update_layout(title_x=0.5)
    fig.show()



    #fila por prioridade: - Prioridade no eixo x
    fig = px.bar(df_filas_por_prioridade, x='prioridade', y='media_minutos', color='Cenário', barmode='group', text='media_minutos', title='Comparativo de Filas por Prioridade de Pacientes')  #text="nation"
    fig.update_traces(texttemplate='%{text:.2s}')
    fig.layout.template = CHART_THEME
    fig.update_traces(textposition='outside')
    fig.update_yaxes(title='Fila Média (Min)', showgrid=False)
    fig.update_xaxes(title='Prioridade do Paciente', showgrid=False)
    fig.update_yaxes(showticklabels=False)
    fig.update_layout(title_x=0.5)

    fig.show()

    #fila por prioridade: - Cenário no eixo x
    fig = px.bar(df_filas_por_prioridade, x='Cenário', y='media_minutos', color='prioridade', barmode='group', text='media_minutos', title='Comparativo de Filas por Prioridade de Pacientes')  #text="nation"
    fig.update_traces(texttemplate='%{text:.2s}')
    fig.layout.template = CHART_THEME
    fig.update_traces(textposition='outside')
    fig.update_yaxes(title='Fila Média (Min)', showgrid=False)
    fig.update_xaxes(title='Prioridade do Paciente', showgrid=False)
    fig.update_yaxes(showticklabels=False)
    fig.update_layout(title_x=0.5)

    fig.show()

    b=0