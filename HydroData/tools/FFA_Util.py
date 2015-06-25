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
        self.results = {}
        
    def stats(self, X):
        """
            Helper function to return several statistics from a pandas series, X
        """
        return X.mean(), X.std(), X.skew(), len(X)
    
    def weightSkew(self, G, Gbar, N):
        #Make sure we got a valid generalized skew value.
        if(Gbar != -200):
            #All adjustments should be made before calculating weighted skew
            
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
            qprint("MSE Station Skew: "+str(MSEg))
            #Now we can calculate the weighted skew
            Gw = (MSEgbar*G + MSEg*Gbar) / (MSEgbar + MSEg)
            
            #This will be the value of skew we use for the rest of the computations
            qprint("Weighted skew: {}".format(Gw))
            return Gw
        else:
            qprint("No plate1 skew found, not weighting skew.")
            return G   
    
    def low_outlier_test(self, Xbar, S, G, Xl, data):
        """
            Helper function that finds low outliers in data where
            data['logQ'] < Xl.  If any are found, stats are recomputed and these
            new stats are returned along with the number of outliers removed and the filtered record.
            
            data is expected to be a pandas series, multi-indexed.  This series contains the site_no as 
            the first index, and the year as the second.  The data values are the log transformed peak 
            flows.
        """
        N = len(data)
        outliers = data[ data < Xl ]
        if not outliers.empty:
            #FOUND LOW OUTLIERS!!!!
            self.status.emit("Low outliers detected for {}, see qgis log".format(data.index.get_level_values(0)[0]))
            qprint("Low outliers (below {}) detected at site number: {}".format(pow(10, Xl), data.index.get_level_values(0)[0]))
            qprint(outliers.to_string())
            
            #Remove low outliers from the record and re-compute stats
            data = data[ data >= Xl ]
            Xbar, S, G, N= self.stats(data)
        #Now return the stats
        return Xbar, S, G, N, len(outliers), data, outliers
    
    def high_outlier_test(self, Xbar, S, G, Xh, data):
        """
            Helper function that finds high outliers in data where
            data['logQ'] > Xh.  If any are found, stats are recomputed and these
            new stats are returned along with the number of outliers removed and the filtered record.
            
            data is expected to be a pandas series, multi-indexed.  This series contains the site_no as 
            the first index, and the year as the second.  The data values are the log transformed peak 
            flows.
        """
        N = len(data)
        outliers = data[ data > Xh ]
        if not outliers.empty:
            #FOUND HIGH OUTLIERS!!!!
            self.status.emit("High outliers detected for {}, see qgis log".format(data.index.get_level_values(0)[0]))
            qprint("High outliers (above {}) detected at site number: {}".format(pow(10, Xh), data.index.get_level_values(0)[0]))
            qprint(outliers.to_string())
            #Remove high outliers from the record and re-compute stats
            data = data[ data <= Xh ]
            Xbar, S, G, N= self.stats(data)
        #Now return the stats
        return Xbar, S, G, N, len(outliers), data, outliers
            
    def historicalStats(self, X, Xz, L, M, S, G, N):
        """
            X = log transformed magnitude of systematic peaks excluding zero flood events, peaks below base, and high or low outliers
            Xz = log of a historic peak including ha high outlier that has historic information
            L = number of low values to be excluded (# zero-flood years, # below base, # low outliers...)
            M = mean of X's
            S = standard deviation of X's
            G = skew of X's
            N = number of X's in systematic record (not including low outliers/zero flood records)
        
            Per Appendix 6, Bulliten 17B, this function calculates
            the historically adjusted mean, standard deviation, and skew.
            
            This function expects the systematic record with outliers removed as X
            and the historical peaks/high outliers in Xz
            (both as pandas series)
            
            Currently this function is only used to adjust for high outliers,
            though it could be extended to allow users to input historic data
        """
        #M_bar = historically adjusted mean
        #H = number of years in historic period
        #Z = number of historic peaks including high outliers that have historic information
        #W = systematic record weight
        #TODO/FIXME Seems like len(Xz is empty :S )
        qprint(Xz.to_string())
        Z = len(Xz)
        H = N + Z + L #TODO/FIXME Should this actually be the difference between the end and start year of the original data???, or maybe the length of the original record(currently implemented)???
        W = float((H - Z)) / (N + L)
        #Adjusted mean (eq 6-2b)
        M_bar = (W*N*M + Xz.sum()) / (H-W*L)
        #std dev squared (eq 6-3b)
        S_bar_sq = ( W*(N-1)*pow(S,2) + W*N*pow(M-M_bar,2) + pow((Xz - M_bar).sum(), 2) ) / (H-W*L-1)
        S_bar = pow(S_bar_sq, 0.5)
        
        #skew (eq 6-3b)
        G_bar = ( (H-W*L)/( (H-W*L-1)*(H-W*L-2)*pow(S_bar, 3) )) * ( (W*(N-1)*(N-2)*pow(S, 3)*G)/N + 3*W*(N-1)*(M-M_bar)*pow(S,2) + W*N*pow(M-M_bar,3) + pow((Xz-M_bar).sum(), 3) )
        
        #Return the adjusted statistics
        qprint("H:{}\tW:{}\tL:{}\tZ:{}\tN:{}\nPeriod used in KnLookup: {}".format(H, W, L, Z, N, H-W*L))
        return M_bar, S_bar, G_bar, H-W*L
        
    def outlierTest(self, Xbar, S, G, N, data, numZero, kntable):
        """
            This function tests for statistical outliers in the record, as per
            Bulliten 17B. It uses the KN table from appendix 4 of the bulliten
            to perform a one-sided 10 percent test.
            
            As Bulliten 17B suggests, the outlier tests are perfromed based on the 
            calculated skew value.
            
            This function returns adjusted statistics if outliers are found, as well
            as the number of high and low outliers and the adjusted record.
        """
        #If low outliers are dectected, then N will change and the calling
        #function is responsible for detecting this change and applying the conditional
        #probability adjustment.  This is because the adjustment should only be applied once,
        #but it is possible that zero-flow years were removed before outlier detection,
        #and if this is the case, and no outliers were detected, then the caller still
        #has to apply the adjustment.        
               
        if G <  -0.40:
            #Consider low outliers first
    
            #calculate the low outlier threshold
            Xl = Xbar - kntable.ix[N]['value']*S
            #Test the data against the low threshold, and get back new stats
            Xbar, S, G, N, N_low, data, low_outliers= self.low_outlier_test(Xbar, S, G, Xl, data)

            #calculate the high outlier threshold
            Xh = Xbar + kntable.ix[N]['value']*S #log10(18500) was testing!!! #Xbar + kntable.ix[N]['value']*S
            #Test the data against the high threshold, and get back new stats
            Xbar, S, G, N, N_high, data, high_outliers = self.high_outlier_test(Xbar, S, G, Xh, data)

            #Adjust for high outliers/historic peaks
            if N_high > 0:
                Xbar, S, G, P = self.historicalStats(data, high_outliers, numZero+N_low, Xbar, S, G, N)
                qprint("New stats\nmean:{}\tstd:{}\tskew:{}".format(Xbar, S, G))
                
        elif G > 0.04:
            #Consider high outliers first
            #calculate the high outlier threshold
            Xh = Xbar + kntable.ix[N]['value']*S
            #Test the data against the high threshold, and get back new stats
            Xbar, S, G, N, N_high, data, high_outliers = self.high_outlier_test(Xbar, S, G, Xh, data)
            
            if N_high > 0:
                #Apply historic peak adjustment before continuing.  Need to calculate
                #adjusted mean, std, skew, and Xl before performing low outlier test
                #TODO/FIXME is this period (P) the correct value to use in this equation for Xl???
                Xbar, S, G, P = self.historicalStats(data, high_outliers, numZero, Xbar, S, G, N)
                #Adjust low outlier threshold based on historic information (P)
                Xl = Xbar - kntable.ix[int(P)]['value']*S
            else:
                #calculate the low outlier threshold
                Xl = Xbar - kntable.ix[N]['value']*S
            
            #Test the data against the low threshold, and get back new stats
            Xbar, S, G, N, N_low, data, low_outliers = self.low_outlier_test(Xbar, S, G, Xl, data)
                
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
            Xbar_h, S_h, G_h, N_h, N_high, data_h, high_outliers = self.high_outlier_test(Xbar, S, G, Xh, data)
            
            #calculate the low outlier threshold
            Xl = Xbar - kntable.ix[N]['value']*S
            #Test the data against the low threshold, and get back new stats
            Xbar, S, G, N, N_low, data, low_outliers = self.low_outlier_test(Xbar, S, G, Xl, data)
            

            #Adjust for high outliers/ historic peaks
            if N_high > 0:
                #Apply historic peak adjustment before continuing
                Xbar, S, G, P = self.historicalStats(data, high_outliers, numZero, Xbar, S, G, N)
                          
        #Finally, return the final statistics needed to create the frequency curve
        return Xbar, S, G, N, N_low, N_high, data
            
    def run(self):
    
        try:
            #Load peak data
            df = pd.read_msgpack(os.path.join(self.tmp_dir,'peak_data.msg'))
            plate1 = pd.read_msgpack(os.path.join(self.data_dir,'plate1.msg'))
            #load the statistics tables ktable, and kntable
            ktable = pd.read_msgpack(os.path.join(self.data_dir,'ktable.msg'))
            #Pull the probabilities from ktable and save them for later reference
            Ps = ktable.index.values
            
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
                #Adopted Skew similar to HECFQ, TODO Trying to match their output...
                Gbar = round(Gbar, 1)
                qprint("Lat/Long Skew keys: {}\t{}, Generalized Skew: {}".format(lat+'.5', lon+'.5', Gbar))
               
                #Before calculating stats we need to remove 0 flow values if they exists
                
                nonZero = data[data['peak_va'] > 0]
                #now get a log-transform of the data
                nonZero['logQ'] = nonZero['peak_va'].apply(lambda x: log10(x))
                #Calculate statistics
                qprint(nonZero.to_string())
                X = nonZero['logQ']
                Xbar, S, G, N= self.stats(X)

                #Need to remember the number of zero-flood years for historical adjustment
                numZero = len(data) - N
                qprint("Stats:\nMean: {}\nStd Dev: {}\nSkew: {}\nN: {}".format(Xbar, S, G, N))

                #Now perform outlier tests
                Xbar, S, G, N, N_low, N_high, X = self.outlierTest(Xbar, S, G, N, X, numZero, kntable)

                qprint("Outlier detection finished")
                qprint("Stats:\nMean: {}\nStd Dev: {}\nSkew: {}\nN: {}".format(Xbar, S, G, N))
                
                #Calculate the original frequency curve
                #TODO/FIXME might be better to interpolate the skews rather than simply round, but may require more depenencies (i.e. Scypi)
                freq = Xbar + ktable[round(G, 1)] * S
                #Rename this series so it is more clear what we now have
                freq.name = 'LogQ'
                freq = freq.reset_index()
                freq['Q'] = freq['LogQ'].apply(lambda x: pow(10,x))
                qprint("Frequency Curve:\n"+freq.to_string())
                
                #Now decide if we need to apply conditional probabilty adjustment
                #The equations for which vary if the historic adjustment was made
                #during outlier detection (or any other time, for that fact.)
                
                #This adjustment is applied when zero-flow years are removed, if peaks below a gage base
                #are removed, or if low outliers are detected and removed.  This utility only knows about
                #zero-flow years and outlier removal at this point, so we simply check to see if the new N
                #is < than the original record length...if so, we need to apply the adjustment.
                #See appendix 5 of Bulletin 17B
                P_adjust = 1
                W = 1
                #Calculate the estimated probability, P_bar = N/n, that any annual peak will exceed the truncation level (eq 5-1a)
                #Where N is the number of peaks above the truncation level and n is the number of years of record
                #TODO/FIXME if we allow user input on historic data, then H isn't simply the length of the record!!!
                #Since we are curretnly only using high outliers found in the record, H=len(data) is fine for now.
                if(N_high > 0):
                    H = len(data)
                    Z = N_high
                    W = float((H-Z)) / (N+L)
                    P_adjust = (H-W*L)/H #eq 5-1b, P_bar for historic adjustment
                else:
                    #Need to cast one of these to get floating point result!
                    P_adjust = float(N)/len(data) #eq 5-1a
                
                if N_low > 0 or numZero > 0: #somewhere low data was removed, need to apply conditional probability adjustment
                    #L is the number of low flow records removed                    
                    L = N_low + numZero
                    if L/len(data) > 0.25:
                        qprint("ERROR: More than 25% of the record for site {} has been truncated, recommend not using this procedure.".format(site))
                        #TODO/FIXME decide what to do here....just go to the next? raise an exception??? for now just skip the site...
                        continue
                       
                    #Have calculated the probability adjustment, apply it
                    #Get the original frequency curve
                    freq_adj = freq.copy()
                    #Apply P_adjust to all probabilities
                    freq_adj['P'] = freq['P']*P_adjust
                    #freq_adj is now the proper adjusted frequency curve,
                    #however to apply the conditional probability adjustment, 
                    #we still need to interpolate values for other probabilities
                    freq_adj['Q'] = freq_adj['LogQ'].apply(lambda x: pow(10,x))
                    qprint("Adjusted Frequency Curve:\n"+freq_adj.to_string())
                    
                    #Set the flow values for original probabilities to nan so they can be interpolated from the adjusted curve
                    freq['LogQ'] = pd.np.nan
                    #Combine the original probabilities from the frequency curve to the adjusted probabilities for interpolation
                    Ps = pd.concat([freq, freq_adj])
                    Ps.set_index('P', inplace=True)
                    #Using pchip cubic interpolation (localized interpolation), interpolate the adjusted probabilities            
                    Ps = Ps.sort().interpolate(method='pchip')
                    #Ps is now the full adjusted probability frequency table
                    qprint("Interpolated Curve:\n"+Ps.to_string())
                    #We can now calculate synthetic statistics based on Appendix 5, Bulletin 17 B
                    #Synthetic Skew = -2.50+3.12 * (Log(Q_.01 / Q_.10) / Log(Q_.10 / Q_.50)) (Eq 5-3)
                    #using propoerty of logs: log(a/b) = log(a)-log(b)
                    G_s = -2.50 + 3.12 * ( (Ps.ix[0.01]['LogQ'] - Ps.ix[0.10]['LogQ'])/ (Ps.ix[0.10]['LogQ'] - Ps.ix[0.50]['LogQ']) )
                    qprint("Gs = "+str(G_s))
                    #Synthetic skew = Log(Q__0.10 / Q_0.50) / (K_.01 - K_.50) (Eq 5-4)
                    S_s = (Ps.ix[0.01]['LogQ'] - Ps.ix[0.50]['LogQ']) / (ktable[round(G_s, 1)].ix[0.01] - ktable[round(G_s, 1)].ix[0.50])
                    qprint("Ss = "+str(S_s))
                    #Synthetic mean = Log(Q_0.50) - K_0.50*(Ss)
                    Xbar_s = Ps.ix[0.50]['LogQ'] - ktable[round(G_s, 1)].ix[0.50] * S_s
                    #These are the statistics we should use to compute a final frequency curve
                    Xbar = Xbar_s
                    G = G_s
                    S = S_s
                
                #By this point we should be ready to compute the final frequency curve, all adjustments have been made
                #except for weighting the skew, do this and then compute the final frequency curve
                #Calculate the weighted skew
                """
                    It would seem logical to use the weighted skew throughout the computations,
                    but the flow chart and examples provided in Appendix 12, Bulliten 17B, suggest otherwise.
                    Their procedure is to use station skew until the very final frequency curve is developed.
                """
                G = self.weightSkew(G, Gbar, N)
                final_freq = Xbar + ktable[round(G, 1)] * S
                #Rename this series so it is more clear what we now have
                final_freq.name = 'LogQ'
                final_freq = final_freq.reset_index().set_index('P')
                #Now get the antilog and get flows in CFS
                final_freq['Q'] = final_freq['LogQ'].apply(lambda x: pow(10,x))

                qprint("Final Frequency Curve:\n"+final_freq.to_string())
                #X is the original data with outliers filtered, calculate plotting positions for these
                #data points
                #X['Rank'] = X.rank(method='max', ascending=False)
                #Calculating Weibull plotting positions, only consider unique values
                plotting_pos = X.drop_duplicates()
                #This series contains the log of the peak values
                plotting_pos.name='LogQ'
                ranks = plotting_pos.rank(method='max', ascending=False)
                #This series contains the rank of each event
                ranks.name='Rank'
                ranked_df = pd.concat([plotting_pos, ranks], axis=1)
                #qprint("plotting pos:\n"+plotting_pos.to_string())
                #qprint("Ranks:\n"+ranks.to_string())
                #Need to adjust if historical peaks found/used.  Since W is 1 unlsess this happens, could just always 
                #calculate...
                if N_high > 0:
                    ranked_df['Rank'] = W * ranked_df['Rank'] - (W-1)*(Z+0.5)
                #Now calculate the exceedance probability and plotting position for the data
                #TODO/FIXME if H (historic record length) isn't the same as record length, then
                #this is WRONG since historic adjustment is m/(H+1) and standard weibull is m/(N+1)
                ranked_df['Exceedance'] = ranked_df['Rank']/(len(data) + 1)
                ranked_df['PP'] = ranked_df['Exceedance']*100
                ranked_df['Q'] = ranked_df['LogQ'].apply(lambda x: pow(10,x))
                qprint("Plotting Data:\n"+ranked_df.to_string())
                
                #Calculating 5% confidence intervals, need K value for skew 0, P 0.05
                zc = ktable[0][0.05]
                a = 1 - (pow(zc, 2) / (2*(N-1)))
                b = pow(zc, 2)/N
                KupC = (ktable[round(G, 1)] + pow( ( pow(ktable[round(G,1)], 2) - a*( pow(ktable[round(G,1)], 2) - b )), 0.5))/a
                KupC.name = 'K_upper'
                KlpC = (ktable[round(G, 1)] - pow( ( pow(ktable[round(G,1)], 2) - a*( pow(ktable[round(G,1)], 2) - b )), 0.5))/a
                KlpC.name = 'K_lower'
                
                confidence = pd.concat([KupC, KlpC], axis=1)
                qprint("Conf\n"+confidence.to_string())
                confidence['LogQ_U'] = Xbar + confidence['K_upper']*S
                confidence['LogQ_L'] = Xbar + confidence['K_lower']*S
                confidence['Q_U'] = confidence['LogQ_U'].apply(lambda x: pow(10,x))
                confidence['Q_L'] = confidence['LogQ_L'].apply(lambda x: pow(10,x))
                #final_freq['Q'].plot()
                self.results[site]={'curve' : final_freq['Q'], 'positions':ranked_df, 'confidence':confidence}
            #Finished processing all sites, return results
            self.finished.emit(True, self.results)    
        except Exception, e:
            import traceback
            self.error.emit(e, traceback.format_exc())
            self.status.emit("Error in flood peak parser thread")
            #print e, traceback.format_exc()
            self.finished.emit(False, self.results)
    
    status = pyqtSignal(str)
    error = pyqtSignal(Exception, basestring)
    finished = pyqtSignal(bool, dict)
    plot = pyqtSignal(pd.Series)

#additional threaded utilities go here???
