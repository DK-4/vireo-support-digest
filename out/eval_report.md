# Classifier evaluation - classify_v1

> **MOCK PREDICTIONS.** Scored against the keyword fallback, not a model. This number describes the fallback only.

**Accuracy 67.7%** (95% CI 57.8%-76.2%) on 96 human-labelled tickets.
Schema-valid 100.0%, invalid output 0.0%. Blank in gold file: 0. No prediction found: 0.

## Per theme

| Theme | Support | Predicted | Precision | Recall | F1 |
|---|---|---|---|---|---|
| Delivery delayed or not received | 9 | 8 | 0.75 | 0.67 | 0.71 |
| Arrived damaged or dead on arrival | 5 | 6 | 0.67 | 0.80 | 0.73 |
| Charging & battery fault | 5 | 6 | 0.67 | 0.80 | 0.73 |
| Audio quality fault | 6 | 6 | 0.67 | 0.67 | 0.67 |
| Connectivity & pairing fault | 8 | 7 | 1.00 | 0.88 | 0.93 |
| App & firmware fault | 6 | 7 | 0.71 | 0.83 | 0.77 |
| Payment & invoice | 12 | 9 | 0.44 | 0.33 | 0.38 |
| Account access / login | 6 | 6 | 1.00 | 1.00 | 1.00 |
| Return pickup & refund status | 13 | 8 | 0.75 | 0.46 | 0.57 |
| Warranty claim / RMA status | 8 | 7 | 1.00 | 0.88 | 0.93 |
| Order change, cancellation & address | 9 | 7 | 0.71 | 0.56 | 0.62 |
| Pre-sales / compatibility (no fault) | 8 | 7 | 0.86 | 0.75 | 0.80 |
| Unclear / other | 1 | 12 | 0.08 | 1.00 | 0.15 |

## Top 5 confusions

| You labelled | Model said | n |
|---|---|---|
| Return pickup & refund status | Unclear / other | 4 |
| Order change, cancellation & address | Payment & invoice | 3 |
| Payment & invoice | Unclear / other | 2 |
| Delivery delayed or not received | Unclear / other | 2 |
| Return pickup & refund status | Order change, cancellation & address | 2 |

## Failures (31)

| Ticket | You | Model | Conf | Model's evidence |
|---|---|---|---|---|
| TK-254461 | Delivery delayed or not received | Unclear / other | 0.2 |  |
| TK-244788 | Payment & invoice | App & firmware fault | 0.35 | app  |
| TK-240738 | Charging & battery fault | Unclear / other | 0.2 |  |
| TK-250746 | Audio quality fault | Arrived damaged or dead on arrival | 0.35 | crack |
| TK-250219 | Delivery delayed or not received | Charging & battery fault | 0.35 | charg |
| TK-248916 | Return pickup & refund status | Unclear / other | 0.2 |  |
| TK-243494 | Return pickup & refund status | Unclear / other | 0.2 |  |
| TK-254596 | Return pickup & refund status | Payment & invoice | 0.35 | invoice |
| TK-251304 | Return pickup & refund status | Unclear / other | 0.2 |  |
| TK-246884 | Payment & invoice | Unclear / other | 0.2 |  |
| TK-240483 | Payment & invoice | Charging & battery fault | 0.35 | charg |
| TK-244344 | Warranty claim / RMA status | Unclear / other | 0.2 |  |
| TK-244486 | Return pickup & refund status | Unclear / other | 0.2 |  |
| TK-246561 | Order change, cancellation & address | Delivery delayed or not received | 0.35 | courier |
| TK-241044 | Delivery delayed or not received | Unclear / other | 0.2 |  |
| TK-242605 | Connectivity & pairing fault | Audio quality fault | 0.35 | audio |
| TK-248118 | Pre-sales / compatibility (no fault) | App & firmware fault | 0.35 | app  |
| TK-254019 | Payment & invoice | Audio quality fault | 0.35 | audio |
| TK-243294 | Payment & invoice | Unclear / other | 0.2 |  |
| TK-246416 | Order change, cancellation & address | Payment & invoice | 0.35 | statement |
| TK-254612 | Audio quality fault | Delivery delayed or not received | 0.35 | tracking |
| TK-252753 | Arrived damaged or dead on arrival | Unclear / other | 0.2 |  |
| TK-249157 | Payment & invoice | Arrived damaged or dead on arrival | 0.35 | damaged |
| TK-251018 | Order change, cancellation & address | Payment & invoice | 0.35 | deducted |
| TK-244147 | Return pickup & refund status | Order change, cancellation & address | 0.35 | cancel |
| TK-249326 | Payment & invoice | Return pickup & refund status | 0.35 | where is the money |
| TK-253533 | Order change, cancellation & address | Payment & invoice | 0.35 | bank says |
| TK-249298 | Return pickup & refund status | Order change, cancellation & address | 0.35 | cancel |
| TK-251691 | Pre-sales / compatibility (no fault) | Return pickup & refund status | 0.35 | Where is the money |
| TK-249577 | Payment & invoice | Pre-sales / compatibility (no fault) | 0.35 | compatible |
| TK-243658 | App & firmware fault | Payment & invoice | 0.35 | INVOICE |