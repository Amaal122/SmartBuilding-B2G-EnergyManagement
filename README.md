# SBEMS — Smart Building Energy Management System

Plateforme Streamlit de supervision énergétique d'un bâtiment tertiaire, développée
pour un projet d'ingénierie **Smart Building / Building-to-Grid (B2G)**.

> **DEMO MODE – SIMULATED DATA** — L'application n'est connectée à aucun capteur,
> compteur, onduleur, BMS, backend, base de données ou API. Aucune commande
> physique n'est envoyée. Les valeurs **réelles** proviennent exclusivement de
> fichiers CSV historiques intégrés au projet (branche `hanine`).

---

## 1. Ce que fait l'application

| Page | Contenu principal |
| --- | --- |
| **Vue Générale** | KPI (consommation, PV, import, surplus, autoconsommation, pointe), courbes consommation/PV, répartition par usage, sources d'énergie, profil horaire, bilan et diagramme de flux, alertes statistiques. |
| **Surveillance Énergétique** | Filtres dates / plage horaire / zones, hourly & daily, pointes, profil horaire, **comparaison entre bâtiments réels**, détection d'anomalies par score Z, journal filtrable et export CSV. |
| **Production Photovoltaïque** | Production réelle de la centrale n°1 (source 15 min, agrégée à l'heure), météo et irradiation, qualité des mesures, comparaison PV/consommation, répartition horaire. |
| **Batterie & Réseau** | Simulation A/B configurable (sans / avec batterie), SOC, charge/décharge, import/export réseau, contrôle de conservation de l'énergie, analyse économique estimative. |
| **Environnement & Équipements** | Météo réelle (température, vent, nébulosité, point de rosée, précipitations), ambiance intérieure simulée, inventaire des équipements et préparation MQTT/Modbus/BACnet. |
| **Données & Configuration** | Inventaire des 7 jeux réels, dimensions/colonnes/types/manquants/couverture/fréquence, import CSV/XLSX validé, export du scénario, paramètres de simulation et diagnostic système. |

### Guide de démonstration (5 minutes)

L'interface est volontairement épurée : une seule idée par page, un graphique principal
et peu de texte. Parcours conseillé pour une présentation :

1. **Vue Générale** — montrer les 6 KPI et la courbe consommation / production.
2. **Surveillance** — changer la plage de dates, montrer le journal et l'export CSV.
3. **Photovoltaïque** — expliquer le passage du pas 15 min au pas horaire.
4. **Batterie & Réseau** — modifier la capacité et comparer les scénarios A et B.
5. **Environnement** — montrer la différence entre météo réelle et capteurs simulés.
6. **Données & Configuration** — ouvrir un jeu réel, importer un CSV, sauvegarder la configuration.

---

## 2. Données sources (branche `hanine`)

Les fichiers suivants ont été repris tels quels de la branche `hanine` du dépôt
et placés dans `data/raw/` et `data/processed/` :

| Fichier | Origine | Contenu | Utilisation |
| --- | --- | --- | --- |
| `data/processed/electricity_office.csv` | ASHRAE Great Energy Predictor III | 180 076 lignes, 243 bâtiments, compteur électrique 0, 2016 | Consommation réelle (174 bâtiments éligibles) |
| `data/processed/solar_final.csv` | Centrale PV n°1 | 744 heures, 2020, agrégation de mesures 15 min | Production PV réelle + irradiation/températures |
| `data/raw/weather_train.csv` | ASHRAE | Météo horaire par site, 2016 | Température, vent, nébulosité, précipitations réelles |
| `data/raw/building_metadata (1).csv` | ASHRAE | Usage, surface, site, année | Sélection et métadonnées des bâtiments |
| `data/processed/smart_building.csv` | Hanine | Scénario aligné 744 h | Référence de validation (36 309 kWh / 27 232 kWh) |
| `data/raw/Plant_1_Generation_Data.csv` | Centrale PV | 15 min, 22 onduleurs | Traçabilité / nombre d'onduleurs |
| `data/raw/Plant_1_Weather_Sensor_Data.csv` | Centrale PV | 15 min | Traçabilité météo centrale |

**Bâtiment par défaut : #520** (site 3, 27 600 pi², 744 heures complètes, aucune
valeur nulle, moyenne 48,8 kWh/h). Il reproduit exactement le scénario préparé
par Hanine. Un sélecteur permet de choisir parmi les **174 bâtiments éligibles**.

### Alignement des installations

Les deux jeux ne décrivent **pas le même bâtiment** :

1. les horodatages PV 2020 sont projetés sur 2016 puis décalés de 2 jours
   (`date.replace(year=2016) − 2 jours`) ;
2. la production de la centrale est multipliée par un facteur afin de couvrir
   75 % de la consommation du bâtiment ASHRAE (paramètre modifiable) ;
3. les trois journées absentes des jeux sources sont conservées comme telles
   (aucune donnée n'est inventée).

Le bilan affiché est donc un **scénario modélisé**, pas une mesure effectuée sur
un site réel unique. L'interface l'indique sur chaque page.

Résultat de référence (bâtiment 520, couverture 75 %) :

| Indicateur | Valeur |
| --- | --- |
| Consommation réelle | 36 309,35 kWh |
| PV réel mis à l'échelle | 27 232,01 kWh |
| Import réseau calculé | 17 069,91 kWh |
| Surplus calculé | 7 992,58 kWh |
| Taux d'autoconsommation | 70,65 % |
| Taux d'autosuffisance | 52,99 % |

---

## 3. Installation et lancement

Prérequis : **Python 3.10+** (testé avec Python 3.12/3.13 sous Windows).

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

L'application s'ouvre sur <http://localhost:8501>.

Pour un serveur sans navigateur :

```bash
streamlit run app.py --server.headless true --server.port 8501
```

---

## 4. Architecture

```
SBEMS/
├── app.py                       # configuration de page, contexte, routage
├── requirements.txt
├── README.md
├── .streamlit/config.toml
├── assets/logo.png
├── data/
│   ├── data_loader.py           # lecture CSV robuste + cache Streamlit
│   ├── data_cleaning.py         # nettoyage, doublons, IQR, qualité
│   ├── data_processing.py       # alignement, scénario, zones, usages
│   ├── data_validation.py       # contrôles de cohérence et de saisie
│   ├── repository.py            # ScenarioContext et accès unique aux données
│   ├── mock_data.py             # constantes conservées (compatibilité)
│   ├── raw/                     # CSV réels ASHRAE et centrale PV
│   └── processed/               # jeux préparés par la branche hanine
├── services/
│   ├── energy_calculations.py   # KPI, bilans, ratios, anomalies Z-score
│   ├── battery_simulation.py    # dispatch A/B, rendements, conservation
│   └── economic_analysis.py     # coûts, économies, payback estimé
├── components/                  # UI réutilisable (inchangée dans l'esprit)
├── utils/                       # calculs historiques, formatage, thème, config
├── views/                       # les six pages
└── tests/                       # unittest (21 tests)
```

Le flux de données est le suivant :

```
CSV réels → data_loader → data_cleaning/validation → data_processing
          → repository.ScenarioContext → views → components (Plotly / HTML)
```

Les pages ne lisent jamais directement les fichiers. Pour brancher une base
temporelle ou un flux MQTT plus tard, seul `data/data_loader.py` doit changer.

---

## 5. Calculs implémentés

### Bilan simplifié (sans batterie)

```text
self_consumed = min(consommation, production_PV)
grid_import   = max(0, consommation − production_PV)
grid_export   = max(0, production_PV − consommation)
SCR           = self_consumed / production_PV × 100   # autoconsommation
SSR           = self_consumed / consommation × 100    # autosuffisance
```

Toutes les divisions sont protégées contre le dénominateur nul. Un import et un
export ne sont jamais comptés simultanément sur le même pas horaire.

### Simulation batterie (scénario B)

À chaque heure : le PV alimente la charge, le surplus charge la batterie puis
est exporté ; le déficit est couvert par la décharge puis par le réseau.

- capacité, SOC initial, SOC min/max, puissances de charge/décharge et
  rendements sont configurables ;
- l'énergie stockée est plafonnée par la capacité et bornée par le SOC ;
- l'énergie restituée est limitée par la puissance de décharge ;
- les pertes de conversion sont comptabilisées ;

Les deux équations vérifiées à chaque pas :

```text
PV        = direct + charge_prélevée + export
Consommation = direct + décharge_livrée + import
```

Le test `check_energy_conservation()` contrôle ces égalités.

### Anomalies

Méthode statistique simple **score Z** (moyenne / écart-type), sur les séries
horaire et journalière, avec un seuil par défaut de |z| ≥ 3. Il ne s'agit **pas**
d'un modèle d'apprentissage automatique.

### Économie

- coût net = import × prix d'achat − export × prix de revente ;
- économie annualisée = économie observée sur la période × 8760 / heures ;
- retour simple = investissement batterie / économie annualisée ;
-Maintenance et dégradation sont des hypothèses simples.

Tous les tarifs sont **configurables** et présentés comme des estimations, jamais
comme des tarifs vérifiés ou des économies mesurées.

---

## 6. Origine des valeurs affichées

| Catégorie | Exemples | Origine |
| --- | --- | --- |
| **REAL DATA** | Consommation ASHRAE, production centrale PV, température extérieure, vent, irradiation | CSV historiques réels |
| **MODELED SCENARIO** | Bilan combiné consommation/PV, import/surplus, ratio de couverture, répartition par zone et par usage | Calculs à partir des données réelles + hypothèses documentées |
| **SIMULATED DATA** | Batterie, SOC, coûts, économies, confort intérieur, humidité, occupation, éclairage, CVC, statuts IoT | Modèles locaux, aucun équipement connecté |

Chaque page affiche un bandeau de provenance et le badge
`DEMO MODE – SIMULATED DATA`.

---

## 7. Tests

```bash
python -m unittest discover -s tests -v
```

21 tests couvrent :

- division sûre, bilan réseau sans double comptage, SCR vs SSR, KPI ;
- agrégations journalières/horaires, détection d'anomalies et petits échantillons ;
- alignement 2020 → 2016, scénario de référence (744 h / 36 309 kWh / 27 232 kWh) ;
- conservation des zones et usages, validation d'un bilan corrompu ;
- nettoyage des doublons et valeurs négatives, bâtiments éligibles ;
- simulation batterie : conservation, limites SOC/puissance, rendements, capacité nulle ;
- analyse économique : retour simple et cas sans économie.

Vérification UI effectuée avec Playwright/Chrome : ouverture des six pages,
sélecteur de bâtiment, changement de période PV, modification de la capacité
batterie, exports CSV, import CSV validé, sauvegarde/réinitialisation de la
configuration, **0 erreur console**.

---

## 8. Limites

- Les trois journées absentes des jeux ASHRAE/PV ne sont pas interpolées : le
  scénario compte 744 heures sur une fenêtre calendaire de 816 heures.
- La répartition par zone et par usage final est une estimation : un seul
  compteur global est disponible.
- Les données de confort intérieur et d'occupation sont simulées.
- Aucune donnée à 15 minutes n'est affichée : la centrale est agrégée à l'heure,
  comme dans le jeu préparé par Hanine.
- Le tarif d'électricité, le coût de la batterie et le prix d'export sont des
  hypothèses saisies par l'utilisateur.
- Aucune persistanceBackend, authentification ou pilotage temps réel.

### Intégration future

1. Remplacer `data/data_loader.py` par un connecteur base temporelle / MQTT.
2. Connecter les compteurs et onduleurs via Modbus TCP ou BACnet/IP.
3. Persister la configuration et l'historique des alertes.
4. Ajouter authentification, rôles et journal d'audit avant tout pilotage réel.

---

*SBEMS v2.0.0 — données historiques réelles, scénario modélisé, batterie simulée.*
