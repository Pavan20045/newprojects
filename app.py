from moviepy.editor import *
import os
import requests
import tempfile
import json
import threading
import uuid
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

TTS_URL = "http://localhost:5000/tts"
VIDEO_STORAGE = {}  # Maps video_id to file path or status


def download_tts_audio(narration, index):
    response = requests.post(TTS_URL, json={"text": narration})
    if response.status_code != 200:
        raise Exception(f"TTS failed for index {index}: {response.text}")
    temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    temp_audio.write(response.content)
    temp_audio.close()
    return temp_audio.name


def generate_text_image(text, index):
    clip = TextClip(text, fontsize=50, color='white', size=(1280, 720), bg_color='black', method='caption')
    clip = clip.set_duration(6)
    video_path = os.path.join(tempfile.gettempdir(), f"scene_{index}.mp4")
    clip.write_videofile(video_path, fps=24, logger=None)
    return video_path


def create_scene_video(video_id, scenes):
    try:
        clips = []
        for idx, scene in enumerate(scenes):
            image_path = generate_text_image(scene['scene_description'], idx)
            audio_path = download_tts_audio(scene['narration'], idx)

            video_clip = VideoFileClip(image_path)
            audio_clip = AudioFileClip(audio_path)
            final_clip = video_clip.set_audio(audio_clip)
            clips.append(final_clip)

        final_video = concatenate_videoclips(clips)
        output_path = os.path.join(tempfile.gettempdir(), f"{video_id}.mp4")
        final_video.write_videofile(output_path, fps=24, codec='libx264', audio_codec='aac')
        VIDEO_STORAGE[video_id] = {"status": "ready", "path": output_path}
    except Exception as e:
        VIDEO_STORAGE[video_id] = {"status": "error", "message": str(e)}


@app.route('/generate_video', methods=['POST'])
def start_video_generation():
    data = request.get_json()
    scenes = data.get("scenes", [])
    if not scenes:
        return jsonify({"error": "No scenes provided"}), 400

    video_id = str(uuid.uuid4())
    VIDEO_STORAGE[video_id] = {"status": "processing"}
    thread = threading.Thread(target=create_scene_video, args=(video_id, scenes))
    thread.start()
    return jsonify({"video_id": video_id})


@app.route('/video_status/<video_id>', methods=['GET'])
def check_status(video_id):
    status = VIDEO_STORAGE.get(video_id)
    if not status:
        return jsonify({"error": "Video ID not found"}), 404
    return jsonify(status)


@app.route('/download_video/<video_id>', methods=['GET'])
def download_video(video_id):
    data = VIDEO_STORAGE.get(video_id)
    if not data:
        return jsonify({"error": "Video not found"}), 404
    if data["status"] != "ready":
        return jsonify({"error": f"Video not ready, current status: {data['status']}"}), 400
    return send_file(data['path'], mimetype='video/mp4', as_attachment=True, download_name="ram_katha.mp4")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
