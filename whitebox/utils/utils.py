#!/usr/bin/env python
# -*- coding: utf-8 -*-

import warnings
import logging
import requests
import pandas as pd
import numpy as np
import pkg_resources
import io
from sklearn.datasets import make_blobs, make_regression
import random


class Settings(object):
    # currently supported aggregate metrics
    supported_agg_errors = ['MSE', 'MAE', 'RMSE', 'RAW']
    # placeholder class swithc - if Sensitivity then pull in html_sensitivity code
    # if Error then pull in html_error code
    html_type = {'WhiteBoxSensitivity': 'html_sensitivity',
                 'WhiteBoxError': 'html_error'}

class ErrorWarningMsgs(object):
    # specify groupbyvars error
    groupbyvars_error = ValueError(
        """groupbyvars must be a list of grouping 
            variables and cannot be None""")

    # specify supported errosr message
    error_type_error = ValueError(
        """Supported values for error_type are [MSE, MAE, RMSE]"""
    )

    cat_df_shape_error = """cat_df and model_df must have same number of observations.
                            \ncat_df shape: {}
                            \nmodel_df shape: {}"""

    predict_model_obj_error = """modelObj does not have predict method. 
                                WhiteBoxError only works with model 
                                objects with predict method"""

    missing_featuredict_error = """featuredict keys missing from assigned cat_df
                                    \ncheck featuredict keys and reassign.
                                    \nMissing keys: {}"""

    run_wb_error = """Must run {}.run() before calling save method"""

    agg_func_error = """aggregate_func must work on 
                            arrays of data and yield scalar
                            \nError: {}"""

    # hold all error messages that are raised based on value or type errors
    error_msgs = {'groupbyvars': groupbyvars_error,
                  'error_type': error_type_error,
                  'cat_df': cat_df_shape_error,
                  'modelobj': predict_model_obj_error,
                  'wb_run_error': run_wb_error,
                  'agg_func': agg_func_error,
                  'featuredict': missing_featuredict_error}

    cat_df_warning = """model_df being used for processing. Given that most 
                        sklearn models cannot directly handle 
                        string objects and they need to be converted to numbers, 
                        the use of model_df for processing may not behave as expected. 
                        For best results, use cat_df with string columns directly"""

    auto_format = """Please note autoformat is currently experimental and may have unintended consequences."""

    warning_msgs = {'cat_df': cat_df_warning,
                    'auto_format': auto_format}


def convert_categorical_independent(dataframe):
    """
    convert pandas dtypes 'categorical' into numerical columns
    :param dataframe: dataframe to perform adjustment on
    :return: dataframe that has converted strings to numbers
    """
    # we want to change the data, not copy and change
    dataframe = dataframe.copy(deep=True)
    # convert all strings to categories and format codes
    for str_col in dataframe.select_dtypes(include=['O', 'category']):
        dataframe.loc[:, str_col] =pd.Categorical(dataframe.loc[:, str_col])
    # convert all category datatypes into numeric
    cats = dataframe.select_dtypes(include=['category'])
    # warn user if no categorical variables detected
    if cats.shape[1] == 0:
        logging.warn("""Pandas categorical variable types not detected""")
        warnings.warn('Pandas categorical variable types not detected', UserWarning)
    # iterate over these columns
    for category in cats.columns:
        dataframe.loc[:, category] = dataframe.loc[:, category].cat.codes

    return dataframe


def create_insights(
                    group,
                    group_var=None,
                    error_type='MSE'):
    """
    create_insights develops various error metrics such as MSE, RMSE, MAE, etc.
    :param group: the grouping object from the pandas groupby
    :param group_var: the column that is being grouped on
    :return: dataframe with error metrics
    """
    assert error_type in ['MSE', 'RMSE', 'MAE', 'RAW'], """Currently only supports
                                                 MAE, MSE, RMSE, RAW"""
    errors = group['errors']
    error_dict = {'MSE': np.mean(errors ** 2),
                  'RMSE': (np.mean(errors ** 2)) ** (1 / 2),
                  'MAE': np.sum(np.absolute(errors))/group.shape[0],
                  'RAW': np.mean(errors)}

    msedf = pd.DataFrame({'groupByValue': group.name,
                          'groupByVarName': group_var,
                          error_type: error_dict[error_type],
                          'Total': float(group.shape[0])}, index=[0])
    return msedf

def to_json(
                dataframe,
                vartype='Continuous',
                html_type='error',
                incremental_val=None):
    # convert dataframe values into a json like object for D3 consumption
    assert vartype in ['Continuous', 'Categorical', 'Accuracy','Percentile'], """Vartypes should only be continuous, 
                                                                                categorical,
                                                                                Percentile or accuracy"""
    assert html_type in ['error', 'sensitivity',
                         'percentile'], 'html_type must be error or sensitivity'
    # prepare for error
    if html_type in ['error', 'percentile']:
        # specify data type
        json_out = {'Type': vartype}
    # prepare for sensitivity
    if html_type == 'sensitivity':
        # convert incremental_val
        if isinstance(incremental_val, float):
            incremental_val = round(incremental_val, 2)
        json_out = {'Type': vartype,
                    'Change': str(incremental_val)}
    # create data records from values in df
    json_out['Data'] = dataframe.to_dict(orient='records')

    return json_out

def flatten_json(dictlist):
    """
    flatten lists of dictionaries of the same variable into one dict
    structure. Inputs: [{'Type': 'Continuous', 'Data': [fixed.acid: 1, ...]},
    {'Type': 'Continuous', 'Data': [fixed.acid : 2, ...]}]
    outputs: {'Type' : 'Continuous', 'Data' : [fixed.acid: 1, fixed.acid: 2]}}
    :param dictlist: current list of dictionaries containing certain column elements
    :return: flattened structure with column variable as key
    """
    # make copy of dictlist
    copydict = dictlist[:]
    if len(copydict) > 1:
        for val in copydict[1:]:
            copydict[0]['Data'].extend(val['Data'])
        # take the revised first element of the list
        toreturn = copydict[0]
    else:
        if isinstance(copydict, list):
            # return the dictionary object if list type
            toreturn = copydict[0]
        else:
            # else return the dictionary itself
            toreturn = copydict
    assert isinstance(toreturn, dict), """flatten_json output object not of class dict.
                                        \nOutput class type: {}""".format(type(toreturn))
    return toreturn

def prob_acc(true_class=0, pred_prob=0.2):
    """
    return the prediction error
    :param true_class: true class label (0 or 1)
    :param pred_prob: predicted probability
    :return: error
    """
    return (true_class * (1-pred_prob)) + ((1-true_class)*pred_prob)


class HTML(object):
    @staticmethod
    def get_html(htmltype='html_error'):
        assert htmltype in ['html_error', 'html_sensitivity'], 'htmltype must be html_error or html_sensitivity'
        html_path = pkg_resources.resource_filename('whitebox', '{}.txt'.format(htmltype))
        # utility class to hold whitebox files
        try:
            wbox_html = open('{}.txt'.format(htmltype), 'r').read()
        except IOError:
            wbox_html = open(html_path, 'r').read()
        return wbox_html

def createmlerror_html(
                        datastring,
                        dependentvar,
                        htmltype='html_error'):
    """
    create WhiteBox error plot html code
    :param datastring: json like object containing data
    :param dependentvar: name of dependent variable
    :return: html string
    """
    assert htmltype in ['html_error', 'html_sensitivity'], """htmltype must be html_error 
                                                                or html_sensitivity"""
    output = HTML.get_html(htmltype=htmltype).replace('<***>',
                                                        datastring
                                                        ).replace('Quality', dependentvar)

    return output

def create_wine_data(cat_cols):
    """
    helper function to grab UCI machine learning wine dataset, convert to
    pandas dataframe, and return
    :return: pandas dataframe
    """

    if not cat_cols:
        cat_cols = ['alcohol', 'fixed acidity']

    red_raw = requests.get(
        'https://archive.ics.uci.edu/ml/machine-learning-databases/wine-quality/winequality-red.csv').content
    red = pd.read_csv(io.StringIO(red_raw.decode('utf-8-sig')),
                      sep=';')
    red['Type'] = 'Red'

    white_raw = requests.get(
        'https://archive.ics.uci.edu/ml/machine-learning-databases/wine-quality/winequality-white.csv').content
    white = pd.read_csv(io.StringIO(white_raw.decode('utf-8-sig')),
                        sep=';')
    white['Type'] = 'White'

    # read in wine quality dataset
    wine = pd.concat([white, red])

    # create category columns
    # create categories
    for cat in cat_cols:
        wine.loc[:, cat] = pd.cut(wine.loc[:, cat], bins=3, labels=['low', 'medium', 'high'])

    return wine


def create_synthetic(nrows=100,
                     ncols=10,
                     ncat=5,
                     num_groupby=3,
                     max_levels=10,
                     mod_type='regression'):
    """
    create synthetic datasets for both classification and regression problems
    :param nrows: num observations
    :param ncols: num features
    :param ncat: num categories
    :param num_groupby: number of groupby columns
    :param max_levels: max bin levels
    :param mod_type: model type --> classification or regression
    :return: synthetic dataset
    """

    if mod_type == 'classification':
        df = pd.DataFrame(make_blobs(n_samples=nrows,
                                     n_features=ncols,
                                     random_state=5)[0])
    else:
        df = pd.DataFrame(make_regression(n_samples=nrows,
                                     n_features=ncols,
                                          random_state=5)[0])

    cols = ['col{}'.format(idx) for idx in list(range(ncols))]

    df.columns = cols

    # reserve col0 for target
    cols = cols[1:]
    # randomly select ncat cols
    cats = list(set([random.choice(cols) for i in range(ncat)]))

    for cat in cats:
        num_bins = max(1, random.choice(list(range(max_levels))))
        bin_labels = ['level_{}'.format(level) for level in list(range(num_bins))]
        df.loc[:, cat] = pd.cut(df.loc[:, cat], bins=num_bins,
                                labels=bin_labels)
        df.loc[:, cat] = df.loc[:, cat].astype(str)

    if mod_type == 'classification':
        df.loc[:, 'col0'] = pd.cut(df.loc[:, 'col0'], bins=2,
                                   labels=[0, 1])
        df.loc[:, 'col0'] = df.loc[:, 'col0'].astype(int)

    df.rename(columns={'col0': 'target'}, inplace=True)

    if not num_groupby:
        num_groupby = max(1, random.choice(list(range(ncat))))

    catcols = df.loc[:, df.columns != 'target'].select_dtypes(include=['O']).columns.values.tolist()

    random.shuffle(catcols)

    groupby = catcols[0:num_groupby]

    return 'target', groupby, df


def create_accuracy(model_type,
                    cat_df,
                    error_type,
                    groupby=None):
    """
    create error metrics for each slice of the groupby variable.
    i.e. if groupby is type of wine,
    create error metric for all white wine, then all red wine.
    :param groupby: groupby variable -- str -- i.e. 'Type'
    :return: accuracy dataframe for groupby variable
    """
    # use this as an opportunity to capture error metrics for the groupby variable
    if model_type == 'classification':
        error_type = 'RAW'

    acc = cat_df.groupby(groupby).apply(create_insights,
                                        group_var=groupby,
                                        error_type=error_type)
    # drop the grouping indexing
    acc.reset_index(drop=True, inplace=True)
    # append to insights_df
    return acc