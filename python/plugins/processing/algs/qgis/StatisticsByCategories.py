# -*- coding: utf-8 -*-

"""
***************************************************************************
    StatisticsByCategories.py
    ---------------------
    Date                 : September 2012
    Copyright            : (C) 2012 by Victor Olaya
    Email                : volayaf at gmail dot com
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

__author__ = 'Victor Olaya'
__date__ = 'September 2012'
__copyright__ = '(C) 2012, Victor Olaya'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

from qgis.core import (QgsApplication,
                       QgsFeatureSink,
                       QgsStatisticalSummary,
                       QgsProcessingUtils)
from processing.core.outputs import OutputTable
from processing.algs.qgis.QgisAlgorithm import QgisAlgorithm
from processing.core.parameters import ParameterVector
from processing.core.parameters import ParameterTableField


class StatisticsByCategories(QgisAlgorithm):

    INPUT_LAYER = 'INPUT_LAYER'
    VALUES_FIELD_NAME = 'VALUES_FIELD_NAME'
    CATEGORIES_FIELD_NAME = 'CATEGORIES_FIELD_NAME'
    OUTPUT = 'OUTPUT'

    def group(self):
        return self.tr('Vector table tools')

    def __init__(self):
        super().__init__()

    def initAlgorithm(self, config=None):
        self.addParameter(ParameterVector(self.INPUT_LAYER,
                                          self.tr('Input vector layer')))
        self.addParameter(ParameterTableField(self.VALUES_FIELD_NAME,
                                              self.tr('Field to calculate statistics on'),
                                              self.INPUT_LAYER, ParameterTableField.DATA_TYPE_NUMBER))
        self.addParameter(ParameterTableField(self.CATEGORIES_FIELD_NAME,
                                              self.tr('Field with categories'),
                                              self.INPUT_LAYER, ParameterTableField.DATA_TYPE_ANY))

        self.addOutput(OutputTable(self.OUTPUT, self.tr('Statistics by category')))

    def name(self):
        return 'statisticsbycategories'

    def displayName(self):
        return self.tr('Statistics by categories')

    def processAlgorithm(self, parameters, context, feedback):
        layer = QgsProcessingUtils.mapLayerFromString(self.getParameterValue(self.INPUT_LAYER), context)
        valuesFieldName = self.getParameterValue(self.VALUES_FIELD_NAME)
        categoriesFieldName = self.getParameterValue(self.CATEGORIES_FIELD_NAME)

        output = self.getOutputFromName(self.OUTPUT)
        valuesField = layer.fields().lookupField(valuesFieldName)
        categoriesField = layer.fields().lookupField(categoriesFieldName)

        features = QgsProcessingUtils.getFeatures(layer, context)
        total = 100.0 / layer.featureCount() if layer.featureCount() else 0
        values = {}
        for current, feat in enumerate(features):
            feedback.setProgress(int(current * total))
            attrs = feat.attributes()
            try:
                value = float(attrs[valuesField])
                cat = str(attrs[categoriesField])
                if cat not in values:
                    values[cat] = []
                values[cat].append(value)
            except:
                pass

        fields = ['category', 'min', 'max', 'mean', 'stddev', 'sum', 'count']
        writer = output.getTableWriter(fields)
        stat = QgsStatisticalSummary(QgsStatisticalSummary.Min | QgsStatisticalSummary.Max |
                                     QgsStatisticalSummary.Mean | QgsStatisticalSummary.StDevSample |
                                     QgsStatisticalSummary.Sum | QgsStatisticalSummary.Count)

        for (cat, v) in list(values.items()):
            stat.calculate(v)
            record = [cat, stat.min(), stat.max(), stat.mean(), stat.sampleStDev(), stat.sum(), stat.count()]
            writer.addRecord(record)
