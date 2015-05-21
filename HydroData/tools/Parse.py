# -*- coding: utf-8 -*-
"""
/***************************************************************************
Parsing utilities to mangle data into Pandas dataframes.
                              -------------------
        begin                : 2015-04-01
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

class parseFloodPeakWorker(QObject):

    def __init__(self):
        QObject.__init__(self)
        self.plugin_path = os.path.split(os.path.dirname(os.path.realpath(__file__)))[0]
        self.data_dir = os.path.join(self.plugin_path, 'tmp')
        self.peak_file = os.path.join(self.data_dir, 'peak')
        self.coord_file = os.path.join(self.data_dir, 'dec_lat_long')
    def run(self):
    
        try:
            #Read the USGS peak flow data into a pandas dataframe
            #This ignores comment lines beginning with #, uses the USGS header, and creates a multi-index, indexing first for site_no then by peak_yr
            df = pd.read_csv(self.peak_file, comment='#', header=0, sep='\t').drop([0]).set_index(['site_no', 'peak_yr'])
            #get rid of columns that aren't useful
            df.drop(['agency_cd', 'gage_ht', 'gage_ht_cd', 'year_last_pk', 'ag_dt', 'ag_tm', 'ag_gage_ht', 'ag_gage_ht_cd'], axis=1, inplace=True)
            
            #we also need to get rid of any row with a bad quality code: 1,3,9, or A
            df = df[(df.peak_cd != '1') & (df.peak_cd != '3') & (df.peak_cd != '9') & (df.peak_cd != 'A')]
            #Now get the coordinate information for these stations and merge them into one dataframe
            df2 = pd.read_csv(self.coord_file, comment='#', header=0, sep='\t').drop([0]).set_index(['site_no'])
            df2.drop(['coord_acy_cd', 'coord_datum_cd'], axis=1, inplace=True)
            
            #Join the data
            df3 = df.join(df2, how='inner')
            #Now one can use a groupby to seperate each site into a data frame to processes
            #This iterator gives us the index name and a dataframe gropubed by site_no
            #we can then call data.ix[site] to get each site's data and processes accordingly
            """
            groups = df.groupby(level='site_no')

            for site, data in groups:
                print site
                print data.ix[site]
            """
            #save this dataframe to a light binary format. This also perserves the multi-index hiearchy
           
            #TODO This might be a good place to look up and add generalized skew values to this data frame.
            #maybe use df['skew'] = lookup(df['dec_lat_va'], df['dec_long_va'] before the groupby...in fact,
            #the groupby may be best saved for when the actual ffa is performed...groupby then apply???
            #FIXME!!!!!!!!!!!!!!!!!!!!!!!!!
            #FIXME this could be bad if two ffa's are running at a time (as the threading allows for) then
            #we have a race condition!!! Maybe have the user name the runs and warn about overwritting?
            #Or use a unique ID of some sort...but must do something!!!
            df3.to_msgpack(os.path.join(self.data_dir, 'peak_data.msg'))
            
            self.status.emit('Finished parsing flood peaks...')
            self.finished.emit(True)
        except Exception, e:
            import traceback
            self.error.emit(e, traceback.format_exc())
            self.status.emit("Error in flood peak parser thread")
            #print e, traceback.format_exc()
            self.finished.emit(False)
    
    status = pyqtSignal(str)
    error = pyqtSignal(Exception, basestring)
    finished = pyqtSignal(bool)
