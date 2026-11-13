# Catalogue des KPI — VIGIE · Groupe BI 5

Chaque KPI a **un grain, une formule et une valeur de référence**. La valeur de référence est celle que
renvoie l'entrepôt chargé ; elle sert à vérifier que Power BI (DAX) et l'application affichent le même chiffre.

> **Règle d'or : un taux se calcule toujours à son grain.** Un taux de churn « par ligne » (40,3 %) n'est ni le
> taux par compte (36,1 %) ni le taux par client (36,8 %). L'entrepôt étant au grain compte, il n'y a plus de
> confusion possible.

## 1. KPI de volume

| # | KPI | Grain | Formule SQL (schéma `dwh`) | Valeur de référence |
|---|---|---|---|---:|
| K01 | Nombre de comptes | compte | `count(*) FROM fait_compte` | **410 309** |
| K02 | Comptes actifs | compte | `count(*) FILTER (WHERE est_clos = 0)` | **262 094** |
| K03 | Comptes clos | compte | `sum(est_clos)` | **148 215** |
| K04 | Nombre de clients | client | `count(*) FROM dim_client` | **363 024** |
| K05 | Clients avec au moins un compte | client | `count(*) FILTER (WHERE nb_comptes > 0)` | **319 040** |
| K06 | Clients partis | client | `sum(est_churn)` | **117 345** |

## 2. KPI de churn

| # | KPI | Grain | Formule | Valeur de référence |
|---|---|---|---|---:|
| K07 | **Taux de churn (comptes)** | compte | `sum(est_clos) / count(*)` | **36,12 %** |
| K08 | **Taux de churn (clients)** | client | `sum(est_churn) / count(*)` sur les clients avec compte | **36,78 %** |
| K09 | Taux de churn (tous clients) | client | `sum(est_churn) / count(*)` sur tous les clients | **32,32 %** |
| K10 | Taux de rétention (clients) | client | `1 − K08` | **63,22 %** |
| K11 | Clôtures hebdomadaires | semaine | `count(*)` par `lundi_semaine` de la date de clôture, semaines à zéro incluses | médiane **165,5** · moyenne **733,7** |
| K12 | Part des opérations de masse | semaine | part des clôtures portée par les 5 semaines les plus chargées | **51,0 %** |

**Définition du churn.** Un compte est en churn s'il est clos (`ACCOUNT_STATUS = 'Closed'`). Un client est en churn
si **tous** ses comptes sont clos. Aucun client n'ayant à la fois un compte actif et un compte clos (contrôle C17),
les deux lectures sont cohérentes entre elles.

## 3. KPI de profil et de valeur

| # | KPI | Grain | Formule | Valeur de référence |
|---|---|---|---|---:|
| K13 | Ancienneté moyenne des clients | client | `avg(anciennete_annees)` (clients avec compte) | **11,98 ans** (médiane 11,13) |
| K14 | Ancienneté moyenne des comptes actifs | compte | `avg(anciennete_compte_jours) / 365.25` sur `est_clos = 0` | **8,24 ans** |
| K15 | Solde médian des comptes actifs | compte | `percentile_cont(0.5)` de `solde` sur `est_clos = 0` | **14** |
| K16 | Solde moyen des comptes actifs | compte | `avg(solde)` sur `est_clos = 0` | **−495,46** |
| K17 | Part de comptes débiteurs (actifs) | compte | `avg(est_debiteur)` sur `est_clos = 0` | **17,26 %** |
| K18 | Taux de multi-équipement | client | part des clients ayant plus d'un compte | **14,25 %** |
| K19 | Part de dossiers complets | client | `avg(dossier_complet)` (clients avec compte) | **47,25 %** |
| K20 | Part de revues en retard | client | `avg(revue_en_retard)` (clients avec compte) | **51,28 %** |

## 4. Règles de calcul et pièges

1. **Solde moyen ≠ solde médian.** Le solde moyen des comptes actifs est négatif (−495) alors que le solde médian
   est de 14 : quelques gros encours de crédit tirent la moyenne. On affiche la **médiane** ; la moyenne n'est
   donnée que pour mémoire. Les montants étant arrondis et plafonnés, ils servent à **comparer**, jamais comme
   encours réel.
2. **Les KPI de solde et d'ancienneté de compte se lisent sur les comptes actifs.** Pour 68 % des comptes clos, le
   solde, la famille, la devise et la date d'ouverture sont vides. Les calculer « tous comptes » mélangerait deux
   populations qui ne sont pas renseignées de la même façon.
3. **Le churn par famille de compte est sous-estimé.** Les 100 478 comptes clos sans famille renseignée tombent dans
   le membre « Non renseigné » (taux de churn 100 %). Le taux des autres familles ne porte donc que sur les comptes
   clos *dont la famille est connue*. Ce membre doit rester **visible** dans tout graphique par famille, devise ou
   produit ; il ne faut pas le filtrer.
4. **L'ancienneté d'un compte n'est pas calculée quand les dates sont incohérentes.** 20 166 comptes clos ont une
   date d'ouverture postérieure à leur date de clôture ; ils sont signalés par `ouverture_apres_cloture` et leur
   ancienneté est `NULL`.
5. **Les dates sont décalées** (anonymisation). On lit des durées et des évolutions, jamais des dates calendaires.
6. **Aucun agrégat publié en dessous de 20 individus** (application, captures, rapport).

## 5. Valeurs de référence par axe (pour vérifier Power BI)

**Taux de churn par segment commercial (grain client)**

| Segment | Clients | Taux de churn | Ancienneté moyenne | Comptes par client |
|---|---:|---:|---:|---:|
| Retail | 290 629 | 37,0 % | 11,8 ans | 1,17 |
| Corporate Small | 23 216 | 34,1 % | 13,3 ans | 1,98 |
| Corporate | 3 097 | 31,8 % | 15,3 ans | 5,76 |
| Premium | 2 098 | 37,7 % | 14,6 ans | 2,68 |

**Taux de churn par tranche d'âge (grain client)**

| Tranche d'âge | Clients | Taux de churn |
|---|---:|---:|
| < 18 ans | 10 067 | 8,4 % |
| 18–24 ans | 9 054 | 23,2 % |
| 25–34 ans | 52 602 | 44,4 % |
| 35–44 ans | 66 685 | 41,3 % |
| 45–54 ans | 60 413 | 37,1 % |
| 55–64 ans | 47 878 | 35,2 % |
| 65 ans et + | 52 315 | 34,7 % |
| Non renseigné | 20 026 | 30,3 % |

**Taux de churn par famille de compte (grain compte)** — voir le piège n° 3

| Famille de compte | Comptes | Comptes clos | Taux de churn |
|---|---:|---:|---:|
| Epargne | 176 588 | 13 247 | 7,5 % |
| *Non renseigné* | 100 478 | 100 478 | 100,0 % |
| Financement court terme | 22 270 | 6 583 | 29,6 % |
| Comptes courants | 22 224 | 3 786 | 17,0 % |
| Credit immobilier | 15 953 | 3 367 | 21,1 % |
| Credit consommation | 15 495 | 3 545 | 22,9 % |
| Contentieux | 14 289 | 3 449 | 24,1 % |
| Comptes en devises | 13 837 | 3 199 | 23,1 % |
| Exigibles | 8 779 | 1 500 | 17,1 % |
| Autres comptes | 6 080 | 1 800 | 29,6 % |
| Placements a terme | 5 790 | 4 779 | 82,5 % |
| Credit investissement | 3 403 | 886 | 26,0 % |
| Comptes indisponibles | 3 321 | 1 186 | 35,7 % |
| Credit automobile | 1 187 | 271 | 22,8 % |
| Coffres | 615 | 139 | 22,6 % |

**Clôtures par année** : 2020 : 36 815 · 2021 : 41 647 · 2022 : 44 042 · 2023 : 18 426 · 2024 : 7 285 (total 148 215).
