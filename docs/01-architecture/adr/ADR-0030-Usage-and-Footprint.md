---
artifact:
  id: ADR-0030
  title: Usage and footprint of AIStack
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 0.2
  status: Proposed
  owner: Architecture
  created: 2026-11-21
  updated: 2026-11-21

relations:
  references:
    - ADR-0029
    - ADR-0027
---

# ADR-0030 — Usage and footprint of AIStack

## Status

Proposed, 2026-11-21. The owner asked on 2026-11-21 for a general page of usage statistics with the carbon
footprint of AIStack, calculated after the AFNOR SPEC 2314 (June 2024). The scope (AIStack and its AI calls,
local and outside) and the measure of the GPU power instead of a declared power were agreed that day; the
rest is proposed and waits for the owner.

## Context

AIStack asks models on the home machine and at outside providers (`ADR-0029`). The journal of AI calls keeps,
for each call, who asked, which engine answered, how long it took and what the policy decided, never a word of
the question. It is the only record of usage AIStack keeps: it keeps no visit statistics of its screens, and
this ADR does not add any.

The owner wants to know what these calls cost in energy and greenhouse gases, and wants the figures to be as
trustworthy as a home installation allows: measured when it can be, published when it cannot, and declared as
a last resort, with the range and the source of each.

## Decision

### 1. A reading screen and a calculation, nothing else

*Usage et empreinte* (`/footprint/`, LAN only, signed-in) reads the journal and `footprint.yml` and writes
nothing. A console card without any AI use leads to it. The calculation (`footprint/estimate.py`) is pure.

### 2. The method

The method follows the principles of the AFNOR SPEC 2314 as the owner described them: a functional unit (here
one call to an AI engine, from the click to the answer), three levels (the machine that answers, the network,
the terminal), equipment allocated by time of use, measured data before declared data, and the uncertainty
written down. Two of the priority indicators are calculated: final energy (kWh) and greenhouse gases (kgCO2e,
GWP at 100 years). Resource depletion and primary energy are not, and the page says so.

The owner's copy of the SPEC carries a notice by AFNOR objecting to its use by AI engines. No text of the SPEC
is copied here or on the page, and the page says the calculation is *inspired by* the SPEC and is not claimed
conforming. Whether it conforms is for the owner to check against the document; this ADR does not decide it.

### 3. Every figure is a range with its origin

`footprint.yml` declares each input with a low, a central and a high value (the low is the scenario with the
least impact: a longer life is on the left), a unit, a `status` (`measured`, `sourced`, `declared`) and a
source. The loader refuses a file that misses a parameter, a value or a source. The page shows the whole
table, so a figure can be traced.

| Input | Origin |
|---|---|
| Electricity in France, 19.6 / 41.4 / 51.9 g/kWh | RTE (direct emissions of production, 2025), Ember (life cycle, 2025), ADEME Base Empreinte (consumption mix, 2024) |
| Electricity at a provider, 210 / 384 / 458 g/kWh | Ember, life cycle 2025: European Union, United States, world |
| Energy of an outside call, 0.24 / 0.3 / 3 Wh | Google (median Gemini text prompt, August 2025, overhead included), Epoch AI (ChatGPT, 2025), the older estimate of 3 Wh |
| GPU at rest, 33.57 W | measured on the GTX 1070 of the MSI, 2026-11-21 |
| GPU power limit, 151 W | measured; the 60 W and 100 W used when the power is not read are declared |
| Terminal, network, machine overhead, making and life of the machine, permanent load | declared, to be confirmed or replaced by a measure |

### 4. The GPU power is measured during the call

`footprint/power.py` reads `nvidia-smi power.draw` every half second while a call runs and the journal keeps the
mean as `gpu_watts`, for a call that did not go outside. When the process cannot read it (no `nvidia-smi`, a
card that reports `[N/A]`, a call shorter than one reading), the call is priced from the declared power and the
page counts it as *estimated*. The reading made on entry only tells whether the power can be read; it is not
counted, because it is taken before the card works. The sampler never stops or delays a question beyond its
own join, and a failing reader is ignored.

For a measured call the low value keeps only what the call added to the idle card; the central and high values
take the whole reading.

### 5. What a call carries

- **Local call**: card power × (1 + overhead of the machine) × PUE × duration, at the French grid, plus the share
  of the machine's making that the duration is of its life.
- **Outside call**: the published energy per call (it already holds the data-centre overhead) at the grid of an
  unknown place, plus the network.
- **Terminal**: for the callers a person waits on (`terminal_callers`), the declared terminal power × duration.
- **A call nothing answered** is counted in usage and carries no energy.
- **Permanent load**: the containers of AIStack that run all the time, apart from calls, over the same period.
  This is a declared power, and for any realistic value it is far above the calls: it is the first thing to measure.

## Not decided here

1. **Measure the permanent load continuously.** Done once by hand on the reference host on 2026-11-21: the UPS reads
   31 % of 520 W (161 W for its whole circuit, resolution about 5 W) and the containers show AIStack holding 2.2 % of their
   memory and 9.2 % of one core, which gives 0.5 / 3.6 / 4.6 W (the owner's `config/footprint.yml`, status `measured`; the
   shipped file keeps the declared 2 / 5 / 10 W, as it cannot know another machine). What remains: the allocation key
   (memory; a processor key would give more) is a choice, the UPS also feeds the Raspberry, and a single reading does not
   follow the load over time. A reading by the vigil of the UPS (NUT) and of the containers' use would.
2. **Whether `nvidia-smi` is visible from the web container.** If it is not, every local call is *estimated* until the container is given the card's monitoring.
3. **The making of the machine** and its life: the declared 350 kgCO2e over 5 years is a placeholder for the maker's figure.
4. **Allocating the making of the machine to the permanent load**, which is not done.
5. **Resource depletion and primary energy**, which are not calculated.
6. **Conformity to the SPEC**, which the owner checks against his copy.
