import simpy
import random
import numpy as np
import scipy
import matplotlib
import matplotlib.pyplot as plt
from random import expovariate, seed, normalvariate
from scipy import stats

from Modelos import *



if __name__ == "__main__":


    def distribuicoes(processo, slot="None"):
        coef_processos = 60 #Conversão para minutos!!
        coef_chegadas = 60
        coef_checkin = 60
        dados = {"chegada":expovariate(1/(1.7 * coef_chegadas)),
                 "ficha": random.triangular(2*coef_chegadas, 7*coef_chegadas, 4*coef_chegadas),
                 "triagem": random.triangular(4*coef_chegadas, 9 * coef_chegadas, 7 * coef_chegadas),
                 "clinico": random.triangular(5*coef_chegadas, 15 * coef_chegadas, 10 * coef_chegadas),
                 "pediatra": random.triangular(8*coef_chegadas, 20 * coef_chegadas, 15 * coef_chegadas),
                 "raio-x": 5 * coef_chegadas,
                 "eletro": 12 * coef_chegadas,
                 "urina": 2 * coef_chegadas,
                 "exame_sangue": 3 * coef_chegadas,
                 "analise_sangue_externo":  4 * 60 * coef_chegadas,
                 "analise_sangue_interno": 2 * 60 * coef_chegadas,
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

        classificacao_clinico_pediatra = [["clinico", 0.7],
                                          ["pediatra", 0.3]]
        # 5 - menos grave e 1 - mais grave
        classificacao_prioridade = [[5, 0.719],
                                    [4, 0.038],
                                    [3, 0.028],
                                    [2, 0.172],
                                    [1, 0.075]]

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
        analise_de_sangue = [[4 * 60 * 60, 0.5],
                             [2 * 60 * 60, 0.5]]

        analise_urina = [[2 * 60 * 60, 1]]


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
                "enfermeira_triagem": [2,False],
                "clinico": [3,True],
                "pediatra": [3,True],
                "raio-x": [1, True],
                "eletro": [1, True],
                "tecnica_enfermagem": [2, True],
                "espaco_medicacao": [8, True]
                }

    tempo = 24 * 60 * 60
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
                            "aplicar_medicacao": ["espaco_medicacao", "tecnica_enfermagem"],
                            "tomar_medicacao" : ["tecnica_enfermagem"], #TODO: pensar em como fazer para liberar apenas 1 requests para liberar apenas a medicação!
                            "eletro": ["eletro"]
                            }

    atribuicoes_processo = {"triagem": "prioridade",
                            "exame_sangue": "tempo_resultado_exame_sangue",
                            "urina": "tempo_resultado_exame_urina"
                        }

    seed(1)
    simulacao = Simulacao(distribuicoes=distribuicoes,
                          imprime=True,
                          recursos=recursos,
                          dist_prob=distribuicoes_probabilidade,
                          tempo=tempo,
                          necessidade_recursos=necessidade_recursos,
                          ordem_processo=ordem_processo,
                          decisoes={},
                          atribuicoes=atribuicoes_processo
                          )

    replicacoes = 1  # corridas * quantidade de dias. Essa é a maneira certa?
    warmup = 0  # Pensei em criar essa forma como porcentagem por tempo, mas o artigo simula de forma continua e indica o warmup como 13 semanas
    CorridaSimulacao = CorridaSimulacao(
        replicacoes=replicacoes,
        simulacao=simulacao,
        duracao_simulacao=tempo,
        periodo_warmup=warmup
    )

    CorridaSimulacao.roda_simulacao()