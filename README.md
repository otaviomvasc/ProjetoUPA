# UPA Simulation (Emergency Care Unit)

## 📋 Description

This repository contains the implementation of a discrete-event simulation framework developed for the research paper "A Generic Simulation Framework for Emergency Care Units: Modeling Patient Flow and Resource Utilization" using the lib Simpy. The project includes the datasets and statistical distributions used, the simulation code, the model structure representing the patient flow, and the methods employed to generate the visualizations used in the analysis of the system, resource utilization and potential bottlenecks.



## 🎯 Objectives

- Simulate patient flow in an emergency care unit
- Analyze different resource allocation scenarios
- Evaluate waiting times and resource utilization
- Compare "As Is" (current) and "To Be" (proposed) scenarios
- Generate performance reports and charts

## 🏗️ System Architecture

### Simulated Processes

1. **Registration** - Patient check-in
2. **Triage** - Initial assessment and priority classification
3. **Clinical Consultation** - General medical care
4. **Pediatric Consultation** - Pediatric care
5. **Exams** - Blood, urine, X-ray, electrocardiogram
6. **Medication** - Medication application and administration

### Simulated Resources

- Secretary
- Triage Nurse
- Clinician
- Pediatrician
- Nursing Technician
- X-ray
- Electrocardiogram
- Medication Space

### Priority Classification

- **Priority 1 (Orange):** 1.7% - Most severe
- **Priority 2 (Yellow):** 13.9% - Severe
- **Priority 3 (Green):** 80.1% - Moderate
- **Priority 4 (Blue):** 0.1% - Mild
- **Priority 5 (White):** 3.2% - Very mild

## 📁 Project Structure

```
SimulacaoUpa/
├── ProjetoUPA/
│   ├── Modelos.py              # Main simulation classes
│   ├── Rodada_Upa.py           # Main execution script
│   ├── main.py                 # Entry file (not used)
│   ├── backup_graficos.py      # Chart generation backup
│   └── gera_graficos_finais.py # Final chart generation
├── dados_recursos.csv          # Exported resource data
├── RESULTADOS_FINAIS - *.xlsx  # Scenario reports
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## 🚀 Installation & Setup

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd SimulacaoUpa
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment:**
   - Windows:
     ```bash
     venv\Scripts\activate
     ```
   - Linux/Mac:
     ```bash
     source venv/bin/activate
     ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## 🎮 How to Use

### Main Execution

To run the full simulation with all scenarios:

```bash
cd ProjetoUPA
python Rodada_Upa.py
```

### Available Scenarios

The system simulates 5 different scenarios:

1. **To Be 1**: Reduced number of secretaries (1 instead of 2)
2. **As Is**: Current scenario (baseline)
3. **To Be 2**: Increased resources (X-ray, ECG, technicians, medication space)
4. **To Be 3**: Increased secretaries and triage nurses
5. **To Be 4**: Increased secretaries, nurses, and clinicians

### Simulation Parameters

- **Duration:** 30 days (2,592,000 seconds)
- **Warm-up:** 5 days (432,000 seconds)
- **Replications:** 55 per scenario
- **Arrival rate:** Exponential distribution (λ = 0.0029)

## 📊 Outputs & Results

### Generated Files

1. **Excel Spreadsheets** (`RESULTADOS_FINAIS - [Scenario].xlsx`):
   - Discrete statistics per replication
   - Continuous statistics per replication
   - Waiting times, resource utilization, WIP

2. **Resource CSV** (`dados_recursos.csv`):
   - Detailed resource utilization data
   - Queue times by process and priority

3. **Interactive Charts** (Plotly):
   - Average resource utilization by scenario
   - Queue times by process
   - Analysis by patient priority
   - Scenario comparisons

### Analyzed Metrics

- **Waiting Time:** Average queue time per process
- **Resource Utilization:** Utilization percentage of each resource
- **WIP (Work in Process):** Average number of patients in the system
- **Throughput:** Number of patients served
- **Priority Analysis:** Performance for different urgency levels

## 🔧 Advanced Configuration

### Modifying Distributions

Time distributions are defined in the `distribuicoes_base()` function in `Rodada_Upa.py`:

```python
def distribuicoes_base(processo, slot="None"):
    coef_processos = 60
    coef_chegadas = 60
    coef_checkin = 60
    dados = {
        "Chegada": expovariate(0.0029),
        "Ficha": max(0.5, random.lognormvariate(0.460, 0.576)) * coef_chegadas,
        "Triagem": max(0.6, random.weibullvariate(2.526, 2.485)) * coef_chegadas,
        "Clínico": max(4.53, random.weibullvariate(6.878, 2.832)) * coef_chegadas,
        "Pediatra": max(5.34, random.gauss(14.022, 5.966)) * coef_chegadas,
        "Raio-x": 5 * coef_chegadas,  # 5 minutes
        "Eletro": 12 * coef_chegadas,  # 12 minutes
        "Exame de Urina": 2 * coef_chegadas,  # 2 minutes
        "Exame de Sangue": 3 * coef_chegadas,  # 3 minutes
        "Análise de Sangue Externo": 0.25 * 60 * coef_chegadas,  # 15 minutes
        "Análise de Sangue Interno": 0.1 * 60 * coef_chegadas,  # 6 minutes
        "Análise de Urina": 2 * 60 * coef_chegadas,  # 120 minutes (2 hours)
        "Aplicar Medicação": random.triangular(
            10 * coef_chegadas, 60 * coef_chegadas, 40 * coef_chegadas
        ),
        "Tomar Medicação": random.gauss(35.350, 2.443) * coef_chegadas,
    }
    return dados[processo]
```

**Distribution Details:**
- All times are in seconds (multiplied by `coef_chegadas = 60` for conversion)
- **Arrival:** Exponential distribution with rate λ = 0.0029
- **Registration (Ficha):** Lognormal distribution (μ=0.460, σ=0.576), minimum 0.5
- **Triage:** Weibull distribution (shape=2.526, scale=2.485), minimum 0.6
- **Clinical Consultation:** Weibull distribution (shape=6.878, scale=2.832), minimum 4.53
- **Pediatric Consultation:** Normal distribution (μ=14.022, σ=5.966), minimum 5.34
- **Medication Application:** Triangular distribution (min=10, max=60, mode=40 minutes)
- **Medication Administration:** Normal distribution (μ=35.350, σ=2.443 minutes)

### Parallel Execution of Scenarios

The simulation implements **parallel execution** of scenario runs using `concurrent.futures.ThreadPoolExecutor`. This allows multiple scenarios to run simultaneously, significantly reducing total execution time.

**How it works:**
- Each scenario runs independently in a separate thread
- All scenarios execute in parallel (up to the number of available CPUs or number of scenarios)
- Results are collected as scenarios complete
- Each scenario generates its own Excel file (`RESULTADOS_FINAIS - [Scenario].xlsx`)

**Performance Benefits:**
- **Speed improvement:** With 5 scenarios, execution time is typically reduced by 3-5x (depending on hardware)
- **Resource utilization:** Makes efficient use of multi-core processors
- **Independence:** Each scenario's execution is isolated, ensuring no data conflicts

**Implementation details:**
The parallelization is implemented in the main execution block of `Rodada_Upa.py`:

```python
def rodar_cenario(cenario, dist_probabilidade, tempo, necessidade_recursos, 
                  ordem_processo, atribuicoes_processo, liberacao_recursos, 
                  warmup, replicacoes=55):
    """Wrapper function to run a scenario and return name and data"""
    dados_cenario = cenario.rodar(...)
    return cenario.nome, dados_cenario

# Parallel execution using ThreadPoolExecutor
with concurrent.futures.ThreadPoolExecutor(max_workers=len(cenarios)) as executor:
    futures = {
        executor.submit(rodar_cenario, cenario, ...): cenario.nome 
        for cenario in cenarios
    }
    
    for future in concurrent.futures.as_completed(futures):
        nome, dados_cenario = future.result()
        estatisticas_finais[nome] = dados_cenario
```

**Note:** The `if __name__ == "__main__":` guard is required for proper execution in all environments.

### Adding New Scenarios

To add a new scenario, modify the `cenarios` list in `Rodada_Upa.py`:

```python
Cenario(
    nome="New Scenario",
    recursos={
        "Secretária": [3, False],
        "Enfermeira de Triagem": [3, False],
        # ... other resources
    },
    distribuicoes=distribuicoes_base,
)
```

## 📈 Results Analysis

### Chart Interpretation

1. **Resource Utilization:** High values (>80%) indicate bottlenecks
2. **Queue Times:** Compare with healthcare benchmarks
3. **Priority Analysis:** Ensure critical patients are served quickly

### Scenario Comparison

- **To Be 1:** Evaluates impact of reducing secretaries
- **To Be 2:** Tests increased exam capacity
- **To Be 3:** Focuses on improving entry process
- **To Be 4:** Combines improvements in entry and care

## 🛠️ Main Dependencies

- **SimPy:** Discrete event simulation framework
- **Pandas:** Data manipulation and analysis
- **Plotly:** Interactive chart generation
- **NumPy:** Numerical computation
- **SciPy:** Statistics and optimization
- **OpenPyXL:** Excel file manipulation

---

**Note:** This project was developed for academic and research purposes in healthcare systems simulation. 