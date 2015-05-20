# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Flood Frequency Analysis
                                 A QGIS plugin
 This plugin uses Bulliten 17 B guidlines for computing a flood frequency analysis
 for the provided stations.  Additionally, this plugin attempts to analyze the flood 
 frequencies by regressing them against various basin characteristics.
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
 # Import the code for the dialog
from ffa_dialog import FFADialog

#Need to import QObject and SIGNAL as well as defaults from plugin builder
from PyQt4.QtCore import QObject, QThread, QMutex
#Need QMessageBox to show click info in message box
from PyQt4.QtGui import QMessageBox

from HydroData.services.USGSPeak import USGSPeakWorker
#Import QGS libraries
from qgis.gui import QgsMapToolEmitPoint
from qgis.core import QgsMapLayerRegistry, QgsMessageLog

from Parse import parseFloodPeakWorker

class FFATool(QObject):
    """Implementation of the FFA Tool, part of the HydroData tool set."""
    
    def __init__(self, iface):
        QObject.__init__(self)
        # Save reference to the QGIS interface
        self.iface = iface
        #Get reference to canvas and click functions
        self.canvas = self.iface.mapCanvas()
        #Tool get get a QgsPoint from each click on the map
        self.clickTool = QgsMapToolEmitPoint(self.canvas)
        #Connect the cnavasClicked event to the handleMouseDown callback
        self.clickTool.canvasClicked.connect(self.handleMouseDown)
        # Create the dialog and keep reference
        self.dlg = FFADialog()

    def handleMouseDown(self, point, button):
        #QMessageBox.information( self.iface.mainWindow(), "Info", "X,Y = %s,%s"%( str(point.x()), str(point.y()) ) )
        self.dlg.clearTextBrowser()
        self.dlg.setTextBrowser( str(point.x())+' , '+str(point.y())+'\n' )
    
    def workerError(self, e, exception_string):
        QgsMessageLog.logMessage('Worker thread raised an exception:\n{}'.format(exception_string), 'Debug', QgsMessageLog.INFO)
        print e
        print exception_string
    
    #Once we know the download finished, try to parse the aquired data
    def peakDownloadFinished(self):
        #Create a thread to parse the data, FIXME this could possibly be done by the download thread to save thread creation???
        thread = QThread(self)
        worker = self.worker = parseFloodPeakWorker()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        #Print the periodic status messages to the text browser
        worker.status.connect(self.dlg.addToTextBrowser)
        worker.error.connect(self.workerError)
        #Connect these signals so we know when the thread finishes
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(thread.quit)
        thread.start()
        
    #Gather the input from the correct source and call the FFA service
    def downloadPeaks(self, stations):
        #Create a new thread to download the usgs data
        thread = QThread(self)
        worker = self.worker = USGSPeakWorker(stations)
        worker.moveToThread(thread)
        #Connect the slots
        thread.started.connect(worker.run)
        #Print the periodic status messages to the text browser
        worker.status.connect(self.dlg.addToTextBrowser)
        worker.error.connect(self.workerError)
        #When done, call the NWISWorkerFinish to handle results
        #worker.finished.connect()
        #Clean up the thread
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        worker.finished.connect(self.peakDownloadFinished)
        worker.finished.connect(thread.quit)
        thread.start()
    
    #Moderate the steps in aquiring, parsing, and processing flood peak data
    def runFFA(self):
        stations = []
        #TODO/FIXME Need to ensure that layer has a 'SiteCode' attribute, or take the ID as input to lookup site numbers
        if self.dlg.selectFeatures.isChecked():
            QgsMessageLog.logMessage("Using selected points", 'Debug', QgsMessageLog.INFO)
            features = self.canvas.currentLayer().selectedFeatures()
        else:
            QgsMessageLog.logMessage("Using selected layer", 'Debug', QgsMessageLog.INFO)
            features = self.canvas.currentLayer().getFeatures()
        for f in features:
            stations.append(f.attribute('SiteCode'))
        
        self.dlg.setTextBrowser('Downloading flood peak data...')
        self.downloadPeaks(stations)
        
        #Now parse the data
        
    def run(self):
        """Run method that performs all the real work"""
        #TODO clean up tmp directory when finished???
        #set the click tool
        self.canvas.setMapTool(self.clickTool)
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            self.runFFA()
        else:
            pass
