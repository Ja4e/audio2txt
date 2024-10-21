import socket
import sounddevice as sd
import numpy as np
import vosk

model = vosk.Model("vosk-model-en-us-0.42-gigaspeech")  # Vosk model
recognizer = vosk.KaldiRecognizer(model, 48000)

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(('localhost', 5905))
server_socket.listen(1)

print("Server listening on port 5905...")

def process_audio(conn):
    print("Client connected")
    audio_buffer = b''
    small_batch_size = 2048
    large_batch_size = 8192
    with sd.RawInputStream(samplerate=48000, blocksize=small_batch_size, channels=1, dtype='int16') as stream:
        while True:
            data = conn.recv(4096)
            if not data:
                print("No data received. Client may have disconnected.")
                break
            audio_data = np.frombuffer(data, dtype=np.int16)
            audio_buffer += audio_data.tobytes()
            while len(audio_buffer) >= small_batch_size:
                small_chunk = audio_buffer[:small_batch_size]
                audio_buffer = audio_buffer[small_batch_size:]
                if recognizer.AcceptWaveform(small_chunk):
                    result = recognizer.Result()
                    print(f"Recognized (small batch): {result}")
                    conn.send(result.encode('utf-8'))
                else:
                    conn.send(recognizer.PartialResult().encode('utf-8'))
            while len(audio_buffer) >= large_batch_size:
                large_chunk = audio_buffer[:large_batch_size]
                audio_buffer = audio_buffer[large_batch_size:]
                if recognizer.AcceptWaveform(large_chunk):
                    result = recognizer.Result()
                    print(f"Recognized (large batch): {result}") 
                    conn.send(result.encode('utf-8'))
                else:
                    conn.send(recognizer.PartialResult().encode('utf-8'))

    print("Client disconnected")
    conn.close()

with server_socket as s:
    conn, addr = server_socket.accept()  # Wait for a client to connect
    process_audio(conn)  # Process audio from the connected client
