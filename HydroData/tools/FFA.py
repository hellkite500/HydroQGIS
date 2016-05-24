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

#Import the custom probability scale for use with plotting frequency curves
import ProbScale

#Need to import QObject and SIGNAL as well as defaults from plugin builder
from PyQt4.QtCore import QObject, QThread, QMutex
#Need QMessageBox to show click info in message box
from PyQt4.QtGui import QMessageBox, QDialogButtonBox

from HydroData.services.USGSPeak import USGSPeakWorker
#Import QGIS libraries
from qgis.core import QgsMapLayerRegistry, QgsMessageLog, QgsMapLayer

#import worker thread classes
from Parse import parseFloodPeakWorker
from FFA_Util import ffaWorker

#import the pandas library
import pandas as pd

#import matplotlib for plotting results
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter, FixedLocator

#Get OS module for path mangling
import os
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
        # Create the dialog and keep reference
        self.dlg = FFADialog()
        #Variable to store output directory path
        self.output_path = ''

    def workerError(self, e, exception_string):
        QgsMessageLog.logMessage('Worker thread raised an exception:\n{}'.format(exception_string), 'Debug', QgsMessageLog.INFO)
        #print e
        #print exception_string
    
    #slot for recieving message when ffaWorker thread has finsihed
    def ffaFinished(self, success, results):
        if(success):
            QgsMessageLog.logMessage(str(len(results)), 'Print', QgsMessageLog.INFO)
            for name, data in results.iteritems():
                pp = data['positions'] 
                conf = data['confidence']
                data['curve'].index = data['curve'].index.map(lambda x:x*100)
                conf.index = conf.index.map(lambda x:x*100)
                pp['percent_ex'] = pp['Exceedance']*100
                
                plt.figure(figsize=(19, 10), dpi=100)

                axes = data['curve'].plot(title='Flood Frequency Curve for '+name, label='Final Frequency Curve')
                axes.legend(['Final Frequency Curve'])

                conf.plot(y='Q_U', ax = axes, style='--', label='Upper 5% confidence')
                conf.plot(y='Q_L', ax = axes, style='--', label='Lower 95% confidence')
                pp.plot(x='percent_ex', y='Q', ax=axes, style='o', label='Recorded Events')   
                
                axes.set_ylabel('Discharge in CFS')
                axes.set_xlabel('Exceedance Probability')
                plt.setp(plt.xticks()[1], rotation=45)
                #Adjust the scales of the x and y axis
                axes.set_yscale('log', basey=10, subsy=[2,3,4,5,6,7,8,9])
                axes.set_xscale('prob_scale', upper=98, lower=.2)
                #Adjust the yaxis labels and format
                axes.yaxis.set_minor_locator(FixedLocator([200, 500, 1500, 2500, 3500, 4500, 5000, 6000, 7000, 8000, 9000, 15000, 20000, 25000, 30000, 35000, 40000, 45000, 50000]))
                axes.yaxis.set_minor_formatter(FormatStrFormatter('%d'))
                axes.yaxis.set_major_formatter(FormatStrFormatter('%d'))
                
                #Finally set the y-limit of the plot to be reasonable
                axes.set_ylim((0, 2*pp['Q'].max()))
                #Invert the x-axis
                axes.invert_xaxis()
                #Turn on major and minor grid lines
                axes.grid(which='both', alpha=.9)
                #to change alpha of major and minor independently, uncomment below and change 'both' above to 'major'
                #axes.grid(which='minor', alpha=.9)
                plt.tight_layout()
                if self.output_path:
                    #make a subdirectory for each station's analysis
                    path = os.path.join(self.output_path, name+'_ffa')
                    if not os.path.exists(path):
                        os.makedirs(path)
                    #Save the results
                    plt.savefig(os.path.join(path, name+'.pdf'))
                    index = 'Exceedance Probability'
                    head = ['Computed Return Flow (CFS)']
                    data['curve'].to_csv(os.path.join(path, name+'_final_freq.csv'), header=head, index_label = index)
                    
                    index = ['Station', 'Year']
                    cols = ['Rank','Exceedance','PP','Q']
                    head = ['Rank', 'Exceedance Probability', 'Weibull Plotting Position', 'Flow (CFS)']
                    data['positions'].to_csv(os.path.join(path, name+'_plotting_positions.csv'), header=head, columns=cols, index_label = index)
                    
                    cols = ['Q_U', 'Q_L']
                    index = 'Exceedance Probability'
                    head = ['Upper 5% confidence', 'Lower 95% confidence']
                    data['confidence'].to_csv(os.path.join(path, name+'_5_95_confidence_intervals.csv'), header=head, columns=cols, index_label = index)
            #finally show the generated plots
            if self.dlg.showPlots.isChecked():
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
        #we have a race condition!!! Maybe have the user name the runs and warn about overwritting? Append time stamps???
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
            station = str(f[str(self.dlg.idFieldComboBox.currentText())])
            if len(station) < 8:
                #TODO/FIXME Bad hack to adjust for QGIS trying to convert station ID's to numerical types
                #And then cutting off leading 0's.  Which happen to be important when querying USGS!!!
                station = "0"*(8-len(station))+station
            stations.append(station)
            QgsMessageLog.logMessage('Adding station: {}\n'.format(station), 'Debug', QgsMessageLog.INFO)
            
        
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
    """
    def inputChanged(self):
        #If using selected feature(s), look up features attributes
        if self.dlg.selectFeatures.isChecked():
            attributes = [a.name() for a in self.canvas.currentLayer().selectedFeatures()[0].attributes()]
            self.dlg.idFieldComboBox.addItems(attributes)
        else:
            #if using an entire layer, lookup layer attributes
            attributes = [a.name() for a in self.canvas.currentLayer().pendingFields()]
            self.dlg.idFieldComboBox.addItems(attributes)
    """
        
    def run(self):
        """Run method that performs all the real work"""
        self.dlg.setTextBrowser("WARNING: Not all stations are suitable for general flood frequency analysis."\
                                +" This tool will perform flood frequency analysis regardless of a station's suitability."\
                                +" Users are encouraged to identify suitable stations from the Hydro Climatic Data Network or the USGS GagesII datasets.")
        #TODO clean up tmp directory when finished???
        # show the dialog and hook the radio button listeners
        #Make sure dialog's comboBox is populated for selecting SiteCode field
        #Doesn't matter if using whole layer or selected, since selected is a subset of layer ;)
        attributes = []
        layer = self.canvas.currentLayer()
        if layer is None or layer.type() != QgsMapLayer.VectorLayer : 
            self.dlg.button_box.button(QDialogButtonBox.Ok).setEnabled(False)
            self.dlg.setTextBrowser('Not station input layer detected, please cancel and select a point layer or a set of station features.')
        else:
            self.dlg.button_box.button(QDialogButtonBox.Ok).setEnabled(True)
            attributes = [a.name() for a in self.canvas.currentLayer().pendingFields()]
        self.dlg.idFieldComboBox.clear()
        self.dlg.idFieldComboBox.addItems(attributes)
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            self.output_path = self.dlg.save_edit.text()
            if self.output_path:
                self.dlg.setTextBrowser('Saving to '+self.output_path)
            else:
                self.dlg.setTextBrowser('No directory given, not saving')
            self.runFFA()
        else:
            pass
