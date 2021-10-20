# Created by julien piccini
# email : piccini.julien@gmail.com
import json
from copy import deepcopy
from pathlib import Path
from typing import IO, Union, List
from collections import defaultdict, deque
import time
import logging

# Non standard libraries
import pandas as pd
from cjapy import config, connector
from .workspace import Workspace
from .requestCreator import RequestCreator

JsonOrDataFrameType = Union[pd.DataFrame, dict]
JsonListOrDataFrameType = Union[pd.DataFrame, List[dict]]


class CJA:
    """
    Class that instantiate a connection to a single CJA API connection.
    You can pass a logging object to log information.
    """

    loggingEnabled = False
    logger = None

    def __init__(
        self,
        config_object: dict = config.config_object,
        header: dict = config.header,
        loggingObject: dict = None,
    ) -> None:
        """
        Instantiate the class with the information provided.
        Arguments:
            loggingObject : OPTIONAL :If you want to set logging capability for your actions.
            header : REQUIRED : config header loaded (DO NOT MODIFY)
            config_object : REQUIRED : config object loaded (DO NOT MODIFY)
        """
        if loggingObject is not None and sorted(
            ["level", "stream", "format", "filename", "file"]
        ) == sorted(list(loggingObject.keys())):
            self.loggingEnabled = True
            self.logger = logging.getLogger(f"{__name__}.login")
            self.logger.setLevel(loggingObject["level"])
            formatter = logging.Formatter(loggingObject["format"])
            if loggingObject["file"]:
                fileHandler = logging.FileHandler(loggingObject["filename"])
                fileHandler.setFormatter(formatter)
                self.logger.addHandler(fileHandler)
            if loggingObject["stream"]:
                streamHandler = logging.StreamHandler()
                streamHandler.setFormatter(formatter)
                self.logger.addHandler(streamHandler)
        self.connector = connector.AdobeRequest(
            config_object=config_object,
            header=header,
            loggingEnabled=self.loggingEnabled,
            logger=self.logger,
        )
        self.header = self.connector.header
        self.endpoint = config.endpoints["global"]

    def getCurrentUser(self, admin: bool = False, useCache: bool = True) -> dict:
        """
        return the current user
        """
        if self.loggingEnabled:
            self.logger.debug("getCurrentUser start")
        path = "/aresconfig/users/me"
        params = {"useCache": useCache}
        if admin:
            params["expansion"] = "admin"
        res = self.connector.getData(self.endpoint + path, params=params)
        return res

    def getCalculatedMetrics(
        self,
        full: bool = False,
        inclType: str = "all",
        dataIds: str = None,
        ownerId: str = None,
        limit: int = 100,
        filterByIds: str = None,
        favorite: bool = False,
        approved: bool = False,
        output: str = "df",
    ) -> JsonListOrDataFrameType:
        """
        Returns a dataframe or the list of calculated Metrics.
        Arguments:
            full : OPTIONAL : returns all possible attributs if set to True (False by default)
            inclType : OPTIONAL : returns the type selected.Possible options are:
                - all (default)
                - shared
                - templates
                - unauthorized
                - deleted
                - internal
                - curatedItem
            dataIds : OPTIONAL : Filters the result to calculated metrics tied to a specific Data View ID (comma-delimited)
            ownerId : OPTIONAL : Filters the result by specific loginId.
            limit : OPTIONAL : Number of results per request (Default 100)
            filterByIds : OPTIONAL : Filter list to only include calculated metrics in the specified list (comma-delimited),
            favorite : OPTIONAL : If set to true, return only favorties calculated metrics. (default False)
            approved : OPTIONAL : If set to true, returns only approved calculated metrics. (default False)
            output : OPTIONAL : by default returns a "dataframe", can also return the list when set to "raw"
        """
        if self.loggingEnabled:
            self.logger.debug(f"getCalculatedMetrics start, output: {output}")
        path = "/calculatedmetrics"
        params = {
            "limit": limit,
            "includeType": inclType,
            "pagination": False,
            "page": 0,
        }
        if full:
            params[
                "expension"
            ] = "dataName,approved,favorite,shares,tags,sharesFullName,usageSummary,usageSummaryWithRelevancyScore,reportSuiteName,siteTitle,ownerFullName,modified,migratedIds,isDeleted,definition,authorization,compatibility,legacyId,internal,dataGroup,categories"
        if dataIds is not None:
            params["dataIds"] = dataIds
        if ownerId is not None:
            params["ownerId"] = ownerId
        if filterByIds is not None:
            params["filterByIds"] = filterByIds
        if favorite:
            params["favorite"] = favorite
        if approved:
            params["approved"] = approved
        res = self.connector.getData(self.endpoint + path, params=params)
        data = res["content"]
        lastPage = res.get("lastPage", True)
        while lastPage != True:
            params["page"] += 1
            res = self.connector.getData(self.endpoint + path, params=params)
            data += res["content"]
            lastPage = res.get("lastPage", True)
        if output == "df":
            df = pd.DataFrame(data)
            return df
        return res

    def getCalculatedMetricsFunctions(
        self, output: str = "raw"
    ) -> JsonListOrDataFrameType:
        """
        Returns a list of calculated metrics functions.
        Arguments:
            output : OPTIONAL : default to "raw", can return "dataframe".
        """
        if self.loggingEnabled:
            self.logger.debug(f"getCalculatedMetricsFunctions start, output: {output}")
        path = "/calculatedmetrics/functions"
        res = self.connector.getData(self.endpoint + path)
        if output == "dataframe":
            df = pd.DataFrame(res)
            return df
        return res

    def getCalculatedMetric(self, calcId: str = None, full: bool = True) -> dict:
        """
        Return a single calculated metrics based on its ID.
        Arguments:
            calcId : REQUIRED : The calculated metric
        """
        if calcId is None:
            raise ValueError("Requires a Calculated Metrics ID")
        if self.loggingEnabled:
            self.logger.debug(f"getCalculatedMetric start, id: {calcId}")
        path = f"/calculatedmetrics/{calcId}"
        params = {"includeHidden": True}
        if full:
            params[
                "expansion"
            ] = "approved,favorite,shares,tags,sharesFullName,usageSummary,usageSummaryWithRelevancyScore,reportSuiteName,siteTitle,ownerFullName,modified,migratedIds,isDeleted,definition,authorization,compatibility,legacyId,internal,dataGroup,categories"
        res = self.connector.getData(self.endpoint + path, params=params)
        return res

    def createCalculatedMetric(self, data: dict = None) -> dict:
        """
        Create a calculated metrics based on the dictionary.
        Arguments:
            data : REQUIRED : dictionary that will set the creation.
        """
        if data is None:
            raise ValueError("Require a dictionary to create the calculated metrics")
        if self.loggingEnabled:
            self.logger.debug(f"createCalculatedMetric start")
        path = "/calculatedmetrics"
        res = self.connector.postData(self.endpoint + path, data=data)
        return res

    def validateCalculatedMetric(self, data: dict = None) -> dict:
        """
        Validate a calculated metrics definition dictionary.
        Arguments:
            data : REQUIRED : dictionary that will set the creation.
        """
        if data is None or type(data) == dict:
            raise ValueError("Require a dictionary to create the calculated metrics")
        if self.loggingEnabled:
            self.logger.debug(f"validateCalculatedMetric start")
        path = "/calculatedmetrics/validate"
        res = self.connector.postData(self.endpoint + path, data=data)
        return res

    def deleteCalculateMetrics(self, calcId: str = None) -> dict:
        """
        Delete a calculated metrics based on its ID.
        Arguments:
            calcId : REQUIRED : The calculated metrics ID that will be deleted.
        """
        if calcId is None:
            raise ValueError("requires a calculated metrics ID")
        if self.loggingEnabled:
            self.logger.debug(f"deleteCalculateMetrics start, id: {calcId}")
        path = f"/calculatedmetrics/{calcId}"
        res = self.connector.deleteData(self.endpoint + path)
        return res

    def updateCalculatedMetrics(self, calcId: str = None, data: dict = None) -> dict:
        """
        Will overwrite the calculated metrics object with the new object (PUT method)
        Arguments:
            calcId : REQUIRED : The calculated metric ID to be updated
            data : REQUIRED : The dictionary that will overwrite.
        """
        if calcId is None:
            raise ValueError("Require a calculated metrics")
        if data is None or type(data) == dict:
            raise ValueError("Require a dictionary to create the calculated metrics")
        if self.loggingEnabled:
            self.logger.debug(f"updateCalculatedMetrics start, id: {calcId}")
        path = f"/calculatedmetrics/{calcId}"
        res = self.connector.putData(self.endpoint + path, data=data)
        return res

    def getShares(
        self,
        userId: str = None,
        inclType: str = "sharedTo",
        limit: int = 100,
        useCache: bool = True,
    ) -> dict:
        """
        Returns the elements shared.
        Arguments:
            userId : OPTIONAL : User ID to return details for.
            inclType : OPTIONAL : Include additional shares not owned by the user
            limit : OPTIONAL : number of result per request.
            useCache: OPTIONAL : Caching the result (default True)
        """
        if self.loggingEnabled:
            self.logger.debug(f"getShares start")
        params = {"limit": limit, "includeType": inclType, "useCache": useCache}
        path = "/componentmetadata/shares"
        if userId is not None:
            params["userId"] = userId
        res = self.connector.getData(self.endpoint + path, params=params)
        return res

    def getShare(self, shareId: str = None, useCache: bool = True) -> dict:
        """
        Returns a specific share element.
        Arguments:
            shareId : REQUIRED : the element ID.
            useCache : OPTIONAL : If caching the response (True by default)
        """
        if self.loggingEnabled:
            self.logger.debug(f"getShare start")
        params = {"useCache": useCache}
        if shareId is None:
            raise ValueError("Require an ID to retrieve the element")
        path = f"/componentmetadata/shares/{shareId}"
        res = self.connector.getData(self.endpoint + path, params=params)
        return res

    def deleteShare(self, shareId: str = None) -> dict:
        """
        Delete the shares of an element.
        Arguments:
            shareId : REQUIRED : the element ID to be deleted.
        """
        if shareId is None:
            raise ValueError("Require an ID to retrieve the element")
        if self.loggingEnabled:
            self.logger.debug(f"deleteShare start, id: {shareId}")
        path = f"/componentmetadata/shares/{shareId}"
        res = self.connector.deleteData(self.endpoint + path)
        return res

    def searchShares(
        self, data: dict = None, full: bool = False, limit: int = 10
    ) -> dict:
        """
        Search for multiple shares on component based on the data passed.
        Arguments:
            data : REQUIRED : dictionary specifying the search.
                example: {
                    "componentType": "string",
                    "componentIds": [
                        "string"
                    ],
                    "dataId": "string"
                }
            full : OPTIONAL : add additional data in the results.(Default False)
            limit : OPTIONAL : number of result per page (10 per default)
        """
        path = "/componentmetadata/shares/component/search"
        if data is None:
            raise ValueError("require a dictionary to specify the search.")
        if self.loggingEnabled:
            self.logger.debug(f"searchShares start")
        params = {"limit": limit}
        if full:
            params["expansion"] = "sharesFullName"
        res = self.connector.postData(self.endpoint + path, data=data, params=params)
        return res

    def updateShares(self, data: list = None, useCache: bool = True) -> dict:
        """
        Create one/many shares for one/many components at once. This is a PUT request.
        For each component object in the passed list, the given shares will replace the current set of shares for each component.
        Arguments:
            data : REQUIRED : list of dictionary containing the component to share.
                Example  [
                    {
                        "componentType": "string",
                        "componentId": "string",
                        "shares": [
                        {
                            "shareToId": 0,
                            "shareToImsId": "string",
                            "shareToType": "string",
                            "accessLevel": "string"
                        }
                        ]
                    }
                ]
            useCache : OPTIONAL : Boolean to use caching. Default is True.
        """
        if data is None or type(data) != list:
            raise ValueError("Require a list of element to share")
        if self.loggingEnabled:
            self.logger.debug(f"updateShares start")
        path = "/componentmetadata/shares"
        params = {"useCache": useCache}
        res = self.connector.putData(self.endpoint + path, params=params, data=data)
        return res

    def getTags(self, limit: int = 100) -> dict:
        """
        Return the tags for the company.
        Arguments:
            limit : OPTIONAL : Number of result per request.
        """
        if self.loggingEnabled:
            self.logger.debug(f"getTags start")
        path = "/componentmetadata/tags"
        params = {"limit": limit}
        res = self.connector.getData(self.endpoint + path, params=params)
        return res

    def createTags(self, data: list = None) -> dict:
        """
        Create tags for the company, attached to components.
        Arguments:
            data : REQUIRED : list of elements to passed.
                Example [
                    {
                        "id": 0,
                        "name": "string",
                        "description": "string",
                        "components": [
                        null
                        ]
                    }
                ]
        """
        path = "/componentmetadata/tags"
        if data is None and type(data) != list:
            raise ValueError("Require a list of tags to be created")
        if self.loggingEnabled:
            self.logger.debug(f"createTags start")
        res = self.connector.postData(self.endpoint + path, data=data)
        return res

    def deleteTags(self, componentIds: str = None, componentType: str = None) -> dict:
        """
        Removes all tags from the passed componentIds.
        Note that currently this is done in a single DB query, so there is a single combined response for the entire operation.
        Arguments:
            componentIds : REQUIRED : comma separated list of component ids to remove tags.
            componentType : REQUIRED : The component type to operate on.
                could be any of the following ; "segment" "dashboard" "bookmark" "calculatedMetric" "project" "dateRange" "metric" "dimension" "virtualReportSuite" "scheduledJob" "alert" "classificationSet" "dataView"
        """
        path = "/componentmetadata/tags"
        if componentIds is None:
            raise ValueError("Require a component ID")
        if componentType is None:
            raise ValueError("Require a component type")
        if componentType not in [
            "segment",
            "dashboard",
            "bookmark",
            "calculatedMetric",
            "project",
            "dateRange",
            "metric",
            "dimension",
            "virtualReportSuite",
            "scheduledJob",
            "alert",
            "classificationSet",
            "dataView",
        ]:
            raise KeyError("componentType not in the enum")
        if self.loggingEnabled:
            self.logger.debug(f"deleteTags start")
        params = {componentType: componentType, componentIds: componentIds}
        res = self.connector.deleteData(self.endpoint + path, params=params)
        return res

    def getTag(self, tagId: str = None) -> dict:
        """
        Return a single tag data by its ID.
        Arguments:
            tagId : REQUIRED : The tag ID to retrieve.
        """
        if tagId is None:
            raise ValueError("Require a tag ID")
        if self.loggingEnabled:
            self.logger.debug(f"getTag start, id: {tagId}")
        path = f"/componentmetadata/tags/{tagId}"
        res = self.connector.getData(self.endpoint + path)
        return res

    def getComponentTags(
        self, componentId: str = None, componentType: str = None
    ) -> dict:
        """
        Return tags for a component based on its ID and type.
        Arguments:
            componentId : REQUIRED : The component ID
            componentType : REQUIRED : The component type.
                could be any of the following ; "segment" "dashboard" "bookmark" "calculatedMetric" "project" "dateRange" "metric" "dimension" "virtualReportSuite" "scheduledJob" "alert" "classificationSet" "dataView"
        """
        if componentId is None:
            raise ValueError("Require a component ID")
        if componentType is None:
            raise ValueError("Require a component type")
        if componentType not in [
            "segment",
            "dashboard",
            "bookmark",
            "calculatedMetric",
            "project",
            "dateRange",
            "metric",
            "dimension",
            "virtualReportSuite",
            "scheduledJob",
            "alert",
            "classificationSet",
            "dataView",
        ]:
            raise KeyError("componentType not in the enum")
        if self.loggingEnabled:
            self.logger.debug(f"getComponentTags start")
        params = {"componentId": componentId, "componentType": componentType}
        path = "/componentmetadata/tags/search"
        res = self.connector.getData(self.endpoint + path, params=params)
        return res

    def updateTags(self, data: list = None) -> dict:
        """
        This endpoint allows many tags at once to be created/deleted. PUT method.
        Any tags passed to this endpoint will become the only tags for that componentId (all other tags will be removed).
        Arguments:
            data : REQUIRED : List of tags and component to be tagged.
                Example [
                            {
                                "componentType": "string",
                                "componentId": "string",
                                "tags": [
                                    {
                                        "id": 0,
                                        "name": "string",
                                        "description": "string",
                                        "components": [
                                        null
                                        ]
                                    }
                                ]
                            }
                        ]
        """
        path = "/componentmetadata/tags/tagitems"
        if data is None or type(data) != list:
            raise ValueError("Require a list of elements to update")
        if self.loggingEnabled:
            self.logger.debug(f"updateTags start")
        res = self.connector.putData(self.endpoint + path, data=data)
        return res

    def getTopItems(
        self,
        dataId: str = None,
        dimension: str = None,
        dateRange: str = None,
        startDate: str = None,
        endDate: str = None,
        limit: int = 100,
        searchClause: str = None,
        searchAnd: str = None,
        searchOr: str = None,
        searchNot: str = None,
        searchPhrase: str = None,
        remoteLoad: bool = True,
        xml: bool = False,
        noneValues: bool = True,
        **kwargs,
    ) -> dict:
        """
        Get the top X items (based on paging restriction) for the specified dimension and dataId. Defaults to last 90 days.
        Arguments:
            dataId : REQUIRED : Data Group or Data View to run the report against
            dimension : REQUIRED : Dimension to run the report against. Example: "variables/page"
            dateRange : OPTIONAL : Format: YYYY-MM-DD/YYYY-MM-DD (default 90 days)
            startDate: OPTIONAL : Format: YYYY-MM-DD
            endDate : OPTIONAL : Format: YYYY-MM-DD
            limit : OPTIONAL : Number of results per request (default 100)
            searchClause : OPTIONAL : General search string; wrap with single quotes. Example: 'PageABC'
            searchAnd : OPTIONAL : Search terms that will be AND-ed together. Space delimited.
            searchOr : OPTIONAL : Search terms that will be OR-ed together. Space delimited.
            searchNot : OPTIONAL : Search terms that will be treated as NOT including. Space delimited.
            searchPhrase : OPTIONAL : A full search phrase that will be searched for.
            remoteLoad : OPTIONAL : tells to load the result in Oberon if possible (default True)
            xml : OPTIONAL : returns the XML for debugging (default False)
            noneValues : OPTIONAL : Controls None values to be included (default True)
        """
        path = "/reports/topItems"
        if dataId is None:
            raise ValueError("Require a data ID")
        if dimension is None:
            raise ValueError("Require a dimension")
        if self.loggingEnabled:
            self.logger.debug(f"getTopItems start")
        params = {
            "dataId": dataId,
            "dimension": dimension,
            "limit": limit,
            "allowRemoteLoad": "true",
            "includeOberonXml": False,
            "lookupNoneValues": True,
        }
        if dateRange is not None:
            params["dateRange"] = dateRange
        if startDate is not None and endDate is not None:
            params["startDate"] = startDate
            params["endDate"] = endDate
        if searchClause is not None:
            params["search-clause"] = searchClause
        if searchAnd is not None:
            params["searchAnd"] = searchAnd
        if searchOr is not None:
            params["searchOr"] = searchOr
        if searchNot is not None:
            params["searchNot"] = searchNot
        if searchPhrase is not None:
            params["searchPhrase"] = searchPhrase
        if remoteLoad == False:
            params["allowRemoteLoad"] = "false"
        if xml:
            params["includeOberonXml"] = True
        if noneValues == False:
            params["lookupNoneValues"] = False
        res = self.connector.getData(self.endpoint + path, params=params)
        return res

    def getDimensions(
        self,
        dataviewId: str = None,
        full: bool = False,
        inclType: str = None,
        verbose: bool = False,
        output: str = "df",
    ) -> dict:
        """
        Used to retrieve dimensions for a dataview
        Arguments:
            dataviewId : REQUIRED : the Data View ID to retrieve data from.
            full : OPTIONAL : To add additional elements (default False)
            inclType : OPTIONAL : Possibility to add "hidden" values
            output : OPTIONAL : Type of output selected, either "df" (default) or "raw"
        """
        if dataviewId is None:
            raise ValueError("Require a Data View ID")
        if self.loggingEnabled:
            self.logger.debug(f"getDimensions start")
        path = f"/datagroups/data/{dataviewId}/dimensions"
        params = {}
        if full:
            params[
                "expansion"
            ] = "approved,favorite,tags,usageSummary,usageSummaryWithRelevancyScore,description,sourceFieldId,segmentable,required,hideFromReporting,hidden,includeExcludeSetting,fieldDefinition,bucketingSetting,noValueOptionsSetting,defaultDimensionSort,persistenceSetting,storageId,tableName,dataSetIds,dataSetType,type,schemaPath,hasData,sourceFieldName,schemaType,sourceFieldType,fromGlobalLookup,multiValued,precision"
        if inclType == "hidden":
            params["includeType"] = "hidden"
        res = self.connector.getData(
            self.endpoint + path, params=params, verbose=verbose
        )
        dimensions = res.get("content", [])
        if output == "df":
            df = pd.DataFrame(dimensions)
            return df
        return dimensions

    def getDimension(
        self, dataviewId: str = None, dimensionId: str = None, full: bool = True
    ):
        """
        Return a specific dimension based on the dataview ID and dimension ID passed.
        Arguments:
            dataviewId : REQUIRED : the Data View ID to retrieve data from.
            dimensionId : REQUIRED : the dimension ID to return
            full : OPTIONAL : To add additional elements (default True)
        """
        if dataviewId is None:
            raise ValueError("Require a Data View ID")
        if dimensionId is None:
            raise ValueError("Require a Dimension ID")
        if self.loggingEnabled:
            self.logger.debug(f"getDimension start, id: {dimensionId}")
        path = f"/datagroups/data/{dataviewId}/dimensions/{dimensionId}"
        params = {}
        if full:
            params[
                "expansion"
            ] = "approved,favorite,tags,usageSummary,usageSummaryWithRelevancyScore,description,sourceFieldId,segmentable,required,hideFromReporting,hidden,includeExcludeSetting,fieldDefinition,bucketingSetting,noValueOptionsSetting,defaultDimensionSort,persistenceSetting,storageId,tableName,dataSetIds,dataSetType,type,schemaPath,hasData,sourceFieldName,schemaType,sourceFieldType,fromGlobalLookup,multiValued,precision"
        res = self.connector.getData(self.endpoint + path, params=params)
        return res

    def getMetrics(
        self,
        dataviewId: str = None,
        full: bool = False,
        inclType: str = None,
        verbose: bool = False,
    ) -> dict:
        """
        Used to retrieve metrics for a dataview
        Arguments:
            dataviewId : REQUIRED : the Data View ID to retrieve data from.
            full : OPTIONAL : To add additional elements (default False)
            inclType : OPTIONAL : Possibility to add "hidden" values
        """
        if dataviewId is None:
            raise ValueError("Require a Data View ID")
        if self.loggingEnabled:
            self.logger.debug(f"getMetrics start")
        path = f"/datagroups/data/{dataviewId}/metrics"
        params = {}
        if full:
            params[
                "expansion"
            ] = "approved,favorite,tags,usageSummary,usageSummaryWithRelevancyScore,description,sourceFieldId,segmentable,required,hideFromReporting,hidden,includeExcludeSetting,fieldDefinition,bucketingSetting,noValueOptionsSetting,defaultDimensionSort,persistenceSetting,storageId,tableName,dataSetIds,dataSetType,type,schemaPath,hasData,sourceFieldName,schemaType,sourceFieldType,fromGlobalLookup,multiValued,precision"
        if inclType == "hidden":
            params["includeType"] = "hidden"
        res = self.connector.getData(
            self.endpoint + path, params=params, verbose=verbose
        )
        return res

    def getMetric(
        self, dataviewId: str = None, metricId: str = None, full: bool = True
    ):
        """
        Return a specific metric based on the dataview ID and dimension ID passed.
        Arguments:
            dataviewId : REQUIRED : the Data View ID to retrieve data from.
            metricId : REQUIRED : the metric ID to return
            full : OPTIONAL : To add additional elements (default True)
        """
        if dataviewId is None:
            raise ValueError("Require a Data View ID")
        if metricId is None:
            raise ValueError("Require a Dimension ID")
        if self.loggingEnabled:
            self.logger.debug(f"getMetric start, id: {metricId}")
        path = f"/datagroups/data/{dataviewId}/metrics/{metricId}"
        params = {}
        if full:
            params[
                "expansion"
            ] = "approved,favorite,tags,usageSummary,usageSummaryWithRelevancyScore,description,sourceFieldId,segmentable,required,hideFromReporting,hidden,includeExcludeSetting,fieldDefinition,bucketingSetting,noValueOptionsSetting,defaultDimensionSort,persistenceSetting,storageId,tableName,dataSetIds,dataSetType,type,schemaPath,hasData,sourceFieldName,schemaType,sourceFieldType,fromGlobalLookup,multiValued,precision"
        res = self.connector.getData(self.endpoint + path, params=params)
        return res

    def getDataViews(
        self,
        limit: int = 100,
        full: bool = True,
        output: str = "df",
        parentDataGroupId: str = None,
        externalIds: str = None,
        externalParentIds: str = None,
        includeType: str = "all",
        cached: bool = True,
        verbose: bool = False,
        **kwargs,
    ) -> JsonListOrDataFrameType:
        """
        Returns the Data View configuration.
        Arguments:
            limit : OPTIONAL : number of results per request (default 100)
            full : OPTIONAL : define if all possible information are returned (default True).
            output : OPTIONAL : Type of output selected, either "df" (default) or "raw"
            parentDataGroupId : OPTIONAL : Filters data views by a single parentDataGroupId
            externalIds : OPTIONAL : Comma-delimited list of external ids to limit the response with.
            externalParentIds : OPTIONAL : Comma-delimited list of external parent ids to limit the response with.
            dataViewIds : OPTIONAL : Comma-delimited list of data view ids to limit the response with.
            includeType : OPTIONAL : include additional DataViews not owned by user.(default "all")
            cached : OPTIONAL : return cached results
            verbose : OPTIONAL : add comments in the console.
        """
        if self.loggingEnabled:
            self.logger.debug(f"getDataViews start, output: {output}")
        path = "/datagroups/dataviews"
        params = {
            "limit": limit,
            "includeType": includeType,
            "cached": cached,
            "page": 0,
        }
        if full:
            params[
                "expansion"
            ] = "name,description,owner,isDeleted,parentDataGroupId,segmentList,currentTimezoneOffset,timezoneDesignator,modified,createdDate,organization,curationEnabled,recentRecordedAccess,sessionDefinition,curatedComponents,externalData,containerNames"
        if parentDataGroupId:
            params["parentDataGroupId"] = parentDataGroupId
        if externalIds:
            params["externalIds"] = externalIds
        if externalParentIds:
            params["externalParentIds"] = externalParentIds
        res = self.connector.getData(
            self.endpoint + path, params=params, verbose=verbose
        )
        data = res["content"]
        last = res.get("last", True)
        while last != True:
            params["page"] += 1
            res = self.connector.getData(
                self.endpoint + path, params=params, verbose=verbose
            )
            data += res["content"]
            last = res.get("last", True)
        if output == "df":
            df = pd.DataFrame(data)
            return df
        return data

    def getDataView(
        self, dataViewId: str = None, full: bool = True, save: bool = False
    ) -> dict:
        """
        Returns a specific Data View configuration from Configuration ID.
        Arguments:
            dataViewId : REQUIRED : The data view ID to retrieve.
            full : OPTIONAL : getting extra information on the data view
            save : OPTIONAL : save the response in JSON format
        """
        if dataViewId is None:
            raise ValueError("dataViewId is required")
        if self.loggingEnabled:
            self.logger.debug(f"getDataView start")
        path = f"/datagroups/dataviews/{dataViewId}"
        params = {}
        if full:
            params[
                "expansion"
            ] = "name,description,owner,isDeleted,parentDataGroupId,segmentList,currentTimezoneOffset,timezoneDesignator,modified,createdDate,organization,curationEnabled,recentRecordedAccess,sessionDefinition,curatedComponents,externalData,containerNames"
        res = self.connector.getData(self.endpoint + path, params=params)
        if save:
            with open(f"{dataViewId}_{int(time.time())}.json", "w") as f:
                f.write(json.dumps(res, indent=4))
        return res

    def validateDataView(self, data: Union[dict, IO]) -> dict:
        """
        Validate the dictionary for the creation of a data view.
        Argument:
            data : REQUIRED : The dictionary or json file that holds the definition for the dataview to be created.
        """
        if data is None:
            raise ValueError("Require information to be passed for data view creation")
        if self.loggingEnabled:
            self.logger.debug(f"validateDataView start")
        path = "/datagroups/dataviews/validate"
        if ".json" in data:
            with open(data, "r") as f:
                data = json.load(f)
        res = self.connector.postData(self.endpoint + path, data=data)
        return res

    def createDataView(self, data: Union[dict, IO] = None, **kwargs) -> dict:
        """
        Create and stores the given Data View in the db.
        Arguments:
            data : REQUIRED : The dictionary or json file that holds the definition for the dataview to be created.
        """
        path = "/datagroups/dataviews/"
        if data is None:
            raise ValueError("Require information to be passed for data view creation")
        if ".json" in data:
            with open(data, "r", encoding=kwargs.get("encoding", "utf-8")) as f:
                data = json.load(f)
        if self.loggingEnabled:
            self.logger.debug(f"createDataView start")
        res = self.connector.postData(self.endpoint + path, data=data)
        return res

    def deleteDataView(self, dataViewId: str = None) -> str:
        """
        Delete a data view by its ID.
        Argument:
            dataViewId : REQUIRED : the data view ID to be deleted
        """
        if dataViewId is None:
            raise ValueError("Require a data view ID")
        if self.loggingEnabled:
            self.logger.debug(f"deleteDataView start, id: {dataViewId}")
        path = f"/datagroups/dataviews/{dataViewId}"
        res = self.connector.deleteData(self.endpoint + path)
        return res

    def updateDataView(
        self, dataViewId: str = None, data: Union[dict, IO] = None, **kwargs
    ) -> dict:
        """
        Update the Data View definition (PUT method)
        Arguments:
            dataViewId : REQUIRED : the data view ID to be updated
            data : REQUIRED : The dictionary or JSON file that holds the definition for the dataview to be updated
        possible kwargs:
            encoding : if you pass a JSON file, you can change the encoding to read it.
        """
        if dataViewId is None:
            raise ValueError("Require a Data View ID")
        if data is None:
            raise ValueError("Require data to be passed for the update")
        if self.loggingEnabled:
            self.logger.debug(f"updateDataView start, id: {dataViewId}")
        path = f"/datagroups/dataviews/{dataViewId}"
        if ".json" in data:
            with open(data, "r", encoding=kwargs.get("encoding", "utf-8")) as f:
                data = json.load(f.read())
        res = self.connector.putData(self.endpoint + path, data=data)
        return res

    def copyDataView(self, dataViewId: str = None) -> dict:
        """
        Copy the setting of a specific data view.
        Arguments:
            dataViewId : REQUIRED : Data View ID to copy the setting on
        """
        if dataViewId is None:
            raise ValueError("Require a data view ID")
        if self.loggingEnabled:
            self.logger.debug(f"copyDataView start, id: {dataViewId}")
        path = f"/datagroups/dataviews/copy/{dataViewId}"
        res = self.connector.putData(self.endpoint + path)
        return res

    def getFilters(
        self,
        limit: int = 100,
        full: bool = False,
        output: str = "df",
        includeType: str = "all",
        name: str = None,
        dataIds: str = None,
        ownerId: str = None,
        filterByIds: str = None,
        cached: bool = True,
        verbose: bool = False,
    ) -> JsonListOrDataFrameType:
        """
        Returns a list of filters used in CJA.
        Arguments:
            limit : OPTIONAL : number of result per request (default 100)
            full : OPTIONAL : add additional information to the filters
            output : OPTIONAL : Type of output selected, either "df" (default) or "raw"
            includeType : OPTIONAL : Include additional segments not owned by user.(default all)
                possible values are "shared" "templates" "deleted" "internal"
            name : OPTIONAL : Filter list to only include filters that contains the Name
            dataIds : OPTIONAL : Filter list to only include filters tied to the specified data group ID list (comma-delimited)
            ownerId : OPTIONAL : Filter by a specific owner ID.
            filterByIds : OPTIONAL : Filters by filter ID (comma-separated list)
            cached : OPTIONAL : return cached results
            toBeUsedInRsid : OPTIONAL : The report suite where the filters is intended to be used. This report suite will be used to determine things like compatibility and permissions.
        """
        if self.loggingEnabled:
            self.logger.debug(f"getFilters start, output: {output}")
        path = "/filters"
        params = {
            "limit": limit,
            "cached": cached,
            "includeType": includeType,
            "page": 0,
        }
        if full:
            params[
                "expansion"
            ] = "compatibility,definition,internal,modified,isDeleted,definitionLastModified,createdDate,recentRecordedAccess,performanceScore,owner,dataId,ownerFullName,dataName,sharesFullName,approved,favorite,shares,tags,usageSummary,usageSummaryWithRelevancyScore"
        if name is not None:
            params["name"] = name
        if dataIds is not None:
            params["dataIds"] = dataIds
        if ownerId is not None:
            params["ownerId"] = ownerId
        if filterByIds is not None:
            params["filterByIds"] = filterByIds
        res = self.connector.getData(
            self.endpoint + path, params=params, verbose=verbose
        )
        lastPage = res.get("lastPage", True)
        data = res["content"]
        while lastPage == False:
            params["page"] += 1
            res = self.connector.getData(
                self.endpoint + path, params=params, verbose=verbose
            )
            data += res["content"]
            lastPage = res.get("lastPage", True)
        if output == "df":
            df = pd.DataFrame(data)
            return df
        return data

    def getFilter(
        self,
        filterId: str = None,
        full: bool = False,
    ) -> dict:
        """
        Returns a single filter definition by its ID.
        Arguments:
            filterId : REQUIRED : ID of the filter
            full : OPTIONAL : Boolean to define additional elements
        """
        if filterId is None:
            raise ValueError("Require a filter ID")
        if self.loggingEnabled:
            self.logger.debug(f"getFilter start, id: {filterId}")
        path = f"/filters/{filterId}"
        params = {}
        if full:
            params[
                "expansion"
            ] = "compatibility,definition,internal,modified,isDeleted,definitionLastModified,createdDate,recentRecordedAccess,performanceScore,owner,dataId,ownerFullName,dataName,sharesFullName,approved,favorite,shares,tags,usageSummary,usageSummaryWithRelevancyScore"
        res = self.connector.getData(self.endpoint + path, params=params)
        return res

    def deleteFilter(self, filterId: str = None) -> str:
        """
        Delete a filter based on its ID.
        Arguments:
            filterId : REQUIRED : Filter ID to be deleted
        """
        if filterId is None:
            raise ValueError("Require a filter ID")
        if self.loggingEnabled:
            self.logger.debug(f"deleteFilter start, id: {filterId}")
        path = f"/filters/{filterId}"
        res = self.connector.deleteData(self.endpoint + path)
        return res

    def validateFilter(self, data: Union[dict, IO] = None, **kwargs) -> dict:
        """
        Validate the syntax for filter creation.
        Arguments:
            data : REQUIRED : Dictionary or JSON file to create a filter
        possible kwargs:
            encoding : if you pass a JSON file, you can change the encoding to read it.
        """
        if data is None:
            raise ValueError("Require some data to validate")
        if self.loggingEnabled:
            self.logger.debug(f"validateFilter start")
        path = "/filters/validate"
        if ".json" in data:
            with open(data, "r", encoding=kwargs.get("encoding", "utf-8")) as f:
                data = json.load(f.read())
        res = self.connector.postData(self.endpoint + path, data=data)
        return res

    def createFilter(self, data: Union[dict, IO] = None, **kwargs) -> dict:
        """
        Create a filter.
        Arguments:
            data : REQUIRED : Dictionary or JSON file to create a filter
        possible kwargs:
            encoding : if you pass a JSON file, you can change the encoding to read it.
        """
        if data is None:
            raise ValueError("Require some data to validate")
        if self.loggingEnabled:
            self.logger.debug(f"createFilter start")
        path = "/filters"
        if ".json" in data:
            with open(data, "r", encoding=kwargs.get("encoding", "utf-8")) as f:
                data = json.load(f)
        res = self.connector.postData(self.endpoint + path, data=data)
        return res

    def updateFilter(
        self, filterId: str = None, data: Union[dict, IO] = None, **kwargs
    ) -> dict:
        """
        Update a filter based on the filter ID.
        Arguments:
            filterId : REQUIRED : Filter ID to be updated
            data : REQUIRED : Dictionary or JSON file to update the filter
        possible kwargs:
            encoding : if you pass a JSON file, you can change the encoding to read it.
        """
        if filterId is None:
            raise ValueError("Require a filter ID")
        if data is None:
            raise ValueError("Require some data to validate")
        if self.loggingEnabled:
            self.logger.debug(f"updateFilter start, id: {filterId}")
        path = f"/filters/{filterId}"
        if ".json" in data:
            with open(data, "r", encoding=kwargs.get("encoding", "utf-8")) as f:
                data = json.load(f.read())
        res = self.connector.putData(self.endpoint + path, data=data)
        return res

    def getAuditLogs(
        self,
        startDate: str = None,
        endDate: str = None,
        action: str = None,
        component: str = None,
        componentId: str = None,
        userType: str = None,
        userId: str = None,
        userEmail: str = None,
        description: str = None,
        pageSize: int = 100,
        n_results: Union[str, int] = "inf",
        output: str = "df",
        save: bool = False,
    ) -> JsonListOrDataFrameType:
        """
        Get Audit Log when few filters are applied.
        All filters are applied with an AND condition.
        Arguments:
            startDate : OPTIONAL : begin range date, format: YYYY-01-01T00:00:00-07 (required if endDate is used)
            endDate : OPTIONAL : begin range date, format: YYYY-01-01T00:00:00-07 (required if startDate is used)
            action : OPTIONAL : The type of action a user or system can make.
                Possible values : CREATE, EDIT, DELETE, LOGIN_FAILED, LOGIN_SUCCESSFUL, API_REQUEST
            component : OPTIONAL :The type of component.
                Possible values : CALCULATED_METRIC, CONNECTION, DATA_GROUP, DATA_VIEW, DATE_RANGE, FILTER, MOBILE, PROJECT, REPORT, SCHEDULED_PROJECT
            componentId : OPTIONAL : The id of the component.
            userType : OPTIONAL : The type of user.
            userId : OPTIONAL : The ID of the user.
            userEmail : OPTIONAL : The email address of the user.
            description : OPTIONAL : The description of the audit log.
            pageSize : OPTIONAL : Number of results per page. If left null, the default size is 100.
            n_results : OPTIONAL : Total number of results you want for that search. Default "inf" will return everything
            output : OPTIONAL : DataFrame by default, can be "raw"
        """
        if self.loggingEnabled:
            self.logger.debug(f"getAuditLogs start")
        params = {"pageNumber": 0, "pageSize": pageSize}
        path = "/auditlogs/api/v1/auditlogs"
        if startDate is not None and endDate is not None:
            params["startDate"] = startDate
            params["endDate"] = endDate
        if action is not None:
            params["action"] = action
        if component is not None:
            params["component"] = component
        if componentId is not None:
            params["componentId"] = componentId
        if userType is not None:
            params["userType"]
        if userId is not None:
            params["userId"] = userId
        if userEmail is not None:
            params["userEmail"] = userEmail
        if description is not None:
            params["description"] = description
        lastPage = False
        data = []
        while lastPage != True:
            res = self.connector.getData(self.endpoint + path, params=params)
            print(res)
            data += res.get("content", [])
            lastPage = res.get("last", True)
            if len(data) > float(n_results):
                lastPage = True
            params["pageNumber"] += 1
        if output == "raw":
            if save:
                with open(f"audit_logs_{int(time.time())}.json", "w") as f:
                    f.write(json.dumps(data))
        df = pd.DataFrame(data)
        try:
            df["userId"] = df["user"].apply(lambda x: x.get("id", ""))
            df["componentId"] = df["component"].apply(lambda x: x.get("id", ""))
            df["componentType"] = df["component"].apply(lambda x: x.get("idType", ""))
            df["componentName"] = df["component"].apply(lambda x: x.get("name", ""))
        except:
            if self.loggingEnabled:
                self.logger.debug(f"issue returning results")
        if save:
            df.to_csv(f"audit_logs.{int(time.time())}.csv", index=False)
        return df

    SAMPLE_FILTERMESSAGE_LOGS = {
        "criteria": {
            "fieldOperator": "AND",
            "fields": [
                {
                    "fieldType": "COMPONENT",
                    "value": ["FILTER", "CALCULATED_METRIC"],
                    "operator": "IN",
                },
                {
                    "fieldType": "DESCRIPTION",
                    "value": ["created"],
                    "operator": "CONTAINS",
                },
            ],
            "subCriteriaOperator": "AND",
            "subCriteria": {
                "fieldOperator": "OR",
                "fields": [
                    {
                        "fieldType": "USER_EMAIL",
                        "value": ["jane"],
                        "operator": "NOT_EQUALS",
                    },
                    {
                        "fieldType": "USER_EMAIL",
                        "value": ["john"],
                        "operator": "EQUALS",
                    },
                ],
                "subCriteriaOperator": None,
                "subCriteria": None,
            },
        },
        "pageSize": 100,
        "pageNumber": 0,
    }

    def searchAuditLogs(self, filterMessage: dict = None) -> JsonListOrDataFrameType:
        """
        Get Audit Log when several filters are applied. You can define the different type of operator and connector to use.
        Operators: EQUALS, CONTAINS, NOT_EQUALS, IN
        Connectors: AND, OR
        Arguments:
            filterMessage : REQUIRED : A dictionary of the search to the Audit Log.
        """
        path = "/auditlogs/api/v1/auditlogs/search"
        if filterMessage is None:
            raise ValueError("Require a filterMessage")
        res = self.connector.postData(self.endpoint + path, data=filterMessage)
        return res

    def _prepareData(
        self,
        dataRows: list = None,
        reportType: str = "normal",
    ) -> dict:
        """
        Read the data returned by the getReport and returns a dictionary used by the Workspace class.
        Arguments:
            dataRows : REQUIRED : data rows data from CJA API getReport
            reportType : REQUIRED : "normal" or "static"
        """
        if dataRows is None:
            raise ValueError("Require dataRows")
        data_rows = deepcopy(dataRows)
        expanded_rows = {}
        if reportType == "normal":
            for row in data_rows:
                expanded_rows[row["itemId"]] = [row["value"]]
                expanded_rows[row["itemId"]] += row["data"]
        elif reportType == "static":
            expanded_rows = data_rows
        return expanded_rows

    def _decrypteStaticData(
        self, dataRequest: dict = None, response: dict = None
    ) -> dict:
        """
        From the request dictionary and the response, decrypte the data to standardise the reading.
        """
        dataRows = []
        ## retrieve StaticRow ID and segmentID
        tableSegmentsRows = {
            obj["id"]: obj["segmentId"]
            for obj in dataRequest["metricContainer"]["metricFilters"]
            if obj["id"].startswith("STATIC_ROW")
        }
        ## retrieve place and segmentID
        segmentApplied = {}
        for obj in dataRequest["metricContainer"]["metricFilters"]:
            if obj["id"].startswith("STATIC_ROW") == False:
                if obj["type"] == "breakdown":
                    segmentApplied[obj["id"]] = f"{obj['dimension']}:::{obj['itemId']}"
                elif obj["type"] == "segment":
                    segmentApplied[obj["id"]] = obj["segmentId"]
                elif obj["type"] == "dateRange":
                    segmentApplied[obj["id"]] = obj["dateRange"]
        ### table columnIds and StaticRow IDs
        tableColumnIds = {
            obj["columnId"]: obj["filters"][0]
            for obj in dataRequest["metricContainer"]["metrics"]
        }
        ### create relations for metrics with Filter on top
        filterRelations = {
            obj["filters"][0]: obj["filters"][1:]
            for obj in dataRequest["metricContainer"]["metrics"]
            if len(obj["filters"]) > 1
        }
        staticRows = set(val for val in tableSegmentsRows.values())
        nb_rows = len(staticRows)  ## define  how many segment used as rows
        nb_columns = int(
            len(dataRequest["metricContainer"]["metrics"]) / nb_rows
        )  ## use to detect rows
        staticRows = set(val for val in tableSegmentsRows.values())
        staticRowsNames = []
        for row in staticRows:
            if row.startswith("s") and "@AdobeOrg" in row:
                filter = self.getFilter(row)
                staticRowsNames.append(filter["name"])
            else:
                staticRowsNames.append(row)
        staticRowDict = {
            row: rowName for row, rowName in zip(staticRows, staticRowsNames)
        }
        ### metrics
        dataRows = defaultdict(list)
        for row in staticRowDict:  ## iter on the different static rows
            for column, data in zip(
                response["columns"]["columnIds"], response["summaryData"]["totals"]
            ):
                if tableSegmentsRows[tableColumnIds[column]] == row:
                    ## check translation of metricId with Static Row ID
                    if row not in dataRows[staticRowDict[row]]:
                        dataRows[staticRowDict[row]].append(row)
                    dataRows[staticRowDict[row]].append(data)
                ## should ends like : {'segmentName' : ['STATIC',123,456]}
        return nb_columns, tableColumnIds, segmentApplied, filterRelations, dataRows

    def getReport(
        self,
        request: Union[dict, IO] = None,
        limit: int = 20000,
        n_results: Union[int, str] = "inf",
        allowRemoteLoad: str = "default",
        useCache: bool = True,
        useResultsCache: bool = False,
        includeOberonXml: bool = False,
        includePredictiveObjects: bool = False,
        returnsNone: bool = None,
        countRepeatInstances: bool = None,
        ignoreZeroes: bool = None,
        dataViewId: str = None,
        resolveColumns: bool = True,
        save: bool = False,
        returnClass: bool = True,
    ) -> Union[Workspace, dict]:
        """
        Return an instance of Workspace that contains the data requested.
        Argumnents:
            request : REQUIRED : either a dictionary of a JSON file that contains the request information.
            limit : OPTIONAL : number of results per request (default 1000)
            n_results : OPTIONAL : total number of results returns. Use "inf" to return everything (default "inf")
            allowRemoteLoad : OPTIONAL : Controls if Oberon should remote load data. Default behavior is true with fallback to false if remote data does not exist
            useCache : OPTIONAL : Use caching for faster requests (Do not do any report caching)
            useResultsCache : OPTIONAL : Use results caching for faster reporting times (This is a pass through to Oberon which manages the Cache)
            includeOberonXml : OPTIONAL : Controls if Oberon XML should be returned in the response - DEBUG ONLY
            includePredictiveObjects : OPTIONAL : Controls if platform Predictive Objects should be returned in the response. Only available when using Anomaly Detection or Forecasting- DEBUG ONLY
            returnsNone : OPTIONAL: Overwritte the request setting to return None values.
            countRepeatInstances : OPTIONAL: Overwritte the request setting to count repeatInstances values.
            ignoreZeroes : OPTIONAL : Ignore zeros in the results
            dataViewId : OPTIONAL : Overwrite the data View ID used for report. Only works if the same components are presents.
            resolveColumns: OPTIONAL : automatically resolve columns from ID to name for calculated metrics & segments. Default True. (works on returnClass only)
            save : OPTIONAL : If you want to save the data (in JSON or CSV, depending the class is used or not)
            returnClass : OPTIONAL : return the class building dataframe and better comprehension of data. (default yes)
        """
        if self.loggingEnabled:
            self.logger.debug(f"Start getReport")
        path = "/reports"
        params = {
            "allowRemoteLoad": allowRemoteLoad,
            "useCache": useCache,
            "useResultsCache": useResultsCache,
            "includeOberonXml": includeOberonXml,
            "includePlatformPredictiveObjects": includePredictiveObjects,
        }
        if ".json" in request:
            with open(request, "r") as f:
                dataRequest = json.load(f)
        elif type(request) == dict:
            dataRequest = request
        else:
            raise ValueError("Require a JSON or Dictionary to request data")
        ### Settings
        dataRequest["settings"]["page"] = 0
        dataRequest["settings"]["limit"] = limit
        if returnsNone:
            dataRequest["settings"]["nonesBehavior"] = "return-nones"
        else:
            dataRequest["settings"]["nonesBehavior"] = "exclude-nones"
        if countRepeatInstances:
            dataRequest["settings"]["countRepeatInstances"] = True
        else:
            dataRequest["settings"]["countRepeatInstances"] = False
        if dataViewId is not None:
            dataRequest["dataId"] = dataViewId
        if ignoreZeroes:
            dataRequest["statistics"]["ignoreZeroes"] = True
        else:
            dataRequest["statistics"]["ignoreZeroes"] = False
        ### Request data
        if self.loggingEnabled:
            self.logger.debug(f"getReport request: {json.dumps(dataRequest,indent=4)}")
        res = self.connector.postData(
            self.endpoint + path, data=dataRequest, params=params
        )
        if "rows" in res.keys():
            reportType = "normal"
            if self.loggingEnabled:
                self.logger.debug(f"reportType: {reportType}")
            dataRows = res.get("rows")
            columns = res.get("columns")
            summaryData = res.get("summaryData")
            totalElements = res.get("numberOfElements")
            lastPage = res.get("lastPage", True)
            if float(len(dataRows)) >= float(n_results):
                ## force end of loop when a limit is set on n_results
                lastPage = True
            while lastPage != True:
                dataRequest["settings"]["page"] += 1
                res = self.connector.postData(
                    self.endpoint + path, data=dataRequest, params=params
                )
                dataRows += res.get("rows")
                lastPage = res.get("lastPage", True)
                totalElements += res.get("numberOfElements")
                if float(len(dataRows)) >= float(n_results):
                    ## force end of loop when a limit is set on n_results
                    lastPage = True
            if self.loggingEnabled:
                self.logger.debug(f"loop for report over: {len(dataRows)} results")
            if returnClass == False:
                return dataRows
            ### create relation between metrics and filters applied
            columnIdRelations = {
                obj["columnId"]: obj["id"]
                for obj in dataRequest["metricContainer"]["metrics"]
            }
            filterRelations = {
                obj["columnId"]: obj["filters"]
                for obj in dataRequest["metricContainer"]["metrics"]
                if len(obj.get("filters", [])) > 0
            }
            metricFilters = {}
            metricFilterTranslation = {}
            for filter in dataRequest["metricContainer"].get("metricFilters", []):
                filterId = filter["id"]
                if filter["type"] == "breakdown":
                    filterValue = f"{filter['dimension']}:{filter['itemId']}"
                    metricFilters[filter["dimension"]] = filter["itemId"]
                if filter["type"] == "dateRange":
                    filterValue = f"{filter['dateRange']}"
                    metricFilters[filterValue] = filterValue
                if filter["type"] == "segment":
                    filterValue = f"{filter['segmentId']}"
                    if filterValue.startswith("s") and "@AdobeOrg" in filterValue:
                        seg = self.getFilter(filterValue)
                        metricFilters[filterValue] = seg["name"]
                metricFilterTranslation[filterId] = filterValue
            metricColumns = {}
            for colId in columnIdRelations.keys():
                metricColumns[colId] = columnIdRelations[colId]
                for element in filterRelations.get(colId, []):
                    metricColumns[colId] += f":::{metricFilterTranslation[element]}"
        else:
            if returnClass == False:
                return res
            reportType = "static"
            if self.loggingEnabled:
                self.logger.debug(f"reportType: {reportType}")
            columns = None  ## no "columns" key in response
            summaryData = res.get("summaryData")
            (
                nb_columns,
                tableColumnIds,
                segmentApplied,
                filterRelations,
                dataRows,
            ) = self._decrypteStaticData(dataRequest=dataRequest, response=res)
            ### Findings metrics
            metricFilters = {}
            metricColumns = []
            for i in range(nb_columns):
                metric: str = res["columns"]["columnIds"][i]
                metricName = metric.split(":::")[0]
                if metricName.startswith("cm"):
                    calcMetric = self.getCalculatedMetric(metricName)
                    metricName = calcMetric["name"]
                correspondingStatic = tableColumnIds[metric]
                ## if the static row has a filter
                if correspondingStatic in list(filterRelations.keys()):
                    ## finding segment applied to metrics
                    for element in filterRelations[correspondingStatic]:
                        segId = segmentApplied[element]
                        metricName += f":::{segId}"
                        metricFilters[segId] = segId
                        if segId.startswith("s") and "@AdobeOrg" in segId:
                            seg = self.getFilter(segId)
                            metricFilters[segId] = seg["name"]
                metricColumns.append(metricName)
                ### ending with ['metric1','metric2 + segId',...]
        ### preparing data points
        if self.loggingEnabled:
            self.logger.debug(f"preparing data")
        preparedData = self._prepareData(dataRows, reportType=reportType)
        if returnClass:
            if self.loggingEnabled:
                self.logger.debug(f"returning Workspace class")
            ## Using the class
            data = Workspace(
                responseData=preparedData,
                dataRequest=dataRequest,
                columns=columns,
                summaryData=summaryData,
                cjaConnector=self,
                reportType=reportType,
                metrics=metricColumns,  ## for normal type   ## for staticReport
                metricFilters=metricFilters,
                resolveColumns=resolveColumns,
            )
            if save:
                data.to_csv()
            return data

    def getMultidimensionalReport(
        self,
        dimensions: list = None,
        dimensionLimit: dict = None,
        metrics: list = None,
        dataViewId: str = None,
        globalFilters: list = None,
        metricFilters: dict = None,
        countRepeatInstances: bool = True,
        returnNones: bool = True,
    ) -> pd.DataFrame:
        """
        Realize a multi-level breakdown report from the elements provided.
        Returns either
        Arguments:
            dimensions : REQUIRED : list of the dimension to breakdown. In the order of the breakdown.
            dimensionLimit : REQUIRED : the number of results to return for each breakdown.
                dictionnary like this: {'dimension1':5,'dimension2':10}
                You can ask to return everything from a dimension by using the 'inf' method
            metrics : REQUIRED : list of metrics to return
            dataViewId : REQUIRED : The dataView Id to use for your report.
            globalFilters : REQUIRED : list of filtersID to be used.
                example : ["filterId1","2020-01-01T00:00:00.000/2020-02-01T00:00:00.000"]
            metricFilters : OPTIONAL : dictionary of the filter you want to apply to the metrics.
                dictionnary like this : {"metric1":"segId1","metric":"segId2"}
            countRepeatInstances : OPTIONAL : set to count repeatInstances values (or not). True by default.
            returnNones : OPTIONAL : Set the behavior of the None values in that request. (True by default)
        """
        if dimensions is None:
            raise ValueError("Require a list of dimensions")
        if dimensionLimit is None:
            raise ValueError(
                "Require a dictionary of dimensions with their number of results"
            )
        if metrics is None:
            raise ValueError("Require a list of metrics")
        if dataViewId is None:
            raise ValueError("Require a Data View ID")
        if self.loggingEnabled:
            self.logger.debug(f"Starting getMultidimensionalReport")
        template = RequestCreator()
        template.setDataViewId(dataViewId)
        template.setRepeatInstance(countRepeatInstances)
        template.setNoneBehavior(returnNones)
        for filter in globalFilters:
            template.addGlobalFilter(filter)
        for metric in metrics:
            template.addMetric(metric)
        if metricFilters is not None:
            for filterKey in metricFilters:
                template.addMetricFilter(
                    metricId=filterKey, filterId=metricFilters[filterKey]
                )
        if self.loggingEnabled:
            self.logger.debug(
                f"first request: {json.dumps(template.to_dict(),indent=2)}"
            )
        level = 0
        list_breakdown = deepcopy(
            dimensions[1:]
        )  ## use to assign the correct variable to the itemsId retrieved
        dict_breakdown_itemId = defaultdict(list)  ## for dimension - itemId
        dict_breakdown_relation = defaultdict(list)  ## for itemId - Sub itemId
        translate_itemId_value = {}  ## for translation between itemId and Value
        for dimension in dimensions:
            df_final = pd.DataFrame()
            template.setDimension(dimension)
            if float(dimensionLimit[dimension]) > 20000:
                template.setLimit("20000")
                limit = "20000"
            else:
                template.setLimit(dimensionLimit[dimension])
                limit = dimensionLimit[dimension]
            ### if we need to add filters
            if dimension == dimensions[0]:
                if self.loggingEnabled:
                    self.logger.debug(f"Starting first iteration: {dimension}")
                request = template.to_dict()
                res = self.getReport(
                    request=request,
                    n_results=dimensionLimit[dimension],
                    limit=limit,
                )
                dataframe = res.dataframe
                dict_breakdown_itemId[list_breakdown[level]] = list(dataframe["itemId"])
                ### ex : {'dimension1' : [itemID1,itemID2,...]}
                translate_itemId_value[dimension] = {
                    itemId: value
                    for itemId, value in zip(
                        list(dataframe["itemId"]), list(dataframe.iloc[:, 1])
                    )
                }  ### {"dimension1":{'itemIdValue':'realValue'}}
            else:  ### starting breakdowns
                if self.loggingEnabled:
                    self.logger.debug(f"Starting breakdowns")
                for itemId in dict_breakdown_itemId[dimension]:
                    ### for each item in the previous element
                    if level > 1:
                        ## adding previous breakdown value to the metric filter
                        original_filterId = dict_breakdown_relation[itemId]
                        for metric in metrics:
                            template.addMetricFilter(
                                metricId=metric, filterId=original_filterId
                            )
                    filterId = f"{dimensions[level - 1]}:::{itemId}"
                    for metric in metrics:
                        template.addMetricFilter(metricId=metric, filterId=filterId)
                    request = template.to_dict()
                    if self.loggingEnabled:
                        self.logger.info(json.dumps(request, indent=4))
                    res = self.getReport(
                        request=request,
                        n_results=dimensionLimit[dimension],
                        limit=limit,
                    )
                    ## cleaning breakdown filters
                    template.removeMetricFilter(filterId=filterId)
                    if level > 1:
                        original_filterId = dict_breakdown_relation[itemId]
                        template.removeMetricFilter(filterId=original_filterId)
                    if self.loggingEnabled:
                        self.logger.debug(json.dumps(template.to_dict(), indent=4))
                    dataframe = res.dataframe
                    list_itemIds = list(dataframe["itemId"])
                    dict_breakdown_itemId[dimension] = list_itemIds
                    ### ex : {'dimension2' : [itemID1,itemID2,...]}
                    dict_breakdown_relation = {
                        itemId: filterId for itemId in list_itemIds
                    }
                    ## translating itemId to value
                    ## {'dimension1':{'itemId':'value'}}
                    translate_itemId_value[dimension] = {
                        itemId: value
                        for itemId, value in zip(
                            list(dataframe["itemId"]), list(dataframe.iloc[:, 1])
                        )
                    }
                    ## in case breakdown doesn't have values.
                    if dataframe.empty == False:
                        nb_metrics = len(metrics)
                        metricsCols = list(dataframe.columns[-nb_metrics:])
                        dictReplace = {
                            oldColName: newColName
                            for oldColName, newColName in zip(metricsCols, metrics)
                        }
                        dataframe.rename(columns=dictReplace, inplace=True)
                        columns_order = deque(dataframe.columns)
                        for lvl in range(level):
                            dataframe[dimensions[lvl]] = translate_itemId_value[
                                dimensions[lvl]
                            ].get(itemId, itemId)
                            columns_order.appendleft(dimensions[lvl])
                        if df_final.empty:
                            df_final = dataframe
                        else:
                            df_final = df_final.append(dataframe, ignore_index=True)
                    df_final = df_final[columns_order]
            level += 1
        workspace = Workspace(
            df_final,
            dataRequest=template.to_dict(),
            summaryData="notApplicable",
            cjaConnector=self,
            reportType="multi",
            metricFilters="notApplicable",
        )
        return workspace
