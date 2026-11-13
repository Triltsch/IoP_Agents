# Woche 2: Kooperation und Kommunikation über OPC UA

[🇬🇧 English](README.md) · **🇩🇪 Deutsch**

Die simulierte Fabrik wird an das Fertigungsprotokoll OPC UA angebunden: Ein Server veröffentlicht Maschinendaten, Clients abonnieren sie, ein HOT-Monitor setzt `RepairNeeded`, und die Mesa-Agenten schreiben ihren Zustand auf den Server.

## Notebooks (Ordner `en` und `de`)

| Notebook | Thema |
|---|---|
| `01_OPC_Server_showcase` | OPC UA-Server der Fabrik (Maschinen `M01…`, `Temperature`, `State`, `Busy`, `RepairNeeded`). **Zuerst starten und laufen lassen.** |
| `02_OPC_PubSub_Clients_showcase` | Publish/Subscribe-Clients: Polling vs. Subscription |
| `03_OPC_Hot_Monitor_Client_showcase` | HOT-Monitor-Client (Polling- und Subscription-Variante); der Code liegt auch als `OPC_Hot_Monitor_Client_<Sprache>.py` vor |
| `04_Reactive_Agents_OPC_student` / `_solution` | Mesa-Agenten mit OPC UA-Kopplung über einen gemeinsamen Puffer; die Student-Version enthält drei Lücken (TODO 1–3) |

## Dateien

- `OPC_Hot_Monitor_Client_de.py` / `OPC_Hot_Monitor_Client_en.py`: der HOT-Monitor als Modul, von Notebook 04 importiert. Die Datei muss im selben Ordner wie das Notebook liegen.

## Hinweise

- Die Notebooks verwenden `nest_asyncio` und `wait-for2==0.3.2` (siehe `../binder/environment.yml`).
- Beenden Sie die Hintergrundtasks mit den letzten Zellen von Notebook 04, bevor Sie den Server neu starten.
