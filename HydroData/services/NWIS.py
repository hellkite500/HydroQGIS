# -*- coding: utf-8 -*-
"""
/***************************************************************************
NWIS worker class for calling NWIS web service via QThread
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
from PyQt4.QtCore import QObject, pyqtSignal, QVariant
from qgis.core import QgsVectorLayer, QgsField, QgsFeature, QgsGeometry, QgsPoint
import urllib2
import json
import math

class NWISWorker(QObject):
    """Worker thread for calling NWIS web service"""
    def __init__(self, point, distance):
        QObject.__init__(self)
        self.distance = float(distance)
        self.point = point
        self.killed = False
        
    def run(self):
        """
        Uses the USGS Instantaneous Values REST Web Service to return a list of
        USGS stream gages within a given distance of lon, lat.
        
        Parameters:
                lat: the latitude in decimal degrees of the point
                lon: the longitude in decimal degrees of the point
                distance: the shortest distance from the point of interest
                    the edge of a boundary box centered on the point
        
        Returns:
                results: list object containing 6 lists as follows,
                    0: list of Site Names
                    1: list of Site Latitudes
                    2: list of Site Longitudes
                    3: list of Site Networks
                    4: list of Site Network Codes
                    5: list of Site Codes
        """
        #NJF Setup parameters to original function
        lon = self.point.x()
        lat = self.point.y()
        distance = self.distance
        ret = []
        
        #define limits of contiguous United States
        NorthLimit = 49.00239
        SouthLimit = 24.52083
        EastLimit = -66.94977
        WestLimit = -124.66722

        #validate coordinates
        if (lon > EastLimit or lon < WestLimit or lat > NorthLimit or lat < SouthLimit):
            self.status.emit('Coordinates outside of valid range: ' + \
                'lat=%s, lon=%s.\nPlease double check your coordinates.'%(lat, lon))
            self.finished.emit(False, ret)
            return
        #self.status.emit('Lat: %f, Lon: %f, Dist: %d'%(lat,lon,distance))
        try:
            self.status.emit('Searching for NWIS Stations')
            #define latitude/longitude box
            r = 3959                                    #radius of the Earth in miles
            delSig = distance / r                       #change in latitude in radians
            delPhi = math.degrees(delSig)               #change in latitude in decimal degrees
            radLat = math.radians(lat)                  #convert latitude to radians
            delLam = math.acos((math.cos(delSig)-math.sin(radLat)*math.sin(radLat)) \
                /(math.cos(radLat)*math.cos(radLat)))   #change in longitude in radians
            degLam = math.degrees(delLam)               #change in longitude in decimal degrees
            wLon = round(lon - degLam, 6)               #western-most longitude in decimal degrees
            sLat = round(lat - delPhi, 6)               #southern-most latitude in decimal degrees
            eLon = round(lon + degLam, 6)               #eastern-most longitude in decimal degrees
            nLat = round(lat + delPhi, 6)               #northern-most latitude in decimal degrees
            check = (degLam * 2) * (delPhi * 2)         #product of angles that define search box

            #check that bounding box is within server limits
            if (check > 25):
                self.status.emit('Bounding box is too large at this latitude. ' + \
                    'd=%s miles.\nPlease choose a smaller distance.'%(distance))
                self.finished.emit(False, ret)
                return
            #self.status.emit('WLon: %f, SLat: %f, ELon: %f, NLat: %f, check: %f'%(wLon, sLat, eLon, nLat, check))
            #build USGS Instantaneous Values REST Web Service URL
            RESTurl = "http://waterservices.usgs.gov/nwis/iv/?" \
                + "format=json" \
                + "&bBox=%s,%s,%s,%s"%(wLon, sLat, eLon, nLat) \
                + "&parameterCd=00060,00065" \
                + "&siteType=ST"

            #load response into JSON object
            response = json.loads(urllib2.urlopen(RESTurl).read())
            
            #check for stations found
            if (len(response['value']['timeSeries']) < 1):
                self.status.emit('No stations found.')
                self.finished.emit(False, ret)
                return
            #create lists of relevant data
            index = 0       #last index of list of sites
            SiteName = []   #list of site names
            SiteLat = []    #list of site latitudes
            SiteLon = []    #list of site longitudes
            SiteNet = []    #list of site networks
            SiteNCd = []    #list of site network codes
            SiteCode = []   #list of site codes

            #load lists with relevant data from response
            """for i in response['value']['timeSeries']:
                SiteName.append(response['value']['timeSeries'][index] \
                ['sourceInfo']['siteName'])
                SiteLat.append(response['value']['timeSeries'][index]['sourceInfo'] \
                ['geoLocation']['geogLocation']['latitude'])
                SiteLon.append(response['value']['timeSeries'][index]['sourceInfo'] \
                ['geoLocation']['geogLocation']['longitude'])
                SiteNet.append(response['value']['timeSeries'][index]['variable'] \
                ['variableCode'][0]['network'])
                SiteNCd.append(response['value']['timeSeries'][index]['variable'] \
                ['variableCode'][0]['value'])
                SiteCode.append(response['value']['timeSeries'][index]['sourceInfo'] \
                ['siteCode'][0]['value'])
                index = index + 1
                #Loop shortened:
                for result in response['value']['timeSeries']:
                SiteName.append(result['sourceInfo']['siteName'])
                SiteLat.append(result['sourceInfo']['geoLocation']['geogLocation']['latitude'])
                SiteLon.append(result['sourceInfo']['geoLocation']['geogLocation']['longitude'])
                SiteNet.append(result['variable']['variableCode'][0]['network'])
                SiteNCd.append(result['variable']['variableCode'][0]['value'])
                SiteCode.append(result['sourceInfo']['siteCode'][0]['value'])
            """
            #print response['value']['timeSeries'][0]['sourceInfo']['siteCode']
            #TODO Can extend this to provide each variable as its own attribute
            sites = {}
            #For each result, get site information
            for result in response['value']['timeSeries']:
                #For each site code, setup its attributes
                #TODO what to do when there is more than one siteCode returned here???
                for code in result['sourceInfo']['siteCode']: 
                    #If we haven't seen this code yet, create an empty dict for adding to.
                    if code['value'] not in sites.keys():
                        sites[code['value']] = {'SiteName':'', 'SiteLat':'', 'SiteLon':'', 'SiteNet':[], 'SiteNCd':[]}
                    
                    sites[code['value']]['SiteName'] = result['sourceInfo']['siteName']
                    sites[code['value']]['SiteLat'] = result['sourceInfo']['geoLocation']['geogLocation']['latitude']
                    sites[code['value']]['SiteLon'] = result['sourceInfo']['geoLocation']['geogLocation']['longitude']
                    #TODO again, what to do with more than one variable code
                    sites[code['value']]['SiteNet'].append( result['variable']['variableCode'][0]['network'] )
                    sites[code['value']]['SiteNCd'].append( result['variable']['variableCode'][0]['value'] )
                    
            #Now create a point layer with the given sites to add to the map.
            layer = QgsVectorLayer('Point', 'NWIS Stations', 'memory')
            layer.startEditing()
            provider = layer.dataProvider()
            #TODO change attribute variable types???
            #Attributes that each point in the new layer will have
            attributes = [QgsField('SiteCode', QVariant.String), \
                          QgsField('SiteName', QVariant.String), \
                          QgsField('SiteLat', QVariant.Double), \
                          QgsField('SiteLong', QVariant.Double), \
                          QgsField('SiteNet', QVariant.String), \
                          QgsField('SiteNCd', QVariant.String)]
            provider.addAttributes(attributes)
            
            for k in sites.keys():
                site = sites[k]
                x = float(site['SiteLon'])
                y = float(site['SiteLat'])
                netString = ','.join(site['SiteNet'])
                NCdString = ','.join(site['SiteNCd'])
                feature = QgsFeature()
                feature.setGeometry(QgsGeometry.fromPoint(QgsPoint(x,y)))
                feature.setAttributes([k, site['SiteName'], y, x, netString, NCdString])
                provider.addFeatures([feature])

            layer.commitChanges()
            f = QgsFeature()
            features = layer.getFeatures()
            for f in features:
                print "F:",f.id(), f.attributes(), f.geometry().asPoint()
            
            self.status.emit('Finished searching for sites')
            self.finished.emit(True, layer)
        except Exception, e:
            import traceback
            self.error.emit(e, traceback.format_exc())
            self.status.emit("Error in NWIS Service Thread")
            #print e, traceback.format_exc()
            self.finished.emit(False, ret)

    status = pyqtSignal(str)
    error = pyqtSignal(Exception, basestring)
    finished = pyqtSignal(bool, object)

