import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import xgboost as xgb
import joblib
import os

# Load the dataset
df = pd.read_csv('gdpr-processed-data.csv')

# Data preprocessing and feature engineering
def preprocess_data(df):
    # Create a copy to avoid modifying the original dataframe
    df_processed = df.copy()
    
    # Handle encrypted rows - extract age and salary ranges
    def extract_range_midpoint(range_str, column):
        if 'encrypted' in df_processed['encryption_status'].values:
            if '-' in str(range_str):
                low, high = map(int, str(range_str).split('-'))
                return (low + high) / 2
        return range_str
    
    # Process Age column
    df_processed['Age_processed'] = df_processed.apply(
        lambda row: extract_range_midpoint(row['Age'], 'Age') 
        if row['encryption_status'] == 'encrypted' else int(row['Age']), 
        axis=1
    )
    
    # Process Salary column
    df_processed['Salary_processed'] = df_processed.apply(
        lambda row: extract_range_midpoint(row['Salary'], 'Salary') 
        if row['encryption_status'] == 'encrypted' else int(row['Salary']), 
        axis=1
    )
    
    # Create features from email for non-encrypted rows
    df_processed['email_domain'] = df_processed.apply(
        lambda row: row['Email'].split('@')[1] if row['encryption_status'] == 'non_encrypted' and '@' in str(row['Email']) 
        else "unknown", 
        axis=1
    )
    
    # Create name length feature
    df_processed['name_length'] = df_processed.apply(
        lambda row: len(row['Name']) if row['encryption_status'] == 'non_encrypted' and row['Name'] != '********' 
        else np.nan, 
        axis=1
    )
    
    # Extract name parts count (first/last name, etc.)
    df_processed['name_parts'] = df_processed.apply(
        lambda row: len(row['Name'].split()) if row['encryption_status'] == 'non_encrypted' and row['Name'] != '********' 
        else np.nan, 
        axis=1
    )
    
    # Fill NaN values with median for numerical columns
    for col in ['name_length', 'name_parts']:
        median_val = df_processed[df_processed['encryption_status'] == 'non_encrypted'][col].median()
        df_processed[col].fillna(median_val, inplace=True)
    
    # Create email length feature
    df_processed['email_length'] = df_processed.apply(
        lambda row: len(row['Email']) if row['encryption_status'] == 'non_encrypted' 
        else np.nan, 
        axis=1
    )
    median_email_length = df_processed[df_processed['encryption_status'] == 'non_encrypted']['email_length'].median()
    df_processed['email_length'].fillna(median_email_length, inplace=True)
    
    # Extract most common email domains
    top_domains = df_processed[df_processed['encryption_status'] == 'non_encrypted']['email_domain'].value_counts().head(5).index.tolist()
    df_processed['domain_category'] = df_processed['email_domain'].apply(
        lambda x: x if x in top_domains else 'other'
    )
    
    # One-hot encode the domain category
    domain_dummies = pd.get_dummies(df_processed['domain_category'], prefix='domain')
    df_processed = pd.concat([df_processed, domain_dummies], axis=1)
    
    # Drop the original columns we no longer need
    columns_to_drop = ['ID', 'Name', 'Age', 'Email', 'Salary', 'email_domain', 'domain_category']
    df_processed.drop(columns=columns_to_drop, inplace=True)
    
    return df_processed

# Preprocess the data
print("Preprocessing data...")
processed_df = preprocess_data(df)

# Split features and target
X = processed_df.drop('encryption_status', axis=1)
y = processed_df['encryption_status']

# Encode the target variable to numeric values
print("Encoding target variable...")
label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)

# Create train-test split
X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded)

# Create preprocessing pipeline for numerical features
print("Building model pipeline...")
numeric_features = ['Age_processed', 'Salary_processed', 'name_length', 'name_parts', 'email_length']
numeric_transformer = Pipeline(steps=[
    ('scaler', StandardScaler())
])

# Create the preprocessor
preprocessor = ColumnTransformer(
    transformers=[
        ('num', numeric_transformer, numeric_features)
    ],
    remainder='passthrough'  # This will pass through all other columns
)

# Define model pipeline with XGBoost - optimized parameters for quick training
model = Pipeline(steps=[
    ('preprocessor', preprocessor),
    ('classifier', xgb.XGBClassifier(
        objective='binary:logistic',
        use_label_encoder=False,
        eval_metric='logloss',
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        random_state=42))
])

# Train the model
print("Training the model...")
model.fit(X_train, y_train)

# Create a dictionary with all necessary components for prediction
gdpr_model_package = {
    'model': model,
    'label_encoder': label_encoder,
    'feature_names': X.columns.tolist(),
    'numeric_features': numeric_features
}

# Save only the model package to the runtime folder
print("Saving model to the current directory...")
joblib.dump(gdpr_model_package, 'gdpr_model_package.pkl')

print(f"Model saved successfully to {os.path.abspath('gdpr_model_package.pkl')}")
print("You can now use this model in a separate Python file for prediction.")
