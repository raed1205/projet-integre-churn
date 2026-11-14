# data/ — local data folder (never versioned)

This folder holds the **anonymised dataset** provided by the supervisors. Its content is excluded from Git by
`.gitignore`: only this README is versioned.

## Getting the data

Copy the files of the `data/` folder of the supervisors' repository here:

| File | Content |
|---|---|
| `data_churn.csv` | main file: 483,536 rows, 32 columns |
| `ACCOUNT_CATEGORY.xlsx` | account families |
| `CLOSURE_REASON.xlsx` | closure reasons |
| `CURRENCY.xlsx` | currencies |
| `INDUSTRY.xlsx` | industry sections |
| `TARGET.xlsx` | lines of business |

To keep the data elsewhere, set the `VIGIE_DATA_DIR` environment variable to that folder.

Expected fingerprint of `data_churn.csv` (SHA-256):
`858551b4293ee1abce4d3aaeac3dea07d817cfd80e111dd52dcff5b06d9fb732` — the first notebook checks it.

## Rules

* The data is for **educational use** within this project only; it is never copied to the repository or to an
  external service.
* No attempt is made to identify the institution, a branch or a customer.
* Deliverables (notebooks, report, application) only show **aggregates**.
