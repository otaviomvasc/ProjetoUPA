import pandas as pd
import plotly.express as px

"""
Arquivo para gerar gráficos a partir do excel gerado pela simulação.
Foi a solução que encontrei para gerar os plots porque o computador não conseguiu rodar
com 30 replicações cada cenário.
"""

def retorna_prioridade(paciente, lista_entidades):
    try:
        prioridade = next(ent.atributos['prioridade'] for ent in lista_entidades if paciente == ent.nome)
        return prioridade
    except KeyError:
        return "Nao Passou da Triagem"


# def analises_tempo_artigo():
#     # tempo médio espera para ficha e triagem
#     tempo_medio_ficha_e_triagem = np.mean(
#         self.entidades.df_entidades.loc[((self.entidades.df_entidades.processo == "Ficha") | (
#                 self.entidades.df_entidades.processo == "Triagem"))]['tempo_fila']) / 60
#
#     tempo_medio_atendimento = np.mean(
#         self.entidades.df_entidades.loc[((self.entidades.df_entidades.processo == "Ficha") | (
#                 self.entidades.df_entidades.processo == "Triagem"))]['tempo_processando']) / 60
#     total = tempo_medio_ficha_e_triagem + tempo_medio_atendimento
#     print(f'{total} tempo de acolhimento total em minutos')
#
#     # tempo_medio_de_espera_para_pacientes:
#     print('-' * 90)
#     df_aux = self.entidades.df_entidades.loc[((self.entidades.df_entidades.processo != "Ficha") | (
#             self.entidades.df_entidades.processo != "Triagem"))]
#
#     df_tempo_fila_prioridade = df_aux.groupby(by=['prioridade_paciente']).agg(
#         {"tempo_fila": "mean"}).reset_index()
#     df_tempo_fila_prioridade['tempo_fila'] = round(df_tempo_fila_prioridade['tempo_fila'] / 60, 2)
#     print(f'{df_tempo_fila_prioridade =}')


def converte_segundos_em_dias(x):
    return x / 86400


def converte_segundos_em_semanas(x):
    return x / (86400 * 7)


def converte_segundos_em_meses(x):
    return x / (86400 * 30)

class Gera_graficos():
    def __init__(self, path):
        self.path =  path

    def cria(self):
        df_total_pacientes = pd.read_excel(self.path, sheet_name="df_total_pacientes")
        df_utilizacao_media = pd.read_excel(self.path, sheet_name="df_utilizacao_media")
        df_fila_media = pd.read_excel(self.path, sheet_name="df_fila_media")
        df_utilizacao_por_recurso = pd.read_excel(self.path, sheet_name="df_utilizacao_por_recurso")
        df_filas_por_prioridade = pd.read_excel(self.path, sheet_name="df_filas_por_prioridade")
        df_estatisticas_bruto = pd.read_csv("df_estatisticas_bruto.csv", sep=',')
        df_recursos = pd.read_csv("df_recursos.csv",sep=',')
        df_entidades = pd.read_csv("df_entidades.csv",sep=',')
        cenarios = list(pd.unique(df_total_pacientes.Cenario))

        graficos_de_todas_as_replicacoes_juntas = False
        dicionario_traduzido_recursos = {
            "Secretária": "Secretariat",  # De 2 para 1
            "Enfermeira de Triagem": "Nurse Screening",
            "Clínico": "Clinic",
            "Pediatra": "Pediatrician",
            "Raio-x": "X-Ray",
            "Eletro": "Electrocardiogram",
            "Técnica de Enfermagem": "Nursing Technician",
            "Espaço para tomar Medicação": "Medication Space"
        }

        dicionario_traduzido_processos = {
            "Ficha": "Registration of Patient",
            "Triagem": "Screening",
            "Clínico": " Clinical Consultation",
            "Pediatra": "Pediatric Consultation",
            "Aplicar Medicação": "Applying Medication",
            "Tomar Medicação": "Taking Medication",
            "Exame de Urina": "Urine Test",
            "Exame de Sangue": "Blood Test",
            "Análise de Urina": "Urine Test Analysis",
            "Análise de Sangue Externo": "External Blood Test Analysis",
            "Análise de Sangue Interno": "Internal Blood Test Analysis",
            "Raio-x": "X-Ray",
            "Eletro": "Electrocardiogram",
            "chegada": "Arrive",
            "saida": "Exit",
            "Aguarda Resultado de Exame": "Waiting Examination Results"
        }

        df_total_pacientes.rename(columns={"Cenario": "Scenarios", "Atendimentos": "Patients Seen"}, inplace=True)
        df_utilizacao_media.rename(columns={"Cenario": "Scenarios", "Utilização": "Resources Usage (%)"}, inplace=True)
        df_fila_media.rename(columns={"Cenario": "Scenarios", "Tempo_Médio_de_Fila": "Queue Average Time (Min)"},
                             inplace=True)
        df_utilizacao_por_recurso.rename(
            columns={"recurso": "Resource", "utilizacao": "Resources Usage (%)", "Cenário": "Scenarios"}, inplace=True)
        df_utilizacao_por_recurso['Resource'] = df_utilizacao_por_recurso.Resource.apply(
            lambda x: dicionario_traduzido_recursos[x])
        df_filas_por_prioridade.rename(
            columns={"prioridade": "Patient Priority", "media_minutos": "Queue Average (Min)", "Cenário": "Scenarios"},
            inplace=True)
        df_estatisticas_bruto.rename(columns={'cenario': "Scenarios", "Replicacao": "Run"}, inplace=True)
        df_recursos.rename(columns={'cenario': "Scenarios", "recurso": "Resource", "utilizacao": "Resources Usage (%)",
                                    "Replicacao": "Run"}, inplace=True)
        df_recursos['Resource'] = df_recursos.Resource.apply(lambda x: dicionario_traduzido_recursos[x])
        df_entidades.rename(columns={"entidade": "Entity", "processo": "Process", 'prioridade': "Patient Priority",
                                     'cenario': "Scenarios"}, inplace=True)
        df_entidades["Process"] = df_entidades["Process"].apply(lambda x: dicionario_traduzido_processos[x])
        df_entidades['Queue Time (Min)'] = round(df_entidades.tempo_fila / 60, 2)
        CHART_THEME = 'plotly_white'

        df_utilizacao_por_recurso["Resources Usage (%)"] = round(df_utilizacao_por_recurso["Resources Usage (%)"]/100,2) #voltando para porcentagem!!
        # Gerar gráficos de cada simulação para todas as corridas!!
        # Gráfico WIP!

        df_estatisticas_bruto['Scenario-Run'] = df_estatisticas_bruto.apply(
            lambda x: x.Scenarios + " - " + "Run " + str(x.Run), axis=1)
        df_scenario_run_WIP = df_estatisticas_bruto.groupby(by=['Scenario-Run', 'discretizacao', 'Scenarios']).agg(
            {"WIP": "mean"}).reset_index()
        duracao_dias_sr = [converte_segundos_em_dias(x) for x in
                           df_scenario_run_WIP.discretizacao]
        fig = px.line(df_scenario_run_WIP, x=duracao_dias_sr, y=df_scenario_run_WIP.WIP, color="Scenarios")
        fig.update_layout(title='Global Average Entities in Process (WIP)')
        fig.update_xaxes(title='Duration (D)', showgrid=False)
        fig.update_yaxes(title='Number os Patients')
        fig.layout.template = CHART_THEME
        fig.update_layout(title_x=0.5)

        fig.show()

        df_recursos['Scenario-Run'] = df_recursos.apply(lambda x: x.Scenarios + " - " + "Run " + str(x.Run), axis=1)
        df_recursos['Scenario-Run-Resource'] = df_recursos.apply(
            lambda x: x.Scenarios + " - " + "Run " + str(x.Run) + x.Resource, axis=1)
        df_recursos['Scenario-Resource'] = df_recursos.apply(lambda x: x.Scenarios + " - " + x.Resource, axis=1)
        # Média de todos os recursos por replicação!!!
        df_rec_scenario_run = df_recursos.groupby(by=['Scenario-Resource', 'T', 'Resource']).agg(
            {"Resources Usage (%)": "mean"}).reset_index()
        fig = px.line(df_rec_scenario_run,
                      x="T", y="Resources Usage (%)", color="Scenario-Resource",
                      title='Resources Utilization')  # hover_data='Scenario-Resource')
        fig.layout.template = CHART_THEME
        fig.update_xaxes(title='Duration (D)', showgrid=False)
        # fig.update_yaxes(title='Utilização dos Recursos (%)')
        fig.update_layout(title_x=0.5)
        fig.show()

        if graficos_de_todas_as_replicacoes_juntas:
            media_de_todas_as_replicações = True
            # Teste:
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

                df_2 = df_recursos.groupby(by=['Scenarios', 'Resource', 'T']).agg(
                    {"Resources Usage (%)": "mean"}).reset_index()
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
                # fig.layout.width = 1000
                fig.update_layout(title_x=0.5)

                fig.show()

            # Utilização dos recursos no tempo!
            fig = px.line(df_recursos,
                          x="T", y="Resources Usage (%)", color="Resource", title='Resources Utilization')
            fig.layout.template = CHART_THEME
            fig.update_xaxes(title='Duration (D)', showgrid=False)
            # fig.update_yaxes(title='Utilização dos Recursos (%)')
            fig.update_layout(title_x=0.5)
            fig.show()

        else:
            for cen in cenarios:
                df_estatisticas_aux = df_estatisticas_bruto.loc[df_estatisticas_bruto.Scenarios == cen]
                df_recursos_aux = df_recursos.loc[df_recursos.Scenarios == cen]
                df_entidades_aux = df_entidades.loc[df_entidades.Scenarios == cen]
                duracao_dias = [converte_segundos_em_dias(x) for x in df_estatisticas_aux.discretizacao]
                fig = px.line(df_estatisticas_aux, x=duracao_dias, y=df_estatisticas_aux.WIP,
                              color=df_estatisticas_aux["Run"])
                fig.update_layout(title=f'Entities in Process (WIP) Scenario {cen}')
                fig.update_xaxes(title='Duration (D)', showgrid=False)
                fig.update_yaxes(title='Number os Patients')
                fig.layout.template = CHART_THEME
                # fig.layout.width = 1000
                fig.update_layout(title_x=0.5)

                fig.show()

                # Utilização dos recursos no tempo!

                fig = px.line(df_recursos_aux,
                              x="T", y="Resources Usage (%)", color="Resource",
                              title=f'Resources Utilization Scenario {cen}')
                fig.layout.template = CHART_THEME
                fig.update_xaxes(title='Duration (D)', showgrid=False)
                # fig.update_yaxes(title='Utilização dos Recursos (%)')
                fig.update_layout(title_x=0.5)
                fig.show()

                # Média tempo fila por prioridade e processo
                df_tempo_fila_prioridade = df_entidades_aux.groupby(by=['Process', "Patient Priority"]).agg(
                    {"Queue Time (Min)": "mean"}).reset_index()
                df_tempo_fila_prioridade["Queue Time (Min)"] = round(df_tempo_fila_prioridade["Queue Time (Min)"], 2)
                fig = px.bar(df_tempo_fila_prioridade, x='Patient Priority', y='Queue Time (Min)', color='Process',
                             text="Queue Time (Min)", title=f"Process Queue Patient Priority in Scenario {cen}")

                fig.update_traces(texttemplate='%{text}')
                fig.layout.template = CHART_THEME
                fig.update_traces(textposition='outside')
                fig.update_yaxes(showticklabels=False)
                # fig.update_xaxes(showticklabels=False)
                fig.update_layout(title_x=0.5)
                fig.show()
                b = 0

        # Tempo médio e fila por processo
        df_tempo_fila_processo = df_entidades.groupby(by=['Scenarios', "Process"]).agg(
            {"Queue Time (Min)": "mean"}).reset_index()
        df_tempo_fila_processo["Queue Time (Min)"] = round(df_tempo_fila_processo["Queue Time (Min)"], 2)
        fig = px.bar(df_tempo_fila_processo, x='Process', y='Queue Time (Min)', color='Scenarios',
                     text="Queue Time (Min)", title="Process Queue Time by Scenarios")
        fig.update_traces(texttemplate='%{text}')
        fig.layout.template = CHART_THEME
        fig.update_traces(textposition='outside')
        fig.update_yaxes(showticklabels=False)
        # fig.update_xaxes(showticklabels=False)
        fig.update_layout(title_x=0.5)
        fig.show()

        # Tempo médio de fila por prioridade!
        df_tempo_fila_prioridade = df_entidades.groupby(by=['Scenarios', "Patient Priority"]).agg(
            {"Queue Time (Min)": "mean"}).reset_index()
        df_tempo_fila_prioridade["Queue Time (Min)"] = round(df_tempo_fila_prioridade["Queue Time (Min)"], 2)
        fig = px.bar(df_tempo_fila_prioridade, x='Patient Priority', y='Queue Time (Min)', color='Scenarios',
                     text="Queue Time (Min)", title="Process Queue Patient Priority")
        fig.update_traces(texttemplate='%{text}')
        fig.layout.template = CHART_THEME
        fig.update_traces(textposition='outside')
        fig.update_yaxes(showticklabels=False)
        # fig.update_xaxes(showticklabels=False)
        fig.update_layout(title_x=0.5)
        fig.show()

        # total de pacientes atendidos!
        fig = px.bar(df_total_pacientes, x='Scenarios', y='Patients Seen', text="Patients Seen",
                     title="Patients Seen by Scenarios")
        fig.update_traces(texttemplate='%{text}')
        fig.layout.template = CHART_THEME
        fig.update_traces(textposition='outside')
        fig.update_yaxes(showticklabels=False)
        fig.update_xaxes(showticklabels=False)
        fig.update_layout(title_x=0.5)
        fig.show()

        # Utiização Média de Recursos
        fig = px.bar(df_utilizacao_por_recurso, x='Resource', y='Resources Usage (%)', color='Scenarios',
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

        # Gráfico de utilização Cenário x Recurso
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

        # Filas por prioridade!
        fig = px.bar(df_filas_por_prioridade, x='Patient Priority', y='Queue Average (Min)', color='Scenarios',
                     barmode='group',
                     text='Queue Average (Min)', title='Patient Queues by Priority in Scenarios')  # text="nation"
        fig.update_traces(texttemplate='%{text:.2s}')
        fig.layout.template = CHART_THEME
        fig.update_traces(textposition='outside')
        # fig.update_yaxes(title='Fila Média (Min)', showgrid=False)
        # fig.update_xaxes(title='Prioridade do Paciente', showgrid=False)
        fig.update_yaxes(showticklabels=False)
        fig.update_layout(title_x=0.5)

        fig.show()

        # Filas por prioridade e processos!
        fig = px.bar(df_filas_por_prioridade, x='Scenarios', y='Queue Average (Min)', color='Patient Priority',
                     barmode='group',
                     text='Queue Average (Min)', title='Patient Queues by Priority in Scenarios')  # text="nation"
        fig.update_traces(texttemplate='%{text:.2s}')
        fig.layout.template = CHART_THEME
        fig.update_traces(textposition='outside')
        # fig.update_yaxes(title='Fila Média (Min)', showgrid=False)
        # fig.update_xaxes(title='Prioridade do Paciente', showgrid=False)
        fig.update_yaxes(showticklabels=False)
        fig.update_layout(title_x=0.5)

        fig.show()

if __name__ == "__main__":
    path = "dados_analise.xlsx"
    Gera_graficos(path=path).cria()