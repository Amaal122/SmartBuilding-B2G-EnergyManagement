# SBEMS — Smart Building Energy Management System

Démonstrateur **front-end** de supervision énergétique d'un bâtiment tertiaire,
développé avec **Streamlit**, **Pandas**, **NumPy** et **Plotly**.

> **DEMO MODE – SIMULATED DATA**
>
> Toutes les mesures, alertes, puissances, températures, occupations et états
> d'équipement sont **générés localement et simulés**. Aucun capteur, compteur,
> onduleur, BMS, passerelle IoT, base de données ou API n'est connecté.
> Aucune commande physique n'est envoyée depuis l'interface.

---

## 1. Aperçu

L'application propose six pages en français, accessibles depuis la barre latérale :

| Page | Contenu |
| --- | --- |
| **Vue Générale** | KPI du jour, équilibre énergétique, production solaire, autoconsommation, alertes de démonstration, coûts indicatifs. |
| **Surveillance Énergétique** | Filtres interactifs (dates, plage horaire, zones), consommation horaire, journal des mesures, analyse des pointes, export CSV. |
| **Production Photovoltaïque** | Périodes 24 h / 7 j / 14 j, puissance solaire, production journalière, autoconsommation, répartition horaire, fiche de l'installation. |
| **Batterie & Réseau** | État de charge (SOC), cycles illustratifs, import/export réseau, surplus PV, Sankey du bilan, synthèse chiffrée. |
| **Environnement & Équipements** | Températures, humidité, occupation, éclairage, CVC, inventaire des équipements, protocoles d'intégration futurs. |
| **Données & Configuration** | Aperçu des jeux de données, imports CSV (visuels), paramètres du bâtiment et tarif, diagnostic système. |

Le bandeau **DEMO MODE – SIMULATED DATA** et les mentions de pied de page
rappellent ce cadre à chaque écran.

---

## 2. Installation et lancement

Prérequis : **Python 3.10+** (testé avec Python 3.13 sous Windows).

```bash
# 1. Créer et activer un environnement virtuel (recommandé)
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Lancer l'application
streamlit run app.py
```

L'application s'ouvre par défaut sur <http://localhost:8501>.

Pour un lancement sans navigateur (CI, serveur distant) :

```bash
streamlit run app.py --server.headless true --server.port 8501
```

---

## 3. Structure du projet

```
Smart-Building/
├── app.py                      # Point d'entrée, configuration de page et routage
├── requirements.txt
├── README.md
├── .streamlit/
│   └── config.toml             # Thème Streamlit (couleurs, typographie)
├── assets/
│   └── logo.png                # Logo SBEMS (généré localement)
├── components/
│   ├── charts.py               # Figures Plotly et rendu commun
│   ├── energy_flow.py          # Diagramme de flux SVG
│   ├── header.py               # En-tête, badge démo, horloge, bâtiment
│   ├── kpi_cards.py            # Cartes KPI et sparklines
│   ├── sidebar.py              # Navigation, statut de démonstration
│   └── ui.py                   # Alertes, capteurs, tableaux, panneaux, footer
├── data/
│   └── mock_data.py            # Génération déterministe des données simulées
├── utils/
│   ├── calculations.py         # Fenêtres temporelles, KPI, alertes, seuils
│   ├── config.py               # Configuration de session et devises
│   ├── formatting.py           # Formats français (nombres, dates, énergie)
│   ├── icons.py                # Bibliothèque d'icônes SVG
│   └── theme.py                # Feuille de style CSS du design system
└── views/
    ├── overview.py
    ├── energy_monitoring.py
    ├── solar_production.py
    ├── battery_grid.py
    ├── environment.py
    └── settings.py
```

La navigation utilise un `st.radio` personnalisé dans `components/sidebar.py`
plutôt que le menu multipage natif de Streamlit, afin de contrôler entièrement
l'apparence de la barre latérale.

---

## 4. Données simulées

`data/mock_data.py` génère **14 jours de mesures horaires** (336 lignes) avec une
graine fixe (`SEED = 20261119`). Les séries restent donc identiques d'un
rafraîchissement à l'autre.

Caractéristiques principales :

- profils de consommation réalistes (activité bureaux, HVAC, éclairage) ;
- production PV suivant un profil solaire simplifié (lever ≈ 7 h, coucher ≈ 18 h,
  nébulosité scénarisée) ;
- température intérieure/extérieure, humidité, occupation et éclairage ;
- état de charge batterie (SOC) et cycles de charge/décharge **illustratifs** ;
- répartition par zone (RDC, étages, toiture) et par usage final.

### Équilibre énergétique simplifié

```text
grid_import = max(0, consommation − production_PV)
surplus     = max(0, production_PV − consommation)
```

Une même énergie n'est jamais comptée simultanément en import et en export.
**Le dispatch batterie est exclu de ce bilan** : la charge et la décharge sont
affichées à titre pédagogique et ne modifient pas le solde réseau.

### Points d'accès aux données

Les vues ne consomment que trois fonctions de `data/mock_data.py` :

- `get_energy_data()` — série horaire principale ;
- `get_zone_data()` — mesures par zone du bâtiment ;
- `get_end_use_data()` — répartition par usage final.

Pour brancher un backend réel (CSV ASHRAE, base de données, MQTT, Modbus TCP,
BACnet/IP), il suffit de remplacer ces implémentations : les pages et les
composants restent inchangés.

---

## 5. Fonctionnalités interactives

- **Filtres de la page Surveillance** : plage de dates (format `JJ/MM/AAAA`),
  plage horaire, sélection multiple de zones. Les KPI, graphiques et le journal
  se recalculent immédiatement.
- **Périodes 24 h / 7 j / 14 j** sur la page photovoltaïque, avec comparaison à
  la période précédente.
- **Export CSV** du journal des mesures filtré (encodage UTF-8 avec BOM pour
  Excel).
- **Formulaire de configuration** : nom du bâtiment, localisation, puissance
  PV installée, capacité batterie, devise et coût du kWh. Les valeurs sont
  conservées pendant la session uniquement ; le bouton **Réinitialiser**
  restaure les valeurs par défaut.
- **Imports CSV** : contrôles visuels de préparation, sans analyse ni
  persistance des fichiers.

---

## 6. Limites de la version

- Aucune persistance : la configuration et les imports disparaissent au
  redémarrage.
- Aucune authentification ni gestion multi-utilisateurs.
- Les alertes sont des constats de surveillance, jamais des actions de
  pilotage.
- Les statuts, seuils (pointe 68 kW, SOC bas 30 %/20 %, etc.) et tarifs sont
  des hypothèses de démonstration non contractuelles.
- Les fichiers CSV importés ne sont ni lus ni validés.

### Pistes d'intégration backend

1. Remplacer `data/mock_data.py` par un connecteur CSV ASHRAE ou une base
   temporelle (TimescaleDB, InfluxDB, PostgreSQL).
2. Ajouter un client MQTT pour les mesures temps réel et un cache de session.
3. Exposer les mêmes structures de données pour Modbus TCP / BACnet/IP.
4. Persister la configuration et l'historique des alertes.
5. Ajouter authentification, rôles et journal d'audit avant tout pilotage réel.

---

## 7. Vérifications rapides

```bash
python -m compileall -q app.py components data utils views
streamlit run app.py
```

Parcours de contrôle conseillé :

1. Vue Générale : KPI, cinq alertes, diagramme de flux, coût estimé.
2. Surveillance : modifier la plage horaire et retirer une zone.
3. Photovoltaïque : basculer entre 24 heures, 7 jours et 14 jours.
4. Batterie & Réseau : vérifier la cohérence import/surplus et la synthèse.
5. Environnement : table d'inventaire et équipement hors ligne.
6. Données & Configuration : enregistrer un nouveau nom, naviguer, puis
   réinitialiser.

---

## 8. Stack technique

- [Streamlit](https://streamlit.io/) ≥ 1.40
- [Pandas](https://pandas.pydata.org/) ≥ 2.1
- [NumPy](https://numpy.org/) ≥ 1.26
- [Plotly](https://plotly.com/python/) ≥ 5.20

Interface, textes et formats : **français**. Les acronymes métier (BEMS, B2G,
HVAC, PV, SOC, MQTT, Modbus, BACnet) sont conservés.

---

*SBEMS v1.0.0 — démonstrateur front-end. Toutes les valeurs affichées sont
simulées.*
