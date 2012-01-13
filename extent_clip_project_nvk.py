# Creates a polygon from your current view extent
# Author:  Sebastian Araya (Adapted from ESRI's Resource Center Code Sample: 'Polygon example')
# Date:    March 1, 2011
# Version: working to be ArcGIS 10.0 / Toolbox
# Added to by Nathaniel V. KELSO
# Date:    April 28, 2011

# WARNING: Only optimized for single dataframe MXD files
# WARNING: Only optimized for loose themes, not grouped themes

import arcpy                                    #basic shit
import arcpy.mapping                            #basic shit
#import time                                    #future progress bar
#import sys                                     #future progress bar
import Tkinter, tkFileDialog                    #for GUI interface
from tkFileDialog import Directory              #for GUI interface
import os, glob                                 #to get the MXD file name
#from ScriptUtils import *                      #for user alert dialog at the end

#Overwrite pre-existing files
arcpy.env.overwriteOutput = True                #default should be True; NOTE: Will not overwrite ArcMap schema locked SHPS
useDataFrameProjection = True                   #default should be True -- assuming user does this before
forceGeographicPrjExport = False                #default should be False, True is good for getting to Azimuth
geoPrjDef = r"C:\\Program Files\\ArcGIS\\Desktop10.0\\Coordinate Systems\\Geographic Coordinate Systems\\World\\WGS 1984.prj"
useExtentOfSelectedFeatures = False             #default: False -- assuming user does this before
useThemeNotFilename = True                      # When False, it uses the file's file name, not the TOC theme name
skipAndRemoveInvisibleLayers = True             #default: True  -- might not deal well with layers inside groups
removeNullResultsFromTOC = True                        #default should be True
deleteNullResultSHPs = True                     #default should be True, only acted on if removeNullResults
deleteNullResultThemesInMXD = True              #default should be True, only acted on if removeNullResults
reprojectDataFrameToAlbers = False              #default should be True
saveOutAIFile = True
filename_whitespace = "_"
clipper_ship_name = "_neatline_clip_extent"     #include _ prefix so it sorts better
clipPrefix = ""
clipPostfix = ""
inMxd = arcpy.mapping.MapDocument("Current")
#inMxd = arcpy.mapping.MapDocument("C:\\ProjectFiles\\2011\\arc10tests\\play.mxd")
#outDir = r"C:\\ProjectFiles\\2011\\arc10tests\\clips\\"
outMXD_postfix = "_clip_prj"
_extSpanXScaler = 0.1                 # Default is 0.1 for 10% larger than view
_extSpanYScaler = 0.1                 # Default is 0.1 for 10% larger than view
themesRemovedCount = 0

try:
    mxd = inMxd

    pathDir = glob.glob(mxd.filePath)
    for filePath in pathDir:
        print os.path.basename(filePath)
        pathFileName = os.path.basename(filePath)
        pathFileName = os.path.splitext(pathFileName)[0]

    outFileName = pathFileName + outMXD_postfix

    # Where are we putting the results?
    dirname = tkFileDialog.askdirectory()
    print dirname
    outDir = dirname + "/"
    outMxd = outDir + outFileName + ".mxd"
    outAI = outDir + outFileName + ".ai"

    #Get the active dataframe in that document (assumes 0 is active, which is not true)
    df = arcpy.mapping.ListDataFrames(mxd)[0]
    # find the name of the active view, then get matching DF objects, assume
    # the first is the one we want (that there aren't multiple DF with the same name)    
    #df = arcpy.mapping.ListDataFrames(mxd, mxd.activeView)[0]

    if useExtentOfSelectedFeatures:
        df.zoomToSelectedFeatures()

    ext = df.extent

    print "we got this loaded: " + mxd.filePath
    print "XMin: %f" % (ext.XMin)
    print "YMin: %f" % (ext.YMin)
    print "XMax: %f" % (ext.XMax)
    print "YMax: %f" % (ext.YMax)
    print "pathDir: %s" % (pathDir)

    # Do we want to expand our window a smidgen?
    _extXSpan = ext.XMax - ext.XMin
    _extYSpan = ext.YMax - ext.YMin

    _extXMin = ext.XMin - _extXSpan * _extSpanXScaler
    _extYMin = ext.YMin - _extYSpan * _extSpanYScaler
    _extXMax = ext.XMax + _extXSpan * _extSpanXScaler
    _extYMax = ext.YMax + _extYSpan * _extSpanYScaler

    # A list of features and coordinate pairs
    # order of nodes coords does not matter
    # extent usage: [lower left, lower right, upper right, upper left]
    # usage:[[[x,y], [x,y], [x,y], [x,y], etc...]] 'coords of nodes
    coordList = [[[_extXMin,_extYMin], [_extXMax,_extYMin], [_extXMax,_extYMax], [_extXMin,_extYMax]]]

    # Create empty Point and Array objects
    point = arcpy.Point()
    array = arcpy.Array()

    # A list that will hold each of the Polygon objects
    featureList = []

    # For each coordinate pair, set the x,y properties and add to the Array object.
    for feature in coordList:
        for coordPair in feature:
            point.X = coordPair[0]
            point.Y = coordPair[1]
            array.add(point)

        # Add the first point of the array in to close off the polygon
        array.add(array.getObject(0))

        # Create a Polygon object based on the array of points
        polygon = arcpy.Polygon(array)

        # Clear the array for future use
        array.removeAll()

        # Append to the list of Polygon objects
        featureList.append(polygon)

    # Create a copy of the Polygon objects, by using featureList as input to 
    # the CopyFeatures tool.
    # Note: Apply the spatial reference projection to the SHP
    arcpy.env.outputCoordinateSystem = df.spatialReference
    arcpy.CopyFeatures_management(featureList, outDir + clipper_ship_name + ".shp")

    print "Done with clip setup, now applying that clip to each layer in the document"

    # Now clip each of the themes in the source MXD's active data frame to that extent
    # NOTE: Freaks out if a group is found
    wrksp = outDir
    # Note: File path is relative to your active workspace, set above
    clipper_ship = clipper_ship_name

    fcCount = 0
    for lyr in arcpy.mapping.ListLayers(mxd,"",df):
        fcCount += 1
        
    # http://help.arcgis.com/en/arcgisdesktop/10.0/help/index.html#/SetProgressor/000v0000000v000000/    
    #arcpy.SetProgressor("step", "Clipping shapes...", 0,fcCount, 1)

    for lyr in arcpy.mapping.ListLayers(mxd,"",df):
        if lyr.isFeatureLayer:
            #print "found a feature layer"
            #arcpy.SetProgressorLabel("Loading " + lyr.name + "...")

            # Local variables:
            if useThemeNotFilename:
               input_name = lyr.name
            else:
                input_name = lyr.datasetName

            print input_name

            # Don't clip a feature with itself
            if  clipper_ship == input_name:
                print "Skipping the clipper ship, next!"
                continue
            
            if skipAndRemoveInvisibleLayers:
                #Leave the print commented outn as lyr.visible apparently throws an error when added to string
                #print "Layer visibility: " + lyr.visible
                if lyr.visible == False:
                    print "Removing invisible layer: " + lyr.name
                    arcpy.mapping.RemoveLayer(df, lyr)
                    themesRemovedCount += 1
                    continue

            # Make pretty output names            
            output_path_with_filename = wrksp
            
            if clipPrefix == "":
                output_path_with_filename += clipPrefix + input_name
            else:
                output_path_with_filename += clipPrefix + filename_whitespace + input_name
                
            if clipPostfix == "":
                output_path_with_filename += clipPostfix
            else:
                output_path_with_filename += filename_whitespace + clipPostfix
                
            #print output_path_with_filename
            output_path_with_filename = output_path_with_filename + ".shp"
            arcpy.env.overwriteOutput = False
            # http://help.arcgis.com/en/arcgisdesktop/10.0/help/index.html#/CreateUniqueName/000v00000020000000/
            # Beware that not all results in the same run will share the same number postfix
            output_path_with_filename = arcpy.CreateUniqueName( output_path_with_filename )            
            print output_path_with_filename

            # Process: Clip
            # Should the output projection be to the extent or to the raw input data?
            # Note: The environment was previously set to the dataframe
            if useDataFrameProjection == False:
                arcpy.env.outputCoordinateSystem = lyr.spatialReference
            # Note: This overrides the dataFrame projection if that flag is also set
            if forceGeographicPrjExport:
                arcpy.env.outputCoordinateSystem = geoPrjDef

            arcpy.Clip_analysis(lyr, clipper_ship, output_path_with_filename, "")

            #TODO: As the layers are processed below, repoint the workspace of that layer to the new files
            # The result is now the layer[0] of the document?
            # This might not always be the case as ArcMap interleaves the new layer into
            # the nearest theme of same pt. line. poly type
            clipResultLayer = arcpy.mapping.ListLayers(mxd,"",df)[0]
            # http://help.arcgis.com/en/arcgisdesktop/10.0/help/index.html#//00s300000039000000.htm
            arcpy.mapping.RemoveLayer(df, clipResultLayer)
            # print "the newest layer is: " + clip_result_layer.name
            # Apparently that clip function doesn't return the result, boo

            #As the layers are processed below, repoint the workspace of that layer to the new files
            #http://help.arcgis.com/en/arcgisdesktop/10.0/help/index.html#/Updating_and_fixing_data_sources_with_arcpy_mapping/00s30000004p000000/
            lyr.replaceDataSource( wrksp, "SHAPEFILE_WORKSPACE", input_name, True )
                            
            # How many features are present in the new SHP?
            exported_feature_count = arcpy.GetCount_management( output_path_with_filename )
            print exported_feature_count

            # Should we clean up null datasets?
            if removeNullResultsFromTOC:
               if exported_feature_count == 0:
                   print "removing..."
                   #delete the SHP?
                   if deleteNullResultSHPs:
                       arcpy.Delete_managment( output_path_with_filename,"" )
                   #also delete the Layer?
                   if deleteNullResultThemesInMXD:
                       arcpy.mapping.RemoveLayer( df, lyr )
                   themesRemovedCount += 1

            #Should we apply the the rule of 1/6th to our extent and set the DF to Albers?
            if reprojectDataFrameToAlbers:
                print "albers, todo list"
                #reference var: ext.XMin,ext.YMin,ext.XMax,ext.YMax
                #If larger than a certain span, use Robinson?
                #http://help.arcgis.com/en/arcgisdesktop/10.0/help/index.html#//001700000079000000.htm
                #sr = arcpy.CreateSpatialReference_management("",fc1,"","","",fcList)
                #http://forums.esri.com/Thread.asp?c=93&f=1729&t=151534
                #spref = "GEOGCS['GCS_WGS_1984',DATUM['D_WGS_1984',SPHEROID['WGS_1984',6378137.0,298.257223563]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]]", "DHDN_To_WGS84_C3" 
                #Coordinate_System = "GEOGCS['GCS_North_American_1983',DATUM['D_North_American_1983',SPHEROID['GRS_1980',6378137.0,298.257222101]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]]"
                #XY_Domain = "-10000.000000 -10000.000000 11474.836450 11474.836450"
                #Spatial_Reference = gp.CreateSpatialReference_management(Coordinate_System,"#",XY_Domain,"#","#","#","#")
                #tempWorkspace = os.path.dirname(os.path.abspath(sys.argv[0]))
                #srCOMObject = getSpatialRefCOMObject(Spatial_Reference,tempWorkspace)
        #arcpy.SetProgressorPosition()
    #arcpy.ResetProgressor()

    # Remove the clipper ship layer    
    clipResultLayer = arcpy.mapping.ListLayers(mxd,"",df)[0]
    # http://help.arcgis.com/en/arcgisdesktop/10.0/help/index.html#//00s300000039000000.htm
    arcpy.mapping.RemoveLayer(df, clipResultLayer)

    arcpy.env.overwriteOutput = True

    # Save out a new copy of the MXD 
    mxd.saveACopy(outMxd)

    if saveOutAIFile:
        arcpy.mapping.ExportToAI(mxd, outAI )

    #print "Removed " + themesRemovedCount + " invisible / null themes"

    print "--------- Success!"
    #raise StandardError, "Done: BUT BIG WARNING!!!!!\nDo not save save this MXD. Close it and open the new one in the specified project folder. If you save this MXD, it will combust, loosing reference to original data sources."
    #arcpy.AddMessage("Done: BUT BIG WARNING!!!!!\nDo not save save this MXD. Close it and open the new one in the specified project folder. If you save this MXD, it will combust, loosing reference to original data sources.")
except:
    print "--------- FAIL (sad face) ----"
    #arcpy.AddMessage("FAIL: Things are broken.")