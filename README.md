# Simulação de UPA (Unidade de Pronto Atendimento)

## 📋 Descrição

Este projeto implementa uma simulação discreta de eventos de uma Unidade de Pronto Atendimento (UPA) utilizando a biblioteca SimPy. O sistema simula o fluxo de pacientes através de diferentes processos médicos, incluindo triagem, consultas clínicas e pediátricas, exames e medicações.

## 🎯 Objetivos

- Simular o fluxo de pacientes em uma UPA
- Analisar diferentes cenários de alocação de recursos
- Avaliar tempos de espera e utilização de recursos
- Comparar cenários "As Is" (atual) com cenários "To Be" (propostos)
- Gerar relatórios e gráficos de performance

## 🏗️ Arquitetura do Sistema

### Processos Simulados

1. **Ficha** - Registro do paciente
2. **Triagem** - Avaliação inicial e classificação de prioridade
3. **Consulta Clínica** - Atendimento médico geral
4. **Consulta Pediátrica** - Atendimento pediátrico
5. **Exames** - Sangue, urina, raio-x, eletrocardiograma
6. **Medicação** - Aplicação e administração de medicamentos

### Recursos Simulados

- Secretária
- Enfermeira de Triagem
- Clínico
- Pediatra
- Técnica de Enfermagem
- Raio-x
- Eletrocardiograma
- Espaço para medicação

### Classificação de Prioridades

- **Prioridade 1 (Laranja)**: 1.7% - Mais grave
- **Prioridade 2 (Amarelo)**: 13.9% - Grave
- **Prioridade 3 (Verde)**: 80.1% - Moderado
- **Prioridade 4 (Azul)**: 0.1% - Leve
- **Prioridade 5 (Branco)**: 3.2% - Muito leve

## 📁 Estrutura do Projeto

```
SimulacaoUpa/
├── ProjetoUPA/
│   ├── Modelos.py              # Classes principais da simulação
│   ├── Rodada_Upa.py           # Script principal de execução
│   ├── main.py                 # Arquivo de entrada (não utilizado)
│   ├── backup_graficos.py      # Backup de geração de gráficos
│   └── gera_graficos_finais.py # Geração de gráficos finais
├── dados_recursos.csv          # Dados de recursos exportados
├── RESULTADOS_FINAIS - *.xlsx  # Relatórios por cenário
├── requirements.txt            # Dependências Python
└── README.md                   # Este arquivo
```

## 🚀 Instalação e Configuração

### Pré-requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)

### Instalação

1. **Clone o repositório:**
   ```bash
   git clone <url-do-repositorio>
   cd SimulacaoUpa
   ```

2. **Crie um ambiente virtual:**
   ```bash
   python -m venv venv
   ```

3. **Ative o ambiente virtual:**
   - Windows:
     ```bash
     venv\Scripts\activate
     ```
   - Linux/Mac:
     ```bash
     source venv/bin/activate
     ```

4. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

## 🎮 Como Usar

### Execução Principal

Para executar a simulação completa com todos os cenários:

```bash
cd ProjetoUPA
python Rodada_Upa.py
```

### Cenários Disponíveis

O sistema simula 5 cenários diferentes:

1. **To Be 1**: Redução de secretárias (1 em vez de 2)
2. **As Is**: Cenário atual (baseline)
3. **To Be 2**: Aumento de recursos (raio-x, eletro, técnicos, espaço medicação)
4. **To Be 3**: Aumento de secretárias e enfermeiras de triagem
5. **To Be 4**: Aumento de secretárias, enfermeiras e clínicos

### Parâmetros de Simulação

- **Duração**: 30 dias (2.592.000 segundos)
- **Warm-up**: 5 dias (432.000 segundos)
- **Replicações**: 55 por cenário
- **Taxa de chegada**: Distribuição exponencial (λ = 0.0029)

## 📊 Saídas e Resultados

### Arquivos Gerados

1. **Planilhas Excel** (`RESULTADOS_FINAIS - [Cenário].xlsx`):
   - Estatísticas discretas por replicação
   - Estatísticas contínuas por replicação
   - Tempos de espera, utilização de recursos, WIP

2. **CSV de Recursos** (`dados_recursos.csv`):
   - Dados detalhados de utilização de recursos
   - Tempos de fila por processo e prioridade

3. **Gráficos Interativos** (Plotly):
   - Utilização média de recursos por cenário
   - Tempos de fila por processo
   - Análise por prioridade de paciente
   - Comparações entre cenários

### Métricas Analisadas

- **Tempo de Espera**: Tempo médio na fila por processo
- **Utilização de Recursos**: Percentual de utilização de cada recurso
- **WIP (Work in Process)**: Número médio de pacientes no sistema
- **Throughput**: Número de pacientes atendidos
- **Análise por Prioridade**: Performance para diferentes níveis de urgência

## 🔧 Configuração Avançada

### Modificando Distribuições

As distribuições de tempo estão definidas na função `distribuicoes_base()` em `Rodada_Upa.py`:

```python
def distribuicoes_base(processo, slot="None"):
    dados = {
        "Chegada": expovariate(0.0029),
        "Ficha": random.triangular(2*2.1*60, 7*2.1*60, 4*2.1*60),
        "Triagem": random.triangular(4*1.3*60, 9*1.3*60, 7*1.6*60),
        # ... outros processos
    }
    return dados[processo]
```

### Adicionando Novos Cenários

Para adicionar um novo cenário, modifique a lista `cenarios` em `Rodada_Upa.py`:

```python
Cenario(
    nome="Novo Cenário",
    recursos={
        "Secretária": [3, False],
        "Enfermeira de Triagem": [3, False],
        # ... outros recursos
    },
    distribuicoes=distribuicoes_base,
)
```

## 📈 Análise dos Resultados

### Interpretação dos Gráficos

1. **Utilização de Recursos**: Valores altos (>80%) indicam gargalos
2. **Tempos de Fila**: Comparar com benchmarks da área médica
3. **Análise por Prioridade**: Verificar se pacientes críticos são atendidos rapidamente

### Comparação de Cenários

- **To Be 1**: Avalia impacto da redução de secretárias
- **To Be 2**: Testa aumento de capacidade de exames
- **To Be 3**: Foca na melhoria do processo de entrada
- **To Be 4**: Combina melhorias de entrada e atendimento

## 🛠️ Dependências Principais

- **SimPy**: Framework de simulação discreta de eventos
- **Pandas**: Manipulação e análise de dados
- **Plotly**: Geração de gráficos interativos
- **NumPy**: Computação numérica
- **SciPy**: Estatísticas e otimização
- **OpenPyXL**: Manipulação de arquivos Excel

## 🤝 Contribuição

Para contribuir com o projeto:

1. Faça um fork do repositório
2. Crie uma branch para sua feature (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -am 'Adiciona nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

## 📝 Licença

Este projeto está sob a licença [inserir tipo de licença]. Veja o arquivo LICENSE para mais detalhes.

## 👥 Autores

[Inserir informações dos autores]

## 📞 Suporte

Para dúvidas ou problemas, abra uma issue no repositório ou entre em contato através de [inserir contato].

---

**Nota**: Este projeto foi desenvolvido para fins acadêmicos e de pesquisa em simulação de sistemas de saúde. 