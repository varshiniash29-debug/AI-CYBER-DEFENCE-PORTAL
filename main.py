import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import ComplementNB
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, classification_report


# -------- LOAD DATA --------
print("Loading dataset...")

df = pd.read_csv("data/final_data_v2.csv", encoding="latin1")

# Keep only required columns
df = df[["text", "label"]]

# Drop missing values
df.dropna(inplace=True)

print("\nTotal rows:", len(df))
print("\nLabel distribution:\n")
print(df["label"].value_counts())


# -------- BALANCE CLASSES --------
print("\nBalancing classes...")
max_count = df["label"].value_counts().max()
balanced_parts = []
for label, group in df.groupby("label"):
    if len(group) < int(max_count * 0.6):
        group = group.sample(int(max_count * 0.6), replace=True, random_state=42)
    balanced_parts.append(group)
df = pd.concat(balanced_parts).sample(frac=1, random_state=42).reset_index(drop=True)

print("\nBalanced label distribution:\n")
print(df["label"].value_counts())


# -------- SPLIT DATA --------
print("\nSplitting data...")

X = df["text"]
y = df["label"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)


# -------- VECTORIZATION --------
print("\nVectorizing text...")

vectorizer = TfidfVectorizer(
    stop_words="english",
    max_features=5000
)

X_train_vec = vectorizer.fit_transform(X_train)
X_test_vec = vectorizer.transform(X_test)


# -------- TRAIN MODEL --------
print("\nTraining model...")

base_model = ComplementNB()
model = CalibratedClassifierCV(base_model, cv=3, method='sigmoid')
model.fit(X_train_vec, y_train)


# -------- EVALUATE --------
print("\nEvaluating model...")

y_pred = model.predict(X_test_vec)

accuracy = accuracy_score(y_test, y_pred)

print("\nAccuracy:", accuracy)

print("\nClassification Report:\n")
print(classification_report(y_test, y_pred))


# -------- SAVE MODEL --------
print("\nSaving model...")

joblib.dump(model, "models/model.pkl")
joblib.dump(vectorizer, "models/vectorizer.pkl")

print("\nModel and vectorizer saved in /models folder ✔")