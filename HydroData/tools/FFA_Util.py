# -*- coding: utf-8 -*-
"""
/***************************************************************************
FFA utilities to perform flood frequency and other analysis.
                              -------------------
        begin                : 2015-05-22
        git sha              : $Format:%H$
        copyright            : (C) 2014 by Nels Frazier
        email                : hellkite500@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
#TODO clean up some unused imports
from PyQt4.QtCore import QObject, pyqtSignal, QVariant
from qgis.core import QgsVectorLayer, QgsField, QgsFeature, QgsGeometry, QgsPoint, QgsMessageLog

import os
import pandas as pd
from math import log10

#Import the skew_map to lookup the skew for each station
import skew_map

def qprint(s):
    QgsMessageLog.logMessage(s, 'Print', QgsMessageLog.INFO)

class ffaWorker(QObject):

    def __init__(self):
        QObject.__init__(self)
        #Create some file path variables
        self.plugin_path = os.path.split(os.path.dirname(os.path.realpath(__file__)))[0]
        self.data_dir = os.path.join(self.plugin_path, 'data')
        self.tmp_dir = os.path.join(self.plugin_path, 'tmp')
    
    def stats(self, X):
        """
            Helper function to return several statistics from a pandas series, X
        """
        return X.mean(), X.std(), X.skew(), len(X)
        
    
    def outlierTest(self, Xbar, S, G, N):
        """
            This function tests for statistical outliers in the record, as per
            Bulliten 17B. It uses the KN table from appendix 4 of the bulliten
            to perform a one-sided 10 percent test.
            
            As Bulliten 17B suggests, the outlier tests are perfromed based on the 
            calculated skew value.
        """
        if G >= -0.40 and G <= 0.40:
            pass
            #Test both low and high outliers before removing any data
            
        
    def run(self):
    
        try:
            #Load peak data
            df = pd.read_msgpack(os.path.join(self.tmp_dir,'peak_data.msg'))
            plate1 = pd.read_msgpack(os.path.join(self.data_dir,'plate1.msg'))
            #make sure the flow values are treated as floating point numbers
            df['peak_va'] = df['peak_va'].astype('float')
            
            #Now we will split and operate on each site independently
            groups = df.groupby(level='site_no')
            
            for site, data in groups:
                QgsMessageLog.logMessage("Processing Station "+site, 'Print', QgsMessageLog.INFO)
                #QgsMessageLog.logMessage(data.head().to_string(), 'Print', QgsMessageLog.INFO)
                
                #look up the generalized skew from Bulletin 17B, plate 1 data
                #Get lat/long from the USGS data, then split off the decimals, since skews
                #are indexed by 1 degree quadrangles.
                lat = data.iloc[0]['dec_lat_va'].split('.')[0]
                lon = data.iloc[0]['dec_long_va'].split('.')[0]
                #Now find the skew, appending .5 to lat/long indicating that we want a skew value
                #between lat and lat+1, and long + long +1
                Gbar = plate1.ix[lat+'.5'][lon+'.5']
                
                qprint("Lat/Long Skew keys: {}\t{}, Generalized Skew: {}".format(lat+'.5', lon+'.5', Gbar))
               
                #Before calculating stats we need to remove 0 flow values if they exists
                nonZero = data[data['peak_va'] > 0]
                #now get a log-transform of the data
                nonZero['logQ'] = nonZero['peak_va'].apply(lambda x: log10(x))
                #Calculate statistics
                #stats = self.stats(nonZero['logQ'])
                X = nonZero['logQ']
                Xbar, S, G, N= self.stats(X)
                qprint("Stats:\nMean: {}\nStd Dev: {}\nSkew: {}\nN: {}".format(Xbar, S, G, N))
                #Make sure we got a valid generalized skew value.
                if(Gbar != -200)
                    #For now we are just using plate1 generalized skews, so MSEgbar = 0.302 per Bulletin 17B
                    MSEgbar = 0.302
                    #Need to calculate MSEg, following Bulletin 17B
                    absG = abs(G)
                    if(absG <= 0.90):
                        A = -0.33 + 0.08*absG
                    else:
                        A = -0.52 + 0.30*absG
                        
                    if(absG <= 1.5):
                        B = 0.94 - 0.26*absG
                    else:
                        B = 0.55
                    
                    MSEg = pow(10, A - (B * log10(N/10)))
                    
                    #Now we can calculate the weighted skew
                    Gw = (MSEgbar*G + MSEg*Gbar) / (MSEgbar + MSEg)
                    
                    #This will be the value of skew we use for the rest of the computations
                    G = Gw
                qprint("Weighted skew: {}".format(G))
                #Now perform outlier tests
                
                self
                
                
                
                
        except Exception, e:
            import traceback
            self.error.emit(e, traceback.format_exc())
            self.status.emit("Error in flood peak parser thread")
            #print e, traceback.format_exc()
            self.finished.emit(False)
    
    status = pyqtSignal(str)
    error = pyqtSignal(Exception, basestring)
    finished = pyqtSignal(bool)

#additional threaded utilities go here???
