"""
DA261 Exercise 2: Vector Search and Classification
TechEd 2025 - SAP HANA Cloud AI Capabilities
Author: Srinivasa Dasari

Covers:
- 2.1 Data Exploration
- 2.3 Vector Similarity Search (TF-IDF)
- 2.4 Classification with Random Forest
"""

import pandas as pd
import numpy as np
from hana_ml import dataframe
from hana_ml.dataframe import create_dataframe_from_pandas
from hana_ml.algorithms.pal.trees import RandomForestClassifier, DecisionTreeClassifier
from sklearn.feature_extraction.text import TfidfVectorizer

# =============================================================================
# 1. CONNECT TO HANA CLOUD
# =============================================================================
def connect_to_hana():
    """Connect to HANA Cloud using PAL_USER"""
    conn = dataframe.ConnectionContext(
        address='04aefaf5-8823-4aef-b849-6e2bdfb3bd7b.hna1.prod-us10.hanacloud.ondemand.com',
        port=443,
        user='PAL_USER',
        password='Initial123',
        encrypt=True,
        sslValidateCertificate=False
    )
    print(f"Connected: {conn.connection.isconnected()}")
    return conn

# =============================================================================
# 2. GENERATE CONSUMER COMPLAINTS DATA
# =============================================================================
def generate_complaints_data(n_rows=300):
    """Generate synthetic consumer complaints data"""
    np.random.seed(42)
    
    products = ['Credit card', 'Mortgage', 'Bank account', 'Student loan', 
                'Personal loan', 'Debt collection', 'Credit reporting']
    companies = ['Chase', 'Wells Fargo', 'Bank of America', 'Citibank', 
                 'Capital One', 'Discover', 'US Bank']
    issues = ['Billing disputes', 'Fraud', 'Customer service', 'Fees', 
              'Account management', 'Collections', 'Credit reporting']
    states = ['CA', 'TX', 'NY', 'FL', 'IL', 'PA', 'OH', 'GA', 'NC', 'MI']
    responses = ['Closed with monetary relief', 'Closed with explanation', 
                 'Closed with non-monetary relief', 'Closed without relief', 'In progress']
    
    # Narrative templates
    narrative_templates = [
        "I noticed unauthorized charges on my account totaling ${amount}. When I called customer service, they were unhelpful.",
        "The company has been calling me at work repeatedly about a debt I already paid. This is harassment.",
        "My credit report shows incorrect information that is damaging my score. I've disputed it multiple times.",
        "I was charged ${amount} in overdraft fees even though I had sufficient funds. The bank refuses to refund.",
        "Someone opened accounts in my name. This is identity theft and the company won't help me resolve it.",
        "The interest rate on my loan increased without any notice. This seems like predatory lending.",
        "I've been trying to close my account for months but they keep finding reasons to keep it open.",
        "The company applied my payment to the wrong account and now says I'm delinquent.",
        "I was promised a promotional rate but was charged the full rate from day one.",
        "Collections keeps calling about a debt that isn't mine. They have the wrong person."
    ]
    
    data = {
        'COMPLAINT_ID': [f'COMP-{str(i).zfill(5)}' for i in range(1, n_rows + 1)],
        'DATE_RECEIVED': pd.date_range(start='2024-01-01', periods=n_rows, freq='D').strftime('%Y-%m-%d').tolist(),
        'PRODUCT': np.random.choice(products, n_rows),
        'ISSUE': np.random.choice(issues, n_rows),
        'COMPANY': np.random.choice(companies, n_rows),
        'STATE': np.random.choice(states, n_rows),
        'NARRATIVE': [t.replace('${amount}', str(np.random.randint(50, 5000))) 
                      for t in np.random.choice(narrative_templates, n_rows)],
        'COMPANY_RESPONSE': np.random.choice(responses, n_rows, p=[0.27, 0.20, 0.19, 0.18, 0.16]),
        'TIMELY_RESPONSE': np.random.choice(['Yes', 'No'], n_rows, p=[0.85, 0.15]),
        'CONSUMER_DISPUTED': np.random.choice(['Yes', 'No'], n_rows, p=[0.30, 0.70])
    }
    
    return pd.DataFrame(data)

# =============================================================================
# 3. EXERCISE 2.1 - DATA EXPLORATION
# =============================================================================
def explore_data(conn, complaints_df):
    """Upload and explore complaints data"""
    
    # Upload to HANA
    complaints_hdf = create_dataframe_from_pandas(
        conn,
        complaints_df,
        table_name='CONSUMER_COMPLAINTS',
        schema='DBADMIN',
        force=True
    )
    print(f"Uploaded {complaints_hdf.count()} complaints")
    
    # Explore distributions
    print("\n=== Product Distribution ===")
    product_dist = complaints_hdf.agg([('count', 'COMPLAINT_ID', 'COUNT')], group_by='PRODUCT')
    print(product_dist.collect())
    
    print("\n=== Company Distribution ===")
    company_dist = complaints_hdf.agg([('count', 'COMPLAINT_ID', 'COUNT')], group_by='COMPANY')
    print(company_dist.collect())
    
    print("\n=== Response Distribution ===")
    response_dist = complaints_hdf.agg([('count', 'COMPLAINT_ID', 'COUNT')], group_by='COMPANY_RESPONSE')
    print(response_dist.collect())
    
    return complaints_hdf

# =============================================================================
# 4. EXERCISE 2.3 - VECTOR SIMILARITY SEARCH
# =============================================================================
def create_vector_table(conn):
    """Create table with REAL_VECTOR column for storing embeddings"""
    cursor = conn.connection.cursor()
    
    # Drop if exists
    try:
        cursor.execute('DROP TABLE DBADMIN.COMPLAINT_VECTORS')
    except:
        pass
    
    # Create with REAL_VECTOR column
    cursor.execute('''
        CREATE TABLE DBADMIN.COMPLAINT_VECTORS (
            COMPLAINT_ID NVARCHAR(20) PRIMARY KEY,
            NARRATIVE NCLOB,
            EMBEDDING REAL_VECTOR(100)
        )
    ''')
    print("Created COMPLAINT_VECTORS table with REAL_VECTOR(100)")

def create_tfidf_embeddings(complaints_df):
    """Create TF-IDF embeddings for narratives"""
    
    vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(complaints_df['NARRATIVE'].values)
    vectors = tfidf_matrix.toarray()
    
    print(f"Created TF-IDF embeddings: {vectors.shape[0]} docs x {vectors.shape[1]} dimensions")
    return vectorizer, vectors

def insert_vectors(conn, complaints_df, vectors):
    """Insert complaints with embeddings into HANA"""
    cursor = conn.connection.cursor()
    
    for i, row in complaints_df.iterrows():
        vector_str = ','.join([str(v) for v in vectors[i]])
        cursor.execute(f'''
            INSERT INTO DBADMIN.COMPLAINT_VECTORS (COMPLAINT_ID, NARRATIVE, EMBEDDING)
            VALUES ('{row["COMPLAINT_ID"]}', '{row["NARRATIVE"].replace("'", "''")}', 
                    TO_REAL_VECTOR('[{vector_str}]'))
        ''')
    
    conn.connection.commit()
    print(f"Inserted {len(complaints_df)} vectors")

def semantic_search(conn, vectorizer, query, top_k=5):
    """Perform semantic similarity search"""
    
    # Vectorize query
    query_vector = vectorizer.transform([query]).toarray()[0]
    vector_str = ','.join([str(v) for v in query_vector])
    
    # Search using COSINE_SIMILARITY
    sql = f'''
        SELECT COMPLAINT_ID, NARRATIVE,
            COSINE_SIMILARITY(EMBEDDING, TO_REAL_VECTOR('[{vector_str}]')) AS SIMILARITY
        FROM DBADMIN.COMPLAINT_VECTORS
        ORDER BY SIMILARITY DESC
        LIMIT {top_k}
    '''
    
    result = conn.sql(sql).collect()
    print(f"\nQuery: '{query}'")
    print(f"Top {top_k} results:")
    for _, row in result.iterrows():
        print(f"  {row['SIMILARITY']:.4f} - {row['NARRATIVE'][:80]}...")
    
    return result

# =============================================================================
# 5. EXERCISE 2.4 - CLASSIFICATION
# =============================================================================
def prepare_classification_data(conn, complaints_df):
    """Prepare data for classification - predict monetary relief"""
    
    # Encode categorical features
    product_map = {p: i for i, p in enumerate(complaints_df['PRODUCT'].unique())}
    company_map = {c: i for i, c in enumerate(complaints_df['COMPANY'].unique())}
    issue_map = {s: i for i, s in enumerate(complaints_df['ISSUE'].unique())}
    state_map = {s: i for i, s in enumerate(complaints_df['STATE'].unique())}
    
    # Create feature dataframe
    train_df = pd.DataFrame({
        'ID': range(len(complaints_df)),
        'PRODUCT_CODE': complaints_df['PRODUCT'].map(product_map),
        'COMPANY_CODE': complaints_df['COMPANY'].map(company_map),
        'ISSUE_CODE': complaints_df['ISSUE'].map(issue_map),
        'STATE_CODE': complaints_df['STATE'].map(state_map),
        'TIMELY': (complaints_df['TIMELY_RESPONSE'] == 'Yes').astype(int),
        'DISPUTED': (complaints_df['CONSUMER_DISPUTED'] == 'Yes').astype(int),
        'TARGET': (complaints_df['COMPANY_RESPONSE'] == 'Closed with monetary relief').astype(int)
    })
    
    print(f"Target Distribution:")
    print(f"  No Relief: {(train_df['TARGET'] == 0).sum()}")
    print(f"  Monetary Relief: {(train_df['TARGET'] == 1).sum()}")
    print(f"  Relief Rate: {train_df['TARGET'].mean()*100:.1f}%")
    
    # Upload to HANA
    train_hdf = create_dataframe_from_pandas(
        conn,
        train_df,
        table_name='COMPLAINT_TRAIN',
        schema='DBADMIN',
        force=True,
        primary_key='ID'
    )
    
    return train_hdf, train_df

def train_random_forest(train_hdf, features, target='TARGET'):
    """Train Random Forest classifier"""
    
    rf_clf = RandomForestClassifier(
        n_estimators=50,
        max_depth=10
    )
    
    print("Training Random Forest...")
    rf_clf.fit(
        data=train_hdf,
        key='ID',
        features=features,
        label=target
    )
    print("Training complete!")
    
    return rf_clf

def evaluate_model(rf_clf, train_hdf, train_df, features):
    """Evaluate model and show feature importance"""
    
    # Predict
    predictions = rf_clf.predict(
        data=train_hdf,
        key='ID',
        features=features
    )
    
    pred_df = predictions.collect()
    actual = train_df['TARGET'].values
    predicted = pred_df['SCORE'].astype(int).values
    
    # Accuracy
    accuracy = (actual == predicted).mean()
    print(f"\nAccuracy: {accuracy*100:.1f}%")
    
    # Confusion matrix
    results = list(zip(actual, predicted))
    tn = results.count((0, 0))
    fp = results.count((0, 1))
    fn = results.count((1, 0))
    tp = results.count((1, 1))
    
    print(f"\nConfusion Matrix:")
    print(f"  True Negatives: {tn}")
    print(f"  False Positives: {fp}")
    print(f"  False Negatives: {fn}")
    print(f"  True Positives: {tp}")
    
    # Metrics
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    print(f"\nMetrics:")
    print(f"  Precision: {precision*100:.1f}%")
    print(f"  Recall: {recall*100:.1f}%")
    print(f"  F1 Score: {f1*100:.1f}%")
    
    # Feature importance
    if hasattr(rf_clf, 'feature_importances_') and rf_clf.feature_importances_ is not None:
        importance_df = rf_clf.feature_importances_.collect()
        print(f"\nFeature Importance:")
        print(importance_df.sort_values('IMPORTANCE', ascending=False))
    
    return predictions

# =============================================================================
# MAIN EXECUTION
# =============================================================================
if __name__ == "__main__":
    # Connect
    conn = connect_to_hana()
    
    # Generate data
    complaints_df = generate_complaints_data(300)
    print(f"Generated {len(complaints_df)} consumer complaints")
    
    # Exercise 2.1 - Explore
    print("\n" + "="*60)
    print("EXERCISE 2.1: DATA EXPLORATION")
    print("="*60)
    complaints_hdf = explore_data(conn, complaints_df)
    
    # Exercise 2.3 - Vector Search
    print("\n" + "="*60)
    print("EXERCISE 2.3: VECTOR SIMILARITY SEARCH")
    print("="*60)
    create_vector_table(conn)
    vectorizer, vectors = create_tfidf_embeddings(complaints_df)
    insert_vectors(conn, complaints_df, vectors)
    
    # Test searches
    semantic_search(conn, vectorizer, "Someone stole my identity")
    semantic_search(conn, vectorizer, "calling me at work about debt")
    semantic_search(conn, vectorizer, "charged fees without telling me")
    
    # Exercise 2.4 - Classification
    print("\n" + "="*60)
    print("EXERCISE 2.4: CLASSIFICATION")
    print("="*60)
    features = ['PRODUCT_CODE', 'COMPANY_CODE', 'ISSUE_CODE', 'STATE_CODE', 'TIMELY', 'DISPUTED']
    train_hdf, train_df = prepare_classification_data(conn, complaints_df)
    rf_clf = train_random_forest(train_hdf, features)
    evaluate_model(rf_clf, train_hdf, train_df, features)
    
    print("\n✅ Exercise 2 Complete!")
