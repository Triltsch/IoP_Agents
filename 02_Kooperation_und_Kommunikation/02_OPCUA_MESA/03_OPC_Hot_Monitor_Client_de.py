#!/usr/bin/env python
# coding: utf-8

# # AsyncUA HOT-Monitor-Client für Fabrikmaschinen
# 
# Dieses Notebook implementiert einen **eigenständigen OPC UA-Client**, der folgendes Verhalten umsetzt:
# 
# - Maschinenknotenwerte pollen oder abonnieren
# - **HOT**-Zustände bei Maschinentemperaturen erkennen
# - prüfen, ob bereits ein Reparaturauftrag vorhanden ist
# - einen Reparaturauftrag durch Setzen einer OPC UA-Variable anlegen
# 
# Es ist dafür ausgelegt, mit einem Fabrik-Server zusammenzuarbeiten, der diese Adressraumstruktur bereitstellt:
# 
# ```text
# Objects
#  └─ Factory
#      ├─ Machines
#      │   ├─ M01
#      │   │   └─ Temperature
#      │   ├─ M02
#      │   │   └─ Temperature
#      │   └─ ...
#      └─ Maintenance
#          └─ Jobs
#              ├─ M01_RepairNeeded
#              ├─ M02_RepairNeeded
#              └─ ...
# ```
# 
# Annahmen (im Code leicht anpassbar):
# 
# - `Temperature` ist ein `Double`-Wert für jede Maschine.
# - Jede `Mxx_RepairNeeded`-Variable unter `Factory/Maintenance/Jobs` ist eine **boolesche** Variable:
#   - `False` → kein Reparaturauftrag vorhanden.
#   - `True`  → Reparaturauftrag bereits angelegt.
# 
# Der Client kann in zwei Modi betrieben werden:
# 
# - **Polling-Modus** – liest Temperaturen regelmäßig und wertet HOT-Bedingungen aus.
# - **Subscription-Modus** – nutzt OPC UA-Subscriptions, um auf Datenaenderungen zu reagieren.
# 

# ## 1. Benötigte Pakete installieren
# 
# Falls `asyncua`, `nest_asyncio` und `wait-for2==0.3.2` noch nicht installiert sind, führen Sie die folgende Zelle einmalig aus.
# 

# In[ ]:


#!pip install -U asyncua nest_asyncio wait-for2==0.3.2


# ## 2. Imports, Konfiguration und Event-Loop-Einrichtung
# 
# Wir konfigurieren den OPC UA-Endpunkt und die Namespace-URI passend zum Fabrik-Server
# und bereiten `nest_asyncio` vor, damit wir `await` in Jupyter komfortabel nutzen können.
# 

# In[1]:


import asyncio
from datetime import datetime
from typing import Dict, Optional

import nest_asyncio
nest_asyncio.apply()

from asyncua import ua, Client

# Konfiguration – diese Konstanten anpassen, falls der Server andere Werte verwendet
SERVER_URL = "opc.tcp://localhost:4840/freeopcua/server/"
FACTORY_NS_URI = "http://ostfalia.de/ipt/factory"

# Konfiguration der HOT-Erkennung
HOT_THRESHOLD = 60.0  # °C – Temperaturen ab diesem Wert gelten als HOT

print("Event-Loop eingerichtet. Server-Endpunkt:", SERVER_URL)
print("HOT-Schwellenwert:", HOT_THRESHOLD, "°C")


# ## 3. Maschinenerkennung und Browse-Hilfsfunktionen
# 
# Wir nehmen an, dass:
# 
# - alle Maschinen direkte Kinder von `Factory/Machines` sind und
# - alle Reparaturauftrag-Flags Kinder von `Factory/Maintenance/Jobs` sind,
#   mit Namen nach dem Muster `Mxx_RepairNeeded`.
# 
# Die folgende Hilfsfunktion erkennt alle Maschinen und sammelt die relevanten Knoten.
# 

# In[2]:


class MachineNodes:
    """Hilfscontainer für die wichtigen Knoten einer Maschine."""

    def __init__(self, name: str, obj_node, temp_node, job_node):
        self.name = name
        self.obj_node = obj_node
        self.temp_node = temp_node
        self.job_node = job_node

    def __repr__(self) -> str:
        return (
            f"MachineNodes(name={self.name!r}, "
            f"temp={self.temp_node.nodeid}, job={self.job_node.nodeid})"
        )


async def discover_machines_with_jobs(client: Client) -> Dict[str, MachineNodes]:
    """Alle Maschinen sowie ihre Temperature- und RepairNeeded-Knoten ermitteln.

    Struktur:

        Objects
         └─ Factory
             ├─ Machines
             │   └─ Mxx / Temperature
             └─ Maintenance
                 └─ Jobs / Mxx_RepairNeeded

    Gibt ein Dictionary zurück, das nach Maschinenname (z. B. 'M01') indiziert ist.
    """
    ns = await client.get_namespace_index(FACTORY_NS_URI)
    print(f"[DISCOVERY] Namespace index for {FACTORY_NS_URI!r}: {ns}")

    objects = client.nodes.objects
    factory = await objects.get_child([f"{ns}:Factory"])

    machines_folder = await factory.get_child([f"{ns}:Machines"])
    maintenance = await factory.get_child([f"{ns}:Maintenance"])
    jobs_folder = await maintenance.get_child([f"{ns}:Jobs"])

    machine_nodes: Dict[str, MachineNodes] = {}

    for mobj in await machines_folder.get_children():
        bname = await mobj.read_browse_name()
        name = bname.Name  # e.g. 'M01', 'M02', ...

        if not name.startswith("M") or len(name) != 3:
            # Nicht-Maschinenknoten überspringen
            print(f"[DISCOVERY] Skipping non–machine node: {bname}")
            continue

        # Temperature-Knoten unter der Maschine
        try:
            temp_node = await mobj.get_child([f"{ns}:Temperature"])
        except Exception as exc:
            print(f"[DISCOVERY] {name}: missing Temperature node ({exc})")
            continue

        # Boolesches Job-Flag: M01_RepairNeeded, M02_RepairNeeded, ...
        job_name = f"{name}_RepairNeeded"
        try:
            job_node = await jobs_folder.get_child([f"{ns}:{job_name}"])
        except Exception as exc:
            print(f"[DISCOVERY] {name}: missing job node '{job_name}' ({exc})")
            continue

        machine_nodes[name] = MachineNodes(name, mobj, temp_node, job_node)
        print(
            f"[DISCOVERY] {name}: temp={temp_node.nodeid}, job={job_node.nodeid}"
        )

    return machine_nodes


# ## 4. HOT-Erkennung und Auftragsverwaltung
# 
# Das Verhalten ist wie folgt definiert:
# 
# - Eine Temperatur gilt als **HOT**, wenn sie größer oder gleich `HOT_THRESHOLD` ist.
# - Ein Reparaturauftrag *existiert*, wenn das entsprechende `Mxx_RepairNeeded`-Flag `True` ist.
# - Um einen Reparaturauftrag anzulegen, wird das boolesche Flag einfach auf `True` gesetzt.
# 
# Wir halten die Logik bewusst einfach, ohne JSON-Nutzdaten.
# 

# In[3]:


def is_hot(value: Optional[float]) -> bool:
    """Gibt True zurück, wenn der Temperaturwert als HOT gilt."""
    return value is not None and value >= HOT_THRESHOLD


async def job_exists(machine: MachineNodes) -> bool:
    """Gibt True zurück, wenn für die angegebene Maschine bereits ein Reparaturauftrag existiert.

    Das boolesche Job-Flag wird wie folgt interpretiert:

        False -> kein Auftrag
        True  -> Auftrag bereits angelegt
    """
    current = await machine.job_node.read_value()
    return bool(current)


async def create_repair_job(machine: MachineNodes):
    """Legt einen Reparaturauftrag an, indem das boolesche Job-Flag auf True gesetzt wird."""
    await machine.job_node.write_value(ua.Variant(True, ua.VariantType.Boolean))
    ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    print(f"[JOB] Repair job created for {machine.name} at {ts}")


async def handle_temperature_reading(machine: MachineNodes, value: float):
    """Neuen Temperaturmesswert verarbeiten: HOT erkennen und ggf. Auftrag anlegen."""
    if not is_hot(value):
        return  # nothing to do

    print(f"[HOT] {machine.name}: {value:.2f} °C >= {HOT_THRESHOLD:.2f} °C") 

    if await job_exists(machine):
        print(f"[JOB] Reparaturauftrag für {machine.name} bereits vorhanden – kein neuer Auftrag angelegt.")
        return

    await create_repair_job(machine)


# ## 5. Polling-basierter HOT-Monitor
# 
# Im **Polling-Modus** geht der Client wie folgt vor:
# 
# 1. Alle Maschinen und ihre Knoten ermitteln,
# 2. `Temperature` für jede Maschine regelmäßig lesen,
# 3. HOT-Zustände erkennen,
# 4. prüfen, ob bereits ein Auftrag existiert,
# 5. bei Bedarf einen Auftrag anlegen, indem `Mxx_RepairNeeded` auf `True` gesetzt wird.
# 
# Dieser Ansatz verwendet ausschließlich `read_value()` und `write_value()` –
# es sind keine OPC UA-Subscriptions involviert.
# 

# In[4]:


async def polling_hot_monitor(runtime_seconds: float = 60.0, poll_interval: float = 1.0):
    """Maschinentemperaturen pollen und HOT-Reparaturaufträge verwalten."""
    async with Client(url=SERVER_URL) as client:
        print("[POLLING] Verbunden mit Server:", SERVER_URL)
        machines = await discover_machines_with_jobs(client)

        loop = asyncio.get_running_loop()
        start = loop.time()

        while True:
            now = loop.time()
            if now - start > runtime_seconds:
                break

            for m in machines.values():
                try:
                    value = await m.temp_node.read_value()
                except Exception as exc:
                    print(f"[POLLING] Fehler beim Lesen der Temperatur für {m.name}: {exc}")
                    continue

                await handle_temperature_reading(m, float(value))

            await asyncio.sleep(poll_interval)

        print("[POLLING] HOT-Monitor abgeschlossen.")


# ## 6. Subscription-basierter HOT-Monitor
# 
# Im **Subscription-Modus** geht der Client wie folgt vor:
# 
# 1. Alle Maschinen ermitteln,
# 2. eine einzige OPC UA-Subscription erstellen,
# 3. jeden `Temperature`-Knoten abonnieren,
# 4. einen Handler (`HotSubHandler`) nutzen, der auf eingehende Datenaenderungs-Benachrichtigungen reagiert.
# 
# Dies ist effizienter als Polling bei einer größeren Anzahl von Maschinen oder
# sich langsam ändernden Werten.
# 

# In[5]:


class HotSubHandler:
    """Subscription-Handler, der auf Temperaturänderungen reagiert und Aufträge verwaltet.

    `machines_by_nodeid` bildet Temperature-NodeIds auf MachineNodes-Instanzen ab,
    damit identifiziert werden kann, zu welcher Maschine eine Benachrichtigung gehört.
    """

    def __init__(self, machines_by_nodeid):
        self.machines_by_nodeid = machines_by_nodeid

    def datachange_notification(self, node, val, data):
        machine = self.machines_by_nodeid.get(node.nodeid)
        if machine is None:
            print(f"[SUB] DataChange for unknown node {node.nodeid}: {val}")
            return

        # Asynchrone Verarbeitung in der laufenden Event-Loop einplanen
        loop = asyncio.get_event_loop()
        loop.create_task(handle_temperature_reading(machine, float(val)))

    def event_notification(self, event):
        # Not used in this simple example, but could handle OPC UA Events.
        print(f"[SUB] Event notification: {event}")


async def subscription_hot_monitor(runtime_seconds: float = 60.0, publishing_interval_ms: int = 500):
    """OPC UA-Subscription nutzen, um Temperaturen zu überwachen und HOT-Reparaturaufträge zu verwalten."""
    async with Client(url=SERVER_URL) as client:
        print("[SUB] Verbunden mit Server:", SERVER_URL)
        machines = await discover_machines_with_jobs(client)

        # NodeId -> MachineNodes-Map für den Handler aufbauen
        by_nodeid = {m.temp_node.nodeid: m for m in machines.values()}
        handler = HotSubHandler(by_nodeid)

        # Subscription erstellen
        subscription = await client.create_subscription(publishing_interval_ms, handler)

        # Alle Temperature-Knoten abonnieren
        for m in machines.values():
            handle = await subscription.subscribe_data_change(m.temp_node)
            print(f"[SUB] {m.name} Temperature abonniert (handle={handle})")

        print(f"[SUB] HOT-Monitor aktiv für ca. {runtime_seconds} Sekunden ...") 

        try:
            await asyncio.sleep(runtime_seconds)
        finally:
            print("[SUB] Subscription wird gelöscht ...")
            await subscription.delete()
            print("[SUB] HOT-Monitor abgeschlossen.")


# ## 7. Den HOT-Monitor starten
# 
# Wähle einen der folgenden Aufrufe in einer separaten Zelle, um den Client zu starten:
# 
# ```python
# # Polling-basiertes Monitoring für 60 Sekunden
# await polling_hot_monitor(runtime_seconds=60.0, poll_interval=1.0)
# 
# # Subscription-basiertes Monitoring für 60 Sekunden
# await subscription_hot_monitor(runtime_seconds=60.0, publishing_interval_ms=500)
# ```
# 
# > **Wichtig:** Stelle sicher, dass dein Fabrik-OPC-UA-Server bereits läuft,
# > bevor du einen dieser Aufrufe ausführst.
# 

# In[6]:


# Beispiel: Subscription-basierten HOT-Monitor für einen Kurztest ausführen
# Genau eine der folgenden Zeilen einkommentieren, um den Client auszuprobieren.

# await polling_hot_monitor(runtime_seconds=30.0, poll_interval=1.0)
await subscription_hot_monitor(runtime_seconds=300.0, publishing_interval_ms=500)


# ## 8. Mögliche Erweiterungen
# 
# - **Unterschiedliche HOT-Schwellenwerte pro Maschine** verwenden
#   (z. B. ein Dictionary `{'M01': 60.0, 'M02': 75.0, ...}`)
#   und `is_hot` entsprechend anpassen.
# - Eine **Abkühlregel** implementieren, die das `Mxx_RepairNeeded`-Flag wieder auf `False` setzt,
#   wenn die Maschinentemperatur für eine gewisse Zeit unter dem Schwellenwert geblieben ist.
# - Diesen HOT-Monitor mit einem übergeordneten Agenten kombinieren
#   (z. B. einem Scheduler oder Dispatcher), der Techniker zuweist oder Tickets in
#   einem externen System erstellt.
# - Das Modell um zusätzliche Zustände erweitern, wie `Busy`, `Failure` oder `PlannedMaintenance`.
# 
# Dieses Notebook stellt einen klar strukturierten, fokussierten OPC UA-Client bereit,
# der Maschinentemperaturen überwacht, HOT-Zustände erkennt und einfache boolesche
# Reparaturauftrag-Flags im Adressraum setzt.
# 
