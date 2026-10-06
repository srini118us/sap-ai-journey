import os
from dotenv import load_dotenv
from hdbcli import dbapi
load_dotenv()
c = dbapi.connect(address=os.environ["DSP_HOST"], port=443, user=os.environ["DSP_USER"],
                  password=os.environ["DSP_PASSWORD"], encrypt=True)
cur = c.cursor()
cur.execute('SELECT SUPPLIER, LEFT(ERROR_MESSAGE,300) FROM "UC4_PROC#SCORING"."SUPPLIER_RISK_DECISION_LOG" WHERE STATUS = \'ERROR\'')
for r in cur.fetchall()[:5]:
    print(r)
