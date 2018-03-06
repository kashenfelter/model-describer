from mdesc.eval import ErrorViz
from sklearn.ensemble import RandomForestClassifier
import pandas as pd
import numpy as np
import requests
import io

def create_wine_data(cat_cols):
    """
    create UCI wine machine learning dataset
    https://archive.ics.uci.edu/ml/machine-learning-databases/wine-quality

    :param cat_cols: columns to convert to categories
    :return UCI wine machine learning dataset
    :rtype pd.DataFrame
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



df = create_wine_data(None)

# set up y var
# set up some params
ydepend = 'quality'

# turn it into a binary classification problem
df.loc[:, ydepend] = df.loc[:, ydepend].apply(lambda x: 0 if x < 5 else 1)

# convert categorical
model_df = pd.get_dummies(df.loc[:, df.columns != ydepend])

# build model
clf = RandomForestClassifier(max_depth=2, random_state=0)
clf.fit(model_df,
        df.loc[:, ydepend])

from sklearn.utils.validation import check_is_fitted

EV = ErrorViz(clf,
              model_df=model_df,
              ydepend=ydepend,
              cat_df=df,
              keepfeaturelist=None,
              groupbyvars=['alcohol'],
              aggregate_func=np.mean,
              verbose=None,
              autoformat_types=True
              )

EV.run(output_path='error_viz_classification.html',
       output_type='html')

