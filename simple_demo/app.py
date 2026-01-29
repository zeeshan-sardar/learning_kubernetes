from flask import Flask, request, jsonify
import joblib
import numpy as np

app = Flask(__name__)
model = joblib.load('model.joblib')

CLASS_NAMES = ['setosa', 'versicolor', 'virginica']

@app.route('/predict', methods=['POST'])
def predict():
    data = request.json
    features = np.array(data['features']).reshape(1, -1)
    
    prediction = model.predict(features)[0]
    confidence = model.predict_proba(features).max()
    
    return jsonify({
        'prediction': int(prediction),
        'class_name': CLASS_NAMES[prediction],
        'confidence': float(confidence),
        'version': 'v2'
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)