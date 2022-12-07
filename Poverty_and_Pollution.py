import csv
from shapely.geometry import Point
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from scipy.stats import pearsonr
import scipy.stats as stats
import statsmodels.api as sm

# Function to take two numerical columns and give results for a Linear Regression, Linear Repression Plot, and Pearson's R
def statistical_analysis(x, y, xlab, ylab, title):
    X = x.values.reshape(-1, 1)
    Y = y.values.reshape(-1, 1)
    linear_regresson = LinearRegression()
    linear_regresson.fit(X, Y) 
    Y_pred = linear_regresson.predict(X)
    print(title)
    plt.scatter(X, Y, color = 'lime')
    plt.plot(X, Y_pred, color = 'aqua')
    plt.xlabel(xlab)
    plt.ylabel(ylab)
    plt.show()
    spector_data = sm.datasets.spector.load()
    spector_data.exog = sm.add_constant(spector_data.exog, prepend=False)
    mod = sm.OLS(spector_data.endog, spector_data.exog)
    res = mod.fit()
    print(res.summary())
    r = stats.pearsonr(x, y)
    print('Persons R calculation: ', r[0])

# File Path to change for code to run smoothly
file_dir = './Data/'

# Open files and reads shp as gdf
#acs_data had crs of 4269 so the other files is set to match 
acs_data = gpd.read_file(file_dir +'ACS1620_county/ACS1620_county.shp')
mines_data = gpd.read_file(file_dir + 'Merge_MergePermit_Active_Coal_Permit/Merge_MergePermit_Active_Coal_Permit.shp').to_crs(4269)
superfund_sites = file_dir + 'ColoradoSuperfundarea.csv'

#imports fields we care about from shp
#included type field with value of mines
mines_gdf = mines_data[['SiteName', 'geometry','PermitAcre']]
mines_gdf.insert(3, 'type', 'mines')


with open(superfund_sites) as file_obj:
    reader_obj = csv.reader(file_obj)

    df = []
    #sets field names to match mines file
    superfund_points = {'SiteName': [], 'geometry': [], 'PermitAcre': [], 'type': []} 
    
    for i, row in enumerate (reader_obj):
        #print(i, row)
        if (i == 0):
            #skips the header row of the csv
            pass
        else:
            x = float(row[11])
            y = float(row[12])
            point = Point(x, y)
            superfund_points['geometry'].append(Point((x, y)))   
            superfund_points['SiteName'].append(row[1])
            superfund_points['PermitAcre'].append(row[13])
            superfund_points['type'].append('superfund site')
            superfund_gdf = gpd.GeoDataFrame(superfund_points, crs="EPSG:4269") 

            
# Combines the active mines and superfund site points to be in one total geodataframe, so all pollution sites can be in one geodataframe             
list_frames = [mines_gdf, superfund_gdf]
combined_frames = pd.concat(list_frames)
    
#adds acs_data to all the mines and superfund sites    
#overlay_gdf = gpd.overlay(combined_frames,acs_data, how = 'intersection')  
overlay_gdf = gpd.sjoin(combined_frames,acs_data, how = 'right')  

#copies select fields from acs_data dataframe; added new column with the number of people in poverty per 1000 people 
county_poverty_df = acs_data[['NAME20','in_poverty','pop1620','geometry']].copy() 
county_poverty_df['per_pvty'] = (acs_data['in_poverty']*1000) / acs_data['pop1620'] 

#overlay_gdf has 1 entry per site; for dissolve i did a count on random column to get 
#number of sites in the county; broomfield should be zero but listed as 1
county_sites_df = overlay_gdf.dissolve(by='NAME20', aggfunc= {'in_poverty': 'count'})

#since I used random colum, i wanted to rename
county_sites_df.rename(columns = {'in_poverty':'sites'},inplace=True)

#county row in overlay_gdf is counted even if no points are in it
#this step swaps all 1s to 0s; changes Broomfield to 0
county_sites_df['sites'] = county_sites_df['sites'].replace(1, 0)

# Alphabetizes the County Poverty dataframe by the name of each county and set that as an index
county_poverty_df1 = county_poverty_df.sort_values(['NAME20']).set_index("NAME20")

# Joining the two dataframes, dropping one column of geometry since only one is needed
pollution_df = county_poverty_df1.join(county_sites_df.drop('geometry', axis=1))

# Setting up the dataframe so that the area of each county polygon can be calculated in square miles
pollution_df = pollution_df.to_crs(crs=2232)

#area converted from survey feet to square miles 
pollution_df['area_sq_mile'] = (pollution_df.area/5280**2)

# Getting the final dataframe ready for statistical tests by adding in the pollution site area in permit acres and converting to square miles
overlay_gdf['PermitAcre'] = overlay_gdf['PermitAcre'].astype(float)
permit_acres_df = overlay_gdf.groupby(['NAME20']).sum()
pollution_df['site_sq_mile'] = permit_acres_df['PermitAcre']/640

# Standardizing the sites per 1,000 square miles and site area per 1,000 square miles 
pollution_df['sites_per_1000_miles'] = pollution_df['sites']*1000/pollution_df['area_sq_mile']
pollution_df['site_area_per_1000_miles'] = pollution_df['site_sq_mile']*1000/pollution_df['area_sq_mile']

# Using the function statistcal_analysis to get results for pollution sites and pollution site areas as functions of the poverty rate, respectively 
statistical_analysis(pollution_df['per_pvty'], pollution_df['sites_per_1000_miles'], 'Poverty Rate (People in Poverty per 1,000 People)', 'Pollution Sites per 1000 Miles', 'Linear Regression Graph 1: Poverty and Pollution Sites per 1,000 Miles')
statistical_analysis(pollution_df['per_pvty'], pollution_df['site_area_per_1000_miles'], 'Poverty Rate (People in Poverty per 1,000 People)', 'Pollution Site Areas per 1000 Miles', 'Linear Regression Graph 2: Poverty and Pollution Sitee Areas per 1,000 Miles')