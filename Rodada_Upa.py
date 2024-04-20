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
                 "Clínico": random.triangular(7.*1*coef_chegadas, 17 * 1* coef_chegadas, 12 * 1* coef_chegadas),
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
        # Cenário 1: Diminuindo uma secretária
        "To Be 1": {"recursos": {"Secretária": [1, False],  # De 2 para 1
                                   "Enfermeira de Triagem": [3, False],
                                   "Clínico": [3, True],
                                   "Pediatra": [2, True],
                                   "Raio-x": [1, True],
                                   "Eletro": [1, True],
                                   "Técnica de Enfermagem": [2, True],
                                   "Espaço para tomar Medicação": [8, True]},
                      "distribuicoes": distribuicoes},

        # Diminuindo o tempo da ficha pela metade e aumentando 1 na triagem
        "To Be 2": {"recursos": {"Secretária": [1, False],
                                   # Tirar uma secretária e colocar outra muito eficiente com metade do tempo
                                   "Enfermeira de Triagem": [3, False],
                                   "Clínico": [2, True],  # De 3 para 2
                                   "Pediatra": [2, True],
                                   "Raio-x": [1, True],
                                   "Eletro": [1, True],
                                   "Técnica de Enfermagem": [2, True],
                                   "Espaço para tomar Medicação": [8, True]},
                      "distribuicoes": distribuicoes_cen4},


        "As Is" : {"recursos": {"Secretária": [2, False],
                                          "Enfermeira de Triagem": [3, False],
                                          "Clínico": [3, True],
                                          "Pediatra": [2, True],
                                          "Raio-x": [1, True],
                                          "Eletro": [1, True],
                                          "Técnica de Enfermagem": [2, True],
                                          "Espaço para tomar Medicação": [8, True]} ,
                             "distribuicoes" : distribuicoes},

        #Cenario 1: Aumento de uma secretária!!
        "To Be 3" : {"recursos":  {"Secretária": [2, False], #aumento de 2 para 3
                                          "Enfermeira de Triagem": [3, False],
                                          "Clínico": [4, True],
                                          "Pediatra": [2, True],
                                          "Raio-x": [1, True],
                                          "Eletro": [1, True],
                                          "Técnica de Enfermagem": [2, True],
                                          "Espaço para tomar Medicação": [8, True]} ,
                             "distribuicoes" : distribuicoes},

        # Cenário 3:  Aumento de uma enfermeira triagem, secretária e um clínico
        "To Be 4": {"recursos": {"Secretária": [3, False],  # aumentei de 2 para 3
                      "Enfermeira de Triagem": [4, False], # aumentei de 3 para 4
                      "Clínico": [4, True], # aumentei de 3 para 4
                      "Pediatra": [2, True],
                      "Raio-x": [1, True],
                      "Eletro": [1, True],
                      "Técnica de Enfermagem": [2, True],
                      "Espaço para tomar Medicação": [8, True]
                      }, "distribuicoes" : distribuicoes},


    }

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
        CorridaSimulacao_cenario.roda_simulacao()
        CorridaSimulacao_cenario.fecha_estatisticas_experimento()
        corridas.append(copy.copy(CorridaSimulacao_cenario))
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

    # Geração final dos gráficos
    # Tradução de dados para o inglês
    traduz = True
    if traduz:
        dicionario_traduzido_recursos = {
            "Secretária": "Secretariat",  # De 2 para 1
             "Enfermeira de Triagem": "Nurse Screening",
             "Clínico": "Clinic",
             "Pediatra": "Pediatrician",
             "Raio-x": "X-Ray",
             "Eletro": "Electrocardiogram" ,
             "Técnica de Enfermagem": "Nursing Technician",
             "Espaço para tomar Medicação": "Medication Space"
        }

        dicionario_traduzido_processos = {
            "Ficha": "Registration of Patient",
            "Triagem": "Screening",
            "Clínico": " Clinical Consultation",
            "Pediatra": "Pediatric Consultation",
            "Aplicar Medicação": "Applying Medication",
            "Tomar Medicação": "Taking Medication" ,
            "Exame de Urina": "Urine Test",
            "Exame de Sangue": "Blood Test" ,
            "Análise de Urina": "Urine Test Analysis",
            "Análise de Sangue Externo": "External Blood Test Analysis" ,
            "Análise de Sangue Interno": "Internal Blood Test Analysis",
            "Raio-x": "X-Ray",
            "Eletro": "Electrocardiogram"
        }

        df_total_pacientes.rename(columns={"Cenario": "Scenarios", "Atendimentos": "Patients Seen"}, inplace=True)
        df_utilizacao_media.rename(columns={"Cenario": "Scenarios", "Utilização": "Resources Usage (%)"}, inplace=True)
        df_fila_media.rename(columns={"Cenario": "Scenarios", "Tempo_Médio_de_Fila": "Queue Average Time (Min)"} ,inplace=True)
        df_utilizacao_por_recurso.rename(columns={"recurso": "Resource", "utilizacao" : "Resources Usage (%)", "Cenário": "Scenarios"}, inplace=True)
        df_utilizacao_por_recurso['Resource'] = df_utilizacao_por_recurso.Resource.apply(lambda x: dicionario_traduzido_recursos[x])
        df_filas_por_prioridade.rename(columns={"prioridade": "Patient Priority", "media_minutos": "Queue Average (Min)",  "Cenário": "Scenarios"},inplace=True)

        CHART_THEME = 'plotly_white'
        fig = px.bar(df_utilizacao_media, x='Scenarios', y='Resources Usage (%)')
        fig.show()


        #Utiização Média de Recursos
        fig = px.bar(df_utilizacao_por_recurso, x='Resource', y='Resources Usage (%)', color='Scenarios', barmode='group',
                     text='Resources Usage (%)', title='Average Utilization Resources in Scenarioss')  # text="nation"
        fig.update_traces(texttemplate='%{text:.2s}')
        fig.layout.template = CHART_THEME
        fig.update_traces(textposition='outside')
        #fig.update_yaxes(title='Utilização Média (%)', showgrid=False)
        #fig.update_xaxes(title='Recurso', showgrid=False)
        fig.update_yaxes(showticklabels=False)
        fig.update_layout(title_x=0.5)
        fig.show()

        #Gráfico de utilização Cenário x Recurso
        fig = px.bar(df_utilizacao_por_recurso, x='Scenarios', y='Resources Usage (%)', color='Resource',
                     barmode='group',
                     text='Resources Usage (%)', title='Average Utilization Resources in Scenarioss')  # text="nation"
        fig.update_traces(texttemplate='%{text:.2s}')
        fig.layout.template = CHART_THEME
        fig.update_traces(textposition='outside')
        # fig.update_yaxes(title='Utilização Média (%)', showgrid=False)
        # fig.update_xaxes(title='Recurso', showgrid=False)
        fig.update_yaxes(showticklabels=False)
        fig.update_layout(title_x=0.5)
        fig.show()

        #Filas por prioridade!
        fig = px.bar(df_filas_por_prioridade, x='Patient Priority', y='Queue Average (Min)', color='Scenarios', barmode='group',
                     text='Queue Average (Min)', title='Patient Queues by Priority in Scenarioss')  # text="nation"
        fig.update_traces(texttemplate='%{text:.2s}')
        fig.layout.template = CHART_THEME
        fig.update_traces(textposition='outside')
        #fig.update_yaxes(title='Fila Média (Min)', showgrid=False)
        #fig.update_xaxes(title='Prioridade do Paciente', showgrid=False)
        fig.update_yaxes(showticklabels=False)
        fig.update_layout(title_x=0.5)

        fig.show()

        #Filas por prioridade e processos!
        fig = px.bar(df_filas_por_prioridade, x='Scenarios', y='Queue Average (Min)', color='Patient Priority', barmode='group',
                     text='Queue Average (Min)', title='Patient Queues by Priority in Scenarios')  # text="nation"
        fig.update_traces(texttemplate='%{text:.2s}')
        fig.layout.template = CHART_THEME
        fig.update_traces(textposition='outside')
        #fig.update_yaxes(title='Fila Média (Min)', showgrid=False)
        #fig.update_xaxes(title='Prioridade do Paciente', showgrid=False)
        fig.update_yaxes(showticklabels=False)
        fig.update_layout(title_x=0.5)

        fig.show()

    else:
        CHART_THEME = 'plotly_white'

        #Utilização geral média
        fig = px.bar(df_utilizacao_media, x='Cenario', y='Utilização')
        fig.show()

        recursos = pd.unique(df_utilizacao_por_recurso.recurso)


        #eixo x = recurso, cenário
        fig = px.bar(df_utilizacao_por_recurso, x='recurso', y='utilizacao', color='Cenário', barmode='group', text='utilizacao', title=' Utilização Média de Recursos nos Cenários')  #text="nation"
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

    b=0
    #TODO:
    #Ver porque está saindo mais pacientes do que entrando! - Parou de acontecer, mas Continuar monitorando
    # Passar tudo para inglês!
    #Colocar cenario 1 como o pior, 3 como o real e 5 como o melhor
    #Passar nome da coluna dos dfs para Cenários
    #ver porque o Media de tempo de fila do recurso Espaço para tomar Medicação está como nan minutos e com média 0 entidades - precisa alterar o nome do recurso. Feito!
    #Passar para inglês!