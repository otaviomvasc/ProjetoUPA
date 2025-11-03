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

seed(1)

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
        prioridade = next(
            ent.atributos["prioridade"]
            for ent in lista_entidades
            if paciente == ent.nome
        )
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
    h = mean_se * stats.t.ppf((1 + confidence) / 2.0, n - 1)
    # Intervalo de confiança: mean, +_h
    return h


def cria_planilha(CorridaSimulacao_base, path=""):
    prs = [1, 2, 3, 4, 5, "sem_pr"]
    recursos = [r for r in CorridaSimulacao_base.dados_planilha[0]["dados_tempo"]]
    aba_1 = list()
    aba_2 = list()
    for run in CorridaSimulacao_base.dados_planilha:
        for rec in CorridaSimulacao_base.dados_planilha[run]["dados_tempo"]:
            dc_rec = {
                "Replicacao": run,
                "Name": rec + ".Queue",
                "Type": "Waiting Time",
                "Source": "Queue",
                "Average": (
                    np.mean(
                        CorridaSimulacao_base.dados_planilha[run]["dados_tempo"][rec][
                            "dados_fila"
                        ]
                    )
                    if len(
                        CorridaSimulacao_base.dados_planilha[run]["dados_tempo"][rec][
                            "dados_fila"
                        ]
                    )
                    > 0
                    else 0
                ),
                "BatchMeansHalfWidth": (
                    calc_ic(
                        CorridaSimulacao_base.dados_planilha[run]["dados_tempo"][rec][
                            "dados_fila"
                        ]
                    )
                    if len(
                        CorridaSimulacao_base.dados_planilha[run]["dados_tempo"][rec][
                            "dados_fila"
                        ]
                    )
                    > 0
                    else 0
                ),
                "StDev": (
                    np.std(
                        CorridaSimulacao_base.dados_planilha[run]["dados_tempo"][rec][
                            "dados_fila"
                        ]
                    )
                    if len(
                        CorridaSimulacao_base.dados_planilha[run]["dados_tempo"][rec][
                            "dados_fila"
                        ]
                    )
                    > 0
                    else 0
                ),
                "Minimum": (
                    min(
                        CorridaSimulacao_base.dados_planilha[run]["dados_tempo"][rec][
                            "dados_fila"
                        ]
                    )
                    if len(
                        CorridaSimulacao_base.dados_planilha[run]["dados_tempo"][rec][
                            "dados_fila"
                        ]
                    )
                    > 0
                    else 0
                ),
                "Maximum": (
                    max(
                        CorridaSimulacao_base.dados_planilha[run]["dados_tempo"][rec][
                            "dados_fila"
                        ]
                    )
                    if len(
                        CorridaSimulacao_base.dados_planilha[run]["dados_tempo"][rec][
                            "dados_fila"
                        ]
                    )
                    > 0
                    else 0
                ),
                "NumberObservations": len(
                    CorridaSimulacao_base.dados_planilha[run]["dados_tempo"][rec][
                        "dados_fila"
                    ]
                ),
            }
            aba_1.append(dc_rec)

            dc_number_waiting = {
                "Replicacao": run,
                "Name": rec + ".Queue",
                "Type": "Number Waiting",
                "Source": "Queue",
                "Average": np.mean(
                    CorridaSimulacao_base.dados_planilha[run]["dados_tempo"][rec][
                        "dados_entidade_em_fila"
                    ]
                ),
                "BatchMeansHalfWidth": calc_ic(
                    CorridaSimulacao_base.dados_planilha[run]["dados_tempo"][rec][
                        "dados_entidade_em_fila"
                    ]
                ),
                "Minimum": min(
                    CorridaSimulacao_base.dados_planilha[run]["dados_tempo"][rec][
                        "dados_entidade_em_fila"
                    ]
                ),
                "Maximum": max(
                    CorridaSimulacao_base.dados_planilha[run]["dados_tempo"][rec][
                        "dados_entidade_em_fila"
                    ]
                ),
            }

            aba_2.append(dc_number_waiting)

            dc_utilizacao = {
                "Replicacao": run,
                "Name": rec,
                "Type": "Instantaneous Utilization",
                "Source": "Resource",
                "Average": np.mean(
                    CorridaSimulacao_base.dados_planilha[run]["dados_tempo"][rec][
                        "dados_utilizacao"
                    ]
                ),
                "BatchMeansHalfWidth": calc_ic(
                    CorridaSimulacao_base.dados_planilha[run]["dados_tempo"][rec][
                        "dados_utilizacao"
                    ]
                ),
                "Minimum": min(
                    CorridaSimulacao_base.dados_planilha[run]["dados_tempo"][rec][
                        "dados_utilizacao"
                    ]
                ),
                "Maximum": max(
                    CorridaSimulacao_base.dados_planilha[run]["dados_tempo"][rec][
                        "dados_utilizacao"
                    ]
                ),
            }
            aba_2.append(dc_utilizacao)

        dc_wip = {
            "Replicacao": run,
            "Name": "Pacientes",
            "Type": "WIP",
            "Source": "Entity",
            "Average": CorridaSimulacao_base.dados_planilha[run]["media_WIP"],
            "BatchMeansHalfWidth": CorridaSimulacao_base.dados_planilha[run]["IC_TS"],
            "Minimum": CorridaSimulacao_base.dados_planilha[run]["min_WIP"],
            "Maximum": CorridaSimulacao_base.dados_planilha[run]["max_wip"],
        }

        aba_2.append(dc_wip)

        dc_entity_Total_Time_global = {
            "Replicacao": run,
            "Name": "Paciente",
            "Type": "Total Time",
            "Source": "Entity",
            "Average": np.mean(
                CorridaSimulacao_base.dados_planilha[run]["media_tempo_sistema_total"]
            ),
            "BatchMeansHalfWidth": CorridaSimulacao_base.dados_planilha[run]["IC_TS"],
            "StDev": CorridaSimulacao_base.dados_planilha[run]["desv_pad_TS"],
            "Minimum": CorridaSimulacao_base.dados_planilha[run]["min_TS"],
            "Maximum": CorridaSimulacao_base.dados_planilha[run]["max_TS"],
            "NumberObservations": CorridaSimulacao_base.dados_planilha[run][
                "amostra_TS"
            ],
        }
        aba_1.append(dc_entity_Total_Time_global)

        dc_entity_VA_Time_global = {
            "Replicacao": run,
            "Name": "Paciente",
            "Type": "VA Time",
            "Source": "Entity",
            "Average": np.mean(
                CorridaSimulacao_base.dados_planilha[run]["Dados_TA"]
            ),  # soma das médias os recursos!
            "BatchMeansHalfWidth": calc_ic(
                CorridaSimulacao_base.dados_planilha[run]["Dados_TA"]
            ),
            "StDev": np.std(CorridaSimulacao_base.dados_planilha[run]["Dados_TA"]),
            "Minimum": min(CorridaSimulacao_base.dados_planilha[run]["Dados_TA"]),
            "Maximum": max(CorridaSimulacao_base.dados_planilha[run]["Dados_TA"]),
            "NumberObservations": len(
                CorridaSimulacao_base.dados_planilha[run]["Dados_TA"]
            ),
        }

        aba_1.append(dc_entity_VA_Time_global)

        dc_entity_Waiting_Time_global = {
            "Replicacao": run,
            "Name": "Paciente",
            "Type": "Wait Time",
            "Source": "Entity",
            "Average": np.mean(
                CorridaSimulacao_base.dados_planilha[run]["Dados_Fila"]
            ),  # soma das médias os recursos!
            "BatchMeansHalfWidth": calc_ic(
                CorridaSimulacao_base.dados_planilha[run]["Dados_Fila"]
            ),
            "StDev": np.std(CorridaSimulacao_base.dados_planilha[run]["Dados_Fila"]),
            "Minimum": min(CorridaSimulacao_base.dados_planilha[run]["Dados_Fila"]),
            "Maximum": max(CorridaSimulacao_base.dados_planilha[run]["Dados_Fila"]),
            "NumberObservations": len(
                CorridaSimulacao_base.dados_planilha[run]["Dados_Fila"]
            ),
        }

        aba_1.append(dc_entity_Waiting_Time_global)

    df_aba_1 = pd.DataFrame(aba_1)
    df_aba_2 = pd.DataFrame(aba_2)
    nome_arquivo = "RESULTADOS_FINAIS" + " - " + path + ".xlsx"
    with pd.ExcelWriter(nome_arquivo) as writer:
        df_aba_1.to_excel(writer, sheet_name="DiscreteTimeStatsByRep")
        df_aba_2.to_excel(writer, sheet_name="ContinuousTimeStatsByRep")


def distribuicoes_cen4(processo, slot="None"):
    coef_processos = 60  # Conversão para minutos!!
    coef_chegadas = 60
    coef_checkin = 60
    dados = {
        "Chegada": expovariate(0.0029),
        "Ficha": random.triangular(
            2 * 1 * coef_chegadas, 7 * 1 * coef_chegadas, 4 * 1 * coef_chegadas
        ),
        "Triagem": random.triangular(
            4 * 1.6 * coef_chegadas,
            9 * 1.6 * coef_chegadas,
            7 * 1.6 * coef_chegadas,
        ),
        "Clínico": random.triangular(
            10 * 0.95 * coef_chegadas,
            20 * 0.95 * coef_chegadas,
            15 * 0.95 * coef_chegadas,
        ),
        "Pediatra": random.triangular(
            8 * coef_chegadas, 20 * coef_chegadas, 15 * coef_chegadas
        ),
        "Raio-x": 5 * coef_chegadas,  # Cincominutos
        "Eletro": 12 * coef_chegadas,
        "Exame de Urina": 2 * coef_chegadas,
        "Exame de Sangue": 3 * coef_chegadas,
        "Análise de Sangue Externo": 0.25
        * 60
        * coef_chegadas,  # Quatrohoras,masreduziprameiaho
        "Análise de Sangue Interno": 0.1 * 60 * coef_chegadas,
        "Análise de Urina": 2 * 60 * coef_chegadas,
        "Aplicar Medicação": random.triangular(
            10 * coef_chegadas, 60 * coef_chegadas, 40 * coef_chegadas
        ),
        "Tomar Medicação": random.triangular(
            5 * coef_chegadas, 40 * coef_chegadas, 15 * coef_chegadas
        ),
    }

    return dados[processo]


class Cenario:
    def __init__(self, nome, recursos, distribuicoes):
        self.nome = nome
        self.recursos = recursos
        self.distribuicoes = distribuicoes

    def rodar(
        self,
        dist_probabilidade,
        tempo,
        necessidade_recursos,
        ordem_processo,
        atribuicoes_processo,
        liberacao_recursos,
        warmup,
        replicacoes=55,
        imprime=False,
    ):
        simulacao = Simulacao(
            distribuicoes=self.distribuicoes,
            imprime=imprime,
            recursos=self.recursos,
            dist_prob=dist_probabilidade,
            tempo=tempo,
            necessidade_recursos=necessidade_recursos,
            ordem_processo=ordem_processo,
            atribuicoes=atribuicoes_processo,
            liberacao_recurso=liberacao_recursos,
            warmup=warmup,
        )
        corrida = CorridaSimulacao(
            replicacoes=replicacoes,
            simulacao=simulacao,
            duracao_simulacao=tempo,
            periodo_warmup=warmup,
            plota_histogramas=True,
        )
        corrida.roda_simulacao()
        dados_cenario = corrida.fecha_estatisticas_experimento()
        cria_planilha(corrida, self.nome)
        return dados_cenario


def distribuicoes_base(processo, slot="None"):
    coef_processos = 60  # Conversão para minutos!!
    coef_chegadas = 60
    coef_checkin = 60
    dados = {
        "Chegada": expovariate(0.0029),
        "Ficha": max(0.5, random.lognormvariate(0.460, 0.576)),
        "Triagem": max(0.6, random.lognormvariate(-4.454, 8.946)),
        "Clínico": max(4.53, random.weibullvariate(6.878, 2.832)),
        "Pediatra": max(5.34, random.gauss(14.022, 5.966)),
        "Raio-x": 5 * coef_chegadas,  # Cincominutos
        "Eletro": 12 * coef_chegadas,
        "Exame de Urina": 2 * coef_chegadas,
        "Exame de Sangue": 3 * coef_chegadas,
        "Análise de Sangue Externo": 0.25
        * 60
        * coef_chegadas,  # Quatrohoras,masreduziprameiaho
        "Análise de Sangue Interno": 0.1 * 60 * coef_chegadas,
        "Análise de Urina": 2 * 60 * coef_chegadas,
        "Aplicar Medicação": random.triangular(
            10 * coef_chegadas, 60 * coef_chegadas, 40 * coef_chegadas
        ),
        "Tomar Medicação": random.gauss(35.350, 2.443),
    }

    return dados[processo]


def calcula_distribuicoes_prob():
    def calcula(dados):
        inicio = 0
        list_aux = []
        for dado in dados:
            list_aux.append([inicio, inicio + dado[1], dado[0]])
            inicio = inicio + dado[1]
        return list_aux

        # 1 - clinico e 2 -  pediatra

    classificacao_clinico_pediatra = [["Clínico", 0.78], ["Pediatra", 0.22]]
    # 5 - menos grave e 1 - mais grave
    classificacao_prioridade = [[4, 0.033], [3, 0.70129], [2, 0.150], [1, 0.117]]

    # saida do sistema após o clinico
    decisao_apos_clinico = [
        ["Saída", 0.4],
        ["Aplicar Medicação", 0.2],
        ["Raio-x", 0.1],
        ["Eletro", 0.1],
        ["Exame de Urina", 0.1],
        ["Exame de Sangue", 0.1],
    ]

    decisao_apos_pediatra = [
        ["Saída", 0.4],
        ["Aplicar Medicação", 0.2],
        ["Raio-x", 0.1],
        ["Eletro", 0.1],
        ["Exame de Urina", 0.1],
        ["Exame de Sangue", 0.1],
    ]

    decisao_apos_medicacao = [
        ["Saída", 0.4],
        [
            "medico",
            0.2,
        ],
        ["Raio-x", 0.1],
        ["Eletro", 0.1],
        ["Exame de Urina", 0.1],
        ["Exame de Sangue", 0.1],
    ]

    decisao_apos_urina = [
        ["medico", 0.7],
        ["Raio-x", 0.1],
        ["Eletro", 0.1],
        ["Exame de Sangue", 0.1],
    ]

    decisao_apos_exame_sangue = [
        ["medico", 0.7],
        ["Raio-x", 0.1],
        ["Eletro", 0.1],
        ["Exame de Urina", 0.1],
    ]

    decisao_apos_raio_x = [
        ["medico", 0.7],
        ["Exame de Sangue", 0.1],
        ["Eletro", 0.1],
        ["Exame de Urina", 0.1],
    ]

    decisao_apos_eletro = [
        ["medico", 0.7],
        ["Exame de Sangue", 0.1],
        ["Raio-x", 0.1],
        ["Exame de Urina", 0.1],
    ]

    # Decisao para tempo de espera do resultado do exame de sangue!!!!
    analise_de_sangue = [[0.5 * 60 * 60, 0.5], [0.25 * 60 * 60, 0.5]]

    analise_urina = [[0.25 * 60 * 60, 1]]

    dict_atr = {
        "decide_atendimento": calcula(classificacao_clinico_pediatra),
        "prioridade": calcula(classificacao_prioridade),
        "decisao_apos_clinico": calcula(decisao_apos_clinico),
        "decisao_apos_pediatra": calcula(decisao_apos_pediatra),
        "decisao_apos_raio_x": calcula(decisao_apos_raio_x),
        "decisao_apos_eletro": calcula(decisao_apos_eletro),
        "decisao_apos_urina": calcula(decisao_apos_urina),
        "decisao_apos_exame_sangue": calcula(decisao_apos_exame_sangue),
        "decisao_apos_medicacao": calcula(decisao_apos_medicacao),
        "tempo_resultado_exame_sangue": calcula(analise_de_sangue),
        "tempo_resultado_exame_urina": calcula(analise_urina),
    }

    return dict_atr


if __name__ == "__main__":

    # Dados e parâmetros default em todos os cenários:
    # seed(1000)
    # seed(1)
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
        "Eletro": ["decisao_apos_eletro"],
    }
    tempo = 24 * 60 * 60 * 30 * 1
    necessidade_recursos = {
        "Ficha": ["Secretária"],
        "Triagem": ["Enfermeira de Triagem"],
        "Clínico": ["Clínico"],
        "Pediatra": ["Pediatra"],
        "Raio-x": ["Raio-x"],
        "Exame de Urina": [],
        "Exame de Sangue": ["Técnica de Enfermagem"],
        "Análise de Sangue Externo": [],
        "Análise de Sangue Interno": [],
        "Análise de Urina": [],
        "Aplicar Medicação": ["Técnica de Enfermagem", "Espaço para tomar Medicação"],
        "Tomar Medicação": [],
        "Eletro": ["Eletro"],
    }

    liberacao_recursos = {
        "Ficha": ["Secretária"],
        "Triagem": ["Enfermeira de Triagem"],
        "Clínico": ["Clínico"],
        "Pediatra": ["Pediatra"],
        "Raio-x": ["Raio-x"],
        "Exame de Urina": [],
        "Exame de Sangue": ["Técnica de Enfermagem"],
        "Análise de Sangue Externo": [],
        "Análise de Sangue Interno": [],
        "Análise de Urina": [],
        "Aplicar Medicação": ["Técnica de Enfermagem"],
        "Tomar Medicação": ["Espaço para tomar Medicação"],
        "Eletro": ["Eletro"],
    }

    atribuicoes_processo = {
        "Triagem": "prioridade",
        "Exame de Sangue": "tempo_resultado_exame_sangue",
        "Exame de Urina": "tempo_resultado_exame_urina",
    }

    prioridades = {
        "Ficha": None,
        "Triagem": None,
        "Clínico": "prioridade",
        "Pediatra": "prioridade",
    }

    distribuicoes_probabilidade = calcula_distribuicoes_prob()

    warmup = 5 * 86400
    replicacoes = 30
    recursos_base = {
        "Secretária": [2, False],
        "Enfermeira de Triagem": [2, False],
        "Clínico": [3, True],
        "Pediatra": [2, True],
        "Raio-x": [1, True],
        "Eletro": [1, True],
        "Técnica de Enfermagem": [2, True],
        "Espaço para tomar Medicação": [8, True],
        "Default_Aguarda_Medicacao": [100000, False],
    }  # Recurso default para guardar entidades esperando exames!}

    # Rodada para 1 cenário apenas!!
    simulacao_base = Simulacao(
        distribuicoes=distribuicoes_base,
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
        replicacoes=55,
        simulacao=simulacao_base,
        duracao_simulacao=tempo,
        periodo_warmup=warmup,
        plota_histogramas=True,
    )
    CorridaSimulacao_base.roda_simulacao()
    dados_cenario = CorridaSimulacao_base.fecha_estatisticas_experimento()
