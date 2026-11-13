# Déploiement de l'application VIGIE

L'application est une application **Streamlit**. Elle ne lit que le dossier `05_web_app/artifacts/`
(agrégats et paramètres du modèle) : le déploiement ne transporte **aucune donnée**.

## 1. Lancer en local

```bash
pip install -r 05_web_app/requirements.txt
```

```bash
streamlit run 05_web_app/app.py
```

L'application s'ouvre sur <http://localhost:8501>. La commande se lance **depuis la racine du dépôt**, pour que le
thème `.streamlit/config.toml` soit pris en compte.

## 2. Déployer sur Streamlit Community Cloud (gratuit)

1. Pousser le dépôt sur GitHub (branche `main`).
2. Ouvrir <https://share.streamlit.io> et se connecter avec le compte GitHub du groupe.
3. **Create app → Deploy a public app from GitHub**, puis renseigner :

   | Champ | Valeur |
   |---|---|
   | Repository | `raed1205/projet-integre-churn` |
   | Branch | `main` |
   | Main file path | `05_web_app/app.py` |
   | App URL | par exemple `vigie-bi5` |

4. **Advanced settings → Python version : 3.11**, puis **Deploy**.
5. Copier l'URL obtenue dans le `README.md` principal (section « Application déployée »).

Streamlit Cloud installe automatiquement `05_web_app/requirements.txt` (le fichier le plus proche du point d'entrée)
et lit le thème dans `.streamlit/config.toml` à la racine. Aucun secret n'est nécessaire.

> Si le dépôt est privé, Streamlit Community Cloud permet de déployer **une** application privée par compte ; il
> faut alors inviter les tuteurs comme lecteurs de l'application (menu *Share*).

## 3. Autres hébergeurs

| Hébergeur | Réglage |
|---|---|
| Hugging Face Spaces | SDK *Streamlit* ; copier le contenu de `05_web_app/` et `.streamlit/` à la racine du Space |
| Render / Railway | commande de démarrage : `streamlit run 05_web_app/app.py --server.port $PORT --server.address 0.0.0.0` |

## 4. Mettre à jour l'application après un ré-entraînement

1. Ré-exécuter les notebooks de `04_machine_learning/notebooks/` (ils réécrivent `05_web_app/artifacts/`).
2. Lancer les tests : `pytest 05_web_app/tests` — ils vérifient notamment qu'aucun identifiant ni aucun petit effectif
   n'a été publié.
3. Commiter et pousser : Streamlit Cloud redéploie tout seul.

## 5. Vérifications avant la soutenance

- [ ] L'URL publique s'ouvre en navigation privée.
- [ ] Les cinq pages s'affichent sans erreur.
- [ ] Le formulaire de prédiction renvoie un score et ses facteurs.
- [ ] L'URL figure dans le `README.md` principal.
- [ ] Une vidéo de secours de la démonstration est enregistrée (`07_presentation/`).
