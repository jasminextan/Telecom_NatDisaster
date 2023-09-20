import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt

# DATA SOURCES
# Telecom Database: https://www.kaggle.com/datasets/mattop/cellular-towers-in-the-united-states
# NRI Database: https://hazards.fema.gov/nri/map
# County SHP: https://www.census.gov/geographies/mapping-files/time-series/geo/carto-boundary-file.html

df = pd.read_csv('data/NRI_Table_Counties/NRI_Table_Counties.csv')

# ID necessary features via data/NRI_Table_Counties/NRIDataDictionary.csv

# Sort,Field Name,Field Alias,Type,Length,Relevant Layer,Metric Type,Version,Version Date
# 5,STATE,State Name,String,250,All,n/a,1.19.0,March 2023
# 8,COUNTY,County Name,String,250,All,n/a,1.19.0,March 2023
# 10,COUNTYFIPS,County FIPS Code,String,20,All,n/a,1.19.0,March 2023
# 14,NRI_ID,National Risk Index ID,String,20,All,n/a,1.19.0,March 2023
# 15,POPULATION,Population (2020),Integer,4,All,n/a,1.19.0,March 2023
# 18,AREA,Area (sq mi),Double,8,All,n/a,1.19.0,March 2023
# 21,RISK_RATNG,National Risk Index - Rating - Composite,String,50,National Risk Index,Rating,1.19.0,March 2023

necessary_features = ['STATE', 'COUNTY', 'COUNTYFIPS', 'NRI_ID', 'POPULATION', 'AREA', 'RISK_RATNG']
df_simplified = df[necessary_features]
df_simplified.to_csv('data/Simplified_NRI_Counties.csv', index=False)

# Generate a new dataset called Celltower_Count.CSV that counts how many cell towers are within each county.

dfcell = pd.read_csv('data/celltowers.csv')
df_count = dfcell.groupby('county').size().reset_index(name='TOWERCOUNT')
df_count.rename(columns={'county': 'COUNTY'}, inplace=True)
df_count.to_csv('data/Celltower_Count.csv', index=False)

# Adjust 'county' feature on both datasets so they can be merged by county.

df = pd.read_csv('data/Simplified_NRI_Counties.csv')
df['COUNTY'] = df['COUNTY'].str.upper()
df.to_csv('data/Simplified_NRI_Counties.csv', index=False)

# Merge two datasets

nri_df = pd.read_csv('data/Simplified_NRI_Counties.csv')
celltower_df = pd.read_csv('data/Celltower_Count.csv')
merged_df = pd.merge(nri_df, celltower_df, on='COUNTY')
merged_df.to_csv('data/Merged_Dataset.csv', index=False)

# "RISK_RATNG" is currently in String form. Turn it into indexes, where Very Low = 1, Relatively Low = 2, Relatively Moderate = 3, Relatively High = 4, Very High = 5

df = pd.read_csv('data/Merged_Dataset.csv')
mapping = {'Very Low': 1, 'Relatively Low': 2, 'Relatively Moderate': 3, 'Relatively High': 4, 'Very High': 5}
df['RISK_RATNG'] = df['RISK_RATNG'].map(mapping).astype(float)

# Create population density POP_DENS feature (Population/Sq Mile)

df['POP_DENS'] = df['POPULATION'] / (df['AREA'])

# Create telecom tower density TOWER_DENS feature (Towers/100 Sq Mile), removing outliers

df['TOWER_DENS'] = df['TOWERCOUNT'] / (df['AREA'] / 100)
z_scores = (df['TOWER_DENS'] - df['TOWER_DENS'].mean()) / df['TOWER_DENS'].std()
threshold = 3
df = df[abs(z_scores) <= threshold]

# Create TOWER_SHORTAGE, which calculates which counties need the most support

# Save Changes
df.to_csv('data/Merged_Dataset.csv', index=False)


# Create map visualization using Geopandas

# Path to the shapefile of US counties
shapefile_path = 'data/cb_2018_us_county_5m/cb_2018_us_county_5m.shp'
# Read the shapefile into a GeoDataFrame
gdf_counties = gpd.read_file(shapefile_path)
gdf_counties['COUNTY'] = gdf_counties['NAME'].str.upper()

print(gdf_counties.columns)
print(df.columns)

gdf_counties = gdf_counties.merge(df, left_on='COUNTY', right_on='COUNTY', how='left')
print(gdf_counties.columns)
print(gdf_counties.head())


# PLOT RISK_RATNG
# Create a figure and axis
fig, ax = plt.subplots()
# Plot the counties with color-coded RISK_RATING
gdf_counties.plot(column='RISK_RATNG', cmap='viridis', linewidth=0.1, ax=ax, edgecolor='0.8')
# Customize the plot
ax.set_title('NRI Natural Disaster Risk Rating by County')
ax.axis('off')
# Add a colorbar with a smaller size
sm = plt.cm.ScalarMappable(cmap='viridis')
sm.set_array(gdf_counties['RISK_RATNG'])
cbar = plt.colorbar(sm, ax=ax, fraction=0.02)  # Specify the ax argument
# Show and save the plot
plt.show()
plt.savefig('visualizations/RiskRating.png')

# PLOT TOWER_DENS
# Create a figure and axis
fig, ax = plt.subplots()
# Plot the counties with color-coded TOWER_DENS
gdf_counties.plot(column='TOWER_DENS', cmap='viridis', linewidth=0.1, ax=ax, edgecolor='0.8')
# Customize the plot
ax.set_title('Cell Tower Density (Towers per 100 Sq Miles) by County')
ax.axis('off')
# Add a colorbar
sm = plt.cm.ScalarMappable(cmap='viridis')
sm.set_array(gdf_counties['TOWER_DENS'])
cbar = plt.colorbar(sm, ax=ax, fraction=0.02)  # Specify the ax argument
# Show the plot
plt.show()
plt.savefig('visualizations/CellTowerDensity.png')
