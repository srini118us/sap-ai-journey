import os, joblib, pandas as pd
from hdbcli import dbapi
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

conn = dbapi.connect(
    address=os.environ["HANA_HOST"],
    port=int(os.environ.get("HANA_PORT", "443")),
    user=os.environ["HANA_USER"],
    password=os.environ["HANA_PASSWORD"],
    encrypt=True,
    sslValidateCertificate=True,
)

df = pd.read_sql('SELECT * FROM ML_PAYMENT.VENDOR_PAYMENTS', conn)
conn.close()

label = "IS_DELAYED"
drop_cols = [label, "DELAY_DAYS", "INVOICE_ID", "VENDOR_ID",
             "NET_DUE_DATE", "CLEARING_DATE"]
X = pd.get_dummies(df.drop(columns=drop_cols), columns=["COMPANY_CODE"],
                   drop_first=True)
y = df[label]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

pos = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
model = XGBClassifier(
    n_estimators=200, max_depth=6, learning_rate=0.1,
    scale_pos_weight=pos, eval_metric="logloss", random_state=42,
)
model.fit(X_train, y_train)

pred = model.predict(X_test)
print("accuracy", accuracy_score(y_test, pred))
print("f1", f1_score(y_test, pred))
print("auc", roc_auc_score(y_test, model.predict_proba(X_test)[:, 1]))

out = "/app/model"
os.makedirs(out, exist_ok=True)
joblib.dump(model, os.path.join(out, "model.joblib"))
joblib.dump(list(X.columns), os.path.join(out, "columns.joblib"))
print("saved artifacts to", out)