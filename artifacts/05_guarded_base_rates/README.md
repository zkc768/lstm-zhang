# Guarded-era base rates & regime composition (measure-only)

Per walk-forward period and per activity tercile: support, base rate (up_rate =
mean y_true), same-row stratified-dummy macro-F1 floor, and delta. Addresses
review #5 (no artifact reported per-period base rates / dummy floor, so the
COVID-period influence and regime comparability were invisible) and the register-E
class-balance concern.

## How produced
Local, deterministic, measure-only re-aggregation of the frozen V2.1 dumps
(sha256 6481f79/cd6925e, verified) through the shipped + unit-tested
`synthesis.build_guarded_base_rates`. No fit, no scoring. Provenance = sha256 chain.

## Per walk-forward period (TCN primary, seed-mean)
| period | support | up_rate | dummy floor | delta vs dummy |
|---|---|---|---|---|
| wf_p1 | 43097 | 0.5127 | 0.5008 | +0.0092 |
| wf_p2 | 45409 | 0.4953 | 0.4995 | +0.0120 |
| wf_p3 | 43664 | 0.5186 | 0.4997 | +0.0074 |
| wf_p4 | 46396 | 0.5066 | 0.5042 | -0.0026 |
| wf_p5 | 44842 | 0.5094 | 0.5003 | +0.0060 |
| wf_p6 | 47242 | 0.5171 | 0.5011 | -0.0013 |
| wf_p7 | 55317 | 0.5269 | 0.5000 | +0.0077 |

(wf_p4 = 2020 COVID, wf_p6 = 2022 bear: read the per-period delta to see which
regimes drag the pooled edge -- the LOO already flagged wf_p4 as most influential.)

## Per activity tercile (TCN primary, seed-mean)
| tercile | support | up_rate (base rate) | dummy floor | delta vs dummy |
|---|---|---|---|---|
| low | 95310 | 0.5234 | 0.5014 | +0.0408 |
| mid | 111178 | 0.5150 | 0.5003 | +0.0056 |
| high | 119479 | 0.5022 | 0.5007 | -0.0210 |

The per-tercile **up_rate and dummy floor are near-constant** across low/mid/high,
so the calm-bar edge is NOT a class-balance / base-rate artifact (the delta is not
manufactured by a skewed dummy floor in calm bars). Descriptive only.

## Verify
```bash
sha256sum -c SHA256SUMS.txt
```
