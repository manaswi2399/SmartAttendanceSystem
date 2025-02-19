import boto3
import openai
from flask import Flask, request, jsonify
from flask_cors import CORS
import datetime
from flask_socketio import SocketIO
from openai import OpenAIError 

app = Flask(__name__)
CORS(app)  # Allows frontend requests
socketio = SocketIO(app, cors_allowed_origins="*")


# AWS Configuration
BUCKET_NAME = "smart-attendance-bucket"
COLLECTION_ID = "student-faces"
TABLE_NAME = "AttendanceRecords"


# Function to query attendance records
def get_attendance_data():
    response = dynamodb.scan(TableName=TABLE_NAME)  # Fetch all attendance data
    records = []
    
    for item in response.get("Items", []):
        records.append({
            "student_id": item["student_id"]["S"],
            "timestamp": item["timestamp"]["S"]
        })
    
    return records

@app.route("/chat", methods=["POST"])
def chat():
    user_query = request.json["message"]  # Get the user’s question

    # Fetch attendance records
    attendance_data = get_attendance_data()

    # Format the query for GPT
    prompt = f"""
    You are an AI assistant for a smart attendance system. Answer based on attendance data:
    Attendance Data: {attendance_data}
    User Query: {user_query}
    """

    try:
        # Use OpenAI's updated method
        client = openai.OpenAI(api_key="{API_KEY}")
        response = client.chat.completions.create( model="gpt-3.5-turbo", messages=[{"role": "user", "content": user_query}])


        # Extract AI-generated response
        ai_response = response["choices"][0]["message"]["content"]

        return jsonify({"reply": ai_response})
    
    except OpenAIError as e:
        return jsonify({"error": str(e)}), 500


s3 = boto3.client("s3")  # Connect to AWS S3
rekognition = boto3.client("rekognition")
dynamodb = boto3.client("dynamodb")

@app.route("/index-face", methods=["POST"])
def index_face():
    data = request.json  # Get JSON data from React
    file_name = data["fileName"]  # Image file name

    # Call AWS Rekognition to detect and store the face
    response = rekognition.index_faces(
        CollectionId=COLLECTION_ID,
        Image={"S3Object": {"Bucket": BUCKET_NAME, "Name": file_name}},
        ExternalImageId=file_name.split(".")[0],  # Use filename (without extension) as student ID
        MaxFaces=1,
        QualityFilter="AUTO",
        DetectionAttributes=["ALL"]
    )

    if not response["FaceRecords"]:
        return jsonify({"message": "No face detected in image."}), 400

    face_id = response["FaceRecords"][0]["Face"]["FaceId"]
    return jsonify({"message": "Face indexed successfully!", "FaceId": face_id})


@app.route("/store-attendance", methods = ["POST"])
def store_attendance():
    data = request.json
    student_id = data["student_id"]
    timestamp = datetime.datetime.now().isoformat()

    dynamodb.put_item(
        TableName=TABLE_NAME,
        Item={
            "student_id": {"S": student_id},
            "timestamp": {"S": timestamp}
        }
    )

    return jsonify({"message": "Attendance recorded successfully!", "student_id": student_id, "timestamp": timestamp})


@app.route("/match-face", methods = ["POST"])
def match_face():
    data = request.json
    file_name = data["fileName"]

    response = rekognition.search_faces_by_image(
        CollectionId=COLLECTION_ID,
        Image={"S3Object": {"Bucket": BUCKET_NAME, "Name": file_name}},
        MaxFaces=1,
        FaceMatchThreshold=85  # Confidence threshold for a match
    )

    if not response["FaceMatches"]:
        return jsonify({"message": "No face match found"}), 404
    
    matched_face = response["FaceMatches"][0]
    student_id = matched_face["Face"]["ExternalImageId"]
    confidence = matched_face["Similarity"]

    return jsonify({"message": "Face matched", "student_id": student_id, "confidence": confidence})

@app.route("/get-presigned-url", methods=["GET"])
def get_presigned_url():
    file_name = request.args.get("fileName")  # Get filename from React

    # Generate a Pre-Signed URL
    upload_url = s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": BUCKET_NAME, "Key": file_name, "ContentType": "image/jpeg"},
        ExpiresIn=3600  # URL valid for 1 hour
    )
    
    return jsonify({"uploadURL": upload_url})  # Send URL to React

if __name__ == "__main__":
    app.run(debug=True, port=5000)
    socketio.run(app, debug=True, port=5000)
