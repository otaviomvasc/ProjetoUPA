import simpy
import random
import numpy as np
from scipy import stats
import plotly.express as px
import pandas as pd
from copy import deepcopy
from collections import defaultdict
import plotly.graph_objects as go


class Simulacao():
    def __init__(self, distribuicoes, imprime, recursos, dist_prob, tempo, necessidade_recursos, ordem_processo,
                  atribuicoes, liberacao_recurso, warmup=0):
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
        self.atribuicoes_por_processo = atribuicoes
        self.recursos_liberados_processo = liberacao_recurso
        self.warmup=warmup
        self.converte_dias = 86400

    def comeca_simulacao(self):
        self.env.process(self.gera_chegadas())
        #self.env.run(until=self.tempo) #valor de teste para desenvolvimento!!!!

    def gera_chegadas(self):
        while True:
            yield self.env.timeout(self.distribuicoes(processo='Chegada'))

            self.estatisticas_sistema.computa_chegadas(momento=self.env.now)
            entidade_individual = Entidade_individual(nome='entidade' + " " + str(self.estatisticas_sistema.chegadas))
            entidade_individual.entrada_sistema = self.env.now
            self.entidades.lista_entidades.append(entidade_individual)
            self.env.process(self.processo_com_recurso(entidade_individual=entidade_individual, processo="Ficha"))

    def processo_com_recurso(self, entidade_individual, processo):

        entidade_individual.entra_fila = self.env.now

        #TODO: alterei o get para primeiro buscar se tem prioridade retorno.Caso não exista a chave no dicionario de atributos, buscara a prioridade de atendimento normal. Optei por deixar explicito!
        requests_recursos = [self.recursos[recurso_humando].request() if type(self.recursos[recurso_humando]) == simpy.resources.resource.Resource
                             else self.recursos[recurso_humando].request(priority=entidade_individual.atributos.get("prioridade_retorno",entidade_individual.atributos.get('prioridade', 5)))
                             for recurso_humando in self.necessidade_recursos[processo]]

        entidade_individual.lista_requests.extend(requests_recursos) #Salvando requests na entidade para conseguir liberar um request em outro processo!!
        for request in requests_recursos:
            yield request

        entidade_individual.processo_atual = processo
        if self.imprime_detalhes:
            print(f'{self.env.now}:  Entidade: {entidade_individual.nome} começou o processo {processo}')

        entidade_individual.sai_fila = self.env.now
        entidade_individual.entra_processo = self.env.now # TODO: esse valor é sempre igual ao sai fila. Logo pode ser uma variável só!

        # delay
        yield self.env.timeout(self.distribuicoes(processo=processo))

        #release
        for rec in self.recursos_liberados_processo[processo]: #também deletar da entidade o requests e não buscar mais pelo request_recursos
            req_recurso_liberado = next(req_recurso for req_recurso in entidade_individual.lista_requests if rec == req_recurso.resource.nome)
            self.recursos_est.fecha_ciclo(nome_recurso=rec,momento=self.env.now, inicio_utilizacao=req_recurso_liberado.usage_since, converte_dias = self.converte_dias)
            self.recursos[rec].release(req_recurso_liberado)
            entidade_individual.lista_requests.remove(req_recurso_liberado) #Manter requests para serem removidos em outros métodos


        entidade_individual.sai_processo = self.env.now
        entidade_individual.fecha_ciclo(processo=processo)

        param = self.atribuicoes_por_processo.get(processo, None)
        if param:
            atr = self.retorna_prob(processo=param)
            entidade_individual.atributos[param] = atr if param == "prioridade" else atr + self.env.now


        if entidade_individual.atributos.get("retorno", False):
            proximo_processo = "Saída" #Pacientes saem do sistema depois do retorno!

        else:
            proximo_processo = self.decide_proximo_processo(processo=processo, entidade=entidade_individual)

        if not isinstance(proximo_processo, str):
            #Fila para aguardar resulltado do exame!
            entidade_individual.entra_fila = self.env.now
            entidade_individual.processo_atual = "Aguarda Resultado de Exame"
            yield self.env.timeout(proximo_processo) #Aguarda tempo do resultado do exame!!!
            entidade_individual.atributos["prioridade_retorno"] = 3  #Pacientes com retorno tem maior prioridade - Verificar se saída dos outros exames está sendo setado!!!
            entidade_individual.atributos["retorno"] = True
            entidade_individual.sai_fila = self.env.now
            entidade_individual.fecha_ciclo(processo="Aguarda Resultado de Exame")
            self.env.process(self.processo_com_recurso(entidade_individual=entidade_individual, processo=entidade_individual.atributos["tipo_atendimento"]))

        if proximo_processo == "Saída":
            entidade_individual.saida_sistema = self.env.now
            entidade_individual.processo_atual = "Saída"
            entidade_individual.fecha_ciclo(processo="Saída")
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
            while True:
                aux = self.retorna_prob(decisao)
                if aux not in [ent['processo'] for ent in entidade.estatisticas]:
                    break
            if decisao == "decide_atendimento":
                entidade.atributos["tipo_atendimento"] = aux
            if aux == "medico":
                entidade.atributos["retorno"] = True
                entidade.atributos["prioridade_retorno"] = 3 #Pacientes que já fizeram seus exames e agora vão fazer retorno para o médico e depois saem do sistema
                if "tempo_resultado_exame_sangue" in entidade.atributos.keys(): #tempo de espera para resultados do exame de sangue (interno ou externo)
                    tempo_espera =  entidade.atributos["tempo_resultado_exame_sangue"] - self.env.now if  self.env.now < entidade.atributos["tempo_resultado_exame_sangue"] else 0
                    return tempo_espera
                elif "tempo_resultado_exame_urina" in entidade.atributos.keys(): #tempo de espera para resultados do exame de urina
                    tempo_espera =  entidade.atributos["tempo_resultado_exame_urina"] - self.env.now if  self.env.now < entidade.atributos["tempo_resultado_exame_urina"] else 0
                    return tempo_espera
                else:
                    return entidade.atributos['tipo_atendimento']

            return aux

    def finaliza_todas_estatisticas(self):
        self.entidades.fecha_estatisticas(warmup=self.warmup, nec_recursos = self.necessidade_recursos)
        self.recursos_est.fecha_estatisticas(warmup=self.warmup, df_entidades=self.entidades.df_entidades)
        self.estatisticas_sistema.fecha_estatisticas(warmup=self.warmup)

    def gera_graficos(self,n, plota):
        #Graficos de WIP, entrada e saída
        def retorna_prioridade(paciente, lista_entidades):
            try:
                prioridade = next(ent.atributos['prioridade'] for ent in lista_entidades if paciente == ent.nome)
                return prioridade
            except KeyError:
                return "Nao Passou da Triagem"

        def analises_tempo_artigo():
            #tempo médio espera para ficha e triagem
            tempo_medio_ficha_e_triagem = np.mean(self.entidades.df_entidades.loc[((self.entidades.df_entidades.processo == "ficha") | (
                        self.entidades.df_entidades.processo == "triagem"))]['tempo_fila'])/60
            print(f'{tempo_medio_ficha_e_triagem = } minutos')

            #tempo_medio_de_espera_para_pacientes:
            print('-' * 90)
            df_aux = self.entidades.df_entidades.loc[((self.entidades.df_entidades.processo != "ficha") | (
                        self.entidades.df_entidades.processo != "triagem"))]

            df_tempo_fila_prioridade = df_aux.groupby(by=['prioridade_paciente']).agg(
                {"tempo_fila": "mean"}).reset_index()
            print(f'{df_tempo_fila_prioridade =}')

        def converte_segundos_em_dias(x):
            return x / 86400

        def converte_segundos_em_semanas(x):
            return x / (86400*7)

        def converte_segundos_em_meses(x):
            return x / (86400*30)

        self.entidades.df_entidades['prioridade_paciente'] = self.entidades.df_entidades.apply(
            lambda x: retorna_prioridade(x.entidade, self.entidades.lista_entidades), axis=1)

        if plota:
            analises_tempo_artigo()
            #Configuração do plot:
            CHART_THEME = 'plotly_white'
            fig = go.Figure()
            fig.layout.template = CHART_THEME
            fig.layout.width = 1000
            #fig.layout.height = 200
            fig.update_xaxes(title='Duração')
            fig.update_layout(title_x=0.5)
            duracao_dias = [converte_segundos_em_dias(x) for x in self.estatisticas_sistema.df_entidades_brutas.discretizacao]
            duracao_semanas = [converte_segundos_em_semanas(x) for x in self.estatisticas_sistema.df_entidades_brutas.discretizacao]
            duracao_mes = [converte_segundos_em_meses(x) for x in self.estatisticas_sistema.df_entidades_brutas.discretizacao]

            fig.update_layout(title='Entidades Simultâneas no Sistema (WIP)')
            fig.update_xaxes(title='Duração (D)',showgrid=False)
            fig.update_yaxes(title='Contagem de Pacientes')

            fig.add_trace(go.Scatter(x=duracao_dias,
                                    y=self.estatisticas_sistema.df_entidades_brutas.WIP,
                                     mode='lines',
                                     name='Total de Entidades no Sistema - Dias',
                                    line = dict(color='blue')
                                  ))


            fig.show()

            # fig = px.line(self.estatisticas_sistema.df_entidades_brutas,
            #               x="discretizacao", y="WIP", title='Grafico de WIP')
            # fig.show()

            # GRÁFICOS DE UTILIZAÇÃO

            # CHART_THEME = 'plotly_white'
            # fig2 = go.Figure()
            # fig2.layout.template = CHART_THEME
            # fig2.layout.width = 1000
            # # fig.layout.height = 200
            # fig2.update_xaxes(title='Duração')
            # duracao = [converte_segundos_em_dias(x) for x in
            #                 self.recursos_est.df_estatisticas_recursos.T]
            #
            # fig2.update_layout(title='Gráfico Utilização dos Recursos')
            # for rec in pd.unique(self.recursos_est.df_estatisticas_recursos.recurso):
            #     df = self.recursos_est.df_estatisticas_recursos.loc[
            #         self.recursos_est.df_estatisticas_recursos.recurso == rec]
            #     utilizacao = df.utilizacao
            #     #tempo = df.T
            #
            #     fig2.add_trace(go.Scatter(x=self.recursos_est.df_estatisticas_recursos.T,
            #                              y=utilizacao,
            #                              mode='lines',
            #                              name=rec,
            #                              #line=dict(color='blue')
            #                           ))
            # fig2.show()

            #self.recursos_est.df_estatisticas_recursos['T_Dias'] = self.recursos_est.df_estatisticas_recursos.T.apply(lambda x: converte_segundos_em_dias(x))


            #Passar tudo para dias no eixo x
            #Colocar unidades entre paratenses nos eixos
            #Titulo centralizado
            #Mudar rotula de dados para formatado ao invés de teste_teste
            #
            fig = px.line(self.recursos_est.df_estatisticas_recursos,
                          x="T", y="utilizacao", color="recurso", title='Gráfico de Utilizacao Total dos Recursos')
            fig.layout.template = CHART_THEME
            fig.update_xaxes(title='Duração (D)', showgrid=False)
            fig.update_yaxes(title='Utilização dos Recursos (%)')
            fig.update_layout(title_x=0.5)
            fig.show()


            #GRÁFICOS TEMPO DE FILA

            df_tempo_fila_time_slot = self.entidades.df_entidades.groupby(by=['processo']).agg({"tempo_fila":"mean"}).reset_index()
            df_tempo_fila_time_slot['tempo_fila'] = round(df_tempo_fila_time_slot['tempo_fila']/60,3)
            fig = px.bar(df_tempo_fila_time_slot,x='processo', y="tempo_fila", title='Média de tempo em fila por processo')
            fig.update_layout(title_x=0.5)
            fig.update_yaxes(showticklabels=False)
            #Rotula de Dados
            for index, row in df_tempo_fila_time_slot.iterrows():
                fig.add_annotation(
                    x=row['processo'],
                    y=row['tempo_fila'],
                    xref="x",
                    yref="y",
                    text=f"<b> {row['tempo_fila']} </b> ",
                    font=dict(
                        family="Arial",
                        size=13,
                    )
                )
            fig.layout.template = CHART_THEME
            fig.update_yaxes(title='Média do Tempo em Fila (Min)', showgrid=False)
            fig.update_xaxes(title='Processos')
            fig.show()


            #Média do tempo em fila por nível de prioridade
            df_tempo_fila_prioridade = self.entidades.df_entidades.groupby(by=['prioridade_paciente']).agg(
                {"tempo_fila": "mean"}).reset_index()

            df_tempo_fila_prioridade['tempo_em_minutos'] = round(df_tempo_fila_prioridade["tempo_fila"], 2)
            fig = px.bar(df_tempo_fila_prioridade, x='prioridade_paciente', y="tempo_em_minutos", title='Média de tempo em fila por Prioridade de Atendimento')
            fig.layout.template = CHART_THEME
            fig.update_yaxes(title='Média do Tempo em Fila por Prioridade (Min)', showgrid=False)
            fig.update_xaxes(title='Prioridade do Paciente', showgrid=False)
            fig.update_yaxes(showticklabels=False)
            fig.update_layout(title_x=0.5)
            for index, row in df_tempo_fila_prioridade.iterrows():
                if row[0] == 'Nao Passou da Triagem':
                    continue
                fig.add_annotation(
                    x=row['prioridade_paciente'],
                    y=row['tempo_em_minutos'],
                    xref="x",
                    yref="y",
                    text=f"<b> {row['tempo_em_minutos']} </b> ",
                    font=dict(
                        family="Arial",
                        size=13,
                    )
                )
            fig.show()


            df_tempo_fila_prioridade_por_processo = self.entidades.df_entidades.loc[self.entidades.df_entidades.entra_fila > self.warmup]
            df_tempo_fila_prioridade_por_processo = df_tempo_fila_prioridade_por_processo.groupby(by=['prioridade_paciente', 'processo']).agg(
                {"tempo_fila": "mean"}).reset_index()

            df_tempo_fila_prioridade_por_processo['tempo_fila_min'] = round(df_tempo_fila_prioridade_por_processo['tempo_fila']/60,3)
            fig = px.bar(df_tempo_fila_prioridade_por_processo, x='prioridade_paciente', y="tempo_fila_min",color='processo', title='Média de tempo em fila por prioridade de Atendimento')
            fig.layout.template = CHART_THEME
            fig.update_yaxes(title='Tempo em Fila por Prioridade e Processos (Min)', showgrid=False)
            fig.update_xaxes(title='Prioridade do Paciente', showgrid=False)
            fig.update_layout(title_x=0.5)
            fig.update_yaxes(showticklabels=False)

            fig.show()


            df_tempo_fila_prioridade_por_processo['n'] = n

    def confirma_fluxos(self):

        possiveis_fluxos =  [
            #Apenas consultas
            ["ficha", "triagem", "clinico", "saida"],
            ["ficha", "triagem", "pediatra", "saida"],
                # Tomar medicação, voltar no clínico e sair
            ["ficha", "triagem", "clinico", "aplicar_medicacao", "tomar_medicacao", "clinico", "saida"],
            ["ficha", "triagem", "pediatra", "aplicar_medicacao", "tomar_medicacao", "pediatra", "saida"],

            #Tomar medicação e ja sair direto
            ["ficha", "triagem", "clinico", "aplicar_medicacao", "tomar_medicacao", "saida"],
            ["ficha", "triagem", "pediatra", "aplicar_medicacao", "tomar_medicacao", "saida"],

            #Tomar medicacao e fazer exame
            ["ficha", "triagem", "clinico", "aplicar_medicacao", "tomar_medicacao", "raio-x", "clinico", "saida"],
            ["ficha", "triagem", "clinico", "aplicar_medicacao", "tomar_medicacao", "exame_sangue", "clinico", "saida"],
            ["ficha", "triagem", "clinico", "aplicar_medicacao", "tomar_medicacao", "urina", "clinico", "saida"],
            ["ficha", "triagem", "clinico", "aplicar_medicacao", "tomar_medicacao", "eletro", "clinico", "saida"],

            ["ficha", "triagem", "pediatra", "aplicar_medicacao", "tomar_medicacao", "raio-x", "pediatra", "saida"],
            ["ficha", "triagem", "pediatra", "aplicar_medicacao", "tomar_medicacao", "exame_sangue", "pediatra", "saida"],
            ["ficha", "triagem", "pediatra", "aplicar_medicacao", "tomar_medicacao", "urina", "pediatra", "saida"],
            ["ficha", "triagem", "pediatra", "aplicar_medicacao", "tomar_medicacao", "eletro", "pediatra", "saida"],

            #Fazer apenas 1 exame
            ["ficha", "triagem", "clinico",  "raio-x", "clinico", "saida"],
            ["ficha", "triagem", "clinico",  "exame_sangue", "clinico", "saida"],
            ["ficha", "triagem", "clinico",  "urina", "clinico", "saida"],
            ["ficha", "triagem", "clinico",  "eletro", "clinico", "saida"],

            ["ficha", "triagem", "pediatra",  "raio-x", "pediatra", "saida"],
            ["ficha", "triagem", "pediatra",  "exame_sangue", "pediatra", "saida"],
            ["ficha", "triagem", "pediatra",  "urina", "pediatra", "saida"],
            ["ficha", "triagem", "pediatra",  "eletro", "pediatra", "saida"],


            #Fazer 2 exames - Iniciar só com 2 exames simultaneos e ir rodando para pegar mais casos:
            #Sangue e Urina
            ["ficha", "triagem", "clinico",  "exame_sangue", "urina", "clinico", "saida"],
            ["ficha", "triagem", "clinico", "urina", "exame_sangue",  "clinico", "saida"],

            ["ficha", "triagem", "pediatra",  "exame_sangue", "urina", "pediatra", "saida"],
            ["ficha", "triagem", "pediatra", "urina", "exame_sangue",  "pediatra", "saida"],

            #Sangue e raio-x
            ["ficha", "triagem", "clinico",  "exame_sangue", "raio-x", "clinico", "saida"],
            ["ficha", "triagem", "clinico", "raio-x", "exame_sangue",  "clinico", "saida"],

            ["ficha", "triagem", "pediatra",  "exame_sangue", "raio-x", "pediatra", "saida"],
            ["ficha", "triagem", "pediatra", "raio-x", "exame_sangue",  "pediatra", "saida"],


            #Sangue e eletro
            ["ficha", "triagem", "clinico",  "exame_sangue", "eletro", "clinico", "saida"],
            ["ficha", "triagem", "clinico", "eletro", "exame_sangue",  "clinico", "saida"],

            ["ficha", "triagem", "pediatra",  "exame_sangue", "eletro", "pediatra", "saida"],
            ["ficha", "triagem", "pediatra", "eletro", "exame_sangue",  "pediatra", "saida"],


            #urina e raio-x
            ["ficha", "triagem", "clinico",  "urina", "raio-x", "clinico", "saida"],
            ["ficha", "triagem", "clinico", "raio-x", "urina",  "clinico", "saida"],

            ["ficha", "triagem", "pediatra",  "urina", "raio-x", "pediatra", "saida"],
            ["ficha", "triagem", "pediatra", "raio-x", "urina",  "pediatra", "saida"],


            #urina e eletro
            ["ficha", "triagem", "clinico",  "urina", "eletro", "clinico", "saida"],
            ["ficha", "triagem", "clinico", "eletro", "urina",  "clinico", "saida"],

            ["ficha", "triagem", "pediatra",  "urina", "eletro", "pediatra", "saida"],
            ["ficha", "triagem", "pediatra", "eletro", "urina",  "pediatra", "saida"],

            #raio-x e eletro:
            ["ficha", "triagem", "clinico",  "raio-x", "eletro", "clinico", "saida"],
            ["ficha", "triagem", "clinico", "eletro", "raio-x",  "clinico", "saida"],

            ["ficha", "triagem", "pediatra",  "raio-x", "eletro", "pediatra", "saida"],
            ["ficha", "triagem", "pediatra", "eletro", "raio-x",  "pediatra", "saida"],

            #fluxos incompletos
            #['ficha', 'triagem', 'clinico', 'urina', 'eletro', 'clinico'], #TODO: porque não saiu do sistema?
           # ['ficha', 'triagem', 'clinico', 'eletro', 'clinico'],
            ['ficha', 'triagem', 'clinico'],
            ['ficha', 'triagem', 'pediatra'],
            ['ficha', 'triagem', 'clinico', 'aplicar_medicacao'],
            ['ficha', 'triagem', 'pediatra', 'aplicar_medicacao'],
            ['ficha', 'triagem', 'pediatra', 'aplicar_medicacao'],
            ['ficha', 'triagem', 'clinico', 'aplicar_medicacao', 'tomar_medicacao'],
            ['ficha', 'triagem', 'clinico', 'eletro', 'clinico'],
            ['ficha', 'triagem', 'clinico', 'raio-x'],
            ['ficha', 'triagem', 'pediatra', 'urina'],
            ['ficha', 'triagem', 'pediatra', 'raio-x', 'eletro'],
            ['ficha', 'triagem', 'clinico', 'eletro'],
            ['ficha', 'triagem', 'clinico', 'raio-x', 'eletro', 'clinico'],
            ['ficha', 'triagem', 'clinico', 'raio-x', 'exame_sangue', 'eletro', 'clinico', 'saida'],
            ['ficha', 'triagem', 'pediatra', 'eletro', 'raio-x'],
            ['ficha', 'triagem', 'clinico', 'eletro', 'urina'],
            ['ficha', 'triagem', 'clinico', 'eletro'],
            ['ficha', 'triagem', 'clinico', 'eletro', 'raio-x'],
            ['ficha', 'triagem', 'clinico', 'aplicar_medicacao', 'tomar_medicacao', 'urina', 'raio-x', 'clinico','saida'],
            ['ficha', 'triagem', 'clinico', 'eletro', 'exame_sangue', 'raio-x', 'clinico', 'saida'],
            ['ficha', 'triagem', 'clinico', 'urina', 'raio-x'],
            ['ficha', 'triagem', 'clinico', 'urina'],
            ['ficha', 'triagem'],
            ['ficha', 'triagem', 'pediatra', 'raio-x'],
            ['ficha', 'triagem', 'pediatra', 'eletro', 'raio-x'],
            ['ficha', 'triagem', 'pediatra', 'raio-x'],
            ['ficha', 'triagem', 'clinico', 'exame_sangue'],
            ['ficha', 'triagem', 'clinico', 'raio-x', 'clinico'],
            ['ficha', 'triagem', 'clinico', 'urina', 'exame_sangue'],
            ['ficha', 'triagem', 'pediatra', 'raio-x', 'urina', 'exame_sangue', 'pediatra', 'saida'],
            ['ficha', 'triagem', 'pediatra', 'eletro'],
            ['ficha', 'triagem', 'clinico', 'raio-x', 'eletro'],
            ['ficha', 'triagem', 'clinico', 'urina'],
            ['ficha', 'triagem', 'clinico', 'urina'],
            ['ficha', 'triagem', 'clinico', 'eletro', 'urina'],
            ['ficha', 'triagem', 'pediatra', 'raio-x', 'urina'],
            ['ficha', 'triagem', 'clinico', 'eletro'],
            ['ficha', 'triagem'],
            ['ficha', 'triagem', 'clinico', 'urina', 'exame_sangue'],
            ['ficha', 'triagem', 'clinico', 'urina'],
            ['ficha'],

        ]


        for ent in self.entidades.lista_entidades:
            fluxo = [f["processo"] for f in ent.estatisticas if f["processo"] != "Aguarda Resultado de Exame"]
            if fluxo not in possiveis_fluxos:
                print(f'{ent.nome}: {fluxo}')
        b=0


class EstatisticasSistema():
    def __init__(self):
        self.chegadas = 0
        self.saidas = 0
        self.WIP = 0
        self.df_estatisticas_simulacao = pd.DataFrame()
        self.entidades_sistema = list()
        self.df_entidades_brutas = pd.DataFrame()

    def fecha_estatisticas(self, warmup=0):
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
        self.df_entidades_brutas = self.df_entidades_brutas.loc[self.df_entidades_brutas.discretizacao > warmup]

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

    def fecha_estatisticas(self, nec_recursos, warmup=0):
        def printa_media(coluna):
            res = round(np.mean(self.df_entidades[coluna]),2)
            print(f'{coluna} : {res/60} minutos')

        def retorna_prioridade(paciente, lista_entidades):
            try:
                prioridade = next(ent.atributos['prioridade'] for ent in lista_entidades if paciente == ent.nome)
                return prioridade
            except KeyError:
                return "Nao Passou da Triagem"

        def retorna_recurso_processo(processo, nec_recursos):
            processo_aux = nec_recursos.get(processo, processo)
            if not isinstance(processo_aux,list):
                return processo_aux
            if len(processo_aux) > 1:
                return processo_aux[0] + "-" + processo_aux[1]
            elif len(processo_aux) == 1:
                return processo_aux[0]



        tempo_sistema = list() #TODO:Loop está muito lento. Melhorar!
        self.df_entidades = pd.DataFrame([est for ent in self.lista_entidades for est in ent.estatisticas])
        self.df_entidades = self.df_entidades.loc[self.df_entidades.entra_fila > warmup]
        self.df_entidades['prioridade'] = self.df_entidades.apply(lambda x: retorna_prioridade(x.entidade, self.lista_entidades),axis=1 )
        self.df_entidades['recurso_do_processo'] = self.df_entidades.apply(lambda x: retorna_recurso_processo(x.processo, nec_recursos), axis=1)

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
        self.lista_requests: list() = []


    def fecha_ciclo(self, processo):
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
        if  processo == "saida_sistema":
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

    def fecha_ciclo(self, nome_recurso, momento, inicio_utilizacao, converte_dias=1):
        recurso = self.recursos[nome_recurso]
        recurso.tempo_utilizacao_recurso += momento - inicio_utilizacao
        #inicio_utilizacao = request.usage_since
        #TODO: preciso usar o momento ou apenas o fecha_utilizacao_recurso ja tem esse dado, visto que será chamado após processo
        dict_aux = {"recurso": nome_recurso,
                    "inicia_utilizacao_recurso": inicio_utilizacao,
                    "finaliza_utilizacao_recurso": momento,
                    "tempo_utilizacao_recurso": momento - inicio_utilizacao,
                    "utilizacao": recurso.tempo_utilizacao_recurso/(recurso._capacity * momento),
                    "T": momento/86400, #Dividido por esse valor para gerar gráficos por Dias!
                    "em_atendimento": recurso.count,
                    "tamanho_fila": len(recurso.queue)
                    }

        recurso.estatisticas.append(dict_aux)

    def fecha_estatisticas(self,df_entidades, warmup=0 ):
        for nome, rec in self.recursos.items():
            df_aux = pd.DataFrame(rec.estatisticas)
            print("-"*90)
            print(f'Utilizacao Média do recurso {nome}: {round(np.mean(df_aux["utilizacao"]),2)*100}%')
            print(f'Média de entidades em fila no recurso Fila do recurso {nome}: {round(np.mean(df_aux["tamanho_fila"])) } entidades')
            if nome == 'tecnica_enfermagem' or nome == 'espaco_medicacao':
                tempo_fila_juntos = round(np.mean(df_entidades.loc[df_entidades.recurso_do_processo == 'tecnica_enfermagem-espaco_medicacao']['tempo_fila'])/60,2)
                fila_separados = round(np.mean(df_entidades.loc[df_entidades.recurso_do_processo == nome]["tempo_fila"]) / 60, 2)
                if nome == 'espaco_medicacao':
                    fila_separados = 0
                print(f'Media de tempo de fila do recurso {nome}: {tempo_fila_juntos + fila_separados} minutos')
            else:
                print(f'Media de tempo de fila do recurso {nome}: {round(np.mean(df_entidades.loc[df_entidades.recurso_do_processo == nome]["tempo_fila"])/60,2)} minutos')
            df_aux['recurso'] = nome
            self.df_estatisticas_recursos = pd.concat([self.df_estatisticas_recursos, df_aux])
        self.df_estatisticas_recursos = self.df_estatisticas_recursos.loc[self.df_estatisticas_recursos['T'] > warmup]

class CorridaSimulacao():
    def __init__(self, replicacoes, simulacao: Simulacao, duracao_simulacao, periodo_warmup, plota_histogramas):
        self.replicacoes: int = replicacoes
        self.df_estatisticas_entidades = pd.DataFrame()  #Lista com cada estatística de cada rodada
        self.df_estatisticas_sistema = pd.DataFrame()
        self.df_estatisticas_recursos = pd.DataFrame()
        self.df_estatistcas_sistemas_brutos = pd.DataFrame()
        self.duracao_simulacao = duracao_simulacao #TODO: Tirar do código
        self.simulacoes = [deepcopy(simulacao) for i in range(replicacoes)]
        self.periodo_warmup = periodo_warmup #TODO: Tirar do código
        self.dados = pd.DataFrame()
        self.plota_graficos_finais = plota_histogramas
    def roda_simulacao(self):
        for n_sim in range(len(self.simulacoes)):
            print(f'Simulação {n_sim + 1}')
            print('-' * 150)
            simulacao = self.simulacoes[n_sim]
            simulacao.comeca_simulacao()
            simulacao.env.run(until=simulacao.tempo)
            simulacao.finaliza_todas_estatisticas()
            if len(self.simulacoes) == 1:
                #simulacao.confirma_fluxos()
                simulacao.gera_graficos(n_sim, self.plota_graficos_finais)

        if self.plota_graficos_finais:
            self.plota_histogramas()
        #Passar para abstract que recebe o df e gera os histogramas, a principio apenas tempo de fila por prioridade e talvez por processo!


    def plota_histogramas(self):

        for sim in self.simulacoes:
            df_aux = sim.entidades.df_entidades
            self.dados = pd.concat([self.dados, df_aux])
        self.dados = self.dados.loc[self.dados.entra_fila > self.periodo_warmup]

        self.dados['tempo_fila'] = self.dados['tempo_fila']/60
        dt_aux =  self.dados.loc[self.dados['tempo_fila'] < 50]
        fig = px.histogram(self.dados, x="tempo_fila", histnorm='probability density', color="prioridade",nbins=100 )
        fig.show()


        # for pr in pd.unique(self.dados.prioridade):
        #     dados = self.dados.loc[((self.dados.prioridade == pr) & (self.dados.processo == 'clinico'))]['tempo_fila']
        #     dados = dados / 60
        #     plt.hist(dados, 20)
        #     plt.axvline(np.mean(dados), color='k', linestyle='dashed', linewidth=2)
        #     plt.title("Tempos de Espera para consulta")
        #     plt.show()


        media_fim = self.dados.groupby(by=['prioridade', 'processo']).agg(
            {'tempo_fila': 'mean'}).reset_index()
        media_fim['tempo_fila'] = media_fim['tempo_fila'] / 60
        fig = px.bar(media_fim, x='prioridade', color="processo", y="tempo_fila",
                     title='Media de tempo em fila por prioridade de Atendimento por processo') #markers=True)
        fig.show()

        media_acolhimento = np.mean(
            media_fim.loc[((media_fim.processo == 'triagem') | (media_fim.processo == "ficha"))]['tempo_fila'])
        print(f'{media_acolhimento = }')
        print(media_fim.loc[media_fim.processo == 'clinico'])
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






