import copy
import statistics

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


def retorna_prioridade(paciente, lista_entidades):
    try:
        prioridade = next(ent.atributos['prioridade'] for ent in lista_entidades if paciente == ent.nome)
        return prioridade
    except KeyError:
        return "Nao Passou da Triagem"


def converte_segundos_em_dias(x):
    return x / 86400


def converte_segundos_em_semanas(x):
    return x / (86400 * 7)


def converte_segundos_em_meses(x):
    return x / (86400 * 30)


def calc_ic(lista):
    confidence = 0.95
    n = len(lista)
    # mean_se: Erro Padrão da Média
    mean_se = stats.sem(lista)
    h = mean_se * stats.t.ppf((1 + confidence) / 2., n - 1)
    # Intervalo de confiança: mean, +_h
    return h

def cria_planilha(CorridaSimulacao_base, path= ""):
    prs = [1, 2, 3, 4, 5, "sem_pr"]
    recursos = [r for r in CorridaSimulacao_base.dados_planilha[0]['dados_tempo']]
    aba_1 = list()
    aba_2 = list()
    for run in CorridaSimulacao_base.dados_planilha:
        for rec in CorridaSimulacao_base.dados_planilha[run]['dados_tempo']:
            dc_rec = {"Replicacao": run, "Name": rec + ".Queue", "Type": "Waiting Time", "Source": "Queue",
                  "Average": np.mean(CorridaSimulacao_base.dados_planilha[run]['dados_tempo'][rec]['dados_fila']) if len(CorridaSimulacao_base.dados_planilha[run]['dados_tempo'][rec]['dados_fila']) > 0 else 0,
                  "BatchMeansHalfWidth": calc_ic(CorridaSimulacao_base.dados_planilha[run]['dados_tempo'][rec]['dados_fila']) if len(CorridaSimulacao_base.dados_planilha[run]['dados_tempo'][rec]['dados_fila']) > 0 else 0,
                  "StDev": np.std(CorridaSimulacao_base.dados_planilha[run]['dados_tempo'][rec]['dados_fila']) if len(CorridaSimulacao_base.dados_planilha[run]['dados_tempo'][rec]['dados_fila']) > 0 else 0,
                  "Minimum": min(CorridaSimulacao_base.dados_planilha[run]['dados_tempo'][rec]['dados_fila']) if len(CorridaSimulacao_base.dados_planilha[run]['dados_tempo'][rec]['dados_fila']) > 0 else 0,
                  "Maximum": max(CorridaSimulacao_base.dados_planilha[run]['dados_tempo'][rec]['dados_fila']) if len(CorridaSimulacao_base.dados_planilha[run]['dados_tempo'][rec]['dados_fila']) > 0 else 0,
                  "NumberObservations":len(CorridaSimulacao_base.dados_planilha[run]['dados_tempo'][rec]['dados_fila']),
                  }
            aba_1.append(dc_rec)

            # TODO: Isso precisa ser o nome do processo!
            dc_number_waiting = {"Replicacao": run, "Name": rec + ".Queue", "Type": "Number Waiting", "Source": "Queue",
                             "Average": np.mean(CorridaSimulacao_base.dados_planilha[run]['dados_tempo'][rec]['dados_entidade_em_fila']),
                             "BatchMeansHalfWidth":calc_ic(CorridaSimulacao_base.dados_planilha[run]['dados_tempo'][rec]['dados_entidade_em_fila']),
                             "Minimum": min(CorridaSimulacao_base.dados_planilha[run]['dados_tempo'][rec]['dados_entidade_em_fila']),
                             "Maximum": max(CorridaSimulacao_base.dados_planilha[run]['dados_tempo'][rec]['dados_entidade_em_fila'])}

            aba_2.append(dc_number_waiting)

            dc_utilizacao = {"Replicacao": run, "Name": rec , "Type": "Instantaneous Utilization", "Source": "Resource",
                             "Average": np.mean(CorridaSimulacao_base.dados_planilha[run]['dados_tempo'][rec]['dados_utilizacao']),
                             "BatchMeansHalfWidth":calc_ic(CorridaSimulacao_base.dados_planilha[run]['dados_tempo'][rec]['dados_utilizacao']),
                             "Minimum": min(CorridaSimulacao_base.dados_planilha[run]['dados_tempo'][rec]['dados_utilizacao']),
                             "Maximum": max(CorridaSimulacao_base.dados_planilha[run]['dados_tempo'][rec]['dados_utilizacao'])}
            aba_2.append(dc_utilizacao)

        dc_wip = {"Replicacao": run, "Name": "Pacientes", "Type": "WIP", "Source": "Entity",
                         "Average": CorridaSimulacao_base.dados_planilha[run]['media_WIP'],
                         "BatchMeansHalfWidth": CorridaSimulacao_base.dados_planilha[run]['IC_TS'],
                         "Minimum": CorridaSimulacao_base.dados_planilha[run]['min_WIP'],
                         "Maximum": CorridaSimulacao_base.dados_planilha[run]['max_wip'],}

        aba_2.append(dc_wip)

        dc_entity_Total_Time_global = {"Replicacao": run, "Name": "Paciente", "Type": "Total Time", "Source": "Entity", "Average": np.mean(CorridaSimulacao_base.dados_planilha[run]['media_tempo_sistema_total']),
                     "BatchMeansHalfWidth": CorridaSimulacao_base.dados_planilha[run]['IC_TS'],
                     "StDev": CorridaSimulacao_base.dados_planilha[run]['desv_pad_TS'],
                     "Minimum":  CorridaSimulacao_base.dados_planilha[run]['min_TS'],
                     "Maximum":  CorridaSimulacao_base.dados_planilha[run]['max_TS'],
                     "NumberObservations": CorridaSimulacao_base.dados_planilha[run]['amostra_TS']
                                       } #TODO: Pegar num_observations!!!!
        aba_1.append(dc_entity_Total_Time_global)
        #TODO: Gerar dados globais!
        dc_entity_VA_Time_global = {"Replicacao": run, "Name": "Paciente", "Type": "VA Time", "Source": "Entity", "Average": np.mean(CorridaSimulacao_base.dados_planilha[run]['Dados_TA']), #soma das médias os recursos!
                     "BatchMeansHalfWidth": calc_ic(CorridaSimulacao_base.dados_planilha[run]['Dados_TA']),
                     "StDev": np.std(CorridaSimulacao_base.dados_planilha[run]['Dados_TA']),
                     "Minimum":  min(CorridaSimulacao_base.dados_planilha[run]['Dados_TA']),
                     "Maximum":  max(CorridaSimulacao_base.dados_planilha[run]['Dados_TA']),
                     "NumberObservations": len(CorridaSimulacao_base.dados_planilha[run]['Dados_TA'])}

        aba_1.append(dc_entity_VA_Time_global)
        #TODO: Gerar dados globais!
        dc_entity_Waiting_Time_global = {"Replicacao": run, "Name": "Paciente", "Type": "Wait Time", "Source": "Entity", "Average": np.mean(CorridaSimulacao_base.dados_planilha[run]['Dados_Fila']),  # soma das médias os recursos!
                                    "BatchMeansHalfWidth": calc_ic(CorridaSimulacao_base.dados_planilha[run]['Dados_Fila']),
                                    "StDev": np.std(CorridaSimulacao_base.dados_planilha[run]['Dados_Fila']),
                                    "Minimum": min(CorridaSimulacao_base.dados_planilha[run]['Dados_Fila']),
                                    "Maximum": max(CorridaSimulacao_base.dados_planilha[run]['Dados_Fila']),
                                    "NumberObservations": len(CorridaSimulacao_base.dados_planilha[run]['Dados_Fila'])}

        aba_1.append(dc_entity_Waiting_Time_global)

    df_aba_1 = pd.DataFrame(aba_1)
    df_aba_2 = pd.DataFrame(aba_2)
    nome_arquivo = 'RESULTADOS_FINAIS' + " - " + path + ".xlsx"
    with pd.ExcelWriter(nome_arquivo) as writer:
        df_aba_1.to_excel(writer, sheet_name='DiscreteTimeStatsByRep')
        df_aba_2.to_excel(writer, sheet_name='ContinuousTimeStatsByRep')


if __name__ == "__main__":

    #Dados e parâmetros default em todos os cenários:
    #seed(1000)
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
    tempo = 24 * 60 * 60 * 30 * 1
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

        classificacao_clinico_pediatra = [["Clínico", 0.78],
                                          ["Pediatra", 0.22]]
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

    warmup = 5 * 86400
    replicacoes = 30
    #seed(1000)
    recursos_base = {"Secretária": [2, False],
                               "Enfermeira de Triagem": [2, False],
                               "Clínico": [3, True],
                               "Pediatra": [2, True],
                               "Raio-x": [1, True],
                               "Eletro": [1, True],
                               "Técnica de Enfermagem": [2, True],
                               "Espaço para tomar Medicação": [8, True],
                               "Default_Aguarda_Medicacao": [100000, False]} #Recurso default para guardar entidades esperando exames!}

    def distribuicoes_base(processo, slot="None"):
        coef_processos = 60 #Conversão para minutos!!
        coef_chegadas = 60
        coef_checkin = 60
        dados = {"Chegada": expovariate(0.0029),
                 "Ficha": random.triangular(2 * 2.12 * coef_chegadas, 7 * 2.12 * coef_chegadas,
                                            4 * 2.12 * coef_chegadas),
                 "Triagem": random.triangular(4 * 1.6 * coef_chegadas, 9 * 1.6 * coef_chegadas,
                                              7 * 1.6 * coef_chegadas),
                 "Clínico": random.triangular(10 * 0.95 * coef_chegadas, 20 * 0.95 * coef_chegadas, 15 * 0.95 * coef_chegadas),
                 "Pediatra": random.triangular(8 * coef_chegadas, 20 * coef_chegadas, 15 * coef_chegadas),
                 "Raio-x": 5 * coef_chegadas,  # Cincominutos
                 "Eletro": 12 * coef_chegadas,
                 "Exame de Urina": 2 * coef_chegadas,
                 "Exame de Sangue": 3 * coef_chegadas,
                 "Análise de Sangue Externo": 0.25 * 60 * coef_chegadas,  # Quatrohoras,masreduziprameiaho
                 "Análise de Sangue Interno": 0.1 * 60 * coef_chegadas,
                 "Análise de Urina": 2 * 60 * coef_chegadas,
                 "Aplicar Medicação": random.triangular(10 * coef_chegadas, 60 * coef_chegadas, 40 * coef_chegadas),
                 "Tomar Medicação": random.triangular(5 * coef_chegadas, 40 * coef_chegadas, 15 * coef_chegadas),
                 }

        return dados[processo]

    #Rodada para 1 cenário apenas!!
    simulacao_base = Simulacao(distribuicoes=distribuicoes_base,
                                  imprime=False,
                                  recursos=recursos_base,
                                  dist_prob=distribuicoes_probabilidade,
                                  tempo=tempo,
                                  necessidade_recursos=necessidade_recursos,
                                  ordem_processo=ordem_processo,
                                  atribuicoes=atribuicoes_processo,
                                  liberacao_recurso=liberacao_recursos,
                                  warmup=0,
                                  )

    CorridaSimulacao_base = CorridaSimulacao(
            replicacoes=1,
            simulacao=simulacao_base,
            duracao_simulacao=tempo,
            periodo_warmup=warmup,
            plota_histogramas=True
        )

    #CorridaSimulacao_base.roda_simulacao()
    b=0
    def distribuicoes_cen4(processo, slot="None"):
        coef_processos = 60  # Conversão para minutos!!
        coef_chegadas = 60
        coef_checkin = 60
        dados = {"Chegada": expovariate(0.0029),
                 "Ficha": random.triangular(2 * 1 * coef_chegadas, 7 * 1 * coef_chegadas,
                                            4 * 1 * coef_chegadas),
                 "Triagem": random.triangular(4 * 1.6 * coef_chegadas, 9 * 1.6 * coef_chegadas,
                                              7 * 1.6 * coef_chegadas),
                 "Clínico": random.triangular(10 * 0.95 * coef_chegadas, 20 * 0.95 * coef_chegadas, 15 * 0.95 * coef_chegadas),
                 "Pediatra": random.triangular(8 * coef_chegadas, 20 * coef_chegadas, 15 * coef_chegadas),
                 "Raio-x": 5 * coef_chegadas,  # Cincominutos
                 "Eletro": 12 * coef_chegadas,
                 "Exame de Urina": 2 * coef_chegadas,
                 "Exame de Sangue": 3 * coef_chegadas,
                 "Análise de Sangue Externo": 0.25 * 60 * coef_chegadas,  # Quatrohoras,masreduziprameiaho
                 "Análise de Sangue Interno": 0.1 * 60 * coef_chegadas,
                 "Análise de Urina": 2 * 60 * coef_chegadas,
                 "Aplicar Medicação": random.triangular(10 * coef_chegadas, 60 * coef_chegadas, 40 * coef_chegadas),
                 "Tomar Medicação": random.triangular(5 * coef_chegadas, 40 * coef_chegadas, 15 * coef_chegadas),
                 }

        return dados[processo]

    cenarios = {
        # Cenário 1: Diminuindo uma secretária e diminuindo o tempo de processo
        "To Be 1": {"recursos": {"Secretária": [1, False],  # De 2 para 1
                                 "Enfermeira de Triagem": [2, False],
                                 "Clínico": [3, True],
                                 "Pediatra": [2, True],
                                 "Raio-x": [1, True],
                                 "Eletro": [1, True],
                                 "Técnica de Enfermagem": [2, True],
                                 "Espaço para tomar Medicação": [8, True],
                                 "Default_Aguarda_Medicacao": [100000, False]},
                    "distribuicoes": distribuicoes_cen4},

        # # Diminuindo o tempo da ficha pela metade e aumentando 1 na triagem

        "As Is": {"recursos": {"Secretária": [2, False],
                               "Enfermeira de Triagem": [2, False],
                               "Clínico": [3, True],
                               "Pediatra": [2, True],
                               "Raio-x": [1, True],
                               "Eletro": [1, True],
                               "Técnica de Enfermagem": [2, True],
                               "Espaço para tomar Medicação": [8, True],
                               "Default_Aguarda_Medicacao": [100000, False]},
                  "distribuicoes": distribuicoes_base},

        #Dobro dos recursos de exame!
        "To Be 2": {"recursos":  {"Secretária": [2, False],
                               "Enfermeira de Triagem": [2, False],
                               "Clínico": [3, True],
                               "Pediatra": [2, True],
                               "Raio-x": [2, True],
                               "Eletro": [2, True],
                               "Técnica de Enfermagem": [4, True],
                               "Espaço para tomar Medicação": [16, True],
                                "Default_Aguarda_Medicacao": [100000, False]},
                    "distribuicoes": distribuicoes_base},


        # # Cenario 1: Aumento de uma secretária e uma enfermeira de triagem!!
        "To Be 3": {"recursos": {"Secretária": [3, False],  # aumento de 2 para 3
                                 "Enfermeira de Triagem": [3, False],
                                 "Clínico": [3, True],
                                 "Pediatra": [2, True],
                                 "Raio-x": [1, True],
                                 "Eletro": [1, True],
                                 "Técnica de Enfermagem": [2, True],
                                 "Espaço para tomar Medicação": [8, True],
                                 "Default_Aguarda_Medicacao": [100000, False]},
                    "distribuicoes": distribuicoes_base},

        # Cenário 3:  Aumento de uma enfermeira triagem, secretária e um clínico
        "To Be 4": {"recursos": {"Secretária": [3, False],  # aumentei de 2 para 3
                                 "Enfermeira de Triagem": [3, False],  # aumentei de 2 para 3
                                 "Clínico": [4, True],  # aumentei de 3 para 4
                                 "Pediatra": [2, True],
                                 "Raio-x": [1, True],
                                 "Eletro": [1, True],
                                 "Técnica de Enfermagem": [2, True],
                                 "Espaço para tomar Medicação": [8, True],
                                 "Default_Aguarda_Medicacao": [100000, False]},
                                "distribuicoes": distribuicoes_base},

    }

    estatisticas_finais = dict()
    corridas = list()
    #Rodada dos cenários
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
            replicacoes= 30,
            simulacao=simulacao_cenario,
            duracao_simulacao=tempo,
            periodo_warmup=warmup,
            plota_histogramas=True
        )
        CorridaSimulacao_cenario.roda_simulacao()
        dados_cenario = CorridaSimulacao_cenario.fecha_estatisticas_experimento()
        #corridas.append(copy.copy(CorridaSimulacao_cenario))
        estatisticas_finais[cen] = dados_cenario
        cria_planilha(CorridaSimulacao_cenario, cen)

    #Formatação dos dataframes para plots - Formato 1!!
    dados_wip = list()
    dados_utilizacao_media = list()
    dados_pacientes_atendidos = list()
    #dados_tempo_fila = list()
    for cen in estatisticas_finais:
        for rep in estatisticas_finais[cen]:
            dados_wip.append({"Cenário": cen, "Replicação": rep, "WIP": estatisticas_finais[cen][rep]['dados_NS'], "discretizacao": estatisticas_finais[cen][rep]["momento_NS"]})
            dados_pacientes_atendidos.append({"Cenário": cen, "Replicação": rep, "entidades_atendidas": len(estatisticas_finais[cen][rep]['dados_TS']) })
            for rec in estatisticas_finais[cen][rep]['dict_utilizacao']:
                dados_utilizacao_media.append({"Cenário": cen,
                                               "Replicação": rep,
                                               "Recurso":rec,
                                                "utilizacao":estatisticas_finais[cen][rep]['dict_utilizacao'][rec]['dados_utilizacao'],
                                                "T":estatisticas_finais[cen][rep]['dict_utilizacao'][rec]['discretizacao'],
                                                "Tempo_fila":estatisticas_finais[cen][rep]['dict_utilizacao'][rec]['tempo_fila'],
                                                "prioridade_entidade": estatisticas_finais[cen][rep]['dict_utilizacao'][rec]['prioridade_entidade'],
                                                "tempo_fila_prioridade_entidade": estatisticas_finais[cen][rep]['dict_utilizacao'][rec]['tempo_fila_prioridade_entidade'],
                                                "processo": estatisticas_finais[cen][rep]['dict_utilizacao'][rec]['processo'],
                                                "tempo_fila_entidades": estatisticas_finais[cen][rep]['dict_utilizacao'][rec]['tempo_fila_entidades'],
                                               })



    graficos_de_todas_as_replicacoes_juntas = False
    traduz = True
    gera_graficos = True #Não consegui gerar gráficos devido a quantidade de dados e memória. Se o computador de quem está rodando aguentar, passar flag como true. Senão, passar como false, gerar os arquivos csv e rodar o  próximo script
    if gera_graficos:
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
                "Eletro": "Electrocardiogram",
                "chegada": "Arrive",
                "saida": "Exit",
                "Aguarda Resultado de Exame": "Waiting Examination Results"
            }

            CHART_THEME = 'plotly_white'

            #Gerar gráficos de cada simulação para todas as corridas!!
            #Gráfico WIP!

            df_wip = pd.DataFrame(dados_wip).explode(["WIP", "discretizacao"])
            df_wip.rename(columns={"Cenário": "Scenarios", "Replicação": "Run"}, inplace=True)
            df_wip['Duracao_Dias'] = df_wip.discretizacao / 86000
            #df_scenario_run_WIP = df_wip.groupby(by=['Scenarios', 'discretizacao', 'Run']).agg({"WIP": "mean"}).reset_index()
            #duracao_dias_sr = [converte_segundos_em_dias(x) for x in df_wip.discretizacao]

            fig = px.line(df_wip, x=df_wip.Duracao_Dias, y=df_wip.WIP, color="Scenarios")
            fig.update_layout(title='Global Average Entities in Process (WIP)')
            fig.update_xaxes(title='Duration (D)', showgrid=False)
            fig.update_yaxes(title='Number os Patients')
            fig.layout.template = CHART_THEME
            fig.update_layout(title_x=0.5)

            fig.show()

            #Não usei WIPS nos resultados
            #WIPS por cenário:
            # for cen in estatisticas_finais:
            #     df_ = df_wip.loc[df_wip.Scenarios == cen]
            #     fig = px.line(df_, x=df_.Duracao_Dias, y=df_.WIP, color="Run")
            #     fig.update_layout(title=f'Global Average Entities in Process (WIP) - Scanerio {cen} ')
            #     fig.update_xaxes(title='Duration (D)', showgrid=False)
            #     fig.update_yaxes(title='Number os Patients')
            #     fig.layout.template = CHART_THEME
            #     fig.update_layout(title_x=0.5)

                #fig.show()


            #Limpar dfs wips para não pesar:
            df_ = 0
            df_wip = 0


            df_recursos = pd.DataFrame(dados_utilizacao_media).explode(['utilizacao', 'T', 'processo', 'prioridade_entidade', 'Tempo_fila', 'tempo_fila_prioridade_entidade', 'tempo_fila_entidades' ])
            df_recursos.rename(columns={'Cenário': "Scenarios",
                                        "Replicação": "Run",
                                        "Recurso": "Resource",
                                        "utilizacao" : "Resources Usage (%)",
                                        'prioridade_entidade':"Patient Priority",
                                        "processo": "Process",
                                        "tempo_fila_prioridade_entidade": "Queue Time (Min)",

                                        }, inplace=True)
            df_recursos['Resource'] = df_recursos.Resource.apply(lambda x: dicionario_traduzido_recursos[x])
            df_recursos['Process'] = df_recursos.Process.apply(lambda x: dicionario_traduzido_processos[x])


            #Utilizações:
            #Média geral por cenário!
            df_ocupacao_media_cenario_por_recurso = df_recursos.groupby(by=['Scenarios', 'Resource']).agg({"Resources Usage (%)": 'mean'}).reset_index()
            df_ocupacao_media_cenario_por_recurso["Resources Usage (%)"] = round(df_ocupacao_media_cenario_por_recurso["Resources Usage (%)"]*100, 2)
            fig = px.bar(df_ocupacao_media_cenario_por_recurso, x='Resource', y='Resources Usage (%)', color='Scenarios', barmode='group',
                         text='Resources Usage (%)', title='Average Utilization Resources in Scenarios')  # text="nation"
            fig.update_traces(texttemplate='%{text:.2s}%')
            fig.layout.template = CHART_THEME
            fig.update_traces(textposition='outside')
            #fig.update_yaxes(title='Utilização Média (%)', showgrid=False)
            #fig.update_xaxes(title='Recurso', showgrid=False)
            fig.update_yaxes(showticklabels=False)
            fig.update_layout(title_x=0.5)
            fig.update_layout(font=dict(size=18))

            fig.show()



            #Média de utilizações por cenário - tentar agrupar em intervalos de tempo menor para gerar uma linha de fato, e não uma mancha (tirar a média arredondando?)!
            fig = px.bar(df_ocupacao_media_cenario_por_recurso, x='Scenarios', y='Resources Usage (%)', color='Resource', barmode='group',
                         text='Resources Usage (%)', title='Average Utilization Resources in Scenarios')  # text="nation"
            fig.update_traces(texttemplate='%{text:.2s}%')
            fig.layout.template = CHART_THEME
            fig.update_traces(textposition='outside')
            #fig.update_yaxes(title='Utilização Média (%)', showgrid=False)
            #fig.update_xaxes(title='Recurso', showgrid=False)
            fig.update_yaxes(showticklabels=False)
            fig.update_layout(title_x=0.5)
            fig.update_layout(font=dict(size=18))
            fig.show()

            #Utilizações para printar!
            s =  [['As Is', 'To Be 1'],
             ['As Is', 'To Be 2'],
            ['As Is', 'To Be 3'],
            ['As Is', 'To Be 4']]

            #Gráficos de utilização que estão no word,comparanado apenas 2 arquivos!!
            for s1 in s:
                df = df_ocupacao_media_cenario_por_recurso.loc[df_ocupacao_media_cenario_por_recurso.Scenarios.isin(s1)]
                fig = px.bar(df, x='Scenarios', y='Resources Usage (%)', color='Resource',
                             barmode='group',
                             text='Resources Usage (%)',
                             title='Average Utilization Resources in Scenarios')  # text="nation"
                fig.update_traces(texttemplate='%{text:.2s}%')
                fig.layout.template = CHART_THEME
                fig.update_traces(textposition='outside')
                # fig.update_yaxes(title='Utilização Média (%)', showgrid=False)
                # fig.update_xaxes(title='Recurso', showgrid=False)
                fig.update_yaxes(showticklabels=False)
                fig.update_layout(title_x=0.5)
                fig.update_layout(font=dict(size=18))
                fig.show()




            #médias de tempos de fila por processo - por cenário e geral?
            df_fila_media_por_processo = df_recursos.groupby(by=['Scenarios', "Process"]).agg({"Queue Time (Min)": "mean"}).reset_index()
            df_fila_entidades = df_recursos.groupby(by=['Scenarios', "Process"]).agg({"Queue Time (Min)": "mean"}).reset_index()
            df_fila_entidades["Queue Time (Min)"] = round(df_fila_entidades["Queue Time (Min)"],2)

            fig = px.bar(df_fila_entidades, x='Process', y="Queue Time (Min)", color='Scenarios' ,text="Queue Time (Min)", title= "Process Queue Time by Scenarios", barmode='group')
            fig.update_traces(texttemplate='%{text:.2s}')
            fig.layout.template = CHART_THEME
            fig.update_traces(textposition='outside')
            fig.update_yaxes(showticklabels=False)
            #fig.update_xaxes(showticklabels=False)
            fig.update_layout(title_x=0.5)
            fig.update_layout(font=dict(size=18))
            fig.show()

            #Versão 2: Cenário x recurso
            fig = px.bar(df_fila_entidades, x='Scenarios', y="Queue Time (Min)", color='Process' ,text="Queue Time (Min)", title= "Process Queue Time by Scenarios", barmode='group')
            fig.update_traces(texttemplate='%{text:.4}')
            fig.layout.template = CHART_THEME
            fig.update_traces(textposition='outside')
            fig.update_yaxes(showticklabels=False)
            #fig.update_xaxes(showticklabels=False)
            fig.update_layout(title_x=0.5)
            fig.update_layout(font=dict(size=18))
            fig.show()


            #Comparação as is/ outros cenários -
            #
            # for s1 in s:
            #     df_1 = df_fila_entidades.loc[df_fila_entidades.Scenarios.isin(s1)].reset_index()
            #     fig = px.bar(df_1, x='Scenarios', y='tempo_fila_entidades', color='Process' ,text="tempo_fila_entidades", title= "Process Queue Time by Scenarios", barmode='group')
            #     fig.update_traces(texttemplate='%{text:.4}')
            #     fig.layout.template = CHART_THEME
            #     fig.update_traces(textposition='outside')
            #     fig.update_yaxes(showticklabels=False)
            #     #fig.update_xaxes(showticklabels=False)
            #     fig.update_layout(title_x=0.5)
            #     fig.update_layout(font=dict(size=18))
            #     #fig.show()


            #Comparação as is outros cenários por prioridade!



            #Tempos de fila por processo e por prioridade de paciente - Média geral!
            df_fila_media_prioridade =  df_recursos.groupby(by=['Scenarios', "Patient Priority"]).agg({"Queue Time (Min)": "mean"}).reset_index()
            df_fila_entidades_prioridade = df_recursos.groupby(by=['Scenarios', "Patient Priority"]).agg({"Queue Time (Min)": "mean"}).reset_index()
            df_fila_entidades_prioridade["Queue Time (Min)"] = round(df_fila_entidades_prioridade["Queue Time (Min)"],2)
            fig = px.bar(df_fila_entidades_prioridade, x='Patient Priority', y="Queue Time (Min)", color='Scenarios' ,text="Queue Time (Min)", title= "Process Queue Patient Priority",  barmode='group')
            fig.update_traces(texttemplate='%{text:.4}')
            fig.layout.template = CHART_THEME
            fig.update_traces(textposition='outside')
            fig.update_yaxes(showticklabels=False)
            #fig.update_xaxes(showticklabels=False)
            fig.update_layout(title_x=0.5)
            fig.update_layout(font=dict(size=18))
            fig.show()


            #Versão 2:
            df_fila_media_prioridade =  df_recursos.groupby(by=['Scenarios', "Patient Priority"]).agg({"Queue Time (Min)": "mean"}).reset_index()
            df_fila_entidades_prioridade = df_recursos.groupby(by=['Scenarios', "Patient Priority"]).agg({"Queue Time (Min)": "mean"}).reset_index()
            df_fila_entidades_prioridade["Queue Time (Min)"] = round(df_fila_entidades_prioridade["Queue Time (Min)"],2)
            fig = px.bar(df_fila_entidades_prioridade, x='Scenarios', y="Queue Time (Min)", color='Patient Priority' ,text="Queue Time (Min)", title= "Process Queue Patient Priority")
            fig.update_traces(texttemplate='%{text:.4}')
            fig.layout.template = CHART_THEME
            fig.update_traces(textposition='outside')
            fig.update_yaxes(showticklabels=False)
            #fig.update_xaxes(showticklabels=False)
            fig.update_layout(title_x=0.5)
            fig.update_layout(font=dict(size=18))
            fig.show()

            #Versão 3: - Que está no word:
            df_aux = df_recursos.loc[((df_recursos.Process == ' Clinical Consultation') & (df_recursos["Patient Priority"] == 1))].reset_index()
            df_fila_processo_prioridade_entidade = df_aux.groupby(by=['Scenarios']).agg({"Queue Time (Min)": "mean"}).reset_index() #DF QUE INDICA O KPI DE MÉDIA DE TEMPO DE ESPERA DE PACIENTENTES PRIORIDADE 1 NO CLÍNICO!!

            # for s2 in s:
            #     df = df_fila_processo_prioridade_entidade.loc[((df_fila_processo_prioridade_entidade.Scenarios.isin(s2)) & (df_fila_processo_prioridade_entidade.Process == ' Clinical Consultation')
            #                                                    & (df_fila_processo_prioridade_entidade["Patient Priority"] == 1))]
            #     fig = px.bar(df, x='Patient Priority', y='Queue Time (Min)',
            #                  color='Process',
            #                  text="Queue Time (Min)", title="Process Queue Patient Priority")
            #     fig.update_traces(texttemplate='%{text:.4}')
            #     fig.layout.template = CHART_THEME
            #     fig.update_traces(textposition='outside')
            #     fig.update_yaxes(showticklabels=False)
            #     # fig.update_xaxes(showticklabels=False)
            #     fig.update_layout(title_x=0.5)
            #     fig.update_layout(font=dict(size=18))
            #     fig.show()

            fig = px.bar(df_fila_entidades_prioridade, x='Scenarios', y="Queue Time (Min)", color='Patient Priority' ,text="Queue Time (Min)", title= "Process Queue Patient Priority", barmode='group')
            fig.update_traces(texttemplate='%{text:.4}')
            fig.layout.template = CHART_THEME
            fig.update_traces(textposition='outside')
            fig.update_yaxes(showticklabels=False)
            #fig.update_xaxes(showticklabels=False)
            fig.update_layout(title_x=0.5)
            fig.update_layout(font=dict(size=18))
            fig.show()



            #Paciente, prioridade e recurso
            df_prioridade_paci_recurso = df_recursos.groupby(by=['Scenarios', "Patient Priority", "Process"]).agg({"Queue Time (Min)": "mean"}).reset_index()
            fig = px.bar(df_prioridade_paci_recurso, x='Process', y="Queue Time (Min)", color='Patient Priority' ,text="Queue Time (Min)", title= "Process Queue Patient Priority", barmode='group')
            fig.update_traces(texttemplate='%{text:.4}')
            fig.layout.template = CHART_THEME
            fig.update_traces(textposition='outside')
            fig.update_yaxes(showticklabels=False)
            #fig.update_xaxes(showticklabels=False)
            fig.update_layout(title_x=0.5)
            fig.update_layout(font=dict(size=18))
            fig.show()


            #Média do total de pacientes atendidos por cenário:
            df_pacientes_atendidos = pd.DataFrame(dados_pacientes_atendidos).groupby(by=['Cenário']).agg({"entidades_atendidas": 'mean'}).reset_index()
            df_pacientes_atendidos.rename(columns={"Cenário": "Scenarios", "entidades_atendidas": "Patient Seen"}, inplace=True)
            fig = px.bar(df_pacientes_atendidos, x='Scenarios', y="Patient Seen",
                         text="Patient Seen", title="Patient Seen")

            fig.update_traces(texttemplate='%{text:.4}')
            fig.layout.template = CHART_THEME
            fig.update_traces(textposition='outside')
            fig.update_yaxes(showticklabels=False)
            #fig.update_xaxes(showticklabels=False)
            fig.update_layout(title_x=0.5)
            fig.update_layout(font=dict(size=18))
            fig.show()

            b=0

