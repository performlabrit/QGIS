# -*- coding: utf-8 -*-

"""
***************************************************************************
    PointsToPaths.py
    ---------------------
    Date                 : April 2014
    Copyright            : (C) 2014 by Alexander Bruy
    Email                : alexander dot bruy at gmail dot com
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""
from builtins import str

__author__ = 'Alexander Bruy'
__date__ = 'April 2014'
__copyright__ = '(C) 2014, Alexander Bruy'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import os
from datetime import datetime

from qgis.PyQt.QtCore import QVariant
from qgis.core import (QgsApplication,
                       QgsFeature,
                       QgsFeatureSink,
                       QgsFields,
                       QgsField,
                       QgsGeometry,
                       QgsDistanceArea,
                       QgsProject,
                       QgsWkbTypes,
                       QgsProcessingUtils)

from processing.algs.qgis.QgisAlgorithm import QgisAlgorithm
from processing.core.parameters import ParameterVector
from processing.core.parameters import ParameterTableField
from processing.core.parameters import ParameterString
from processing.core.outputs import OutputVector
from processing.core.outputs import OutputDirectory
from processing.tools import dataobjects


class PointsToPaths(QgisAlgorithm):

    VECTOR = 'VECTOR'
    GROUP_FIELD = 'GROUP_FIELD'
    ORDER_FIELD = 'ORDER_FIELD'
    DATE_FORMAT = 'DATE_FORMAT'
    #GAP_PERIOD = 'GAP_PERIOD'
    OUTPUT_LINES = 'OUTPUT_LINES'
    OUTPUT_TEXT = 'OUTPUT_TEXT'

    def group(self):
        return self.tr('Vector creation tools')

    def __init__(self):
        super().__init__()

    def initAlgorithm(self, config=None):
        self.addParameter(ParameterVector(self.VECTOR,
                                          self.tr('Input point layer'), [dataobjects.TYPE_VECTOR_POINT]))
        self.addParameter(ParameterTableField(self.GROUP_FIELD,
                                              self.tr('Group field'), self.VECTOR))
        self.addParameter(ParameterTableField(self.ORDER_FIELD,
                                              self.tr('Order field'), self.VECTOR))
        self.addParameter(ParameterString(self.DATE_FORMAT,
                                          self.tr('Date format (if order field is DateTime)'), '', optional=True))
        #self.addParameter(ParameterNumber(
        #    self.GAP_PERIOD,
        #    'Gap period (if order field is DateTime)', 0, 60, 0))
        self.addOutput(OutputVector(self.OUTPUT_LINES, self.tr('Paths'), datatype=[dataobjects.TYPE_VECTOR_LINE]))
        self.addOutput(OutputDirectory(self.OUTPUT_TEXT, self.tr('Directory')))

    def name(self):
        return 'pointstopath'

    def displayName(self):
        return self.tr('Points to path')

    def processAlgorithm(self, parameters, context, feedback):
        layer = QgsProcessingUtils.mapLayerFromString(self.getParameterValue(self.VECTOR), context)
        groupField = self.getParameterValue(self.GROUP_FIELD)
        orderField = self.getParameterValue(self.ORDER_FIELD)
        dateFormat = str(self.getParameterValue(self.DATE_FORMAT))
        #gap = int(self.getParameterValue(self.GAP_PERIOD))
        dirName = self.getOutputValue(self.OUTPUT_TEXT)

        fields = QgsFields()
        fields.append(QgsField('group', QVariant.String, '', 254, 0))
        fields.append(QgsField('begin', QVariant.String, '', 254, 0))
        fields.append(QgsField('end', QVariant.String, '', 254, 0))
        writer = self.getOutputFromName(self.OUTPUT_LINES).getVectorWriter(fields, QgsWkbTypes.LineString, layer.crs(),
                                                                           context)

        points = dict()
        features = QgsProcessingUtils.getFeatures(layer, context)
        total = 100.0 / layer.featureCount() if layer.featureCount() else 0
        for current, f in enumerate(features):
            point = f.geometry().asPoint()
            group = f[groupField]
            order = f[orderField]
            if dateFormat != '':
                order = datetime.strptime(str(order), dateFormat)
            if group in points:
                points[group].append((order, point))
            else:
                points[group] = [(order, point)]

            feedback.setProgress(int(current * total))

        feedback.setProgress(0)

        da = QgsDistanceArea()
        da.setSourceCrs(layer.sourceCrs())
        da.setEllipsoid(QgsProject.instance().ellipsoid())

        current = 0
        total = 100.0 / len(points) if points else 1
        for group, vertices in list(points.items()):
            vertices.sort()
            f = QgsFeature()
            f.initAttributes(len(fields))
            f.setFields(fields)
            f['group'] = group
            f['begin'] = vertices[0][0]
            f['end'] = vertices[-1][0]

            fileName = os.path.join(dirName, '%s.txt' % group)

            with open(fileName, 'w') as fl:
                fl.write('angle=Azimuth\n')
                fl.write('heading=Coordinate_System\n')
                fl.write('dist_units=Default\n')

                line = []
                i = 0
                for node in vertices:
                    line.append(node[1])

                    if i == 0:
                        fl.write('startAt=%f;%f;90\n' % (node[1].x(), node[1].y()))
                        fl.write('survey=Polygonal\n')
                        fl.write('[data]\n')
                    else:
                        angle = line[i - 1].azimuth(line[i])
                        distance = da.measureLine(line[i - 1], line[i])
                        fl.write('%f;%f;90\n' % (angle, distance))

                    i += 1

            f.setGeometry(QgsGeometry.fromPolyline(line))
            writer.addFeature(f, QgsFeatureSink.FastInsert)
            current += 1
            feedback.setProgress(int(current * total))

        del writer
