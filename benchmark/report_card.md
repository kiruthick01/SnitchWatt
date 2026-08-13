# Snitchwatt Report Card

TVLA run across simulated device profiles (n_traces=3000, n_samples=200, leak_sample=100, seed=7).

| Profile | Verdict | max \|t\| | Notes |
|---|---|---|---|
| `unprotected_high_snr` | FLAGGED | 129.96 | Obviously broken implementation, strong leak. |
| `unprotected_low_snr` | FLAGGED | 5.44 | Borderline case: weak but real leak, tests detector sensitivity. |
| `masked_implementation` | PASS | 3.34 | Clean countermeasure, no data-dependent component anywhere. |
| `masked_implementation_with_residual_leak` | FLAGGED | 4.98 | Imperfect countermeasure: small residual leak survives masking. |
