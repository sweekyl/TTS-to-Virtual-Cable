import io
import sounddevice as sd
import numpy as np
from gtts import gTTS
from pydub import AudioSegment
import tkinter as tk
from tkinter import scrolledtext, Frame
import threading

vac_index = None
window = None
text_area = None
speak_button = None
listen_button = None
status_label = None

def get_vac_device_index(device_name_part="Line 1 (Virtual Audio Cable)"):
    try:
        devices = sd.query_devices()
        print("Поиск аудиоустройства вывода...")
        available_devices = []
        for i, device in enumerate(devices):
            if device['max_output_channels'] > 0:
                available_devices.append((i, device['name']))
                if device_name_part.lower() in device['name'].lower():
                    print(f"Найдено устройство: {i} - {device['name']}")
                    return i

        print(f"Ошибка: Устройство вывода, содержащее '{device_name_part}', не найдено.")
        print("Доступные устройства вывода:")
        if available_devices:
            for i, name in available_devices:
                print(f"  {i}: {name}")
        else:
            print("  Не найдено доступных устройств вывода.")
        return None
    except Exception as e:
        print(f"Ошибка при поиске аудиоустройств: {e}")
        return None

def generate_audio(text, lang='ru', status_label_ref=None):
    if not text:
        print("Нет текста для генерации аудио.")
        if status_label_ref:
            status_label_ref.config(text="Ошибка: Введите текст.")
        return None, None

    try:
        if status_label_ref:
            status_label_ref.config(text="Генерация речи...")
            status_label_ref.update_idletasks()

        tts = gTTS(text=text, lang=lang)
        mp3_fp = io.BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)

        if status_label_ref:
            status_label_ref.config(text="Обработка аудио...")
            status_label_ref.update_idletasks()

        audio = AudioSegment.from_file(mp3_fp, format="mp3")
        samples = np.array(audio.get_array_of_samples()).astype(np.float32)

        if audio.sample_width == 2: # 16-bit
             samples /= np.iinfo(np.int16).max
        elif audio.sample_width == 1: # 8-bit
             samples /= np.iinfo(np.int8).max

        if audio.channels > 1:
             samples = samples.reshape((-1, audio.channels))[:, 0]

        samplerate = audio.frame_rate
        print(f"Аудио сгенерировано (Частота: {samplerate} Гц).")
        return samples, samplerate

    except sd.PortAudioError as pae:
        error_message = f"Ошибка PortAudio: {pae}"
        print(error_message)
        if status_label_ref:
            status_label_ref.config(text=error_message)
        return None, None
    except FileNotFoundError as fnf_error:
        error_message = f"Ошибка: {fnf_error}"
        print(error_message)
        if "ffmpeg" in str(fnf_error) or "ffprobe" in str(fnf_error):
            error_message += " (Убедитесь, что ffmpeg установлен и в PATH)"
        if status_label_ref:
            status_label_ref.config(text=error_message)
        return None, None
    except Exception as e:
        error_message = f"Ошибка генерации аудио: {type(e).__name__}"
        print(f"Произошла ошибка при генерации/обработке аудио: {e}")
        if "timed out" in str(e).lower():
            error_message += " (Ошибка сети или gTTS?)"
        if status_label_ref:
            status_label_ref.config(text=error_message)
        return None, None


def play_audio(samples, samplerate, device_index=None, status_label_ref=None):
    if samples is None or samplerate is None:
        print("Нет аудиоданных для воспроизведения.")
        if status_label_ref:
           status_label_ref.config(text="Ошибка: Не удалось сгенерировать аудио.")
        return False

    try:
        device_info = "умолчанию" if device_index is None else f"устройстве {device_index}"
        print(f"Воспроизведение на устройстве {device_info} (Частота: {samplerate} Гц)...")
        if status_label_ref:
            status_label_ref.config(text=f"Воспроизведение ({device_info})...")
            status_label_ref.update_idletasks()

        sd.play(samples, samplerate=samplerate, device=device_index)
        sd.wait()

        print("Воспроизведение завершено.")
        if status_label_ref:
            status_label_ref.config(text="Готово.")
        return True

    except sd.PortAudioError as pae:
        error_message = f"Ошибка PortAudio при воспроизведении: {pae}"
        print(error_message)
        if status_label_ref:
            status_label_ref.config(text=error_message)
        return False
    except Exception as e:
        error_message = f"Ошибка воспроизведения: {e}"
        print(error_message)
        if status_label_ref:
            status_label_ref.config(text=error_message)
        return False

def set_buttons_state(state):
    if speak_button:
        speak_button.config(state=state)
    if listen_button:
        listen_button.config(state=state)

def run_tts_task(text, target_device_index):
    global status_label

    samples, samplerate = generate_audio(text, lang='ru', status_label_ref=status_label)

    play_audio(samples, samplerate, device_index=target_device_index, status_label_ref=status_label)

    if window:
        window.after(0, set_buttons_state, tk.NORMAL)

def on_speak_button_click():
    user_text = text_area.get("1.0", tk.END).strip()
    if not user_text:
        status_label.config(text="Введите текст для озвучивания.")
        return
    if vac_index is None:
        status_label.config(text="Ошибка: VAC устройство не найдено.")
        return

    set_buttons_state(tk.DISABLED)
    status_label.config(text="Запуск (VAC)...")
    tts_thread = threading.Thread(target=run_tts_task, args=(user_text, vac_index), daemon=True)
    tts_thread.start()

def on_listen_button_click():
    user_text = text_area.get("1.0", tk.END).strip()
    if not user_text:
        status_label.config(text="Введите текст для прослушивания.")
        return

    set_buttons_state(tk.DISABLED)
    status_label.config(text="Запуск (Прослушать)...")
    listen_thread = threading.Thread(target=run_tts_task, args=(user_text, None), daemon=True)
    listen_thread.start()


if __name__ == "__main__":
    VIRTUAL_CABLE_NAME_PART = "Line 1 (Virtual Audio Cable)"

    vac_index = get_vac_device_index(VIRTUAL_CABLE_NAME_PART)

    window = tk.Tk()
    window.title("Текст в Речь -> VAC / Динамики")
    window.geometry("450x350")

    instruction_label = tk.Label(window, text="Введите текст для озвучивания:")
    instruction_label.pack(pady=(10, 0))

    text_area = scrolledtext.ScrolledText(window, wrap=tk.WORD, width=50, height=12, relief=tk.SUNKEN, borderwidth=1)
    text_area.pack(pady=5, padx=10)

    button_frame = Frame(window)
    button_frame.pack(pady=10)

    listen_button = tk.Button(button_frame, text="Прослушать", command=on_listen_button_click, width=15, height=2)
    listen_button.pack(side=tk.LEFT, padx=5)

    speak_button = tk.Button(button_frame, text="Озвучить (VAC)", command=on_speak_button_click, width=15, height=2)
    speak_button.pack(side=tk.LEFT, padx=5)

    if vac_index is None:
        speak_button.config(state=tk.DISABLED, text="Озвучить (Нет VAC)")
        initial_status = "VAC не найден. Доступно только прослушивание."
    else:
       initial_status = f"Готово (VAC: {vac_index})."

    status_label = tk.Label(window, text=initial_status, relief=tk.SUNKEN, anchor=tk.W)
    status_label.pack(fill=tk.X, padx=10, pady=(0, 5), ipady=2)

    window.mainloop()
