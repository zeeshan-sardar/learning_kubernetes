from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier
import joblib

# Load data and train a simple model
iris = load_iris()
model = RandomForestClassifier(n_estimators=10)
model.fit(iris.data, iris.target)

# Save the model
joblib.dump(model, 'model.joblib')
print("Model saved!")