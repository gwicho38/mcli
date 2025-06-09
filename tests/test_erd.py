#!/usr/bin/env python3
"""
Test script for graph transformation that doesn't rely on the module structure.
This script directly uses the core functions from generate_graph.py.
"""

import os
import json
import time
import pydot
from collections import defaultdict

# # Create a comprehensive sample graph data for testing that mimics the original realGraph.json
# SAMPLE_GRAPH_DATA = {
#     "type": "GlobalCanvasMergeGraphResult",
#     "graph": {
#         "m_vertices": {
#             "type": "Array<GlobalCanvasGraphNode<GlobalCanvasGraphNodeData>>",
#             "value": [
#                 # Primary entities
#                 {
#                     "type": "GlobalCanvasGraphEntityNode",
#                     "id": "ReliabilityAssetCase",
#                     "category": "Entity",
#                     "data": {
#                         "name": "ReliabilityAssetCase",
#                         "categoryMetadataIdentifier": "ReliabilityAssetCase",
#                         "package": "reliabilityAssetCase",
#                         "fields": [
#                             {"name": "vehicleAssetClass", "type": "AssetClass"},
#                             {"name": "currentState", "type": "CaseState"},
#                             {"name": "currentStateHistory", "type": "CaseStateHistory"},
#                             {"name": "facility", "type": "Facility"},
#                             {"name": "latestValidMxEffort", "type": "MxEffort"},
#                             {"name": "vehicle", "type": "ReliabilityAsset"},
#                             {"name": "alert", "type": "ReliabilityAssetAlert"},
#                             {"name": "firstAlert", "type": "ReliabilityAssetAlert"},
#                             {"name": "assignee", "type": "ReliabilityAssigneeTimedValue"},
#                             {"name": "priority", "type": "ReliabilityPriorityTimedValue"},
#                             {"name": "assigneeHistory", "type": "[CaseAssigneeHistory]"},
#                             {"name": "comments", "type": "[CaseComment]"},
#                             {"name": "priorityHistory", "type": "[CasePriorityHistory]"},
#                             {"name": "stateHistories", "type": "[CaseStateHistory]"},
#                             {"name": "transitions", "type": "[CaseStateTransition]"},
#                             {"name": "caseQuantityRelations", "type": "[CaseToPartQuantityRelation]"},
#                             {"name": "completeMxEfforts", "type": "[MxEffort]"},
#                             {"name": "validMxEfforts", "type": "[MxEffort]"},
#                             {"name": "readinessAlertRelations", "type": "[ReadinessAssetAlertToCaseRelation]"},
#                             {"name": "alerts", "type": "[ReadinessAssetAlert]"},
#                             {"name": "assignedAlerts", "type": "[ReadinessAssetAlert]"},
#                             {"name": "positionToFailureModeRelations", "type": "[ReadinessAssetPositionToFailureModeRelation]"},
#                             {"name": "alertRelations", "type": "[ReliabilityAssetAlertToCaseRelation]"},
#                             {"name": "failureModeRelations", "type": "[ReliabilityAssetCaseFailureModeRelation]"},
#                             {"name": "assetRelations", "type": "[ReliabilityAssetCaseToAssetRelation]"},
#                             {"name": "lastUpdatedDateHistory", "type": "[ReliabilityAssetCaseUpdateHistory]"},
#                             {"name": "alertAssets", "type": "[ReliabilityAsset]"},
#                             {"name": "allAssets", "type": "[ReliabilityAsset]"},
#                             {"name": "directAssets", "type": "[ReliabilityAsset]"},
#                             {"name": "workOrders", "type": "[WorkOrder]"},
#                             {"name": "alertFailureModes", "type": "[string]"},
#                             {"name": "collaborators", "type": "[string]"},
#                             {"name": "failureModeIds", "type": "[string]"},
#                             {"name": "failureModes", "type": "[string]"},
#                             {"name": "actioned", "type": "boolean"},
#                             {"name": "isAgendaItem", "type": "boolean"},
#                             {"name": "isLatestValidMxEffortComplete", "type": "boolean"},
#                             {"name": "mxVerified", "type": "boolean"},
#                             {"name": "outstanding", "type": "boolean"},
#                             {"name": "lastUpdatedDate", "type": "datetime"},
#                             {"name": "latestActivityTime", "type": "datetime"},
#                             {"name": "latestCommentCreationTime", "type": "datetime"},
#                             {"name": "latestStateCreationTime", "type": "datetime"},
#                             {"name": "estimatedCostOfUnplannedDowntime", "type": "double"},
#                             {"name": "estimatedCostOfUnplannedMaintenance", "type": "double"},
#                             {"name": "caseAgeInDays", "type": "int"},
#                             {"name": "numAssignedAlerts", "type": "int"},
#                             {"name": "numFeedbacks", "type": "int"},
#                             {"name": "numOpenWorkOrders", "type": "int"},
#                             {"name": "numOperationsSinceAlert", "type": "int"},
#                             {"name": "numOperationsSinceMaintenance", "type": "int"},
#                             {"name": "numTotalAlerts", "type": "int"},
#                             {"name": "numTotalAssets", "type": "int"},
#                             {"name": "numWorkOrders", "type": "int"},
#                             {"name": "assigneeName", "type": "string"},
#                             {"name": "caseNameAndDescription", "type": "string"},
#                             {"name": "description", "type": "string"},
#                             {"name": "id", "type": "string"},
#                             {"name": "latestActivity", "type": "string"},
#                             {"name": "latestActivityDisplayName", "type": "string"},
#                             {"name": "name", "type": "string"},
#                             {"name": "priorityValue", "type": "string"},
#                             {"name": "subHeaderText", "type": "string"},
#                             {"name": "topContributors", "type": "string"},
#                             {"name": "typeIdent", "type": "string"},
#                             {"name": "vehicleMajcom", "type": "string"}
#                         ]
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEntityNode",
#                     "id": "ReliabilityAssetAlert",
#                     "category": "Entity",
#                     "data": {
#                         "name": "ReliabilityAssetAlert",
#                         "categoryMetadataIdentifier": "ReliabilityAssetAlert",
#                         "package": "reliabilityAssetCase",
#                         "fields": [
#                             {"name": "parent", "type": "ReliabilityAsset"},
#                             {"name": "primaryModelOutput", "type": "ReliabilityAssetAlert.ModelOutput"},
#                             {"name": "triggeringModel", "type": "ReliabilityMlModel"},
#                             {"name": "timestamp", "type": "datetime"},
#                             {"name": "id", "type": "string"},
#                             {"name": "name", "type": "string"},
#                             {"name": "triggeringModelId", "type": "string"},
#                             {"name": "typeIdent", "type": "string"}
#                         ]
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEntityNode",
#                     "id": "ReadinessAssetAlert",
#                     "category": "Entity",
#                     "data": {
#                         "name": "ReadinessAssetAlert",
#                         "categoryMetadataIdentifier": "ReadinessAssetAlert",
#                         "package": "reliabilityAssetCase",
#                         "fields": [
#                             {"name": "failureMode", "type": "FailureMode"},
#                             {"name": "positionToFailureModeRelation", "type": "ReadinessAssetPositionToFailureModeRelation"},
#                             {"name": "operation", "type": "ReadinessOperation"},
#                             {"name": "parent", "type": "ReliabilityAsset"},
#                             {"name": "primaryModelOutput", "type": "ReliabilityAssetAlert.ModelOutput"},
#                             {"name": "assignedCase", "type": "ReliabilityAssetCase"},
#                             {"name": "triggeringModel", "type": "ReliabilityMlModel"},
#                             {"name": "assignee", "type": "User"},
#                             {"name": "assigneeHistory", "type": "[ReadinessAlertAssigneeHistory]"},
#                             {"name": "caseRelations", "type": "[ReadinessAssetAlertToCaseRelation]"},
#                             {"name": "isAssigned", "type": "boolean"},
#                             {"name": "isHighRisk", "type": "boolean"},
#                             {"name": "predictionTimestamp", "type": "datetime"},
#                             {"name": "timestamp", "type": "datetime"},
#                             {"name": "id", "type": "string"},
#                             {"name": "name", "type": "string"},
#                             {"name": "typeIdent", "type": "string"}
#                         ]
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEntityNode",
#                     "id": "Asset",
#                     "category": "Entity",
#                     "data": {
#                         "name": "Asset",
#                         "categoryMetadataIdentifier": "Asset",
#                         "package": "reliabilityAssetCase",
#                         "fields": [
#                             {"name": "assetClass", "type": "AssetClass"},
#                             {"name": "facility", "type": "Facility"},
#                             {"name": "parentAsset", "type": "ReliabilityAsset"},
#                             {"name": "childAssets", "type": "[ReliabilityAsset]"},
#                             {"name": "id", "type": "string"},
#                             {"name": "serialNumber", "type": "string"},
#                             {"name": "tailNumber", "type": "string"},
#                             {"name": "assetId", "type": "string"},
#                             {"name": "name", "type": "string"}
#                         ]
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEntityNode",
#                     "id": "ReliabilityAsset",
#                     "category": "Entity",
#                     "data": {
#                         "name": "ReliabilityAsset",
#                         "categoryMetadataIdentifier": "ReliabilityAsset",
#                         "package": "reliabilityAssetCase",
#                         "fields": [
#                             {"name": "assetClass", "type": "AssetClass"},
#                             {"name": "facility", "type": "Facility"},
#                             {"name": "parentAsset", "type": "ReliabilityAsset"},
#                             {"name": "childAssets", "type": "[ReliabilityAsset]"},
#                             {"name": "reliabilityAlerts", "type": "[ReliabilityAssetAlert]"},
#                             {"name": "readinessAlerts", "type": "[ReadinessAssetAlert]"},
#                             {"name": "name", "type": "string"},
#                             {"name": "serialNumber", "type": "string"},
#                             {"name": "id", "type": "string"},
#                             {"name": "assetId", "type": "string"}
#                         ]
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEntityNode",
#                     "id": "AssetType",
#                     "category": "Entity",
#                     "data": {
#                         "name": "AssetType",
#                         "categoryMetadataIdentifier": "AssetType",
#                         "package": "reliabilityAssetCase",
#                         "fields": [
#                             {"name": "assets", "type": "[Asset]"},
#                             {"name": "id", "type": "string"},
#                             {"name": "name", "type": "string"},
#                             {"name": "description", "type": "string"}
#                         ]
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEntityNode",
#                     "id": "CaseAssigneeHistory",
#                     "category": "Entity",
#                     "data": {
#                         "name": "CaseAssigneeHistory",
#                         "categoryMetadataIdentifier": "CaseAssigneeHistory",
#                         "package": "reliabilityAssetCase",
#                         "fields": [
#                             {"name": "parent", "type": "ReliabilityAssetCase"},
#                             {"name": "value", "type": "User"},
#                             {"name": "timestamp", "type": "datetime"},
#                             {"name": "attachedFileName", "type": "string"},
#                             {"name": "id", "type": "string"},
#                             {"name": "name", "type": "string"}
#                         ]
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEntityNode",
#                     "id": "ReadinessOperation",
#                     "category": "Entity",
#                     "data": {
#                         "name": "ReadinessOperation",
#                         "categoryMetadataIdentifier": "ReadinessOperation",
#                         "package": "reliabilityAssetCase",
#                         "fields": [
#                             {"name": "asset", "type": "ReliabilityAsset"},
#                             {"name": "alerts", "type": "[ReadinessAssetAlert]"},
#                             {"name": "isComplete", "type": "boolean"},
#                             {"name": "startTime", "type": "datetime"},
#                             {"name": "endTime", "type": "datetime"},
#                             {"name": "id", "type": "string"},
#                             {"name": "missionId", "type": "string"},
#                             {"name": "name", "type": "string"},
#                             {"name": "operationDurationMinutes", "type": "double"},
#                             {"name": "typeIdent", "type": "string"}
#                         ]
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEntityNode",
#                     "id": "MaintenanceAction",
#                     "category": "Entity",
#                     "data": {
#                         "name": "MaintenanceAction",
#                         "categoryMetadataIdentifier": "MaintenanceAction",
#                         "package": "reliabilityAssetCase",
#                         "fields": [
#                             {"name": "asset", "type": "ReliabilityAsset"},
#                             {"name": "relatedCase", "type": "ReliabilityAssetCase"},
#                             {"name": "isComplete", "type": "boolean"},
#                             {"name": "startTime", "type": "datetime"},
#                             {"name": "completionTime", "type": "datetime"},
#                             {"name": "estimatedCost", "type": "double"},
#                             {"name": "actualCost", "type": "double"},
#                             {"name": "id", "type": "string"},
#                             {"name": "actionType", "type": "string"},
#                             {"name": "description", "type": "string"},
#                             {"name": "name", "type": "string"},
#                             {"name": "status", "type": "string"},
#                             {"name": "workOrderId", "type": "string"}
#                         ]
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEntityNode",
#                     "id": "MaintenanceAssetAlert",
#                     "category": "Entity",
#                     "data": {
#                         "name": "MaintenanceAssetAlert",
#                         "categoryMetadataIdentifier": "MaintenanceAssetAlert",
#                         "package": "reliabilityAssetCase",
#                         "fields": [
#                             {"name": "asset", "type": "ReliabilityAsset"},
#                             {"name": "relatedCase", "type": "ReliabilityAssetCase"},
#                             {"name": "timestamp", "type": "datetime"},
#                             {"name": "severity", "type": "string"},
#                             {"name": "description", "type": "string"},
#                             {"name": "id", "type": "string"},
#                             {"name": "name", "type": "string"},
#                             {"name": "source", "type": "string"},
#                             {"name": "status", "type": "string"}
#                         ]
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEntityNode",
#                     "id": "CaseState",
#                     "category": "Entity",
#                     "data": {
#                         "name": "CaseState",
#                         "categoryMetadataIdentifier": "CaseState",
#                         "package": "reliabilityAssetCase",
#                         "fields": [
#                             {"name": "deleted", "type": "boolean"},
#                             {"name": "description", "type": "string"},
#                             {"name": "id", "type": "string"},
#                             {"name": "name", "type": "string"},
#                             {"name": "state", "type": "string"}
#                         ]
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEntityNode",
#                     "id": "CaseStateHistory",
#                     "category": "Entity",
#                     "data": {
#                         "name": "CaseStateHistory",
#                         "categoryMetadataIdentifier": "CaseStateHistory",
#                         "package": "reliabilityAssetCase",
#                         "fields": [
#                             {"name": "parent", "type": "ReliabilityAssetCase"},
#                             {"name": "state", "type": "CaseState"},
#                             {"name": "timestamp", "type": "datetime"},
#                             {"name": "id", "type": "string"},
#                             {"name": "name", "type": "string"}
#                         ]
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEntityNode",
#                     "id": "CasePriorityHistory",
#                     "category": "Entity",
#                     "data": {
#                         "name": "CasePriorityHistory",
#                         "categoryMetadataIdentifier": "CasePriorityHistory",
#                         "package": "reliabilityAssetCase",
#                         "fields": [
#                             {"name": "parent", "type": "ReliabilityAssetCase"},
#                             {"name": "timestamp", "type": "datetime"},
#                             {"name": "attachedFileName", "type": "string"},
#                             {"name": "id", "type": "string"},
#                             {"name": "name", "type": "string"},
#                             {"name": "value", "type": "string"}
#                         ]
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEntityNode",
#                     "id": "AssetClass",
#                     "category": "Entity",
#                     "data": {
#                         "name": "AssetClass",
#                         "categoryMetadataIdentifier": "AssetClass",
#                         "package": "reliabilityAssetCase",
#                         "fields": [
#                             {"name": "aircraftModel", "type": "AircraftModel"},
#                             {"name": "hierarchyTemplate", "type": "AssetHierarchyTemplate"},
#                             {"name": "failureModeLibrary", "type": "FailureModeLibrary"},
#                             {"name": "definitionVersion", "type": "ReliabilityAssetClassDefinitionVersion"},
#                             {"name": "childAssetClassRelations", "type": "[AssetClassParentChildRelation]"},
#                             {"name": "parentAssetClassRelations", "type": "[AssetClassParentChildRelation]"},
#                             {"name": "expectedSensors", "type": "[ExpectedSensor]"},
#                             {"name": "failureModes", "type": "[FailureMode]"},
#                             {"name": "pandaGroups", "type": "[PandaGroup]"},
#                             {"name": "directCases", "type": "[ReliabilityAssetCase]"},
#                             {"name": "assets", "type": "[ReliabilityAsset]"},
#                             {"name": "kpis", "type": "[string]"},
#                             {"name": "hasChildren", "type": "boolean"},
#                             {"name": "hasValidAlertsAndRootAssets", "type": "boolean"},
#                             {"name": "hasValidCases", "type": "boolean"},
#                             {"name": "expectedSensorCount", "type": "int"},
#                             {"name": "id", "type": "string"},
#                             {"name": "name", "type": "string"},
#                             {"name": "translatedName", "type": "string"},
#                             {"name": "typeIdent", "type": "string"}
#                         ]
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEntityNode",
#                     "id": "Facility",
#                     "category": "Entity",
#                     "data": {
#                         "name": "Facility",
#                         "categoryMetadataIdentifier": "Facility",
#                         "package": "reliabilityAssetCase",
#                         "fields": [
#                             {"name": "assets", "type": "[ReliabilityAsset]"},
#                             {"name": "cases", "type": "[ReliabilityAssetCase]"},
#                             {"name": "id", "type": "string"},
#                             {"name": "location", "type": "string"},
#                             {"name": "name", "type": "string"}
#                         ]
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEntityNode",
#                     "id": "MxEffort",
#                     "category": "Entity",
#                     "data": {
#                         "name": "MxEffort",
#                         "categoryMetadataIdentifier": "MxEffort",
#                         "package": "reliabilityAssetCase",
#                         "fields": [
#                             {"name": "asset", "type": "ReliabilityAsset"},
#                             {"name": "workOrder", "type": "WorkOrder"},
#                             {"name": "isComplete", "type": "boolean"},
#                             {"name": "creationTime", "type": "datetime"},
#                             {"name": "id", "type": "string"},
#                             {"name": "maintenanceAction", "type": "string"},
#                             {"name": "name", "type": "string"}
#                         ]
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEntityNode",
#                     "id": "WorkOrder",
#                     "category": "Entity",
#                     "data": {
#                         "name": "WorkOrder",
#                         "categoryMetadataIdentifier": "WorkOrder",
#                         "package": "reliabilityAssetCase",
#                         "fields": [
#                             {"name": "isComplete", "type": "boolean"},
#                             {"name": "creationTime", "type": "datetime"},
#                             {"name": "workDueDate", "type": "datetime"},
#                             {"name": "workEndDate", "type": "datetime"},
#                             {"name": "workStartDate", "type": "datetime"},
#                             {"name": "totalActCosts", "type": "decimal"},
#                             {"name": "apparentCause", "type": "string"},
#                             {"name": "assigneeName", "type": "string"},
#                             {"name": "causeText", "type": "string"},
#                             {"name": "codingIncludingTextField", "type": "string"},
#                             {"name": "comments", "type": "string"},
#                             {"name": "description", "type": "string"},
#                             {"name": "failureMode", "type": "string"},
#                             {"name": "functionalLocation", "type": "string"},
#                             {"name": "id", "type": "string"},
#                             {"name": "maintActivityType", "type": "string"},
#                             {"name": "name", "type": "string"},
#                             {"name": "partStatus", "type": "string"},
#                             {"name": "preventiveMaintenanceType", "type": "string"},
#                             {"name": "priority", "type": "string"},
#                             {"name": "priorityDescription", "type": "string"},
#                             {"name": "reasonCode", "type": "string"},
#                             {"name": "resolution", "type": "string"},
#                             {"name": "serviceGroup", "type": "string"},
#                             {"name": "serviceTeam", "type": "string"},
#                             {"name": "status", "type": "string"},
#                             {"name": "statusCode", "type": "string"},
#                             {"name": "symptomCode", "type": "string"},
#                             {"name": "typeIdent", "type": "string"},
#                             {"name": "uiPartStatus", "type": "string"},
#                             {"name": "workOrderNumber", "type": "string"},
#                             {"name": "workOrderPriority", "type": "string"},
#                             {"name": "workOrderType", "type": "string"},
#                             {"name": "workSubtype", "type": "string"},
#                             {"name": "workType", "type": "string"}
#                         ]
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEntityNode",
#                     "id": "CaseComment",
#                     "category": "Entity",
#                     "data": {
#                         "name": "CaseComment",
#                         "categoryMetadataIdentifier": "CaseComment",
#                         "package": "reliabilityAssetCase",
#                         "fields": [
#                             {"name": "parent", "type": "ReliabilityAssetCase"},
#                             {"name": "createdByUser", "type": "User"},
#                             {"name": "fileAttachments", "type": "[CaseCommentAttachment]"},
#                             {"name": "taggedUsers", "type": "[User]"},
#                             {"name": "isCloseComment", "type": "boolean"},
#                             {"name": "comment", "type": "string"},
#                             {"name": "id", "type": "string"},
#                             {"name": "name", "type": "string"},
#                             {"name": "url", "type": "string"}
#                         ]
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEntityNode",
#                     "id": "CaseCommentAttachment",
#                     "category": "Entity",
#                     "data": {
#                         "name": "CaseCommentAttachment",
#                         "categoryMetadataIdentifier": "CaseCommentAttachment",
#                         "package": "reliabilityAssetCase",
#                         "fields": [
#                             {"name": "parent", "type": "CaseComment"},
#                             {"name": "contentSize", "type": "int"},
#                             {"name": "contentType", "type": "string"},
#                             {"name": "id", "type": "string"},
#                             {"name": "name", "type": "string"},
#                             {"name": "url", "type": "string"}
#                         ]
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEntityNode",
#                     "id": "CaseStateTransition",
#                     "category": "Entity",
#                     "data": {
#                         "name": "CaseStateTransition",
#                         "categoryMetadataIdentifier": "CaseStateTransition",
#                         "package": "reliabilityAssetCase",
#                         "fields": [
#                             {"name": "from", "type": "CaseState"},
#                             {"name": "to", "type": "CaseState"},
#                             {"name": "trigger", "type": "TransitionTrigger"},
#                             {"name": "acl", "type": "[AclEntry]"},
#                             {"name": "userUpdatedFields", "type": "[string]"},
#                             {"name": "deleted", "type": "boolean"},
#                             {"name": "hidden", "type": "boolean"},
#                             {"name": "isValid", "type": "boolean"},
#                             {"name": "userOwned", "type": "boolean"},
#                             {"name": "condition", "type": "string"},
#                             {"name": "id", "type": "string"},
#                             {"name": "includeSpec", "type": "string"},
#                             {"name": "name", "type": "string"}
#                         ]
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEntityNode",
#                     "id": "CaseToPartQuantityRelation",
#                     "category": "Entity",
#                     "data": {
#                         "name": "CaseToPartQuantityRelation",
#                         "categoryMetadataIdentifier": "CaseToPartQuantityRelation",
#                         "package": "reliabilityAssetCase",
#                         "fields": [
#                             {"name": "failureMode", "type": "FailureMode"},
#                             {"name": "nsn", "type": "NationalStockNumber"},
#                             {"name": "assetCase", "type": "ReliabilityAssetCase"},
#                             {"name": "caseNeedsParts", "type": "boolean"},
#                             {"name": "quantityRequired", "type": "double"},
#                             {"name": "functionalLocation", "type": "string"},
#                             {"name": "id", "type": "string"},
#                             {"name": "name", "type": "string"}
#                         ]
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEntityNode",
#                     "id": "ReadinessAssetAlertToCaseRelation",
#                     "category": "Entity",
#                     "data": {
#                         "name": "ReadinessAssetAlertToCaseRelation",
#                         "categoryMetadataIdentifier": "ReadinessAssetAlertToCaseRelation",
#                         "package": "reliabilityAssetCase",
#                         "fields": [
#                             {"name": "from", "type": "ReadinessAssetAlert"},
#                             {"name": "to", "type": "ReliabilityAssetCase"},
#                             {"name": "id", "type": "string"},
#                             {"name": "name", "type": "string"}
#                         ]
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEntityNode",
#                     "id": "ReadinessAssetPositionToFailureModeRelation",
#                     "category": "Entity",
#                     "data": {
#                         "name": "ReadinessAssetPositionToFailureModeRelation",
#                         "categoryMetadataIdentifier": "ReadinessAssetPositionToFailureModeRelation",
#                         "package": "reliabilityAssetCase",
#                         "fields": [
#                             {"name": "targetAssetClass", "type": "AssetClass"},
#                             {"name": "targetPlatform", "type": "AssetClass"},
#                             {"name": "failureMode", "type": "FailureMode"},
#                             {"name": "id", "type": "string"},
#                             {"name": "name", "type": "string"},
#                             {"name": "projectId", "type": "string"},
#                             {"name": "targetFunctionalLocation", "type": "string"}
#                         ]
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEntityNode",
#                     "id": "ReliabilityAssetAlertToCaseRelation",
#                     "category": "Entity",
#                     "data": {
#                         "name": "ReliabilityAssetAlertToCaseRelation",
#                         "categoryMetadataIdentifier": "ReliabilityAssetAlertToCaseRelation",
#                         "package": "reliabilityAssetCase",
#                         "fields": [
#                             {"name": "from", "type": "ReliabilityAssetAlert"},
#                             {"name": "to", "type": "ReliabilityAssetCase"},
#                             {"name": "id", "type": "string"},
#                             {"name": "name", "type": "string"}
#                         ]
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEntityNode",
#                     "id": "ReliabilityAssetCaseToAssetRelation",
#                     "category": "Entity",
#                     "data": {
#                         "name": "ReliabilityAssetCaseToAssetRelation",
#                         "categoryMetadataIdentifier": "ReliabilityAssetCaseToAssetRelation",
#                         "package": "reliabilityAssetCase",
#                         "fields": [
#                             {"name": "to", "type": "ReliabilityAsset"},
#                             {"name": "from", "type": "ReliabilityAssetCase"},
#                             {"name": "id", "type": "string"},
#                             {"name": "name", "type": "string"}
#                         ]
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEntityNode",
#                     "id": "ReliabilityAssetCaseUpdateHistory",
#                     "category": "Entity",
#                     "data": {
#                         "name": "ReliabilityAssetCaseUpdateHistory",
#                         "categoryMetadataIdentifier": "ReliabilityAssetCaseUpdateHistory",
#                         "package": "reliabilityAssetCase",
#                         "fields": [
#                             {"name": "state", "type": "CaseState"},
#                             {"name": "thisCase", "type": "ReliabilityAssetCase"},
#                             {"name": "validMxEfforts", "type": "[MxEffort]"},
#                             {"name": "alerts", "type": "[ReadinessAssetAlert]"},
#                             {"name": "workOrders", "type": "[WorkOrder]"},
#                             {"name": "updatedTime", "type": "datetime"},
#                             {"name": "description", "type": "string"},
#                             {"name": "id", "type": "string"},
#                             {"name": "latestAssignee", "type": "string"},
#                             {"name": "name", "type": "string"}
#                         ]
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEntityNode",
#                     "id": "SubAsset",
#                     "category": "Entity",
#                     "data": {
#                         "name": "SubAsset",
#                         "categoryMetadataIdentifier": "SubAsset",
#                         "package": "reliabilityAssetCase",
#                         "fields": [
#                             {"name": "parentAsset", "type": "Asset"},
#                             {"name": "id", "type": "string"},
#                             {"name": "name", "type": "string"},
#                             {"name": "serialNumber", "type": "string"},
#                             {"name": "position", "type": "string"}
#                         ]
#                     }
#                 }
#             ]
#         },
#         "m_edges": {
#             "type": "Array<GlobalCanvasGraphEdge<GlobalCanvasGraphEdgeData>>",
#             "value": [
#                 # ReliabilityAssetCase to its direct children
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "ReliabilityAssetCase",
#                     "target": "ReliabilityAsset",
#                     "data": {
#                         "type": "relation"
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "ReliabilityAssetCase",
#                     "target": "CaseStateHistory",
#                     "data": {
#                         "type": "relation"
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "ReliabilityAssetCase",
#                     "target": "CaseState",
#                     "data": {
#                         "type": "relation"
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "ReliabilityAssetCase",
#                     "target": "MaintenanceAction",
#                     "data": {
#                         "type": "relation"
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "ReliabilityAssetCase",
#                     "target": "ReliabilityAssetAlert",
#                     "data": {
#                         "type": "relation"
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "ReliabilityAssetCase",
#                     "target": "CaseComment",
#                     "data": {
#                         "type": "relation"
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "ReliabilityAssetCase",
#                     "target": "CaseAssigneeHistory",
#                     "data": {
#                         "type": "relation"
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "ReliabilityAssetCase",
#                     "target": "CasePriorityHistory",
#                     "data": {
#                         "type": "relation"
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "ReliabilityAssetCase",
#                     "target": "CaseToPartQuantityRelation",
#                     "data": {
#                         "type": "relation"
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "ReliabilityAssetCase",
#                     "target": "ReadinessAssetAlert",
#                     "data": {
#                         "type": "relation"
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "ReliabilityAssetCase",
#                     "target": "WorkOrder",
#                     "data": {
#                         "type": "relation"
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "ReliabilityAssetCase",
#                     "target": "MxEffort",
#                     "data": {
#                         "type": "relation"
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "ReliabilityAssetCase",
#                     "target": "Facility",
#                     "data": {
#                         "type": "relation"
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "ReliabilityAssetCase",
#                     "target": "AssetClass",
#                     "data": {
#                         "type": "relation"
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "ReliabilityAssetCase",
#                     "target": "ReliabilityAssetCaseUpdateHistory",
#                     "data": {
#                         "type": "relation"
#                     }
#                 },
                
#                 # Asset to its children
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "Asset",
#                     "target": "AssetType",
#                     "data": {
#                         "type": "relation"
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "Asset",
#                     "target": "SubAsset",
#                     "data": {
#                         "type": "relation"
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "Asset",
#                     "target": "Facility",
#                     "data": {
#                         "type": "relation"
#                     }
#                 },
                
#                 # ReliabilityAsset to its children
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "ReliabilityAsset",
#                     "target": "AssetClass",
#                     "data": {
#                         "type": "relation"
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "ReliabilityAsset",
#                     "target": "Facility",
#                     "data": {
#                         "type": "relation"
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "ReliabilityAsset",
#                     "target": "ReliabilityAssetAlert",
#                     "data": {
#                         "type": "relation"
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "ReliabilityAsset",
#                     "target": "ReadinessAssetAlert",
#                     "data": {
#                         "type": "relation"
#                     }
#                 },
                
#                 # ReadinessAssetAlert relationships
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "ReadinessAssetAlert",
#                     "target": "ReliabilityAsset",
#                     "data": {
#                         "type": "relation"
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "ReadinessAssetAlert",
#                     "target": "ReadinessOperation",
#                     "data": {
#                         "type": "relation"
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "ReadinessAssetAlert",
#                     "target": "ReadinessAssetPositionToFailureModeRelation",
#                     "data": {
#                         "type": "relation"
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "ReadinessAssetAlert",
#                     "target": "ReliabilityAssetCase",
#                     "data": {
#                         "type": "relation"
#                     }
#                 },
                
#                 # ReadinessOperation relationships
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "ReadinessOperation",
#                     "target": "ReliabilityAsset",
#                     "data": {
#                         "type": "relation"
#                     }
#                 },
                
#                 # CaseComment relationships
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "CaseComment",
#                     "target": "CaseCommentAttachment",
#                     "data": {
#                         "type": "relation"
#                     }
#                 },
                
#                 # Various relation objects
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "ReliabilityAssetAlertToCaseRelation",
#                     "target": "ReliabilityAssetAlert",
#                     "data": {
#                         "type": "relation"
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "ReliabilityAssetAlertToCaseRelation",
#                     "target": "ReliabilityAssetCase",
#                     "data": {
#                         "type": "relation"
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "ReadinessAssetAlertToCaseRelation",
#                     "target": "ReadinessAssetAlert",
#                     "data": {
#                         "type": "relation"
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "ReadinessAssetAlertToCaseRelation",
#                     "target": "ReliabilityAssetCase",
#                     "data": {
#                         "type": "relation"
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "ReliabilityAssetCaseToAssetRelation",
#                     "target": "ReliabilityAsset",
#                     "data": {
#                         "type": "relation"
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "ReliabilityAssetCaseToAssetRelation",
#                     "target": "ReliabilityAssetCase",
#                     "data": {
#                         "type": "relation"
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "CaseToPartQuantityRelation",
#                     "target": "ReliabilityAssetCase",
#                     "data": {
#                         "type": "relation"
#                     }
#                 },
                
#                 # State relationships
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "CaseStateHistory",
#                     "target": "CaseState",
#                     "data": {
#                         "type": "relation"
#                     }
#                 },
#                 {
#                     "type": "GlobalCanvasGraphEdge",
#                     "source": "CaseStateTransition",
#                     "target": "CaseState",
#                     "data": {
#                         "type": "relation"
#                     }
#                 }
#             ]
#         }
#     }
# }

SAMPLE_GRAPH_DATA = {}
try:
    json_file_path = "/Users/lefv/repos/mcli/realGraph.json"
    with open(json_file_path, 'r') as f:
        SAMPLE_GRAPH_DATA = json.load(f)
except Exception as e:
    print(e)

# Import the core functions
def load_graph_data(json_file_path):
    """Load the graph data from a JSON file."""
    try:
        with open(json_file_path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        print("Attempting to fix the JSON file...")
        
        # Try to read the file and fix common JSON issues
        with open(json_file_path, 'r') as f:
            content = f.read()
        
        # Replace any trailing commas in arrays or objects
        content = content.replace(",]", "]").replace(",}", "}")
        
        # Create a fixed file
        fixed_file = json_file_path + ".fixed"
        with open(fixed_file, 'w') as f:
            f.write(content)
        
        print(f"Created fixed file: {fixed_file}")
        print("Trying to load the fixed file...")
        
        # Try loading the fixed file
        with open(fixed_file, 'r') as f:
            return json.load(f)

def build_adjacency_list(graph_data):
    """Build an adjacency list from the graph data."""
    # Extract vertices and edges
    vertices = graph_data["graph"]["m_vertices"]["value"]
    edges = graph_data["graph"]["m_edges"]["value"]
    
    # Create mapping of IDs to node info
    node_map = {node["id"]: node for node in vertices}
    
    # Build adjacency list (directed graph)
    adj_list = defaultdict(list)
    for edge in edges:
        source = edge["source"]
        target = edge["target"]
        adj_list[source].append(target)
    
    return node_map, adj_list

def count_descendants(node_id, adj_list, visited=None):
    """Count the number of descendants for a node (reachable subgraph size)."""
    if visited is None:
        visited = set()
    
    if node_id in visited:
        return 0
    
    visited.add(node_id)
    count = 1  # Count the node itself
    
    for neighbor in adj_list.get(node_id, []):
        if neighbor not in visited:
            count += count_descendants(neighbor, adj_list, visited)
    
    return count

def find_top_level_nodes(node_map, adj_list, top_n=10):
    """Find the top N nodes with the most descendants."""
    # Count descendants for each node
    descendant_counts = {}
    for node_id in node_map:
        descendant_counts[node_id] = count_descendants(node_id, adj_list)
    
    # Sort nodes by descendant count
    sorted_nodes = sorted(descendant_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Return top N nodes and their counts
    return [(node_id, count) for node_id, count in sorted_nodes[:top_n]]

def build_hierarchical_graph(top_level_nodes, node_map, adj_list, max_depth=2):
    """Build a hierarchical graph with top-level nodes as roots."""
    hierarchy = {}
    
    # For each top-level node, build its subgraph
    for node_id, _ in top_level_nodes:
        subgraph = {}
        visited = set()
        build_subgraph(node_id, node_map, adj_list, subgraph, visited, 0, max_depth)
        hierarchy[node_id] = subgraph
    
    return hierarchy

def build_subgraph(node_id, node_map, adj_list, subgraph, visited, current_depth, max_depth):
    """Recursively build a subgraph for a node up to max_depth."""
    if node_id in visited or current_depth > max_depth:
        return
    
    visited.add(node_id)
    subgraph[node_id] = {
        "node_info": node_map[node_id],
        "children": {}
    }
    
    if current_depth < max_depth:
        for child_id in adj_list.get(node_id, []):
            build_subgraph(child_id, node_map, adj_list, subgraph[node_id]["children"], 
                          visited, current_depth + 1, max_depth)

def extract_fields_from_node(node_data):
    """Extract fields from node data for display in the table."""
    fields = []
    
    # If this is an entity node, extract fields from the data
    if node_data.get("category") == "Entity":
        # Get fields from node data
        if "data" in node_data:
            # Add package as a field
            if "package" in node_data["data"]:
                fields.append(("package", node_data["data"]["package"]))
            
            # Add name if available
            if "name" in node_data["data"]:
                fields.append(("name", node_data["data"]["name"]))
            
            # Add categoryMetadataIdentifier if available
            if "categoryMetadataIdentifier" in node_data["data"]:
                fields.append(("type", node_data["data"]["categoryMetadataIdentifier"]))
    
    # Add id field
    if "id" in node_data:
        fields.append(("id", node_data["id"]))
    
    # Add category field
    if "category" in node_data:
        fields.append(("category", node_data["category"]))
    
    return fields

def create_table_html(entity, node_data, font_size=10):
    """Create HTML table-style label for a node."""
    fields = extract_fields_from_node(node_data)
    
    # Sanitize entity name
    entity = entity.replace(".", "_")
    entity = entity.replace("<", "[")
    entity = entity.replace(">", "]")
    
    # Start the HTML table
    html = f'<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="2">'
    
    # Header row
    html += f'<TR><TD PORT="header" COLSPAN="2" BGCOLOR="lightgrey"><B><FONT POINT-SIZE="{font_size+2}">{entity}</FONT></B></TD></TR>'
    
    # Add "Data" section if there are fields
    if fields:
        html += f'<TR><TD COLSPAN="2" BGCOLOR="#E0E0E0"><B><FONT POINT-SIZE="{font_size}">Fields</FONT></B></TD></TR>'
        
        # Add each field
        for field_name, field_value in fields:
            # Convert < and > to [ and ] for HTML compatibility
            if field_value:
                field_value = str(field_value).replace("<", "[").replace(">", "]")
            html += f'<TR><TD><FONT POINT-SIZE="{font_size}">{field_name}</FONT></TD><TD><FONT POINT-SIZE="{font_size}">{field_value}</FONT></TD></TR>'
    
    # Close the table
    html += "</TABLE>>"
    return html

def create_dot_graph(hierarchy, root_node_id, max_depth=2):
    """Create a DOT graph visualization from the hierarchical model."""
    graph = pydot.Dot(
        graph_type="digraph", 
        rankdir="TB", 
        splines="ortho", 
        bgcolor="white",
        label=f"Hierarchical Model for {root_node_id}",
        fontsize=14,
        labelloc="t"
    )
    
    # Track nodes that have been added to avoid duplicates
    added_nodes = set()
    # Track node depths for coloring
    node_depths = {root_node_id: 0}
    
    # Add nodes and edges recursively
    add_nodes_and_edges(graph, hierarchy, root_node_id, added_nodes, node_depths, max_depth)
    
    # Create a subgraph to force the root node to be at the top
    root_subgraph = pydot.Subgraph(rank="min")
    root_subgraph.add_node(pydot.Node(root_node_id))
    graph.add_subgraph(root_subgraph)
    
    return graph

def add_nodes_and_edges(graph, hierarchy, node_id, added_nodes, node_depths, max_depth, current_depth=0):
    """Recursively add nodes and edges to the graph."""
    if current_depth > max_depth or node_id in added_nodes:
        return
    
    # Find the node data
    # For root nodes, it's in hierarchy[node_id][node_id]
    # For other nodes, we need to look through the hierarchy to find them
    if node_id in hierarchy:
        node_data = hierarchy[node_id][node_id]["node_info"]
    else:
        # Look for this node in other nodes' children
        for root in hierarchy:
            found = find_node_in_hierarchy(hierarchy[root], node_id)
            if found:
                node_data = found
                break
        else:
            # Node not found in hierarchy
            print(f"Warning: Node {node_id} not found in hierarchy")
            return
    
    # Record node depth
    node_depths[node_id] = current_depth
    
    # Create HTML table label for this node
    node_label = create_table_html(node_id, node_data)
    
    # Determine node color based on depth
    if current_depth == 0:
        bg_color = "lightblue"  # Root node
    elif current_depth == 1:
        bg_color = "#E6F5FF"  # First level
    else:
        bg_color = "#F0F8FF"  # Deeper levels
    
    # Create the node with HTML table label
    dot_node = pydot.Node(
        node_id,
        shape="none",  # Using 'none' to allow custom HTML table
        label=node_label,
        style="filled",
        fillcolor=bg_color,
        margin="0"
    )
    
    graph.add_node(dot_node)
    added_nodes.add(node_id)
    
    # Add edges to children if not at max depth
    if current_depth < max_depth:
        # Get children - different path depending on whether this is a root node
        if node_id in hierarchy:
            children = hierarchy[node_id][node_id]["children"]
        else:
            # Look up this node's children
            children_container = find_children_container(hierarchy, node_id)
            if not children_container:
                return
            children = children_container
        
        for child_id in children:
            # Add an edge from this node to the child
            edge = pydot.Edge(
                node_id,
                child_id,
                dir="both",
                arrowtail="none",
                arrowhead="normal",
                constraint=True,
                color="black",
                penwidth=1.5
            )
            graph.add_edge(edge)
            
            # Recursively add the child node and its children
            if child_id not in added_nodes:
                add_nodes_and_edges(graph, hierarchy, child_id, added_nodes, node_depths, max_depth, current_depth + 1)

def find_node_in_hierarchy(subgraph, target_node):
    """Find a node's data in the hierarchy."""
    # Check each node in the subgraph
    for node_id, node_data in subgraph.items():
        if node_id == target_node:
            return node_data["node_info"]
        
        # Recursively check children
        if "children" in node_data:
            result = find_node_in_hierarchy(node_data["children"], target_node)
            if result:
                return result
    
    return None

def find_children_container(hierarchy, parent_node):
    """Find a node's children container in the hierarchy."""
    # Check each root node
    for root_id, root_data in hierarchy.items():
        # Check if the target is a direct child of this root
        if parent_node in root_data[root_id]["children"]:
            return root_data[root_id]["children"][parent_node]["children"]
        
        # Look in the children of this root's children
        for child_id, child_data in root_data[root_id]["children"].items():
            if parent_node == child_id:
                return child_data["children"]
            
            # Could add deeper searching if needed
    
    return {}

def main():
    """Run the test with a depth of 3."""
    # Define depth
    depth = 3
    print(f"Testing ERD generation with a depth of {depth}...")
    
    try:
        # Use the sample graph data directly
        graph_data = SAMPLE_GRAPH_DATA
        
        # Build the adjacency list
        node_map, adj_list = build_adjacency_list(graph_data)
        
        # Find the top-level nodes
        top_nodes = find_top_level_nodes(node_map, adj_list, top_n=3)
        
        # Print the top nodes and their descendant counts
        print("\nTop-level nodes (with most descendants):")
        for node_id, count in top_nodes:
            print(f"  {node_id}: {count} descendants")
        
        # Build the hierarchical graph
        hierarchy = build_hierarchical_graph(top_nodes, node_map, adj_list, max_depth=depth)
        
        # Generate file paths
        timestamp = str(int(time.time() * 1000000))
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
        os.makedirs(output_dir, exist_ok=True)
        
        # For each top-level node, generate DOT and PNG files
        print("\nGenerating DOT and PNG visualizations...")
        for root_node_id, descendant_count in top_nodes:
            # Create the DOT graph
            dot_graph = create_dot_graph(hierarchy, root_node_id, max_depth=depth)
            
            # Define file paths
            dot_file = os.path.join(output_dir, f"{root_node_id}_depth{depth}_{timestamp}.dot")
            png_file = os.path.join(output_dir, f"{root_node_id}_depth{depth}_{timestamp}.png")
            
            # Save the files
            dot_graph.write_raw(dot_file)
            dot_graph.write_png(png_file)
            
            print(f"  Generated files for {root_node_id}:")
            print(f"    DOT: {dot_file}")
            print(f"    PNG: {png_file}")
        
        print("\nERD generation completed successfully!")
        
    except Exception as e:
        print(f"Error during ERD generation: {e}")

if __name__ == "__main__":
    main()