# -*- coding: utf-8 -*-
"""
/***************************************************************************
 NWIS station search tool.
                                 A QGIS plugin
 This plugin seraches for stations with NWIS data in a particular bounding box.
                              -------------------
        begin                : 2014-11-30
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
from nwis_search_dialog import NWISsearchDialog

#Need to import QObject and SIGNAL as well as defaults from plugin builder
from PyQt4.QtCore import QObject, QThread
#Need QMessageBox to show click info in message box
from PyQt4.QtGui import QMessageBox

from HydroData.services.NWIS import NWISWorker

#Import QGS libraries
from qgis.gui import QgsMapToolEmitPoint
from qgis.core import QgsMapLayerRegistry, QgsMessageLog


class NWISsearchTool(QObject):
    """Implementation of the Station Search Tool, part of the HydroData tool set."""
    
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
        #QMessageBox.information( self.iface.mainWindow(), "Info", "connect = %s"%str(result) )
        
        # Create the dialog and keep reference
        self.dlg = NWISsearchDialog()
    
    def workerError(self, e, exception_string):
        QgsMessageLog.logMessage('Worker thread raised an exception:\n'.format(exception_string), level=QgsMessageLog.CRITICAL)
        print e
        print exception_string  
           
    def NWISWorkerFinish(self, success, layer):
        if success:
            QgsMapLayerRegistry.instance().addMapLayer(layer)
        
    
    def handleMouseDown(self, point, button):
        #QMessageBox.information( self.iface.mainWindow(), "Info", "X,Y = %s,%s"%( str(point.x()), str(point.y()) ) )
        self.dlg.clearTextBrowser()
        self.dlg.setTextBrowser( str(point.x())+' , '+str(point.y())+'\n' )
        distance = self.dlg.getDistance()
        #Create a new thread to call the NWIS web service
        thread = QThread(self)
        worker = self.worker = NWISWorker(point, distance)
        worker.moveToThread(thread)
        #Connect the slots
        thread.started.connect(worker.run)
        #Print the periodic status messages to the text browser
        worker.status.connect(self.dlg.addToTextBrowser)
        worker.error.connect(self.workerError)
        #When done, call the NWISWorkerFinish to handle results
        worker.finished.connect(self.NWISWorkerFinish)
        #Clean up the thread
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        worker.finished.connect(thread.quit)
        thread.start()
        
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
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass
        else:
            pass
