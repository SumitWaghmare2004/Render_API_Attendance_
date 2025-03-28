
#================================================ Skips GUI on Render and not on local system
import cv2
import numpy as np
import os
import json
from PIL import Image as PILImage, ImageTk
from datetime import datetime
from flask import Flask, jsonify  # Flask for API

# Initialize Flask
app = Flask(__name__)

# Check if running on Render
if os.environ.get("RENDER"):
    print("Running on Render, skipping Tkinter GUI")
    root = None  # No Tkinter in Render
else:
    from tkinter import *
    from tkinter import messagebox
    root = Tk()
    root.title("Attendance System")

if root:  # Only execute GUI-related code if Tkinter is enabled
    # Load the background image
    # background_image = Image.open("Resources/background.png")
    background_image = PILImage.open("Resources/background.png")
    background_image = background_image.resize((1280, 720), PILImage.Resampling.LANCZOS)
    background_photo = ImageTk.PhotoImage(background_image)

    # Load the image to display after marking attendance
    marked_image_path = "Resources/3.png"
    marked_image = PILImage.open(marked_image_path)

    # Create a white background of 640x495 pixels
    background = PILImage.new('RGB', (640, 495), (255, 255, 255))

    # Calculate the position to paste the marked image at the center
    marked_image_width, marked_image_height = marked_image.size
    center_x = (640 - marked_image_width) // 2
    center_y = (495 - marked_image_height) // 2

    # Paste the marked image onto the background at the center
    background.paste(marked_image, (center_x, center_y))

    marked_photo = ImageTk.PhotoImage(background)

    # Set up the GUI elements
    canvas = Canvas(root, width=1280, height=720)
    canvas.pack()
    canvas.create_image(0, 0, anchor=NW, image=background_photo)

    # Adjust positions for the elements
    video_label = Label(root)
    canvas.create_window(50, 150, anchor=NW, window=video_label)

    # Title label
    title_label = Label(root, text="Attendance Status", font=("Algerian", 15, "bold"), bg='white', fg='black')
    canvas.create_window(1007, 75, anchor="center", window=title_label)

    # Info label
    info_label = Label(root, text="Information will be displayed here.", font=("Helvetica", 16), bg='white')
    canvas.create_window(820, 150, anchor=NW, window=info_label)

# Initialize webcam
video_capture = cv2.VideoCapture(0)

# Initialize face cascade
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Load face coordinates and names from JSON file
def load_face_coordinates():
    try:
        with open('coordinates_data.json', 'r') as file:
            data = json.load(file)
            return {name: [list(map(int, coords)) for coords in coords_list] for name, coords_list in data.items()}
    except FileNotFoundError:
        print("coordinates_data.json not found.")
        return {}

face_coordinates = load_face_coordinates()

# Load additional person info
def load_person_info():
    person_info = {}
    try:
        with open('person_info.txt', 'r') as file:
            for line in file:
                if ':' in line:
                    name, info = line.split(':', 1)
                    person_info[name.strip()] = info.strip()
    except FileNotFoundError:
        print("person_info.txt not found.")
    return person_info

person_info = load_person_info()

unrecognized_shown = False  # Flag to show error message only once
attendance_marked = False  # Flag to track if attendance is already marked

ATTENDANCE_FILE = "attendance.txt"  # Attendance file path

def mark_attendance(name):
    """Marks attendance and saves to file."""
    with open(ATTENDANCE_FILE, "a") as f: 
        f.write(f"{name}, {datetime.now()}\n")

def process_frame():
    global unrecognized_shown, attendance_marked, video_capture

    ret, frame = video_capture.read()
    if not ret:
        return

    frame = cv2.resize(frame, (640, 495))

    if attendance_marked:
        video_capture.release()
        cv2.destroyAllWindows()

        if root:  # Only update GUI if Tkinter is enabled
            video_label.imgtk = marked_photo
            video_label.configure(image=marked_photo)
        return  

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

    detected_any_face = False
    for (x, y, w, h) in faces:
        detected = False

        for name, coords_list in face_coordinates.items():
            for coords in coords_list:
                cx, cy, cw, ch = coords
                if (abs(x - cx) < 20 and abs(y - cy) < 20 and
                    abs(w - cw) < 20 and abs(h - ch) < 20):
                    info = person_info.get(name, None)
                    if root:
                        if info:
                            info_label.config(text=f"\n\nName: {name}\n\n\tTime: {datetime.now().strftime('%H:%M:%S')}\n\n{info}\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n Have a Nice Day!")
                        else:
                            info_label.config(text=f"\n\nName: {name}\n\nTime: {datetime.now().strftime('%H:%M:%S')}\n\n\n\n\n\n\n\n\n\n\n\n\n\n\t\t Have a Nice Day!")
                    
                    mark_attendance(name)
                    attendance_marked = True
                    unrecognized_shown = False
                    detected = True
                    detected_any_face = True
                    break
            if detected:
                break

        if not detected:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.rectangle(frame, (x, y+h-35), (x+w, y+h), (0, 255, 0), cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame, "Unknown", (x + 6, y+h - 6), font, 1.0, (255, 255, 255), 1)

    if not detected_any_face and not unrecognized_shown and root:
        messagebox.showerror("Error", "Face not recognized!")
        unrecognized_shown = True

    if root:
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = PILImage.fromarray(image)
        image = ImageTk.PhotoImage(image)
        video_label.imgtk = image
        video_label.configure(image=image)
        video_label.after(10, process_frame)

# Flask API to fetch attendance data
@app.route('/get_attendance', methods=['GET'])
def get_attendance():
    """API endpoint to fetch attendance data."""
    if not os.path.exists(ATTENDANCE_FILE):
        return jsonify([])
    
    with open(ATTENDANCE_FILE, "r") as file:
        lines = file.readlines()
    
    attendance_list = []
    for line in lines:
        name, time = line.strip().split(",")  
        attendance_list.append({"name": name, "time": time})
    
    return jsonify(attendance_list)

if __name__ == "__main__":
    import threading
    flask_thread = threading.Thread(target=lambda: app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=False))
    flask_thread.daemon = True
    flask_thread.start()
    
    if root:  # Only run GUI if Tkinter is enabled
        process_frame()
        root.mainloop()
