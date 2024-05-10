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


def analises_tempo_artigo():
    # tempo médio espera para ficha e triagem
    tempo_medio_ficha_e_triagem = np.mean(
        self.entidades.df_entidades.loc[((self.entidades.df_entidades.processo == "Ficha") | (
                self.entidades.df_entidades.processo == "Triagem"))]['tempo_fila']) / 60

    tempo_medio_atendimento = np.mean(
        self.entidades.df_entidades.loc[((self.entidades.df_entidades.processo == "Ficha") | (
                self.entidades.df_entidades.processo == "Triagem"))]['tempo_processando']) / 60
    total = tempo_medio_ficha_e_triagem + tempo_medio_atendimento
    print(f'{total} tempo de acolhimento total em minutos')

    # tempo_medio_de_espera_para_pacientes:
    print('-' * 90)
    df_aux = self.entidades.df_entidades.loc[((self.entidades.df_entidades.processo != "Ficha") | (
            self.entidades.df_entidades.processo != "Triagem"))]

    df_tempo_fila_prioridade = df_aux.groupby(by=['prioridade_paciente']).agg(
        {"tempo_fila": "mean"}).reset_index()
    df_tempo_fila_prioridade['tempo_fila'] = round(df_tempo_fila_prioridade['tempo_fila'] / 60, 2)
    print(f'{df_tempo_fila_prioridade =}')


def converte_segundos_em_dias(x):
    return x / 86400


def converte_segundos_em_semanas(x):
    return x / (86400 * 7)


def converte_segundos_em_meses(x):
    return x / (86400 * 30)


if __name__ == "__main__":

    #Dados e parâmetros default em todos os cenários:
    seed(1000)
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

    warmup = 50000
    replicacoes = 16
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
                                  warmup=50000,
                                  )

    CorridaSimulacao_base = CorridaSimulacao(
            replicacoes=5,
            simulacao=simulacao_base,
            duracao_simulacao=tempo,
            periodo_warmup=50000,
            plota_histogramas=True
        )

    CorridaSimulacao_base.roda_simulacao()
    CorridaSimulacao_base.fecha_estatisticas_experimento()
    # CorridaSimulacao_base.df_estatisticas_entidades.to_excel("df_entidades.xlsx")
    # CorridaSimulacao_base.df_estatisticas_recursos.to_excel("df_recursos.xlsx")
    # CorridaSimulacao_base.df_estatistcas_sistemas_brutos.to_excel("df_WIP.xlsx")
    # TS = [(ent.saida_sistema - ent.entrada_sistema) / 60 for sim in CorridaSimulacao_base.simulacoes for ent in
    #               sim.entidades.lista_entidades if ent.saida_sistema > 1]
    # print(f'Media: {round(np.mean(TS),2)}, Mediana {round(np.median(TS),2)}, Moda {round(statistics.mode(TS),2)}')

    #Unicos pontos que iremos alterar a principio na geração de cenários será os recursos e tempos de processo!

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
        # Cenário 1: Diminuindo uma secretária
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
            replicacoes=53, #replicacoes,
            simulacao=simulacao_cenario,
            duracao_simulacao=tempo,
            periodo_warmup=warmup,
            plota_histogramas=True
        )
        CorridaSimulacao_cenario.roda_simulacao()
        CorridaSimulacao_cenario.fecha_estatisticas_experimento()
        CorridaSimulacao_cenario.df_estatistcas_sistemas_brutos['cenario'] = cen
        CorridaSimulacao_cenario.df_estatisticas_entidades['cenario'] = cen
        CorridaSimulacao_cenario.df_estatisticas_recursos['cenario'] = cen

        corridas.append(copy.copy(CorridaSimulacao_cenario))
        estatisticas_finais[cen] = {"Atendimentos":CorridaSimulacao_cenario.numero_atendimentos,
                                    "utilizacao_media": CorridaSimulacao_cenario.utilizacao_media,
                                    "utilizacao_media_por_recurso": CorridaSimulacao_cenario.utilizacao_media_por_recurso,
                                    "media_tempo_fila_geral": CorridaSimulacao_cenario.media_em_fila_geral,
                                    "media_fila_por_prioridade": CorridaSimulacao_cenario.df_media_fila_por_prioridade,
                                    "dados_hist_entidades": CorridaSimulacao_cenario.dados}


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

    df_estatisticas_bruto = pd.DataFrame()
    df_recursos = pd.DataFrame()
    df_entidades = pd.DataFrame()
    nome_cenario = [c for c in cenarios]
    for cor in corridas:
        df_estatisticas_bruto = pd.concat([df_estatisticas_bruto, cor.df_estatistcas_sistemas_brutos])
        df_recursos = pd.concat([df_recursos, cor.df_estatisticas_recursos])
        df_entidades = pd.concat([df_entidades, cor.df_estatisticas_entidades])



    graficos_de_todas_as_replicacoes_juntas = False
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
            "Eletro": "Electrocardiogram",
            "chegada": "Arrive",
            "saida": "Exit",
            "Aguarda Resultado de Exame": "Waiting Examination Results"
        }

        df_total_pacientes.rename(columns={"Cenario": "Scenarios", "Atendimentos": "Patients Seen"}, inplace=True)
        df_utilizacao_media.rename(columns={"Cenario": "Scenarios", "Utilização": "Resources Usage (%)"}, inplace=True)
        df_fila_media.rename(columns={"Cenario": "Scenarios", "Tempo_Médio_de_Fila": "Queue Average Time (Min)"} ,inplace=True)
        df_utilizacao_por_recurso.rename(columns={"recurso": "Resource", "utilizacao" : "Resources Usage (%)", "Cenário": "Scenarios"}, inplace=True)
        df_utilizacao_por_recurso['Resource'] = df_utilizacao_por_recurso.Resource.apply(lambda x: dicionario_traduzido_recursos[x])
        df_filas_por_prioridade.rename(columns={"prioridade": "Patient Priority", "media_minutos": "Queue Average (Min)",  "Cenário": "Scenarios"},inplace=True)
        df_estatisticas_bruto.rename(columns={'cenario': "Scenarios", "Replicacao": "Run"}, inplace=True)
        df_recursos.rename(columns={'cenario': "Scenarios", "recurso": "Resource", "utilizacao" : "Resources Usage (%)",  "Replicacao": "Run"}, inplace=True)
        df_recursos['Resource'] = df_recursos.Resource.apply(lambda x: dicionario_traduzido_recursos[x])
        df_entidades.rename(columns={"entidade": "Entity", "processo": "Process", 'prioridade': "Patient Priority", 'cenario': "Scenarios"}, inplace=True)
        df_entidades["Process"] = df_entidades["Process"].apply(lambda x: dicionario_traduzido_processos[x])
        df_entidades['Queue Time (Min)'] =  round(df_entidades.tempo_fila/60,2)
        CHART_THEME = 'plotly_white'

        #Gerar gráficos de cada simulação para todas as corridas!!
        #Gráfico WIP!

        df_estatisticas_bruto['Scenario-Run'] = df_estatisticas_bruto.apply(lambda x: x.Scenarios + " - " + "Run " +str(x.Run), axis=1)
        df_scenario_run_WIP = df_estatisticas_bruto.groupby(by=['Scenario-Run', 'discretizacao', 'Scenarios']).agg({"WIP": "mean"}).reset_index()
        duracao_dias_sr = [converte_segundos_em_dias(x) for x in
                          df_scenario_run_WIP.discretizacao]
        fig = px.line(df_scenario_run_WIP, x=duracao_dias_sr, y=df_scenario_run_WIP.WIP, color="Scenarios")
        fig.update_layout(title='Global Average Entities in Process (WIP)')
        fig.update_xaxes(title='Duration (D)', showgrid=False)
        fig.update_yaxes(title='Number os Patients')
        fig.layout.template = CHART_THEME
        fig.update_layout(title_x=0.5)

        fig.show()


        df_recursos['Scenario-Run'] = df_recursos.apply(lambda x: x.Scenarios + " - " + "Run " + str(x.Run), axis = 1)
        df_recursos['Scenario-Run-Resource'] = df_recursos.apply(lambda x: x.Scenarios + " - " + "Run " + str(x.Run) + x.Resource, axis=1)
        df_recursos['Scenario-Resource'] = df_recursos.apply(lambda x: x.Scenarios + " - "  +  x.Resource, axis=1)
        #Média de todos os recursos por replicação!!!
        df_rec_scenario_run = df_recursos.groupby(by=['Scenario-Resource', 'T', 'Resource']).agg({"Resources Usage (%)": "mean"}).reset_index()
        fig = px.line(df_rec_scenario_run,
                      x="T", y="Resources Usage (%)", color="Scenario-Resource", title='Resources Utilization') #hover_data='Scenario-Resource')
        fig.layout.template = CHART_THEME
        fig.update_xaxes(title='Duration (D)', showgrid=False)
        # fig.update_yaxes(title='Utilização dos Recursos (%)')
        fig.update_layout(title_x=0.5)
        fig.show()

        if graficos_de_todas_as_replicacoes_juntas:
            media_de_todas_as_replicações = True
            #Teste:
            if media_de_todas_as_replicações:
                df = df_estatisticas_bruto.groupby(by=['Scenarios', 'discretizacao']).agg({"WIP": "mean"}).reset_index()
                duracao_dias_2 = [converte_segundos_em_dias(x) for x in
                                df.discretizacao]

                fig = px.line(df, x=duracao_dias_2, y=df.WIP, color="Scenarios")
                fig.update_layout(title='Global Average Entities in Process (WIP)')
                fig.update_xaxes(title='Duration (D)', showgrid=False)
                fig.update_yaxes(title='Number os Patients')
                fig.layout.template = CHART_THEME
                fig.update_layout(title_x=0.5)

                fig.show()

                df_2 = df_recursos.groupby(by=['Scenarios', 'Resource', 'T']).agg({"Resources Usage (%)": "mean"}).reset_index()
                fig = px.line(df_2,
                              x="T", y="Resources Usage (%)", color="Resource", title='Resources Utilization')
                fig.layout.template = CHART_THEME
                fig.update_xaxes(title='Duration (D)', showgrid=False)
                # fig.update_yaxes(title='Utilização dos Recursos (%)')
                fig.update_layout(title_x=0.5)
                fig.show()

            else:
                duracao_dias = [converte_segundos_em_dias(x) for x in
                                df_estatisticas_bruto.discretizacao]
                fig = px.line(df_estatisticas_bruto, x=duracao_dias, y=df_estatisticas_bruto.WIP, color="Scenarios")
                fig.update_layout(title='Entities in Process (WIP)')
                fig.update_xaxes(title='Duration (D)', showgrid=False)
                fig.update_yaxes(title='Number os Patients')
                fig.layout.template = CHART_THEME
                #fig.layout.width = 1000
                fig.update_layout(title_x=0.5)

                fig.show()


            #Utilização dos recursos no tempo!
            fig = px.line(df_recursos,
                          x="T", y="Resources Usage (%)", color="Resource", title='Resources Utilization')
            fig.layout.template = CHART_THEME
            fig.update_xaxes(title='Duration (D)', showgrid=False)
            #fig.update_yaxes(title='Utilização dos Recursos (%)')
            fig.update_layout(title_x=0.5)
            fig.show()

        else:
            for cen in cenarios:
                df_estatisticas_aux = df_estatisticas_bruto.loc[df_estatisticas_bruto.Scenarios == cen]
                df_recursos_aux = df_recursos.loc[df_recursos.Scenarios == cen]
                df_entidades_aux = df_entidades.loc[df_entidades.Scenarios == cen]
                duracao_dias = [converte_segundos_em_dias(x) for x in df_estatisticas_aux.discretizacao]
                fig = px.line(df_estatisticas_aux, x=duracao_dias, y=df_estatisticas_aux.WIP, color=df_estatisticas_aux["Run"])
                fig.update_layout(title=f'Entities in Process (WIP) Scenario {cen}')
                fig.update_xaxes(title='Duration (D)', showgrid=False)
                fig.update_yaxes(title='Number os Patients')
                fig.layout.template = CHART_THEME
                #fig.layout.width = 1000
                fig.update_layout(title_x=0.5)

                fig.show()

                #Utilização dos recursos no tempo!

                fig = px.line(df_recursos_aux,
                              x="T", y="Resources Usage (%)", color="Resource", title=f'Resources Utilization Scenario {cen}')
                fig.layout.template = CHART_THEME
                fig.update_xaxes(title='Duration (D)', showgrid=False)
                #fig.update_yaxes(title='Utilização dos Recursos (%)')
                fig.update_layout(title_x=0.5)
                fig.show()

                #Média tempo fila por prioridade e processo
                df_tempo_fila_prioridade = df_entidades_aux.groupby(by=['Process', "Patient Priority"]).agg({"Queue Time (Min)": "mean"}).reset_index()
                df_tempo_fila_prioridade["Queue Time (Min)"] = round(df_tempo_fila_prioridade["Queue Time (Min)"], 2)
                fig = px.bar(df_tempo_fila_prioridade, x='Patient Priority', y='Queue Time (Min)', color='Process', text="Queue Time (Min)", title=f"Process Queue Patient Priority in Scenario {cen}")

                fig.update_traces(texttemplate='%{text}')
                fig.layout.template = CHART_THEME
                fig.update_traces(textposition='outside')
                fig.update_yaxes(showticklabels=False)
                #fig.update_xaxes(showticklabels=False)
                fig.update_layout(title_x=0.5)
                fig.show()
                b=0

        #Tempo médio e fila por processo
        df_tempo_fila_processo = df_entidades.groupby(by=['Scenarios', "Process"]).agg({"Queue Time (Min)": "mean"}).reset_index()
        df_tempo_fila_processo["Queue Time (Min)"] = round(df_tempo_fila_processo["Queue Time (Min)"],2)
        fig = px.bar(df_tempo_fila_processo, x='Process', y='Queue Time (Min)', color='Scenarios' ,text="Queue Time (Min)", title= "Process Queue Time by Scenarios")
        fig.update_traces(texttemplate='%{text}')
        fig.layout.template = CHART_THEME
        fig.update_traces(textposition='outside')
        fig.update_yaxes(showticklabels=False)
        #fig.update_xaxes(showticklabels=False)
        fig.update_layout(title_x=0.5)
        fig.show()


        #Tempo médio de fila por prioridade!
        df_tempo_fila_prioridade = df_entidades.groupby(by=['Scenarios', "Patient Priority"]).agg({"Queue Time (Min)": "mean"}).reset_index()
        df_tempo_fila_prioridade["Queue Time (Min)"] = round(df_tempo_fila_prioridade["Queue Time (Min)"],2)
        fig = px.bar(df_tempo_fila_prioridade, x='Patient Priority', y='Queue Time (Min)', color='Scenarios' ,text="Queue Time (Min)", title= "Process Queue Patient Priority")
        fig.update_traces(texttemplate='%{text}')
        fig.layout.template = CHART_THEME
        fig.update_traces(textposition='outside')
        fig.update_yaxes(showticklabels=False)
        #fig.update_xaxes(showticklabels=False)
        fig.update_layout(title_x=0.5)
        fig.show()


        #total de pacientes atendidos!
        fig = px.bar(df_total_pacientes, x='Scenarios', y='Patients Seen', text="Patients Seen",  title="Patients Seen by Scenarios")
        fig.update_traces(texttemplate='%{text}')
        fig.layout.template = CHART_THEME
        fig.update_traces(textposition='outside')
        fig.update_yaxes(showticklabels=False)
        fig.update_xaxes(showticklabels=False)
        fig.update_layout(title_x=0.5)
        fig.show()


        #Utiização Média de Recursos
        fig = px.bar(df_utilizacao_por_recurso, x='Resource', y='Resources Usage (%)', color='Scenarios', barmode='group',
                     text='Resources Usage (%)', title='Average Utilization Resources in Scenarios')  # text="nation"
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
                     text='Resources Usage (%)', title='Average Utilization Resources in Scenarios')  # text="nation"
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
                     text='Queue Average (Min)', title='Patient Queues by Priority in Scenarios')  # text="nation"
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
        try:
            CHART_THEME = 'plotly_white'
            fig = px.bar(df_total_pacientes, x='Scenarios', y='Patients Seen', text="Patients Seen",  title="Patients Seen by Scenarios")
            fig.update_traces(texttemplate='%{text}')
            fig.layout.template = CHART_THEME
            fig.update_traces(textposition='outside')
            fig.update_yaxes(showticklabels=False)
            fig.update_xaxes(showticklabels=False)
            fig.update_layout(title_x=0.5)
            fig.show()
            #Utilização geral média
            fig = px.bar(df_utilizacao_media, x='Cenario', y='Utilização')
            fig.show()
        except:
            b=0
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

