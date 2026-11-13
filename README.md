# Internet of Production – agent systems part: lab material

**🇬🇧 English** · [🇩🇪 Deutsch](README.de.md)

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/Triltsch/IoP_Agents/HEAD?urlpath=lab)

Hands-on exercises of the agent systems part of the lecture *Internet of Production* (Ostfalia University of Applied Sciences). One thread runs through all three weeks: **a factory of machines that heat up, a coordinator that detects the HOT state, and a maintenance agent that repairs the machines** – first as reactive agents (Mesa), then connected to the shop floor via OPC UA, finally orchestrated with LangGraph, MCP and an LLM.

## Start

- **Without installation:** click the Binder badge above (environment: `binder/environment.yml`). The first start can take a few minutes.
- **Locally:** `conda env create -f binder/environment.yml`, then `conda activate iop-agents` and register the kernel:
  `python -m ipykernel install --user --name iop-agents --display-name "Python (iop-agents)"`

## Structure

One folder per lecture week, one subfolder per language (`en`, `de`). Where an exercise has gaps for the students it exists as `_student` (with gaps `___` and `# TODO`) and `_solution`; demo notebooks that are only run and discussed carry the suffix `_showcase`.

| Folder | Content |
|---|---|
| `W1_Reactive_Agents` | **Week 1:** reactive agents in Mesa 3 (sense–decide–act): machine, maintenance and order agents on a grid |
| `W2_Cooperation_Communication` | **Week 2:** 01 OPC UA server of the factory; 02 publish/subscribe clients; 03 HOT monitor client; 04 Mesa agents coupled to OPC UA via a shared buffer (`_student` with three gaps) |
| `W3_Frameworks_LangGraph_MCP` | **Week 3:** 01 stateful agents with LangGraph; 02 MCP server/client and an LLM coordinator (stub, no API key); 03 the same with a real LLM API |
| `binder/` | Environment for Binder and local use |

## Recommended order

Week 1 → week 2 → week 3. In week 2 start the OPC UA server (notebook 01) first and keep it running while you work through 02–04.

## Notes

- Notebook `W3/03_MCP_LLM_API_showcase` needs an API key in the environment variable `OPENAI_API_KEY`. Never write a key into a notebook or commit it.
- Pinned versions: Mesa 3.0.3 and `wait-for2==0.3.2` (needed by `asyncua`). Other versions are not tested with these notebooks.
