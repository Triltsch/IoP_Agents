# Week 2: cooperation and communication via OPC UA

**🇬🇧 English** · [🇩🇪 Deutsch](README.de.md)

The simulated factory is connected to the shop-floor protocol OPC UA: a server publishes machine data, clients subscribe, a HOT monitor sets `RepairNeeded`, and the Mesa agents write their state to the server.

## Notebooks (folders `en` and `de`)

| Notebook | Topic |
|---|---|
| `01_OPC_Server_showcase` | The OPC UA server of the factory (machines `M01…`, `Temperature`, `State`, `Busy`, `RepairNeeded`). **Start it first and keep it running.** |
| `02_OPC_PubSub_Clients_showcase` | Publish/subscribe clients: polling vs. subscription |
| `03_OPC_Hot_Monitor_Client_showcase` | HOT monitor client (polling and subscription variant); its code is also available as `OPC_Hot_Monitor_Client_<lang>.py` |
| `04_Reactive_Agents_OPC_student` / `_solution` | Mesa agents with OPC UA coupling through a shared buffer; the student version has three gaps (TODO 1–3) |

## Files

- `OPC_Hot_Monitor_Client_en.py` / `OPC_Hot_Monitor_Client_de.py`: the HOT monitor as module, imported by notebook 04. It must stay in the same folder as the notebook.

## Notes

- The notebooks use `nest_asyncio` and `wait-for2==0.3.2` (see `../binder/environment.yml`).
- Stop background tasks with the last cells of notebook 04 before you restart the server.
