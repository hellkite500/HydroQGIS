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

#import worker thread classes
from Parse import parseFloodPeakWorker
from FFA_Util import ffaWorker

#import the pandas library
import pandas as pd

#import matplotlib for plotting results
import matplotlib.pylab as plt
"""
This structure is somewhat messy.  This particular tool has several steps, and different uses.
The current structure of this code is for each step to be executed in it's own thread.

This allows an insurance that certain steps complete before others, but still never hangs the UI.

Also, depending on future implementation, one may wish to processes already quired data in a different way.
This modularized design allows for the same code to be used to make this happen.
"""

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
        #print e
        #print exception_string
    
    #slot for recieving message when ffaWorker thread has finsihed
    def ffaFinished(self, success, freq_curv, name):
        if(success):
            #Can't plot in threads, so plot result when done!
            freq_curv.plot(label=name)
            plt.show()
    
    #When the parser finishes, we need to take the resulting dataframe
    #and perform some additional processing.
    def parserFinished(self, success):
        if success:
            #Create a thread to parse the data
            thread = QThread(self)
            worker = self.worker = ffaWorker()
            worker.moveToThread(thread)
            thread.started.connect(worker.run)
            #Print the periodic status messages to the text browser
            worker.status.connect(self.dlg.addToTextBrowser)
            worker.error.connect(self.workerError)
            #Connect these signals so we know when the thread finishes
            worker.finished.connect(self.ffaFinished)
            worker.finished.connect(worker.deleteLater)
            thread.finished.connect(thread.deleteLater)
            thread.finished.connect(thread.quit)
            thread.start()
    
    
    #Once we know the download finished, try to parse the aquired data
    def peakDownloadFinished(self, success):
        if success:
            #Create a thread to parse the data
            thread = QThread(self)
            worker = self.worker = parseFloodPeakWorker()
            worker.moveToThread(thread)
            thread.started.connect(worker.run)
            #Print the periodic status messages to the text browser
            worker.status.connect(self.dlg.addToTextBrowser)
            worker.error.connect(self.workerError)
            #Connect these signals so we know when the thread finishes
            worker.finished.connect(self.parserFinished)
            worker.finished.connect(worker.deleteLater)
            thread.finished.connect(thread.deleteLater)
            thread.finished.connect(thread.quit)
            thread.start()
        else:
            pass
    
    #Gather the input from the correct source and call the FFA service
    def downloadPeaks(self, stations):
        #FIXME!!!!!!!!!!!!!!!!!!!!!!!!!
        #FIXME this could be bad if two ffa's are running at a time (as the threading allows for) then
        #we have a race condition!!! Maybe have the user name the runs and warn about overwritting?
        #Or use a unique ID of some sort...but must do something!!!
        
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
        if len(stations) == 0:
            self.dlg.setTextBrowser('No stations selected!')
             # show the dialog
            self.dlg.show()
            # Run the dialog event loop
            result = self.dlg.exec_()
            # See if OK was pressed
            if result:
                self.runFFA()
            else:
                pass
        else:
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
