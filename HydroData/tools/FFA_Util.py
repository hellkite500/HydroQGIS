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

class ffaWorker(QObject):

    def __init__(self):
        QObject.__init__(self)
        #Create some file path variables
        self.plugin_path = os.path.split(os.path.dirname(os.path.realpath(__file__)))[0]
        self.data_dir = os.path.join(self.plugin_path, 'tmp')
    
    
    def run(self):
    
        try:
            #Load peak data
            df = pd.read_msgpack(os.path.join(self.data_dir,'peak_data.msg'))
            #log-transform the data
            df['peak_va'] = df['peak_va'].astype('float')
            df['logQ'] = df.apply(lambda x: log10(x['peak_va']), axis=1)
            #get generalized skew
            df['gen_skew'] = df.apply(skew_map.getSkew, axis=1)
            
            QgsMessageLog.logMessage(df.head().to_string(), 'Print', QgsMessageLog.INFO)
            
            #Now we will split an operate on each site independently
            groups = df.groupby(level='site_no')
            for site, data in groups:
                QgsMessageLog.logMessage("Processing Station "+site, 'Print', QgsMessageLog.INFO)
                #QgsMessageLog.logMessage(data.head().to_string(), 'Print', QgsMessageLog.INFO)
                #Calculate mean and skew statistics
                
                
                
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
