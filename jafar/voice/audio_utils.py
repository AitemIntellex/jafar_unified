import pyaudio
import numpy as np

def calibrate_noise_level(mic_stream, frame_length, sample_rate, duration=2):
    """
    Calibrates the noise level of the environment using an existing audio stream.
    """
    print("Калибровка уровня шума... Пожалуйста, сохраняйте тишину.")
    frames = []
    num_reads = int((sample_rate / frame_length) * duration)

    for _ in range(num_reads):
        try:
            data = mic_stream.read(frame_length, exception_on_overflow=False)
            frames.append(data)
        except IOError:
            pass

    if not frames:
        print("Не удалось получить аудиоданные для калибровки.")
        return 500

    audio_data = np.frombuffer(b''.join(frames), dtype=np.int16)
    
    if audio_data.size == 0:
        print("Аудиоданные пусты после калибровки.")
        return 500

    noise_level = np.sqrt(np.mean(audio_data.astype(float)**2))
    # Увеличиваем множитель и добавляем минимальный порог для надежности
    silence_threshold = max(noise_level * 2.5, 50) 
    
    return silence_threshold
