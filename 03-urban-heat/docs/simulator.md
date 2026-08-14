# Simulator

The simulator is the "what-if" layer of the planner. A planner drags sliders, the backend re-runs the exact cost-benefit formulas of the optimizer (docs/intervention-optimizer.md), and the dashboard shows the simulated ΔLST and the re-scored vulnerability.

## Slider controls

| Slider | Range | Step | Default (optimizer plan) |
|---|---|---|---|
| Trees | 0 – 10,000 | 100 | 1,200 |
| Cool roofs | 0 – 200,000 m² | 1,000 | 18,000 m² |
| Reflective pavement | 0 – 50,000 m² | 500 | 4,500 m² |
| Budget (read-only display) | ₹0 – ₹10 Cr | — | ₹5 Cr |

## Re-run semantics

Every slider change triggers `POST /simulate` (docs/api-contract.md). The backend:

1. Validates quantities (non-negative integers, within slider bounds).
2. Re-runs the optimizer formulas with the zone's stored inputs:
   - cool roofs: `ΔLST = f_cr · 0.40 · 12 °C`, `f_cr = cool_roof_m2 / zone built-up area`;
   - trees: `ΔLST = (trees · 25 / zone_area_km2·1e6) · 2.5 °C`;
   - pavement: `ΔLST = f_pv · 3.5 °C`;
   - `total_delta_lst = Σ contributions` (never exceeds 0; inputs above capacity are clamped to capacity).
3. Re-scores vulnerability with `LST_new = LST − |total_delta_lst|` and the updated vegetation fraction, using the exact decision-engine formula (docs/decision-engine.md).
4. Returns the response with `confidence: "estimate"`.

Simulated rows are never written to the `vulnerability` table — they are ephemeral until the planner saves a plan (`POST /plans`).

## Mandatory labeling

All simulator outputs — in the API response, the dashboard panel, and any exported plan — must display:

> **"Model estimate, not guaranteed physical outcome."**

The response contract carries the machine-readable flag `confidence: "estimate"`; the UI renders a persistent warning banner next to every simulated number.

## Response example — Zone #104, optimizer defaults

Request:

```json
{
  "zone_id": 104,
  "trees": 1200,
  "cool_roof_m2": 18000,
  "pavement_m2": 4500
}
```

Response:

```json
{
  "zone_id": 104,
  "interventions": [
    { "type": "cool_roof",           "qty": 18000, "cost": 6300000, "delta_lst": -0.72 },
    { "type": "tree",                "qty": 1200,  "cost": 1440000, "delta_lst": -0.30 },
    { "type": "reflective_pavement", "qty": 4500,  "cost": 2025000, "delta_lst": -0.52 }
  ],
  "total_delta_lst": -1.54,
  "new_vulnerability": 69,
  "confidence": "estimate"
}
```

## Simulator rules

- `total_delta_lst` is clamped to −10.0 °C (physical upper bound of the linear model).
- `new_vulnerability` is recomputed, never extrapolated: the full weighted composite re-runs with the simulated inputs, and `confidence: "estimate"` tags the result.
- Cost is capped by the budget display value; if the plan exceeds the budget, the dashboard warns and marks the interventions exceeding budget as "over budget".