import React, {useRef, useState } from "react";
import Webcam from "react-webcam";
import axios from "axios";

const SERVER_URL = "http://localhost:5000";

function App() {
    const webcamRef = useRef(null);
    const [image, setImage] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [faceMessage, setFaceMessage] = useState("");
    const [userMessage, setUserMessage] = useState("");
    const [chat, setChat] = useState([]);


    const sendMessage = async () => {
      if (!userMessage) return;

      const newChat = [...chat, { sender: "User", text: userMessage }];
      setChat(newChat);

      try {
          const response = await axios.post(`${SERVER_URL}/chat`, { message: userMessage });
          setChat([...newChat, { sender: "AI", text: response.data.reply }]);
      } catch (error) {
          console.error("Chat error:", error);
      }

      setUserMessage("");
  };


    const captureImage = async (action) => {
        setUploading(true);
        setFaceMessage("");

        // Capture the image
        const imageSrc = webcamRef.current.getScreenshot();
        
        // Convert base64 to Blob
        const blob = await fetch(imageSrc).then(res => res.blob());

        // Generate a unique filename
        const fileName = `student-${Date.now()}.jpg`;

        try {
            // Get a pre-signed URL from Flask
            const { data } = await axios.get(`${SERVER_URL}/get-presigned-url?fileName=${fileName}`);

            // Upload the file to S3
            await axios.put(data.uploadURL, blob, {
                headers: { "Content-Type": "image/jpeg" }
            });

            setImage(imageSrc);

            // Call the Flask API to index the face
            if (action === "register"){
              const faceResponse = await axios.post(`${SERVER_URL}/index-face`, { fileName });
              setFaceMessage(faceResponse.data.message);
            }

            if (action === "recognize"){
              const faceResponse = await axios.post(`${SERVER_URL}/match-face`, { fileName })
              setFaceMessage(`Student Recognized: ${faceResponse.data.student_id} (Confidence: ${faceResponse.data.confidence.toFixed(2)}%)`);
              const student_id = faceResponse.data.student_id;
              await axios.post(`${SERVER_URL}/store-attendance`, { student_id: student_id })

            }

            
        } catch (error) {
            console.error("Error:", error);
            alert("Something went wrong!");
        }

        setUploading(false);
    };

    return (
        <div style={{ textAlign: "center", padding: "20px" }}>
            <h1>Smart Attendance System</h1>
            <Webcam ref={webcamRef} screenshotFormat="image/jpeg" width={400} height={300} />
            <br />
            <button onClick={() => captureImage("register")} disabled={uploading}>
                {uploading ? "Registering..." : "Register Student"}
            </button>
            <button onClick={() => captureImage("recognize")} disabled={uploading}>
                {uploading ? "Recognizing..." : "Recognize Student"}
            </button>
            <br />
            {image && <img src={image} alt="Captured" width="300" />}
            <h3>{faceMessage}</h3>


            <div style={{ maxWidth: "600px", margin: "auto", textAlign: "center", padding: "20px" }}>
            <h1>AI Attendance Chatbot</h1>
            <div style={{ height: "300px", overflowY: "auto", border: "1px solid #ddd", padding: "10px" }}>
                {chat.map((msg, index) => (
                    <p key={index} style={{ textAlign: msg.sender === "User" ? "right" : "left" }}>
                        <strong>{msg.sender}: </strong> {msg.text}
                    </p>
                ))}
            </div>
            <input
                type="text"
                value={userMessage}
                onChange={(e) => setUserMessage(e.target.value)}
                placeholder="Ask about attendance..."
                style={{ width: "80%", padding: "10px", marginTop: "10px" }}
            />
            <button onClick={sendMessage} style={{ marginLeft: "10px", padding: "10px" }}>
                Send
            </button>
        </div>
        </div>
    );
}

export default App;
