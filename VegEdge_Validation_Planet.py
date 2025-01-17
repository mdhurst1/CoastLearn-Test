#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 13 08:31:29 2022

@author: fmuir
"""
#!/usr/bin/env python
# coding: utf-8

# # VegEdge
# 

#%% Imports and Initialisation


import os
import numpy as np
import pickle
import warnings
warnings.filterwarnings("ignore")
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from matplotlib import gridspec
plt.ion()
from datetime import datetime, timezone, timedelta
from Toolshed import Download, Image_Processing, Shoreline, Toolbox, Transects, VegetationLine
import mpl_toolkits as mpl
from mpl_toolkits.axes_grid1.inset_locator import zoomed_inset_axes, mark_inset
from matplotlib.ticker import MaxNLocator
import matplotlib.dates as mdates
from sklearn.datasets import load_diabetes
from sklearn.metrics import mean_squared_error, r2_score
import seaborn as sns; sns.set()
import math
import geemap
import ee
import pprint
from shapely import geometry
from shapely.geometry import Point, LineString, Polygon
import pandas as pd
import geopandas as gpd
import matplotlib.cm as cm
import pyproj
from IPython.display import clear_output
import scipy
from scipy import optimize
import csv
import math

ee.Initialize()


#%% Define ROI using map


"""
OPTION 1: Generate a map. Use the polygon drawing tool on the left-hand side to 
draw out the region of coast you're interested in.
"""

Map = geemap.Map(center=[0,0],zoom=2)
Map.add_basemap('HYBRID')
Map


#%% 

# Run this after hand digitising to capture the coordinates of the ref shore
roi = Map.user_roi.geometries().getInfo()[0]['coordinates']
polygon = [[roi[0][0],roi[0][3],roi[0][1],roi[0][2]]]
point = ee.Geometry.Point(roi[0][0])


#%% Define ROI using coordinates of a rectangle

"""
OPTION 2: ROI polygon is defined using coordinates of a bounding box (in WGS84).
"""

##ST ANDREWS WEST
# sitename = 'StAndrewsWest'
# lonmin, lonmax = -2.89087, -2.84869
# latmin, latmax = 56.32641, 56.39814


##ST ANDREWS EAST
# sitename = 'StAndrewsEast'
# lonmin, lonmax = -2.84869, -2.79878
# latmin, latmax = 56.32641, 56.39814

##ST ANDREWS
sitename = 'StAndrewsPlanet'
lonmin, lonmax = -2.89087, -2.79878
latmin, latmax = 56.32641, 56.39814

##FELIXSTOWE
#lonmin, lonmax = 1.316128, 1.370888
#latmin, latmax = 51.930771, 51.965265

##BAY OF SKAILL
#lonmin, lonmax = -3.351555, -3.332693
#latmin, latmax = 59.048456, 59.057759

##SHINGLE STREET
#lonmin, lonmax = 1.446131, 1.460008
#latmin, latmax = 52.027039, 52.037448

#point = ee.Geometry.Point([lonmin, latmin]) 
if latmin > latmax:
    print('Check your latitude min and max bounding box values!')
    oldlatmin = latmin
    oldlatmax = latmax
    latmin = oldlatmax
    latmax = oldlatmin
if lonmin > lonmax:
    print('Check your longitude min and max bounding box values!')
    oldlonmin = lonmin
    oldlonmax = lonmax
    lonmin = oldlonmax
    lonmax = oldlonmin
    
polygon = [[[lonmin, latmin],[lonmax, latmin],[lonmin, latmax],[lonmax, latmax]]]
point = ee.Geometry.Point(polygon[0][0]) 

#%% Image Settings


# it's recommended to convert the polygon to the smallest rectangle (sides parallel to coordinate axes)       
polygon = Toolbox.smallest_rectangle(polygon)

# directory where the data will be stored
filepath = os.path.join(os.getcwd(), 'Data')

# date range
#dates = ['2021-05-01', '2021-07-02']

# date range for valiation
vegsurveyshp = './Validation/StAndrews_Veg_Edge_combined_2019_2022_singlepart.shp'
vegsurvey = gpd.read_file(vegsurveyshp)
vegdatemin = vegsurvey.Date.min()
vegdatemax = vegsurvey.Date.max()
# vegdatemin = datetime.strftime(datetime.strptime(vegsurvey.Date.min(), '%Y-%m-%d') - timedelta(weeks=4),'%Y-%m-%d')
# vegdatemax = datetime.strftime(datetime.strptime(vegsurvey.Date.max(), '%Y-%m-%d') + timedelta(weeks=4),'%Y-%m-%d')
dates = [vegdatemin, vegdatemax]
#dates = list(vegsurvey.Date.unique())
#dates = ['2011-03-04','2016-01-20']

print(dates)

if len(dates)>2:
    daterange='no'
else:
    daterange='yes'


years = list(Toolbox.daterange(datetime.strptime(dates[0],'%Y-%m-%d'), datetime.strptime(dates[-1],'%Y-%m-%d')))

# satellite missions
# Input a list of containing any/all of 'L5', 'L8', 'S2'
sat_list = ['PSScene4Band']

cloudthresh = 0.5

projection_epsg = 27700
image_epsg = 32630


# put all the inputs into a dictionnary
inputs = {'polygon': polygon, 'dates': dates, 'daterange':daterange, 'sat_list': sat_list, 'sitename': sitename, 'filepath':filepath, 'cloudthresh':cloudthresh}

direc = os.path.join(filepath, sitename)

if os.path.isdir(direc) is False:
    os.mkdir(direc)
 
    
#%% Image Retrieval

# before downloading the images, check how many images are available for your inputs

print('Enter your Planet API key: ')
os.environ['PL_API_KEY'] = input()
print('Your API key is: '+os.environ['PL_API_KEY'])
Sat = Toolbox.PlanetImageRetrieval(inputs)

Subset1 = Sat[0][45:63]
Subset2 = Sat[0][243:]
Sat[0] = Subset1
Sat[0].extend(Subset2)

# idURLs = Toolbox.PlanetDownload(Sat,filepath,sitename)
# metadata = Toolbox.PlanetMetadata(Sat, filepath, sitename)

#%% Image Download

"""
OPTION 1: Populate metadata using image names pulled from server.
"""
Sat = Toolbox.image_retrieval(inputs)
metadata = Toolbox.metadata_collection(inputs, Sat, filepath, sitename)

#%% Load In Local Imagery
Sat = Toolbox.LocalImageRetrieval(inputs)
metadata = Toolbox.LocalImageMetadata(inputs, Sat)

#%%  Metadata filtering using validation dates only
veridates = list(vegsurvey.Date.unique())
def neardate(satdates,veridate):
    return min(satdates, key=lambda x: abs(x - veridate))

nearestdates = dict.fromkeys(sat_list)
nearestIDs = dict.fromkeys(sat_list)

for sat in sat_list:
    print(sat,'sat')
    satdates=[]
    nearestdate = []
    nearestID = []
    for veridate in veridates:
        print('verification:\t',veridate)
        veridate = datetime.strptime(veridate,'%Y-%m-%d')
        for satdate in metadata[sat]['dates']:
            satdates.append(datetime.strptime(satdate,'%Y-%m-%d'))
        nearestdate.append(datetime.strftime(neardate(satdates,veridate),'%Y-%m-%d'))
        nearestID.append(metadata[sat]['dates'].index(datetime.strftime(neardate(satdates,veridate),'%Y-%m-%d')))
        print('nearest:\t\t',neardate(satdates,veridate))
    nearestdates[sat] = nearestdate
    nearestIDs[sat] = nearestID


#%%
L5 = dict.fromkeys(metadata['L5'].keys())
L8 = dict.fromkeys(metadata['L5'].keys())
S2 = dict.fromkeys(metadata['L5'].keys())

#must use extend() instead of append() for ranges of values
for satkey in dict.fromkeys(metadata['L5'].keys()):
    L5[satkey] = [metadata['L5'][satkey][0]]
    L5[satkey].extend(metadata['L5'][satkey][20:22])
    L5[satkey].extend(metadata['L5'][satkey][45:47])
    L8[satkey] = [metadata['L8'][satkey][41]]
    L8[satkey].append(metadata['L8'][satkey][42])
    L8[satkey].extend(metadata['L8'][satkey][143:145])
    L8[satkey].append(metadata['L8'][satkey][153])
    L8[satkey].append(metadata['L8'][satkey][159])       
    S2[satkey] = metadata['S2'][satkey][127:148]
    S2[satkey].extend(metadata['S2'][satkey][255:267])
    S2[satkey].extend(metadata['S2'][satkey][405:424])
    S2[satkey].extend(metadata['S2'][satkey][490:507])
    
    

metadata = {'L5':L5,'L8':L8,'S2':S2}
with open(os.path.join(filepath, sitename, sitename + '_validation_metadata.pkl'), 'wb') as f:
    pickle.dump(metadata, f)

#for nearestd in nearestdate:
#    print([i for i, x in enumerate(metadata['S2']['dates']) if x == nearestd])

# L5: 12 images (28% of 44), 1:27 (87s) = 0.138 im/s OR 7.25 im/s
# L8: 198 images, 16:42 (1002s) = 0.198 im/s OR 5 s/im
# S2: 34 images (10% of 335), 5:54 (354s) = 0.096 im/s OR 10.4 s/im

#%% Image Load-In
"""
OPTION 2: Populate metadata using pre-existing metadata.
"""

filepath = os.path.join(inputs['filepath'], sitename)
with open(os.path.join(filepath, sitename + '_metadata.pkl'), 'rb') as f:
    metadata = pickle.load(f)


#%% Vegetation Edge Settings

BasePath = 'Data/' + sitename + '/Veglines'

if os.path.isdir(BasePath) is False:
    os.mkdir(BasePath)

settings = {
    # general parameters:
    'cloud_thresh': cloudthresh,        # threshold on maximum cloud cover
    'output_epsg': image_epsg,     # epsg code of spatial reference system desired for the output   
    # quality control:
    'check_detection': True,    # if True, shows each shoreline detection to the user for validation
    'adjust_detection': True,  # if True, allows user to adjust the postion of each shoreline by changing the threhold
    'save_figure': True,        # if True, saves a figure showing the mapped shoreline for each image
    # [ONLY FOR ADVANCED USERS] shoreline detection parameters:
    'min_beach_area': 200,     # minimum area (in metres^2) for an object to be labelled as a beach
    'buffer_size': 250,         # radius (in metres) for buffer around sandy pixels considered in the shoreline detection
    'min_length_sl': 500,       # minimum length (in metres) of shoreline perimeter to be valid
    'cloud_mask_issue': False,  # switch this parameter to True if sand pixels are masked (in black) on many images  
    'sand_color': 'bright',    # 'default', 'dark' (for grey/black sand beaches) or 'bright' (for white sand beaches)
    # add the inputs defined previously
    'inputs': inputs,
    'projection_epsg': projection_epsg,
    'year_list': years,
    'hausdorff_threshold':3*(10**50)
}



#%% Vegetation Edge Reference Line Digitisation

"""
OPTION 1: Generate a map. Use the line drawing tool on the left-hand side to 
trace along the reference vegetation edge.
"""
#Draw reference line onto the map then run the next cell

Map = geemap.Map(center=[0,0],zoom=2)
Map.add_basemap('HYBRID')
Map

#%%
referenceLine = Map.user_roi.geometries().getInfo()[0]['coordinates']

for i in range(len(referenceLine)):
    #referenceLine[i][0], referenceLine[i][1] = referenceLine[i][1], referenceLine[i][0]
    referenceLine[i] = list(referenceLine[i])

ref_epsg = 4326
referenceLine = Toolbox.convert_epsg(np.array(referenceLine),ref_epsg,image_epsg)
referenceLine = Toolbox.spaced_vertices(referenceLine)

settings['reference_shoreline'] = referenceLine
settings['ref_epsg'] = ref_epsg
settings['max_dist_ref'] = 500

#%% Vegetation Edge Reference Line Load-In

"""
OPTION 2: Load in coordinates of reference line shapefile and format for use in
the veg extraction.
"""

#referenceLineShp = os.path.join(inputs['filepath'], sitename,'StAndrews_refLine.shp')
referenceLineShp = os.path.join(inputs['filepath'], 'StAndrews_refLine.shp')
referenceLineDF = gpd.read_file(referenceLineShp)
refLinex,refLiney = referenceLineDF.geometry[0].coords.xy
# swap latlon coordinates around and format into list
referenceLineList = list([refLinex[i],refLiney[i]] for i in range(len(refLinex)))
# convert to UTM zone for use with the satellite images
ref_epsg = 4326
referenceLine = Toolbox.convert_epsg(np.array(referenceLineList),ref_epsg,image_epsg)
referenceLine = Toolbox.spaced_vertices(referenceLine)

settings['reference_shoreline'] = referenceLine
settings['ref_epsg'] = ref_epsg
settings['max_dist_ref'] = 100


#%% Vegetation Line Extraction

"""
OPTION 1: Run extraction tool and return output dates, lines, filenames and 
image properties.
"""
#get_ipython().run_line_magic('matplotlib', 'qt')
output, output_latlon, output_proj = VegetationLine.extract_veglines(metadata, settings, polygon, dates)

# L5: 44 images, 2:13 (133s) = 0.33 im/s OR 3 s/im
# L8: 20 images (10% of 198), 4:23 (263s) = 0.08 im/s OR 13 s/im
# S2: 335 images, 5:54 (354s) = 0.096 im/s OR 10.4 s/im



