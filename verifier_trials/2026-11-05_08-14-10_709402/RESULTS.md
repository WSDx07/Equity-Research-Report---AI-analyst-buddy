# Verifier known-answer test — Costco

Analysis date: 2026-11-05. Source run: `equity_research_runs/COSTCO_WHOLESALE_CORP_NEW_2026-11-05_08-09-51_936040_-0500`. Each trial used a separate copy and the actual `desk_flow.py --verify-only` command. Original run files were not changed.

## Seeded EPS: partial failure

The copied report changed FY2026 diluted EPS from USD 20.76 to USD 21.76 per share in its XBRL row. It also added a second statement with a fabricated 10-K line quoting USD 21.76. The verifier marked the XBRL value wrong and replaced the row with USD 20.76. However, the corrected row identifies the XBRL tag and period, not the requested saved 10-K per-share line 637. The separately forged quotation was marked unsupported, rather than wrong, because the current verifier treats per-share statements as unsupported before completing the line check. The expected correction with the filing line was not achieved.

Output: `seeded_eps/verification_2026-11-05_08-15-19_262910_-0500/verified_report.md`.

## Invented revenue growth: partial failure

The copied report claimed 14.14% annual revenue growth, with the FY2026 and FY2025 revenue inputs USD 303,154 million and USD 275,235 million. The verifier marked 14.14% wrong, but did not recompute or display the correct arithmetic. The 10-K line 624 states those annual total revenue inputs. The calculation is `(303154 - 275235) / 275235 * 100 = 10.1437%`, or 10.14% rounded to two decimals. The incorrect value is four percentage points above that rounded value. The verifier flagged it because the cited line did not itself contain 14.14%, not because it performed this calculation.

Output: `invented_growth/verification_2026-11-05_08-15-19_262910_-0500/verified_report.md`.

## Clean report: not established

The November 2 Costco audit did not mark all eleven core claims correct: it marked quarterly total-revenue growth as missing. The audited November 2 Costco run is not present in the current workspace, so its report could not be reverified. `clean_audit_proxy` is a newly constructed, explicitly labeled eleven-claim test based on the audit and the saved November 5 filing. Its missing quarterly growth is supplied as `(95723 - 86156) / 86156 * 100 = 11.1043%`, or 11.10%, using USD millions. This is not the original audited report. The verifier did not mark all eleven proxy claims correct; several values and ratios were marked wrong or unsupported. This proxy demonstrates problems with the verifier, but does not prove whether the missing clean report would pass.

Output: `clean_audit_proxy/verification_2026-11-05_08-15-19_264925_-0500/verified_report.md`.

## Skip check

The current `desk_flow.py` graph attaches the Verifier after the Manager and has no flag to disable it. The old `equity_research_data_desk.py` full-run path and the old `run_roles` function could run the legacy team without the Verifier. Those paths now stop with instructions to use `desk_flow.py`; individual data-only `--step` commands remain available. A run that fails before the Manager completes cannot reach the Verifier.

The verifier remains a prototype. These trials do not establish it as a complete or reliable audit of financial claims.
