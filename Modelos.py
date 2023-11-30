import simpy
import random
import numpy as np
from scipy import stats
import plotly.express as px
import pandas as pd
from copy import deepcopy
from collections import defaultdict


class Simulacao():
    def __init__(self, distribuicoes, imprime, recursos, dist_prob, tempo, necessidade_recursos, ordem_processo,
                 decisoes, atribuicoes):
        self.env = simpy.Environment()
        self.distribuicoes = distribuicoes
        self.entidades = Entidades()
        self.recursos_est = Recursos(env=self.env,recursos=recursos)  # Foi necessário criar 2x de recursos. Pensar algo melhor!
        self.recursos = self.recursos_est.recursos
        self.estatisticas_sistema = EstatisticasSistema()
        self.imprime_detalhes = imprime
        self.dist_probabilidade = dist_prob
        self.tempo = tempo
        self.necessidade_recursos = necessidade_recursos
        self.proximo_processo = ordem_processo
        self.decisoes = decisoes
        self.atribuicoes_por_processo = atribuicoes

    def comeca_simulacao(self):
        self.env.process(self.gera_chegadas())
        #self.env.run(until=self.tempo) #valor de teste para desenvolvimento!!!!

    def gera_chegadas(self):
        while True:
            yield self.env.timeout(self.distribuicoes(processo='chegada'))

            self.estatisticas_sistema.computa_chegadas(momento=self.env.now)
            entidade_individual = Entidade_individual(nome='entidade' + " " + str(self.estatisticas_sistema.chegadas))
            entidade_individual.entrada_sistema = self.env.now
            self.entidades.lista_entidades.append(entidade_individual)
            self.env.process(self.processo_com_recurso(entidade_individual=entidade_individual, processo="ficha"))


    def processo_com_recurso(self, entidade_individual, processo):

        entidade_individual.entra_fila = self.env.now

        requests_recursos = [self.recursos[recurso_humando].request() if type(self.recursos[recurso_humando]) == simpy.resources.resource.Resource
                             else self.recursos[recurso_humando].request(priority=entidade_individual.atributos['prioridade'])
                             for recurso_humando in self.necessidade_recursos[processo]]


        for request in requests_recursos:
            yield request

        entidade_individual.processo_atual = processo
        if self.imprime_detalhes:
            print(f'{self.env.now}:  Entidade: {entidade_individual.nome} começou o processo {processo}')

        entidade_individual.sai_fila = self.env.now
        entidade_individual.entra_processo = self.env.now  # TODO: esse valor é sempre igual ao sai fila. Logo pode ser uma variável só!

        # delay
        yield self.env.timeout(self.distribuicoes(processo=processo))

        #release
        for i in range(len(self.necessidade_recursos[processo])):
            self.recursos_est.fecha_ciclo(nome_recurso=self.necessidade_recursos[processo][i], momento=self.env.now, inicio_utilizacao=requests_recursos[i].usage_since)
            self.recursos[self.necessidade_recursos[processo][i]].release(requests_recursos[i])


        entidade_individual.sai_processo = self.env.now
        entidade_individual.fecha_ciclo(processo=processo)

        param = self.atribuicoes_por_processo.get(processo, None)
        if param:
            atr = self.retorna_prob(processo=param)
            entidade_individual.atributos[param] = atr if param == "prioridade" else atr + self.env.now


        if entidade_individual.atributos.get("retorno", False):
            proximo_processo = "saida" #Pacientes saem do sistema depois do retorno!

        else:
            proximo_processo = self.decide_proximo_processo(processo=processo, entidade=entidade_individual)

        if not isinstance(proximo_processo, str):
            yield self.env.timeout(proximo_processo) #Aguarda tempo do resultado do exame!!!
            entidade_individual.atributos["prioridade"] = 2  #Pacientes com retorno tem maior prioridade
            entidade_individual.atributos["retorno"] = True
            self.env.process(self.processo_com_recurso(entidade_individual=entidade_individual, processo=entidade_individual.atributos["tipo_atendimento"]))

        if proximo_processo == "saida":
            entidade_individual.saida_sistema = self.env.now
            entidade_individual.fecha_ciclo(processo="saida_sistema")
            self.estatisticas_sistema.computa_saidas(self.env.now)
            if self.imprime_detalhes:
                print(f'{self.env.now}: Entidade {entidade_individual.nome} saiu do sistema!')
        elif isinstance(proximo_processo, str):
            self.env.process(self.processo_com_recurso(entidade_individual=entidade_individual, processo=proximo_processo))


    def retorna_prob(self, processo):
        aleatorio = random.random()
        return next(pr[2] for pr in self.dist_probabilidade[processo] if aleatorio >= pr[0] and aleatorio <= pr[1])

    def decide_proximo_processo(self, processo, entidade):

        proximo_processo = self.proximo_processo[processo]
        if isinstance(proximo_processo, str): #Aqui já vai direto para próximo processo
            return proximo_processo
        else:#Aqui é necessária decisão
            decisao = self.proximo_processo[processo][0]
            aux = self.retorna_prob(decisao)
            if decisao == "decide_atendimento":
                entidade.atributos["tipo_atendimento"] = aux
            if aux == "medico":
                if "tempo_resultado_exame_sangue" in entidade.atributos.keys(): #tempo de espera para resultados do exame de sangue (interno ou externo)
                    tempo_espera =  entidade.atributos["tempo_resultado_exame_sangue"] - self.env.now
                    return tempo_espera
                elif "tempo_resultado_exame_urina" in entidade.atributos.keys(): #tempo de espera para resultados do exame de urina
                    tempo_espera =  entidade.atributos["tempo_resultado_exame_urina"] - self.env.now
                    return tempo_espera

                else:
                    return "clinico"

            return aux


    def finaliza_todas_estatisticas(self):
        self.entidades.fecha_estatisticas()
        self.recursos_est.fecha_estatisticas()
        self.estatisticas_sistema.fecha_estatisticas()

    def gera_graficos(self):
        #Graficos de WIP, entrada e saída

        fig = px.line(self.estatisticas_sistema.df_entidades_brutas,
                      x="discretizacao", y="WIP", title='Grafico de WIP')
        fig.show()


        # GRÁFICOS DE UTILIZAÇÃO
        fig = px.line(self.recursos_est.df_estatisticas_recursos,
                      x="T", y="utilizacao", color="recurso", title='Grafico de Utilizacao Total dos Recursos')
        fig.show()



        #GRÁFICOS TEMPO DE FILA
        df_tempo_fila_time_slot = self.entidades.df_entidades.groupby(by=['processo']).agg({"tempo_fila":"mean"}).reset_index()
        fig = px.bar(df_tempo_fila_time_slot,x='processo', y="tempo_fila", title='Media de tempo em fila por processo')
        fig.show()

        #TODO: Criar análises por cada nível de prioridade!!!


class EstatisticasSistema():
    def __init__(self):
        self.chegadas = 0
        self.saidas = 0
        self.WIP = 0
        self.df_estatisticas_simulacao = pd.DataFrame()
        self.entidades_sistema = list()
        self.df_entidades_brutas = pd.DataFrame()

    def fecha_estatisticas(self):
        print(f'Chegadas: {self.chegadas}')
        print(f'Saídas: {self.saidas}')
        print(f'WIP: {self.WIP} ')
        entidades_sistema = np.mean([rec["WIP"] for rec in self.entidades_sistema]) #TODO: Verificar como esse cálculo ta sendo feito!!
        dict_aux = {"Chegadas": self.chegadas,
                    "Saidas": self.saidas,
                    "WIP": self.WIP,
                    "Media_Sistema": entidades_sistema}

        self.df_entidades_brutas = pd.DataFrame(self.entidades_sistema)
        self.df_estatisticas_simulacao = pd.DataFrame([dict_aux])

    def computa_chegadas(self, momento):
        #TODO: Adaptar para computar chegadas de mais de um indivíduo!!!!
        self.chegadas += 1
        self.WIP += 1
        self.entidades_sistema.append({"discretizacao": momento,
                                       "WIP": self.WIP,
                                       "processo": "chegada"})

    def computa_saidas(self, momento):
        self.saidas += 1
        self.WIP -= 1
        self.entidades_sistema.append({"discretizacao": momento,
                                       "WIP": self.WIP,
                                       "processo": "saida"})

class Entidades:
    def __init__(self):
        self.lista_entidades = list()
        self.df_entidades = pd.DataFrame()
        self.resultados_entidades = pd.DataFrame()

    def fecha_estatisticas(self):
        def printa_media(coluna):
            res = round(np.mean(self.df_entidades[coluna]),2)
            print(f'{coluna} : {res/60} minutos')

        tempo_sistema = list() #TODO:Loop está muito lento. Melhorar!
        self.df_entidades = pd.DataFrame([est for ent in self.lista_entidades for est in ent.estatisticas])


        dict_estatisticas_calculadas = {"tempo_sistema":np.mean([ent.saida_sistema - ent.entrada_sistema for ent in self.lista_entidades if ent.saida_sistema > 1]),
        "tempo_processamento":round(np.mean(self.df_entidades['tempo_processando']),2),
        "tempo_fila" :round(np.mean(self.df_entidades['tempo_fila']),2)}
        printa_media(coluna='tempo_processando')
        printa_media(coluna='tempo_fila')
        print(f'TS: { dict_estatisticas_calculadas["tempo_sistema"] / 60} minutos') #TODO: Prof considerou a média do tempo que as máquinas sairam da manutenção, já que o sistema é continuo. Confirmar como fica em sistemas não-continuos
        self.resultados_entidades = pd.DataFrame([dict_estatisticas_calculadas])

class Entidade_individual(Entidades):
    def __new__(cls, *args, **kwargs):   #Usado para não relacionar um individuo com outro (substituindo o deepcopy)
        return object.__new__(cls)

    def __init__(self, nome):
        self.nome = nome
        self.entra_fila: float = 0.0
        self.sai_fila: float = 0.0
        self.entra_processo: float = 0.0
        self.sai_processo: float = 0.0
        self.estatisticas = list()
        self.entrada_sistema: float = 0.0
        self.saida_sistema: float = 0.0
        self.time_slot = None
        self.tempo_sistema = 0
        self.atributos: defaultdict = {}
        self.processo_atual: str


    def fecha_ciclo(self, processo):
        if not processo == "saida_sistema":
            aux_dados = {"entidade": self.nome,
                         "processo": processo,
                         "entra_fila": self.entra_fila,
                         "sai_fila": self.sai_fila,
                         "tempo_fila": self.sai_fila - self.entra_fila,
                         "entra_processo": self.sai_fila,
                         "sai_processo": self.sai_processo,
                         "tempo_processando": self.sai_processo - self.entra_processo,
                         "time_slot" : self.time_slot}

            self.estatisticas.append(aux_dados)
            self.entra_fila: float = 0.0
            self.sai_fila: float = 0.0
            self.entra_processo: float = 0.0
            self.sai_processo: float = 0.0

        else:
            self.tempo_sistema = self.saida_sistema - self.entrada_sistema

class Recursos:
    def __init__(self, recursos, env):
        self.recursos = self.cria_recursos(recursos, env)
        self.df_estatisticas_recursos = pd.DataFrame()

    def cria_recursos(self, dict_recursos, env):
        recursos_dict = dict()
        for rec, cap in dict_recursos.items():
            if cap[1]:
                rec_aux = simpy.PriorityResource(env,capacity=cap[0])
            else:
                rec_aux = simpy.Resource(env, capacity=cap[0])
            rec_aux.nome = rec
            rec_aux.inicia_utilizacao_recurso = 0
            rec_aux.finaliza_utilizacao_recurso = 0
            rec_aux.utilizacao = 0
            rec_aux.estatisticas = []
            rec_aux.tempo_utilizacao_recurso = 0
            #rec_aux.fecha_ciclo = fecha_ciclo
            recursos_dict[rec] = rec_aux

        return recursos_dict

    def fecha_ciclo(self, nome_recurso, momento, inicio_utilizacao):
        recurso = self.recursos[nome_recurso]
        recurso.tempo_utilizacao_recurso += round(momento - inicio_utilizacao)
        #inicio_utilizacao = request.usage_since
        #TODO: preciso usar o momento ou apenas o fecha_utilizacao_recurso ja tem esse dado, visto que será chamado após processo
        dict_aux = {"recurso": nome_recurso,
                    "inicia_utilizacao_recurso": inicio_utilizacao,
                    "finaliza_utilizacao_recurso": momento,
                    "tempo_utilizacao_recurso": momento - inicio_utilizacao,
                    "utilizacao": recurso.tempo_utilizacao_recurso/(recurso._capacity * momento),
                    "T": momento,
                    "em_atendimento": recurso.count,
                    "tamanho_fila": len(recurso.queue)
                    }

        recurso.estatisticas.append(dict_aux)

    def fecha_estatisticas(self):
        for nome, rec in self.recursos.items():
            df_aux = pd.DataFrame(rec.estatisticas)
            print(f'Utilizacao Média do recurso {nome}: {round(np.mean(df_aux["utilizacao"]),2)*100}%')
            print(f'Média da Fila do recurso {nome}: {round(np.mean(df_aux["tamanho_fila"]) / 60)} minutos')
            df_aux['recurso'] = nome
            self.df_estatisticas_recursos = pd.concat([self.df_estatisticas_recursos, df_aux])
        b=0

class CorridaSimulacao():
    def __init__(self, replicacoes, simulacao: Simulacao, duracao_simulacao, periodo_warmup):
        self.replicacoes: int = replicacoes
        self.df_estatisticas_entidades = pd.DataFrame()  #Lista com cada estatística de cada rodada
        self.df_estatisticas_sistema = pd.DataFrame()
        self.df_estatisticas_recursos = pd.DataFrame()
        self.df_estatistcas_sistemas_brutos = pd.DataFrame()
        self.duracao_simulacao = duracao_simulacao
        self.simulacoes = [deepcopy(simulacao) for i in range(replicacoes)]
        self.periodo_warmup = periodo_warmup
    def roda_simulacao(self):
        for n_sim in range(len(self.simulacoes)):
            print(f'Simulação {n_sim + 1}')
            print('-' * 150)
            simulacao = self.simulacoes[n_sim]
            simulacao.comeca_simulacao()
            simulacao.env.run(until=simulacao.tempo)
            simulacao.finaliza_todas_estatisticas()
            if len(self.simulacoes) == 1:
                simulacao.gera_graficos()

    def fecha_estatisticas_experimento(self):
        def calc_ic(lista):
            confidence = 0.95
            n = len(lista)
            # mean_se: Erro Padrão da Média
            mean_se = stats.sem(lista)
            h = mean_se * stats.t.ppf((1 + confidence) / 2., n - 1)
            # Intervalo de confiança: mean, +_h
            return h
        #Agrupando os dados
        for n_sim in range(len(self.simulacoes)):
            #junção dos dados das entidades
            df_entidades = self.simulacoes[n_sim].entidades.df_entidades
            df_entidades = df_entidades.loc[df_entidades.entra_processo > self.periodo_warmup]
            df_entidades['Replicacao'] = n_sim + 1


            #junção dos dados das estatísticas do sistema
            df_sistema = self.simulacoes[n_sim].estatisticas_sistema.df_estatisticas_simulacao
            df_sistema['Replicacao'] = n_sim + 1

            df_sistema_bruto = self.simulacoes[n_sim].estatisticas_sistema.df_entidades_brutas
            df_sistema_bruto = df_sistema_bruto.loc[df_sistema_bruto.discretizacao > self.periodo_warmup]
            df_sistema_bruto['Replicacao'] = n_sim + 1

            #junção dos dados das estatísticas dos recursos
            df_recursos = self.simulacoes[n_sim].recursos_est.df_estatisticas_recursos
            df_recursos = df_recursos.loc[df_recursos['T'] > self.periodo_warmup]
            df_recursos['Replicacao'] = n_sim + 1


            self.df_estatisticas_entidades = pd.concat([self.df_estatisticas_entidades, df_entidades])
            self.df_estatisticas_sistema = pd.concat([self.df_estatisticas_sistema,df_sistema ])
            self.df_estatisticas_recursos = pd.concat([self.df_estatisticas_recursos, df_recursos])
            self.df_estatistcas_sistemas_brutos = pd.concat([self.df_estatistcas_sistemas_brutos, df_sistema_bruto])


        TS = [(ent.saida_sistema - ent.entrada_sistema)/60 for sim in self.simulacoes for ent in sim.entidades.lista_entidades if ent.saida_sistema > 1]
        TS2 = [(ent.saida_sistema - ent.entrada_sistema)/60 if ent.saida_sistema > 1 else (self.duracao_simulacao - ent.entrada_sistema) for sim in self.simulacoes for ent in sim.entidades.lista_entidades]
        TA = self.df_estatisticas_entidades['tempo_processando']
        TF = self.df_estatisticas_entidades['tempo_fila']
        NA = self.df_estatisticas_recursos['em_atendimento']
        NA2 = self.df_estatisticas_recursos.groupby(by=["recurso"]).agg({'em_atendimento': 'mean'}).reset_index().em_atendimento
        NF = self.df_estatisticas_recursos['tamanho_fila']
        NF2 = self.df_estatisticas_recursos.groupby(by=["recurso"]).agg({'tamanho_fila': 'mean'}).reset_index().tamanho_fila
        NS = self.df_estatistcas_sistemas_brutos["WIP"]
        USO = self.df_estatisticas_recursos['utilizacao']

        TS_ = round(np.mean(TS)/60, 2)
        TS2_ = round(np.mean(TS2)/60,2)
        TA_ = round(np.mean(self.df_estatisticas_entidades['tempo_processando'])/60,2)
        TF_ = round(np.mean(self.df_estatisticas_entidades['tempo_fila'])/60,2)
        NA_ = round(np.mean(self.df_estatisticas_recursos['em_atendimento'])/60,2)
        NA2_ = round(sum(self.df_estatisticas_recursos.groupby(by=["recurso"]).agg({'em_atendimento': 'mean'}).reset_index().em_atendimento),2)
        NF_ = round(np.mean(self.df_estatisticas_recursos['tamanho_fila']),2)
        NF2_ = round(sum(self.df_estatisticas_recursos.groupby(by=["recurso"]).agg({'tamanho_fila': 'mean'}).reset_index().tamanho_fila),2)
        NS_ = round(np.mean(self.df_estatistcas_sistemas_brutos["WIP"]), 2)
        USO_= round(np.mean(self.df_estatisticas_recursos['utilizacao']),2)


        df_aux = self.df_estatistcas_sistemas_brutos.groupby(by=['processo', "Replicacao"]).agg({"WIP": "count"}).reset_index()
        chegadas = np.mean(df_aux.loc[df_aux.processo == 'chegada']['WIP'])
        saidas = np.mean(df_aux.loc[df_aux.processo == 'saida']['WIP'])
        df_wip = self.df_estatistcas_sistemas_brutos.groupby(by=["Replicacao"]).agg({"WIP": "mean"}).reset_index()
        WIP = round(np.mean([self.df_estatistcas_sistemas_brutos["WIP"]]))
        print(f'Chegadas: {chegadas} entidades')
        print(f'Saidas:   {saidas} entidades')
        print(f'WIP:      {WIP} entidades')
        print()
        comprimento_linha = 100
        print("=" * comprimento_linha)
        print("Indicadores de Desempenho do Sistema", end="\n")
        print("=" * comprimento_linha)

        #TODO: Preciso calcular recursos/entidades por processo ?
        print('NS: {0:.2f} \u00B1 {1:.2f} entidades (IC 95%)'.format(np.mean(NS_), calc_ic(NS)))
        print('NF: {0:.2f} \u00B1 {1:.2f} entidades (IC 95%)'.format(np.mean(NF_), calc_ic(NF)))
        print('NF: {0:.2f} \u00B1 {1:.2f} entidades (IC 95%) - FORMA DE CÁLCULO 2'.format(np.mean(NF2_), calc_ic(NF2)))
        print('NA: {0:.2f} \u00B1 {1:.2f} entidades (IC 95%)'.format(np.mean(NA_), calc_ic(NA)))
        print('NA: {0:.2f} \u00B1 {1:.2f} entidades (IC 95%) - FORMA DE CÁLCULO 2'.format(np.mean(NA2_), calc_ic(NA2)))
        print('TS: {0:.2f} \u00B1 {1:.2f} minutos (IC 95%)'.format(np.mean(TS_), calc_ic(TS)))
        print('TS: {0:.2f} \u00B1 {1:.2f} minutos (IC 95%) - FORMA DE CÁLCULO CONSIDERANDO WIPS'.format(np.mean(TS2_), calc_ic(TS2)))
        print('TF: {0:.2f} \u00B1 {1:.2f} minutos (IC 95%)'.format(np.mean(TF_), calc_ic(TF)))
        print('TA: {0:.2f} \u00B1 {1:.2f} minutos (IC 95%)'.format(np.mean(TA_), calc_ic(TA)))
        print('USO:{0:.2f}% \u00B1 {1:.2f}%  (IC 95%)'.format(np.mean(USO) * 100, calc_ic(USO) * 100))
        print("=" * comprimento_linha, end="\n")

        #Calculando os resultados
            #Sempre que houver uma saída de invidiuo
        # NS = Média de individuos - S
        # NA = Fila para o recurso (Salvar informações nos dados do recurso) - .count
        # NF = Tamanho da Fila .queue


        #Média de cada entidade
        #TS: tempo no sistema (valor calculado por entidade)
        #TA: Tempo de atendimento
        #TF: Tempo em fila






