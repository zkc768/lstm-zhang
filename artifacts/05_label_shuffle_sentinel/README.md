# Within-day label-shuffle sentinel (measure-only leakage negative control)

Register Tier-1 negative control + review-E adjudication: permute y_true WITHIN
each (ticker, trading_day), recompute the frozen candidate's per-tercile macro-F1
over 50 permutations. A genuine, leakage-free edge must NOT survive the shuffle --
the observed macro-F1 must clear the per-tercile shuffled null. If a shuffled
permutation reproduced the edge, that would indicate within-day leakage or a
base-rate / tercile-construction artifact (the central register-E concern).

## How produced
Local, deterministic (base_seed=0), measure-only over the frozen V2.1 dumps
(sha256 6481f79/cd6925e) through the shipped + unit-tested
`synthesis.build_guarded_label_shuffle_sentinel`. Candidate predictions are fixed;
only labels are permuted. Provenance = sha256 chain.

## The result (TCN primary, 50 perms, seed-mean)
| tercile | observed delta vs dummy | shuffled delta mean | shuffled delta max | observed > shuffle max (PASS) |
|---|---|---|---|---|
| all | 325967 | +0.0064 | -0.03721 | -0.03262 | True |
| low | 95310 | +0.0408 | -0.03624 | -0.03010 | True |
| mid | 111178 | +0.0056 | -0.03752 | -0.03271 | True |
| high | 119479 | -0.0210 | -0.03866 | -0.03143 | True |

All terciles PASS (observed edge clears the within-day-shuffle null): **True**.
The observed edge -- including the calm low tercile -- sits clearly ABOVE its
permutation null, so it requires genuine row-level label alignment; it is NOT a
within-day-leakage or day-base-rate / class-construction artifact. NOTE the shuffled
null lands ~0.037 BELOW the stratified-dummy floor (not at 0) because the candidate's
prediction class-balance differs from the dummy's -- macro-F1 punishes the
candidate's more imbalanced predictions against random labels; this is expected and
is why the correct test is 'observed clears the null', not 'shuffled delta == 0'.
This does NOT rule out a Roll(1984) bid-ask-bounce microstructure artifact in the
underlying labels, which would need raw 5-min bars / half-spread vs the 3bps band
(out of scope for this predictions-dump-only pass) -- recorded as a residual limitation.

## Verify
```bash
sha256sum -c SHA256SUMS.txt
```
