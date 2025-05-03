import tkinter as tk
import gtts
import pydub
import sounddevice as sd
import soundfile as sf
import tempfile
import os
import threading
import queue
import time

# Укажи здесь ИНДЕКС или ИМЯ входа твоего виртуального кабеля
VIRTUAL_CABLE_DEVICE = None # <--- ЗАМЕНИ None НА НУЖНОЕ ЗНАЧЕНИЕ!

audio_queue = queue.Queue()

def generate_and_queue_speech():
    text = text_entry.get("1.0", tk.END).strip()
    if not text:
        if window.winfo_exists() and speak_button['state'] == tk.DISABLED:
             window.after(10, lambda: speak_button.config(state=tk.NORMAL))
        return

    speak_button.config(state=tk.DISABLED)
    filepath_mp3 = None

    try:
        tts = gtts.gTTS(text=text, lang='ru')
        temp_mp3_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3', dir=None)
        filepath_mp3 = temp_mp3_file.name
        temp_mp3_file.close()
        tts.save(filepath_mp3)
        audio_queue.put(filepath_mp3)
    except gtts.tts.gTTSError as e_gtts:
        print(f"Ошибка gTTS: {e_gtts}")
        if filepath_mp3 and os.path.exists(filepath_mp3): os.remove(filepath_mp3)
    except Exception as e_save:
        print(f"Ошибка при генерации/сохранении: {e_save}")
        if filepath_mp3 and os.path.exists(filepath_mp3): os.remove(filepath_mp3)
    finally:
        if window.winfo_exists():
            window.after(10, lambda: speak_button.config(state=tk.NORMAL))

def audio_playback_thread():
    while True:
        filepath_mp3 = None
        filepath_wav = None
        stream1_success = False
        stream2_success = False
        try:
            filepath_mp3 = audio_queue.get()
            if filepath_mp3 is None:
                break

            if VIRTUAL_CABLE_DEVICE is None:
                print("Ошибка: VIRTUAL_CABLE_DEVICE не указано.")
                if os.path.exists(filepath_mp3): os.remove(filepath_mp3)
                audio_queue.task_done()
                continue

            audio_segment = pydub.AudioSegment.from_mp3(filepath_mp3)
            temp_wav_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav', dir=None)
            filepath_wav = temp_wav_file.name
            temp_wav_file.close()
            audio_segment.export(filepath_wav, format="wav")

            data, samplerate = sf.read(filepath_wav, dtype='float32')

            try:
                sd.play(data, samplerate, device=VIRTUAL_CABLE_DEVICE, blocking=False)
                stream1_success = True
            except Exception as e_play1:
                print(f"Ошибка воспроизведения на {VIRTUAL_CABLE_DEVICE}: {e_play1}")

            try:
                sd.play(data, samplerate, device=None, blocking=False)
                stream2_success = True
            except Exception as e_play2:
                print(f"Ошибка воспроизведения на устройстве по умолчанию: {e_play2}")

            if stream1_success or stream2_success:
                sd.wait()

        except FileNotFoundError:
             print(f"Ошибка: Не найден файл {filepath_mp3} или {filepath_wav}")
        except pydub.exceptions.CouldntDecodeError as e_decode:
             print(f"Ошибка Pydub: Не удалось декодировать MP3 {filepath_mp3}. Проверьте ffmpeg. Ошибка: {e_decode}")
        except Exception as e_play:
            print(f"Ошибка обработки/воспроизведения: {e_play}")
        finally:
            if filepath_wav and os.path.exists(filepath_wav):
                try: os.remove(filepath_wav)
                except Exception as e: print(f"Не удалось удалить WAV {filepath_wav}: {e}")
            if filepath_mp3 and os.path.exists(filepath_mp3):
                 try: os.remove(filepath_mp3)
                 except Exception as e: print(f"Не удалось удалить MP3 {filepath_mp3}: {e}")
            try: audio_queue.task_done()
            except ValueError: pass

def start_generation_thread():
    if VIRTUAL_CABLE_DEVICE is None:
         print("Ошибка: VIRTUAL_CABLE_DEVICE не указано в коде.")
         return

    thread = threading.Thread(target=generate_and_queue_speech)
    thread.daemon = True
    thread.start()

playback_thread = threading.Thread(target=audio_playback_thread)
playback_thread.daemon = True
playback_thread.start()

window = tk.Tk()
window.title("TTS v  mikro")
window.geometry("400x300")

def on_closing():
    audio_queue.put(None)
    playback_thread.join(timeout=0.5)
    window.destroy()

window.protocol("WM_DELETE_WINDOW", on_closing)

text_entry = tk.Text(window, wrap=tk.WORD, height=10, width=45)
text_entry.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
text_entry.focus_set()

initial_button_state = tk.NORMAL if VIRTUAL_CABLE_DEVICE is not None else tk.DISABLED
speak_button = tk.Button(window, text="Озвучить", command=start_generation_thread, height=2, state=initial_button_state)
speak_button.pack(fill=tk.X, padx=10, pady=(0, 10))

window.mainloop()

print("Программа завершена.")