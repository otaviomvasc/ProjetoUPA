import simpy
import random
import numpy as np
from scipy import stats
import plotly.express as px
import pandas as pd
from copy import deepcopy
from collections import defaultdict
import plotly.graph_objects as go
import math


class Simulacao:
    def __init__(
        self,
        distribuicoes,
        imprime,
        recursos,
        dist_prob,
        tempo,
        necessidade_recursos,
        ordem_processo,
        atribuicoes,
        liberacao_recurso,
        warmup=0,
    ):
        self.env = simpy.Environment()
        self.distribuicoes = distribuicoes
        self.entidades = Entidades()
        self.recursos_est = Recursos(
            env=self.env, recursos=recursos
        )  # Foi necessário criar 2x de recursos. Pensar algo melhor!
        self.recursos = self.recursos_est.recursos
        self.estatisticas_sistema = EstatisticasSistema()
        self.imprime_detalhes = imprime
        self.dist_probabilidade = dist_prob
        self.tempo = tempo
        self.necessidade_recursos = necessidade_recursos
        self.proximo_processo = ordem_processo
        self.atribuicoes_por_processo = atribuicoes
        self.recursos_liberados_processo = liberacao_recurso
        self.warmup = warmup
        self.converte_dias = 86400
        self.param_m = 405
        self.prox_avaliação = self.param_m * 60

    def comeca_simulacao(self):
        self.env.process(self.gera_chegadas())
        # self.env.run(until=self.tempo) #valor de teste para desenvolvimento!!!!

    def gera_chegadas(self):
        while True:
            yield self.env.timeout(self.distribuicoes(processo="Chegada"))
            # for i in range(2):
            #     yield self.env.timeout(0)
            self.estatisticas_sistema.computa_chegadas(momento=self.env.now)
            entidade_individual = Entidade_individual(
                nome="entidade" + " " + str(self.estatisticas_sistema.chegadas)
            )
            entidade_individual.entrada_sistema = self.env.now
            self.entidades.lista_entidades.append(entidade_individual)
            self.env.process(
                self.processo_com_recurso(
                    entidade_individual=entidade_individual, processo="Ficha"
                )
            )

    def processo_com_recurso(self, entidade_individual, processo):

        entidade_individual.entra_fila = self.env.now
        if processo != "Ficha":
            self.estatisticas_sistema.computa_entidade_entrando_em_fila(self.env.now)

        # Avaliar atendimento de pacientes muito tempo na fila de N em N minutos para não deixar simulação muito lenta.

        # if self.env.now > self.prox_avaliação:

        # Retirar entidades com prioridades 4 e 5 do sistema, porque na realidade eles desistem antes que finalize os 240 minutos na fila
        if self.env.now > self.prox_avaliação:
            ents_tempo_espera_longo = [
                ent
                for ent in self.entidades.lista_entidades
                if ent.atributos.get("prioridade", 0) > 3
                and ent.saida_sistema == 0
                and ent.atributos.get("prioridade_retorno", 0) != 3
                and self.env.now - ent.entra_fila > self.param_m * 60
            ]
            for ent in ents_tempo_espera_longo:
                ent.saida_sistema = self.env.now
                ent.processo_atual = "Saída"
                entidade_individual.sai_fila = self.env.now
                ent.fecha_ciclo(processo="Saída")
                # Deletar o requests antigo!
                result = dict()
                for rec in self.recursos:
                    try:
                        self.recursos[rec].queue.remove(ent.lista_requests[0])
                        break
                    except:
                        continue

                self.estatisticas_sistema.computa_saidas(self.env.now)
                if self.imprime_detalhes:
                    print(f"{self.env.now}: Entidade {ent.nome} saiu do sistema!")
                self.estatisticas_sistema.computa_saidas(self.env.now)
            self.prox_avaliação += self.param_m * 60

        # TODO: alterei o get para primeiro buscar se tem prioridade retorno.Caso não exista a chave no dicionario de atributos, buscara a prioridade de atendimento normal. Optei por deixar explicito!
        requests_recursos = [
            (
                self.recursos[recurso_humando].request()
                if type(self.recursos[recurso_humando])
                == simpy.resources.resource.Resource
                else self.recursos[recurso_humando].request(
                    priority=entidade_individual.atributos.get(
                        "prioridade_retorno",
                        entidade_individual.atributos.get("prioridade", 5),
                    )
                )
            )
            for recurso_humando in self.necessidade_recursos[processo]
        ]

        entidade_individual.lista_requests.extend(
            requests_recursos
        )  # Salvando requests na entidade para conseguir liberar um request em outro processo!!

        # Alteração para impedir que entidades de prioridades menores fiquem tempo demais na fila!

        for request in requests_recursos:
            yield request

        entidade_individual.processo_atual = processo
        if self.imprime_detalhes:
            print(
                f"{self.env.now}:  Entidade: {entidade_individual.nome} começou o processo {processo}"
            )

        entidade_individual.sai_fila = self.env.now
        self.estatisticas_sistema.computa_entidade_saindo_da_fila(self.env.now)
        entidade_individual.entra_processo = (
            self.env.now
        )  # TODO: esse valor é sempre igual ao sai fila. Logo pode ser uma variável só!
        # self.estatisticas_sistema.computa_entidade_entrando_atendimento(self.env.now)

        # delay
        yield self.env.timeout(self.distribuicoes(processo=processo))

        # release
        for rec in self.recursos_liberados_processo[
            processo
        ]:  # também deletar da entidade o requests e não buscar mais pelo request_recursos
            req_recurso_liberado = next(
                req_recurso
                for req_recurso in entidade_individual.lista_requests
                if rec == req_recurso.resource.nome
            )
            self.recursos_est.fecha_ciclo(
                nome_recurso=rec,
                momento=self.env.now,
                inicio_utilizacao=req_recurso_liberado.usage_since,
                entidade=entidade_individual,
                processo=processo,
            )
            self.recursos[rec].release(req_recurso_liberado)
            entidade_individual.lista_requests.remove(
                req_recurso_liberado
            )  # Manter requests para serem removidos em outros métodos

        entidade_individual.sai_processo = self.env.now
        # self.estatisticas_sistema.computa_entidade_saindo_atendimento(self.env.now)
        entidade_individual.fecha_ciclo(processo=processo)

        param = self.atribuicoes_por_processo.get(processo, None)
        if param:
            atr = self.retorna_prob(processo=param)
            entidade_individual.atributos[param] = (
                atr if param == "prioridade" else atr + self.env.now
            )

        if entidade_individual.atributos.get("retorno", False):
            proximo_processo = "Saída"  # Pacientes saem do sistema depois do retorno!

        else:
            proximo_processo = self.decide_proximo_processo(
                processo=processo, entidade=entidade_individual
            )

        if not isinstance(proximo_processo, str):
            # Fila para aguardar resulltado do exame!
            entidade_individual.entra_fila = self.env.now
            # self.estatisticas_sistema.computa_entidade_entrando_em_fila(self.env.now)
            entidade_individual.processo_atual = "Aguarda Resultado de Exame"
            req = self.recursos["Default_Aguarda_Medicacao"].request()
            yield self.env.timeout(
                proximo_processo
            )  # Aguarda tempo do resultado do exame!!!
            self.recursos_est.fecha_ciclo(
                nome_recurso="Default_Aguarda_Medicacao",
                momento=self.env.now,
                inicio_utilizacao=entidade_individual.entra_fila,
                entidade=entidade_individual,
                processo="Aguarda Resultado de Exame",
            )
            self.recursos["Default_Aguarda_Medicacao"].release(req)
            entidade_individual.atributos["prioridade_retorno"] = (
                3  # Pacientes com retorno tem maior prioridade - Verificar se saída dos outros exames está sendo setado!!!
            )
            entidade_individual.atributos["retorno"] = True
            entidade_individual.sai_fila = self.env.now
            # self.estatisticas_sistema.computa_entidade_saindo_da_fila(self.env.now)
            entidade_individual.fecha_ciclo(processo="Aguarda Resultado de Exame")
            self.env.process(
                self.processo_com_recurso(
                    entidade_individual=entidade_individual,
                    processo=entidade_individual.atributos["tipo_atendimento"],
                )
            )

        if proximo_processo == "Saída":
            entidade_individual.saida_sistema = self.env.now
            entidade_individual.processo_atual = "Saída"
            entidade_individual.fecha_ciclo(processo="Saída")
            self.estatisticas_sistema.computa_saidas(self.env.now)
            if self.imprime_detalhes:
                print(
                    f"{self.env.now}: Entidade {entidade_individual.nome} saiu do sistema!"
                )
        elif isinstance(proximo_processo, str):
            self.env.process(
                self.processo_com_recurso(
                    entidade_individual=entidade_individual, processo=proximo_processo
                )
            )

    def retorna_prob(self, processo):
        aleatorio = random.random()
        return next(
            pr[2]
            for pr in self.dist_probabilidade[processo]
            if aleatorio >= pr[0] and aleatorio <= pr[1]
        )

    def decide_proximo_processo(self, processo, entidade):

        proximo_processo = self.proximo_processo[processo]
        if isinstance(
            proximo_processo, str
        ):  # Aqui já vai direto para próximo processo
            return proximo_processo
        else:  # Aqui é necessária decisão
            decisao = self.proximo_processo[processo][0]
            while True:
                aux = self.retorna_prob(decisao)
                if aux not in [ent["processo"] for ent in entidade.estatisticas]:
                    break
            if decisao == "decide_atendimento":
                entidade.atributos["tipo_atendimento"] = aux
            if aux == "medico":
                entidade.atributos["retorno"] = True
                entidade.atributos["prioridade_retorno"] = (
                    3  # Pacientes que já fizeram seus exames e agora vão fazer retorno para o médico e depois saem do sistema
                )
                if (
                    "tempo_resultado_exame_sangue" in entidade.atributos.keys()
                ):  # tempo de espera para resultados do exame de sangue (interno ou externo)
                    tempo_espera = (
                        entidade.atributos["tempo_resultado_exame_sangue"]
                        - self.env.now
                        if self.env.now
                        < entidade.atributos["tempo_resultado_exame_sangue"]
                        else 0
                    )
                    return tempo_espera
                elif (
                    "tempo_resultado_exame_urina" in entidade.atributos.keys()
                ):  # tempo de espera para resultados do exame de urina
                    tempo_espera = (
                        entidade.atributos["tempo_resultado_exame_urina"] - self.env.now
                        if self.env.now
                        < entidade.atributos["tempo_resultado_exame_urina"]
                        else 0
                    )
                    return tempo_espera
                else:
                    return entidade.atributos["tipo_atendimento"]

            return aux

    def finaliza_todas_estatisticas(self):
        # Agrupa os dados
        self.entidades.fecha_estatisticas(
            warmup=self.warmup, nec_recursos=self.necessidade_recursos
        )  # TODO: Acelerar a busca pela prioridade das entidades!!!
        self.recursos_est.fecha_estatisticas(
            warmup=self.warmup, df_entidades=self.entidades.df_entidades
        )
        self.estatisticas_sistema.fecha_estatisticas(warmup=self.warmup)
        self.resultados_da_replicacao, dados_planilha = (
            self.calcula_estatisticas_da_replicacao()
        )
        # limpa todos os dados para não pesar a classe
        verifica = False
        df_fim = 0
        if verifica:
            df = self.recursos_est.df_estatisticas_recursos
            df = df.loc[df["T"] >= 5].reset_index()  # retirada do warm-up
            fila_media_ficha = np.mean(
                df.loc[df.processo == "Ficha"]["tempo_fila_acumulada"]
            )
            fila_media_triagem = np.mean(
                df.loc[df.processo == "Triagem"]["tempo_fila_acumulada"]
            )
            print(f"fila acolhida: {fila_media_ficha + fila_media_triagem}")
            df_clinico = df.loc[df.processo == "Clínico"].reset_index()
            df_fim = (
                df_clinico.groupby(by=["prioridade_entidade"])
                .agg({"fila_acumulada_prioridade": "mean"})
                .reset_index()
            )
            print(
                df_clinico.groupby(by=["prioridade_entidade"]).agg(
                    {"fila_acumulada_prioridade": "mean"}
                )
            )
        gera_warm_up = False
        if gera_warm_up:
            CHART_THEME = "plotly_white"
            df = self.recursos_est.df_estatisticas_recursos
            # df = df.loc[df['T'] >= 5].reset_index()
            pr = 1
            df = df.loc[((df.prioridade_entidade == pr) & (df.recurso == "Clínico"))]
            fig = px.line(
                df,
                x="T",
                y="fila_acumulada_prioridade",
                title="Warm-up time for priority 1 patient care at the clinic",
            )
            fig.layout.template = CHART_THEME
            fig.update_layout(title_x=0.5)
            fig.update_xaxes(title="Duration (D)", showgrid=False)
            fig.update_yaxes(title="Queue Average (Min)")
            fig.show()
        self.limpa_dados()
        return dados_planilha, df_fim

    def gera_graficos(self, n, plota):
        # Graficos de WIP, entrada e saída
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

        def analises_tempo_artigo():
            # tempo médio espera para ficha e triagem
            tempo_medio_ficha_e_triagem = (
                np.mean(
                    self.entidades.df_entidades.loc[
                        (
                            (self.entidades.df_entidades.processo == "Ficha")
                            | (self.entidades.df_entidades.processo == "Triagem")
                        )
                    ]["tempo_fila"]
                )
                / 60
            )

            tempo_medio_atendimento = (
                np.mean(
                    self.entidades.df_entidades.loc[
                        (
                            (self.entidades.df_entidades.processo == "Ficha")
                            | (self.entidades.df_entidades.processo == "Triagem")
                        )
                    ]["tempo_processando"]
                )
                / 60
            )
            total = tempo_medio_ficha_e_triagem + tempo_medio_atendimento
            print(f"{total} tempo de acolhimento total em minutos")

            # tempo_medio_de_espera_para_pacientes:
            print("-" * 90)
            df_aux = self.entidades.df_entidades.loc[
                (
                    (self.entidades.df_entidades.processo != "Ficha")
                    | (self.entidades.df_entidades.processo != "Triagem")
                )
            ]

            df_tempo_fila_prioridade = (
                df_aux.groupby(by=["prioridade_paciente"])
                .agg({"tempo_fila": "mean"})
                .reset_index()
            )
            df_tempo_fila_prioridade["tempo_fila"] = round(
                df_tempo_fila_prioridade["tempo_fila"] / 60, 2
            )
            print(f"{df_tempo_fila_prioridade =}")

        def converte_segundos_em_dias(x):
            return x / 86400

        def converte_segundos_em_semanas(x):
            return x / (86400 * 7)

        def converte_segundos_em_meses(x):
            return x / (86400 * 30)

        self.entidades.df_entidades["prioridade_paciente"] = (
            self.entidades.df_entidades.apply(
                lambda x: retorna_prioridade(
                    x.entidade, self.entidades.lista_entidades
                ),
                axis=1,
            )
        )

        if plota:
            analises_tempo_artigo()
            # Configuração do plot:
            CHART_THEME = "plotly_white"
            fig = go.Figure()
            fig.layout.template = CHART_THEME
            fig.layout.width = 1000
            # fig.layout.height = 200
            fig.update_xaxes(title="Duração")
            fig.update_layout(title_x=0.5)
            duracao_dias = [
                converte_segundos_em_dias(x)
                for x in self.estatisticas_sistema.df_entidades_brutas.discretizacao
            ]
            duracao_semanas = [
                converte_segundos_em_semanas(x)
                for x in self.estatisticas_sistema.df_entidades_brutas.discretizacao
            ]
            duracao_mes = [
                converte_segundos_em_meses(x)
                for x in self.estatisticas_sistema.df_entidades_brutas.discretizacao
            ]

            fig.update_layout(title="Entidades Simultâneas no Sistema (WIP)")
            fig.update_xaxes(title="Duração (D)", showgrid=False)
            fig.update_yaxes(title="Contagem de Pacientes")

            fig.add_trace(
                go.Scatter(
                    x=duracao_dias,
                    y=self.estatisticas_sistema.df_entidades_brutas.WIP,
                    mode="lines",
                    name="Total de Entidades no Sistema - Dias",
                    line=dict(color="blue"),
                )
            )

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

            # self.recursos_est.df_estatisticas_recursos['T_Dias'] = self.recursos_est.df_estatisticas_recursos.T.apply(lambda x: converte_segundos_em_dias(x))

            # Passar tudo para dias no eixo x
            # Colocar unidades entre paratenses nos eixos
            # Titulo centralizado
            # Mudar rotula de dados para formatado ao invés de teste_teste
            #
            fig = px.line(
                self.recursos_est.df_estatisticas_recursos,
                x="T",
                y="utilizacao",
                color="recurso",
                title="Gráfico de Utilizacao Total dos Recursos",
            )
            fig.layout.template = CHART_THEME
            fig.update_xaxes(title="Duração (D)", showgrid=False)
            fig.update_yaxes(title="Utilização dos Recursos (%)")
            fig.update_layout(title_x=0.5)
            fig.show()

            # GRÁFICOS TEMPO DE FILA

            df_tempo_fila_time_slot = (
                self.entidades.df_entidades.groupby(by=["processo"])
                .agg({"tempo_fila": "mean"})
                .reset_index()
            )
            df_tempo_fila_time_slot["tempo_fila"] = round(
                df_tempo_fila_time_slot["tempo_fila"] / 60, 3
            )
            fig = px.bar(
                df_tempo_fila_time_slot,
                x="processo",
                y="tempo_fila",
                title="Média de tempo em fila por processo",
            )
            fig.update_layout(title_x=0.5)
            fig.update_yaxes(showticklabels=False)
            # Rotula de Dados
            for index, row in df_tempo_fila_time_slot.iterrows():
                fig.add_annotation(
                    x=row["processo"],
                    y=row["tempo_fila"],
                    xref="x",
                    yref="y",
                    text=f"<b> {row['tempo_fila']} </b> ",
                    font=dict(
                        family="Arial",
                        size=13,
                    ),
                )
            fig.layout.template = CHART_THEME
            fig.update_yaxes(title="Média do Tempo em Fila (Min)", showgrid=False)
            fig.update_xaxes(title="Processos")
            fig.show()

            # Média do tempo em fila por nível de prioridade
            df_tempo_fila_prioridade = (
                self.entidades.df_entidades.groupby(by=["prioridade_paciente"])
                .agg({"tempo_fila": "mean"})
                .reset_index()
            )

            df_tempo_fila_prioridade["tempo_em_minutos"] = round(
                df_tempo_fila_prioridade["tempo_fila"], 2
            )
            fig = px.bar(
                df_tempo_fila_prioridade,
                x="prioridade_paciente",
                y="tempo_em_minutos",
                title="Média de tempo em fila por Prioridade de Atendimento",
            )
            fig.layout.template = CHART_THEME
            fig.update_yaxes(
                title="Média do Tempo em Fila por Prioridade (Min)", showgrid=False
            )
            fig.update_xaxes(title="Prioridade do Paciente", showgrid=False)
            fig.update_yaxes(showticklabels=False)
            fig.update_layout(title_x=0.5)
            for index, row in df_tempo_fila_prioridade.iterrows():
                if row[0] == "Nao Passou da Triagem":
                    continue
                fig.add_annotation(
                    x=row["prioridade_paciente"],
                    y=row["tempo_em_minutos"],
                    xref="x",
                    yref="y",
                    text=f"<b> {row['tempo_em_minutos']} </b> ",
                    font=dict(
                        family="Arial",
                        size=13,
                    ),
                )
            fig.show()

            df_tempo_fila_prioridade_por_processo = self.entidades.df_entidades.loc[
                self.entidades.df_entidades.entra_fila > self.warmup
            ]
            df_tempo_fila_prioridade_por_processo = (
                df_tempo_fila_prioridade_por_processo.groupby(
                    by=["prioridade_paciente", "processo"]
                )
                .agg({"tempo_fila": "mean"})
                .reset_index()
            )

            df_tempo_fila_prioridade_por_processo["tempo_fila_min"] = round(
                df_tempo_fila_prioridade_por_processo["tempo_fila"] / 60, 3
            )
            fig = px.bar(
                df_tempo_fila_prioridade_por_processo,
                x="prioridade_paciente",
                y="tempo_fila_min",
                color="processo",
                title="Média de tempo em fila por prioridade de Atendimento",
            )
            fig.layout.template = CHART_THEME
            fig.update_yaxes(
                title="Tempo em Fila por Prioridade e Processos (Min)", showgrid=False
            )
            fig.update_xaxes(title="Prioridade do Paciente", showgrid=False)
            fig.update_layout(title_x=0.5)
            fig.update_yaxes(showticklabels=False)

            fig.show()

            df_tempo_fila_prioridade_por_processo["n"] = n

    def confirma_fluxos(self):

        possiveis_fluxos = [
            # Apenas consultas
            ["ficha", "triagem", "clinico", "saida"],
            ["ficha", "triagem", "pediatra", "saida"],
            # Tomar medicação, voltar no clínico e sair
            [
                "ficha",
                "triagem",
                "clinico",
                "aplicar_medicacao",
                "tomar_medicacao",
                "clinico",
                "saida",
            ],
            [
                "ficha",
                "triagem",
                "pediatra",
                "aplicar_medicacao",
                "tomar_medicacao",
                "pediatra",
                "saida",
            ],
            # Tomar medicação e ja sair direto
            [
                "ficha",
                "triagem",
                "clinico",
                "aplicar_medicacao",
                "tomar_medicacao",
                "saida",
            ],
            [
                "ficha",
                "triagem",
                "pediatra",
                "aplicar_medicacao",
                "tomar_medicacao",
                "saida",
            ],
            # Tomar medicacao e fazer exame
            [
                "ficha",
                "triagem",
                "clinico",
                "aplicar_medicacao",
                "tomar_medicacao",
                "raio-x",
                "clinico",
                "saida",
            ],
            [
                "ficha",
                "triagem",
                "clinico",
                "aplicar_medicacao",
                "tomar_medicacao",
                "exame_sangue",
                "clinico",
                "saida",
            ],
            [
                "ficha",
                "triagem",
                "clinico",
                "aplicar_medicacao",
                "tomar_medicacao",
                "urina",
                "clinico",
                "saida",
            ],
            [
                "ficha",
                "triagem",
                "clinico",
                "aplicar_medicacao",
                "tomar_medicacao",
                "eletro",
                "clinico",
                "saida",
            ],
            [
                "ficha",
                "triagem",
                "pediatra",
                "aplicar_medicacao",
                "tomar_medicacao",
                "raio-x",
                "pediatra",
                "saida",
            ],
            [
                "ficha",
                "triagem",
                "pediatra",
                "aplicar_medicacao",
                "tomar_medicacao",
                "exame_sangue",
                "pediatra",
                "saida",
            ],
            [
                "ficha",
                "triagem",
                "pediatra",
                "aplicar_medicacao",
                "tomar_medicacao",
                "urina",
                "pediatra",
                "saida",
            ],
            [
                "ficha",
                "triagem",
                "pediatra",
                "aplicar_medicacao",
                "tomar_medicacao",
                "eletro",
                "pediatra",
                "saida",
            ],
            # Fazer apenas 1 exame
            ["ficha", "triagem", "clinico", "raio-x", "clinico", "saida"],
            ["ficha", "triagem", "clinico", "exame_sangue", "clinico", "saida"],
            ["ficha", "triagem", "clinico", "urina", "clinico", "saida"],
            ["ficha", "triagem", "clinico", "eletro", "clinico", "saida"],
            ["ficha", "triagem", "pediatra", "raio-x", "pediatra", "saida"],
            ["ficha", "triagem", "pediatra", "exame_sangue", "pediatra", "saida"],
            ["ficha", "triagem", "pediatra", "urina", "pediatra", "saida"],
            ["ficha", "triagem", "pediatra", "eletro", "pediatra", "saida"],
            # Fazer 2 exames - Iniciar só com 2 exames simultaneos e ir rodando para pegar mais casos:
            # Sangue e Urina
            [
                "ficha",
                "triagem",
                "clinico",
                "exame_sangue",
                "urina",
                "clinico",
                "saida",
            ],
            [
                "ficha",
                "triagem",
                "clinico",
                "urina",
                "exame_sangue",
                "clinico",
                "saida",
            ],
            [
                "ficha",
                "triagem",
                "pediatra",
                "exame_sangue",
                "urina",
                "pediatra",
                "saida",
            ],
            [
                "ficha",
                "triagem",
                "pediatra",
                "urina",
                "exame_sangue",
                "pediatra",
                "saida",
            ],
            # Sangue e raio-x
            [
                "ficha",
                "triagem",
                "clinico",
                "exame_sangue",
                "raio-x",
                "clinico",
                "saida",
            ],
            [
                "ficha",
                "triagem",
                "clinico",
                "raio-x",
                "exame_sangue",
                "clinico",
                "saida",
            ],
            [
                "ficha",
                "triagem",
                "pediatra",
                "exame_sangue",
                "raio-x",
                "pediatra",
                "saida",
            ],
            [
                "ficha",
                "triagem",
                "pediatra",
                "raio-x",
                "exame_sangue",
                "pediatra",
                "saida",
            ],
            # Sangue e eletro
            [
                "ficha",
                "triagem",
                "clinico",
                "exame_sangue",
                "eletro",
                "clinico",
                "saida",
            ],
            [
                "ficha",
                "triagem",
                "clinico",
                "eletro",
                "exame_sangue",
                "clinico",
                "saida",
            ],
            [
                "ficha",
                "triagem",
                "pediatra",
                "exame_sangue",
                "eletro",
                "pediatra",
                "saida",
            ],
            [
                "ficha",
                "triagem",
                "pediatra",
                "eletro",
                "exame_sangue",
                "pediatra",
                "saida",
            ],
            # urina e raio-x
            ["ficha", "triagem", "clinico", "urina", "raio-x", "clinico", "saida"],
            ["ficha", "triagem", "clinico", "raio-x", "urina", "clinico", "saida"],
            ["ficha", "triagem", "pediatra", "urina", "raio-x", "pediatra", "saida"],
            ["ficha", "triagem", "pediatra", "raio-x", "urina", "pediatra", "saida"],
            # urina e eletro
            ["ficha", "triagem", "clinico", "urina", "eletro", "clinico", "saida"],
            ["ficha", "triagem", "clinico", "eletro", "urina", "clinico", "saida"],
            ["ficha", "triagem", "pediatra", "urina", "eletro", "pediatra", "saida"],
            ["ficha", "triagem", "pediatra", "eletro", "urina", "pediatra", "saida"],
            # raio-x e eletro:
            ["ficha", "triagem", "clinico", "raio-x", "eletro", "clinico", "saida"],
            ["ficha", "triagem", "clinico", "eletro", "raio-x", "clinico", "saida"],
            ["ficha", "triagem", "pediatra", "raio-x", "eletro", "pediatra", "saida"],
            ["ficha", "triagem", "pediatra", "eletro", "raio-x", "pediatra", "saida"],
            # fluxos incompletos
            # ['ficha', 'triagem', 'clinico', 'urina', 'eletro', 'clinico'], #TODO: porque não saiu do sistema?
            # ['ficha', 'triagem', 'clinico', 'eletro', 'clinico'],
            ["ficha", "triagem", "clinico"],
            ["ficha", "triagem", "pediatra"],
            ["ficha", "triagem", "clinico", "aplicar_medicacao"],
            ["ficha", "triagem", "pediatra", "aplicar_medicacao"],
            ["ficha", "triagem", "pediatra", "aplicar_medicacao"],
            ["ficha", "triagem", "clinico", "aplicar_medicacao", "tomar_medicacao"],
            ["ficha", "triagem", "clinico", "eletro", "clinico"],
            ["ficha", "triagem", "clinico", "raio-x"],
            ["ficha", "triagem", "pediatra", "urina"],
            ["ficha", "triagem", "pediatra", "raio-x", "eletro"],
            ["ficha", "triagem", "clinico", "eletro"],
            ["ficha", "triagem", "clinico", "raio-x", "eletro", "clinico"],
            [
                "ficha",
                "triagem",
                "clinico",
                "raio-x",
                "exame_sangue",
                "eletro",
                "clinico",
                "saida",
            ],
            ["ficha", "triagem", "pediatra", "eletro", "raio-x"],
            ["ficha", "triagem", "clinico", "eletro", "urina"],
            ["ficha", "triagem", "clinico", "eletro"],
            ["ficha", "triagem", "clinico", "eletro", "raio-x"],
            [
                "ficha",
                "triagem",
                "clinico",
                "aplicar_medicacao",
                "tomar_medicacao",
                "urina",
                "raio-x",
                "clinico",
                "saida",
            ],
            [
                "ficha",
                "triagem",
                "clinico",
                "eletro",
                "exame_sangue",
                "raio-x",
                "clinico",
                "saida",
            ],
            ["ficha", "triagem", "clinico", "urina", "raio-x"],
            ["ficha", "triagem", "clinico", "urina"],
            ["ficha", "triagem"],
            ["ficha", "triagem", "pediatra", "raio-x"],
            ["ficha", "triagem", "pediatra", "eletro", "raio-x"],
            ["ficha", "triagem", "pediatra", "raio-x"],
            ["ficha", "triagem", "clinico", "exame_sangue"],
            ["ficha", "triagem", "clinico", "raio-x", "clinico"],
            ["ficha", "triagem", "clinico", "urina", "exame_sangue"],
            [
                "ficha",
                "triagem",
                "pediatra",
                "raio-x",
                "urina",
                "exame_sangue",
                "pediatra",
                "saida",
            ],
            ["ficha", "triagem", "pediatra", "eletro"],
            ["ficha", "triagem", "clinico", "raio-x", "eletro"],
            ["ficha", "triagem", "clinico", "urina"],
            ["ficha", "triagem", "clinico", "urina"],
            ["ficha", "triagem", "clinico", "eletro", "urina"],
            ["ficha", "triagem", "pediatra", "raio-x", "urina"],
            ["ficha", "triagem", "clinico", "eletro"],
            ["ficha", "triagem"],
            ["ficha", "triagem", "clinico", "urina", "exame_sangue"],
            ["ficha", "triagem", "clinico", "urina"],
            ["ficha"],
        ]

        for ent in self.entidades.lista_entidades:
            fluxo = [
                f["processo"]
                for f in ent.estatisticas
                if f["processo"] != "Aguarda Resultado de Exame"
            ]
            if fluxo not in possiveis_fluxos:
                print(f"{ent.nome}: {fluxo}")
        b = 0

    def calcula_estatisticas_da_replicacao(self):
        def calc_ic(lista):
            confidence = 0.95
            n = len(lista)
            # mean_se: Erro Padrão da Média
            mean_se = stats.sem(lista)
            h = mean_se * stats.t.ppf((1 + confidence) / 2.0, n - 1)
            # Intervalo de confiança: mean, +_h
            return h

        entidades_que_sairam_do_sistema = [
            ent.nome for ent in self.entidades.lista_entidades if ent.saida_sistema > 1
        ]
        df_ent = self.entidades.df_entidades.loc[
            self.entidades.df_entidades.entra_processo >= self.warmup
        ]
        df_ent_aux = df_ent.loc[df_ent.entidade.isin(entidades_que_sairam_do_sistema)]
        df_soma_tempos_por_entidade = (
            df_ent_aux.groupby(by=["entidade"])
            .agg({"tempo_processando": "sum", "tempo_fila": "sum"})
            .reset_index()
        )
        media_tempo_processando = (
            np.mean(df_soma_tempos_por_entidade.tempo_processando) / 60
        )
        df_media_tempo_fila = np.mean(df_soma_tempos_por_entidade.tempo_fila) / 60
        aux_TS = [
            (ent.saida_sistema - ent.entrada_sistema) / 60
            for ent in self.entidades.lista_entidades
            if ent.saida_sistema > 1
        ]

        # PARTE DO WIP AINDA PRECISA DE CONCERTO! - CALCULAR JUNTO COM WIP O NÚMERO EM ATENDIMENTO E O NÚMERO EM FILA
        df_wip = self.estatisticas_sistema.df_entidades_brutas.loc[
            self.estatisticas_sistema.df_entidades_brutas.discretizacao >= self.warmup
        ]
        dados_NS = list(df_wip["WIP"])
        dados_em_fila = list(df_wip["em_fila"])
        dados_em_atend = list(df_wip["em_atendimento"])
        media_NS_final = round(np.mean(dados_NS), 2)
        media_NF_final = round(np.mean(dados_em_fila), 2)
        media_NA_final = round(np.mean(dados_em_atend), 2)

        dados_WIP = list(df_wip["WIP"])
        media_WIP = np.mean(dados_WIP)

        ####### RECURSOS #####
        df_rec_rep = self.recursos_est.df_estatisticas_recursos.loc[
            self.recursos_est.df_estatisticas_recursos["T"] * 86000 >= self.warmup
        ]
        rec_avaliados = [
            r for r in pd.unique(df_rec_rep.recurso) if r != "Default_Aguarda_Medicacao"
        ]
        dict_rec = dict()
        for rc in rec_avaliados:
            dict_rec[rc] = {
                "dados_utilizacao": list(
                    df_rec_rep.loc[df_rec_rep.recurso == rc]["utilizacao"]
                ),
                "media_utilizacao": np.mean(
                    df_rec_rep.loc[df_rec_rep.recurso == rc]["utilizacao"]
                ),
                "tempo_fila": list(
                    df_rec_rep.loc[df_rec_rep.recurso == rc]["tempo_fila_acumulada"]
                ),
                "prioridade_entidade": list(
                    df_rec_rep.loc[df_rec_rep.recurso == rc]["prioridade_entidade"]
                ),
                "tempo_fila_prioridade_entidade": list(
                    df_rec_rep.loc[df_rec_rep.recurso == rc][
                        "fila_acumulada_prioridade"
                    ]
                ),
                "discretizacao": list(df_rec_rep.loc[df_rec_rep.recurso == rc]["T"]),
                "media_tempo_fila_pr1_clinico": np.mean(
                    df_rec_rep.loc[
                        (
                            (df_rec_rep.recurso == "Clínico")
                            & (df_rec_rep.prioridade_entidade == 1)
                        )
                    ]["fila_acumulada_prioridade"]
                ),
                "processo": list(df_rec_rep.loc[df_rec_rep.recurso == rc]["processo"]),
                "tempo_fila_entidades": list(
                    df_rec_rep.loc[df_rec_rep.recurso == rc]["Fila_Entidades"]
                ),
            }

        # Calculo do número de replicações
        # Número médio de pacientes prioridade 1 no recurso clínico!
        dt_aux = {
            "dados_TS": aux_TS,
            "momento_NS": list(df_wip.discretizacao),
            "media_TS": np.mean(aux_TS),
            "media_TA_total": media_tempo_processando,
            "media_TF_total": df_media_tempo_fila,
            "dados_TA": list(df_soma_tempos_por_entidade.tempo_processando),
            "dados_TF": list(df_soma_tempos_por_entidade.tempo_fila),
            "dict_utilizacao": dict_rec,
            "dados_NS": dados_NS,
            "dados_NF": dados_em_fila,
            "dados_NA": dados_em_atend,
            "media_NS_final": media_NS_final,
            "media_NF_final": media_NF_final,
            "media_NA_final": media_NA_final,
        }

        dict_rec2 = dict()
        prs = [1, 2, 3, 4, 5, "sem_pr"]

        for rc in rec_avaliados:
            dict_pr = dict()
            dados = df_rec_rep.loc[(df_rec_rep.recurso == rc)][
                "fila_acumulada_prioridade"
            ]
            dados2 = df_rec_rep.loc[(df_rec_rep.recurso == rc)][
                "tempo_processo_por_prioridade"
            ]
            dict_rec2[rc] = {
                "dados_utilizacao": df_rec_rep.loc[df_rec_rep.recurso == rc][
                    "utilizacao"
                ],
                "dados_fila": dados,
                "dados_atendimento": dados2,
                "dados_entidade_em_fila": df_rec_rep.loc[df_rec_rep.recurso == rc][
                    "media_entidades_em_fila_acumulada"
                ],
            }

        dados_planilha = {
            "dados_tempo": dict_rec2,
            "media_tempo_sistema_total": np.mean(aux_TS),
            "min_TS": min(aux_TS),
            "max_TS": max(aux_TS),
            "desv_pad_TS": np.std(aux_TS),
            "IC_TS": calc_ic(aux_TS),
            "amostra_TS": len(aux_TS),
            "media_WIP": np.mean(dados_WIP),
            "min_WIP": min(dados_WIP),
            "max_wip": max(dados_WIP),
            "desv_pad_WIP": np.std(dados_WIP),
            "IC_wip": calc_ic(dados_WIP),
            "Dados_TA": [
                i / 60 for i in list(df_soma_tempos_por_entidade.tempo_processando)
            ],
            "Dados_Fila": [
                i / 60 for i in list(df_soma_tempos_por_entidade.tempo_fila)
            ],
        }

        return dt_aux, dados_planilha

    def limpa_dados(self):
        self.entidades = []
        self.estatisticas_sistema = []
        self.recursos_est.df_estatisticas_recursos = []


class EstatisticasSistema:
    def __init__(self):
        self.chegadas = 0
        self.saidas = 0
        self.WIP = 0
        self.em_fila = 0
        self.em_atendimento = 0
        self.df_estatisticas_simulacao = pd.DataFrame()
        self.entidades_sistema = list()
        self.df_entidades_brutas = pd.DataFrame()

    def fecha_estatisticas(self, warmup=0):
        print(f"Chegadas: {self.chegadas}")
        print(f"Saídas: {self.saidas}")
        print(f"WIP: {self.WIP} ")
        entidades_sistema = np.mean(
            [rec["WIP"] for rec in self.entidades_sistema]
        )  # TODO: Verificar como esse cálculo ta sendo feito!!
        dict_aux = {
            "Chegadas": self.chegadas,
            "Saidas": self.saidas,
            "WIP": self.WIP,
            "Media_Sistema": entidades_sistema,
        }

        self.df_entidades_brutas = pd.DataFrame(self.entidades_sistema)
        self.df_entidades_brutas = self.df_entidades_brutas.drop_duplicates(
            subset="discretizacao", keep="last"
        )  # removendo registros da mesma discretização para pegar a foto final!!

        self.df_estatisticas_simulacao = pd.DataFrame([dict_aux])
        self.df_entidades_brutas = self.df_entidades_brutas.loc[
            self.df_entidades_brutas.discretizacao >= warmup
        ]

    def computa_chegadas(self, momento):
        # TODO: Adaptar para computar chegadas de mais de um indivíduo!!!!
        self.chegadas += 1
        self.WIP += 1
        self.em_fila += 1
        self.entidades_sistema.append(
            {
                "discretizacao": momento,
                "WIP": self.WIP,
                "processo": "chegada",
                "em_fila": self.em_fila,
                "em_atendimento": self.em_atendimento,
            }
        )

    def computa_saidas(self, momento):
        self.saidas += 1
        self.WIP -= 1
        self.em_atendimento -= 1
        self.entidades_sistema.append(
            {
                "discretizacao": momento,
                "WIP": self.WIP,
                "processo": "saida",
                "em_fila": self.em_fila,
                "em_atendimento": self.em_atendimento,
            }
        )

    def computa_entidade_entrando_em_fila(self, momento):
        self.em_fila += 1
        self.em_atendimento -= 1
        self.entidades_sistema.append(
            {
                "discretizacao": momento,
                "WIP": self.WIP,
                "processo": "fila",
                "em_fila": self.em_fila,
                "em_atendimento": self.em_atendimento,
            }
        )

    def computa_entidade_saindo_da_fila(self, momento):
        self.em_fila -= 1
        self.em_atendimento += 1
        self.entidades_sistema.append(
            {
                "discretizacao": momento,
                "WIP": self.WIP,
                "processo": "fila",
                "em_fila": self.em_fila,
                "em_atendimento": self.em_atendimento,
            }
        )

    def computa_entidade_entrando_atendimento(self, momento):
        self.em_atendimento += 1
        self.entidades_sistema.append(
            {
                "discretizacao": momento,
                "WIP": self.WIP,
                "processo": "atendimento",
                "em_fila": self.em_fila,
                "em_atendimento": self.em_atendimento,
            }
        )

    def computa_entidade_saindo_atendimento(self, momento):
        self.em_atendimento -= 1
        self.entidades_sistema.append(
            {
                "discretizacao": momento,
                "WIP": self.WIP,
                "processo": "atendimento",
                "em_fila": self.em_fila,
                "em_atendimento": self.em_atendimento,
            }
        )


class Entidades:
    def __init__(self):
        self.lista_entidades = list()
        self.df_entidades = pd.DataFrame()
        self.resultados_entidades = pd.DataFrame()

    def fecha_estatisticas(self, nec_recursos, warmup=0):
        def printa_media(coluna):
            res = round(np.mean(self.df_entidades[coluna]), 2)
            print(f"{coluna} : {res/60} minutos")

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

        def retorna_recurso_processo(processo, nec_recursos):
            processo_aux = nec_recursos.get(processo, processo)
            if not isinstance(processo_aux, list):
                return processo_aux
            if len(processo_aux) > 1:
                return processo_aux[0] + "-" + processo_aux[1]
            elif len(processo_aux) == 1:
                return processo_aux[0]

        tempo_sistema = list()  # TODO:Loop está muito lento. Melhorar!
        # Dados estão sendo calculados errados. Métricas de Tempo de sistema, tempo de fila e tempo de atendimento não precisam ser calculadas aqui!
        self.df_entidades = pd.DataFrame(
            [est for ent in self.lista_entidades for est in ent.estatisticas]
        )
        self.df_entidades = self.df_entidades.loc[
            self.df_entidades.entra_fila >= warmup
        ]
        self.df_entidades["prioridade"] = self.df_entidades.apply(
            lambda x: retorna_prioridade(x.entidade, self.lista_entidades), axis=1
        )
        self.df_entidades["recurso_do_processo"] = self.df_entidades.apply(
            lambda x: retorna_recurso_processo(x.processo, nec_recursos), axis=1
        )

        # dict_estatisticas_calculadas = {"tempo_sistema":np.mean([ent.saida_sistema - ent.entrada_sistema for ent in self.lista_entidades if ent.saida_sistema > 1]),
        # "tempo_processamento":round(np.mean(self.df_entidades['tempo_processando']),2),
        # "tempo_fila" :round(np.mean(self.df_entidades['tempo_fila']),2)}
        # printa_media(coluna='tempo_processando')
        # printa_media(coluna='tempo_fila')
        # print(f'TS: { dict_estatisticas_calculadas["tempo_sistema"] / 60} minutos')
        # self.resultados_entidades = pd.DataFrame([dict_estatisticas_calculadas])


class Entidade_individual(Entidades):
    def __new__(
        cls, *args, **kwargs
    ):  # Usado para não relacionar um individuo com outro (substituindo o deepcopy)
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
        aux_dados = {
            "entidade": self.nome,
            "processo": processo,
            "entra_fila": self.entra_fila,
            "sai_fila": self.sai_fila,
            "tempo_fila": self.sai_fila - self.entra_fila,
            "entra_processo": (
                self.sai_fila if processo != "Aguarda Resultado de Exame" else 0
            ),
            "sai_processo": self.sai_processo,
            "tempo_processando": self.sai_processo - self.entra_processo,
            "time_slot": self.time_slot,
        }

        self.estatisticas.append(aux_dados)
        self.entra_fila: float = 0.0
        self.sai_fila: float = 0.0
        self.entra_processo: float = 0.0
        self.sai_processo: float = 0.0
        if processo == "Saída":
            self.tempo_sistema = self.saida_sistema - self.entrada_sistema


class Recursos:
    def __init__(self, recursos, env):
        self.recursos = self.cria_recursos(recursos, env)
        self.df_estatisticas_recursos = pd.DataFrame()

    def cria_recursos(self, dict_recursos, env):
        recursos_dict = dict()
        for rec, cap in dict_recursos.items():
            if cap[1]:
                rec_aux = simpy.PriorityResource(env, capacity=cap[0])
            else:
                rec_aux = simpy.Resource(env, capacity=cap[0])
            rec_aux.nome = rec
            rec_aux.inicia_utilizacao_recurso = 0
            rec_aux.finaliza_utilizacao_recurso = 0
            rec_aux.utilizacao = 0
            rec_aux.estatisticas = []
            rec_aux.tempo_utilizacao_recurso = 0
            rec_aux.lista_fila_acumulada = list()
            rec_aux.tempo_fila_dinamico = 0
            rec_aux.fila_acumulada_por_prioridade = {
                1: [],
                2: [],
                3: [],
                4: [],
                5: [],
                "sem_pr": [],
            }
            rec_aux.media_entidade_em_fila_acumulada = list()
            rec_aux.media_entidade_em_atendimento_acumulado = list()
            rec_aux.tempo_atendimento_entidade_geral = (0,)
            rec_aux.lista_tempo_atendimento_geral = list()
            rec_aux.tempo_atendimento_por_prioridade = {
                1: [],
                2: [],
                3: [],
                4: [],
                5: [],
                "sem_pr": [],
            }
            rec_aux.tempo_de_espera_do_recurso = 0.0
            rec_aux.lista_tempo_espera_do_recurso = 0

            # rec_aux.fecha_ciclo = fecha_ciclo
            recursos_dict[rec] = rec_aux

        return recursos_dict

    def fecha_ciclo(self, nome_recurso, momento, inicio_utilizacao, entidade, processo):
        recurso = self.recursos[nome_recurso]
        recurso.tempo_utilizacao_recurso += round(momento - inicio_utilizacao)
        tempo_atendimento = momento - entidade.entra_processo
        tempo_fila_ent = entidade.sai_fila - entidade.entra_fila
        recurso.lista_fila_acumulada.append(tempo_fila_ent / 60)
        recurso.lista_tempo_atendimento_geral.append(tempo_atendimento / 60)
        recurso.tempo_atendimento_entidade_geral = np.mean(
            recurso.lista_tempo_atendimento_geral
        )

        recurso.tempo_fila_dinamico = np.mean(recurso.lista_fila_acumulada)
        prioridade_entidade = entidade.atributos.get(
            "prioridade", "sem_pr"
        )  # Definição de qual entidade, dado que cada prioridade é uma entidade?
        recurso.fila_acumulada_por_prioridade[prioridade_entidade].append(
            tempo_fila_ent / 60
        )  # valores acumulados estaticos
        recurso.tempo_atendimento_por_prioridade[prioridade_entidade].append(
            tempo_atendimento / 60
        )
        recurso.media_entidade_em_fila_acumulada.append(len(recurso.queue))
        recurso.media_entidade_em_atendimento_acumulado.append(recurso.count)

        dict_aux = {
            "recurso": nome_recurso,
            "processo": processo,
            "utilizacao": recurso.tempo_utilizacao_recurso
            / (recurso._capacity * momento),
            "T": momento
            / 86400,  # Dividido por esse valor para gerar gráficos por Dias!
            "em_atendimento": recurso.count,
            "tamanho_fila": len(recurso.queue),
            "tempo_fila_acumulada": recurso.tempo_fila_dinamico,  # Média geral - Que será usada para cálculo final caso tenhamos uma mesma entidade!
            "tempo_processo_acumulado": recurso.tempo_atendimento_entidade_geral,
            "tempo_processo_por_prioridade": np.mean(
                recurso.tempo_atendimento_por_prioridade[prioridade_entidade]
            ),
            "prioridade_entidade": prioridade_entidade,  # Média do tempo em fila da prioriade!
            "fila_acumulada_prioridade": np.mean(
                recurso.fila_acumulada_por_prioridade[prioridade_entidade]
            ),  # Média dos tempos em filas acumulados por entidade!
            "media_entidades_em_fila_acumulada": np.mean(
                recurso.media_entidade_em_fila_acumulada
            ),
            "media_entidades_em_atendimento_acumulado": np.mean(
                recurso.media_entidade_em_atendimento_acumulado
            ),
        }

        recurso.estatisticas.append(dict_aux)

    def fecha_estatisticas(self, df_entidades, warmup=0):
        for nome, rec in self.recursos.items():
            df_aux = pd.DataFrame(rec.estatisticas)
            df_aux["Fila_Entidades"] = rec.lista_fila_acumulada
            df_aux = df_aux.loc[df_aux["T"] * 86400 > warmup]
            print("-" * 90)
            print(
                f'Utilizacao Média do recurso {nome}: {round(np.mean(df_aux["utilizacao"]),2)*100}%'
            )  # Correto!!!
            print(
                f'Média do Tamanho da fila recurso (Cálculo apenas salvando tamanho da fila) {nome}: {round(np.mean(df_aux["tamanho_fila"])) } entidades'
            )  # Corrigir entidades em fila do recurso, fazendo o mesmo calculo das médias
            # print(f'Tempo Médio de Fila Acumulada Final (Ultimo registro): {round(rec.tempo_fila_dinamico,2)} minutos')
            print(
                f"Tempo Médio de Fila Acumulada Médio (Média Geral de todas os registros): {round(np.mean(rec.lista_fila_acumulada), 2) } minutos"
            )
            for k, v in rec.fila_acumulada_por_prioridade.items():
                if len(v) == 0:
                    continue
                else:
                    media = round(np.mean(v), 2)
                    print(f"Prioridade: {k} - média de tempo em fila: {media} minutos")

            print(
                f"Média de entidades em fila acumulada: {round(np.mean(rec.media_entidade_em_fila_acumulada),6)} entidades"
            )
            print(
                f"Média de entidades em atendimento acumulada: {round(np.mean(rec.media_entidade_em_atendimento_acumulado), 6)} entidades"
            )

            # if nome == 'Técnica de Enfermagem' or nome == 'Espaço para tomar Medicação':
            #     tempo_fila_juntos = round(np.mean(df_entidades.loc[df_entidades.recurso_do_processo == 'Técnica de Enfermagem-Espaço para tomar Medicação']['tempo_fila'])/60,2)
            #     fila_separados = round(np.mean(df_entidades.loc[df_entidades.recurso_do_processo == nome]["tempo_fila"]) / 60, 2)
            #     if nome == 'Espaço para tomar Medicação':
            #         fila_separados = 0
            #     print(f'Media de tempo de fila do recurso {nome}: {tempo_fila_juntos + fila_separados} minutos')
            # else:
            #     print(f'Media de tempo de fila do recurso {nome}: {round(np.mean(df_entidades.loc[df_entidades.recurso_do_processo == nome]["tempo_fila"])/60,2)} minutos')
            # df_aux['recurso'] = nome

            self.df_estatisticas_recursos = pd.concat(
                [self.df_estatisticas_recursos, df_aux]
            )

        self.df_estatisticas_recursos = self.df_estatisticas_recursos.loc[
            self.df_estatisticas_recursos["T"] * 86400 > warmup
        ]  # multipliquei por 86400 para voltar converter o valor para segundos porque na hora de salvar os dados eu precisei salvar em minutos


class CorridaSimulacao:
    def __init__(
        self,
        replicacoes,
        simulacao: Simulacao,
        duracao_simulacao,
        periodo_warmup,
        plota_histogramas,
    ):
        self.replicacoes: int = replicacoes
        self.df_estatisticas_entidades = (
            pd.DataFrame()
        )  # Lista com cada estatística de cada rodada
        self.df_estatisticas_sistema = pd.DataFrame()
        self.df_estatisticas_recursos = pd.DataFrame()
        self.df_estatistcas_sistemas_brutos = pd.DataFrame()
        self.duracao_simulacao = duracao_simulacao  # TODO: Tirar do código
        self.simulacoes = [deepcopy(simulacao) for i in range(replicacoes)]
        self.periodo_warmup = periodo_warmup  # TODO: Tirar do código
        self.dados = pd.DataFrame()
        self.plota_graficos_finais = plota_histogramas
        self.dados_planilha = dict()
        self.dados_fila_validacao = [[], [], [], []]

    def roda_simulacao(self, gera_planilha=False):
        df_aux = pd.DataFrame()
        for n_sim in range(len(self.simulacoes)):
            print(f"Simulação {n_sim + 1}")
            print("-" * 150)
            simulacao = self.simulacoes[n_sim]
            simulacao.comeca_simulacao()
            simulacao.env.run(until=simulacao.tempo)
            dados_p, dados_validacao = simulacao.finaliza_todas_estatisticas()
            # dados_validacao['rep'] = n_sim
            # df_aux = pd.concat([df_aux, dados_validacao])
            self.dados_planilha[n_sim] = dados_p

            # if len(self.simulacoes) == 1:
            # simulacao.confirma_fluxos()
            # simulacao.gera_graficos(n_sim, self.plota_graficos_finais)

            # calculo do warm-up para média do tempo em fila dos pacientes de prioridade 1

    def plota_histogramas(self):

        for sim in self.simulacoes:
            df_aux = sim.entidades.df_entidades
            self.dados = pd.concat([self.dados, df_aux])
        self.dados = self.dados.loc[self.dados.entra_fila > self.periodo_warmup]

        self.dados["tempo_fila"] = self.dados["tempo_fila"] / 60
        dt_aux = self.dados.loc[self.dados["tempo_fila"] < 50]
        fig = px.histogram(
            self.dados,
            x="tempo_fila",
            histnorm="probability density",
            color="prioridade",
            nbins=100,
        )
        # fig.show()

        media_fim = (
            self.dados.groupby(by=["prioridade", "processo"])
            .agg({"tempo_fila": "mean"})
            .reset_index()
        )
        media_fim["tempo_fila"] = media_fim["tempo_fila"] / 60
        fig = px.bar(
            media_fim,
            x="prioridade",
            color="processo",
            y="tempo_fila",
            title="Media de tempo em fila por prioridade de Atendimento por processo",
        )  # markers=True)
        # fig.show()

        media_acolhimento = np.mean(
            media_fim.loc[
                ((media_fim.processo == "triagem") | (media_fim.processo == "ficha"))
            ]["tempo_fila"]
        )
        print(f"{media_acolhimento = }")
        print(media_fim.loc[media_fim.processo == "clinico"])

    def fecha_estatisticas_experimento(self):
        def calc_ic(lista):
            confidence = 0.95
            n = len(lista)
            # mean_se: Erro Padrão da Média
            mean_se = stats.sem(lista)
            h = mean_se * stats.t.ppf((1 + confidence) / 2.0, n - 1)
            # Intervalo de confiança: mean, +_h
            return h

        calcula_corridas = False
        estatisticas_v2 = True

        if estatisticas_v2:
            # Calculo do Tempo no Sistema (TS), Tempo de Atendimento (TA) e Tempo em Fila (TF)
            tempos_sistema_por_replicacao = dict()
            # salvamento de métricas
            for n_sim_ in range(len(self.simulacoes)):
                tempos_sistema_por_replicacao[n_sim_] = deepcopy(
                    self.simulacoes[n_sim_].resultados_da_replicacao
                )
                self.simulacoes[n_sim_].resultados_da_replicacao = []

            # Calculos finais dos Tempos!
            medias_finais_TS = [
                v["media_TS"] for v in tempos_sistema_por_replicacao.values()
            ]
            medias_finais_TA = [
                v["media_TA_total"] for v in tempos_sistema_por_replicacao.values()
            ]
            medias_finais_TF = [
                v["media_TF_total"] for v in tempos_sistema_por_replicacao.values()
            ]
            dados_TS = [
                i for v in tempos_sistema_por_replicacao.values() for i in v["dados_TS"]
            ]
            dados_TA = [
                i / 60
                for v in tempos_sistema_por_replicacao.values()
                for i in v["dados_TA"]
            ]
            dados_TF = [
                i / 60
                for v in tempos_sistema_por_replicacao.values()
                for i in v["dados_TF"]
            ]

            TS_final = np.mean(medias_finais_TS)
            TA_final = np.mean(medias_finais_TA)
            TF_final = np.mean(medias_finais_TF)

            print(
                "TS: {0:.2f} \u00b1 {1:.2f} minutos (IC 95%)".format(
                    np.mean(medias_finais_TS), calc_ic(dados_TS)
                )
            )
            print(
                "TF: {0:.2f} \u00b1 {1:.2f} minutos (IC 95%)".format(
                    np.mean(medias_finais_TF), calc_ic(dados_TA)
                )
            )
            print(
                "TA: {0:.2f} \u00b1 {1:.2f} minutos (IC 95%)".format(
                    np.mean(medias_finais_TA), calc_ic(dados_TF)
                )
            )
            print(f"Diferença = {round(TA_final + TF_final - TS_final,2)}")

            # Calculos Finais das utilizações!
            print("-" * 90)
            print("Média de Utilização dos Recursos")
            print("-" * 90)
            rec_avaliados = [
                r
                for r in tempos_sistema_por_replicacao[0]["dict_utilizacao"].keys()
                if r != "Default_Aguarda_Medicacao"
            ]
            list_utilizacao_medias = list()
            for r in rec_avaliados:
                medias = [
                    v["dict_utilizacao"][r]["media_utilizacao"]
                    for v in tempos_sistema_por_replicacao.values()
                ]
                dados = [
                    i
                    for v in tempos_sistema_por_replicacao.values()
                    for i in v["dict_utilizacao"][r]["dados_utilizacao"]
                ]
                print(
                    "Media Utilização do recurso {0}: {1:.2f}% \u00b1 {2:.2f} % (IC 95%)".format(
                        r, np.round(np.mean(medias) * 100, 2), calc_ic(dados)
                    )
                )
                list_utilizacao_medias.append(
                    {"recurso": r, "utilizacao": np.mean(medias) * 100}
                )

            # Calculo final das entidades no sistema!
            media_das_medias_WIP = [
                v["media_NS_final"] for v in tempos_sistema_por_replicacao.values()
            ]
            media_das_medias_NA = [
                v["media_NA_final"] for v in tempos_sistema_por_replicacao.values()
            ]
            media_das_medias_NF = [
                v["media_NF_final"] for v in tempos_sistema_por_replicacao.values()
            ]
            dados_WIP_full = [
                i for v in tempos_sistema_por_replicacao.values() for i in v["dados_NS"]
            ]
            dados_NA_full = [
                i for v in tempos_sistema_por_replicacao.values() for i in v["dados_NA"]
            ]
            dados_NF_full = [
                i for v in tempos_sistema_por_replicacao.values() for i in v["dados_NF"]
            ]

            media_WIP = np.mean(media_das_medias_WIP)
            media_NA = np.mean(media_das_medias_NA)
            media_NF = np.mean(media_das_medias_NF)

            print(
                "NS: {0:.2f} \u00b1 {1:.2f} entidades (IC 95%)".format(
                    media_WIP, calc_ic(dados_WIP_full)
                )
            )
            print(
                "NF: {0:.2f} \u00b1 {1:.2f} entidades (IC 95%)".format(
                    media_NA, calc_ic(dados_NF_full)
                )
            )
            print(
                "NA: {0:.2f} \u00b1 {1:.2f} entidades (IC 95%)".format(
                    media_NF, calc_ic(dados_NA_full)
                )
            )
            print(f"Diferença = {round(media_NA + media_NF - media_WIP,2)}")

            if calcula_corridas:
                dados = [
                    v["dict_utilizacao"]["Clínico"]["media_tempo_fila_pr1_clinico"]
                    for v in tempos_sistema_por_replicacao.values()
                ]
                media = np.mean(dados)
                t = 2.776  # t4
                # t = 2.145 #t14
                # t = 2.021 #t40
                # t = 2.042 #t30
                desvio = np.std(dados)
                ic = [
                    round(media - (t * desvio / math.sqrt(self.replicacoes)), 4),
                    round(media + (t * desvio / math.sqrt(self.replicacoes)), 4),
                ]
                precisao_desejada = 1.7
                h = round((t * (desvio / math.sqrt(self.replicacoes))), 4)
                replicacoes_finais = np.ceil(
                    self.replicacoes * (h / precisao_desejada) ** 2
                )
                print(
                    f"{np.mean(media) = }" f" - {t = }",
                    f" - {ic = }",
                    f" - {h = }",
                    f" - {precisao_desejada = }",
                    f" - {replicacoes_finais = }",
                )

            return tempos_sistema_por_replicacao

        else:
            # Estatisticas antigas!
            TS = [
                (ent.saida_sistema - ent.entrada_sistema) / 60
                for sim in self.simulacoes
                for ent in sim.entidades.lista_entidades
                if ent.saida_sistema > 1
            ]
            TS2 = [
                (
                    (ent.saida_sistema - ent.entrada_sistema) / 60
                    if ent.saida_sistema > 1
                    else (self.duracao_simulacao - ent.entrada_sistema)
                )
                for sim in self.simulacoes
                for ent in sim.entidades.lista_entidades
            ]
            TA = self.df_estatisticas_entidades["tempo_processando"]
            TF = self.df_estatisticas_entidades["tempo_fila"]
            NA = self.df_estatisticas_recursos["em_atendimento"]
            NA2 = (
                self.df_estatisticas_recursos.groupby(by=["recurso"])
                .agg({"em_atendimento": "mean"})
                .reset_index()
                .em_atendimento
            )
            NF = self.df_estatisticas_recursos["tamanho_fila"]
            NF2 = (
                self.df_estatisticas_recursos.groupby(by=["recurso"])
                .agg({"tamanho_fila": "mean"})
                .reset_index()
                .tamanho_fila
            )
            NS = self.df_estatistcas_sistemas_brutos["WIP"]
            USO = self.df_estatisticas_recursos["utilizacao"]

            TS_ = round(np.mean(TS), 2)
            TS2_ = round(np.mean(TS2), 2)
            TA_ = round(
                np.mean(self.df_estatisticas_entidades["tempo_processando"]) / 60, 2
            )
            TF_ = round(np.mean(self.df_estatisticas_entidades["tempo_fila"]) / 60, 2)
            NA_ = round(
                np.mean(self.df_estatisticas_recursos["em_atendimento"]) / 60, 2
            )
            NA2_ = round(
                sum(
                    self.df_estatisticas_recursos.groupby(by=["recurso"])
                    .agg({"em_atendimento": "mean"})
                    .reset_index()
                    .em_atendimento
                ),
                2,
            )
            NF_ = round(np.mean(self.df_estatisticas_recursos["tamanho_fila"]), 2)
            NF2_ = round(
                sum(
                    self.df_estatisticas_recursos.groupby(by=["recurso"])
                    .agg({"tamanho_fila": "mean"})
                    .reset_index()
                    .tamanho_fila
                ),
                2,
            )
            NS_ = round(np.mean(self.df_estatistcas_sistemas_brutos["WIP"]), 2)
            USO_ = round(np.mean(self.df_estatisticas_recursos["utilizacao"]), 2)

            df_aux = (
                self.df_estatistcas_sistemas_brutos.groupby(
                    by=["processo", "Replicacao"]
                )
                .agg({"WIP": "count"})
                .reset_index()
            )
            chegadas = np.mean(df_aux.loc[df_aux.processo == "chegada"]["WIP"])
            saidas = np.mean(df_aux.loc[df_aux.processo == "saida"]["WIP"])
            df_wip = (
                self.df_estatistcas_sistemas_brutos.groupby(by=["Replicacao"])
                .agg({"WIP": "mean"})
                .reset_index()
            )
            WIP = round(np.mean([self.df_estatistcas_sistemas_brutos["WIP"]]))
            print(f"Chegadas: {chegadas} entidades")
            print(f"Saidas:   {saidas} entidades")
            print(f"WIP:      {WIP} entidades")
            print()
            comprimento_linha = 100
            print("=" * comprimento_linha)
            print("Indicadores de Desempenho do Sistema", end="\n")
            print("=" * comprimento_linha)

            # TODO: Preciso calcular recursos/entidades por processo ?
            print(
                "NS: {0:.2f} \u00b1 {1:.2f} entidades (IC 95%)".format(
                    np.mean(NS_), calc_ic(NS)
                )
            )
            print(
                "NF: {0:.2f} \u00b1 {1:.2f} entidades (IC 95%)".format(
                    np.mean(NF_), calc_ic(NF)
                )
            )
            print(
                "NF: {0:.2f} \u00b1 {1:.2f} entidades (IC 95%) - FORMA DE CÁLCULO 2".format(
                    np.mean(NF2_), calc_ic(NF2)
                )
            )
            print(
                "NA: {0:.2f} \u00b1 {1:.2f} entidades (IC 95%)".format(
                    np.mean(NA_), calc_ic(NA)
                )
            )
            print(
                "NA: {0:.2f} \u00b1 {1:.2f} entidades (IC 95%) - FORMA DE CÁLCULO 2".format(
                    np.mean(NA2_), calc_ic(NA2)
                )
            )
            print(
                "TS: {0:.2f} \u00b1 {1:.2f} minutos (IC 95%)".format(
                    np.mean(TS_), calc_ic(TS)
                )
            )
            print(
                "TS: {0:.2f} \u00b1 {1:.2f} minutos (IC 95%) - FORMA DE CÁLCULO CONSIDERANDO WIPS".format(
                    np.mean(TS2_), calc_ic(TS2)
                )
            )
            print(
                "TF: {0:.2f} \u00b1 {1:.2f} minutos (IC 95%)".format(
                    np.mean(TF_), calc_ic(TF)
                )
            )
            print(
                "TA: {0:.2f} \u00b1 {1:.2f} minutos (IC 95%)".format(
                    np.mean(TA_), calc_ic(TA)
                )
            )
            print(
                "USO:{0:.2f}% \u00b1 {1:.2f}%  (IC 95%)".format(
                    np.mean(USO) * 100, calc_ic(USO) * 100
                )
            )
            print("=" * comprimento_linha, end="\n")

            # TODO: Usar resultados finais do artigo como atributo da classe ou retorno da função?
            # Definição dos valores finais para salvamento e gráficos:
            self.numero_atendimentos = (
                saidas  # TODO: checar porque está saindo mais gente do que entrando!!
            )
            self.utilizacao_media = np.mean(USO) * 100
            self.media_em_fila_geral = (np.mean(TF_), calc_ic(TF))
            self.df_media_fila_por_prioridade = (
                self.df_estatisticas_entidades.groupby(by=["prioridade"])
                .agg({"tempo_fila": "mean"})
                .reset_index()
            )
            self.df_media_fila_por_prioridade["media_minutos"] = round(
                self.df_media_fila_por_prioridade["tempo_fila"] / 60, 2
            )
            self.utilizacao_media_por_recurso = (
                self.df_estatisticas_recursos.groupby(by=["recurso"])
                .agg({"utilizacao": "mean"})
                .reset_index()
            )
