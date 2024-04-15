import simpy
import random
import numpy as np
import scipy
import matplotlib
import matplotlib.pyplot as plt
from random import expovariate, seed, normalvariate
from scipy import stats

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

        return dados[processo] #TODO: lembrar como fazer get de 2 níveis!!

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


    #seed(80)
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

    prioridades = {
        "Ficha": None,
        "Triagem": None,
        "Clínico": "prioridade",
        "Pediatra": "prioridade"
    }

    distribuicoes_probabilidade = calcula_distribuicoes_prob()

    recursos = {"Secretária": [2, False],
                "Enfermeira de Triagem": [3,False],
                "Clínico": [4,True],
                "Pediatra": [2,True],
                "Raio-x": [1, True],
                "Eletro": [1, True],
                "Técnica de Enfermagem": [2, True],
                "Espaço para tomar Medicação": [8, True]
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

    warmup = 0

    simulacao = Simulacao(distribuicoes=distribuicoes,
                          imprime=False,
                          recursos=recursos,
                          dist_prob=distribuicoes_probabilidade,
                          tempo=tempo,
                          necessidade_recursos=necessidade_recursos,
                          ordem_processo=ordem_processo,
                          atribuicoes=atribuicoes_processo,
                          liberacao_recurso=liberacao_recursos,
                          warmup = warmup,
                          )

    replicacoes = 1  # corridas * quantidade de dias. Essa é a maneira certa?
     # Pensei em criar essa forma como porcentagem por tempo, mas o artigo simula de forma continua e indica o warmup como 13 semanas
    CorridaSimulacao = CorridaSimulacao(
        replicacoes=replicacoes,
        simulacao=simulacao,
        duracao_simulacao=tempo,
        periodo_warmup=warmup,
        plota_histogramas=True
    )

    CorridaSimulacao.roda_simulacao()
    CorridaSimulacao.fecha_estatisticas_experimento()

