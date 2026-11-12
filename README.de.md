# Internet of Production – Teil Agentensysteme: Praktikumsmaterial

[🇬🇧 English](README.md) · **🇩🇪 Deutsch**

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/Triltsch/IoP_Agents/HEAD?urlpath=lab)

Übungen zum Teil Agentensysteme der Vorlesung *Internet of Production* (Ostfalia Hochschule für angewandte Wissenschaften). Ein roter Faden zieht sich durch alle drei Wochen: **eine Fabrik, deren Maschinen sich erhitzen, ein Koordinator, der den HOT-Zustand erkennt, und ein Wartungsagent, der die Maschinen repariert** – zuerst als reaktive Agenten (Mesa), dann über OPC UA an die Fertigungsebene angebunden, schließlich orchestriert mit LangGraph, MCP und einem LLM.

## Start

- **Ohne Installation:** Binder-Badge oben anklicken (Umgebung: `binder/environment.yml`). Der erste Start kann einige Minuten dauern.
- **Lokal:** `conda env create -f binder/environment.yml`, dann `conda activate iop-agents` und den Kernel registrieren:
  `python -m ipykernel install --user --name iop-agents --display-name "Python (iop-agents)"`

## Struktur

Ein Ordner je Vorlesungswoche, ein Unterordner je Sprache (`en`, `de`). Wo eine Übung Lücken für die Studierenden enthält, gibt es sie als `_student` (mit Lücken `___` und `# TODO`) und `_solution`; die übrigen Notebooks sind durchgerechnete Beispiele (`_solution`).

| Ordner | Inhalt |
|---|---|
| `W1_Reactive_Agents` | **Woche 1:** reaktive Agenten in Mesa 3 (Sense–Decide–Act): Maschinen-, Wartungs- und Auftragsagenten auf einem Gitter |
| `W2_Cooperation_Communication` | **Woche 2:** 01 OPC UA-Server der Fabrik; 02 Publish/Subscribe-Clients; 03 HOT-Monitor-Client; 04 Mesa-Agenten über einen gemeinsamen Puffer an OPC UA gekoppelt (`_student` mit drei Lücken) |
| `W3_Frameworks_LangGraph_MCP` | **Woche 3:** 01 zustandsbehaftete Agenten mit LangGraph; 02 MCP-Server/-Client und LLM-Koordinator (Stub, ohne API-Key); 03 dasselbe mit echter LLM-API |
| `binder/` | Umgebung für Binder und lokale Nutzung |

## Empfohlene Reihenfolge

Woche 1 → Woche 2 → Woche 3. In Woche 2 zuerst den OPC UA-Server (Notebook 01) starten und während der Arbeit an 02–04 laufen lassen.

## Hinweise

- Das Notebook `W3/03_MCP_LLM_API_solution` benötigt einen API-Key in der Umgebungsvariable `OPENAI_API_KEY`. Schreiben Sie nie einen Key in ein Notebook und checken Sie ihn nicht ein.
- Fest gewählte Versionen: Mesa 3.0.3 und `wait-for2==0.3.2` (von `asyncua` benötigt). Andere Versionen sind mit diesen Notebooks nicht getestet.
