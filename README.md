
# OSeMOSYS LAC

OSeMOSYS LAC (OSeMOSYS Latin America and Caribbean) Energy Model is a regionally integrated energy model, developed using the OSeMOSYS (Open Source Energy Modelling System) framework, specifically adapted to the energy reality of Latin America and the Caribbean. The model intricately represents each of the countries in the LAC region, encompassing a broad spectrum of energy sources and technologies prevalent in these areas. OSeMOSYS LAC is designed to provide a platform for comprehensive energy planning and policy analysis in the region.

## Workflow
![Workflow](https://github.com/EPERLab/OSeMOSYS-LAC/blob/main/Workflow.png)

## Installation
Note: These manual installation steps will be automated in future releases of OSeMOSYS LAC.
Tools to be installed:
1. Install OSeMOSYS Global following the steps at: https://osemosys-global.readthedocs.io/en/latest/installation.html
2. Clone clewsy repository following the steps at: https://github.com/OSeMOSYS/clewsy
### How to Run
1. Create a OSeMOSYS Global configuration file ```config.yaml``` with the time slices and countries.  
Use the instructions in [Configuration File](https://osemosys-global.readthedocs.io/en/latest/getting-started.html#configuration-file) to create the file.
In this repository you will find an example configuration file to create a Costa Rica model.

2. Generate the input OSeMOSYS Global CSV files using  [Generate Input Data](https://osemosys-global.readthedocs.io/en/latest/advanced-functionality.html#generate-template-data)
```
snakemake generate_input_data -j6
```
3. Replace the clewsy.py file in the clewsy folder with the one in this repository.

4. Create the configuration file to use [clewsy](https://github.com/OSeMOSYS/clewsy)for create the structure for the energy model. In this repository you can find an example of configuration file.

In *Years:* you must enter the years that correspond to the startYear and endYear that you entered in the OSeMOSYS Global configuration file.

In *LandRegions*: you must put the same country codes that you put in the OSeMOSYS Global configuration file in the geographic_scope section. 

If you are using a node in OSeMOSYS Global within a country you must put it in LandToGridMap following the structure: 
'AAAXX' where AAA is a 3-letter country code, specified in the 'geographic scope' and XX is a 2-letter sub-regional node code. 

In *EndUseFuels: you must enter all the fuels used in the sectors you want to create. Following this structure:
```
EndUseFuels: {
  SECTOR1:['FUELa','FUELb','FUELc'],
  SECTOR2:['FUELx','FUELy','FUELz'],
  .
  .
  .
  SECTORn:['FUELa',FUELz','FUELb']
}
```
See this example:

```
EndUseFuels: {
  AGR: ['ELC','DSL'],
  IND: ['ELC','LPG','GSL'],
}
```
This example indicates that in the agriculture sector (AGR) the end-use fuels used are electricity (ELC) and diesel (DSL) and in industrial sector (IND) are electricity (ELC), liquefied petroleum gas (LPG) and gasoline (GSL).

In *PowerPlants* you must indicate which power plants you want to create. OSeMOSYS Global creates plants for the technologies contained in [Technology Acronyms](https://osemosys-global.readthedocs.io/en/latest/model-structure.html#technology-acronyms) so if you want any plant that is not in this list you must add it following the following structure:
```
PowerPlants: {
   PWR(FUEL): ['Description', 'IAR', 'MIN' or 'RNW'],
}
```
In IAR you should put the input activity ratio for this plant then put if the plant use something non renewable (MIN) or use renewable sources (RNW).
See this example:
```
PowerPlants: {
   PWRDSL: ['Diesel power plant', '0.88', 'MIN'],
}
```
This example creates a diesel power plant, with a input activity ratio of '2.5' and indicates 'MIN' because use diesel.
Note: The value of the IAR will be overwritten with the value of each national model in the following steps.

5. Create the dictionary to use the TransMoSYS code.
In dictionary.yaml you should indicate first the country code and the region code, if you are not going to indicate a region enter XX.
In *SpecifiedDemand* you must put all the demands you create as EndUseFuels with clewsy and how is named it in the national model following the structure:
```
AAAXX:
  SpecifiedDemand: {
      SECTOR+FUEL:['NAME1','NAME2']
```
See the case for Costa Rica model:
```
CRIXX:
  SpecifiedDemand: {
    AGRELC:['E5AGRELE'],
    AGRDSL:['E5AGRDSL'],
    COMELC:['E5PUBELE','E5COMELE'],
    COMLPG:['E5COMLPG'],
    RESELC:['E5RESELE'],
    RESLPG:['E5RESLPG'],
    }
```
For *PowerPlants* and *SupplyTechs* you must put the fuel and naming of every power plant and supply technology that it is in the national model. Following the structure:
```
PowerPlants: {
    FUEL:['NAME1','NAME2'],
    }
SupplyTechs: {
    FUEL:['NAME1','NAME2'],  
    }
```
See the case for Costa Rica model:
```
PowerPlants: {
    HYD:['PPHROR','PPHDAM'],
    GEO:['PPGEO'],
    DSL:['PPDSL'],
    BIO:['PPBIO'],
    SPV:['PPPVT',PPVTHYD','PPPVTS','PPPVD',' PPPVDS'],
    WON:['PPWNDON'],
    }
SupplyTechs: {
    DSL:['DIST_DSL'],
    LPG:['DIST_LPG']   
    }    
```
6. Run the TransMoSYS code and then replace the folder *data* on the OSeMOSYS Global.

7. Run OSeMOSYS Global as usual:
```
snakemake -j6
```

