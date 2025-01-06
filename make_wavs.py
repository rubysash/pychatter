import numpy as np

def generate_notification_sounds():
    """
    Generate and save two different notification sounds:
    1. A soft click for sent messages
    2. A gentle chime for received messages
    Both sounds remain gentle and non-intrusive
    """
    # Parameters for the sounds
    sample_rate = 44100
    duration = 0.1  # 100ms total duration
    t = np.linspace(0, duration, int(sample_rate * duration), False)

    # Generate sent sound (soft click)
    click_duration = 0.02  # 20ms
    click_samples = int(sample_rate * click_duration)
    fade_in = np.linspace(0, 1, click_samples)
    fade_out = np.exp(-t[:click_samples] * 200)
    click = fade_in * fade_out * np.sin(2 * np.pi * 800 * t[:click_samples])
   
    sent_sound = np.zeros(int(sample_rate * duration))
    sent_sound[:click_samples] = click * 0.75

    # Generate received sound (gentle chime)
    chime_freq1 = 1000  # Higher frequency for chime
    chime_freq2 = 1700  # Second frequency for harmonics
    fade_envelope = np.exp(-t * 40)  # Slower fade out for chime
    
    chime = (np.sin(2 * np.pi * chime_freq1 * t) * 0.6 +  # Main tone
             np.sin(2 * np.pi * chime_freq2 * t) * 0.4)   # Harmonic
    received_sound = chime * fade_envelope * 0.5  # Gentle volume

    # Convert to 16-bit integers
    sent_sound = (sent_sound * 32767).astype(np.int16)
    received_sound = (received_sound * 32767).astype(np.int16)

    # Save as WAV files
    import wave
    
    # Save sent sound
    with wave.open('sent.wav', 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(sent_sound.tobytes())
        
    # Save received sound
    with wave.open('received.wav', 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(received_sound.tobytes())

def generate_notification_sounds4():
    """
    Generate and save two different notification sounds:
    1. A soft click for sent messages
    2. A reversed soft click for received messages
    Both sounds are very gentle and non-intrusive
    """
    # Parameters for the sounds
    sample_rate = 44100
    duration = 0.05  # 50ms total duration
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    # Generate sent sound (soft click)
    click_duration = 0.02  # 20ms
    click_samples = int(sample_rate * click_duration)
    fade_in = np.linspace(0, 1, click_samples)
    fade_out = np.exp(-t[:click_samples] * 200)
    click = fade_in * fade_out * np.sin(2 * np.pi * 800 * t[:click_samples])
   
    sent_sound = np.zeros(int(sample_rate * duration))
    sent_sound[:click_samples] = click * 0.75  # Increased amplitude to 75%
    
    # Generate received sound (reversed soft click with slight modification)
    received_sound = np.zeros(int(sample_rate * duration))
    reversed_click = np.flip(click) * 0.75  # Increased amplitude to 75%
    received_sound[-click_samples:] = reversed_click  # Put it at the end of the duration
    
    # Convert to 16-bit integers
    sent_sound = (sent_sound * 32767).astype(np.int16)
    received_sound = (received_sound * 32767).astype(np.int16)
    
    # Save as WAV files
    import wave
    
    # Save sent sound
    with wave.open('sent.wav', 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(sent_sound.tobytes())
        
    # Save received sound
    with wave.open('received.wav', 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(received_sound.tobytes())

def generate_notification_sounds3():
    """
    Generate and save two different notification sounds:
    1. A soft click for sent messages
    2. A reversed soft click for received messages
    Both sounds are very gentle and non-intrusive
    """
    # Parameters for the sounds
    sample_rate = 44100
    duration = 0.05  # 50ms total duration
    t = np.linspace(0, duration, int(sample_rate * duration), False)

    # Generate sent sound (soft click)
    click_duration = 0.02  # 20ms
    click_samples = int(sample_rate * click_duration)
    fade_in = np.linspace(0, 1, click_samples)
    fade_out = np.exp(-t[:click_samples] * 200)
    click = fade_in * fade_out * np.sin(2 * np.pi * 800 * t[:click_samples])
    
    sent_sound = np.zeros(int(sample_rate * duration))
    sent_sound[:click_samples] = click * 0.25  # Reduce amplitude to 25%

    # Generate received sound (reversed soft click with slight modification)
    received_sound = np.zeros(int(sample_rate * duration))
    reversed_click = np.flip(click) * 0.25  # Reverse the click and keep same amplitude
    received_sound[-click_samples:] = reversed_click  # Put it at the end of the duration

    # Convert to 16-bit integers
    sent_sound = (sent_sound * 32767).astype(np.int16)
    received_sound = (received_sound * 32767).astype(np.int16)

    # Save as WAV files
    import wave

    # Save sent sound
    with wave.open('sent.wav', 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(sent_sound.tobytes())

    # Save received sound
    with wave.open('received.wav', 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(received_sound.tobytes())

def generate_notification_sounds2():
    """
    Generate and save two different notification sounds:
    1. A soft click for sent messages
    2. A gentle ding for received messages
    """
    # Parameters for the sounds
    sample_rate = 44100
    duration = 0.1  # 100ms
    t = np.linspace(0, duration, int(sample_rate * duration), False)

    # Generate sent sound (soft click)
    sent_sound = np.zeros(int(sample_rate * duration))
    click_duration = 0.02  # 20ms
    click_samples = int(sample_rate * click_duration)
    click = np.exp(-t[:click_samples] * 200) * np.sin(2 * np.pi * 1000 * t[:click_samples])
    sent_sound[:click_samples] = click * 0.3  # Reduce amplitude to 30%

    # Generate received sound (gentle ding)
    received_freq = 1000  # 1kHz
    fade = np.exp(-t * 20)  # Exponential decay
    ding = np.sin(2 * np.pi * received_freq * t) * fade
    received_sound = ding * 0.3  # Reduce amplitude to 30%

    # Convert to 16-bit integers
    sent_sound = (sent_sound * 32767).astype(np.int16)
    received_sound = (received_sound * 32767).astype(np.int16)

    # Save as WAV files
    import wave

    # Save sent sound
    with wave.open('sent.wav', 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(sent_sound.tobytes())

    # Save received sound
    with wave.open('received.wav', 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(received_sound.tobytes())

generate_notification_sounds()
