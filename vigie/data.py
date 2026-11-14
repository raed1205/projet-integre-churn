"""Loading, typing and building the analysis grains.

Three grains coexist in the source file:

* **row**      : one customer / account / product match (483,536 rows);
* **account**  : one row per ``ACCOUNT_NO`` (410,309 accounts);
* **customer** : one row per ``CUSTOMER_NO`` (363,024 customers).

Every function is deterministic: same file => same figures.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from . import config

MAIN_FILE = "data_churn.csv"
REFERENCE_FILES = {
    "ACCOUNT_CATEGORY": "CATEGORY_ID",
    "CLOSURE_REASON": "REASON_ID",
    "CURRENCY": "CURRENCY_CODE",
    "INDUSTRY": "INDUSTRY_CODE",
    "TARGET": "TARGET_CODE",
}

DATE_COLUMNS = [
    "CUST_OPENING_DATE", "LAST_REVIEW_DATE", "NEXT__REVIEW_DATE",
    "ACCT_OPENING_DATE", "ACCT_CLOSE_DATE", "STARTDATE", "MATURITYDATE",
]
NUMERIC_COLUMNS = ["BIRTH_PERIOD", "SALARY", "ACCT_BALANCE", "AMOUNT", "FIXEDRATE"]

CUSTOMER_COLUMNS = [
    "CUSTOMER_NO", "NATIONALITY_REGION", "RESIDENCE_REGION", "MARITAL_STATUS",
    "BIRTH_PERIOD", "CUST_OPENING_DATE", "NATURE_CLIENT", "PARTYCLASS", "LOB",
    "SCORE_KYC", "COMPLETED_FILE", "LAST_REVIEW_DATE", "NEXT__REVIEW_DATE",
    "INDUSTRY", "SALARY", "BRANCH_GROUP",
]
ACCOUNT_COLUMNS = [
    "ACCOUNT_NO", "CUSTOMER_NO", "ACCOUNT_STATUS", "ACCT_OPENING_DATE",
    "ACCT_CLOSE_DATE", "ACCOUNT_CATEGORY", "ACCOUNT_TYPE_DESC", "CURRENCY",
    "CLOSURE_REASON", "ACCT_BALANCE", "PRODUCT_GROUP", "PRODUCT_LINE",
    "STARTDATE", "MATURITYDATE", "AMOUNT", "FIXEDRATE", "PRODUCT_STATUS",
]


def _data_dir(folder: str | Path | None) -> Path:
    d = Path(folder) if folder else config.DATA_DIR
    if not (d / MAIN_FILE).exists():
        raise FileNotFoundError(
            f"{MAIN_FILE} not found in {d}. Copy the files provided by the supervisors into data/ "
            "(git-ignored) or set VIGIE_DATA_DIR."
        )
    return d


def fingerprint(folder: str | Path | None = None) -> dict:
    """SHA-256 fingerprint of the source file: proves which file the figures were computed on."""
    path = _data_dir(folder) / MAIN_FILE
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return {"file": MAIN_FILE, "sha256": h.hexdigest(), "bytes": path.stat().st_size}


def load_raw(folder: str | Path | None = None) -> pd.DataFrame:
    """Read the CSV as is: everything as text, blanks stay missing values."""
    return pd.read_csv(_data_dir(folder) / MAIN_FILE, dtype=str, keep_default_na=False, na_values=[""])


def cast_types(df: pd.DataFrame) -> pd.DataFrame:
    """Convert the YYYYMMDD dates and the numeric columns."""
    out = df.copy()
    for c in DATE_COLUMNS:
        out[c] = pd.to_datetime(out[c], format="%Y%m%d", errors="coerce")
    for c in NUMERIC_COLUMNS:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    return out


def load(folder: str | Path | None = None) -> pd.DataFrame:
    """Row-grain data, typed."""
    return cast_types(load_raw(folder))


def load_references(folder: str | Path | None = None) -> dict[str, pd.DataFrame]:
    """The five Excel label files, keyed by name."""
    d = _data_dir(folder)
    refs = {}
    for name in REFERENCE_FILES:
        ref = pd.read_excel(d / f"{name}.xlsx", dtype=str)
        ref.columns = [c.strip() for c in ref.columns]
        refs[name] = ref
    return refs


def reference_date(df: pd.DataFrame) -> pd.Timestamp:
    """Date of the snapshot: the last account event observed."""
    return max(df["ACCT_OPENING_DATE"].max(), df["ACCT_CLOSE_DATE"].max())


def account_grain(df: pd.DataFrame) -> pd.DataFrame:
    """One row per account.

    De-duplication rule (justified in the report):

    1. rows without ``ACCOUNT_NO`` are set aside (customers with no account);
    2. when an account carries several closing dates, the **first** one is kept
       (it is the churn event; later ones are adjustments);
    3. in the rare cases (16 accounts) where the fixed rate differs between rows,
       the highest is kept — an arbitrary but deterministic rule;
    4. ``N_SOURCE_ROWS`` keeps the number of merged rows, for reconciliation.
    """
    a = df[df["ACCOUNT_NO"].notna()]
    by_account = a.groupby("ACCOUNT_NO", sort=False)
    n_rows = by_account.size().rename("N_SOURCE_ROWS")
    rate = by_account["FIXEDRATE"].max()
    accounts = (
        a.sort_values(["ACCOUNT_NO", "ACCT_CLOSE_DATE", "CLOSURE_REASON"], na_position="last")
        .drop_duplicates("ACCOUNT_NO", keep="first")
        .set_index("ACCOUNT_NO")
        .join(n_rows)
    )
    accounts["FIXEDRATE"] = rate
    accounts = accounts.reset_index()
    accounts["CHURN"] = (accounts["ACCOUNT_STATUS"] == "Closed").astype(int)
    return accounts


def customer_grain(df: pd.DataFrame, accounts: pd.DataFrame | None = None) -> pd.DataFrame:
    """One row per customer, with the number of accounts and the churn flag.

    Customer churn = **all** of the customer's accounts are closed. In this dataset no
    customer has both an active and a closed account, so "all closed" and "at least one
    closed" coincide. Customers with no account have a missing ``CHURN`` (out of scope).
    """
    if accounts is None:
        accounts = account_grain(df)
    customers = df[CUSTOMER_COLUMNS].drop_duplicates("CUSTOMER_NO").set_index("CUSTOMER_NO")
    agg = accounts.groupby("CUSTOMER_NO").agg(
        N_ACCOUNTS=("ACCOUNT_NO", "size"),
        N_CLOSED_ACCOUNTS=("CHURN", "sum"),
        CHURN_DATE=("ACCT_CLOSE_DATE", "max"),
    )
    customers = customers.join(agg)
    customers["N_ACCOUNTS"] = customers["N_ACCOUNTS"].fillna(0).astype(int)
    has_account = customers["N_ACCOUNTS"] > 0
    customers["CHURN"] = pd.NA
    customers.loc[has_account, "CHURN"] = (
        customers.loc[has_account, "N_CLOSED_ACCOUNTS"] == customers.loc[has_account, "N_ACCOUNTS"]
    ).astype(int)
    customers["CHURN"] = customers["CHURN"].astype("Int64")
    return customers.reset_index()


NOT_PROVIDED = "Not provided"
AGE_BANDS = ["Under 18", "18–24", "25–34", "35–44", "45–54", "55–64", "65 and over"]
TENURE_BANDS = ["Under 2 years", "2–5 years", "5–10 years", "10–15 years", "15 years and over"]


def age_band(birth_period: pd.Series, ref_year: int) -> pd.Series:
    """Readable age band, computed at the middle of the 5-year birth period."""
    age = ref_year - (birth_period + 2)
    return (pd.cut(age, bins=[-1, 17, 24, 34, 44, 54, 64, 200], labels=AGE_BANDS)
            .astype("object").fillna(NOT_PROVIDED))


def tenure_band(years: pd.Series) -> pd.Series:
    return (pd.cut(years, bins=[-0.01, 2, 5, 10, 15, 100], labels=TENURE_BANDS)
            .astype("object").fillna(NOT_PROVIDED))


# --------------------------------------------------------------------------
# Display labels
# --------------------------------------------------------------------------
# The reference files and some codes carry French labels. They are kept untouched in the
# warehouse (they are source data); this dictionary gives the English wording used by the
# application, the dashboards and the report.
ENGLISH_LABELS = {
    # account families (ACCOUNT_CATEGORY.xlsx)
    "Autres comptes": "Other accounts", "Coffres": "Safe-deposit boxes", "Comptes courants": "Current accounts",
    "Comptes en devises": "Foreign-currency accounts", "Comptes indisponibles": "Blocked accounts",
    "Contentieux": "Litigation", "Credit automobile": "Car loans", "Credit consommation": "Consumer credit",
    "Credit immobilier": "Mortgages", "Credit investissement": "Investment loans", "Epargne": "Savings",
    "Exigibles": "Demand deposits", "Financement court terme": "Short-term financing",
    "Placements a terme": "Term deposits",
    # closure reasons (CLOSURE_REASON.xlsx)
    "Autre": "Other", "Cessation d'activite": "Business closure", "Changement d'adresse": "Change of address",
    "Changement d'employeur": "Change of employer", "Deces": "Death", "Delais de traitement": "Processing delays",
    "Offre concurrente": "Competing offer", "Qualite de service": "Quality of service",
    "Reclamation non traitee": "Unresolved complaint", "Refus de credit": "Loan refusal",
    "Tarification": "Pricing", "Transfert interne": "Internal transfer",
    # currencies (CURRENCY.xlsx)
    "Monnaie locale": "Local currency", "Monnaie locale convertible": "Convertible local currency",
    "Euro": "Euro", "Dollar americain": "US dollar", "Autres devises": "Other currencies",
    # industry sections (INDUSTRY.xlsx)
    "Agriculture, sylviculture et peche": "Agriculture, forestry and fishing",
    "Industries extractives": "Mining and quarrying", "Industrie manufacturiere": "Manufacturing",
    "Energie": "Energy", "Eau et dechets": "Water and waste", "Construction": "Construction",
    "Commerce": "Trade", "Transports et entreposage": "Transport and storage",
    "Hebergement et restauration": "Accommodation and food services",
    "Information et communication": "Information and communication",
    "Activites financieres et assurance": "Finance and insurance", "Activites immobilieres": "Real estate",
    "Activites specialisees et scientifiques": "Professional and scientific activities",
    "Services administratifs et de soutien": "Administrative and support services",
    "Administration publique": "Public administration", "Enseignement": "Education",
    "Sante et action sociale": "Health and social work", "Arts et loisirs": "Arts and recreation",
    "Autres services": "Other services", "Activites des menages": "Household activities",
    "Organismes extraterritoriaux": "Extraterritorial organisations",
    "Non renseigne ou autre": "Not provided or other",
    # product groups (codes of the main file)
    "EPARGNE": "Savings", "COMPTE_COURANT": "Current account", "CREDIT_IMMOBILIER": "Mortgage",
    "CREDIT_CONSO": "Consumer credit", "PLACEMENT": "Term deposit", "DEPOT_VUE": "Demand deposit",
    "FINANCEMENT_COURT_TERME": "Short-term financing", "CREDIT_INVESTISSEMENT": "Investment loan",
    "INDISPONIBLE": "Blocked", "COMPTE_DEVISES": "Foreign-currency account", "CREDIT_AUTO": "Car loan",
    "COFFRE": "Safe-deposit box",
    # zones (codes of the main file)
    "LOCAL": "Local", "EUROPE": "Europe", "AFRIQUE_MO": "Africa / Middle East", "AMERIQUES": "Americas",
    "ASIE_OCEANIE": "Asia / Oceania", "AUTRE": "Other",
}
MARITAL_STATUS_LABELS = {"C": "Single", "M": "Married", "D": "Divorced", "V": "Widowed"}
CUSTOMER_TYPE_LABELS = {"PPH": "Individual", "PM": "Legal entity", "PRO": "Professional",
                        "TRPP": "Other (TRPP)", "TRPM": "Other (TRPM)"}


def english(label) -> str:
    """English wording of a source label (unknown labels are returned unchanged)."""
    return ENGLISH_LABELS.get(label, label)
