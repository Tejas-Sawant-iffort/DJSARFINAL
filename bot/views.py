import os
import requests
import openai
import speech_recognition as sr
from dotenv import load_dotenv
from pydub import AudioSegment
from pydub.playback import play as play_audio
from io import BytesIO
from django.shortcuts import render,redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import base64
import json
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError

# Load environment variables from .env file (API keys)
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Set Sarvam STT, TTS, and translation API URLs
SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"
SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
SARVAM_SPEAKER = "pavithra"  # Set your desired TTS speaker here

def voice_bot_view(request):
    return render(request, "voice_bot.html")

def capture_audio():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    print("Listening...")
    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)

    audio_file_path = "voicebot/static/audio/captured_audio.wav"
    with open(audio_file_path, "wb") as f:
        f.write(audio.get_wav_data())
    
    print("Audio captured.")
    return audio_file_path

def sarvam_speech_to_text(audio_file_path, language_code):
    files = {"file": (audio_file_path, open(audio_file_path, "rb"), "audio/wav")}
    data = {"language_code": language_code, "model": "saarika:v1"}
    headers = {"API-Subscription-Key": SARVAM_API_KEY}

    response = requests.post(SARVAM_STT_URL, files=files, data=data, headers=headers)
    print("API Response Status:", response.status_code)
    print("API Response Text:", response.text)  # Print detailed response from the API
    return response.json()


def sarvam_text_to_speech(text, language_code):
    payload = {
        "inputs": [text],
        "target_language_code": language_code,
        "speaker": SARVAM_SPEAKER,
        "pitch": 0,
        "pace": 1.2,
        "loudness": 1.5,
        "speech_sample_rate": 8000,
        "enable_preprocessing": True,
        "model": "bulbul:v1"
    }
    headers = {"Content-Type": "application/json", "API-Subscription-Key": SARVAM_API_KEY}

    response = requests.post(SARVAM_TTS_URL, json=payload, headers=headers)
    if response.status_code == 200:
        audio_base64 = response.json()["audios"][0]
        audio_data = base64.b64decode(audio_base64)
        audio_file_path = default_storage.save('audio/response.wav', ContentFile(audio_data))
        return default_storage.url(audio_file_path)
    return None



 

import time
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def voice_bot(request):
    transcription = ""
    response_text = ""
    audio_url = ""

    latencies = {
        "receive_audio": 0,
        "save_audio": 0,
        "transcription": 0,
        "openai_response": 0,
        "text_to_speech": 0
    }

    if request.method == 'POST':
        # Measure audio file reception time
        start_time = time.time()
        audio_file = request.FILES.get('audio')
        latencies["receive_audio"] = time.time() - start_time
        
        audio_file_path = 'voicebot/static/audio/captured_audio.wav'
        
        if audio_file:
            print("Audio file received.")
            start_time = time.time()
            with open(audio_file_path, 'wb+') as destination:
                for chunk in audio_file.chunks():
                    destination.write(chunk)
            latencies["save_audio"] = time.time() - start_time
            print("Audio file saved:", audio_file_path)
        else:
            print("No audio file received.")
            return JsonResponse({'error': 'No audio file uploaded'}, status=400)

        # Check language code in session
        language_code = request.session.get('language_code', 'en-IN')
        print("Language Code:", language_code)

        print("Preprocessed audio file saved:", audio_file_path)

        # Measure transcription time
        start_time = time.time()
        transcription_response = sarvam_speech_to_text(audio_file_path, language_code)
        latencies["transcription"] = time.time() - start_time
        print("Transcription response:", transcription_response)
        transcription = transcription_response.get("transcript", "")

        if transcription:
            # Measure OpenAI response time
            start_time = time.time()
            openai_response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are Tejas from a village, a friendly AI..."},
                    {"role": "user", "content": transcription}
                ]
            )
            latencies["openai_response"] = time.time() - start_time
            response_text = openai_response.choices[0].message["content"]
            print("OpenAI response:", response_text)

            # Measure TTS time
            start_time = time.time()
            audio_url = sarvam_text_to_speech(response_text, language_code)
            latencies["text_to_speech"] = time.time() - start_time
            print("Generated audio URL:", audio_url)
        else:
            print("Transcription failed.")
            response_text = "Your Audio Was not clear, Please try again"
            transcription = "Audio !"

    return JsonResponse({
        'transcription': transcription, 
        'response': response_text, 
        'audioUrl': audio_url,
        'latencies': latencies  # Pass the latencies to the response
    })


def home(request):
    return render(request, "home.html")

def choice(request):
    return render(request, "choice_language.html")

def select_languagecode(language_id):
    language_map = {
        '1': 'hi-IN',
        '2': 'mr-IN',
        '3': 'bn-IN',
        '4': 'od-IN',
        '5': 'pa-IN',
        '6': 'te-IN',
        '7': 'kn-IN',
        '8': 'ml-IN',
        '9': 'gu-IN',
        '10': 'ta-IN',
        '11': 'en-IN'

    }
    return language_map.get(str(language_id), 'en-IN')

def select_language(request):
    if request.method == 'POST':
        language_id = request.POST.get('language_id')
        request.session['language_code'] = select_languagecode(language_id)
        return redirect('voice')   
    return render(request, 'home.html')
