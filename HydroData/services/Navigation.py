# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Navigation worker class for calling EPA WATHERS Deliniation Service via QThread
                              -------------------
        begin                : 2014-11-24
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
from PyQt4.QtCore import QObject, pyqtSignal
from qgis.core import QgsVectorLayer, QgsApplication
import urllib2
import json
import os.path
import re
import glob

class NavigationWorker(QObject):
    def __init__(self, inputs, navMutex):
        self.comID = inputs[0]
        self.fMeasure = inputs[1]
        QObject.__init__(self)
        self.mutex = navMutex
        
    def getNextFileName(self, path):
        current = glob.glob(path+'/*.json')
        numList = [0]
        for f in current:
            i = os.path.splitext(f)[0]
            try:
                n = re.findall('[0-9]+$', i)[0]
                numList.append(int(n))
            except IndexError:
                pass
        next = max(numList) + 1
        #print next
        return 'tmp_watershed%d.json'%(next)
        
    def run(self):
        ret = None
        try:
            self.status.emit("Started Navigation Service Call")
            #Build navigationDelineation service URL based on inputs retrieved from point service
            url = "http://ofmpub.epa.gov/waters10/NavigationDelineation.Service?"\
                    +"pNavigationType=UT"\
                    +"&pStartComid=%s"%self.comID\
                    +"&pStartMeasure=%s"%self.fMeasure\
                    +"&pMaxDistance=1000"\
                    +"&pMaxTime="\
                    +"&pAggregationFlag=true"\
                    +"&pFeatureType=CATCHMENT"\
                    +"&pOutputFlag=BOTH"\
                    +"&optNHDPlusDataset=2.1"\
                    +"&optOutGeomFormat=GEOJSON"
            #Call the EPA Waters navigation service
            response = json.loads(urllib2.urlopen(url).read())
            if not response or not response['output'] or not response['output']['shape']:
                self.status.emit('No shape returned from EPA WATERS')
                self.finished.emit(False, ret)
                return
            
            plugin_path = os.path.dirname(os.path.realpath(__file__))
            tmp = os.path.join(plugin_path, 'tmp')
            #Make sure each thread uniquely names its file.
            self.mutex.lock()
            file_name = os.path.join(tmp, self.getNextFileName(tmp))
            self.mutex.unlock()
            with open(file_name, 'w') as fp:
                json.dump(response['output']['shape'], fp)
            #TODO Add properties to layer from response, such as area ect...
            layer = QgsVectorLayer(file_name, 'Delineated Watershed', 'ogr')
            if layer.isValid():
                ret = layer
                self.status.emit("Complete")
                self.finished.emit(True, ret)
            else:
                #self.dlg.setTextBrowser(json.dumps(response['output']['shape']))
                #self.dlg.setTextBrowser('Layer from:\n'+url+'\n\nis invalid, could not reneder.')
                showText = 'Layer from:\n'+url+'\n\nis invalid, could not reneder.'
                self.status.emit(showText)
                self.finished.emit(False, ret)
        except Exception, e:
            import traceback
            self.error.emit(e, traceback.format_exc())
            self.status.emit("Error in Navigation Service Thread")
            print e, traceback.format_exc()
            self.finished.emit(False, ret)
        
    status = pyqtSignal(str)
    error = pyqtSignal(Exception, basestring)
    finished = pyqtSignal(bool, object)
    #TODO CLEAN UP TMP DIR
