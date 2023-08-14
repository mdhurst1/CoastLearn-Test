#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul 18 13:15:00 2022

@author: fmuir
"""

#%% Imports and Initialisation


import os
import sys
import numpy as np
import pickle
import warnings
from datetime import datetime, timedelta
warnings.filterwarnings("ignore")
import pdb

import seaborn as sns
# sns.set(style='whitegrid') #sns.set(context='notebook', style='darkgrid', palette='deep', font='sans-serif', font_scale=1, color_codes=False, rc=None)
import matplotlib as mpl
from matplotlib import cm
import matplotlib.colors as pltcls
mpl.use('Qt5Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib import gridspec
import matplotlib.patches as mpatches
from matplotlib.collections import PatchCollection
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
plt.ion()

from shapely import geometry
from shapely.geometry import Point, LineString
import rasterio

from Toolshed import Toolbox, Transects, Image_Processing

from sklearn.metrics import mean_squared_error, r2_score

import geemap
import ee

import pandas as pd
import geopandas as gpd

import csv
import math

ee.Initialize()


# SCALING:
# Journal 2-column width: 224pt or 3.11in
# Journal 1-column width: 384pt or 5.33in
# Spacing between: 0.33in
# Journal 2-column page: 6.55in


#%%


def ValidViolin(sitename, ValidationShp,DatesCol,ValidDict,TransectIDs):
    """
    Violin plot showing distances between validation and satellite, for each date of validation line.
    FM Oct 2022

    Parameters
    ----------
    ValidationShp : str
        Path to validation lines shapefile.
    DatesCol : str
        Name of dates column in shapefile.
    ValidDict : dict
        Validation dictionary created from ValidateIntersects().

    """
    
    filepath = os.path.join(os.getcwd(), 'Data', sitename, 'plots')
    if os.path.isdir(filepath) is False:
        os.mkdir(filepath)
    
    ValidGDF = gpd.read_file(ValidationShp)
    violin = []
    violindates = []
    Vdates = ValidGDF[DatesCol].unique()
    for Vdate in Vdates:
        valsatdist = []
        for Tr in range(TransectIDs[0],TransectIDs[1]): 
            if Tr > len(ValidDict['Vdates']): # for when transect values extend beyond what transects exist
                print("check your chosen transect values!")
                return
            if Vdate in ValidDict['Vdates'][Tr]:
                DateIndex = (ValidDict['Vdates'][Tr].index(Vdate))
                # rare occasion where transect intersects valid line but NOT sat line (i.e. no distance between them)
                if ValidDict['valsatdist'][Tr] != []:
                    valsatdist.append(ValidDict['valsatdist'][Tr][DateIndex])
                else:
                    continue
            else:
                continue
        # due to way dates are used, some transects might be missing validation dates so violin collection will be empty
        if valsatdist != []: 
            violin.append(valsatdist)
            violindates.append(Vdate)
    # sort both dates and list of values by date
    if len(violindates) > 1:
        violindatesrt, violinsrt = [list(d) for d in zip(*sorted(zip(violindates, violin), key=lambda x: x[0]))]
    else:
        violindatesrt = violindates
        violinsrt = violin
    df = pd.DataFrame(violinsrt)
    df = df.transpose()
    df.columns = violindatesrt
    
    f = plt.figure(figsize=(14, 6))
    if len(violindates) > 1:
        ax = sns.violinplot(data = df, linewidth=1, palette = 'magma_r', orient='h')
    else:
        ax = sns.violinplot(data = df, linewidth=1, orient='h',)
        
    ax.set(xlabel='Distance$_{satellite - validation}$ (m)', ylabel='Validation line date')
    ax.set_title('Accuracy of Transects ' + str(TransectIDs[0]) + ' to ' + str(TransectIDs[1]))
    
    # set axis limits to rounded maximum value of all violins (either +ve or -ve)
    axlim = round(np.max([abs(df.min().min()),abs(df.max().max())]),-1)
    ax.set_xlim(-axlim, axlim)
    ax.set_xticks([-30,-15,-10,10,15,30],minor=True)
    ax.xaxis.grid(b=True, which='minor',linestyle='--', alpha=0.5)
    median = ax.axvline(df.median().mean(), c='r', ls='-.')
    
    handles = [median]
    labels = ['median' + str(round(df.median().mean(),1)) + 'm']
    ax.legend(handles,labels)
    
    ax.set_axisbelow(False)
    plt.tight_layout()
    
    figpath = os.path.join(filepath,sitename+'_Validation_Satellite_Distances_Violin_'+str(TransectIDs[0])+'to'+str(TransectIDs[1])+'.png')
    plt.savefig(figpath)
    print('figure saved under '+figpath)
    

def SatViolin(sitename, SatGDF, DatesCol,ValidDict,TransectIDs, PlotTitle):
    """
    Violin plot showing distances between validation and satellite, for each date of validation line.
    FM Oct 2022

    Parameters
    ----------
    ValidationShp : str
        Path to validation lines shapefile.
    DatesCol : str
        Name of dates column in shapefile.
    ValidDict : dict
        Validation dictionary created from ValidateIntersects().

    """
    
    filepath = os.path.join(os.getcwd(), 'Data', sitename, 'plots')
    if os.path.isdir(filepath) is False:
        os.mkdir(filepath)
    
       
    violin = []
    violindates = []
    Sdates = SatGDF[DatesCol].unique()
    
    for Sdate in Sdates:
        valsatdist = []
        # for each transect in given range
        for Tr in range(TransectIDs[0],TransectIDs[1]): 
            if Tr > len(ValidDict['dates']): # for when transect values extend beyond what transects exist
                print("check your chosen transect values!")
                return
            if Sdate in ValidDict['dates'][Tr]:
                DateIndex = (ValidDict['dates'][Tr].index(Sdate))
                # rare occasion where transect intersects valid line but NOT sat line (i.e. no distance between them)
                if ValidDict['valsatdist'][Tr] != []:
                    try:
                        valsatdist.append(ValidDict['valsatdist'][Tr][DateIndex])
                    except:
                        pdb.set_trace()
                else:
                    continue
            else:
                continue
        # due to way dates are used, some transects might be missing validation dates so violin collection will be empty
        if valsatdist != []: 
            violin.append(valsatdist)
            violindates.append(Sdate)
    # sort both dates and list of values by date
    if len(violindates) > 1:
        violindatesrt, violinsrt = [list(d) for d in zip(*sorted(zip(violindates, violin), key=lambda x: x[0]))]
    else:
        violindatesrt = violindates
        violinsrt = violin
    df = pd.DataFrame(violinsrt)
    df = df.transpose()
    df.columns = violindatesrt
    
    # initialise matching list of sat names for labelling
    satnames = dict.fromkeys(violindatesrt)
    # for each date in sorted list
    for Sdate in violindatesrt:    
        satmatch = []
        for Tr in range(len(ValidDict['TransectID'])):
            # loop through transects to find matching date from which to find satname
            if Sdate not in ValidDict['dates'][Tr]:
                continue
            else:
                satmatch.append(ValidDict['satname'][Tr][ValidDict['dates'][Tr].index(Sdate)])
        # cycling through transects leads to list of repeating satnames; take the unique entry
        satnames[Sdate] = list(set(satmatch))[0]
    
    f = plt.figure(figsize=(2.6, 4.51), dpi=300)
    sns.set(font_scale=0.5)
    
    patches = []
    rect10 = mpatches.Rectangle((-10, -50), 20, 100)
    rect15 = mpatches.Rectangle((-15, -50), 30, 100)
    patches.append(rect10)
    patches.append(rect15)
    coll=PatchCollection(patches, facecolor="black", alpha=0.05, zorder=0)
    
    sns.set_style("whitegrid", {'axes.grid' : False})
    if len(violindates) > 1:
        # plot stacked violin plots
        ax = sns.violinplot(data = df, linewidth=0, palette = 'magma_r', orient='h', cut=0, inner='quartile')
        ax.add_collection(coll)        # set colour of inner quartiles to white dependent on colour ramp 
        for l in ax.lines:
            l.set_linestyle('-')
            l.set_linewidth(1)
            l.set_color('white')
            
        # cut away bottom halves of violins
        # for violin in ax.collections:
        #     bbox = violin.get_paths()[0].get_extents()
        #     x0, y0, width, height = bbox.bounds
        #     violin.set_clip_path(plt.Rectangle((x0, y0), width, height / 2, transform=ax.transData))
    else:
        ax = sns.violinplot(data = df, linewidth=1, orient='h',cut=0, inner='quartile')
        ax.add_collection(coll)
        
    ax.set(xlabel='Distance$_{satellite - validation}$ (m)', ylabel='Validation line date')
    ax.set_title(PlotTitle)
    
    # set axis limits to rounded maximum value of all violins (either +ve or -ve)
    # round UP to nearest 10
    try:
        axlim = math.ceil(np.max([abs(df.min().min()),abs(df.max().max())]) / 10) * 10
        if axlim < 100:
            ax.set_xlim(-axlim, axlim)
        else:
            ax.set_xlim(-100,100)
    except:
        ax.set_xlim(-100, 100)
    
    # create specific median lines for specific platforms
    medians = []
    labels = []
    # dataframe dates and matching satnames
    satdf = pd.DataFrame(satnames, index=[0])
    # for each platform name
    uniquesats = sorted(set(list(satnames.values())))
    colors = plt.cm.Blues(np.linspace(0.4, 1, len(uniquesats)))
    for satname, c in zip(uniquesats, colors):
        sats = satdf.apply(lambda row: row[row == satname].index, axis=1)
        sats = sats[0].tolist()
        # get dataframe column indices for each date that matches the sat name
        colind = [df.columns.get_loc(sat) for sat in sats]
        # set the date axis label for each date to corresponding satname colour
        [ax.get_yticklabels()[ind].set_color(c) for ind in colind]
        # get median of only the columns that match each sat name
        concatl = []
        for s in sats:
            concatl.append(df[s])
        concatpd = pd.concat(concatl)
        medians.append(ax.axvline(concatpd.median(), c=c, ls='--', lw=1))
        if 'PSScene4Band' in satname:
            satname = 'PS'
        labels.append(satname + ' median = ' + str(round(concatpd.median(),1)) + 'm')
    
    ax.axvline(0, c='k', ls='-', alpha=0.4, lw=0.5)
    ax.legend(medians,labels, loc='lower right')
    
    ax.set_axisbelow(False)
    plt.tight_layout()
    
    figpath = os.path.join(filepath,sitename+'_Validation_Satellite_Distances_Violin_'+str(TransectIDs[0])+'to'+str(TransectIDs[1])+'.png')
    plt.savefig(figpath, dpi=300)
    print('figure saved under '+figpath)
    
    plt.show()
    

def SatPDF(sitename, SatGDF,DatesCol,ValidDict,TransectIDs, PlotTitle):
    """
    Prob density function plot showing distances between validation and satellite, for each date of validation line.
    FM Oct 2022

    Parameters
    ----------
    ValidationShp : str
        Path to validation lines shapefile.
    DatesCol : str
        Name of dates column in shapefile.
    ValidDict : dict
        Validation dictionary created from ValidateIntersects().

    """
    
    filepath = os.path.join(os.getcwd(), 'Data', sitename, 'plots')
    if os.path.isdir(filepath) is False:
        os.mkdir(filepath)
        
    violin = []
    violindates = []
    Sdates = SatGDF[DatesCol].unique()
    
    for Sdate in Sdates:
        valsatdist = []
        # for each transect in given range
        for Tr in range(TransectIDs[0],TransectIDs[1]): 
            if Tr > len(ValidDict['dates']): # for when transect values extend beyond what transects exist
                print("check your chosen transect values!")
                return
            if Sdate in ValidDict['dates'][Tr]:
                DateIndex = (ValidDict['dates'][Tr].index(Sdate))
                # rare occasion where transect intersects valid line but NOT sat line (i.e. no distance between them)
                if ValidDict['valsatdist'][Tr] != []:
                    valsatdist.append(ValidDict['valsatdist'][Tr][DateIndex])
                else:
                    continue
            else:
                continue
        # due to way dates are used, some transects might be missing validation dates so violin collection will be empty
        if valsatdist != []: 
            violin.append(valsatdist)
            violindates.append(Sdate)
    # sort both dates and list of values by date
    if len(violindates) > 1:
        violindatesrt, violinsrt = [list(d) for d in zip(*sorted(zip(violindates, violin), key=lambda x: x[0]))]
    else:
        violindatesrt = violindates
        violinsrt = violin
    df = pd.DataFrame(violinsrt)
    df = df.transpose()
    df.columns = violindatesrt
    
    # initialise matching list of sat names for labelling
    satnames = dict.fromkeys(violindatesrt)
    # for each date in sorted list
    for Sdate in violindatesrt:    
        satmatch = []
        for Tr in range(len(ValidDict['TransectID'])):
            # loop through transects to find matching date from which to find satname
            if Sdate not in ValidDict['dates'][Tr]:
                continue
            else:
                satmatch.append(ValidDict['satname'][Tr][ValidDict['dates'][Tr].index(Sdate)])
        # cycling through transects leads to list of repeating satnames; take the unique entry
        satnames[Sdate] = list(set(satmatch))[0]
    
    f = plt.figure(figsize=(2.6, 4.58), dpi=300)
    ax = f.add_subplot(111)
    sns.set(font_scale=0.6)
    
    patches = []
    rect10 = mpatches.Rectangle((-10, -50), 20, 100)
    rect15 = mpatches.Rectangle((-15, -50), 30, 100)
    patches.append(rect10)
    patches.append(rect15)
    coll=PatchCollection(patches, facecolor="black", alpha=0.1, zorder=0)
    
    sns.axes_style("darkgrid")
    sns.set_style({'axes.facecolor':'#E0E0E0', 'axes.grid' : False})
    if len(violindates) > 1:
                   
        kdecmap = cm.get_cmap('magma_r',len(violindates))
        for i in range(len(violindates)):
            if df.iloc[:,i].isnull().sum() == df.shape[0]:
                kdelabel = None
            else:
                # find name of column for legend labelling (sat date)
                kdelabel = df.columns[i]
            sns.kdeplot(data = df.iloc[:,i], color=kdecmap.colors[i], label=kdelabel, alpha=0.8)
            
        ax.add_collection(coll)
        leg1 = ax.legend(loc='upper left',facecolor='w')
            
    ax.set(xlabel='Distance$_{satellite - validation}$ (m)', ylabel='')
    ax.set_title(PlotTitle)
    plt.yticks([])
    
    # set axis limits to rounded maximum value of all violins (either +ve or -ve)
    # round UP to nearest 10
    try:
        axlim = math.ceil(np.max([abs(df.min().min()),abs(df.max().max())]) / 10) * 10
        ax.set_xlim(-axlim, axlim)
    except:
        ax.set_xlim(-100, 100)
      
    # create specific median lines for specific platforms
    medians = []
    labels = []
    # dataframe dates and matching satnames
    satdf = pd.DataFrame(satnames, index=[0])
    # remove empty columns to make plotting/legends easier
    df = df.dropna(axis=1, how='all')
    commondates=[col for col in df.columns.intersection(satdf.columns)]
    satdf = satdf[commondates]
    
    # for each platform name
    uniquesats = sorted(set(list(satnames.values())))
    colors = plt.cm.Blues(np.linspace(0.4, 1, len(uniquesats)))
    for satname, c in zip(uniquesats, colors):
        try:
            sats = satdf.apply(lambda row: row[row == satname].index, axis=1)
        except:
            print("Can't plot empty Transects with no validation data!")
            continue
        sats = sats[0].tolist()
        # skip calculating satellite median if transects are empty for this satellite
        if sats == []:
            continue
        # get dataframe column indices for each date that matches the sat name
        colind = [df.columns.get_loc(sat) for sat in sats]
        # set the date legend label for each date to corresponding satname colour
        [leg1.get_texts()[ind].set_color(c) for ind in colind]
            
        # get median of only the columns that match each sat name
        concatl = []
        for s in sats:
            concatl.append(df[s])
        concatpd = pd.concat(concatl)
        medians.append(ax.axvline(concatpd.median(), c=c, ls='--', lw=1))
        if 'PSScene4Band' in satname:
            satname = 'PS'
        labels.append(satname + ' $\eta$ = ' + str(round(concatpd.median(),1)) + 'm')
    
    # Overall error as text
    totald = []
    for date in df.columns:
        d = df[date]
        for i,datum in enumerate(d):
            totald.append(datum)

    totald = np.array(totald)
    mse = np.mean(np.power(totald[~np.isnan(totald)], 2))
    mae = np.mean(abs(totald[~np.isnan(totald)]))
    rmse = np.sqrt(mse)
    
    l = Line2D([],[], color='none')
    medians.append(l)
    labels.append('RMSE = ' + str(round(rmse,1)) +'m')
    
    # set legend for median lines  
    ax.axvline(0, c='k', ls='-', alpha=0.4, lw=0.5)
    medleg = ax.legend(medians,labels, loc='upper right',facecolor='w')
    plt.gca().add_artist(leg1)
    
    
    # plt.draw()
    # # get bounding box loc of legend to plot text underneath it
    # p = medleg.get_window_extent()
    # ax.annotate('Hi', (p.p0[1], p.p1[0]), (p.p0[1], p.p1[0]), xycoords='figure pixels', zorder=9, ha='right')    
    ax.set_axisbelow(False)
    plt.tight_layout()
    
    figpath = os.path.join(filepath,sitename+'_Validation_Satellite_Distances_PDF_'+str(TransectIDs[0])+'to'+str(TransectIDs[1])+'.png')
    plt.savefig(figpath, dpi=300)
    print('figure saved under '+figpath)
    
    plt.show()
    
    #mpl.rcParams.update(mpl.rcParamsDefault)

def PlatformViolin(sitename, SatShp,SatCol,ValidDict,TransectIDs, PlotTitle=None):
    """
    Violin plot showing distances between validation and satellite, for each platform used.
    FM Oct 2022

    Parameters
    ----------
    ValidationShp : str
        Path to validation lines shapefile.
    DatesCol : str
        Name of sat column in shapefile.
    ValidDict : dict
        Validation dictionary created from ValidateIntersects().

    """
    
    filepath = os.path.join(os.getcwd(), 'Data', sitename, 'plots')
    if os.path.isdir(filepath) is False:
        os.mkdir(filepath)
    
    if type(SatShp) == str:
        SatGDF = gpd.read_file(SatShp)
    else:
        SatGDF = SatShp
        
    violin = []
    violinsats = []
    Snames = SatGDF[SatCol].unique()
    
    for Sname in Snames:
        valsatdist = []
        # for each transect in given range
        for Tr in range(TransectIDs[0],TransectIDs[1]): 
            if Tr > len(ValidDict[SatCol]): # for when transect values extend beyond what transects exist
                print("check your chosen transect values!")
                return
            if Sname in ValidDict[SatCol][Tr]:
                # need to build list instead of using .index(), as there are multiple occurrences of sat names per transect
                DateIndexes = [i for i, x in enumerate(ValidDict[SatCol][Tr]) if x == Sname]
                # rare occasion where transect intersects valid line but NOT sat line (i.e. no distance between them)
                if ValidDict['valsatdist'][Tr] != []:
                    for DateIndex in DateIndexes:
                        valsatdist.append(ValidDict['valsatdist'][Tr][DateIndex])
                else: # if ValidDict['valsatdist'][Tr] is empty
                    continue
            else: # if Sname isn't in ValidDict[Tr]
                continue
        # due to way dates are used, some transects might be missing validation dates so violin collection will be empty
        if valsatdist != []: 
            violin.append(valsatdist)
            violinsats.append(Sname)
    # sort both dates and list of values by date
    if len(violinsats) > 1:
        violinsatsrt, violinsrt = [list(d) for d in zip(*sorted(zip(violinsats, violin), key=lambda x: x[0]))]
    else:
        violinsatsrt = violinsats
        violinsrt = violin
    df = pd.DataFrame(violinsrt)
    df = df.transpose()
    df.columns = violinsatsrt
       
    f = plt.figure(figsize=(3.31,3.31),dpi=300)
    sns.set(font_scale=0.6)
    
    patches = []
    rect10 = mpatches.Rectangle((-10, -50), 20, 100)
    rect15 = mpatches.Rectangle((-15, -50), 30, 100)
    patches.append(rect10)
    patches.append(rect15)
    coll=PatchCollection(patches, facecolor="black", alpha=0.05, zorder=0)
    colors = plt.cm.Blues(np.linspace(0.4, 1, len(violinsatsrt)))
    
    sns.set_style("whitegrid", {'axes.grid' : False})
    if len(violinsatsrt) > 1:
        # plot stacked violin plots
        ax = sns.violinplot(data = df, linewidth=0, palette = colors, orient='h', cut=0, inner='quartile')
        ax.add_collection(coll)        # set colour of inner quartiles to white dependent on colour ramp 
        for il, l in enumerate(ax.lines):
            l.set_linestyle('--')
            l.set_linewidth(0.7)
            l.set_color('white')
            # overwrite middle line (median) setting to a thicker white line
            for i in range(0,3*len(violinsatsrt))[1::3]:
                if i == il:
                    l.set_linestyle('-')
                    l.set_linewidth(1)
                    l.set_color('white')
    else:
        ax = sns.violinplot(data = df, linewidth=1, orient='h',cut=0, inner='quartile')
        ax.add_collection(coll)
        
    ax.set(xlabel='Distance$_{satellite - validation}$ (m)', ylabel='Satellite image platform')
    if 'PSScene4Band' in violinsatsrt:
        yticklabels = [item.get_text() for item in ax.get_yticklabels()]
        yticklabels[yticklabels.index('PSScene4Band')] = 'PS'
        ax.set_yticklabels(yticklabels)

    if PlotTitle != None:
        ax.set_title(PlotTitle)
    
    # set axis limits to rounded maximum value of all violins (either +ve or -ve)
    # round UP to nearest 10
    axlim = math.ceil(np.max([abs(df.min().min()),abs(df.max().max())]) / 10) * 10
    if axlim < 150:
        ax.set_xlim(-axlim, axlim)
    else:
        ax.set_xlim(-150, 150)
    # ax.set_xticks([-30,-15,-10,10,15,30],minor=True)
    # ax.xaxis.grid(b=True, which='minor',linestyle='--', alpha=0.5)
    
    # # create specific median lines for specific platforms
    legend_elements = []
    ilines = list(range(0,3*len(violinsatsrt))[1::3])
    for i, (satname, iline) in enumerate(zip(violinsatsrt, ilines)):
        satmedian = df[satname].median()
        satMSE = np.mean(df[satname]**2)
        satMAE = np.mean(abs(df[satname]))
        satRMSE = np.sqrt(satMSE)
        leglabel = 'MAE = ' +str(round(satMAE,1))+'m\nRMSE = '+str(round(satRMSE,1))+'m'
        medianlabel = '$\eta_{dist}$ = '+str(round(satmedian,1))+'m'
        LegPatch = Patch( facecolor=colors[i], label = leglabel)
        legend_elements.append(LegPatch)
        if axlim < 150:
            ax.text(-axlim+1, i+0.1, leglabel)
        else:
            ax.text(-149, i+0.1, leglabel)
        medianline = ax.lines[iline].get_data()[1][0]
        ax.text(satmedian, medianline-0.05, medianlabel,ha='center')
    
    ax.axvline(0, c='k', ls='-', alpha=0.4, lw=0.5)
    
    ax.set_axisbelow(False)
    plt.tight_layout()
    
    figpath = os.path.join(filepath,sitename+'_Validation_Satellite_PlatformDistances_Violin_'+str(TransectIDs[0])+'to'+str(TransectIDs[1])+'.png')
    plt.savefig(figpath, dpi=300)
    print('figure saved under '+figpath)
    
    plt.show()

    for i in df.columns:
        print('No. of transects for '+i+' with sub-pixel accuracy:')
        if i == 'L5' or i == 'L7' or i == 'L8' or i == 'L9':
            subpix = (df[i].between(-15,15).sum()/df[i].count())*100
        else:
            subpix = (df[i].between(-10,10).sum()/df[i].count())*100
        print(str(round(subpix,2))+'%')
    
def ThresholdViolin(filepath,sites):
    
    outfilepath = os.path.join(os.getcwd(), 'Data', sites[0], 'plots')
    if os.path.isdir(outfilepath) is False:
        os.mkdir(outfilepath)
      
    violindict = {}
    for site in sites:
        with open(os.path.join(filepath,site ,site+ '_output.pkl'), 'rb') as f:
            outputdict = pickle.load(f)
        violindict[site] = outputdict['vthreshold']
    
    # concat together threshold columns (even if different sizes; fills with nans)
    violinDF = pd.DataFrame(dict([ (k,pd.Series(v)) for k,v in violindict.items()]))
        
    # colors = ['#21A790','#1D37FB'] #West = Teal, East = Blue
    # colors = [pltcls.to_hex(plt.cm.YlGnBu(i)) for i in range(len(violinDF.keys()))]
    ylgnbu = mpl.colormaps['YlGnBu']
    
    colors = ylgnbu(np.linspace((1/(len(violinDF.keys())+1)), 1-(1/(len(violinDF.keys())+1)), len(violinDF.keys())))
    
    # fig = plt.figure(figsize=[1.89,2.64], tight_layout=True)
    fig = plt.figure(figsize=(3.31, 3.31), dpi=300, tight_layout=True)

    # sns.set(font="Arial", font_scale=0.55)
    sns.set(font="Arial", font_scale=0.6)
    sns.set_style("whitegrid", {'axes.grid' : False})
    
    ax = sns.violinplot(data = violinDF, linewidth=0, palette = 'YlGnBu', orient='v', cut=0, inner='quart')
    # change quartile line styles
    for il, l in enumerate(ax.lines):
        l.set_linestyle(':')
        l.set_linewidth(0.5)
        l.set_color('white')
        # overwrite middle line (median) setting to a thicker white line
        for i in range(0,3*len(violinDF.columns))[1::3]:
            if i == il:
                l.set_linestyle('--')
    
    ax.set_xticklabels(['Inner Estuarine','Open Coast'])
    plt.ylabel('NDVI threshold value')
    plt.ylim(0,0.5)
    
    # create legend with medians and data labels for each violin
    legend_elements = []
    for i, key in enumerate(violinDF.keys()):
        # find median value
        satmedian = violinDF[key].median()
        satmin = violinDF[key].min()
        satmax = violinDF[key].max()
        # pass median to legend object
        leglabel = '$\eta_{NDVI}$ = '+str(round(satmedian,2))
        LegPatch = Patch( facecolor=colors[i], label = leglabel)
        legend_elements.append(LegPatch)
        # define data labels for max and min values
        ypos = [satmin-0.018, satmax+0.003]
        textlabels = [str(round(satmin,2)), str(round(satmax,2))]
        # for each min and max value of each violin, label data
        for j in range(len(ypos)):
            ax.text(i, ypos[j], textlabels[j], ha='center')
        
    plt.legend(handles=legend_elements, loc='upper right')
  
    plt.tight_layout()
    outfilename = outfilepath+'/'
    for site in sites:
        outfilename += site+'_'
    outfilename += 'Thresholds_Violin.png'
    plt.savefig(outfilename, dpi=300)
    print('figure saved under '+outfilename)

    plt.show()
    
  


    

    

def CoastPlot(settings, sitename):
    
    filepath = os.path.join(settings['inputs']['filepath'], sitename)
    with open(os.path.join(filepath, sitename + '_output.pkl'), 'rb') as f:
        output = pickle.load(f)
    with open(os.path.join(filepath, sitename + '_output_latlon.pkl'), 'rb') as f:
        output_latlon = pickle.load(f)
    with open(os.path.join(filepath, sitename + '_output_proj.pkl'), 'rb') as f:
        output_proj = pickle.load(f)
      
    # remove duplicate date lines 
    output = Toolbox.remove_duplicates(output) # removes duplicates (images taken on the same date by the same satellite)
    output_latlon = Toolbox.remove_duplicates(output_latlon)
    output_proj = Toolbox.remove_duplicates(output_proj)
    
    # Saves the veglines as shapefiles locally under Veglines.
    direc = os.path.join(filepath, 'veglines')
    geomtype = 'lines'
    name_prefix = 'Data/' + sitename + '/veglines/'

    if os.path.isdir(direc) is False:
        os.mkdir(direc)
   
    # Save output veglines 
    Toolbox.save_shapefiles(output_proj, name_prefix, sitename, settings['projection_epsg'])

    referenceLineShp = os.path.join(settings['inputs']['filepath'], 'StAndrews_refLine.shp')

    # Check if transect pickle file already exists, and if not, make new one
    try:
        with open(os.path.join(filepath, sitename + '_transect_proj' + '.pkl'), 'rb') as f:
            transect_proj = pickle.load(f)
        with open(os.path.join(filepath, sitename + '_transect_latlon' + '.pkl'), 'rb') as f:
            transect_latlon = pickle.load(f)
    except:
        # Set params for cross-shore transects along ref line
        SmoothingWindowSize = 21
        NoSmooths = 100
        TransectSpacing = 10
        DistanceInland = 350
        DistanceOffshore = 350
        BasePath = 'Data/' + sitename + '/veglines'
        # Produces Transects for the reference line
        TransectSpec =  os.path.join(BasePath, 'Transect.shp')
        geo = gpd.read_file(TransectSpec)
        Transects.ProduceTransects(SmoothingWindowSize, NoSmooths, TransectSpacing, DistanceInland, DistanceOffshore, settings['image_epsg'], sitename, BasePath, referenceLineShp)
        transect_latlon, transect_proj = Transects.stuffIntoLibrary(geo, settings['image_epsg'], settings['projection_epsg'], filepath, sitename)
    


    settings['along_dist'] = 50
    cross_distance = Transects.compute_intersection(output_proj, transect_proj, settings, 'vegetation_') 
    
    
    #%% Option 2: Load distances in if they already exist
    
    cross_distance = dict([])
    
    with open('Data/'+sitename+'/vegetation_transect_time_series.csv', newline='') as csvfile:
        spamreader = csv.DictReader(csvfile, delimiter=',', quotechar='|')
        for lines in spamreader:
            for i in range(len(lines)-2):
                cross_distance['Transect_'+str(i+1)] = []
    
    with open('Data/'+sitename+'/vegetation_transect_time_series.csv', newline='') as csvfile:
        spamreader = csv.DictReader(csvfile, delimiter=',', quotechar='|')
        for lines in spamreader:
            for i in range(len(lines)-2):
                transect_name = 'Transect Transect_' + str(i+1)
                try:
                    cross_distance['Transect_'+str(i+1)].append(float(lines[transect_name]))
                except:
                    cross_distance['Transect_'+str(i+1)].append(np.nan)
    
    
    #%% Validation Data compilation into dict
    vegsurveyshp = './Validation/StAndrews_Veg_Edge_combined_singlepart.shp'
    vegsurvey = gpd.read_file(vegsurveyshp)
    
    settings['along_dist'] = 50
    
    # define disctionary of same structure as output_proj
    vegsurvey_proj = dict.fromkeys(output_proj.keys())
    vegsurvey = vegsurvey.sort_values(by=['Date'])
    # fill dates field from geodataframe of survey lines
    vegsurvey_proj['dates'] = list(vegsurvey['Date'])
    vegsurvey_proj['shorelines'] = []
    
    for i in range(len(vegsurvey)):
        # get x and y coords of each survey line (singlepart!)
        vegxs,vegys = vegsurvey.geometry[i].coords.xy
        vegx_points = np.array([])
        vegy_points = np.array([])
        for j in range(len(vegxs)):
            # populate separate arrays of x and y values
            vegx_points = np.append(vegx_points,vegxs[j])
            vegy_points = np.append(vegy_points,vegys[j])
        # concatenate x and y coords together as two columns in array
        vegsurvey_proj['shorelines'].append(np.column_stack([vegx_points,vegy_points])) 
    
    #%%Validation Data intersections
    # perform intersection calculations for each transect       
    veg_cross_distance = Transects.compute_intersection(vegsurvey_proj, transect_proj, settings, 'vegsurveys_') 
    
    #%% Option 2: Load veg survey distances in if they already exist
    
    veg_cross_distance = dict([])
    
    with open('Data/'+sitename+'/vegsurveys_transect_time_series.csv', newline='') as csvfile:
        spamreader = csv.DictReader(csvfile, delimiter=',', quotechar='|')
        for lines in spamreader:
            for i in range(len(lines)-2):
                veg_cross_distance['Transect_'+str(i+1)] = []
    
    with open('Data/'+sitename+'/vegsurveys_transect_time_series.csv', newline='') as csvfile:
        spamreader = csv.DictReader(csvfile, delimiter=',', quotechar='|')
        for lines in spamreader:
            for i in range(len(lines)-2):
                transect_name = 'Transect Transect_' + str(i+1)
                try:
                    veg_cross_distance['Transect_'+str(i+1)].append(float(lines[transect_name]))
                except:
                    veg_cross_distance['Transect_'+str(i+1)].append(np.nan)
    
    #%% Validation statistics
    '''compare distances along transects for each veg survey date matched with its closest satellite date.
    cross_distance is in m'''
    cross_distance['dates'] = output_proj['dates']
    veg_cross_distance['dates'] = vegsurvey_proj['dates']
    
    # Survey dates:
     # '2007-04-04'
     # '2011-05-01'
     # '2012-03-27'
     # '2016-08-01'
     # '2017-07-17'
     # '2018-06-28'
     # '2018-12-11'
    
    # define dict of same structure as cross_distance
    veg_dist = dict.fromkeys(transect_proj.keys())
    
    for trno in range(len(transect_proj)):
        # for each transect, capture single cross_distances to fix date duplicates from singlepart
         veg_dist['Transect_'+str(trno+1)] = []
         for vegdate in list(dict.fromkeys(veg_cross_distance['dates'])):
             # get matching indices for each unique survey date
             indices = [i for i, x in enumerate(veg_cross_distance['dates']) if x == vegdate]
             # repopulate each transect list with the maximum cross distance value for each list of same dates
             try:
                 veg_dist['Transect_'+str(trno+1)].append(np.nanmax(veg_cross_distance['Transect_'+str(trno+1)][indices[0]:indices[-1]+1]))
             except ValueError:
                 veg_dist['Transect_'+str(trno+1)].append(np.nanmax(veg_cross_distance['Transect_'+str(trno+1)][indices[0]]))
    veg_dist['dates'] = list(dict.fromkeys(veg_cross_distance['dates']))
     
    
    #%% Export Transect Intersection Data
    
    
    E_cross_distance = dict([])
    W_cross_distance = dict([])
    sitename = 'StAndrewsEast'
    with open('Data/'+sitename+'/vegetation_transect_time_series.csv', newline='') as csvfile:
        spamreader = csv.DictReader(csvfile, delimiter=',', quotechar='|')
        for lines in spamreader:
            for i in range(len(lines)-2):
                E_cross_distance['Transect_'+str(i+1)] = []
    
    with open('Data/'+sitename+'/vegetation_transect_time_series.csv', newline='') as csvfile:
        spamreader = csv.DictReader(csvfile, delimiter=',', quotechar='|')
        for lines in spamreader:
            for i in range(len(lines)-2):
                transect_name = 'Transect Transect_' + str(i+1)
                try:
                    E_cross_distance['Transect_'+str(i+1)].append(float(lines[transect_name]))
                except:
                    E_cross_distance['Transect_'+str(i+1)].append(np.nan)
                    
    sitename = 'StAndrewsWest'
    with open('Data/'+sitename+'/vegetation_transect_time_series.csv', newline='') as csvfile:
        spamreader = csv.DictReader(csvfile, delimiter=',', quotechar='|')
        for lines in spamreader:
            for i in range(len(lines)-2):
                W_cross_distance['Transect_'+str(i+1)] = []
    
    with open('Data/'+sitename+'/vegetation_transect_time_series.csv', newline='') as csvfile:
        spamreader = csv.DictReader(csvfile, delimiter=',', quotechar='|')
        for lines in spamreader:
            for i in range(len(lines)-2):
                transect_name = 'Transect Transect_' + str(i+1)
                try:
                    W_cross_distance['Transect_'+str(i+1)].append(float(lines[transect_name]))
                except:
                    W_cross_distance['Transect_'+str(i+1)].append(np.nan)
    
    # parse out transect numbers and linestrings
    parsed_transects = [[trno, LineString(transect_proj[trno])] for trno in transect_proj.keys()]
    transect_df = pd.DataFrame(data=parsed_transects,columns=['TrName','geometry'])
    transect_df = transect_df.set_index(transect_df['TrName'])
    transect_gdf = gpd.GeoDataFrame(transect_df, geometry=transect_df['geometry'])
    transect_gdf.index = range(1,transect_gdf.shape[0]+1)
    
    # reformat/transpose to dataframes where index is Transect_x and cols are dates, formatted as 'yyyymmdd'
    W_crossdist_df = pd.DataFrame(W_cross_distance, index=['s'+date.replace('-','') for date in cross_distance['dates']]).T
    
    # vegdist_df = pd.DataFrame(veg_dist, index=['v'+date.replace('-','') for date in veg_dist['dates']]).T
    # vegdist_df = vegdist_df.drop(vegdist_df.index[-1])
    # bothdists_df = pd.concat([crossdist_df,vegdist_df], axis=1)
    # bothdists_df.index = range(1,bothdists_df.shape[0]+1)
    # fulldist_df = pd.concat([bothdists_df, transect_gdf['geometry']],axis=1)
    # fulldist_gdf = gpd.GeoDataFrame(fulldist_df,geometry=fulldist_df['geometry'])
    
    # fulldist_gdf.to_file(os.path.join(os.getcwd()+'/Data/StAndrews_VegSat_TransectDistances.shp'))
            
    
    #%% Plotting - Validation Statistics
    #St Andrews West plotting
    
    #Inner estuary south side
    fig = plt.figure(figsize=[10,8], tight_layout=True)
    #plt.axis('equal')
    plt.grid(linestyle=':', color='0.5')
    plt.title('Edenside, South Side')
    
    
    
    for i,j,c in zip(range(7),[0,1,4,6,10,18,30],['#FCFFA1','#FBB314','#ED641F','#BA3251','#75176A','#2F0B5B','#07070A']):
        veg_x = list([])
        sat_y = list([])
        for trno in range(570,924):
            datelabels = 'Survey date: '+veg_dist['dates'][i]+'; Sat image date: '+cross_distance['dates'][j]
            plt.plot(veg_dist['Transect_'+str(trno+1)][i],cross_distance['Transect_'+str(trno+1)][j],color=c, marker='o', alpha=.5, label=datelabels if trno == 570 else "") #2007
            veg_x.append(veg_dist['Transect_'+str(trno+1)][i])
            sat_y.append(cross_distance['Transect_'+str(trno+1)][j])
        idx = np.isfinite(veg_x) & np.isfinite(sat_y)
        veg_x = np.array(veg_x)[idx]
        sat_y = np.array(sat_y)[idx]
        try:
            m, b = np.polyfit(veg_x, sat_y, 1)
            print(cross_distance['dates'][j]+' RMSE: '+str(mean_squared_error(veg_x, sat_y, squared=False)))
            print(cross_distance['dates'][j]+' R squared: '+str(r2_score(veg_x, sat_y)))
            plt.plot(veg_x,m*veg_x+b, color=c)
        except:
            continue
    plt.plot(range(1000), range(1000), color=(0.3,0.3,0.3,0.5), linestyle='--', label='Expected trend')
    plt.xlabel('Validation edge distance (m)')
    plt.ylabel('Satellite derived edge distance (m)')
    plt.xlim((0,1000))
    plt.ylim((0,1000))
    plt.legend()
    plt.savefig('/media/14TB_RAID_Array/User_Homes/Freya_Muir/PhD/Year2/Outputs/Figures/VegSat_StAndrews_Errors_SEdenside.png')
    plt.show()
    
    
    #Inner estuary north side
    fig = plt.figure(figsize=[10,8], tight_layout=True)
    #plt.axis('equal')
    plt.grid(linestyle=':', color='0.5')
    plt.title('Edenside, North Side')
    for i,j,c in zip(range(7),[0,1,4,6,10,18,30],['#FCFFA1','#FBB314','#ED641F','#BA3251','#75176A','#2F0B5B','#07070A']):
        veg_x = list([])
        sat_y = list([])
        for trno in range(925,1290):
            datelabels = 'Survey date: '+veg_dist['dates'][i]+'; Sat image date: '+cross_distance['dates'][j]
            plt.plot(veg_dist['Transect_'+str(trno+1)][i],cross_distance['Transect_'+str(trno+1)][j],color=c, marker='^', alpha=.5, label=datelabels if trno == 925 else "") #2007
            veg_x.append(veg_dist['Transect_'+str(trno+1)][i])
            sat_y.append(cross_distance['Transect_'+str(trno+1)][j])
        idx = np.isfinite(veg_x) & np.isfinite(sat_y)
        veg_x = np.array(veg_x)[idx]
        sat_y = np.array(sat_y)[idx]
        try:
            m, b = np.polyfit(veg_x, sat_y, 1)
            print(cross_distance['dates'][j]+' RMSE: '+str(mean_squared_error(veg_x, sat_y, squared=False)))
            print(cross_distance['dates'][j]+' R squared: '+str(r2_score(veg_x, sat_y)))
            plt.plot(veg_x,m*veg_x+b,color=c)
        except:
            continue
    plt.plot(range(1000), range(1000), color=(0.3,0.3,0.3,0.5), linestyle='--', label='Expected trend')
    plt.xlabel('Validation edge distance (m)')
    plt.ylabel('Satellite derived edge distance (m)')
    plt.xlim((0,600))
    plt.ylim((0,600))
    plt.legend()
    plt.savefig('/media/14TB_RAID_Array/User_Homes/Freya_Muir/PhD/Year2/Outputs/Figures/VegSat_StAndrews_Errors_NEdenside.png')
    plt.show()
    
    #%% St Andrews East plotting
    
    #St Andrews Peninsula
    fig, ax = plt.subplots(figsize=[10,10], tight_layout=True)
    #plt.axis('equal')
    ax.grid(linestyle=':', color='0.5')
    plt.title('St Andrews Peninsula')
    axins = ax.inset_axes([0.05, 0.55, 0.4, 0.4])
    axins.grid(linestyle=':', color='0.5')
    
    for i,j,c in zip(range(7),[0,1,3,6,9,13,18],['#FCFFA1','#FBB314','#ED641F','#BA3251','#75176A','#2F0B5B','#07070A']):
        veg_x = []
        sat_y = []
        for trno in range(0,600):
            datelabels = 'Survey date: '+veg_dist['dates'][i]+'; Sat image date: '+cross_distance['dates'][j]
            ax.plot(veg_dist['Transect_'+str(trno+1)][i],cross_distance['Transect_'+str(trno+1)][j],color=c, marker='o', alpha=.5, label=datelabels if trno == 0 else "") #2007
            axins.plot(veg_dist['Transect_'+str(trno+1)][i],cross_distance['Transect_'+str(trno+1)][j],color=c, marker='o', alpha=.5, label=datelabels if trno == 0 else "") #2007
            veg_x.append(veg_dist['Transect_'+str(trno+1)][i])
            sat_y.append(cross_distance['Transect_'+str(trno+1)][j])
        idx = np.isfinite(veg_x) & np.isfinite(sat_y)
        veg_x = np.array(veg_x)[idx]
        sat_y = np.array(sat_y)[idx]
        try:
            m, b = np.polyfit(veg_x, sat_y, 1)
            print(cross_distance['dates'][j]+' RMSE: '+str(mean_squared_error(veg_x, sat_y, squared=False)))
            print(cross_distance['dates'][j]+' R squared: '+str(r2_score(veg_x, sat_y)))
            ax.plot(veg_x,m*veg_x+b,color=c)
            axins.plot(veg_x,m*veg_x+b,color=c)
        except:
            continue
    ax.plot(range(1000), range(1000), color=(0.3,0.3,0.3,0.5), linestyle='--', label='Expected trend')
    axins.plot(range(1000), range(1000), color=(0.3,0.3,0.3,0.5), linestyle='--', label='Expected trend')
    plt.xlabel('Validation edge distance (m)')
    plt.ylabel('Satellite derived edge distance (m)')
    ax.set_xlim((0,1000))
    ax.set_ylim((0,1000))
    axins.set_xlim(250,450)
    axins.set_ylim(250,450)
    plt.legend()
    plt.savefig('/media/14TB_RAID_Array/User_Homes/Freya_Muir/PhD/Year2/Outputs/Figures/VegSat_StAndrews_Errors_Peninsula.png')
    plt.show()
    
    # Tentsmuir
    fig = plt.figure(figsize=[10,10], tight_layout=True)
    #plt.axis('equal')
    plt.grid(linestyle=':', color='0.5')
    plt.title('Tentsmuir')
    for i,j,c in zip(range(7),[0,1,3,6,9,13,18],['#FCFFA1','#FBB314','#ED641F','#BA3251','#75176A','#2F0B5B','#07070A']):
        veg_x = list([])
        sat_y = list([])
        for trno in range(1291,1712):
            datelabels = 'Survey date: '+veg_dist['dates'][i]+'; Sat image date: '+cross_distance['dates'][j]
            plt.plot(veg_dist['Transect_'+str(trno+1)][i],cross_distance['Transect_'+str(trno+1)][j],color=c, marker='^', alpha=.5, label=datelabels if trno == 1291 else "") #2007
            veg_x.append(veg_dist['Transect_'+str(trno+1)][i])
            sat_y.append(cross_distance['Transect_'+str(trno+1)][j])
        idx = np.isfinite(veg_x) & np.isfinite(sat_y)
        veg_x = np.array(veg_x)[idx]
        sat_y = np.array(sat_y)[idx]
        try:
            m, b = np.polyfit(veg_x, sat_y, 1)
            print(cross_distance['dates'][j]+' RMSE: '+str(mean_squared_error(veg_x, sat_y, squared=False)))
            print(cross_distance['dates'][j]+' R squared: '+str(r2_score(veg_x, sat_y)))
            plt.plot(veg_x,m*veg_x+b, color=c)
        except:
            continue
    plt.plot(range(1000), range(1000), color=(0.3,0.3,0.3,0.5), linestyle='--', label='Expected trend')
    plt.xlabel('Validation edge distance (m)')
    plt.ylabel('Satellite derived edge distance (m)')
    plt.xlim((200,500))
    plt.ylim((200,500))
    plt.legend()
    plt.savefig('/media/14TB_RAID_Array/User_Homes/Freya_Muir/PhD/Year2/Outputs/Figures/VegSat_StAndrews_Errors_Tentsmuir.png')
    plt.show()
     
    #%% Plotting - Otsu threshold amounts
    from matplotlib import rcParams
    rcParams['font.sans-serif'] = 'Arial'
    
    
    
    sitename = 'StAndrewsWest'
    with open(os.path.join('/media/14TB_RAID_Array/User_Homes/Freya_Muir/PhD/Year2/ModelsFrameworks/CoastWatch-main/Data/',sitename ,sitename+ '_output_proj.pkl'), 'rb') as f:
        output_proj_West = pickle.load(f)
    
    sitename = 'StAndrewsEast'
    with open(os.path.join('/media/14TB_RAID_Array/User_Homes/Freya_Muir/PhD/Year2/ModelsFrameworks/CoastWatch-main/Data/',sitename ,sitename+ '_output_proj.pkl'), 'rb') as f:
        output_proj_East = pickle.load(f)
    
    output_proj_East['dates_dt'] = [datetime.strptime(date, '%Y-%m-%d') for date in output_proj_East['dates']]
    
    output_proj_West['dates_dt'] = [datetime.strptime(date, '%Y-%m-%d') for date in output_proj_West['dates']]
    
    colors = ['#21A790','#1D37FB'] #West = Teal, East = Blue
    fig = plt.figure(figsize=[16,6], tight_layout=True)
    
    plt.plot(output_proj_West['dates_dt'],output_proj_West['Otsu_threshold'], 'o', color=colors[0],  label='West/Inner estuarine')
    
    plt.plot(output_proj_East['dates_dt'],output_proj_East['Otsu_threshold'], 'o', color=colors[1], label='East/Open coast')
    
    plt.xlabel('Date (yyyy-mm-dd)')
    plt.ylabel('Otsu threshold value (1)')
    plt.legend(loc='upper left')
    plt.gca().xaxis.set_major_locator(mpl.dates.YearLocator())
    plt.xticks(rotation=270)
    plt.savefig('/media/14TB_RAID_Array/User_Homes/Freya_Muir/PhD/Year2/Outputs/Figures/VegSat_StAndrews_OtsuThresholds.png')
    plt.show()
    
    # combine these different collections into a list
    East_West_Otsu = [output_proj_West['Otsu_threshold'], output_proj_East['Otsu_threshold']]
    
    fig, ax = plt.subplots(figsize=[8,8], tight_layout=True)
    violin = ax.violinplot(East_West_Otsu)
    
    for patch, color in zip(violin['bodies'], colors):
        patch.set_color(color)
        for partname in list(violin.keys())[1:]:
            vp = violin[partname]
            vp.set_edgecolor(colors)
            #vp.set_linewidth(1)
    
    plt.xticks([1,2], ['West/Inner estuarine','East/Open coast'])    
    plt.ylabel('NDVI threshold')
    plt.savefig('/media/14TB_RAID_Array/User_Homes/Freya_Muir/PhD/Year2/Outputs/Figures/VegSat_StAndrews_OtsuThresholdsViolin.png')
    plt.show()
    
    
    #%%Plotting - Vegetation Edge
    
    #Displays produced lines/transects
    
    fig = plt.figure(figsize=[15,8], tight_layout=True)
    plt.axis('equal')
    plt.xlabel('Eastings')
    plt.ylabel('Northings')
    #plt.xlim(509000,513000)
    #plt.ylim(6244400,6247250)
    plt.grid(linestyle=':', color='0.5')
    for i in range(len(output_proj['shorelines'])):
        sl = output_proj['shorelines'][i]
        date = output_proj['dates'][i]
        plt.plot(sl[:,0], sl[:,1], '.')#, label=date.strptime('%d-%m-%Y'))
     
    for i,key in enumerate(list(transect_proj.keys())):
        plt.plot(transect_proj[key][0,0],transect_proj[key][0,1], 'bo', ms=5)
        plt.plot(transect_proj[key][:,0],transect_proj[key][:,1],'k-',lw=1)
        #plt.text(transects_proj[key][0,0]-100, transects_proj[key][0,1]+100, key, va='center', ha='right', bbox=dict(boxstyle="square", ec='k',fc='w'))
    plt.show()
    
    # #%% Mapping of Results
    
    # """
    # Creates map object centred at ROI + adds compiled satellite image as base-layer
    # """
    # #Map = geemap.Map(center=[polygon[0][0][1],polygon[0][0][0]],zoom=12)
    # #Map.add_basemap('HYBRID')
    
    # #Generates colours for lines to be drawn in. Check out https://seaborn.pydata.org/tutorial/color_palettes.html for colour options...
    # palette = sns.color_palette("bright", len(output['shorelines']))
    # palette = palette.as_hex()
    
    # #Choose 'points' or 'lines' for the layer geometry
    # geomtype = 'points'
    
    # for i in range(len(output['shorelines'])):
    #     shore = dict([])
    #     if len(output_latlon['shorelines'][i])==0:
    #         continue
    #     shore = {'dates':[output_latlon['dates'][i]], 'shorelines':[output_latlon['shorelines'][i]], 'filename':[output_latlon['filename'][i]], 'cloud_cover':[output_latlon['cloud_cover'][i]], 'idx':[output_latlon['idx'][i]], 'Otsu_threshold':[output_latlon['Otsu_threshold'][i]], 'satname':[output_latlon['satname'][i]]}
    #     gdf = Toolbox.output_to_gdf(shore, geomtype)
    #     Line = geemap.geopandas_to_ee(gdf, geodesic=True)
    #     Map.addLayer(Line,{'color': str(palette[i])},'coast'+str(i))
    
    # Map
    
    # In[ ]:
    
    
    #Displays the transects
    
    for i,key in enumerate(list(transect_proj.keys())):
        plt.plot(transect_proj[key][0,0],transect_proj[key][0,1], 'bo', ms=5)
        plt.plot(transect_proj[key][:,0],transect_proj[key][:,1],'k-',lw=1)
        #plt.text(transects_proj[key][0,0]-100, transects_proj[key][0,1]+100, key, va='center', ha='right', bbox=dict(boxstyle="square", ec='k',fc='w'))
    plt.show()
    
    
    # In[ ]:
    
    
    #Displays the lines
    
    fig = plt.figure(figsize=[15,8])
    plt.axis('equal')
    plt.xlabel('Eastings')
    plt.ylabel('Northings')
    plt.grid(linestyle=':', color='0.5')
    for i in range(len(output_proj['shorelines'])):
        sl = output_proj['shorelines'][i]
        date = output_proj['dates'][i]
        plt.plot(sl[:,0], sl[:,1], '.')#, label=date.strftime('%d-%m-%Y'))
    plt.legend()
    plt.show()
    
    
    # In[ ]:
    
    
    #Cross-distance plots for ALL transects (do not bother if you are considering a LOT of transects)
    
    fig = plt.figure(figsize=[15,12], tight_layout=True)
    gs = gridspec.GridSpec(len(cross_distance),2, wspace=0.035, width_ratios=[3,1])
    gs.update(left=0.05, right=0.95, bottom=0.05, top=0.95, hspace=0.2)
    for i,key in enumerate(cross_distance.keys()):
        if np.all(np.isnan(cross_distance[key])):
            continue
        ax = fig.add_subplot(gs[i,0])
        ax.grid(linestyle=':', color='0.5')
        ax.set_ylim([-100,110])
        ax.plot(output['dates'], cross_distance[key]- np.nanmedian(cross_distance[key]), '-o', ms=6, mfc='w')
        #ax.set_ylabel('distance [m]', fontsize=12)
        ax.text(0.5,0.95, key, bbox=dict(boxstyle="square", ec='k',fc='w'), ha='center',va='top', transform=ax.transAxes, fontsize=14)
        if i!= len(cross_distance.keys())-1:
            ax.set_xticklabels('')
        ax = fig.add_subplot(gs[i,1])
        #ax.set_xlim([-50,50])
        ax.set_xlim([0,0.015])
        sns.distplot(cross_distance[key]- np.nanmedian(cross_distance[key]), bins=10, color="b", ax=ax, vertical=True)
        ax.set_yticklabels('')
        if i!= len(cross_distance.keys())-1:
            ax.set_xticklabels('')
    fig.text(0.01, 0.5, 'Cross-Shore Distance / m', va='center', rotation='vertical', fontsize=12)
    
    
    # In[ ]:
    
    
    transect_range = [[0, 50],[51,110],[111,180],[181,240],[241,len(output['dates'])-1]]
    #transect_colour = sns.color_palette("bright", len(transect_range))
    colours = ['#ff0000','#0084ff','#ff00f7','#00fa0c', '#ffb300', '#00ffcc','#7b00ff']
    transect_colour = colours
    
    
    # In[ ]:
    
    
    #In this cell, you can iterate on transect range (we will use these ranges to analyse specific regions of the edge)
    
    fig = plt.figure(figsize=[15,8], tight_layout=True)
    plt.axis('equal')
    plt.xlabel('Eastings')
    plt.ylabel('Northings')
    #plt.xlim(509000,513000)
    #plt.ylim(6244400,6247250)
    plt.grid(linestyle=':', color='0.5')
    for i in range(len(output_proj['shorelines'])):
        sl = output_proj['shorelines'][i]
        date = output_proj['dates'][i]
        plt.plot(sl[:,0], sl[:,1], '.')#, label=date.strptime('%d-%m-%Y'))
    
    if transect_range == 'full':
        transect_range = [[0,len(transect_proj.keys())]]   
    
    for i,key in enumerate(list(transect_proj.keys())):
        for j in range(len(transect_range)):
            if transect_range[j][0] <= i <= transect_range[j][1]:
                plt.plot(transect_proj[key][0,0],transect_proj[key][0,1], 'bo', ms=5,color=transect_colour[j])
                plt.plot(transect_proj[key][:,0],transect_proj[key][:,1],'k-',lw=1,color=transect_colour[j])
        #plt.text(transects_proj[key][0,0]-100, transects_proj[key][0,1]+100, key, va='center', ha='right', bbox=dict(boxstyle="square", ec='k',fc='w'))
    
    plt.savefig('Data/' + sitename + '/jpg_files/transectsFull', bbox_inches='tight')
      
    plt.show()
    
    
    # In[ ]:
    
    
    #Year by Year
    
    from matplotlib import rcParams
    rcParams.update({'figure.autolayout': True})
    
    fig, axs = plt.subplots(len(transect_range),sharex=True,figsize=(10, 12))
    fig.text(0.005, 0.5, "Average Yearly Vegetation Cross-Edge Distance / m", va='center', rotation='vertical', fontsize=12)
    
    for i in range(len(transect_range)):
        axs[i].set_title("Transects:"+str(transect_range[i][0])+"-"+str(transect_range[i][1]),backgroundcolor=transect_colour[i],color='white')
        if i != len(transect_range)-1:
            axs[i].xaxis.set_visible(False)
        if i == len(transect_range)-1:
            axs[i].set_xlabel("Year", fontsize=12)
        for j in range(transect_range[i][0],transect_range[i][1]):
            KEY = 'Transect_'+str(j+1)
            try:
                a, b, c, d, e = Toolbox.Separate_TimeSeries_year(cross_distance, output_proj, KEY)
                NaN_mask = np.isfinite(e)
                axs[i].plot(np.array(d)[NaN_mask],np.array(e)[NaN_mask])
            except:
                continue
                
    plt.savefig('Data/' + sitename + '/jpg_files/avgYearlyVegPosition', bbox_inches='tight')
    
    
    # In[ ]:
    
    
    #Good at looking at seasonal patterns. Takes a while.
    
    #plt.figure(figsize=[15,12])
    
    months = ["Jan", "Feb", "Mar", "Apr", "May", "June", "July", "Aug", "Sept", "Oct", "Nov", "Dec"]
    Month_dict = {"Jan":[], "Feb":[], "Mar":[], "Apr":[], "May":[], "June":[], "July":[], "Aug":[], "Sept":[], "Oct":[], "Nov":[], "Dec":[]}
    
    Total_Month_Arr = []
    test1 = []
    test2 = []
    
    fig, axs = plt.subplots(len(transect_range),sharex=True,figsize=(10, 12))
    
    for l in range(len(transect_range)):
    
        for i in range(transect_range[l][0],transect_range[l][1]):
            KEY = 'Transect_'+str(i+1)
            try:
                a, b, c, d, e = Toolbox.Separate_TimeSeries_month(cross_distance, output_proj,KEY)
    
                zipped_lists = zip(d,e)
                s = sorted(zipped_lists)
                tuples = zip(s)
    
                new_d = []
                new_e = []
    
                sortedList = [list(tuple) for tuple in  tuples]
    
                for v in range(len(sortedList)):
                    new_d.append(sortedList[v][0][0])
                    new_e.append(sortedList[v][0][1])
    
                month_arr = []
                for j in range(len(d)):
                    a = datetime.strptime(str(new_d[j]),'%m')
                    month_arr.append(a.strftime('%b'))
    
                axs[l].scatter(month_arr,new_e,label=KEY)
                test1.append(new_d)
                test2.append(new_e)
            except:
                continue
    
        avg = []
        st_err = []
        Total_organised = []
        temp = []
    
        for k in range(len(test2[0])):
            for h in range(len(test2)):
                temp.append(test2[h][k])
            Total_organised.append(temp)
            avg.append(np.nanmean(temp))
            st_err.append(np.nanstd(temp)/(len(temp)**0.5))
            temp = []
        
        Total_Month_Arr.append(Total_organised)
        
        #plt.errorbar(month_arr,avg, yerr=st_err, color='k')
        axs[l].scatter(month_arr,avg, color='k', s=50, marker='x')
    
        #plt.legend()
        axs[l].set_title("Transects:"+str(transect_range[l][0])+"-"+str(transect_range[l][1]),backgroundcolor=transect_colour[l],color='white')
    
    fig.text(0.01,0.5,"Averaged Monthly Vegetation Cross-Edge Distance / m", va='center', rotation='vertical')
    plt.xlabel("Month")
    
    plt.savefig('Data/' + sitename + '/jpg_files/monthScatter', bbox_inches='tight')
    
    
    # In[ ]:
    
    
    fig, axs = plt.subplots(len(transect_range),sharex=True,figsize=(10, 12))
    
    for j in range(len(Total_Month_Arr)):
        
        axs[j].set_title("Transects:"+str(transect_range[j][0])+"-"+str(transect_range[j][1]),backgroundcolor=transect_colour[j],color='white')
        axs[j].boxplot(Total_Month_Arr[j],notch=True, flierprops = dict(marker='o', markersize=8, linestyle='none', markeredgecolor='r'))
    
    fig.text(0.01,0.5,"Averaged Monthly Vegetation Cross-Edge Distance / m", va='center', rotation='vertical')
    plt.xticks(new_d, month_arr)
    
    plt.savefig('Data/' + sitename + '/jpg_files/monthBox', bbox_inches='tight')
    
    plt.show()
    
    
    # In[ ]:
    
    
    def adjacent_values(vals, q1, q3):
        upper_adjacent_value = q3 + (q3 - q1) * 1.5
        upper_adjacent_value = np.clip(upper_adjacent_value, q3, vals[-1])
    
        lower_adjacent_value = q1 - (q3 - q1) * 1.5
        lower_adjacent_value = np.clip(lower_adjacent_value, vals[0], q1)
        return lower_adjacent_value, upper_adjacent_value
    
    
    def set_axis_style(ax, labels):
        ax.xaxis.set_tick_params(direction='out')
        ax.xaxis.set_ticks_position('bottom')
        ax.set_xticks(np.arange(1, len(labels) + 1))
        ax.set_xticklabels(labels)
        ax.set_xlim(0.25, len(labels) + 0.75)
        #ax.set_xlabel('Sample name')
    
    fig, axs = plt.subplots(len(transect_range),sharex=True,figsize=(10, 12))
    
    for j in range(len(Total_Month_Arr)):
        
        axs[j].set_title("Transects:"+str(transect_range[j][0])+"-"+str(transect_range[j][1]),backgroundcolor=transect_colour[j],color='white')
        parts = axs[j].violinplot(Total_Month_Arr[j], showmeans=False, showmedians=False, showextrema=False)
    
        for pc in parts['bodies']:
            pc.set_facecolor(transect_colour[j])
            pc.set_edgecolor('black')
            pc.set_alpha(0.7)
    
        quartile1, medians, quartile3 = np.percentile(Total_Month_Arr[j], [25, 50, 75], axis=1)
        whiskers = np.array([
            adjacent_values(sorted_array, q1, q3)
            for sorted_array, q1, q3 in zip(Total_Month_Arr[j], quartile1, quartile3)])
        whiskers_min, whiskers_max = whiskers[:, 0], whiskers[:, 1]
    
        inds = np.arange(1, len(medians) + 1)
        axs[j].scatter(inds, medians, marker='o', color='white', s=30, zorder=3)
        axs[j].vlines(inds, quartile1, quartile3, color='k', linestyle='-', lw=5)
        axs[j].vlines(inds, whiskers_min, whiskers_max, color='k', linestyle='-', lw=1)
        
        if j == len(Total_Month_Arr):
            set_axis_style(axs[j], month_arr)
    
    fig.text(0.005,0.5,"Averaged Monthly Vegetation Cross-Edge Distance / m", va='center', rotation='vertical')
    plt.xticks(new_d, month_arr)
    
    plt.savefig('Data/' + sitename + '/jpg_files/monthViolin', bbox_inches='tight')
    
    plt.show()
    
    
    # In[ ]:
    
    
    #array of colours for each of the averaged transect-analysis (add more if need be)
    colours = ['#ff0000','#0084ff','#ff00f7','#00fa0c', '#ffb300', '#00ffcc','#7b00ff']
    
    Rows = []
    
    with open('Data/'+sitename+'/vegetation_transect_time_series.csv', newline='') as csvfile:
        spamreader = csv.reader(csvfile, delimiter=',', quotechar='|')
        for row in spamreader:
            Rows.append(row[2:])
    
    cross_distance_condensed, standard_err_condensed, transect_condensed, Dates = Transects.transect_compiler(Rows, transect_proj, 100, output)
    
    
    # In[ ]:
    
    
    fig = plt.figure(figsize=[15,12], tight_layout=True)
    gs = gridspec.GridSpec(len(cross_distance_condensed),2, wspace=0.035, width_ratios=[4,1])
    gs.update(left=0.05, right=0.95, bottom=0.05, top=0.95, hspace=0.05)
    
    x = np.arange(datetime(1984,1,1), datetime(2022,1,1), timedelta(days=100)).astype(str)
    y = [0]*139
    
    for i,key in enumerate(cross_distance_condensed.keys()):
        
        if np.all(np.isnan(cross_distance_condensed[key])):
            continue
            
        ax = fig.add_subplot(gs[i,0])
        ax.grid(linestyle=':', color='0.5')
        ax.set_ylim([min(cross_distance_condensed[key]- np.nanmedian(cross_distance_condensed[key]))-5,max(cross_distance_condensed[key]- np.nanmedian(cross_distance_condensed[key]))+5])
        dates = mpl.dates.date2num(Dates[key])
        ax.errorbar(dates, cross_distance_condensed[key]- np.nanmedian(cross_distance_condensed[key]), yerr = standard_err_condensed[key],fmt='-o',ecolor= 'k', color= colours[i], ms=6, mfc='w')
    
        ax.fill_between(dates, 0, cross_distance_condensed[key]- np.nanmedian(cross_distance_condensed[key]),alpha=0.5,color=colours[i])
        ax.set_title("Transects:"+str(transect_range[i][0])+"-"+str(transect_range[i][1]),backgroundcolor=transect_colour[i],color='white')
    
        ax.set_xticklabels(['1982','1986','1992','1998','2004','2010','2016','2020','2014','2018','2022'])
    
        if i!= len(cross_distance_condensed.keys())-1:
            ax.set_xticklabels('')
    
        ax = fig.add_subplot(gs[i,1])
        ax.set_xlim([0,0.020])
        sns.distplot(cross_distance_condensed[key]- np.nanmedian(cross_distance_condensed[key]), bins=10, color=colours[i], ax=ax, vertical=True)
        ax.set_yticklabels('')
        
        if i!= len(cross_distance_condensed.keys())-1:
            ax.set_xticklabels('')
            ax.set_xlabel('')
            
    fig.text(0.01, 0.5, 'Cross Vegetation-Edge Distance / m', va='center', rotation='vertical', fontsize=13.8)
    
    plt.savefig('Data/' + sitename + '/jpg_files/crossEdgeDistances', bbox_inches='tight')
    
    
    # In[ ]:
    
    
    ref_sl_conv = Toolbox.convert_epsg(settings['reference_shoreline'], 32630, 27700)[:,:-1]
    
    vv = dict([])
    vv['1'] = [ref_sl_conv]
    
    #Displays produced lines/transects
    
    fig = plt.figure()#figsize=[15,8], tight_layout=True)
    plt.axis('equal')
    #plt.xlabel('Eastings')
    #plt.ylabel('Northings')
    plt.xlim(min(vv['1'][0][:,0]),max(vv['1'][0][:,0]))
    plt.xticks('')
    plt.yticks('')
    plt.ylim(min(vv['1'][0][:,1])-50,max(vv['1'][0][:,1])+50)
    plt.grid(linestyle=':', color='0.5')
    for i in range(len(vv['1'])):
        sl = vv['1'][i]
        date = vv['1'][i]
        plt.plot(sl[:,0], sl[:,1], '.', color='k')#, label=date.strptime('%d-%m-%Y'))
     
    for i,key in enumerate(list(transect_condensed.keys())):
        plt.plot(transect_condensed[key][0,0],transect_condensed[key][0,1], 'bo', color= colours[i], ms=5)
        plt.plot(transect_condensed[key][:,0],transect_condensed[key][:,1],'k-', color= colours[i], lw=1)
        plt.text(transect_condensed[key][1][0],transect_condensed[key][1][1], key, va='bottom', ha='right', bbox=dict(boxstyle="round", ec='k',fc='w'), fontsize=10)
    
    plt.savefig('Data/' + sitename + '/jpg_files/refEdge_Transects', bbox_inches='tight')
    plt.show()
    
    
    # In[ ]:
    
    
    Big_percent = []
    for i,key in enumerate(cross_distance_condensed.keys()):
        cross = cross_distance_condensed[key]- np.nanmedian(cross_distance_condensed[key])
        percent_diff = []
        for j in range(len(cross)):
            percent_diff.append(100*(cross[j]-cross[0])/cross[0])
            
        Big_percent.append(percent_diff)
    
    
    # In[ ]:
    
    
    Big_arr = []
    Big_datearr = []
    
    Year = [[]]*(2021-1984)
    
    for i in range(len(transect_range)):
        percent_diff = []
        dist_arr = []
        date_arr = []
        for j in range(transect_range[i][0],transect_range[i][1]):
            KEY = 'Transect_'+str(j+1)
            try:
                a, b, c, d, e = Toolbox.Separate_TimeSeries_year(cross_distance, output_proj, KEY)
                NaN_mask = np.isfinite(e)
                dist_arr.append(list(np.array(e)[NaN_mask]))
                date_arr.append(list(np.array(d)[NaN_mask]))
                #percent_diff.append()
            except:
                continue
        Big_arr.append(dist_arr)
        Big_datearr.append(date_arr)
    
    
    # In[ ]:
    
    
    Big_Percent = []
    
    for j in range(len(Big_arr)):
        Medium_Percent_TransectRange = []
        Year = dict([])
        for i in range(len(Big_arr[j])):
            for k in range(len(Big_arr[j][i])):
                index = Big_datearr[j][i][k]-1984
                if Year.get(str(index)) == None:
                    Year[str(index)] = []
                Year[str(index)].append(Big_arr[j][i][index-1])
                #print(len(Year[index-1]))
        List_year = []
        for v, key in enumerate(Year):
            List_year.append(np.mean(Year[key]))
        Big_Percent.append(List_year[1:])
        #print(List_year)
    
    
    # In[ ]:
    
    
    Barz = []
    
    for i in range(len(Big_Percent)):
        temp = []
        for j in range(len(Big_Percent[i])):
            temp.append(100*(Big_Percent[i][j]-Big_Percent[i][0])/Big_Percent[i][0])
        Barz.append(temp)
    
    
    # In[ ]:
    
    
    fig, axs = plt.subplots(figsize=(10, 12))
    for i in range(len(Barz)):
        axs.barh(np.arange(len(Barz[i]))+(i/5), Barz[i], align='center',height= 0.2,color=colours[i],label='Transects: '+str(transect_range[i][0])+"-"+str(transect_range[i][1]) )
    axs.plot([0]*100,np.arange(0,37,0.37),'-.',color='k')
    axs.set_xlabel("% Change Since 1984")
    #axs.set_xlim(-500,500)
    axs.set_yticks(np.arange(0,37,1))
    axs.set_yticklabels(list(np.array(d)[NaN_mask]))
    fig.text(0.25,0.85,"Accretion (Relative to 1984)")
    fig.text(0.58,0.85,"Erosion (Relative to 1984)")
    axs.legend(loc='lower right')
    for i in range(37):
        axs.plot(np.arange(-500,500,10),[i-0.1]*100,'-.',color='k',alpha=0.7,linewidth=0.45)
    fig.savefig(os.path.join('Data/' + sitename + '/jpg_files/barBreakdown.jpg'), dpi=150)
    plt.show()
    
#%%
# Plot transects with transition zone of veg to compare harsh vs dissipative boundaries




#%%

"""
%% Produces Transects and Coast shape-files for the reference line

SmoothingWindowSize = 21
NoSmooths = 100
TransectSpacing = 10
DistanceInland = 350
DistanceOffshore = 350
BasePath = 'Data/' + sitename + '/Veglines'


Transects.ProduceTransects(SmoothingWindowSize, NoSmooths, TransectSpacing, DistanceInland, DistanceOffshore, image_epsg, sitename, BasePath, referenceLineShp)

#(Optional) Produces transects for all produced lines
#Transects.ProduceTransects_all(SmoothingWindowSize, NoSmooths, TransectSpacing, DistanceInland, DistanceOffshore, projection_epsg, BasePath)


%% **Option 1**: Defines all transects in a library.

TransectSpec =  os.path.join(BasePath, 'Transect.shp')
geo = gpd.read_file(TransectSpec)

transect_latlon, transect_proj = Transects.stuffIntoLibrary(geo, image_epsg, projection_epsg, filepath, sitename)


%% **Option 2**: Or just load them if already produced


with open(os.path.join(filepath, sitename + '_transect_proj' + '.pkl'), 'rb') as f:
    transect_proj = pickle.load(f)
with open(os.path.join(filepath, sitename + '_transect_latlon' + '.pkl'), 'rb') as f:
    transect_latlon = pickle.load(f)


%% Option 1: Compute distances of shorelines along transects


settings['along_dist'] = 50
cross_distance = Transects.compute_intersection(output_proj, transect_proj, settings, 'vegetation_') 


%% Option 2: Load distances in if they already exist

cross_distance = dict([])

with open('Data/'+sitename+'/vegetation_transect_time_series.csv', newline='') as csvfile:
    spamreader = csv.DictReader(csvfile, delimiter=',', quotechar='|')
    for lines in spamreader:
        for i in range(len(lines)-2):
            cross_distance['Transect_'+str(i+1)] = []

with open('Data/'+sitename+'/vegetation_transect_time_series.csv', newline='') as csvfile:
    spamreader = csv.DictReader(csvfile, delimiter=',', quotechar='|')
    for lines in spamreader:
        for i in range(len(lines)-2):
            transect_name = 'Transect Transect_' + str(i+1)
            try:
                cross_distance['Transect_'+str(i+1)].append(float(lines[transect_name]))
            except:
                cross_distance['Transect_'+str(i+1)].append(np.nan)


#%% Validation Data compilation into dict
vegsurveyshp = './Validation/StAndrews_Veg_Edge_combined_singlepart.shp'
vegsurvey = gpd.read_file(vegsurveyshp)

settings['along_dist'] = 50

# define disctionary of same structure as output_proj
vegsurvey_proj = dict.fromkeys(output_proj.keys())
vegsurvey = vegsurvey.sort_values(by=['Date'])
# fill dates field from geodataframe of survey lines
vegsurvey_proj['dates'] = list(vegsurvey['Date'])
vegsurvey_proj['shorelines'] = []

for i in range(len(vegsurvey)):
    # get x and y coords of each survey line (singlepart!)
    vegxs,vegys = vegsurvey.geometry[i].coords.xy
    vegx_points = np.array([])
    vegy_points = np.array([])
    for j in range(len(vegxs)):
        # populate separate arrays of x and y values
        vegx_points = np.append(vegx_points,vegxs[j])
        vegy_points = np.append(vegy_points,vegys[j])
    # concatenate x and y coords together as two columns in array
    vegsurvey_proj['shorelines'].append(np.column_stack([vegx_points,vegy_points])) 

#%%Validation Data intersections
# perform intersection calculations for each transect       
veg_cross_distance = Transects.compute_intersection(vegsurvey_proj, transect_proj, settings, 'vegsurveys_') 

#%% Option 2: Load veg survey distances in if they already exist

veg_cross_distance = dict([])

with open('Data/'+sitename+'/vegsurveys_transect_time_series.csv', newline='') as csvfile:
    spamreader = csv.DictReader(csvfile, delimiter=',', quotechar='|')
    for lines in spamreader:
        for i in range(len(lines)-2):
            veg_cross_distance['Transect_'+str(i+1)] = []

with open('Data/'+sitename+'/vegsurveys_transect_time_series.csv', newline='') as csvfile:
    spamreader = csv.DictReader(csvfile, delimiter=',', quotechar='|')
    for lines in spamreader:
        for i in range(len(lines)-2):
            transect_name = 'Transect Transect_' + str(i+1)
            try:
                veg_cross_distance['Transect_'+str(i+1)].append(float(lines[transect_name]))
            except:
                veg_cross_distance['Transect_'+str(i+1)].append(np.nan)

#%% Validation statistics
'''compare distances along transects for each veg survey date matched with its closest satellite date.
cross_distance is in m'''
cross_distance['dates'] = output_proj['dates']
veg_cross_distance['dates'] = vegsurvey_proj['dates']

# Survey dates:
 # '2007-04-04'
 # '2011-05-01'
 # '2012-03-27'
 # '2016-08-01'
 # '2017-07-17'
 # '2018-06-28'
 # '2018-12-11'

# define dict of same structure as cross_distance
veg_dist = dict.fromkeys(transect_proj.keys())

for trno in range(len(transect_proj)):
    # for each transect, capture single cross_distances to fix date duplicates from singlepart
     veg_dist['Transect_'+str(trno+1)] = []
     for vegdate in list(dict.fromkeys(veg_cross_distance['dates'])):
         # get matching indices for each unique survey date
         indices = [i for i, x in enumerate(veg_cross_distance['dates']) if x == vegdate]
         # repopulate each transect list with the maximum cross distance value for each list of same dates
         try:
             veg_dist['Transect_'+str(trno+1)].append(np.nanmax(veg_cross_distance['Transect_'+str(trno+1)][indices[0]:indices[-1]+1]))
         except ValueError:
             veg_dist['Transect_'+str(trno+1)].append(np.nanmax(veg_cross_distance['Transect_'+str(trno+1)][indices[0]]))
veg_dist['dates'] = list(dict.fromkeys(veg_cross_distance['dates']))
 

#%% Export Transect Intersection Data


E_cross_distance = dict([])
W_cross_distance = dict([])
sitename = 'StAndrewsEast'
with open('Data/'+sitename+'/vegetation_transect_time_series.csv', newline='') as csvfile:
    spamreader = csv.DictReader(csvfile, delimiter=',', quotechar='|')
    for lines in spamreader:
        for i in range(len(lines)-2):
            E_cross_distance['Transect_'+str(i+1)] = []

with open('Data/'+sitename+'/vegetation_transect_time_series.csv', newline='') as csvfile:
    spamreader = csv.DictReader(csvfile, delimiter=',', quotechar='|')
    for lines in spamreader:
        for i in range(len(lines)-2):
            transect_name = 'Transect Transect_' + str(i+1)
            try:
                E_cross_distance['Transect_'+str(i+1)].append(float(lines[transect_name]))
            except:
                E_cross_distance['Transect_'+str(i+1)].append(np.nan)
                
sitename = 'StAndrewsWest'
with open('Data/'+sitename+'/vegetation_transect_time_series.csv', newline='') as csvfile:
    spamreader = csv.DictReader(csvfile, delimiter=',', quotechar='|')
    for lines in spamreader:
        for i in range(len(lines)-2):
            W_cross_distance['Transect_'+str(i+1)] = []

with open('Data/'+sitename+'/vegetation_transect_time_series.csv', newline='') as csvfile:
    spamreader = csv.DictReader(csvfile, delimiter=',', quotechar='|')
    for lines in spamreader:
        for i in range(len(lines)-2):
            transect_name = 'Transect Transect_' + str(i+1)
            try:
                W_cross_distance['Transect_'+str(i+1)].append(float(lines[transect_name]))
            except:
                W_cross_distance['Transect_'+str(i+1)].append(np.nan)

# parse out transect numbers and linestrings
parsed_transects = [[trno, LineString(transect_proj[trno])] for trno in transect_proj.keys()]
transect_df = pd.DataFrame(data=parsed_transects,columns=['TrName','geometry'])
transect_df = transect_df.set_index(transect_df['TrName'])
transect_gdf = gpd.GeoDataFrame(transect_df, geometry=transect_df['geometry'])
transect_gdf.index = range(1,transect_gdf.shape[0]+1)

# reformat/transpose to dataframes where index is Transect_x and cols are dates, formatted as 'yyyymmdd'
W_crossdist_df = pd.DataFrame(W_cross_distance, index=['s'+date.replace('-','') for date in cross_distance['dates']]).T

vegdist_df = pd.DataFrame(veg_dist, index=['v'+date.replace('-','') for date in veg_dist['dates']]).T
vegdist_df = vegdist_df.drop(vegdist_df.index[-1])
bothdists_df = pd.concat([crossdist_df,vegdist_df], axis=1)
bothdists_df.index = range(1,bothdists_df.shape[0]+1)
fulldist_df = pd.concat([bothdists_df, transect_gdf['geometry']],axis=1)
fulldist_gdf = gpd.GeoDataFrame(fulldist_df,geometry=fulldist_df['geometry'])

fulldist_gdf.to_file(os.path.join(os.getcwd()+'/Data/StAndrews_VegSat_TransectDistances.shp'))
        

#%% Plotting - Validation Statistics
#St Andrews West plotting

#Inner estuary south side
fig = plt.figure(figsize=[10,8], tight_layout=True)
#plt.axis('equal')
plt.grid(linestyle=':', color='0.5')
plt.title('Edenside, South Side')



for i,j,c in zip(range(7),[0,1,4,6,10,18,30],['#FCFFA1','#FBB314','#ED641F','#BA3251','#75176A','#2F0B5B','#07070A']):
    veg_x = list([])
    sat_y = list([])
    for trno in range(570,924):
        datelabels = 'Survey date: '+veg_dist['dates'][i]+'; Sat image date: '+cross_distance['dates'][j]
        plt.plot(veg_dist['Transect_'+str(trno+1)][i],cross_distance['Transect_'+str(trno+1)][j],color=c, marker='o', alpha=.5, label=datelabels if trno == 570 else "") #2007
        veg_x.append(veg_dist['Transect_'+str(trno+1)][i])
        sat_y.append(cross_distance['Transect_'+str(trno+1)][j])
    idx = np.isfinite(veg_x) & np.isfinite(sat_y)
    veg_x = np.array(veg_x)[idx]
    sat_y = np.array(sat_y)[idx]
    try:
        m, b = np.polyfit(veg_x, sat_y, 1)
        print(cross_distance['dates'][j]+' RMSE: '+str(mean_squared_error(veg_x, sat_y, squared=False)))
        print(cross_distance['dates'][j]+' R squared: '+str(r2_score(veg_x, sat_y)))
        plt.plot(veg_x,m*veg_x+b, color=c)
    except:
        continue
plt.plot(range(1000), range(1000), color=(0.3,0.3,0.3,0.5), linestyle='--', label='Expected trend')
plt.xlabel('Validation edge distance (m)')
plt.ylabel('Satellite derived edge distance (m)')
plt.xlim((0,1000))
plt.ylim((0,1000))
plt.legend()
plt.savefig('/media/14TB_RAID_Array/User_Homes/Freya_Muir/PhD/Year2/Outputs/Figures/VegSat_StAndrews_Errors_SEdenside.png')
plt.show()


#Inner estuary north side
fig = plt.figure(figsize=[10,8], tight_layout=True)
#plt.axis('equal')
plt.grid(linestyle=':', color='0.5')
plt.title('Edenside, North Side')
for i,j,c in zip(range(7),[0,1,4,6,10,18,30],['#FCFFA1','#FBB314','#ED641F','#BA3251','#75176A','#2F0B5B','#07070A']):
    veg_x = list([])
    sat_y = list([])
    for trno in range(925,1290):
        datelabels = 'Survey date: '+veg_dist['dates'][i]+'; Sat image date: '+cross_distance['dates'][j]
        plt.plot(veg_dist['Transect_'+str(trno+1)][i],cross_distance['Transect_'+str(trno+1)][j],color=c, marker='^', alpha=.5, label=datelabels if trno == 925 else "") #2007
        veg_x.append(veg_dist['Transect_'+str(trno+1)][i])
        sat_y.append(cross_distance['Transect_'+str(trno+1)][j])
    idx = np.isfinite(veg_x) & np.isfinite(sat_y)
    veg_x = np.array(veg_x)[idx]
    sat_y = np.array(sat_y)[idx]
    try:
        m, b = np.polyfit(veg_x, sat_y, 1)
        print(cross_distance['dates'][j]+' RMSE: '+str(mean_squared_error(veg_x, sat_y, squared=False)))
        print(cross_distance['dates'][j]+' R squared: '+str(r2_score(veg_x, sat_y)))
        plt.plot(veg_x,m*veg_x+b,color=c)
    except:
        continue
plt.plot(range(1000), range(1000), color=(0.3,0.3,0.3,0.5), linestyle='--', label='Expected trend')
plt.xlabel('Validation edge distance (m)')
plt.ylabel('Satellite derived edge distance (m)')
plt.xlim((0,600))
plt.ylim((0,600))
plt.legend()
plt.savefig('/media/14TB_RAID_Array/User_Homes/Freya_Muir/PhD/Year2/Outputs/Figures/VegSat_StAndrews_Errors_NEdenside.png')
plt.show()

#%% St Andrews East plotting

#St Andrews Peninsula
fig, ax = plt.subplots(figsize=[10,10], tight_layout=True)
#plt.axis('equal')
ax.grid(linestyle=':', color='0.5')
plt.title('St Andrews Peninsula')
axins = ax.inset_axes([0.05, 0.55, 0.4, 0.4])
axins.grid(linestyle=':', color='0.5')

for i,j,c in zip(range(7),[0,1,3,6,9,13,18],['#FCFFA1','#FBB314','#ED641F','#BA3251','#75176A','#2F0B5B','#07070A']):
    veg_x = []
    sat_y = []
    for trno in range(0,600):
        datelabels = 'Survey date: '+veg_dist['dates'][i]+'; Sat image date: '+cross_distance['dates'][j]
        ax.plot(veg_dist['Transect_'+str(trno+1)][i],cross_distance['Transect_'+str(trno+1)][j],color=c, marker='o', alpha=.5, label=datelabels if trno == 0 else "") #2007
        axins.plot(veg_dist['Transect_'+str(trno+1)][i],cross_distance['Transect_'+str(trno+1)][j],color=c, marker='o', alpha=.5, label=datelabels if trno == 0 else "") #2007
        veg_x.append(veg_dist['Transect_'+str(trno+1)][i])
        sat_y.append(cross_distance['Transect_'+str(trno+1)][j])
    idx = np.isfinite(veg_x) & np.isfinite(sat_y)
    veg_x = np.array(veg_x)[idx]
    sat_y = np.array(sat_y)[idx]
    try:
        m, b = np.polyfit(veg_x, sat_y, 1)
        print(cross_distance['dates'][j]+' RMSE: '+str(mean_squared_error(veg_x, sat_y, squared=False)))
        print(cross_distance['dates'][j]+' R squared: '+str(r2_score(veg_x, sat_y)))
        ax.plot(veg_x,m*veg_x+b,color=c)
        axins.plot(veg_x,m*veg_x+b,color=c)
    except:
        continue
ax.plot(range(1000), range(1000), color=(0.3,0.3,0.3,0.5), linestyle='--', label='Expected trend')
axins.plot(range(1000), range(1000), color=(0.3,0.3,0.3,0.5), linestyle='--', label='Expected trend')
plt.xlabel('Validation edge distance (m)')
plt.ylabel('Satellite derived edge distance (m)')
ax.set_xlim((0,1000))
ax.set_ylim((0,1000))
axins.set_xlim(250,450)
axins.set_ylim(250,450)
plt.legend()
plt.savefig('/media/14TB_RAID_Array/User_Homes/Freya_Muir/PhD/Year2/Outputs/Figures/VegSat_StAndrews_Errors_Peninsula.png')
plt.show()

# Tentsmuir
fig = plt.figure(figsize=[10,10], tight_layout=True)
#plt.axis('equal')
plt.grid(linestyle=':', color='0.5')
plt.title('Tentsmuir')
for i,j,c in zip(range(7),[0,1,3,6,9,13,18],['#FCFFA1','#FBB314','#ED641F','#BA3251','#75176A','#2F0B5B','#07070A']):
    veg_x = list([])
    sat_y = list([])
    for trno in range(1291,1712):
        datelabels = 'Survey date: '+veg_dist['dates'][i]+'; Sat image date: '+cross_distance['dates'][j]
        plt.plot(veg_dist['Transect_'+str(trno+1)][i],cross_distance['Transect_'+str(trno+1)][j],color=c, marker='^', alpha=.5, label=datelabels if trno == 1291 else "") #2007
        veg_x.append(veg_dist['Transect_'+str(trno+1)][i])
        sat_y.append(cross_distance['Transect_'+str(trno+1)][j])
    idx = np.isfinite(veg_x) & np.isfinite(sat_y)
    veg_x = np.array(veg_x)[idx]
    sat_y = np.array(sat_y)[idx]
    try:
        m, b = np.polyfit(veg_x, sat_y, 1)
        print(cross_distance['dates'][j]+' RMSE: '+str(mean_squared_error(veg_x, sat_y, squared=False)))
        print(cross_distance['dates'][j]+' R squared: '+str(r2_score(veg_x, sat_y)))
        plt.plot(veg_x,m*veg_x+b, color=c)
    except:
        continue
plt.plot(range(1000), range(1000), color=(0.3,0.3,0.3,0.5), linestyle='--', label='Expected trend')
plt.xlabel('Validation edge distance (m)')
plt.ylabel('Satellite derived edge distance (m)')
plt.xlim((200,500))
plt.ylim((200,500))
plt.legend()
plt.savefig('/media/14TB_RAID_Array/User_Homes/Freya_Muir/PhD/Year2/Outputs/Figures/VegSat_StAndrews_Errors_Tentsmuir.png')
plt.show()
 
#%% Plotting - Otsu threshold amounts
from matplotlib import rcParams
rcParams['font.sans-serif'] = 'Arial'



sitename = 'StAndrewsWest'
with open(os.path.join('/media/14TB_RAID_Array/User_Homes/Freya_Muir/PhD/Year2/ModelsFrameworks/CoastWatch-main/Data/',sitename ,sitename+ '_output_proj.pkl'), 'rb') as f:
    output_proj_West = pickle.load(f)

sitename = 'StAndrewsEast'
with open(os.path.join('/media/14TB_RAID_Array/User_Homes/Freya_Muir/PhD/Year2/ModelsFrameworks/CoastWatch-main/Data/',sitename ,sitename+ '_output_proj.pkl'), 'rb') as f:
    output_proj_East = pickle.load(f)

output_proj_East['dates_dt'] = [datetime.strptime(date, '%Y-%m-%d') for date in output_proj_East['dates']]

output_proj_West['dates_dt'] = [datetime.strptime(date, '%Y-%m-%d') for date in output_proj_West['dates']]

colors = ['#21A790','#1D37FB'] #West = Teal, East = Blue
fig = plt.figure(figsize=[16,6], tight_layout=True)

plt.plot(output_proj_West['dates_dt'],output_proj_West['Otsu_threshold'], 'o', color=colors[0],  label='West/Inner estuarine')

plt.plot(output_proj_East['dates_dt'],output_proj_East['Otsu_threshold'], 'o', color=colors[1], label='East/Open coast')

plt.xlabel('Date (yyyy-mm-dd)')
plt.ylabel('Otsu threshold value (1)')
plt.legend(loc='upper left')
plt.gca().xaxis.set_major_locator(matplotlib.dates.YearLocator())
plt.xticks(rotation=270)
plt.savefig('/media/14TB_RAID_Array/User_Homes/Freya_Muir/PhD/Year2/Outputs/Figures/VegSat_StAndrews_OtsuThresholds.png')
plt.show()

# combine these different collections into a list
East_West_Otsu = [output_proj_West['Otsu_threshold'], output_proj_East['Otsu_threshold']]

fig, ax = plt.subplots(figsize=[8,8], tight_layout=True)
violin = ax.violinplot(East_West_Otsu)

for patch, color in zip(violin['bodies'], colors):
    patch.set_color(color)
    for partname in list(violin.keys())[1:]:
        vp = violin[partname]
        vp.set_edgecolor(colors)
        #vp.set_linewidth(1)

plt.xticks([1,2], ['West/Inner estuarine','East/Open coast'])    
plt.ylabel('NDVI threshold')
plt.savefig('/media/14TB_RAID_Array/User_Homes/Freya_Muir/PhD/Year2/Outputs/Figures/VegSat_StAndrews_OtsuThresholdsViolin.png')
plt.show()

#%% Validation MSE

      


#%%Plotting - Vegetation Edge

#Displays produced lines/transects

fig = plt.figure(figsize=[15,8], tight_layout=True)
plt.axis('equal')
plt.xlabel('Eastings')
plt.ylabel('Northings')
#plt.xlim(509000,513000)
#plt.ylim(6244400,6247250)
plt.grid(linestyle=':', color='0.5')
for i in range(len(output_proj['shorelines'])):
    sl = output_proj['shorelines'][i]
    date = output_proj['dates'][i]
    plt.plot(sl[:,0], sl[:,1], '.')#, label=date.strptime('%d-%m-%Y'))
 
for i,key in enumerate(list(transect_proj.keys())):
    plt.plot(transect_proj[key][0,0],transect_proj[key][0,1], 'bo', ms=5)
    plt.plot(transect_proj[key][:,0],transect_proj[key][:,1],'k-',lw=1)
    #plt.text(transects_proj[key][0,0]-100, transects_proj[key][0,1]+100, key, va='center', ha='right', bbox=dict(boxstyle="square", ec='k',fc='w'))
plt.show()

#%% Mapping of Results
#%% Save output veglines


#Saves the veglines as shapefiles locally under Veglines.
direc = os.path.join(filepath, 'veglines')
geomtype = 'lines'
name_prefix = 'Data/' + sitename + '/veglines/'

if os.path.isdir(direc) is False:
    os.mkdir(direc)

Toolbox.save_shapefiles(output_proj, name_prefix, sitename, projection_epsg)

# initialise the ref variable for storing line info in
#ref_line = np.delete(settings['reference_shoreline'],2,1)
#ref = {'dates':['3000-12-30'], 'shorelines':[ref_line], 'filename':[0], 'cloud_cover':[0], 'geoaccuracy':[0], 'idx':[0], 'Otsu_threshold':[0], 'satname':[0]}
#Toolbox.save_shapefiles(ref, geomtype, name_prefix, sitename)

#

# In[ ]:


fig, axs = plt.subplots(figsize=(10, 12))
for i in range(len(Barz)):
    axs.barh(np.arange(len(Barz[i]))+(i/5), Barz[i], align='center',height= 0.2,color=colours[i],label='Transects: '+str(transect_range[i][0])+"-"+str(transect_range[i][1]) )
axs.plot([0]*100,np.arange(0,37,0.37),'-.',color='k')
axs.set_xlabel("% Change Since 1984")
#axs.set_xlim(-500,500)
axs.set_yticks(np.arange(0,37,1))
axs.set_yticklabels(list(np.array(d)[NaN_mask]))
fig.text(0.25,0.85,"Accretion (Relative to 1984)")
fig.text(0.58,0.85,"Erosion (Relative to 1984)")
axs.legend(loc='lower right')
for i in range(37):
    axs.plot(np.arange(-500,500,10),[i-0.1]*100,'-.',color='k',alpha=0.7,linewidth=0.45)
fig.savefig(os.path.join('Data/' + sitename + '/jpg_files/barBreakdown.jpg'), dpi=150)
plt.show()


# ## Analysis - Comparison with Field Data




# Creates map object centred at ROI + adds compiled satellite image as base-layer

#Map = geemap.Map(center=[polygon[0][0][1],polygon[0][0][0]],zoom=12)
#Map.add_basemap('HYBRID')

#Generates colours for lines to be drawn in. Check out https://seaborn.pydata.org/tutorial/color_palettes.html for colour options...
palette = sns.color_palette("bright", len(output['shorelines']))
palette = palette.as_hex()

#Choose 'points' or 'lines' for the layer geometry
geomtype = 'points'

for i in range(len(output['shorelines'])):
    shore = dict([])
    if len(output_latlon['shorelines'][i])==0:
        continue
    shore = {'dates':[output_latlon['dates'][i]], 'shorelines':[output_latlon['shorelines'][i]], 'filename':[output_latlon['filename'][i]], 'cloud_cover':[output_latlon['cloud_cover'][i]], 'idx':[output_latlon['idx'][i]], 'Otsu_threshold':[output_latlon['Otsu_threshold'][i]], 'satname':[output_latlon['satname'][i]]}
    gdf = Toolbox.output_to_gdf(shore, geomtype)
    Line = geemap.geopandas_to_ee(gdf, geodesic=True)
    Map.addLayer(Line,{'color': str(palette[i])},'coast'+str(i))

Map

# In[ ]:


#Displays the transects

for i,key in enumerate(list(transect_proj.keys())):
    plt.plot(transect_proj[key][0,0],transect_proj[key][0,1], 'bo', ms=5)
    plt.plot(transect_proj[key][:,0],transect_proj[key][:,1],'k-',lw=1)
    #plt.text(transects_proj[key][0,0]-100, transects_proj[key][0,1]+100, key, va='center', ha='right', bbox=dict(boxstyle="square", ec='k',fc='w'))
plt.show()


# In[ ]:


#Displays the lines

fig = plt.figure(figsize=[15,8])
plt.axis('equal')
plt.xlabel('Eastings')
plt.ylabel('Northings')
plt.grid(linestyle=':', color='0.5')
for i in range(len(output_proj['shorelines'])):
    sl = output_proj['shorelines'][i]
    date = output_proj['dates'][i]
    plt.plot(sl[:,0], sl[:,1], '.')#, label=date.strftime('%d-%m-%Y'))
plt.legend()
plt.show()


# In[ ]:


#Cross-distance plots for ALL transects (do not bother if you are considering a LOT of transects)

fig = plt.figure(figsize=[15,12], tight_layout=True)
gs = gridspec.GridSpec(len(cross_distance),2, wspace=0.035, width_ratios=[3,1])
gs.update(left=0.05, right=0.95, bottom=0.05, top=0.95, hspace=0.2)
for i,key in enumerate(cross_distance.keys()):
    if np.all(np.isnan(cross_distance[key])):
        continue
    ax = fig.add_subplot(gs[i,0])
    ax.grid(linestyle=':', color='0.5')
    ax.set_ylim([-100,110])
    ax.plot(output['dates'], cross_distance[key]- np.nanmedian(cross_distance[key]), '-o', ms=6, mfc='w')
    #ax.set_ylabel('distance [m]', fontsize=12)
    ax.text(0.5,0.95, key, bbox=dict(boxstyle="square", ec='k',fc='w'), ha='center',va='top', transform=ax.transAxes, fontsize=14)
    if i!= len(cross_distance.keys())-1:
        ax.set_xticklabels('')
    ax = fig.add_subplot(gs[i,1])
    #ax.set_xlim([-50,50])
    ax.set_xlim([0,0.015])
    sns.distplot(cross_distance[key]- np.nanmedian(cross_distance[key]), bins=10, color="b", ax=ax, vertical=True)
    ax.set_yticklabels('')
    if i!= len(cross_distance.keys())-1:
        ax.set_xticklabels('')
fig.text(0.01, 0.5, 'Cross-Shore Distance / m', va='center', rotation='vertical', fontsize=12)


# In[ ]:


transect_range = [[0, 50],[51,110],[111,180],[181,240],[241,len(output['dates'])-1]]
#transect_colour = sns.color_palette("bright", len(transect_range))
colours = ['#ff0000','#0084ff','#ff00f7','#00fa0c', '#ffb300', '#00ffcc','#7b00ff']
transect_colour = colours


# In[ ]:


#In this cell, you can iterate on transect range (we will use these ranges to analyse specific regions of the edge)

fig = plt.figure(figsize=[15,8], tight_layout=True)
plt.axis('equal')
plt.xlabel('Eastings')
plt.ylabel('Northings')
#plt.xlim(509000,513000)
#plt.ylim(6244400,6247250)
plt.grid(linestyle=':', color='0.5')
for i in range(len(output_proj['shorelines'])):
    sl = output_proj['shorelines'][i]
    date = output_proj['dates'][i]
    plt.plot(sl[:,0], sl[:,1], '.')#, label=date.strptime('%d-%m-%Y'))

if transect_range == 'full':
    transect_range = [[0,len(transect_proj.keys())]]   

for i,key in enumerate(list(transect_proj.keys())):
    for j in range(len(transect_range)):
        if transect_range[j][0] <= i <= transect_range[j][1]:
            plt.plot(transect_proj[key][0,0],transect_proj[key][0,1], 'bo', ms=5,color=transect_colour[j])
            plt.plot(transect_proj[key][:,0],transect_proj[key][:,1],'k-',lw=1,color=transect_colour[j])
    #plt.text(transects_proj[key][0,0]-100, transects_proj[key][0,1]+100, key, va='center', ha='right', bbox=dict(boxstyle="square", ec='k',fc='w'))

plt.savefig('Data/' + sitename + '/jpg_files/transectsFull', bbox_inches='tight')
  
plt.show()


# In[ ]:


#Year by Year

from matplotlib import rcParams
rcParams.update({'figure.autolayout': True})

fig, axs = plt.subplots(len(transect_range),sharex=True,figsize=(10, 12))
fig.text(0.005, 0.5, "Average Yearly Vegetation Cross-Edge Distance / m", va='center', rotation='vertical', fontsize=12)

for i in range(len(transect_range)):
    axs[i].set_title("Transects:"+str(transect_range[i][0])+"-"+str(transect_range[i][1]),backgroundcolor=transect_colour[i],color='white')
    if i != len(transect_range)-1:
        axs[i].xaxis.set_visible(False)
    if i == len(transect_range)-1:
        axs[i].set_xlabel("Year", fontsize=12)
    for j in range(transect_range[i][0],transect_range[i][1]):
        KEY = 'Transect_'+str(j+1)
        try:
            a, b, c, d, e = Toolbox.Separate_TimeSeries_year(cross_distance, output_proj, KEY)
            NaN_mask = np.isfinite(e)
            axs[i].plot(np.array(d)[NaN_mask],np.array(e)[NaN_mask])
        except:
            continue
            
plt.savefig('Data/' + sitename + '/jpg_files/avgYearlyVegPosition', bbox_inches='tight')


# In[ ]:


#Good at looking at seasonal patterns. Takes a while.

#plt.figure(figsize=[15,12])

months = ["Jan", "Feb", "Mar", "Apr", "May", "June", "July", "Aug", "Sept", "Oct", "Nov", "Dec"]
Month_dict = {"Jan":[], "Feb":[], "Mar":[], "Apr":[], "May":[], "June":[], "July":[], "Aug":[], "Sept":[], "Oct":[], "Nov":[], "Dec":[]}

Total_Month_Arr = []
test1 = []
test2 = []

fig, axs = plt.subplots(len(transect_range),sharex=True,figsize=(10, 12))

for l in range(len(transect_range)):

    for i in range(transect_range[l][0],transect_range[l][1]):
        KEY = 'Transect_'+str(i+1)
        try:
            a, b, c, d, e = Toolbox.Separate_TimeSeries_month(cross_distance, output_proj,KEY)

            zipped_lists = zip(d,e)
            s = sorted(zipped_lists)
            tuples = zip(s)

            new_d = []
            new_e = []

            sortedList = [list(tuple) for tuple in  tuples]

            for v in range(len(sortedList)):
                new_d.append(sortedList[v][0][0])
                new_e.append(sortedList[v][0][1])

            month_arr = []
            for j in range(len(d)):
                a = datetime.strptime(str(new_d[j]),'%m')
                month_arr.append(a.strftime('%b'))

            axs[l].scatter(month_arr,new_e,label=KEY)
            test1.append(new_d)
            test2.append(new_e)
        except:
            continue

    avg = []
    st_err = []
    Total_organised = []
    temp = []

    for k in range(len(test2[0])):
        for h in range(len(test2)):
            temp.append(test2[h][k])
        Total_organised.append(temp)
        avg.append(np.nanmean(temp))
        st_err.append(np.nanstd(temp)/(len(temp)**0.5))
        temp = []
    
    Total_Month_Arr.append(Total_organised)
    
    #plt.errorbar(month_arr,avg, yerr=st_err, color='k')
    axs[l].scatter(month_arr,avg, color='k', s=50, marker='x')

    #plt.legend()
    axs[l].set_title("Transects:"+str(transect_range[l][0])+"-"+str(transect_range[l][1]),backgroundcolor=transect_colour[l],color='white')

fig.text(0.01,0.5,"Averaged Monthly Vegetation Cross-Edge Distance / m", va='center', rotation='vertical')
plt.xlabel("Month")

plt.savefig('Data/' + sitename + '/jpg_files/monthScatter', bbox_inches='tight')


# In[ ]:


fig, axs = plt.subplots(len(transect_range),sharex=True,figsize=(10, 12))

for j in range(len(Total_Month_Arr)):
    
    axs[j].set_title("Transects:"+str(transect_range[j][0])+"-"+str(transect_range[j][1]),backgroundcolor=transect_colour[j],color='white')
    axs[j].boxplot(Total_Month_Arr[j],notch=True, flierprops = dict(marker='o', markersize=8, linestyle='none', markeredgecolor='r'))

fig.text(0.01,0.5,"Averaged Monthly Vegetation Cross-Edge Distance / m", va='center', rotation='vertical')
plt.xticks(new_d, month_arr)

plt.savefig('Data/' + sitename + '/jpg_files/monthBox', bbox_inches='tight')

plt.show()


# In[ ]:


def adjacent_values(vals, q1, q3):
    upper_adjacent_value = q3 + (q3 - q1) * 1.5
    upper_adjacent_value = np.clip(upper_adjacent_value, q3, vals[-1])

    lower_adjacent_value = q1 - (q3 - q1) * 1.5
    lower_adjacent_value = np.clip(lower_adjacent_value, vals[0], q1)
    return lower_adjacent_value, upper_adjacent_value


def set_axis_style(ax, labels):
    ax.xaxis.set_tick_params(direction='out')
    ax.xaxis.set_ticks_position('bottom')
    ax.set_xticks(np.arange(1, len(labels) + 1))
    ax.set_xticklabels(labels)
    ax.set_xlim(0.25, len(labels) + 0.75)
    #ax.set_xlabel('Sample name')

fig, axs = plt.subplots(len(transect_range),sharex=True,figsize=(10, 12))

for j in range(len(Total_Month_Arr)):
    
    axs[j].set_title("Transects:"+str(transect_range[j][0])+"-"+str(transect_range[j][1]),backgroundcolor=transect_colour[j],color='white')
    parts = axs[j].violinplot(Total_Month_Arr[j], showmeans=False, showmedians=False, showextrema=False)

    for pc in parts['bodies']:
        pc.set_facecolor(transect_colour[j])
        pc.set_edgecolor('black')
        pc.set_alpha(0.7)

    quartile1, medians, quartile3 = np.percentile(Total_Month_Arr[j], [25, 50, 75], axis=1)
    whiskers = np.array([
        adjacent_values(sorted_array, q1, q3)
        for sorted_array, q1, q3 in zip(Total_Month_Arr[j], quartile1, quartile3)])
    whiskers_min, whiskers_max = whiskers[:, 0], whiskers[:, 1]

    inds = np.arange(1, len(medians) + 1)
    axs[j].scatter(inds, medians, marker='o', color='white', s=30, zorder=3)
    axs[j].vlines(inds, quartile1, quartile3, color='k', linestyle='-', lw=5)
    axs[j].vlines(inds, whiskers_min, whiskers_max, color='k', linestyle='-', lw=1)
    
    if j == len(Total_Month_Arr):
        set_axis_style(axs[j], month_arr)

fig.text(0.005,0.5,"Averaged Monthly Vegetation Cross-Edge Distance / m", va='center', rotation='vertical')
plt.xticks(new_d, month_arr)

plt.savefig('Data/' + sitename + '/jpg_files/monthViolin', bbox_inches='tight')

plt.show()


# In[ ]:


#array of colours for each of the averaged transect-analysis (add more if need be)
colours = ['#ff0000','#0084ff','#ff00f7','#00fa0c', '#ffb300', '#00ffcc','#7b00ff']

Rows = []

with open('Data/'+sitename+'/vegetation_transect_time_series.csv', newline='') as csvfile:
    spamreader = csv.reader(csvfile, delimiter=',', quotechar='|')
    for row in spamreader:
        Rows.append(row[2:])

cross_distance_condensed, standard_err_condensed, transect_condensed, Dates = Transects.transect_compiler(Rows, transect_proj, 100, output)


# In[ ]:


fig = plt.figure(figsize=[15,12], tight_layout=True)
gs = gridspec.GridSpec(len(cross_distance_condensed),2, wspace=0.035, width_ratios=[4,1])
gs.update(left=0.05, right=0.95, bottom=0.05, top=0.95, hspace=0.05)

x = np.arange(datetime(1984,1,1), datetime(2022,1,1), timedelta(days=100)).astype(str)
y = [0]*139

for i,key in enumerate(cross_distance_condensed.keys()):
    
    if np.all(np.isnan(cross_distance_condensed[key])):
        continue
        
    ax = fig.add_subplot(gs[i,0])
    ax.grid(linestyle=':', color='0.5')
    ax.set_ylim([min(cross_distance_condensed[key]- np.nanmedian(cross_distance_condensed[key]))-5,max(cross_distance_condensed[key]- np.nanmedian(cross_distance_condensed[key]))+5])
    dates = matplotlib.dates.date2num(Dates[key])
    ax.errorbar(dates, cross_distance_condensed[key]- np.nanmedian(cross_distance_condensed[key]), yerr = standard_err_condensed[key],fmt='-o',ecolor= 'k', color= colours[i], ms=6, mfc='w')

    ax.fill_between(dates, 0, cross_distance_condensed[key]- np.nanmedian(cross_distance_condensed[key]),alpha=0.5,color=colours[i])
    ax.set_title("Transects:"+str(transect_range[i][0])+"-"+str(transect_range[i][1]),backgroundcolor=transect_colour[i],color='white')

    ax.set_xticklabels(['1982','1986','1992','1998','2004','2010','2016','2020','2014','2018','2022'])

    if i!= len(cross_distance_condensed.keys())-1:
        ax.set_xticklabels('')

    ax = fig.add_subplot(gs[i,1])
    ax.set_xlim([0,0.020])
    sns.distplot(cross_distance_condensed[key]- np.nanmedian(cross_distance_condensed[key]), bins=10, color=colours[i], ax=ax, vertical=True)
    ax.set_yticklabels('')
    
    if i!= len(cross_distance_condensed.keys())-1:
        ax.set_xticklabels('')
        ax.set_xlabel('')
        
fig.text(0.01, 0.5, 'Cross Vegetation-Edge Distance / m', va='center', rotation='vertical', fontsize=13.8)

plt.savefig('Data/' + sitename + '/jpg_files/crossEdgeDistances', bbox_inches='tight')


# In[ ]:


ref_sl_conv = Toolbox.convert_epsg(settings['reference_shoreline'], 32630, 27700)[:,:-1]

vv = dict([])
vv['1'] = [ref_sl_conv]

#Displays produced lines/transects

fig = plt.figure()#figsize=[15,8], tight_layout=True)
plt.axis('equal')
#plt.xlabel('Eastings')
#plt.ylabel('Northings')
plt.xlim(min(vv['1'][0][:,0]),max(vv['1'][0][:,0]))
plt.xticks('')
plt.yticks('')
plt.ylim(min(vv['1'][0][:,1])-50,max(vv['1'][0][:,1])+50)
plt.grid(linestyle=':', color='0.5')
for i in range(len(vv['1'])):
    sl = vv['1'][i]
    date = vv['1'][i]
    plt.plot(sl[:,0], sl[:,1], '.', color='k')#, label=date.strptime('%d-%m-%Y'))
 
for i,key in enumerate(list(transect_condensed.keys())):
    plt.plot(transect_condensed[key][0,0],transect_condensed[key][0,1], 'bo', color= colours[i], ms=5)
    plt.plot(transect_condensed[key][:,0],transect_condensed[key][:,1],'k-', color= colours[i], lw=1)
    plt.text(transect_condensed[key][1][0],transect_condensed[key][1][1], key, va='bottom', ha='right', bbox=dict(boxstyle="round", ec='k',fc='w'), fontsize=10)

plt.savefig('Data/' + sitename + '/jpg_files/refEdge_Transects', bbox_inches='tight')
plt.show()


# In[ ]:


Big_percent = []
for i,key in enumerate(cross_distance_condensed.keys()):
    cross = cross_distance_condensed[key]- np.nanmedian(cross_distance_condensed[key])
    percent_diff = []
    for j in range(len(cross)):
        percent_diff.append(100*(cross[j]-cross[0])/cross[0])
        
    Big_percent.append(percent_diff)


# In[ ]:


Big_arr = []
Big_datearr = []

Year = [[]]*(2021-1984)

for i in range(len(transect_range)):
    percent_diff = []
    dist_arr = []
    date_arr = []
    for j in range(transect_range[i][0],transect_range[i][1]):
        KEY = 'Transect_'+str(j+1)
        try:
            a, b, c, d, e = Toolbox.Separate_TimeSeries_year(cross_distance, output_proj, KEY)
            NaN_mask = np.isfinite(e)
            dist_arr.append(list(np.array(e)[NaN_mask]))
            date_arr.append(list(np.array(d)[NaN_mask]))
            #percent_diff.append()
        except:
            continue
    Big_arr.append(dist_arr)
    Big_datearr.append(date_arr)


# In[ ]:


Big_Percent = []

for j in range(len(Big_arr)):
    Medium_Percent_TransectRange = []
    Year = dict([])
    for i in range(len(Big_arr[j])):
        for k in range(len(Big_arr[j][i])):
            index = Big_datearr[j][i][k]-1984
            if Year.get(str(index)) == None:
                Year[str(index)] = []
            Year[str(index)].append(Big_arr[j][i][index-1])
            #print(len(Year[index-1]))
    List_year = []
    for v, key in enumerate(Year):
        List_year.append(np.mean(Year[key]))
    Big_Percent.append(List_year[1:])
    #print(List_year)


# In[ ]:


Barz = []

for i in range(len(Big_Percent)):
    temp = []
    for j in range(len(Big_Percent[i])):
        temp.append(100*(Big_Percent[i][j]-Big_Percent[i][0])/Big_Percent[i][0])
    Barz.append(temp)

"""
