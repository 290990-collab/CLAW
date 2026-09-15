## Orchestrazione: orchestratore e worker

Il modello di questo progetto, e il default del framework. Il coordinatore spawna i subagent e ne riceve il report; **i subagent non comunicano lateralmente**: una domanda fuori mandato torna al coordinatore, che la gira a chi serve. Il parallelo segue la regola 1, il riuso della sessione la regola 8.
