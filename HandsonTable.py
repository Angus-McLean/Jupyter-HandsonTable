import json
from IPython.core.display import display, HTML, Javascript
import pandas as pd
import numpy as np


class HandsonTable():
    ALL_TABLES = {}
    
    DEFAULT_CONFIG = {
        'filters': True,
        'dropdownMenu': True,
        'contextMenu': True,
        'columnSorting': {
            'indicator': True
        },
        'autoWrapRow': True,
        'maxColWidth': 200,
        'pageSize' : 14
    }
    
    @staticmethod
    def init_notebook():
        display(Javascript(filename="node_modules/handsontable/dist/handsontable.full.min.js"))
        display(Javascript(filename="jupyter-handsontable.js"))
        display(HTML("""<link href="node_modules/handsontable/dist/handsontable.full.min.css" rel="stylesheet" type="text/css">"""))
    
    @staticmethod
    def update_table(name, json_df):
        df_update = pd.read_json(json_df, orient="split")
        HandsonTable.ALL_TABLES['_'] = df_update
        HandsonTable.ALL_TABLES[name].df.update(df_update)
        print('update_table called!', name, df_update)
       
    @staticmethod
    def query_table(name, json_query):
        query = json.loads(json_query)
        tableObj = HandsonTable.ALL_TABLES[name]
        
        # Filtering
        if 'filters' in query and len(query['filters']):
            df_subset = tableObj.queryDf(query['filters'])
        else :
            df_subset = tableObj.df

        # Sorting
        if 'sorts' in query and len(query['sorts']):
            col = df_subset.columns[query['sorts'][0]['column']]
            asc = query['sorts'][0]['sortOrder'] == 'asc'
            df_subset = df_subset.sort_values(col, ascending=asc)
            
        # Pagination
        pageNum = query['pageNum'] if 'pageNum' in query else 0
        df_subset = tableObj.getPage(df_subset, pageNum)

        return json.dumps(df_subset.to_json(orient='split', date_format='iso'))
    
    def __init__(self, name, df, config):
        self.name = name
        self.df = df
        self.raw_config = config
        all_config = self.buildConfigs(config)
        self.config = all_config

        HandsonTable.ALL_TABLES[name] = self
        df_page = self.getPage(df)
        self.display_table(df_page, all_config)
        
    def queryDf(self, query):
        if len(query)==0: return self.df
        masks = []
        for q in query:
            col = self.df.columns[q['column']]
            masks.append(applyColFilter(self.df[col], q))
        mask = np.all(masks, axis=0)        
        return self.df[mask]
    
    def getPage(self, df, pageNum=0):
        start = pageNum*self.config['pageSize']
        return df[start:start+self.config['pageSize']]
    
    def buildConfigs(self, config):
        z = HandsonTable.DEFAULT_CONFIG.copy()
        z.update(config)
        z['columns'] = self.getColDataTypes()
        return z
        
    def getColDataTypes(self) :
        colTypesDict = {}
        typesConv = {
            'numeric' : np.number,
            'date' : np.datetime64,
            'text' : object
        }
        for (txtType, dtype) in typesConv.items():
            colTypesDict.update({col : txtType for col in self.df.select_dtypes(include=[dtype]).columns})
        colTypes = list(map(lambda a : {'type':colTypesDict[a]}, self.df.columns))
        return colTypes

    def display_table(self, df, config):
        display(Javascript("""
            (function(element){
                require(['jupyter-handsontable'], function(JupyterHandsontable) {
                    var name = '%s'; var data = JSON.parse(%s); var config = %s;
                    var hot = new JupyterHandsontable(name, element.get(0), data, config);
                });
            })(element);
        """ % (self.name, json.dumps(df.to_json(orient='split', date_format='iso')), json.dumps(config))))

        
#### Helper Methods
def applyColFilter(series, colFilter):
    masks = list(map(lambda cond : applyCondition(series, cond), colFilter['conditions']))
    if colFilter['operation'] == "disjunction":
        return np.any(np.array(masks), axis=0)
    if colFilter['operation'] == "conjunction":
        return np.all(np.array(masks), axis=0)

def applyCondition(series, cond) :
    if cond['name'] in ['gt', 'eq', 'lt']:
        return getattr(series, cond['name'])(float(cond['args'][0]))

    if cond['name']=='gte': return series >= float(cond['args'][0])
    if cond['name']=='lte': return series <= float(cond['args'][0])
    if cond['name']=='neq': return series != float(cond['args'][0])
    
    if cond['name']=='empty': return series.isna()
    if cond['name']=='not_empty': return ~(series.isna())
    
    if cond['name']=='by_value': return series.isin(cond['args'][0])
    if cond['name']=='between':
        return np.all([series>float(cond['args'][0]), series<float(cond['args'][1])], axis=0)

    if cond['name']=='not_between':
        return np.all([series<float(cond['args'][0]), series>float(cond['args'][1])], axis=0)
        
        