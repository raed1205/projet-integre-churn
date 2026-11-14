# Power BI report screenshots

Drop the screenshots of the report pages here, **with no customer row**:

| Expected file | Page |
|---|---|
| `page1_overview.png` | Overview |
| `page2_churn.png` | Churn analysis |
| `page3_segments.png` | Customer segmentation |

Before taking them, check that no visual shows `customer_code` or `account_code`, and that no table lists
individual rows. The `.pbix` file is **never** committed: it is handed to the supervisors outside GitHub.

Meanwhile, [`../mockups/`](../mockups/) shows the three target pages, produced by the JavaScript interface from the
same aggregates: they serve as a layout model and as a reference for the figures.
