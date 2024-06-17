import pandas as pd
from pathlib import Path
import yaml
from itertools import product
## Read dictionary for translation
with open('dictionary.yaml', 'r') as file:
    dictionary = yaml.safe_load(file)
# Extract list of countries
countries = list(dictionary.keys())
# Delete the last two characters from each value
updated_countries = [country[:-2] for country in countries]
# Continue with the rest of the code
with open('configLAC.yaml', 'r') as file: #Config File of OSeMOSYS Global
    og_data = yaml.safe_load(file)
dayparts_keys = og_data['dayparts'].keys()
seasons_keys = og_data['seasons'].keys()
combinations = [f"{season}{daypart}" for season, daypart in product(seasons_keys, dayparts_keys)]
countries_og = og_data['geographic_scope']
olade_countries = list(set(updated_countries) ^ set(countries_og))
startYear=og_data['startYear']
endYear=og_data['endYear']
df_sad = pd.DataFrame(columns=['REGION', 'FUEL', 'YEAR', 'VALUE'])
df_sad.to_csv('data/SpecifiedAnnualDemand.csv', index=False)
df_sap = pd.DataFrame(columns=['REGION', 'FUEL', 'TIMESLICE', 'YEAR', 'VALUE'])
df_sap.to_csv('data/SpecifiedDemandProfile.csv', index=False)

#SpecifiedAnnualDemand
for country in dictionary.keys():
    code = country[:3]
    code = Path(code)
    #SpecifiedAnnualDemand
    df_country = pd.read_csv(code / 'SpecifiedAnnualDemand.csv')
    specified_demand = dictionary[country]['SpecifiedDemand']
    for sector in specified_demand:
        term = specified_demand[sector]
        filtered_df = df_country[df_country['FUEL'].isin(term)]
        filtered_df.loc[:, 'REGION'] = 'GLOBAL'
        if sector[-3:] == 'ELC':
            filtered_df.loc[:, 'FUEL'] = sector + country + '02'
        else:
            filtered_df.loc[:, 'FUEL'] = sector + country
        filtered_df = filtered_df.groupby(['REGION', 'FUEL', 'YEAR'])['VALUE'].mean().reset_index()
        filtered_df = filtered_df[(filtered_df['YEAR'] >= startYear) & (filtered_df['YEAR'] <= endYear)]
        filtered_df.to_csv('data/SpecifiedAnnualDemand.csv', header=False, index=False, mode='a')
    print("SpecifiedAnnualDemand for "+str(code)+" updated")
    #SpecifiedDemandProfile
    df_country = pd.read_csv(code / 'SpecifiedDemandProfile.csv')
    specified_demand = dictionary[country]['SpecifiedDemand']
    for sector in specified_demand:
        term = specified_demand[sector]
        term = str(term)
        term_list = term.split(',')[0].strip("['']")
        filtered_df = df_country[df_country['FUEL'].isin([term_list])]
        filtered_df.loc[:, 'REGION'] = 'GLOBAL'
        if sector[-3:] == 'ELC':
            filtered_df.loc[:, 'FUEL'] = sector + country + '02'
        else:
            filtered_df.loc[:, 'FUEL'] = sector + country
        filtered_df = filtered_df.groupby(['REGION', 'FUEL', 'YEAR'])['VALUE'].mean().reset_index()
        filtered_df.loc[:, 'VALUE'] = 1/len(combinations)
        filtered_df = filtered_df[(filtered_df['YEAR'] >= startYear) & (filtered_df['YEAR'] <= endYear)]
        final_df = pd.DataFrame(columns=['REGION', 'FUEL', 'TIMESLICE','YEAR', 'VALUE'])
        # Iterate over each row in filtered_df
        for idx, row in filtered_df.iterrows():
            # For each row, iterate over each combination and create a new row
            for idx, row in filtered_df.iterrows():
                # For each row, create a DataFrame with repeated rows for each item in combinations
                temp_df = pd.DataFrame({
                    'REGION': [row['REGION']] * len(combinations),
                    'FUEL': [row['FUEL']] * len(combinations),
                    'TIMESLICE': combinations,
                    'YEAR': [row['YEAR']] * len(combinations),
                    'VALUE': [row['VALUE']] * len(combinations),
                    })
                # Concatenate temp_df with final_df
                if final_df.empty:
                    final_df = temp_df
                final_df = pd.concat([final_df, temp_df], ignore_index=True)
            final_df = final_df.dropna()
        final_df = final_df.drop_duplicates()
        final_df.to_csv('data/SpecifiedDemandProfile.csv', header=False, index=False, mode='a')
    #CapacityFactor (Annual Resolution)
    df_country = pd.read_csv(code / 'CapacityFactor.csv')
    PowerPlants= dictionary[country]['PowerPlants'] 
    for powerplant in PowerPlants:
        term = PowerPlants[powerplant]
        # Filter technologies with the specified term
        filtered_df = df_country[df_country['TECHNOLOGY'].isin(term)]
        filtered_df.loc[:, 'REGION'] = 'GLOBAL'
        #Changed to match the format of OSeMOSYS Global
        filtered_df.loc[:, 'TECHNOLOGY'] = "PWR" + powerplant + country + "01"
        # Find the mean for values in the same year
        filtered_df = filtered_df.groupby(['REGION', 'TECHNOLOGY','YEAR'])['VALUE'].mean().reset_index()
        final_df = pd.DataFrame(columns=['REGION', 'TECHNOLOGY', 'YEAR', 'VALUE', 'TIMESLICE'])
        # Iterate over each row in filtered_df
        for idx, row in filtered_df.iterrows():
            # For each row, iterate over each combination and create a new row
            for idx, row in filtered_df.iterrows():
                # For each row, create a DataFrame with repeated rows for each item in combinations
                temp_df = pd.DataFrame({
                    'REGION': [row['REGION']] * len(combinations),
                    'TECHNOLOGY': [row['TECHNOLOGY']] * len(combinations),
                    'YEAR': [row['YEAR']] * len(combinations),
                    'VALUE': [row['VALUE']] * len(combinations),
                    'TIMESLICE': combinations
                    })
                # Concatenate temp_df with final_df
                if final_df.empty:
                    final_df = temp_df
                final_df = pd.concat([final_df, temp_df], ignore_index=True)
            final_df = final_df.dropna()
        # Read OSeMOSYS Global CapacityFactor.csv
        df_cf = pd.read_csv('data/CapacityFactor.csv')
        df_cf = pd.concat([df_cf, final_df]).drop_duplicates(subset=['REGION', 'TECHNOLOGY','TIMESLICE', 'YEAR'], keep='last')
        df_cf = df_cf[(df_cf['YEAR'] >= startYear) & (df_cf['YEAR'] <= endYear)]
        # Save dataframe to CapacityFactor.csv
        df_cf.to_csv('data/CapacityFactor.csv', index=False)
    #CapacityToActivityUnit
    df_country = pd.read_csv(code / 'CapacityToActivityUnit.csv')
    PowerPlants= dictionary[country]['PowerPlants']
    SupplyTechs= dictionary[country]['SupplyTechs']
    for powerplant in PowerPlants:
        term = PowerPlants[powerplant]
        filtered_df = df_country[df_country['TECHNOLOGY'].isin(term)]
        filtered_df.loc[:, 'REGION'] = 'GLOBAL'
        filtered_df.loc[:, 'TECHNOLOGY'] = "PWR" + powerplant + country + "01"
        filtered_df = filtered_df.groupby(['REGION', 'TECHNOLOGY'])['VALUE'].mean().reset_index()
        df_ctau = pd.read_csv('data/CapacityToActivityUnit.csv')
        df_ctau = pd.concat([df_ctau, filtered_df]).drop_duplicates(subset=['REGION', 'TECHNOLOGY'], keep='last')
        df_ctau.to_csv('data/CapacityToActivityUnit.csv', index=False)
    for supplytech in SupplyTechs:
        term = SupplyTechs[supplytech]
        filtered_df = df_country[df_country['TECHNOLOGY'].isin(term)]
        filtered_df.loc[:, 'REGION'] = 'GLOBAL'
        filtered_df.loc[:, 'TECHNOLOGY'] = "SUP" + supplytech + country
        filtered_df = filtered_df.groupby(['REGION', 'TECHNOLOGY'])['VALUE'].mean().reset_index()
        df_ctau = pd.concat([df_ctau, filtered_df]).drop_duplicates(subset=['REGION', 'TECHNOLOGY'], keep='last')
        df_ctau.to_csv('data/CapacityToActivityUnit.csv', index=False)
    #CapitalCost
    df_country = pd.read_csv(code / 'CapitalCost.csv')
    PowerPlants= dictionary[country]['PowerPlants']
    SupplyTechs= dictionary[country]['SupplyTechs']
    for powerplant in PowerPlants:
        term = PowerPlants[powerplant]
        filtered_df = df_country[df_country['TECHNOLOGY'].isin(term)]
        filtered_df.loc[:, 'REGION'] = 'GLOBAL'
        filtered_df.loc[:, 'TECHNOLOGY'] = "PWR" + powerplant + country + "01"
        filtered_df = filtered_df.groupby(['REGION', 'TECHNOLOGY', 'YEAR'])['VALUE'].sum().reset_index()
        df_cc = pd.read_csv('data/CapitalCost.csv')
        df_cc = pd.concat([df_cc, filtered_df]).drop_duplicates(subset=['REGION', 'TECHNOLOGY', 'YEAR'], keep='last')
        df_cc = df_cc[(df_cc['YEAR'] >= startYear) & (df_cc['YEAR'] <= endYear)]
        df_cc.to_csv('data/CapitalCost.csv', index=False)
    for supplytech in SupplyTechs:
        term = SupplyTechs[supplytech]
        filtered_df = df_country[df_country['TECHNOLOGY'].isin(term)]
        filtered_df.loc[:, 'REGION'] = 'GLOBAL'
        filtered_df.loc[:, 'TECHNOLOGY'] = "SUP" + supplytech + country
        filtered_df = filtered_df.groupby(['REGION', 'TECHNOLOGY', 'YEAR'])['VALUE'].sum().reset_index()
        df_cc = pd.concat([df_cc, filtered_df]).drop_duplicates(subset=['REGION', 'TECHNOLOGY', 'YEAR'], keep='last')
        df_cc = df_cc[(df_cc['YEAR'] >= startYear) & (df_cc['YEAR'] <= endYear)]
        df_cc.to_csv('data/CapitalCost.csv', index=False)
    #FixedCost
    df_country = pd.read_csv(code / 'FixedCost.csv')
    PowerPlants= dictionary[country]['PowerPlants']
    SupplyTechs= dictionary[country]['SupplyTechs']
    for powerplant in PowerPlants:
        term = PowerPlants[powerplant]
        filtered_df = df_country[df_country['TECHNOLOGY'].isin(term)]
        filtered_df.loc[:, 'REGION'] = 'GLOBAL'
        filtered_df.loc[:, 'TECHNOLOGY'] = "PWR" + powerplant + country + "01"
        filtered_df = filtered_df.groupby(['REGION', 'TECHNOLOGY', 'YEAR'])['VALUE'].sum().reset_index()
        df_fc = pd.read_csv('data/FixedCost.csv')
        df_fc = pd.concat([df_fc, filtered_df]).drop_duplicates(subset=['REGION', 'TECHNOLOGY', 'YEAR'], keep='last')
        df_fc = df_fc[(df_fc['YEAR'] >= startYear) & (df_fc['YEAR'] <= endYear)]
        df_fc.to_csv('data/FixedCost.csv', index=False)
    for supplytech in SupplyTechs:
        term = SupplyTechs[supplytech]
        filtered_df = df_country[df_country['TECHNOLOGY'].isin(term)]
        filtered_df.loc[:, 'REGION'] = 'GLOBAL'
        filtered_df.loc[:, 'TECHNOLOGY'] = "SUP" + supplytech + country
        filtered_df = filtered_df.groupby(['REGION', 'TECHNOLOGY', 'YEAR'])['VALUE'].sum().reset_index()
        df_fc = pd.concat([df_fc, filtered_df]).drop_duplicates(subset=['REGION', 'TECHNOLOGY', 'YEAR'], keep='last')
        df_fc = df_fc[(df_fc['YEAR'] >= startYear) & (df_fc['YEAR'] <= endYear)]
        df_fc.to_csv('data/FixedCost.csv', index=False)

    #VariableCost
    df_country = pd.read_csv(code / 'VariableCost.csv')
    PowerPlants= dictionary[country]['PowerPlants']
    SupplyTechs= dictionary[country]['SupplyTechs']
    for powerplant in PowerPlants:
        term = PowerPlants[powerplant]
        filtered_df = df_country[df_country['TECHNOLOGY'].isin(term)]
        filtered_df.loc[:, 'REGION'] = 'GLOBAL'
        filtered_df.loc[:, 'TECHNOLOGY'] = "PWR" + powerplant + country + "01"
        filtered_df.loc[:,'MODE_OF_OPERATION'] = 1
        filtered_df_copy = filtered_df.copy()
        filtered_df_copy.loc[:,'MODE_OF_OPERATION'] = 2
        filtered_df = pd.concat([filtered_df, filtered_df_copy])
        filtered_df = filtered_df.groupby(['REGION', 'TECHNOLOGY', 'MODE_OF_OPERATION', 'YEAR'])['VALUE'].sum().reset_index()
        df_vc = pd.read_csv('data/VariableCost.csv')
        df_vc = pd.concat([df_vc, filtered_df]).drop_duplicates(subset=['REGION', 'TECHNOLOGY','MODE_OF_OPERATION', 'YEAR'], keep='last')
        df_vc = df_vc[(df_vc['YEAR'] >= startYear) & (df_vc['YEAR'] <= endYear)]
        df_vc.to_csv('data/VariableCost.csv', index=False)
    for supplytech in SupplyTechs:
        term = SupplyTechs[supplytech]
        filtered_df = df_country[df_country['TECHNOLOGY'].isin(term)]
        filtered_df.loc[:, 'REGION'] = 'GLOBAL'
        filtered_df.loc[:, 'TECHNOLOGY'] = "SUP" + supplytech + country
        filtered_df.loc[:,'MODE_OF_OPERATION'] = 1
        filtered_df_copy = filtered_df.copy()
        filtered_df_copy.loc[:,'MODE_OF_OPERATION'] = 2
        filtered_df = pd.concat([filtered_df, filtered_df_copy])
        filtered_df = filtered_df.groupby(['REGION', 'TECHNOLOGY','MODE_OF_OPERATION','YEAR'])['VALUE'].sum().reset_index()
        df_vc = pd.concat([df_vc, filtered_df]).drop_duplicates(subset=['REGION', 'TECHNOLOGY','MODE_OF_OPERATION', 'YEAR'], keep='last')
        df_vc = df_vc[(df_vc['YEAR'] >= startYear) & (df_vc['YEAR'] <= endYear)]
        df_vc.to_csv('data/VariableCost.csv', index=False)
    #EmissonActivityRatio
    df_country = pd.read_csv(code / 'EmissionActivityRatio.csv')
    PowerPlants= dictionary[country]['PowerPlants']
    SupplyTechs= dictionary[country]['SupplyTechs']
    for powerplant in PowerPlants:
        term = PowerPlants[powerplant]
        filtered_df = df_country[df_country['TECHNOLOGY'].isin(term)]
        filtered_df.loc[:, 'REGION'] = 'GLOBAL'
        filtered_df.loc[:, 'EMISSION'] = 'CO2'
        filtered_df.loc[:, 'TECHNOLOGY'] = "PWR" + powerplant + country + "01"
        filtered_df.loc[:, 'MODE_OF_OPERATION'] = 1
        filtered_df_copy = filtered_df.copy()
        filtered_df_copy.loc[:,'MODE_OF_OPERATION'] = 2
        filtered_df = pd.concat([filtered_df, filtered_df_copy])
        filtered_df = filtered_df.groupby(['REGION', 'TECHNOLOGY','EMISSION','MODE_OF_OPERATION','YEAR'])['VALUE'].mean().reset_index()
        df_ear = pd.read_csv('data/EmissionActivityRatio.csv')
        df_ear = pd.concat([df_ear, filtered_df]).drop_duplicates(subset=['REGION', 'TECHNOLOGY', 'EMISSION', 'MODE_OF_OPERATION', 'YEAR'], keep='last')
        df_ear = df_ear[(df_ear['YEAR'] >= startYear) & (df_ear['YEAR'] <= endYear)]
        df_ear.to_csv('data/EmissionActivityRatio.csv', index=False)
    for supplytech in SupplyTechs:
        term = SupplyTechs[supplytech]
        filtered_df = df_country[df_country['TECHNOLOGY'].isin(term)]
        filtered_df.loc[:, 'REGION'] = 'GLOBAL'
        filtered_df.loc[:, 'EMISSION'] = 'CO2'
        filtered_df.loc[:, 'TECHNOLOGY'] = "SUP" + supplytech + country
        filtered_df.loc[:,'MODE_OF_OPERATION'] = 1
        filtered_df_copy = filtered_df.copy()
        filtered_df_copy.loc[:,'MODE_OF_OPERATION'] = 2
        filtered_df = pd.concat([filtered_df, filtered_df_copy])
        filtered_df = filtered_df.groupby(['REGION', 'TECHNOLOGY','EMISSION','MODE_OF_OPERATION','YEAR'])['VALUE'].mean().reset_index()
        df_ear = pd.concat([df_ear, filtered_df]).drop_duplicates(subset=['REGION', 'TECHNOLOGY','EMISSION','MODE_OF_OPERATION','YEAR'], keep='last')
        df_ear = df_ear[(df_ear['YEAR'] >= startYear) & (df_ear['YEAR'] <= endYear)]
        df_ear.to_csv('data/EmissionActivityRatio.csv', index=False)
    #ResidualCapacity
    df_country = pd.read_csv(code / 'ResidualCapacity.csv')
    PowerPlants= dictionary[country]['PowerPlants']
    SupplyTechs= dictionary[country]['SupplyTechs']
    for powerplant in PowerPlants:
        term = PowerPlants[powerplant]
        filtered_df = df_country[df_country['TECHNOLOGY'].isin(term)]
        filtered_df.loc[:, 'REGION'] = 'GLOBAL'
        filtered_df.loc[:, 'TECHNOLOGY'] = "PWR" + powerplant + country + "01"
        filtered_df = filtered_df.groupby(['REGION', 'TECHNOLOGY', 'YEAR'])['VALUE'].sum().reset_index()
        df_rc = pd.read_csv('data/ResidualCapacity.csv')
        df_rc = pd.concat([df_rc, filtered_df]).drop_duplicates(subset=['REGION', 'TECHNOLOGY', 'YEAR'], keep='last')
        df_rc = df_rc[(df_rc['YEAR'] >= startYear) & (df_rc['YEAR'] <= endYear)]
        df_rc.to_csv('data/ResidualCapacity.csv', index=False)
    for supplytech in SupplyTechs:
        term = SupplyTechs[supplytech]
        filtered_df = df_country[df_country['TECHNOLOGY'].isin(term)]
        filtered_df.loc[:, 'REGION'] = 'GLOBAL'
        filtered_df.loc[:, 'TECHNOLOGY'] = "SUP" + supplytech + country
        filtered_df = filtered_df.groupby(['REGION', 'TECHNOLOGY', 'YEAR'])['VALUE'].sum().reset_index()
        df_rc = pd.concat([df_rc, filtered_df]).drop_duplicates(subset=['REGION', 'TECHNOLOGY', 'YEAR'], keep='last')
        df_rc = df_rc[(df_rc['YEAR'] >= startYear) & (df_rc['YEAR'] <= endYear)]
        df_rc.to_csv('data/ResidualCapacity.csv', index=False)
    #OperationalLife
    df_country = pd.read_csv(code / 'OperationalLife.csv')
    PowerPlants= dictionary[country]['PowerPlants']
    SupplyTechs= dictionary[country]['SupplyTechs']
    for powerplant in PowerPlants:
        term = PowerPlants[powerplant]
        filtered_df = df_country[df_country['TECHNOLOGY'].isin(term)]
        filtered_df.loc[:, 'REGION'] = 'GLOBAL'
        filtered_df.loc[:, 'TECHNOLOGY'] = "PWR" + powerplant + country + "01"
        filtered_df = filtered_df.groupby(['REGION', 'TECHNOLOGY'])['VALUE'].sum().reset_index()
        df_ol = pd.read_csv('data/OperationalLife.csv')
        df_ol = pd.concat([df_ol, filtered_df]).drop_duplicates(subset=['REGION', 'TECHNOLOGY'], keep='last')
        df_ol.to_csv('data/OperationalLife.csv', index=False)
    for supplytech in SupplyTechs:
        term = SupplyTechs[supplytech]
        filtered_df = df_country[df_country['TECHNOLOGY'].isin(term)]
        filtered_df.loc[:, 'REGION'] = 'GLOBAL'
        filtered_df.loc[:, 'TECHNOLOGY'] = "SUP" + supplytech + country
        filtered_df = filtered_df.groupby(['REGION', 'TECHNOLOGY'])['VALUE'].sum().reset_index()
        df_ol = pd.concat([df_ol, filtered_df]).drop_duplicates(subset=['REGION', 'TECHNOLOGY'], keep='last')
        df_ol.to_csv('data/OperationalLife.csv', index=False)
    #TotalAnnualMaxCapacity
    df_country = pd.read_csv(code / 'TotalAnnualMaxCapacity.csv')
    PowerPlants= dictionary[country]['PowerPlants']
    SupplyTechs= dictionary[country]['SupplyTechs']
    for powerplant in PowerPlants:
        term = PowerPlants[powerplant]
        filtered_df = df_country[df_country['TECHNOLOGY'].isin(term)]
        filtered_df.loc[:, 'REGION'] = 'GLOBAL'
        filtered_df.loc[:, 'TECHNOLOGY'] = "PWR" + powerplant + country + "01"
        filtered_df = filtered_df.groupby(['REGION', 'TECHNOLOGY', 'YEAR'])['VALUE'].sum().reset_index()
        df_tamc = pd.read_csv('data/TotalAnnualMaxCapacity.csv')
        df_tamc = pd.concat([df_tamc, filtered_df]).drop_duplicates(subset=['REGION', 'TECHNOLOGY', 'YEAR'], keep='last')
        df_tamc = df_tamc[(df_tamc['YEAR'] >= startYear) & (df_tamc['YEAR'] <= endYear)]
        df_tamc.to_csv('data/TotalAnnualMaxCapacity.csv', index=False)
    for supplytech in SupplyTechs:
        term = SupplyTechs[supplytech]
        filtered_df = df_country[df_country['TECHNOLOGY'].isin(term)]
        filtered_df.loc[:, 'REGION'] = 'GLOBAL'
        filtered_df.loc[:, 'TECHNOLOGY'] = "SUP" + supplytech + country
        filtered_df = filtered_df.groupby(['REGION', 'TECHNOLOGY', 'YEAR'])['VALUE'].sum().reset_index()
        df_tamc = pd.concat([df_tamc, filtered_df]).drop_duplicates(subset=['REGION', 'TECHNOLOGY', 'YEAR'], keep='last')
        df_tamc = df_tamc[(df_tamc['YEAR'] >= startYear) & (df_tamc['YEAR'] <= endYear)]
        df_tamc.to_csv('data/TotalAnnualMaxCapacity.csv', index=False)







            
     

       
