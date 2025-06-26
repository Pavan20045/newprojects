from moviepy.editor import *
import os
import requests
import tempfile
import json
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

TTS_URL = "http://localhost:5000/tts"  # Your local ElevenLabs TTS endpoint

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

def create_scene_video(scenes):
    clips = []
    for idx, scene in enumerate(scenes):
        image_path = generate_text_image(scene['scene_description'], idx)
        audio_path = download_tts_audio(scene['narration'], idx)

        video_clip = VideoFileClip(image_path)
        audio_clip = AudioFileClip(audio_path)
        final_clip = video_clip.set_audio(audio_clip)
        clips.append(final_clip)

    final_video = concatenate_videoclips(clips)
    output_path = os.path.join(tempfile.gettempdir(), "final_output.mp4")
    final_video.write_videofile(output_path, fps=24, codec='libx264', audio_codec='aac')
    return output_path

@app.route('/generate_video', methods=['POST'])
def generate_video_api():
    try:
        data = request.get_json()
        scenes = data.get("scenes", [])
        if not scenes:
            return jsonify({"error": "No scene data provided"}), 400

        output_video_path = create_scene_video(scenes)
        return send_file(output_video_path, mimetype='video/mp4', as_attachment=True, download_name="ram_katha.mp4")

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        scenes = data.get("scenes", [])
        if not scenes:
            return jsonify({"error": "Missing 'scenes' in webhook payload"}), 400

        output_video_path = create_scene_video(scenes)
        return send_file(output_video_path, mimetype='video/mp4', as_attachment=True, download_name="webhook_video.mp4")

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
