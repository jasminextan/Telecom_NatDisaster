import pandas as pd
import geopandas as gpd
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
mapping = {'Very Low': 0, 'Relatively Low': 1, 'Relatively Moderate': 2, 'Relatively High': 3, 'Very High': 4}
df['RISK_RATNG'] = df['RISK_RATNG'].map(mapping).astype(float)

# Create population density POP_DENS feature (Population/Sq Mile)

df['POP_DENS'] = df['POPULATION'] / (df['AREA'])

# Create telecom population density TOWER_POP_DENS feature (Towers/100 Population), removing outliers

df['TOWER_POP_DENS'] = df['TOWERCOUNT'] / (df['POPULATION']/100)
z_scores = (df['TOWER_POP_DENS'] - df['TOWER_POP_DENS'].mean()) / df['TOWER_POP_DENS'].std()
threshold = 3
df = df[abs(z_scores) <= threshold]

# Create telecom area density TOWER_AREA_DENS feature (Towers/100 Sq Mile), removing outliers

df['TOWER_AREA_DENS'] = df['TOWERCOUNT'] / (df['AREA'] / 100)
z_scores = (df['TOWER_AREA_DENS'] - df['TOWER_AREA_DENS'].mean()) / df['TOWER_AREA_DENS'].std()
threshold = 3
df = df[abs(z_scores) <= threshold]

# Create TOWER_SHORTAGE, which calculates which counties have cell tower shortages, based on area coverage and population density
# On average, the maximum usable range of a cell tower is 25 miles (40 kilometers). The typical coverage radius of a cell tower is 1 to 3 miles.
# To be conservative, we will take 5 miles as the ideal coverage range of a cell tower.
# Source: https://dgtlinfra.com/cell-tower-range-how-far-reach/
# With a radius of 5 miles, each tower can cover 79 sq miles. 
# Therefore, Ideal TOWER_AREA_DENS = 1.27 towers / 100 miles

# An average cellular tower allows about 30 simultaneous users for voice calls and 60 for 4G data.
# For 80% of the population to have 4G access in a natural disaster, one cell tower can cover 75 population.
# Source: https://surecall.com/surecall-cell-phone-signal-booster-blog/capacity-in-the-cell-signal-oriented-world/
# Therefore: Ideal  = 1.33 towers / 100 population

# Difference between ideal and actual
df['POPSHORTAGE_DIFF'] = df['TOWER_POP_DENS'] - 1.33
df['AREASHORTAGE_DIFF'] = df['TOWER_AREA_DENS'] - 1.27
df['SHORTAGE_SUM'] = df['AREASHORTAGE_DIFF'] + df['POPSHORTAGE_DIFF']

# Identify quintile for feature "SHORTAGE_SUM" in df and create a new variable "SHORTAGE_RATING" that indicates which quintile each entry falls under.
df['SHORTAGE_RATING'] = pd.qcut(df['SHORTAGE_SUM'], q=5, labels=False)

# Create "BUILDTOWER" that multiplies "SHORTAGE_RATING" and "RISK_RATNG", creating a measure of areas that are high in natural disaster risk and low in cell tower coverage.
df['BUILDTOWER'] = df['SHORTAGE_RATING'] * df['RISK_RATNG']

# Retrieve Top 10 Counties
top_ten = df.sort_values('BUILDTOWER', ascending=False).head(10)[['BUILDTOWER', 'COUNTY', 'SHORTAGE_RATING', 'RISK_RATNG']]
print(top_ten)

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
plt.savefig('visualizations/RiskRating.png')
plt.show()

# PLOT SHORTAGE_RATING
# Create a figure and axis
fig, ax = plt.subplots()
# Plot the counties with color-coded SHORTAGE_RATING
gdf_counties.plot(column='SHORTAGE_RATING', cmap='viridis', linewidth=0.1, ax=ax, edgecolor='0.8')
# Customize the plot
ax.set_title('Areas with Insufficent Coverage by County')
ax.axis('off')
# Add a colorbar
sm = plt.cm.ScalarMappable(cmap='viridis')
sm.set_array(gdf_counties['SHORTAGE_RATING'])
cbar = plt.colorbar(sm, ax=ax, fraction=0.02)  # Specify the ax argument
# Show and save the plot
plt.savefig('visualizations/CellTowerShortage.png')
plt.show()

# PLOT BUILDTOWER
# Create a figure and axis
fig, ax = plt.subplots()
# Plot the counties with color-coded BUILDTOWER
gdf_counties.plot(column='BUILDTOWER', cmap='viridis', linewidth=0.1, ax=ax, edgecolor='0.8')
# Customize the plot
ax.set_title('Areas with Insufficent Coverage and High Natural Disaster Risk by County')
ax.axis('off')
# Add a colorbar
sm = plt.cm.ScalarMappable(cmap='viridis')
sm.set_array(gdf_counties['BUILDTOWER'])
cbar = plt.colorbar(sm, ax=ax, fraction=0.02)  # Specify the ax argument
# Show and save the plot
plt.savefig('visualizations/BUILDTOWERSHERE.png')
plt.show()

print(top_ten)
'''
      BUILDTOWER      COUNTY  SHORTAGE_RATING  RISK_RATNG
433         12.0  WASHINGTON                4         3.0
527         12.0       CLARK                4         3.0
289         12.0      MARION                4         3.0
865         12.0     DOUGLAS                4         3.0
792         12.0      ORANGE                4         3.0
607         12.0   LAFAYETTE                4         3.0
1248        12.0       WAYNE                4         3.0
787         12.0      ORANGE                3         4.0
2096        12.0   ST. LOUIS                4         3.0
179         12.0     JACKSON                4         3.0
'''