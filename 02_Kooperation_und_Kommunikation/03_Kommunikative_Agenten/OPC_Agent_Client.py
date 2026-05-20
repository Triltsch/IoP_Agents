#!/usr/bin/env python
# coding: utf-8

# # AsyncUA agent client for factory machines
# 
# This notebook implements a **stand–alone OPC UA client** that fulfils the behaviour:
# 
# - poll or subscribe to machine nodes  
# - detect **HOT** conditions on machine temperatures  
# - check if a repair job already exists  
# - create a repair job by setting an OPC UA variable
# 
# It is designed to work with a factory server exposing this address space structure:
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
# Assumptions (easy to adapt in code):
# 
# - `Temperature` is a `Double` value for each machine.
# - Each `Mxx_RepairNeeded` under `Factory/Maintenance/Jobs` is a **boolean** variable:
#   - `False` → no repair job exists.  
#   - `True`  → repair job already created.
# 
# The client can operate in two modes:
# 
# - **Polling mode** – periodically reads temperatures and evaluates HOT conditions.
# - **Subscription mode** – uses OPC UA Subscriptions to react to data changes.
# 

# ## 1. Install required packages
# 
# If `asyncua` and `nest_asyncio` are not installed yet in your environment,
# run the following cell once.
# 


# ## 2. Imports, configuration, and event loop setup
# 
# We configure the OPC UA endpoint and namespace URI to match the factory server,
# and prepare `nest_asyncio` so that we can comfortably use `await` in Jupyter.
# 

# In[1]:


import asyncio
from datetime import datetime
from typing import Dict, Optional

import nest_asyncio
nest_asyncio.apply()

from asyncua import ua, Client

# Configuration – adapt these constants if your server uses different values
SERVER_URL = "opc.tcp://localhost:4840/freeopcua/server/"
FACTORY_NS_URI = "http://ostfalia.de/ipt/factory"

# HOT detection configuration
HOT_THRESHOLD = 60.0  # °C – temperatures at or above this value are considered HOT

print("Event loop set up. Server endpoint:", SERVER_URL)
print("HOT threshold:", HOT_THRESHOLD, "°C")


# ## 3. Machine discovery and browse helpers
# 
# We assume that:
# 
# - all machines are direct children of `Factory/Machines`, and
# - all repair–job flags are children of `Factory/Maintenance/Jobs`,
#   with names following the pattern `Mxx_RepairNeeded`.
# 
# The helper below discovers all machines and collects the relevant nodes.
# 

# In[2]:


class MachineNodes:
    """Convenience container for the important nodes of a machine."""

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
    """Discover all machines and their Temperature / RepairNeeded job nodes.

    Structure:

        Objects
         └─ Factory
             ├─ Machines
             │   └─ Mxx / Temperature
             └─ Maintenance
                 └─ Jobs / Mxx_RepairNeeded

    Returns a dictionary keyed by machine name (e.g. 'M01').
    """
    ns = await client.get_namespace_index(FACTORY_NS_URI)
    #print(f"[DISCOVERY] Namespace index for {FACTORY_NS_URI!r}: {ns}")

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
            # Skip non–machine nodes if any
            print(f"[DISCOVERY] Skipping non–machine node: {bname}")
            continue

        # Temperature node under the machine
        try:
            temp_node = await mobj.get_child([f"{ns}:Temperature"])
        except Exception as exc:
            print(f"[DISCOVERY] {name}: missing Temperature node ({exc})")
            continue

        # Boolean job flag: M01_RepairNeeded, M02_RepairNeeded, ...
        job_name = f"{name}_RepairNeeded"
        try:
            job_node = await jobs_folder.get_child([f"{ns}:{job_name}"])
        except Exception as exc:
            print(f"[DISCOVERY] {name}: missing job node '{job_name}' ({exc})")
            continue

        machine_nodes[name] = MachineNodes(name, mobj, temp_node, job_node)
        # print(
        #     f"[DISCOVERY] {name}: temp={temp_node.nodeid}, job={job_node.nodeid}"
        # )

    return machine_nodes


# ## 4. HOT detection and job management
# 
# The behaviour is defined as follows:
# 
# - A temperature is **HOT** if it is greater than or equal to `HOT_THRESHOLD`.
# - A repair job *exists* if the corresponding `Mxx_RepairNeeded` flag is `True`.
# - To create a repair job, we simply set the boolean flag to `True`.
# 
# We keep the logic intentionally simple, without JSON payloads.
# 

# In[3]:


def is_hot(value: Optional[float]) -> bool:
    """Return True if the temperature value is considered HOT."""
    return value is not None and value >= HOT_THRESHOLD


async def job_exists(machine: MachineNodes) -> bool:
    """Return True if a repair job already exists for the given machine.

    We interpret the boolean job flag as:

        False -> no job
        True  -> job already created
    """
    current = await machine.job_node.read_value()
    return bool(current)


async def create_repair_job(machine: MachineNodes):
    """Create a repair job by setting the boolean job flag to True."""
    await machine.job_node.write_value(ua.Variant(True, ua.VariantType.Boolean))
    ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    print(f"[JOB] Repair job created for {machine.name} at {ts}")


async def handle_temperature_reading(machine: MachineNodes, value: float):
    """Process a new temperature reading: detect HOT and create job if necessary."""
    if not is_hot(value):
        return  # nothing to do

    print(f"[HOT] {machine.name}: {value:.2f} °C >= {HOT_THRESHOLD:.2f} °C") 

    if await job_exists(machine):
        print(f"[JOB] Repair job already exists for {machine.name} – no new job created.")
        return

    await create_repair_job(machine)


# ## 5. Polling-based HOT monitor
# 
# In **polling mode**, the client:
# 
# 1. discovers all machines and their nodes,
# 2. periodically reads `Temperature` for each machine,
# 3. detects HOT conditions,
# 4. checks whether a job already exists,
# 5. creates a job by setting `Mxx_RepairNeeded` to `True` if needed.
# 
# This approach uses only `read_value()` and `write_value()` – no OPC UA
# Subscriptions are involved.
# 

# In[5]:


async def polling_hot_monitor(runtime_seconds: float = 60.0, poll_interval: float = 1.0):
    """Poll machine temperatures and manage HOT repair jobs."""
    async with Client(url=SERVER_URL) as client:
        print("[POLLING] Connected to server:", SERVER_URL)
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
                    print(f"[POLLING] Failed to read temperature for {m.name}: {exc}")
                    continue

                await handle_temperature_reading(m, float(value))

            await asyncio.sleep(poll_interval)

        print("[POLLING] HOT monitor finished.")


# ## 6. Subscription-based HOT monitor
# 
# In **subscription mode**, the client:
# 
# 1. discovers all machines,
# 2. creates a single OPC UA Subscription,
# 3. subscribes to each `Temperature` node,
# 4. uses a handler (`HotSubHandler`) that reacts to incoming data–change notifications.
# 
# This is more efficient than polling for a larger number of machines or
# slowly changing values.
# 

# In[4]:


class HotSubHandler:
    """Subscription handler that reacts to temperature changes and manages jobs.

    `machines_by_nodeid` maps temperature NodeIds to MachineNodes instances
    so that we can identify which machine a notification belongs to.
    """

    def __init__(self, machines_by_nodeid):
        self.machines_by_nodeid = machines_by_nodeid

    def datachange_notification(self, node, val, data):
        machine = self.machines_by_nodeid.get(node.nodeid)
        if machine is None:
            print(f"[SUB] DataChange for unknown node {node.nodeid}: {val}")
            return

        # Schedule the async processing in the running event loop
        loop = asyncio.get_event_loop()
        loop.create_task(handle_temperature_reading(machine, float(val)))

    def event_notification(self, event):
        # Not used in this simple example, but could handle OPC UA Events.
        print(f"[SUB] Event notification: {event}")


async def subscription_hot_monitor(runtime_seconds: float = 60.0, publishing_interval_ms: int = 500):
    """Use an OPC UA Subscription to monitor temperatures and manage HOT repair jobs."""
    async with Client(url=SERVER_URL) as client:
        print("[SUB] Connected to server:", SERVER_URL)
        machines = await discover_machines_with_jobs(client)

        # Build NodeId -> MachineNodes map for the handler
        by_nodeid = {m.temp_node.nodeid: m for m in machines.values()}
        handler = HotSubHandler(by_nodeid)

        # Create subscription
        subscription = await client.create_subscription(publishing_interval_ms, handler)

        # Subscribe to all temperature nodes
        for m in machines.values():
            handle = await subscription.subscribe_data_change(m.temp_node)
            print(f"[SUB] Subscribed to {m.name} Temperature (handle={handle})")

        print(f"[SUB] HOT monitor active for about {runtime_seconds} seconds ...") 

        try:
            await asyncio.sleep(runtime_seconds)
        finally:
            print("[SUB] Deleting subscription ...")
            await subscription.delete()
            print("[SUB] HOT monitor finished.")
            
async def _get_job_node(client: Client, machine_name: str):
        ns = await client.get_namespace_index(FACTORY_NS_URI)
        objects = client.nodes.objects
        factory = await objects.get_child([f"{ns}:Factory"])
        maintenance = await factory.get_child([f"{ns}:Maintenance"])
        jobs = await maintenance.get_child([f"{ns}:Jobs"])
        job_node = await jobs.get_child([f"{ns}:{machine_name}_RepairNeeded"])
        return job_node

async def read_repair_flag(machine_name: str) -> bool:
    """
    Read Factory/Maintenance/Jobs/Mxx_RepairNeeded for a single machine.
    """
    async with Client(url=SERVER_URL) as client:
        job_node = await _get_job_node(client, machine_name)
        value = await job_node.read_value()
        return bool(value)
    
async def _clear_repair_flag(machine_name: str) -> None:
    """
    Clear the Factory/Maintenance/Jobs/Mxx_RepairNeeded flag for a single machine.

    Parameters
    ----------
    machine_name:
        OPC UA machine name, e.g. "M01", "M02", ...
    """
    async with Client(url=SERVER_URL) as client:
        job_node = await _get_job_node(client, machine_name)

        # job_node is the Boolean Mxx_RepairNeeded variable
        await job_node.write_value(ua.Variant(False, ua.VariantType.Boolean))
        print(f"[HOT_CLIENT] Cleared RepairNeeded for {machine_name} on OPC UA server.")


def clear_repair_flag_sync(machine_name: str) -> None:
    """
    Synchronous wrapper so that non-async code (e.g. Mesa agents) can clear
    a repair flag on the OPC UA server.

    This uses asyncio.get_event_loop().run_until_complete(...), so it should
    be called in an environment where nest_asyncio has been applied.
    """
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_clear_repair_flag(machine_name))


# -----------------------------------------------------------------------------
# Read all Mxx_RepairNeeded flags into a model-side dictionary
# -----------------------------------------------------------------------------

async def read_all_repair_flags() -> dict[str, bool]:
    """
    Read the OPC UA nodes Factory/Maintenance/Jobs/Mxx_RepairNeeded for all machines.

    Returns
    -------
    dict:  { "M01": True/False, "M02": True/False, ... }
    """
    async with Client(url=SERVER_URL) as client:
        machines_nodes = await discover_machines_with_jobs(client)

        result = {}
        for name, nodes in machines_nodes.items():
            try:
                value = await nodes.job_node.read_value()
                result[name] = bool(value)
            except Exception as exc:
                print(f"[HOT_CLIENT] Failed reading RepairNeeded for {name}: {exc}")
                result[name] = False
        return result


def read_all_repair_flags_sync() -> dict[str, bool]:
    """
    Synchronous wrapper for Mesa to fetch all repair flags.
    """
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(read_all_repair_flags())


