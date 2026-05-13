import pandas as pd
import pickle
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix


def train():
    df = pd.read_csv('data/gestures.csv', header=None)

    df.columns = ['gesture'] + [f'feature_{i}' for i in range(len(df.columns) - 1)]

    # Print dataset statistics
    print("\n=== DATASET STATISTICS ===")
    print(f"Total samples: {len(df)}")
    print("\nSamples per gesture:")
    gesture_counts = df['gesture'].value_counts().sort_index()
    for gesture, count in gesture_counts.items():
        print(f"  {gesture}: {count} rows")

    X = df.drop('gesture', axis=1)
    y = df['gesture']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print(f"\nTraining set: {len(X_train)} samples")
    print(f"Test set: {len(X_test)} samples")

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    # Print overall accuracy
    print(f'\n=== MODEL PERFORMANCE ===')
    print(f'Overall accuracy: {accuracy:.2%}')

    # Print per-gesture accuracy breakdown
    print("\n=== PER-GESTURE ACCURACY ===")
    print(classification_report(y_test, y_pred, zero_division=0))

    # Print confusion matrix
    print("\n=== CONFUSION MATRIX ===")
    cm = confusion_matrix(y_test, y_pred, labels=sorted(y.unique()))
    print(f"Labels: {sorted(y.unique())}")
    print(cm)

    with open('data/gesture_model.pkl', 'wb') as f:
        pickle.dump(model, f)

    print(f'\n✓ Model saved to data/gesture_model.pkl')


if __name__ == "__main__":
    train()
