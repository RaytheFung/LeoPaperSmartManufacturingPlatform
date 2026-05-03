# Real Data + Scenario Mode Strategy for LeoPaper FYP

## Core Positioning
This FYP should be positioned as a **Smart Manufacturing Decision-Support Platform** built on real LeoPaper manufacturing data, with a clearly separated **Scenario Mode** for demonstrating future-facing capabilities that are not yet fully supported by live source systems.

The platform should therefore have two explicit operating modes:

### 1. Real Data Mode
Purpose:
- prove that company CSI / MES / Energy / Maintenance data can be integrated;
- prove that machine-level and hour-level manufacturing analysis is possible;
- prove that a real ML-assisted efficiency model can be trained and used for ranking opportunities.

This mode is the basis for all defendable claims in the FYP.

Allowed claims in this mode:
- real ETL ingestion works;
- real machine alias resolution works;
- real monthly unified analytics works;
- real maintenance integration works;
- real ML-assisted efficiency benchmarking / ranking works.

Not allowed in this mode:
- fake order queues presented as real live scheduling inputs;
- synthetic fallback results presented as formal analysis;
- simulated savings presented as actual validated plant economics.

### 2. Scenario Mode
Purpose:
- demonstrate how the platform could be used for planning, what-if simulation, or executive storytelling;
- allow realistic mock data that follows the original company Excel structure and value ranges;
- show future product direction without pretending that every source system integration already exists.

This mode must be explicitly labelled in the UI and presentation as:
- Scenario Mode
- Demo Mode
- Mock Order Queue
- Simulated Future Cases

Scenario Mode is acceptable for:
- Smart Scheduling demo queue
- what-if order mix analysis
- hypothetical maintenance timing comparison
- executive storytelling dashboards
- stress testing UI flows

Scenario Mode must not be used to claim:
- final model accuracy
- real operational savings already achieved
- validated predictive maintenance performance

## FYP-Safe Storyline
The final story should be:

1. I used real company manufacturing data to build an integration and analytics backbone.
2. I created a canonical machine identity layer across CSI, MES, Energy, and Maintenance.
3. I built ML-assisted efficiency benchmarking from real production context.
4. I added Scenario Mode to demonstrate future decision-support workflows in a realistic but clearly labelled way.

This is stronger than pretending the whole system is already a live autonomous optimizer.

## Recommended Product Structure

### Real Data Mode pages
- ETL Pipeline
- Unified Analytics / Monthly Insights
- Maintenance Integration
- ML Opportunity Ranking
- Team / Task / Machine analysis

### Scenario Mode pages
- Smart Scheduling (mock but realistic order queue)
- What-if machine loading simulator
- maintenance timing simulation
- executive presentation demo

## Scenario Data Design Principles
Mock data must not be random nonsense.
It should be generated from empirical distributions derived from real data where possible.

Use real data to estimate:
- machine family frequency
- task type frequency
- material mix
- production quantity ranges
- team size distribution
- maintenance interval ranges
- typical energy usage ranges
- stop-rate / setup-rate ranges

Then generate scenario records that:
- follow original Excel column names and structure;
- stay inside realistic value bands;
- preserve key relationships such as quantity vs energy, machine family vs speed range, maintenance age vs risk tendency.

## Recommended Claim Boundary in Demo / Presentation
Use this wording:
- "validated on real company data" for ETL, integration, analytics, and ML-assisted ranking;
- "demonstrated in Scenario Mode" for planning / scheduling / what-if capabilities;
- "assumption-based directional estimate" for savings shown in Scenario Mode.

Avoid this wording:
- "fully deployed AI optimizer"
- "predictive maintenance already proven"
- "all savings are real and validated"

## Near-Term Build Priority

Priority A:
- finish canonical raw-to-silver normalization on real data
- finish fact_machine_hour v1
- stabilize ML path on real unified data

Priority B:
- build scenario generator based on real distributions
- connect Scenario Mode scheduling page to that generator
- keep scenario outputs visually polished and clearly labelled

## Success Criteria
The FYP is successful if:
- the platform runs end-to-end on real company data;
- machine identity and monthly analytics are defensible;
- at least one real ML-assisted feature is working and explainable;
- Scenario Mode is polished enough to show management the next-stage potential.
