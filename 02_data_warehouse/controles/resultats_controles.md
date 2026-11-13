# Résultats des contrôles de chargement

> Exécution de `controles.sql` sur l'entrepôt chargé — **19 contrôles, 19 OK**.
> Source = schéma `staging` (copie brute des fichiers) · Cible = schéma `dwh` (modèle en étoile).
> À ré-exécuter dans pgAdmin après chaque chargement Talend : le tableau doit être identique.

| Contrôle | Libellé | Attendu | Obtenu | Verdict |
|---|---|---:|---:|:---:|
| C01 | Lignes chargées en staging | 483536 | 483536 | ✔ OK |
| C02 | Comptes distincts : source = table de faits | 410309 | 410309 | ✔ OK |
| C03 | Clients distincts : source = dimension client | 363024 | 363024 | ✔ OK |
| C04 | Lignes source avec compte = somme de nb_lignes_source | 439552 | 439552 | ✔ OK |
| C05 | Clients sans compte (nb_comptes = 0) | 43984 | 43984 | ✔ OK |
| C06 | Comptes clos : source = table de faits | 148215 | 148215 | ✔ OK |
| C07 | Taux de churn par compte (%) | 36.12 | 36.12 | ✔ OK |
| C08 | Clients en churn : source = dimension client | 117345 | 117345 | ✔ OK |
| C09 | Comptes dont la date de clôture n'est pas la première (doit valoir 0) | 0 | 0 | ✔ OK |
| C10 | Somme des soldes : source dédoublonnée = table de faits | −636 613 392,10 | −636 613 392,10 | ✔ OK |
| C11 | Série hebdomadaire : total des clôtures | 148215 | 148215 | ✔ OK |
| C12 | Comptes en double dans les faits (doit valoir 0) | 0 | 0 | ✔ OK |
| C13 | Faits sans client dans la dimension (doit valoir 0) | 0 | 0 | ✔ OK |
| C14 | Incohérences statut / date de clôture (doit valoir 0) | 0 | 0 | ✔ OK |
| C15 | Clôtures antérieures à l'ouverture non signalées (doit valoir 0) | 0 | 0 | ✔ OK |
| C16 | Clients dont nb_comptes ne correspond pas aux faits (doit valoir 0) | 0 | 0 | ✔ OK |
| C17 | Clients à statut mixte actif / clos (doit valoir 0) | 0 | 0 | ✔ OK |
| C18 | Dates des faits absentes de dim_date (doit valoir 0) | 0 | 0 | ✔ OK |
| C19 | Anciennetés de compte négatives (doit valoir 0) | 0 | 0 | ✔ OK |

## Répartitions de contrôle

**Part des faits rattachés au membre « Non renseigné » (clé 0)**

| Dimension | % des comptes |
|---|---:|
| Famille de compte | 24.5 |
| Date de clôture (comptes actifs) | 63.9 |
| Motif de clôture | 67.2 |
| Devise | 24.5 |
| Produit | 36.9 |
| Date d'ouverture | 24.5 |

Ces parts sont identiques aux taux de valeurs manquantes mesurés au grain compte dans le notebook d'analyse
univariée : aucune information n'a été perdue ni inventée pendant le chargement.

**Anomalie de la source signalée, non corrigée**

| Indicateur | Valeur |
|---|---:|
| Comptes clos dont la date d'ouverture est renseignée | 47737 |
| … dont ouverture postérieure à la clôture | 20166 |
| Part | 42.2 % |

Pour ces comptes, la date d'ouverture ne peut pas servir à calculer une ancienneté. L'entrepôt conserve la valeur
source, positionne `ouverture_apres_cloture = true` et laisse `anciennete_compte_jours` à `NULL`.

**Les cinq semaines les plus chargées en clôtures (opérations de masse)**

| Semaine (lundi) | Clôtures | Part du total |
|---|---:|---:|
| 12/04/2021 | 24295 | 16.4 % |
| 21/09/2020 | 22525 | 15.2 % |
| 07/11/2022 | 16301 | 11.0 % |
| 03/10/2022 | 8794 | 5.9 % |
| 01/11/2021 | 3641 | 2.5 % |

Ces cinq semaines portent 51,0 % des 148 215 clôtures. Les dates étant décalées par l'anonymisation, elles ne correspondent à aucun calendrier réel.
