from sklearn.ensemble import RandomForestClassifier

FEATURES = ['MACD', 'RSI', 'EMA_12', 'EMA_26', 'BB_UPPER', 'BB_LOWER', 'RET_1D']


def train_classifier(df):
    X = df[FEATURES]
    y = df['TARGET']
    model = RandomForestClassifier(n_estimators=200, random_state=42)
    model.fit(X, y)
    return model
