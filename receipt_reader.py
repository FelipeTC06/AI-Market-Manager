from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os
import google.generativeai as genai
import tempfile
import json
from pymongo import MongoClient

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client["AI_Market_Manager"]
purchases_collection = db["purchases"]

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(model_name="gemini-1.5-flash")

app = Flask(__name__)

@app.route('/receipt_reader', methods=['POST'])
def receipt_reader():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400

    image = request.files['image']

    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpeg") as temp:
        temp.write(image.read())
        temp.flush()

        sample_file = genai.upload_file(path=temp.name, display_name=image.filename)

    response = model.generate_content([
        sample_file, 
        "Create a valid JSON containing each item from the receipt with its respective information (name, quantity as a number, unit_price as a number, total_price as a number), the total amount of the purchase as a number, and the purchase_date."
    ])

    response_text = response.text.replace("```json\n", "").replace("```", "")

    try:
        response_json = json.loads(response_text)
    except json.JSONDecodeError as e:
        return jsonify({'error': 'Failed to parse JSON', 'details': str(e)}), 500

    return jsonify(response_json), 200

@app.route('/save_purchase', methods=['POST'])
def save_purchase():
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        if "items" not in data or "purchase_date" not in data or "total_amount" not in data:
            return jsonify({'error': 'Missing required fields'}), 400

        purchase_id = purchases_collection.insert_one(data).inserted_id

        return jsonify({'message': 'Purchase saved successfully', 'purchase_id': str(purchase_id)}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to process purchase', 'details': str(e)}), 500

@app.route('/get_all_purchases/<int:user_id>', methods=['GET'])
def get_all_purchases(user_id):
    try:
        purchases = list(purchases_collection.find({"user_id": user_id}, {"_id": 0}))
        
        if not purchases:
            return jsonify({'message': 'No purchases found for this user'}), 404
        
        return jsonify(purchases), 200
    except Exception as e:
        return jsonify({'error': 'Failed to fetch purchases', 'details': str(e)}), 500

    

if __name__ == '__main__':
    app.run(debug=True)
