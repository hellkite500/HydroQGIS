# -*- coding: utf-8 -*-
"""
/***************************************************************************
FFA worker class for downloading USGS peak flow data using a QThread
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
from PyQt4.QtCore import QObject, pyqtSignal, QVariant
from qgis.core import QgsVectorLayer, QgsField, QgsFeature, QgsGeometry, QgsPoint, QgsMessageLog
import urllib
import json
import math
import os
import pandas as pd

class USGSPeakWorker(QObject):
    """Worker thread for calling NWIS web service"""
    def __init__(self, stations):
        QObject.__init__(self)
        self.stations = stations
        QgsMessageLog.logMessage('Station Len:  '+str(len(stations)), 'Debug', QgsMessageLog.INFO)
        self.killed = False
        self.plugin_path = os.path.split(os.path.dirname(os.path.realpath(__file__)))[0]
        self.data_dir = os.path.join(self.plugin_path, 'tmp')
        QgsMessageLog.logMessage(self.data_dir, 'Debug', QgsMessageLog.INFO)
    """
    Get flood peak data from usgs for the stations listed in station_file
    """
    def getFloodPeaks(self):
        #Web root for USGS peakflow data
        usgs_root = 'http://nwis.waterdata.usgs.gov/nwis/peak'
        #Start building the peak flow query string
        query = usgs_root + '?multiple_site_no='

        #Add in all stations to the query string
        for s in self.stations:
            query += s+'%2C'
            #QgsMessageLog.logMessage('Code '+s, 'Debug', QgsMessageLog.INFO)

        #Quick hack to remove the last %2C from the query
        query = query[:-3:]

        #Add additional parameters to the http string
        query += '&group_key=NONE'
        query += '&sitefile_output_format=rdb_file'
        query += '&column_name=agency_cd'
        query += '&column_name=site_no'
        query += '&column_name=station_nm'
        query += '&column_name=lat_va'
        query += '&column_name=long_va'
        query += '&set_logscale_y=1'
        query += '&format=rdb'
        query += '&date_format=separate_columns'
        query += '&rdb_compression=value'
        query += '&hn2_compression=file'
        query += '&list_of_search_criteria=multiple_site_no'
        #Get peak flow file
        #QgsMessageLog.logMessage(query, 'Debug', QgsMessageLog.INFO)
        urllib.urlretrieve(query, os.path.join(self.data_dir, 'peak'))
        
    """
    Get the latitude, longitude, and drainage area for the stations listed in station_file
    """
    def getLatLong(self):
        #Web root for USGS peakflow data
        usgs_root = 'http://nwis.waterdata.usgs.gov/nwis/peak'
        #Start building the peak flow query string
        query = usgs_root + '?multiple_site_no='

        #Add in all stations to the query string
        for s in self.stations:
            query += s+'%2C'

        #Quick hack to remove the last %2C from the query
        query = query[:-3:]
        #Now get lat_long data for the stations

        #Add additional parameters to url
        query += '&group_key=huc_cd'
        query += '&format=sitefile_output'
        query += '&sitefile_output_format=rdb'
        query += '&column_name=site_no'
        query += '&column_name=dec_lat_va'
        query += '&column_name=dec_long_va'
        query += '&column_name=coord_acy_cd'
        query += '&column_name=coord_datum_cd'
        query += '&column_name=drain_area_va'
        query += '&set_logscale_y=1'
        query += '&date_format=YYYY-MM-DD'
        query += '&rdb_compression=file'
        query += '&hn2_compression=file'
        query += '&list_of_search_criteria=multiple_site_no'

        #Make http request
        urllib.urlretrieve(query, os.path.join(self.data_dir, 'dec_lat_long'))
        #QgsMessageLog.logMessage(query, 'Debug', QgsMessageLog.INFO)
    
    def run(self):
        """
        Downloads peak flow data for given stations from USGS
        TODO DESCRIBE MORE!!!
        """
        try:
            self.status.emit('attempting download')
            self.getFloodPeaks()
            self.getLatLong()
            self.status.emit('Finished downloading data...')
            self.finished.emit(True)
            #should we download peak flow data, parse, and delete?  Cache? Store as attributes???
        except Exception, e:
            import traceback
            self.error.emit(e, traceback.format_exc())
            self.status.emit("Error in FFA Service Thread")
            #print e, traceback.format_exc()
            self.finished.emit(False)

    status = pyqtSignal(str)
    error = pyqtSignal(Exception, basestring)
    finished = pyqtSignal(bool)

