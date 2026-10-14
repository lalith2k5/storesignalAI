# StoreSignal AI - 3-Minute Demo Script

Pre-flight: run `make reset && make all && make eval` once before presenting.
Then `make ui` and open http://localhost:8501.

## 0:00 - Opening (15s)

Say: "Retailers collect thousands of customer and employee messages across
four channels. The important signal - a broken freezer, a mislabelled
allergen - is fragmented, buried in noise, and surfaces weeks late."

## 0:15 - Show the data (20s)

Tab: Command Center.
Point at the metrics: 40,031 records processed, 9,516 alerts, 1,702 policy
escalations, 4 regions.
Say: "Four channels - reviews, in-app, staff notes, call transcripts.
Mixed English, Hinglish, transliterated Tamil and Marathi."

## 0:35 - Show fusion (25s)

Tab: Incident Explorer.
Filter: Region = West, Category = refrigeration.
Open the top incident card.
Say: "These records arrived on different channels, different days.
The system fused them into one incident and kept the source evidence."

## 1:00 - Show early warning (30s)

Tab: Early-Warning Radar.
Store = S014, Category = refrigeration.
Point at the line chart and the flagged days table.
Say: "Small in absolute volume, but rising sharply at one store.
The robust z-score flagged it 24 days before the reference point.
This is the killer feature - catching problems before they go national."

## 1:30 - Show safety logic (25s)

Tab: Early-Warning Radar.
Store = S007, Category = allergen_risk.
Say: "Watch this. Only a handful of reports. Volume alone would never
trigger an alert. But allergen is a mandatory-risk category, so policy
escalates it regardless - routed to Food Safety with a 2-hour SLA."

## 1:55 - Show action (25s)

Tab: Regional Action Brief. Region = West.
Scroll through the six sections.
Say: "Every week, one page per region. Top five incidents, evidence
quotes, owner, next step, and data caveats. No narrative - just action."

## 2:20 - Show proof (30s)

Tab: Model & Trust.
Point at the three metrics and the seeded-incident table.
Say: "Real measured numbers, not simulated. Macro-F1 0.626 against hidden
labels, escalation precision 0.974, all three seeded incidents detected
with 7, 24, and 5-day lead times. The evaluation script is the only
component that ever reads the hidden labels."

## 2:50 - Close (10s)

Say: "StoreSignal turns scattered store chatter into earlier, explainable,
accountable action."

## If asked about limitations

- Alert volume is demo-scale. Production would tighten the fusion
  threshold. (Line in src/storesignal/fusion/incidents.py.)
- Real 40k dataset swap-in is untested; pipeline is designed for it but
  never run against real data.
- Classifier labels are pseudo-labels from taxonomy keywords because the
  spec reserves hidden labels for evaluation only. On real data, the
  transformer upgrade path may be needed.
