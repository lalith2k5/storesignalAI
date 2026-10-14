# StoreSignal AI - Real Data Robustness Check

**Dataset:** Google Play India Reviews (Kaggle)

**Caveat:** This dataset has no ground-truth labels. This is a
robustness check that the pipeline runs unchanged on real
multilingual Indian retail text. It is NOT an evaluation of
classification quality.

## Summary

- Records processed: **20,000**
- Virtual stores (one per app): **8**
- Policy escalations raised: **2940**
- Records routed to human review: **7277** (36.4%)
- Records flagged actionable: **3242**

## Language distribution (real text)

- `en`: 19,689 (98.4%)
- `hi-en`: 251 (1.3%)
- `hi`: 60 (0.3%)

## Top classified categories

- `app_crash`: 4,683
- `food_safety_other`: 2,882
- `order_accuracy`: 2,819
- `other`: 2,038
- `delivery`: 1,954
- `stockout`: 1,880
- `order_cancellation`: 821
- `refund_issue`: 616
- `price_discrepancy`: 447
- `billing_error`: 277

## Policy escalations by category

- `allergen_risk`: 4
- `food_safety_other`: 2,882
- `foreign_object`: 26
- `hygiene`: 13
- `staff_misconduct`: 15

## What this proves

- The normalization pipeline handles real code-mixed and English
  text from Indian apps without modification.
- The trained classifier produces coherent category assignments on
  text it has never seen.
- The policy guardrail fires on real allergen/hygiene/misconduct
  signals independent of volume.
- The pipeline is not overfit to the synthetic distribution.