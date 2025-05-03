import io
import sounddevice as sd
import numpy as np
from gtts import gTTS
from pydub import AudioSegment
import tkinter as tk
from tkinter import scrolledtext
import threading

def get_vac_device_index(device_name_part="Line 1 (Virtual Audio Cable)"): # <--- кабель
    try:
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            if device['max_output_channels'] > 0 and \
               device_name_part.lower() in device['name'].lower():
                print(f"Найдено устройство: {i} - {device['name']}")
                return i
        print(f"Ошибка: Устройство вывода, содержащее '{device_name_part}', не найдено.")
        print("Доступные устройства вывода:")
        for i, device in enumerate(devices):
            if device['max_output_channels'] > 0:
                 print(f"  {i}: {device['name']}")
        return None
    except Exception as e:
        print(f"Ошибка при поиске аудиоустройств: {e}")
        return None

def speak_text_to_vac(text, lang='ru', device_index=None, status_label=None):
    if device_index is None:
        print("Не указано устройство вывода.")
        if status_label:
            status_label.config(text="Ошибка: Устройство вывода не найдено.")
        return

    if not text:
        print("Нет текста для озвучивания.")
        if status_label:
            status_label.config(text="Введите текст для озвучивания.")
        return

    try:
        if status_label:
            status_label.config(text="Генерация речи...")
            status_label.update_idletasks()

        tts = gTTS(text=text, lang=lang)
        mp3_fp = io.BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)

        if status_label:
            status_label.config(text="Обработка аудио...")
            status_label.update_idletasks()

        audio = AudioSegment.from_file(mp3_fp, format="mp3")
        samples = np.array(audio.get_array_of_samples()).astype(np.float32)
        samples /= np.iinfo(audio.array_type).max

        samplerate = audio.frame_rate

        print(f"Воспроизведение на устройстве {device_index} (Частота: {samplerate} Гц)...")
        if status_label:
            status_label.config(text="Воспроизведение...")
            status_label.update_idletasks()

        sd.play(samples, samplerate=samplerate, device=device_index)
        sd.wait()

        print("Воспроизведение завершено.")
        if status_label:
            status_label.config(text="Готово.")

    except sd.PortAudioError as pae:
        print(f"Ошибка PortAudio: {pae}")
        if status_label:
            status_label.config(text=f"Ошибка аудио: {pae}")
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        if status_label:
            error_message = f"Ошибка: {type(e).__name__}"
            if "No such file or directory: 'ffmpeg'" in str(e) or \
               "No such file or directory: 'ffprobe'" in str(e):
                error_message += " (Возможно, не установлен ffmpeg?)"
            elif "timed out" in str(e).lower():
                 error_message += " (Ошибка сети или gTTS?)"
            status_label.config(text=error_message)

def on_speak_button_click():
    user_text = text_area.get("1.0", tk.END).strip()
    speak_button.config(state=tk.DISABLED)
    status_label.config(text="Запуск...")
    tts_thread = threading.Thread(target=run_tts_in_thread, args=(user_text,), daemon=True)
    tts_thread.start()

def run_tts_in_thread(text):
    speak_text_to_vac(text, lang='ru', device_index=vac_index, status_label=status_label)
    window.after(0, lambda: speak_button.config(state=tk.NORMAL))

if __name__ == "__main__":
    # имя кабеля для поиска
    vac_index = get_vac_device_index("Line 1 (Virtual Audio Cable)") # <--- ИЗМЕНЕНО ЗДЕСЬ

    if vac_index is None:
        print("\nНе удалось найти виртуальный аудиокабель. Запуск GUI отменен.")
    else:
        window = tk.Tk()
        window.title("Текст в Речь -> VAC")
        window.geometry("400x300")

        instruction_label = tk.Label(window, text="Введите текст для озвучивания:")
        instruction_label.pack(pady=(10, 0))

        text_area = scrolledtext.ScrolledText(window, wrap=tk.WORD, width=45, height=10, relief=tk.SUNKEN, borderwidth=1)
        text_area.pack(pady=5, padx=10)

        speak_button = tk.Button(window, text="Озвучить", command=on_speak_button_click, width=15, height=2)
        speak_button.pack(pady=10)

        status_label = tk.Label(window, text="Готово к работе.", relief=tk.SUNKEN, anchor=tk.W)
        status_label.pack(fill=tk.X, padx=10, pady=(0, 5), ipady=2)

        window.mainloop()
