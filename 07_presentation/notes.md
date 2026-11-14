# Speaker notes — VIGIE defence (20 minutes + 10 minutes of questions)

> Generated from the notes of `slides.pptx` (`tools/build_slides.py`). Every member speaks; the live demo lasts at least 5 minutes.

| Speaker | Slides | Time |
|---|---|---:|
| Raed Meddeb | 1–3, 11–13, 19 | ≈ 6 min |
| Ines Ayed | 4–5, 8 | ≈ 3 min |
| Salsabil Ben Elhadj | 6–7 | ≈ 2.5 min |
| Salah Chebbi | 9–10, 18 | ≈ 3 min |
| Ibrahim Grira | 14–17 (including the 5-minute live demo) | ≈ 6 min |

## 1. Customer churn analysis and prediction

[Raed] Good morning. We are Group BI 5 and our project is called VIGIE — French for 'lookout'. In 20 minutes we will show how we went from a raw banking file to a deployed tool that measures and anticipates churn. Each of us will present the part they led.

## 2. The question: understand, measure and anticipate churn

[Raed Meddeb] The bank gave us an anonymised snapshot of 363 thousand customers. Our goal was to answer three questions: how much churn, where and why, and what comes next. We followed the five phases of the project, with one rule: verify every number before using it.

## 3. Architecture: one chain, one code base

[Raed Meddeb] Six stages. The key design choice is the shared library: the warehouse, the notebooks and the application compute every number with the same code, so a figure cannot differ from one deliverable to another.

## 4. Phase 1 · A rate is meaningless without its grain

[Ines Ayed] First finding: the file mixes three grains. The same data gives 40, 36 or 32 percent of churn depending on what you count. We fixed two grains: the account for the warehouse, the customer for the model. And no customer is both active and closed — which makes customer churn unambiguous.

## 5. Phase 1 · Some blanks give the answer away

[Ines Ayed] Missing values are not all the same. The important ones: balance, account family, currency and opening date are blank for 68 percent of closed accounts and never for active ones. They record the departure — so they cannot be used to predict it. Outliers: a third of balances are 'outliers', but they are loans in debit, not errors.

## 6. Phase 2 · Star schema at account grain

[Salsabil Ben Elhadj] One fact table, one row per account, eight dimensions. Two choices matter: a 'Not provided' member with key zero, so no join ever loses rows, and a calendar built in SQL that plays two roles — opening and closing.

## 7. Phase 2 · ETL and 19 checks, 19 OK

[Salsabil Ben Elhadj] The flow: staging, transformation, load. The Talend jobs are specified component by component, and a Python pipeline gives the reference load. Then 19 checks compare source and warehouse: volumes, KPIs, integrity. All pass.

## 8. Phase 3 · Reporting: 3 pages, 30 documented DAX measures

[Ines Ayed] Thirty DAX measures, each with the value it must show — so the report can be checked number by number. Two rules: a rate at its grain, and inactive date relationships so that a date filter never distorts the global KPIs. The JavaScript dashboard is our bonus and our mockup.

## 9. Phase 4 · The KPI: weekly closures — and 5 mass weeks

[Salah Chebbi] Our KPI is the number of accounts closed per week. Five weeks carry half of all closures: they are batch operations, with 'Other' as reason in 99.5 percent of cases. They cannot be forecast, so we corrected the series and forecast the ordinary activity.

## 10. Phase 4 · LSTM: −40% vs naive, but a median does as well

[Salah Chebbi] The LSTM cuts the error of the naive forecast by 40 percent and beats the simple RNN and ARIMA. But an 8-week moving median does slightly better. With 202 weeks, a regime change and random spikes, that is expected, and we show it instead of hiding it. On the second KPI, customers lost, the LSTM is the best.

## 11. Phase 4 · Leakage check: a 0.95 AUC would be a lie

[Raed Meddeb] Before modelling churn, we tested every column: can its blanks alone guess the target? Ten columns can. If we keep only three blank flags, the AUC jumps to 0.95. That is not a good model, it is a model reading the answer. Without them we get 0.75 — the honest level.

## 12. Phase 4 · Churn model: XGBoost, AUC 0.751, recall 79%

[Raed Meddeb] Customer grain, twelve profile features, a split per customer so nobody is in both training and test. Three models; XGBoost wins and is well calibrated. At our threshold it catches 79 percent of the leavers. Targeting the top 30 percent of scores reaches half of the departures.

## 13. Phase 4 · Why customers leave

[Raed Meddeb] SHAP tells us why. The strongest signal is an overdue file review. Churn peaks at 25 to 44 years and after 5 to 10 years of relationship, and holding several accounts protects. The segment barely matters. Caveat: a neglected file can also be a consequence of leaving — so we report the model with and without these features.

## 14. Phase 5 · The VIGIE application

[Ibrahim Grira] The application has five pages around the three required features: summary KPIs, an explained prediction on a fictitious profile, and the LSTM forecast. It only reads aggregates and the model's trees in JSON — no customer data. Live demo next.

## 15. Phase 5 · UML: use cases, sequence, classes

[Ibrahim Grira] Three diagrams: the global use cases with four actors, the sequence of a prediction request, and the classes of the application — the model, the prediction, the artefact store and the fictitious generator.

## 16. Phase 5 · Tests, CI and data protection

[Ibrahim Grira] Twenty-six automated tests run on every push with GitHub Actions. They check the encoding, the model, every page of the app — and the confidentiality rules: if anyone commits a data file or a customer identifier, the build fails.

## 17. Live demo

[Ibrahim Grira] Demo plan (5 minutes): overview and the grain note; prediction with the default profile, then move 'months since last review' to 100 and show the score and the drivers change; fictitious portfolio; forecast page. Backup: the video in 07_presentation if the network fails.

## 18. Limitations and next steps

[Salah Chebbi] Our limits: a single snapshot, no behavioural data, batch closures mixed with real departures, and a short series. Next steps: separate batch closures at the source, add monthly behavioural snapshots, re-train regularly, and measure the value of a retention campaign against a control group.

## 19. Conclusion: watch the files nobody reviews

[Raed Meddeb] To conclude: we delivered the full chain, and every stage is verified. The main lesson: question the numbers before trusting them. And the business message: an overdue file review is the strongest warning sign — the bank can act on it today. Thank you; we are happy to take your questions.
