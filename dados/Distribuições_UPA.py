def distribuicoes(tipo):
    return {
        # Cada segundo real, representa 60 min 
        "Etapa_triagem": random.weibullvariate(2.217,1.658),
        "Intervalo_entre_triagens": random.weibullvariate(1.231,0.0),
        "Etapa_registro": random.lognormvariate(0.460,0.576),
        "Etapa_consulta_pediatra": random.gauss(14.022,5.966),
        "Etapa_consulta_clinica": random.weibullvariate(6.878,2.832),
        "Etapa_enfermaria": random.expovariate(0.571),
        "Etapa_medicacao": random.gauss(35.350,2.443), #tempo da bolsa descer e a pessoa ficar de observação
        }.get(tipo,0.0)