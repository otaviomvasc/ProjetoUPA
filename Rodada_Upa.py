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
        dados = {"chegada":expovariate(0.0029),
                 "ficha": random.triangular(2*2.12*coef_chegadas, 7*2.12*coef_chegadas, 4*2.12*coef_chegadas),
                 "triagem": random.triangular(4*1.6*coef_chegadas, 9 * 1.6 * coef_chegadas, 7 * 1.6 * coef_chegadas),
                 "clinico": random.triangular(10*1*coef_chegadas, 20 * 1* coef_chegadas, 15 * 1* coef_chegadas),
                 "pediatra": random.triangular(8*coef_chegadas, 20 * coef_chegadas, 15 * coef_chegadas),
                 "raio-x": 5 * coef_chegadas, #Cinco minutos
                 "eletro": 12 * coef_chegadas,
                 "urina": 2 * coef_chegadas,
                 "exame_sangue": 3 * coef_chegadas,
                 "analise_sangue_externo":  0.25 * 60 * coef_chegadas, #Quatro horas, mas reduzi pra meia ho
                 "analise_sangue_interno": 0.1 * 60 * coef_chegadas,
                 "analise_urina": 2 * 60 * coef_chegadas,
                 "aplicar_medicacao": random.triangular(10*coef_chegadas, 60 * coef_chegadas, 40 * coef_chegadas),
                 "tomar_medicacao": random.triangular(5*coef_chegadas, 40 * coef_chegadas, 15 * coef_chegadas),
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

        classificacao_clinico_pediatra = [["clinico", 0.74],
                                          ["pediatra", 0.26]]
        # 5 - menos grave e 1 - mais grave
        classificacao_prioridade = [[5, 0.032],
                                    [4, 0.001],
                                    [3, 0.70129],
                                    [2, 0.150],
                                    [1, 0.117]]

        #saida do sistema após o clinico
        decisao_apos_clinico = [["saida", 0.4],
                                      ["aplicar_medicacao", 0.2],
                                      ["raio-x", 0.1],
                                      ["eletro", 0.1],
                                      ["urina", 0.1],
                                      ["exame_sangue", 0.1]]

        decisao_apos_pediatra = [["saida", 0.4],
                                      ["aplicar_medicacao", 0.2],
                                      ["raio-x", 0.1],
                                      ["eletro", 0.1],
                                      ["urina", 0.1],
                                      ["exame_sangue", 0.1]]

        decisao_apos_medicacao = [["saida", 0.4],
                                  ["medico", 0.2], #TODO: E O PACIENTE QUE VEM DO PEDIATRA E TOMA MEDICAÇÃO? COMO ELE VAI VOLTAR PARA LÁ?
                                  ["raio-x", 0.1],
                                  ["eletro", 0.1],
                                  ["urina", 0.1],
                                  ["exame_sangue", 0.1]
                                  ]

        decisao_apos_urina = [["medico", 0.7],
                              ["raio-x", 0.1],
                              ["eletro", 0.1],
                              ["exame_sangue", 0.1]
                              ]

        decisao_apos_exame_sangue = [["medico", 0.7],
                              ["raio-x", 0.1],
                              ["eletro", 0.1],
                              ["urina", 0.1]
                              ]

        decisao_apos_raio_x = [["medico", 0.7],
                             ["exame_sangue", 0.1],
                             ["eletro", 0.1],
                             ["urina", 0.1]
                                             ]

        decisao_apos_eletro = [["medico", 0.7],
                             ["exame_sangue", 0.1],
                             ["raio-x", 0.1],
                             ["urina", 0.1]]

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
        "ficha": "triagem",
        "triagem": ["decide_atendimento"],
        "clinico": ["decisao_apos_clinico"],
        "pediatra": ["decisao_apos_pediatra"],
        "aplicar_medicacao": "tomar_medicacao",
        "tomar_medicacao": ["decisao_apos_medicacao"],
        "urina": ["decisao_apos_urina"],
        "exame_sangue": ["decisao_apos_exame_sangue"],
        "analise_urina": "medico",
        "raio-x": ["decisao_apos_raio_x"],
        "eletro": ["decisao_apos_eletro"]
    }

    prioridades = {
        "ficha": None,
        "triagem": None,
        "clinico": "prioridade",
        "pediatra": "prioridade"
    }

    distribuicoes_probabilidade = calcula_distribuicoes_prob()

    recursos = {"secretaria": [2, False],
                "enfermeira_triagem": [3,False],
                "clinico": [4,True],
                "pediatra": [2,True],
                "raio-x": [1, True],
                "eletro": [1, True],
                "tecnica_enfermagem": [2, True],
                "espaco_medicacao": [8, True]
                }

    tempo = 24 * 60 * 60 * 30
    necessidade_recursos = {"ficha": ["secretaria"],
                            "triagem": ["enfermeira_triagem"],
                            "clinico": ["clinico"],
                            "pediatra": ["pediatra"],
                            "raio-x" : ["raio-x"],
                            "urina" : [],
                            "exame_sangue": ["tecnica_enfermagem"],
                            "analise_sangue_externo": [],
                            "analise_sangue_interno": [],
                            "analise_urina": [],
                            "aplicar_medicacao": ["tecnica_enfermagem", "espaco_medicacao"],
                            "tomar_medicacao" : [],
                            "eletro": ["eletro"]
                            }

    liberacao_recursos = {"ficha": ["secretaria"],
                            "triagem": ["enfermeira_triagem"],
                            "clinico": ["clinico"],
                            "pediatra": ["pediatra"],
                            "raio-x" : ["raio-x"],
                            "urina" : [],
                            "exame_sangue": ["tecnica_enfermagem"],
                            "analise_sangue_externo": [],
                            "analise_sangue_interno": [],
                            "analise_urina": [],
                            "aplicar_medicacao": ["tecnica_enfermagem"],
                            "tomar_medicacao" : ["espaco_medicacao"], #TODO: pensar em como fazer para liberar apenas 1 requests para liberar apenas a medicação!
                            "eletro": ["eletro"]
                            }

    atribuicoes_processo = {"triagem": "prioridade",
                            "exame_sangue": "tempo_resultado_exame_sangue",
                            "urina": "tempo_resultado_exame_urina"
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

    replicacoes = 10  # corridas * quantidade de dias. Essa é a maneira certa?
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