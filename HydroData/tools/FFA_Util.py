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
    QgsMessageLog.logMessage(str(s), 'Print', QgsMessageLog.INFO)

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
    
    def weightSkew(G, Gbar, N):
        #Make sure we got a valid generalized skew value.
        if(Gbar != -200):
            #TODO/FIXME Adjust for historicall data as per appendix 6, bulletin 17B
            
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
            qprint("Weighted skew: {}".format(G))
            return Gw
        else:
            qprint("No plate1 skew found, not weighting skew.")
            return G   
    
    def low_outlier_test(self, Xbar, S, G, Xl, data):
        """
            Helper function that finds low outliers in data where
            data['logQ'] < Xl.  If any are found, stats are recomputed and these
            new stats are returned along with the number of outliers removed and the filtered record.
        """
        
        outliers = data[ data['logQ'] < Xl ]
        if not outliers.empty:
            #FOUND LOW OUTLIERS!!!!
            self.status.emmit("Low outliers detected for {}, see qgis log".format(data.index.get_level_values(0)[0])
            qprint("Low outliers detected at site number: {}".format(data.index.get_level_values(0)[0]))
            qprint(outliers.to_string())
            
            #Remove low outliers from the record and re-compute stats
            data = data[ data['logQ'] >= Xl ]
            Xbar = data['logQ'].mean()
            S = data['logQ'].std()
            G = data['logQ'].skew()
        #Now return the stats
        return Xbar, S, G, len(outliers), data
    
    def high_outlier_test(self, Xbar, S, G, Xh, data):
        """
            Helper function that finds high outliers in data where
            data['logQ'] > Xh.  If any are found, stats are recomputed and these
            new stats are returned along with the number of outliers removed and the filtered record.
        """
        outliers = data[ data['logQ'] > Xh ]
        if not outliers.empty:
            #FOUND HIGH OUTLIERS!!!!
            self.status.emmit("High outliers detected for {}, see qgis log".format(data.index.get_level_values(0)[0])
            qprint("High outliers detected at site number: {}".format(data.index.get_level_values(0)[0]))
            qprint(outliers.to_string())
            #Remove high outliers from the record and re-compute stats
            data = data[ data['logQ'] <= Xh ]
            Xbar = data['logQ'].mean()
            S = data['logQ'].std()
            G = data['logQ'].skew()
        #Now return the stats
        return Xbar, S, G, len(outliers), data
            
    
    def outlierTest(self, Xbar, S, G, N, data, kntable):
        """
            This function tests for statistical outliers in the record, as per
            Bulliten 17B. It uses the KN table from appendix 4 of the bulliten
            to perform a one-sided 10 percent test.
            
            As Bulliten 17B suggests, the outlier tests are perfromed based on the 
            calculated skew value.
        """
               
        
        
        if G <  -0.40:
            #Consider low outliers first
    
            #calculate the low outlier threshold
            Xl = Xbar - kntable.ix[N]['value']*S
            #Test the data against the low threshold, and get back new stats
            Xbar, S, G, N_low, data= self.low_outlier_test(Xbar, S, G, Xl, data)
            #This gives the record length with low outliers removed
            N = N - N_low
            
            #calculate the high outlier threshold
            Xh = Xbar + kntable.ix[N]['value']*S
            #Test the data against the high threshold, and get back new stats
            Xbar, S, G, N_high, data = self.high_outlier_test(Xbar, S, G, Xl, data)
            N = N - N_high
            
            #Now decide if we need to apply conditional probabilty adjustment
            #Or adjust for high outliers/ historic peaks TODO/FIXME
            if N_high > 0:
                #Apply historic peak adjustment before continuing
                #TODO/FIXME
                pass
                
            if N_Low > 0:
                #Apply condtional probability adjustment TODO/FIXME
                pass
                
        elif G > 0.04:
            #Consider high outliers first
            #calculate the high outlier threshold
            Xh = Xbar + kntable.ix[N]['value']*S
            #Test the data against the high threshold, and get back new stats
            Xbar, S, G, N_high, data = self.high_outlier_test(Xbar, S, G, Xl, data)
            N = N - N_high
            
            if N_high > 0:
                #Apply historic peak adjustment before continuing
                #TODO/FIXME for historical adjustment, use Xl = M~ - K_h*S~ (eq 8b, bulliten 17B)
                #TODO/FIXME
                pass
            
            #calculate the low outlier threshold
            Xl = Xbar - kntable.ix[N]['value']*S
            #Test the data against the low threshold, and get back new stats
            Xbar, S, G, N_low, data = self.low_outlier_test(Xbar, S, G, Xl, data)
            #This gives the record length with low outliers removed
            N = N - N_low
            
            if N_low > 0:
                #Apply condtional probability adjustment TODO/FIXME
                pass
                
        else: #  -0.4 <= G <= 0.4
            #Consider both before adjusting
            """
                In this case we have to test for outliers before the record is modified.
                Use the same two test functions, but don't overwrite the original statistics
                when testing the high outliers.  We can with the low, since the high has already
                been computed.
            """
            #calculate the high outlier threshold
            Xh = Xbar + kntable.ix[N]['value']*S
            #Test the data against the high threshold, but don't overwrite stats yet
            Xbar_h, S_h, G_h, N_high, data_h = self.high_outlier_test(Xbar, S, G, Xl, data)
            
            #calculate the low outlier threshold
            Xl = Xbar - kntable.ix[N]['value']*S
            #Test the data against the low threshold, and get back new stats
            Xbar, S, G, N_low, data = self.low_outlier_test(Xbar, S, G, Xl, data)
            N = N - N_low
            
            #Now decide if we need to apply conditional probabilty adjustment
            #Or adjust for high outliers/ historic peaks TODO/FIXME
            if N_high > 0:
                #Apply historic peak adjustment before continuing
                #TODO/FIXME
                pass
                
            if N_Low > 0:
                #Apply condtional probability adjustment TODO/FIXME
                pass

            
            
        #Finally, return the final statistics needed to create the frequency curve
        return Xbar, S, G, N, data
        
    def run(self):
    
        try:
            #Load peak data
            df = pd.read_msgpack(os.path.join(self.tmp_dir,'peak_data.msg'))
            plate1 = pd.read_msgpack(os.path.join(self.data_dir,'plate1.msg'))
            #load the statistics tables ktable, and kntable
            ktable = pd.read_msgpack(os.path.join(self.data_dir,'ktable.msg'))
            kntable = pd.read_msgpack(os.path.join(self.data_dir, 'kntable.msg'))
            
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
                #TODO/FIXME use Appendix 5 conditional probability adjustment if zero flood years found
                nonZero = data[data['peak_va'] > 0]
                #now get a log-transform of the data
                nonZero['logQ'] = nonZero['peak_va'].apply(lambda x: log10(x))
                #Calculate statistics
                #stats = self.stats(nonZero['logQ'])
                X = nonZero['logQ']
                Xbar, S, G, N= self.stats(X)
                qprint("Stats:\nMean: {}\nStd Dev: {}\nSkew: {}\nN: {}".format(Xbar, S, G, N))
                #Calculate the weighted skew
                """
                    It would seem logical to use the weighted skew throughout the computations,
                    but the flow chart and examples provided in Appendix 12, Bulliten 17B, suggest otherwise.
                    Their procedure is to use station skew until after outliers are removed...
                """
                #G = self.weightSkew(G, Gbar, N)
                #Now perform outlier tests
                Xbar, S, G, N, data = self.outlierTest(Xbar, S, G, N, data, kntable)
                
                
                
                
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
