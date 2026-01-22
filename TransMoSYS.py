import pandas as pd
from pathlib import Path
import yaml
from itertools import product
import os

print("Directorio de trabajo actual:", os.getcwd())

# ----------------------------
# CONFIG / INPUTS
# ----------------------------
DICT_PATH = '/Users/javiermonge/Desktop/TransMoSYS/dictionary_LV.yaml'
OG_CONFIG_PATH = '/Users/javiermonge/Desktop/TransMoSYS/config.yaml'
OUT_DIR = Path("data")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Read dictionary for translation
with open(DICT_PATH, 'r') as file:
    dictionary = yaml.safe_load(file)

countries = list(dictionary.keys())
updated_countries = [country[:-2] for country in countries]  # e.g. COLXX -> COL

# Read OSeMOSYS Global config
with open(OG_CONFIG_PATH, 'r') as file:
    og_data = yaml.safe_load(file)

dayparts_keys = og_data['dayparts'].keys()
seasons_keys = og_data['seasons'].keys()
combinations = [f"{season}{daypart}" for season, daypart in product(seasons_keys, dayparts_keys)]

countries_og = og_data['geographic_scope']
olade_countries = list(set(updated_countries) ^ set(countries_og))

startYear = og_data['startYear']
endYear = og_data['endYear']

# ----------------------------
# SpecifiedDemandProfile (FIX)
# ----------------------------
# Instead of writing inside loop (overwriting), collect and write once.
profiles_all = []

# ----------------------------
# Pre-load global CSVs once (safer pattern)
# ----------------------------
# Only load if files exist; otherwise create empty skeletons
def load_or_empty(path, cols):
    if Path(path).exists():
        return pd.read_csv(path)
    return pd.DataFrame(columns=cols)

df_cf = load_or_empty(OUT_DIR / "CapacityFactor.csv", ["REGION","TECHNOLOGY","TIMESLICE","YEAR","VALUE"])
df_ctau = load_or_empty(OUT_DIR / "CapacityToActivityUnit.csv", ["REGION","TECHNOLOGY","VALUE"])
df_cc = load_or_empty(OUT_DIR / "CapitalCost.csv", ["REGION","TECHNOLOGY","YEAR","VALUE"])
df_fc = load_or_empty(OUT_DIR / "FixedCost.csv", ["REGION","TECHNOLOGY","YEAR","VALUE"])
df_vc = load_or_empty(OUT_DIR / "VariableCost.csv", ["REGION","TECHNOLOGY","MODE_OF_OPERATION","YEAR","VALUE"])
df_ear = load_or_empty(OUT_DIR / "EmissionActivityRatio.csv", ["REGION","TECHNOLOGY","EMISSION","MODE_OF_OPERATION","YEAR","VALUE"])
df_rc = load_or_empty(OUT_DIR / "ResidualCapacity.csv", ["REGION","TECHNOLOGY","YEAR","VALUE"])
df_ol = load_or_empty(OUT_DIR / "OperationalLife.csv", ["REGION","TECHNOLOGY","VALUE"])
df_tamc = load_or_empty(OUT_DIR / "TotalAnnualMaxCapacity.csv", ["REGION","TECHNOLOGY","YEAR","VALUE"])


for country in dictionary.keys():
    print("Country:", country)

    code = Path(country[:3])  # folder name like "COL"

    # ============================================================
    # SpecifiedDemandProfile (generate uniform profile from YAML)
    # ============================================================
    specified_demand = dictionary[country]['SpecifiedDemand']  # list
    rows = []

    for sector in specified_demand:
        # Build FUEL code
        new_fuel_code = sector + country
        if sector.endswith('ELC'):
            new_fuel_code = sector + country + '02'

        for year in range(startYear, endYear + 1):
            for ts in combinations:
                rows.append({
                    "REGION": "GLOBAL",
                    "FUEL": new_fuel_code,
                    "TIMESLICE": ts,
                    "YEAR": year,
                    "VALUE": 1 / len(combinations)
                })

    df_profile_country = pd.DataFrame(rows).drop_duplicates()
    profiles_all.append(df_profile_country)

    # ============================================================
    # CapacityFactor (Annual -> timeslices replication)
    # ============================================================
    df_country = pd.read_csv(code / 'CapacityFactor.csv')
    PowerPlants = dictionary[country]['PowerPlants']

    for powerplant in PowerPlants:
        term = PowerPlants[powerplant] or []
        filtered_df = df_country[df_country['TECHNOLOGY'].isin(term)].copy()
        if filtered_df.empty:
            continue

        filtered_df.loc[:, 'REGION'] = 'GLOBAL'
        filtered_df.loc[:, 'TECHNOLOGY'] = "PWR" + powerplant + country + "01"
        filtered_df = filtered_df.groupby(['REGION', 'TECHNOLOGY', 'YEAR'])['VALUE'].mean().reset_index()

        # replicate across timeslices
        temp = []
        for _, row in filtered_df.iterrows():
            for ts in combinations:
                temp.append({
                    "REGION": row["REGION"],
                    "TECHNOLOGY": row["TECHNOLOGY"],
                    "YEAR": row["YEAR"],
                    "VALUE": row["VALUE"],
                    "TIMESLICE": ts
                })
        final_df = pd.DataFrame(temp).dropna()

        df_cf = pd.concat([df_cf, final_df], ignore_index=True)
        df_cf = df_cf.drop_duplicates(subset=['REGION','TECHNOLOGY','TIMESLICE','YEAR'], keep='last')
        df_cf = df_cf[(df_cf['YEAR'] >= startYear) & (df_cf['YEAR'] <= endYear)]

    # ============================================================
    # CapacityToActivityUnit
    # ============================================================
    df_country = pd.read_csv(code / 'CapacityToActivityUnit.csv')
    SupplyTechs = dictionary[country]['SupplyTechs']
    FinalTechs = dictionary[country]['FinalTechs']

    for powerplant in PowerPlants:
        term = PowerPlants[powerplant] or []
        filtered_df = df_country[df_country['TECHNOLOGY'].isin(term)].copy()
        if filtered_df.empty:
            continue
        filtered_df.loc[:, 'REGION'] = 'GLOBAL'
        filtered_df.loc[:, 'TECHNOLOGY'] = "PWR" + powerplant + country + "01"
        filtered_df = filtered_df.groupby(['REGION','TECHNOLOGY'])['VALUE'].mean().reset_index()
        df_ctau = pd.concat([df_ctau, filtered_df], ignore_index=True)

    for supplytech in SupplyTechs:
        term = SupplyTechs[supplytech] or []
        filtered_df = df_country[df_country['TECHNOLOGY'].isin(term)].copy()
        if filtered_df.empty:
            continue
        filtered_df.loc[:, 'REGION'] = 'GLOBAL'
        filtered_df.loc[:, 'TECHNOLOGY'] = "SUP" + supplytech + country
        filtered_df = filtered_df.groupby(['REGION','TECHNOLOGY'])['VALUE'].mean().reset_index()
        df_ctau = pd.concat([df_ctau, filtered_df], ignore_index=True)

    for finaltech in FinalTechs:
        term = FinalTechs[finaltech] or []
        filtered_df = df_country[df_country['TECHNOLOGY'].isin(term)].copy()
        if filtered_df.empty:
            continue
        filtered_df.loc[:, 'REGION'] = 'GLOBAL'
        tech = "DEM" + finaltech + country
        if finaltech.endswith('ELC'):
            tech = "DEM" + finaltech + country + '02'
        filtered_df.loc[:, 'TECHNOLOGY'] = tech
        filtered_df = filtered_df.groupby(['REGION','TECHNOLOGY'])['VALUE'].mean().reset_index()
        df_ctau = pd.concat([df_ctau, filtered_df], ignore_index=True)

    df_ctau = df_ctau.drop_duplicates(subset=['REGION','TECHNOLOGY'], keep='last')

    # ============================================================
    # CapitalCost
    # ============================================================
    df_country = pd.read_csv(code / 'CapitalCost.csv')

    for powerplant in PowerPlants:
        term = PowerPlants[powerplant] or []
        filtered_df = df_country[df_country['TECHNOLOGY'].isin(term)].copy()
        if filtered_df.empty:
            continue
        filtered_df.loc[:, 'REGION'] = 'GLOBAL'
        filtered_df.loc[:, 'TECHNOLOGY'] = "PWR" + powerplant + country + "01"
        filtered_df = filtered_df.groupby(['REGION','TECHNOLOGY','YEAR'])['VALUE'].sum().reset_index()
        df_cc = pd.concat([df_cc, filtered_df], ignore_index=True)

    for supplytech in SupplyTechs:
        term = SupplyTechs[supplytech] or []
        filtered_df = df_country[df_country['TECHNOLOGY'].isin(term)].copy()
        if filtered_df.empty:
            continue
        filtered_df.loc[:, 'REGION'] = 'GLOBAL'
        filtered_df.loc[:, 'TECHNOLOGY'] = "SUP" + supplytech + country
        filtered_df = filtered_df.groupby(['REGION','TECHNOLOGY','YEAR'])['VALUE'].sum().reset_index()
        df_cc = pd.concat([df_cc, filtered_df], ignore_index=True)

    for finaltech in FinalTechs:
        term = FinalTechs[finaltech] or []
        filtered_df = df_country[df_country['TECHNOLOGY'].isin(term)].copy()
        if filtered_df.empty:
            continue
        filtered_df.loc[:, 'REGION'] = 'GLOBAL'
        tech = "DEM" + finaltech + country
        if finaltech.endswith('ELC'):
            tech = "DEM" + finaltech + country + '02'
        filtered_df.loc[:, 'TECHNOLOGY'] = tech
        filtered_df = filtered_df.groupby(['REGION','TECHNOLOGY','YEAR'])['VALUE'].sum().reset_index()
        df_cc = pd.concat([df_cc, filtered_df], ignore_index=True)

    df_cc = df_cc.drop_duplicates(subset=['REGION','TECHNOLOGY','YEAR'], keep='last')
    df_cc = df_cc[(df_cc['YEAR'] >= startYear) & (df_cc['YEAR'] <= endYear)]

    # ============================================================
    # FixedCost
    # ============================================================
    df_country = pd.read_csv(code / 'FixedCost.csv')

    for powerplant in PowerPlants:
        term = PowerPlants[powerplant] or []
        filtered_df = df_country[df_country['TECHNOLOGY'].isin(term)].copy()
        if filtered_df.empty:
            continue
        filtered_df.loc[:, 'REGION'] = 'GLOBAL'
        filtered_df.loc[:, 'TECHNOLOGY'] = "PWR" + powerplant + country + "01"
        filtered_df = filtered_df.groupby(['REGION','TECHNOLOGY','YEAR'])['VALUE'].sum().reset_index()
        df_fc = pd.concat([df_fc, filtered_df], ignore_index=True)

    for supplytech in SupplyTechs:
        term = SupplyTechs[supplytech] or []
        filtered_df = df_country[df_country['TECHNOLOGY'].isin(term)].copy()
        if filtered_df.empty:
            continue
        filtered_df.loc[:, 'REGION'] = 'GLOBAL'
        filtered_df.loc[:, 'TECHNOLOGY'] = "SUP" + supplytech + country
        filtered_df = filtered_df.groupby(['REGION','TECHNOLOGY','YEAR'])['VALUE'].sum().reset_index()
        df_fc = pd.concat([df_fc, filtered_df], ignore_index=True)

    for finaltech in FinalTechs:
        term = FinalTechs[finaltech] or []
        filtered_df = df_country[df_country['TECHNOLOGY'].isin(term)].copy()
        if filtered_df.empty:
            continue
        filtered_df.loc[:, 'REGION'] = 'GLOBAL'
        tech = "DEM" + finaltech + country
        if finaltech.endswith('ELC'):
            tech = "DEM" + finaltech + country + '02'
        filtered_df.loc[:, 'TECHNOLOGY'] = tech
        filtered_df = filtered_df.groupby(['REGION','TECHNOLOGY','YEAR'])['VALUE'].sum().reset_index()
        df_fc = pd.concat([df_fc, filtered_df], ignore_index=True)

    df_fc = df_fc.drop_duplicates(subset=['REGION','TECHNOLOGY','YEAR'], keep='last')
    df_fc = df_fc[(df_fc['YEAR'] >= startYear) & (df_fc['YEAR'] <= endYear)]

    # ============================================================
    # VariableCost
    # ============================================================
    df_country = pd.read_csv(code / 'VariableCost.csv')

    def expand_modes(df):
        df = df.copy()
        df.loc[:, 'MODE_OF_OPERATION'] = 1
        df2 = df.copy()
        df2.loc[:, 'MODE_OF_OPERATION'] = 2
        return pd.concat([df, df2], ignore_index=True)

    for powerplant in PowerPlants:
        term = PowerPlants[powerplant] or []
        filtered_df = df_country[df_country['TECHNOLOGY'].isin(term)].copy()
        if filtered_df.empty:
            continue
        filtered_df.loc[:, 'REGION'] = 'GLOBAL'
        filtered_df.loc[:, 'TECHNOLOGY'] = "PWR" + powerplant + country + "01"
        filtered_df = expand_modes(filtered_df)
        filtered_df = filtered_df.groupby(['REGION','TECHNOLOGY','MODE_OF_OPERATION','YEAR'])['VALUE'].sum().reset_index()
        df_vc = pd.concat([df_vc, filtered_df], ignore_index=True)

    for supplytech in SupplyTechs:
        term = SupplyTechs[supplytech] or []
        filtered_df = df_country[df_country['TECHNOLOGY'].isin(term)].copy()
        if filtered_df.empty:
            continue
        filtered_df.loc[:, 'REGION'] = 'GLOBAL'
        filtered_df.loc[:, 'TECHNOLOGY'] = "SUP" + supplytech + country
        filtered_df = expand_modes(filtered_df)
        filtered_df = filtered_df.groupby(['REGION','TECHNOLOGY','MODE_OF_OPERATION','YEAR'])['VALUE'].sum().reset_index()
        df_vc = pd.concat([df_vc, filtered_df], ignore_index=True)

    for finaltech in FinalTechs:
        term = FinalTechs[finaltech] or []
        filtered_df = df_country[df_country['TECHNOLOGY'].isin(term)].copy()
        if filtered_df.empty:
            continue
        filtered_df.loc[:, 'REGION'] = 'GLOBAL'
        tech = "DEM" + finaltech + country
        if finaltech.endswith('ELC'):
            tech = "DEM" + finaltech + country + '02'
        filtered_df.loc[:, 'TECHNOLOGY'] = tech
        filtered_df = expand_modes(filtered_df)
        filtered_df = filtered_df.groupby(['REGION','TECHNOLOGY','MODE_OF_OPERATION','YEAR'])['VALUE'].sum().reset_index()
        df_vc = pd.concat([df_vc, filtered_df], ignore_index=True)

    df_vc = df_vc.drop_duplicates(subset=['REGION','TECHNOLOGY','MODE_OF_OPERATION','YEAR'], keep='last')
    df_vc = df_vc[(df_vc['YEAR'] >= startYear) & (df_vc['YEAR'] <= endYear)]

    # ============================================================
    # EmissionActivityRatio
    # ============================================================
    df_country = pd.read_csv(code / 'EmissionActivityRatio.csv')

    def add_emissions(df, tech_name):
        df = df.copy()
        df.loc[:, 'REGION'] = 'GLOBAL'
        df.loc[:, 'EMISSION'] = 'CO2'
        df.loc[:, 'TECHNOLOGY'] = tech_name
        df = expand_modes(df)
        df = df.groupby(['REGION','TECHNOLOGY','EMISSION','MODE_OF_OPERATION','YEAR'])['VALUE'].mean().reset_index()
        return df

    for powerplant in PowerPlants:
        term = PowerPlants[powerplant] or []
        tmp = df_country[df_country['TECHNOLOGY'].isin(term)]
        if tmp.empty:
            continue
        df_ear = pd.concat([df_ear, add_emissions(tmp, "PWR" + powerplant + country + "01")], ignore_index=True)

    for supplytech in SupplyTechs:
        term = SupplyTechs[supplytech] or []
        tmp = df_country[df_country['TECHNOLOGY'].isin(term)]
        if tmp.empty:
            continue
        df_ear = pd.concat([df_ear, add_emissions(tmp, "SUP" + supplytech + country)], ignore_index=True)

    for finaltech in FinalTechs:
        term = FinalTechs[finaltech] or []
        tmp = df_country[df_country['TECHNOLOGY'].isin(term)]
        if tmp.empty:
            continue
        tech = "DEM" + finaltech + country
        if finaltech.endswith('ELC'):
            tech = "DEM" + finaltech + country + '02'
        df_ear = pd.concat([df_ear, add_emissions(tmp, tech)], ignore_index=True)

    df_ear = df_ear.drop_duplicates(subset=['REGION','TECHNOLOGY','EMISSION','MODE_OF_OPERATION','YEAR'], keep='last')
    df_ear = df_ear[(df_ear['YEAR'] >= startYear) & (df_ear['YEAR'] <= endYear)]

    # ============================================================
    # ResidualCapacity
    # ============================================================
    df_country = pd.read_csv(code / 'ResidualCapacity.csv')

    def add_simple_year_sum(df, tech_name):
        df = df.copy()
        df.loc[:, 'REGION'] = 'GLOBAL'
        df.loc[:, 'TECHNOLOGY'] = tech_name
        df = df.groupby(['REGION','TECHNOLOGY','YEAR'])['VALUE'].sum().reset_index()
        return df

    for powerplant in PowerPlants:
        term = PowerPlants[powerplant] or []
        tmp = df_country[df_country['TECHNOLOGY'].isin(term)]
        if tmp.empty:
            continue
        df_rc = pd.concat([df_rc, add_simple_year_sum(tmp, "PWR" + powerplant + country + "01")], ignore_index=True)

    for supplytech in SupplyTechs:
        term = SupplyTechs[supplytech] or []
        tmp = df_country[df_country['TECHNOLOGY'].isin(term)]
        if tmp.empty:
            continue
        df_rc = pd.concat([df_rc, add_simple_year_sum(tmp, "SUP" + supplytech + country)], ignore_index=True)

    for finaltech in FinalTechs:
        term = FinalTechs[finaltech] or []
        tmp = df_country[df_country['TECHNOLOGY'].isin(term)]
        if tmp.empty:
            continue
        tech = "DEM" + finaltech + country
        if finaltech.endswith('ELC'):
            tech = "DEM" + finaltech + country + '02'
        df_rc = pd.concat([df_rc, add_simple_year_sum(tmp, tech)], ignore_index=True)

    df_rc = df_rc.drop_duplicates(subset=['REGION','TECHNOLOGY','YEAR'], keep='last')
    df_rc = df_rc[(df_rc['YEAR'] >= startYear) & (df_rc['YEAR'] <= endYear)]

    # ============================================================
    # OperationalLife
    # ============================================================
    df_country = pd.read_csv(code / 'OperationalLife.csv')

    def add_simple_mean(df, tech_name):
        df = df.copy()
        df.loc[:, 'REGION'] = 'GLOBAL'
        df.loc[:, 'TECHNOLOGY'] = tech_name
        df = df.groupby(['REGION','TECHNOLOGY'])['VALUE'].mean().reset_index()
        return df

    for powerplant in PowerPlants:
        term = PowerPlants[powerplant] or []
        tmp = df_country[df_country['TECHNOLOGY'].isin(term)]
        if tmp.empty:
            continue
        df_ol = pd.concat([df_ol, add_simple_mean(tmp, "PWR" + powerplant + country + "01")], ignore_index=True)

    for supplytech in SupplyTechs:
        term = SupplyTechs[supplytech] or []
        tmp = df_country[df_country['TECHNOLOGY'].isin(term)]
        if tmp.empty:
            continue
        df_ol = pd.concat([df_ol, add_simple_mean(tmp, "SUP" + supplytech + country)], ignore_index=True)

    for finaltech in FinalTechs:
        term = FinalTechs[finaltech] or []
        tmp = df_country[df_country['TECHNOLOGY'].isin(term)]
        if tmp.empty:
            continue
        tech = "DEM" + finaltech + country
        if finaltech.endswith('ELC'):
            tech = "DEM" + finaltech + country + '02'
        df_ol = pd.concat([df_ol, add_simple_mean(tmp, tech)], ignore_index=True)

    df_ol = df_ol.drop_duplicates(subset=['REGION','TECHNOLOGY'], keep='last')

    # ============================================================
    # TotalAnnualMaxCapacity
    # ============================================================
    df_country = pd.read_csv(code / 'TotalAnnualMaxCapacity.csv')

    for powerplant in PowerPlants:
        term = PowerPlants[powerplant] or []
        tmp = df_country[df_country['TECHNOLOGY'].isin(term)]
        if tmp.empty:
            continue
        df_tamc = pd.concat([df_tamc, add_simple_year_sum(tmp, "PWR" + powerplant + country + "01")], ignore_index=True)

    for supplytech in SupplyTechs:
        term = SupplyTechs[supplytech] or []
        tmp = df_country[df_country['TECHNOLOGY'].isin(term)]
        if tmp.empty:
            continue
        df_tamc = pd.concat([df_tamc, add_simple_year_sum(tmp, "SUP" + supplytech + country)], ignore_index=True)

    for finaltech in FinalTechs:
        term = FinalTechs[finaltech] or []
        tmp = df_country[df_country['TECHNOLOGY'].isin(term)]
        if tmp.empty:
            continue
        tech = "DEM" + finaltech + country
        if finaltech.endswith('ELC'):
            tech = "DEM" + finaltech + country + '02'
        df_tamc = pd.concat([df_tamc, add_simple_year_sum(tmp, tech)], ignore_index=True)

    df_tamc = df_tamc.drop_duplicates(subset=['REGION','TECHNOLOGY','YEAR'], keep='last')
    df_tamc = df_tamc[(df_tamc['YEAR'] >= startYear) & (df_tamc['YEAR'] <= endYear)]


# ----------------------------
# WRITE OUTPUTS (once, after loop)
# ----------------------------
# SpecifiedDemandProfile (ALL countries)
df_sap = pd.concat(profiles_all, ignore_index=True).drop_duplicates()
df_sap.to_csv(OUT_DIR / 'SpecifiedDemandProfile.csv', index=False)

# Write other global files
df_cf.to_csv(OUT_DIR / "CapacityFactor.csv", index=False)
df_ctau.to_csv(OUT_DIR / "CapacityToActivityUnit.csv", index=False)
df_cc.to_csv(OUT_DIR / "CapitalCost.csv", index=False)
df_fc.to_csv(OUT_DIR / "FixedCost.csv", index=False)
df_vc.to_csv(OUT_DIR / "VariableCost.csv", index=False)
df_ear.to_csv(OUT_DIR / "EmissionActivityRatio.csv", index=False)
df_rc.to_csv(OUT_DIR / "ResidualCapacity.csv", index=False)
df_ol.to_csv(OUT_DIR / "OperationalLife.csv", index=False)
df_tamc.to_csv(OUT_DIR / "TotalAnnualMaxCapacity.csv", index=False)

print("Done.")
print(f"SpecifiedDemandProfile rows: {len(df_sap):,} | fuels: {df_sap['FUEL'].nunique()} | sample regions: {df_sap['REGION'].unique()}")
