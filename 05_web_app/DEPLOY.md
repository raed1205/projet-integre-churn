# Deploying the VIGIE application

The application is a **Streamlit** app. It only reads the `05_web_app/artifacts/` folder (aggregates and model
parameters): deploying it carries **no data**.

## 1. Run locally

```bash
pip install -r 05_web_app/requirements.txt
```

```bash
streamlit run 05_web_app/app.py
```

The app opens at <http://localhost:8501>. Run the command **from the repository root** so that the theme in
`.streamlit/config.toml` is applied.

## 2. Deploy on Streamlit Community Cloud (free)

1. Push the repository to GitHub (`main` branch).
2. Open <https://share.streamlit.io> and sign in with the group's GitHub account.
3. **Create app → Deploy a public app from GitHub**, then fill in:

   | Field | Value |
   |---|---|
   | Repository | `raed1205/projet-integre-churn` |
   | Branch | `main` |
   | Main file path | `05_web_app/app.py` |
   | App URL | e.g. `vigie-bi5` |

4. **Advanced settings → Python version: 3.11**, then **Deploy**.
5. Copy the resulting URL into the main `README.md` ("Deployed application" section).

Streamlit Cloud installs `05_web_app/requirements.txt` automatically (the file closest to the entry point) and reads
the theme from `.streamlit/config.toml` at the root. No secret is needed.

> If the repository is private, Streamlit Community Cloud allows **one** private app per account; invite the
> supervisors as viewers of the app (*Share* menu).

## 3. Other hosts

| Host | Setting |
|---|---|
| Hugging Face Spaces | *Streamlit* SDK; copy the content of `05_web_app/` and `.streamlit/` to the root of the Space |
| Render / Railway | start command: `streamlit run 05_web_app/app.py --server.port $PORT --server.address 0.0.0.0` |

## 4. Updating the application after re-training

1. Re-run the notebooks of `04_machine_learning/notebooks/` (they rewrite `05_web_app/artifacts/`).
2. Run the tests: `pytest 05_web_app/tests` — among other things they check that no identifier and no small count
   was published.
3. Commit and push: Streamlit Cloud redeploys on its own.

## 5. Checks before the defence

- [ ] The public URL opens in a private browser window.
- [ ] The five pages display without error.
- [ ] The prediction form returns a score and its drivers.
- [ ] The URL appears in the main `README.md`.
- [ ] A backup video of the demo is recorded (`07_presentation/`).
