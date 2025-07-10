# UPA Simulation (Emergency Care Unit)

## 📋 Description

Code for the manuscript titled "Evaluating the Efficiency of a Public Emergency Care Unit through Computer Simulation," which implements a discrete-event simulation of an Emergency Care Unit (UPA) using the SimPy library. The system simulates the flow of patients through various medical processes, including triage, clinical and pediatric consultations, exams, and medication administration.

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
    dados = {
        "Chegada": expovariate(0.0029),
        "Ficha": random.triangular(2*2.1*60, 7*2.1*60, 4*2.1*60),
        "Triagem": random.triangular(4*1.3*60, 9*1.3*60, 7*1.6*60),
        # ... other processes
    }
    return dados[processo]
```

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