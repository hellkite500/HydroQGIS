# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Point worker class for calling EPA WATHERS Point Index Service via QThread
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
import urllib2
import json

class PointWorker(QObject):
    """Worker thread for delinating watersheds via EPA WATERS"""
    def __init__(self, point):
        QObject.__init__(self)
        self.point = point
        self.killed = False
        
    def run(self):
        ret = None
        #Try to connect to the EPA WATERS web server and get back a watershed feature
        try:
            self.status.emit("Started Point Service Call")
            x = str(self.point.x())
            y = str(self.point.y())
            url = "http://ofmpub.epa.gov/waters10/PointIndexing.Service?"\
                    +"pGeometry=POINT(%s+%s)"%(x,y)\
                    +"&pGeometryMod=WKT%2CSRID%3D8265"\
                    +"&pResolution=3"\
                    +"&pPointIndexingMethod=DISTANCE"\
                    +"&pPointIndexingMaxDist=25"\
                    +"&pOutputPathFlag=FALSE"\
                    +"&pReturnFlowlineGeomFlag=FALSE"\
                    +"&optNHDPlusDataset=2.1"
            #Call the EPA Waters point service using the qgis lat long coordinates clicked
            #print url
            response = json.loads(urllib2.urlopen(url).read())
            if response['output']:
                results = response['output']['ary_flowlines']
                showText = x+' , '+y + '\nFound %d results:\n'%len(results)
                showText = showText+'comid = %d\nfmeasure = %d'%(results[0]['comid'],results[0]['fmeasure'])
                #Return the comid and fmeasure found by the point service
                ret = (results[0]['comid'], results[0]['fmeasure'])
                self.finished.emit(True, ret)
            else:
                showText = 'No features found at %s, %s'%(x,y)
                self.finished.emit(False, ret)
            #Send out status message
            self.status.emit(showText)
        except Exception, e:
            import traceback
            self.error.emit(e, traceback.format_exc())
            self.status.emit("Error in Point Service Thread")
            #print e, traceback.format_exc()
            self.finished.emit(False, ret)

    status = pyqtSignal(str)
    error = pyqtSignal(Exception, basestring)
    finished = pyqtSignal(bool, tuple)

