# Mesures DAX — rapport Power BI VIGIE

> **Groupe BI 5** · Projet Intégré, ESPRIT School of Business
> Chaque mesure est donnée avec son **grain**, sa **formule** et sa **valeur attendue**. Les valeurs attendues ont été
> calculées en SQL sur l'entrepôt chargé (voir [`02_data_warehouse/kpis.md`](../02_data_warehouse/kpis.md)) : une
> mesure DAX est juste si elle affiche ce chiffre, sans filtre.

## 1. Le modèle sémantique

Tables importées depuis PostgreSQL (schéma `dwh`) : `fait_compte`, `dim_client`, `dim_date`, `dim_agence`,
`dim_secteur`, `dim_categorie_compte`, `dim_devise`, `dim_motif_cloture`, `dim_produit`.

| Relation | Cardinalité | Direction du filtre | État |
|---|---|---|---|
| `dim_client[client_id]` → `fait_compte[client_id]` | 1 : N | simple | active |
| `dim_agence[agence_id]` → `fait_compte[agence_id]` | 1 : N | simple | active |
| `dim_secteur[secteur_id]` → `fait_compte[secteur_id]` | 1 : N | simple | active |
| `dim_categorie_compte[categorie_id]` → `fait_compte[categorie_id]` | 1 : N | simple | active |
| `dim_devise[devise_id]` → `fait_compte[devise_id]` | 1 : N | simple | active |
| `dim_motif_cloture[motif_id]` → `fait_compte[motif_id]` | 1 : N | simple | active |
| `dim_produit[produit_id]` → `fait_compte[produit_id]` | 1 : N | simple | active |
| `dim_date[date_id]` → `fait_compte[date_cloture_id]` | 1 : N | simple | **inactive** |
| `dim_date[date_id]` → `fait_compte[date_ouverture_id]` | 1 : N | simple | **inactive** |

**Pourquoi les deux relations de date sont inactives.** `dim_date` joue deux rôles (ouverture et clôture). Si l'une
des deux était active, un filtre de date réduirait *tous* les indicateurs à ce rôle : un segment « 2023 » ne
garderait que les comptes clos en 2023, et le taux de churn afficherait 100 %. Avec deux relations inactives, les
KPI globaux restent stables et chaque mesure temporelle choisit explicitement son rôle avec `USERELATIONSHIP`.

**Réglages du modèle**

* Marquer `dim_date` comme table de dates (colonne `date_complete`).
* Masquer dans la vue Rapport toutes les colonnes `*_id`, ainsi que `code_client` et `code_compte` : aucun identifiant
  ne doit pouvoir être glissé dans un visuel.
* Trier `dim_date[nom_mois]` par `dim_date[mois]`.
* Créer une table vide `_Mesures` et y ranger toutes les mesures, par dossiers d'affichage.

## 2. Mesures de volume

| Mesure | Grain | Valeur attendue |
|---|---|---:|
| `Nb Comptes` | compte | 410 309 |
| `Nb Comptes Clos` | compte | 148 215 |
| `Nb Comptes Actifs` | compte | 262 094 |
| `Nb Clients` | client | 363 024 |
| `Nb Clients Avec Compte` | client | 319 040 |
| `Nb Clients Partis` | client | 117 345 |

```dax
Nb Comptes = COUNTROWS ( fait_compte )

Nb Comptes Clos = SUM ( fait_compte[est_clos] )

Nb Comptes Actifs = [Nb Comptes] - [Nb Comptes Clos]

Nb Clients = COUNTROWS ( dim_client )

Nb Clients Avec Compte =
CALCULATE ( COUNTROWS ( dim_client ), dim_client[nb_comptes] > 0 )

Nb Clients Partis = SUM ( dim_client[est_churn] )
```

## 3. Mesures de churn

| Mesure | Grain | Valeur attendue |
|---|---|---:|
| `Taux Churn Comptes` | compte | 36,12 % |
| `Taux Churn Clients` | client | 36,78 % |
| `Taux Churn Tous Clients` | client | 32,32 % |
| `Taux Rétention Clients` | client | 63,22 % |
| `Écart Churn vs Moyenne` | client | 0,00 pt (sans filtre) |
| `Indice de Risque` | client | 1,00 (sans filtre) |

```dax
Taux Churn Comptes = DIVIDE ( [Nb Comptes Clos], [Nb Comptes] )

Taux Churn Clients = DIVIDE ( [Nb Clients Partis], [Nb Clients Avec Compte] )

Taux Churn Tous Clients = DIVIDE ( [Nb Clients Partis], [Nb Clients] )

Taux Rétention Clients = 1 - [Taux Churn Clients]

-- Référence : le taux de l'ensemble de la clientèle, quels que soient les filtres posés sur le client.
Taux Churn Clients (global) =
CALCULATE ( [Taux Churn Clients], REMOVEFILTERS ( dim_client ) )

-- Écart en points par rapport à la moyenne : sert à colorer les barres (rouge au-dessus, vert en dessous).
Écart Churn vs Moyenne = [Taux Churn Clients] - [Taux Churn Clients (global)]

-- 1,2 = le segment part 20 % plus souvent que la moyenne.
Indice de Risque = DIVIDE ( [Taux Churn Clients], [Taux Churn Clients (global)] )
```

> ⚠ **Le piège du grain.** `Taux Churn Comptes` se lit avec les dimensions du **compte** (famille, devise, produit,
> motif). `Taux Churn Clients` se lit avec les attributs de **`dim_client`** (segment, tranche d'âge, ancienneté,
> score KYC, dossier complet). Les filtres vont des dimensions vers les faits, pas l'inverse : un filtre sur la
> famille de compte ne filtre pas `dim_client`. Pour compter des clients selon un attribut du compte, utiliser :
>
> ```dax
> Nb Clients (via comptes) = DISTINCTCOUNT ( fait_compte[client_id] )
> ```

## 4. Mesures temporelles

| Mesure | Valeur attendue |
|---|---:|
| `Clôtures` (sans filtre de date) | 148 215 |
| `Clôtures` en 2020 · 2021 · 2022 · 2023 · 2024 | 36 815 · 41 647 · 44 042 · 18 426 · 7 285 |
| `Clôtures` de la semaine du 12/04/2021 | 24 295 |
| `Part des 5 Semaines de Masse` | 51,0 % |
| `Ouvertures` (sans filtre de date) | 309 831 |

```dax
-- Clôtures datées par la date de clôture (rôle « clôture » de dim_date).
Clôtures =
CALCULATE (
    [Nb Comptes Clos],
    USERELATIONSHIP ( fait_compte[date_cloture_id], dim_date[date_id] )
)

-- Ouvertures datées par la date d'ouverture (rôle « ouverture »). Les comptes sans date d'ouverture sont exclus.
Ouvertures =
CALCULATE (
    [Nb Comptes],
    USERELATIONSHIP ( fait_compte[date_ouverture_id], dim_date[date_id] ),
    fait_compte[date_ouverture_id] <> 0
)

-- Cumul des clôtures depuis le début de la période.
Clôtures Cumulées =
VAR fin = MAX ( dim_date[date_complete] )
RETURN
    CALCULATE ( [Clôtures], FILTER ( ALL ( dim_date ), dim_date[date_complete] <= fin ) )

-- Moyenne mobile sur 8 semaines : lisse les pics. À utiliser avec dim_date[lundi_semaine] en axe.
Clôtures Moyenne Mobile 8 sem =
VAR fin = MAX ( dim_date[lundi_semaine] )
RETURN
    DIVIDE (
        CALCULATE (
            [Clôtures],
            FILTER ( ALL ( dim_date ), dim_date[lundi_semaine] > fin - 56 && dim_date[lundi_semaine] <= fin )
        ),
        8
    )

-- Poids des opérations de masse : part des clôtures portée par les 5 semaines les plus chargées.
Part des 5 Semaines de Masse =
VAR semaines = TOPN ( 5, ALL ( dim_date[lundi_semaine] ), [Clôtures], DESC )
RETURN
    DIVIDE (
        SUMX ( semaines, [Clôtures] ),
        CALCULATE ( [Clôtures], ALL ( dim_date ) )
    )
```

> Les dates du jeu de données sont décalées par l'anonymisation. Les axes de temps montrent des **évolutions** ;
> ne pas les rapprocher d'un calendrier réel dans les titres ou les commentaires du rapport.

## 5. Mesures de profil et de valeur

| Mesure | Grain | Valeur attendue |
|---|---|---:|
| `Ancienneté Moyenne Clients` | client | 11,98 ans |
| `Ancienneté Moyenne Comptes Actifs` | compte | 8,24 ans |
| `Solde Médian Comptes Actifs` | compte | 14 |
| `Solde Moyen Comptes Actifs` | compte | −495,46 |
| `Part Comptes Débiteurs` | compte | 17,26 % |
| `Part Clients Multi-Équipés` | client | 14,25 % |
| `Part Dossiers Complets` | client | 47,25 % |
| `Part Revues en Retard` | client | 51,28 % |
| `Comptes par Client` | client | 1,29 |

```dax
Ancienneté Moyenne Clients =
CALCULATE ( AVERAGE ( dim_client[anciennete_annees] ), dim_client[nb_comptes] > 0 )

Ancienneté Moyenne Comptes Actifs =
DIVIDE (
    CALCULATE ( AVERAGE ( fait_compte[anciennete_compte_jours] ), fait_compte[est_clos] = 0 ),
    365.25
)

-- La médiane, pas la moyenne : quelques gros encours de crédit tirent la moyenne vers le bas.
Solde Médian Comptes Actifs =
CALCULATE ( MEDIAN ( fait_compte[solde] ), fait_compte[est_clos] = 0 )

Solde Moyen Comptes Actifs =
CALCULATE ( AVERAGE ( fait_compte[solde] ), fait_compte[est_clos] = 0 )

Part Comptes Débiteurs =
DIVIDE (
    CALCULATE ( COUNTROWS ( fait_compte ), fait_compte[est_clos] = 0, fait_compte[est_debiteur] = TRUE () ),
    CALCULATE ( COUNTROWS ( fait_compte ), fait_compte[est_clos] = 0 )
)

Part Clients Multi-Équipés =
DIVIDE (
    CALCULATE ( COUNTROWS ( dim_client ), dim_client[nb_comptes] > 1 ),
    [Nb Clients Avec Compte]
)

Part Dossiers Complets =
DIVIDE (
    CALCULATE ( COUNTROWS ( dim_client ), dim_client[nb_comptes] > 0, dim_client[dossier_complet] = TRUE () ),
    [Nb Clients Avec Compte]
)

Part Revues en Retard =
DIVIDE (
    CALCULATE ( COUNTROWS ( dim_client ), dim_client[nb_comptes] > 0, dim_client[revue_en_retard] = TRUE () ),
    CALCULATE ( COUNTROWS ( dim_client ), dim_client[nb_comptes] > 0, NOT ISBLANK ( dim_client[revue_en_retard] ) )
)

Comptes par Client = DIVIDE ( [Nb Comptes], [Nb Clients Avec Compte] )

-- Valeur d'un client : somme des soldes de ses comptes actifs, puis médiane sur les clients du segment.
Solde Médian par Client =
MEDIANX (
    FILTER ( VALUES ( dim_client[client_id] ), CALCULATE ( [Nb Comptes Actifs] ) > 0 ),
    CALCULATE ( SUM ( fait_compte[solde] ), fait_compte[est_clos] = 0 )
)
```

## 6. Valeurs de contrôle par segment

À comparer à la page 3 du rapport (filtre sur `dim_client[segment]`).

| Segment | `Nb Clients Avec Compte` | `Taux Churn Clients` | `Ancienneté Moyenne Clients` | `Comptes par Client` | `Part Clients Multi-Équipés` | `Part Dossiers Complets` | `Solde Médian par Client` |
|---|---:|---:|---:|---:|---:|---:|---:|
| Retail | 290 629 | 37,0 % | 11,8 ans | 1,17 | 10,8 % | 48,1 % | 88 |
| Corporate Small | 23 216 | 34,1 % | 13,3 ans | 1,98 | 44,4 % | 33,7 % | 78 |
| Corporate | 3 097 | 31,8 % | 15,3 ans | 5,76 | 78,6 % | 52,0 % | −79 |
| Premium | 2 098 | 37,7 % | 14,6 ans | 2,68 | 57,6 % | 68,2 % | 385 |

Par tranche d'âge et par famille de compte : voir les tableaux de [`kpis.md`](../02_data_warehouse/kpis.md).

## 7. Mise en forme conditionnelle et libellés dynamiques

```dax
-- Couleur des barres : rouge au-dessus de la moyenne, vert en dessous (Format → Couleurs → fx → Valeur du champ).
Couleur Churn = IF ( [Écart Churn vs Moyenne] > 0, "#D62839", "#2A9D8F" )

-- Titre dynamique de la page 1.
Titre Vue d'ensemble =
"Churn : " & FORMAT ( [Taux Churn Comptes], "0.0 %" ) & " des comptes · "
    & FORMAT ( [Taux Churn Clients], "0.0 %" ) & " des clients"

-- Avertissement affiché quand un visuel par famille, devise ou produit est à l'écran.
Avertissement Non Renseigné =
"Lecture : " & FORMAT (
    DIVIDE ( CALCULATE ( [Nb Comptes Clos], dim_categorie_compte[categorie_id] = 0 ), [Nb Comptes Clos] ), "0 %"
) & " des comptes clos n'ont plus de famille renseignée ; le taux des autres familles est sous-estimé."
```

Valeur attendue pour le pourcentage de `Avertissement Non Renseigné` : **68 %** (100 478 comptes clos sur 148 215).

## 8. Liste de vérification des mesures

- [ ] Sans aucun filtre, les six mesures de volume affichent les valeurs attendues.
- [ ] `Taux Churn Comptes` = 36,12 % et `Taux Churn Clients` = 36,78 %.
- [ ] La somme de `Clôtures` par année redonne 148 215.
- [ ] Un segment sur `dim_date[annee]` ne modifie pas `Nb Comptes` (les relations de date sont bien inactives).
- [ ] Le tableau par segment correspond à la section 6.
- [ ] Aucun visuel n'expose `code_client` ni `code_compte`.
