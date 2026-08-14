# Intervention optimizer — cost-benefit math

The optimizer answers the spending question directly: **given ₹X of budget, which interventions in which zones yield the greatest heat reduction for the most exposed people?**

## Cost and benefit formulas (locked)

### 1. Cool roofs — ₹350/m²

```
albedo change:      Δalbedo = 0.65 − 0.25 = 0.40
zone ΔLST:          ΔLST = f_cr · Δalbedo · 12 °C = f_cr · 4.8 °C
f_cr:               treated roof area / zone built-up area (fraction of roofs treated)
cost:               350 × treated_m2 (INR)
```

### 2. Tree planting — ₹1,200/tree

```
canopy per tree:    25 m²
canopy fraction:    canopy_fraction = (trees × 25 m²) / zone area
zone ΔLST:          ΔLST ≈ canopy_fraction × 2.5 °C
cost:               1200 × trees (INR)
```

### 3. Reflective pavement — ₹450/m²

```
albedo change:      Δalbedo = 0.35
zone ΔLST:          ΔLST ≈ f_pv · 3.5 °C          (f_pv = treated paved area / zone paved area)
cost:               450 × treated_m2 (INR)
```

## Optimization problem

```
maximize   Σ_zones Σ_i ( ΔLST(i, z) × exposed_population(z) )
subject to Σ_zones Σ_i cost(i, z) ≤ budget
           capacity(i, z) ≤ cap(i, z)            # physical limits per zone per type
```

- `exposed_population(z)` = zone population (census) — weighting by people, not just degrees.
- `cap(cool_roof, z)` = 15 % of zone built-up area (only structurally suitable roofs).
- `cap(tree, z)` = number of plantable sites (existing open ground with NDVI < 0.3, not on roads).
- `cap(pavement, z)` = 15 % of zone paved area (road + parking surface).

**Algorithm:** greedy knapsack — sort candidate (zone, intervention) units by benefit/cost ratio `ΔLST × exposed_population / cost`, take in descending order until the budget or all capacities are exhausted. Capacity caps make the selection tractable and physically honest.

## Worked example — Zone #104, budget ₹5 Cr

Zone #104: built-up area 120,000 m², paved area 30,000 m², population 45,000 (18,000/km² over 2.5 km²). The optimizer returns:

| Intervention | Qty | Unit | Cost (INR) | Zone ΔLST (°C) | Benefit/cost (°C per ₹L) |
|---|---|---|---|---|---|
| Cool roofs (f_cr = 0.15 of 120,000 m² built-up) | 18,000 | m² | 63,00,000 | −0.72 | 0.0114 |
| Trees (canopy 30,000 m² = 0.12 of zone) | 1,200 | trees | 14,40,000 | −0.30 | 0.0208 |
| Reflective pavement (f_pv = 0.15 of 30,000 m² paved) | 4,500 | m² | 20,25,000 | −0.52 | 0.0257 |
| **Total** | | | **97,65,000 (₹97.7L ≤ ₹5 Cr)** | **−1.54 ≈ −1.5 °C** | |

Check arithmetic:
- Cool roofs: 0.15 × 0.40 × 12 = 0.72 °C; cost 18,000 × 350 = ₹63,00,000.
- Trees: 0.12 × 2.5 = 0.30 °C; canopy 1,200 × 25 = 30,000 m²; cost 1,200 × 1,200 = ₹14,40,000.
- Pavement: 0.15 × 3.5 = 0.525 ≈ 0.52 °C; cost 4,500 × 450 = ₹20,25,000.
- ΣΔLST = 0.72 + 0.30 + 0.52 = 1.54 ≈ **−1.5 °C**; Σcost = ₹97,65,000.

**Vulnerability impact:** re-scoring Zone #104 with the simulated LST and vegetation → 87 → **69 (−18 points)**. Note that the planner's demo run in the simulator (sliders tuned upward) reaches ΔLST −2.1 °C — the simulator re-runs these same formulas with the adjusted quantities.

Greedy ordering note: pavement has the best benefit/cost ratio (0.0257), then trees (0.0208), then cool roofs (0.0114); all three are selected because each hits its capacity cap before the budget binds.

## Cross-zone allocation

Within one budget run, the same greedy order applies across all 1,500 zones; zones with the highest `ΔLST × exposed_population` per rupee are funded first. The output is a priority list of interventions, not a single zone's plan — the dashboard renders it as the priority map.

## Output contract

```json
{
  "zone_id": 104,
  "budget_inr": 50000000,
  "total_cost_inr": 9765000,
  "est_delta_lst_c": -1.54,
  "new_vulnerability": 69,
  "interventions": [
    { "type": "cool_roof",            "qty": 18000, "unit": "m2",    "cost_inr": 6300000,  "delta_lst_c": -0.72 },
    { "type": "tree",                 "qty": 1200,  "unit": "trees", "cost_inr": 1440000,  "delta_lst_c": -0.30 },
    { "type": "reflective_pavement",  "qty": 4500,  "unit": "m2",    "cost_inr": 2025000,  "delta_lst_c": -0.52 }
  ],
  "confidence": "estimate"
}
```

Every value in this contract is a **model estimate**, not a guaranteed physical outcome.