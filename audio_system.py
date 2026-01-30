import wave
import pyaudio
import pygame
import time
import numpy as np
from io import BytesIO

class AudioSystem:
    def __init__(self):
        self.sample_rate = 44100
        self.channels = 1
        self.chunk = 1024
        
    def text_to_speech(self, text, language='en'):
        """Convert text to speech (simulated)"""
        # For simulation, create a simple beep sound
        return self.generate_beep_sound()
    
    def generate_beep_sound(self, frequency=440, duration=1.0):
        """Generate a simple beep sound"""
        samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, samples, False)
        tone = np.sin(frequency * t * 2 * np.pi)
        
        # Convert to 16-bit PCM
        audio = (tone * 32767).astype(np.int16)
        
        # Create WAV file in memory
        wav_buffer = BytesIO()
        with wave.open(wav_buffer, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio.tobytes())
        
        wav_buffer.seek(0)
        return wav_buffer
    
    def record_audio(self, duration=5):
        """Record audio from microphone"""
        try:
            p = pyaudio.PyAudio()
            stream = p.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk
            )
            
            frames = []
            for _ in range(0, int(self.sample_rate / self.chunk * duration)):
                data = stream.read(self.chunk)
                frames.append(data)
            
            stream.stop_stream()
            stream.close()
            p.terminate()
            
            # Save to WAV buffer
            wav_buffer = BytesIO()
            with wave.open(wav_buffer, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2)
                wf.setframerate(self.sample_rate)
                wf.writeframes(b''.join(frames))
            
            wav_buffer.seek(0)
            return wav_buffer
            
        except Exception as e:
            print(f"Audio recording failed: {e}")
            return None
    
    def play_audio(self, audio_bytes):
        """Play audio from bytes"""
        try:
            pygame.mixer.init(frequency=self.sample_rate)
            
            # Save to temp file
            temp_file = "temp_audio.wav"
            with open(temp_file, 'wb') as f:
                if isinstance(audio_bytes, BytesIO):
                    f.write(audio_bytes.getvalue())
                else:
                    f.write(audio_bytes)
            
            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()
            
            # Wait for playback
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            
            return True
        except Exception as e:
            print(f"Audio playback failed: {e}")
            return False
