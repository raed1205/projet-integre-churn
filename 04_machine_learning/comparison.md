# Tableaux comparatifs des modèles — VIGIE · Groupe BI 5

> Fichier généré par `src/rapport_comparatif.py` à partir de `resultats/*.json` (eux-mêmes écrits par les
> notebooks). Aucun chiffre n'est saisi à la main.  
> Fichier source : `data_churn.csv`, SHA-256 `858551b4293ee1ab…`

## 1. Prédiction du churn (grain client, jeu de test : 47 856 clients)

Découpage par client (`GroupShuffleSplit`, 70 / 15 / 15). Seuil de décision choisi sur la validation (F1 maximal).

| Modèle | ROC-AUC | PR-AUC | Precision | Recall | F1 | Accuracy | Brier | Seuil |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Référence (taux moyen) | 0,500 | 0,369 | 0,000 | 0,000 | 0,000 | 0,631 | 0,233 | 0,50 |
| Régression logistique | 0,686 | 0,538 | 0,518 | 0,676 | 0,586 | 0,649 | 0,209 | 0,34 |
| Random Forest | 0,748 | 0,607 | 0,515 | 0,813 | 0,631 | 0,649 | 0,193 | 0,30 |
| XGBoost | 0,751 | 0,611 | 0,518 | 0,807 | 0,631 | 0,652 | 0,192 | 0,30 |
| **XGBoost optimisé (retenu)** | 0,751 | 0,611 | 0,526 | 0,790 | 0,632 | 0,661 | 0,192 | 0,32 |

**Matrices de confusion (jeu de test)**

| Modèle | Vrais positifs | Faux positifs | Faux négatifs | Vrais négatifs |
|---|---:|---:|---:|---:|
| Référence (taux moyen) | 0 | 0 | 17 638 | 30 218 |
| Régression logistique | 11 914 | 11 098 | 5 724 | 19 120 |
| Random Forest | 14 344 | 13 521 | 3 294 | 16 697 |
| XGBoost | 14 230 | 13 228 | 3 408 | 16 990 |
| XGBoost optimisé (retenu) | 13 935 | 12 536 | 3 703 | 17 682 |

**Modèle retenu : XGBoost optimisé.** Hyperparamètres (recherche aléatoire, validation croisée par client) : `colsample_bytree` = 0.8, `learning_rate` = 0.05, `max_depth` = 7, `min_child_weight` = 1, `n_estimators` = 300, `reg_lambda` = 1, `subsample` = 0.9.

Stabilité (ROC-AUC) : entraînement 0,768 · validation 0,752 · test 0,751.

### Contrôle de la fuite de cible

| Modèle | ROC-AUC sur le test |
|---|---:|
| Modèle AVEC variables de fuite | 0,951 |
| Modèle SANS variable de fuite (retenu) | 0,751 |

Colonnes exclues pour fuite (AUC du seul indicateur « valeur manquante » ≥ 0,80) :

| Colonne | % vide si actif | % vide si clos | AUC du vide | Verdict |
|---|---:|---:|---:|---|
| `ACCT_CLOSE_DATE` | 100,0 | 0,0 | 1,000 | FUITE — exclue |
| `CLOSURE_REASON` | 100,0 | 9,1 | 0,954 | FUITE — exclue |
| `CURRENCY` | 0,0 | 67,8 | 0,839 | FUITE — exclue |
| `ACCOUNT_CATEGORY` | 0,0 | 67,8 | 0,839 | FUITE — exclue |
| `ACCT_OPENING_DATE` | 0,0 | 67,8 | 0,839 | FUITE — exclue |
| `ACCOUNT_TYPE_DESC` | 0,0 | 67,8 | 0,839 | FUITE — exclue |
| `ACCT_BALANCE` | 0,0 | 67,8 | 0,839 | FUITE — exclue |
| `AMOUNT` | 15,0 | 77,7 | 0,813 | FUITE — exclue |
| `PRODUCT_LINE` | 14,7 | 76,0 | 0,806 | FUITE — exclue |
| `PRODUCT_GROUP` | 14,7 | 76,0 | 0,806 | FUITE — exclue |
| `COMPLETED_FILE` | 41,0 | 62,5 | 0,608 | À surveiller |

`PRODUCT_STATUS` est exclue elle aussi : ce n'est pas son vide mais ses valeurs (`CLOSE`, `PENDING.CLOSURE`, `UNAUTH`) qui désignent la clôture.

### Analyse de sensibilité (même XGBoost, variables retirées ou ajoutées)

| Scénario | Colonnes | ROC-AUC | PR-AUC | Écart de ROC-AUC |
|---|---:|---:|---:|---:|
| Modèle retenu (12 variables) | 31 | 0,751 | 0,611 | +0,000 |
| + secteur d'activité et groupe d'agences (14 variables) | 65 | 0,756 | 0,626 | +0,006 |
| Sans les deux variables de revue | 29 | 0,730 | 0,593 | −0,021 |
| Sans la famille Conformité | 22 | 0,660 | 0,505 | −0,091 |
| Conformité seule | 9 | 0,716 | 0,573 | −0,035 |
| Relation seule | 11 | 0,628 | 0,470 | −0,123 |
| Démographie seule | 11 | 0,581 | 0,426 | −0,170 |

### Importance des variables

| Variable | Gain XGBoost | SHAP (part) |
|---|---:|---:|
| Mois avant la prochaine revue | 20,0 % | 34,2 % |
| Mois depuis la dernière revue | 40,0 % | 18,5 % |
| Ancienneté client (années) | 10,0 % | 11,8 % |
| Âge | 11,5 % | 11,0 % |
| Nombre de comptes | 7,2 % | 5,5 % |
| Score KYC | 3,2 % | 4,9 % |
| Dossier complet | 0,4 % | 4,3 % |
| Revenu déclaré | 2,1 % | 3,0 % |
| Statut marital | 1,8 % | 2,6 % |
| Segment commercial | 1,3 % | 1,6 % |
| Nature du client | 1,0 % | 1,5 % |
| Zone de résidence | 1,6 % | 1,2 % |

### Courbe de gains et niveaux de risque

| Clients ciblés (scores décroissants) | Départs captés | Taux de churn dans la cible | Lift |
|---:|---:|---:|---:|
| 5 % | 10,0 % | 73,9 % | 2,00 |
| 10 % | 19,0 % | 70,1 % | 1,90 |
| 20 % | 35,4 % | 65,3 % | 1,77 |
| 30 % | 50,0 % | 61,5 % | 1,67 |
| 50 % | 74,4 % | 54,8 % | 1,49 |

| Niveau de risque | Clients du test | Taux de churn observé |
|---|---:|---:|
| Faible (< 25 %) | 17 707 | 15,0 % |
| Modéré (25–50 %) | 14 647 | 37,9 % |
| Élevé (≥ 50 %) | 15 502 | 60,9 % |

## 2. Prévision du KPI — clôtures de comptes par semaine

Série corrigée des opérations de masse · 202 semaines · entraînement 142 · validation 20 · test 40 (du 2023-05-22 au 2024-02-19) · fenêtre de 8 semaines · prévision à un pas.

| Modèle | Type | MAE | RMSE | MAE vs naïve | RMSE vs naïve |
|---|---|---:|---:|---:|---:|
| Médiane mobile 8 semaines | Référence | 272,4 | 549,8 | -43 % | -36 % |
| LSTM | Deep Learning | 287,2 (± 6,4 sur 3 graines) | 577,2 | -40 % | -33 % |
| RNN simple | Deep Learning | 323,6 (± 9,3 sur 3 graines) | 607,7 | -32 % | -29 % |
| ARIMA(2, 1, 2) | Référence | 334,7 | 576,7 | -30 % | -33 % |
| Moyenne mobile 4 semaines | Référence | 373,0 | 575,3 | -22 % | -33 % |
| Naïve (dernière valeur) | Référence | 478,3 | 859,5 | +0 % | +0 % |

## 3. Bonus — second KPI : clients perdus par semaine

Série corrigée des opérations de masse · 202 semaines · entraînement 142 · validation 20 · test 40 (du 2023-05-22 au 2024-02-19) · fenêtre de 8 semaines · prévision à un pas.

| Modèle | Type | MAE | RMSE | MAE vs naïve | RMSE vs naïve |
|---|---|---:|---:|---:|---:|
| LSTM | Deep Learning | 124,5 (± 1,0 sur 3 graines) | 220,2 | -45 % | -52 % |
| Médiane mobile 8 semaines | Référence | 133,3 | 216,4 | -41 % | -53 % |
| RNN simple | Deep Learning | 143,6 (± 4,6 sur 3 graines) | 232,8 | -37 % | -49 % |
| ARIMA(2, 1, 2) | Référence | 159,9 | 248,9 | -30 % | -46 % |
| Moyenne mobile 4 semaines | Référence | 196,4 | 276,0 | -14 % | -40 % |
| Naïve (dernière valeur) | Référence | 227,2 | 459,5 | +0 % | +0 % |

**Lecture.** Le LSTM réduit nettement l'erreur de la prévision naïve et fait mieux que le RNN simple, ARIMA et la moyenne mobile. Il ne bat pas la médiane mobile sur les clôtures de comptes ; il obtient la meilleure MAE sur les clients perdus. Le MAPE n'est pas utilisé : il n'est pas défini sur les semaines à zéro.
