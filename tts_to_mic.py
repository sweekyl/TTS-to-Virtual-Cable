import io
import sounddevice as sd
import numpy as np
from gtts import gTTS
from pydub import AudioSegment
import tkinter as tk
from tkinter import scrolledtext, Frame, Checkbutton, BooleanVar, Label, Button, LEFT, X, W, SUNKEN, WORD, END, DISABLED, NORMAL
import threading

vac_index = None
window = None
text_area = None
speak_button = None
listen_button = None
status_label = None
always_on_top_var = None

def get_vac_device_index(device_name_part="Line 1 (Virtual Audio Cable)"):
    try:
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            if device['max_output_channels'] > 0:
                if device_name_part.lower() in device['name'].lower():
                    return i
        return None
    except Exception as e:
        return None

def generate_audio(text, lang='ru', status_label_ref=None):
    if not text:
        if status_label_ref:
            status_label_ref.config(text="Ошибка: Введите текст для озвучивания.")
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
            status_label_ref.config(text="Обработка аудио (декодирование)...")
            status_label_ref.update_idletasks()

        audio = AudioSegment.from_file(mp3_fp, format="mp3")
        samples = np.array(audio.get_array_of_samples()).astype(np.float32)

        if audio.sample_width == 2:
            samples /= np.iinfo(np.int16).max
        elif audio.sample_width == 1:
            samples = (samples - 128.0) / 128.0
        elif audio.sample_width == 4:
             samples /= np.iinfo(np.int32).max

        if audio.channels > 1:
            samples = samples.reshape((-1, audio.channels))[:, 0]

        samplerate = audio.frame_rate
        return samples, samplerate

    except sd.PortAudioError as pae:
        error_message = f"Ошибка PortAudio при генерации: {pae}"
        if status_label_ref:
            status_label_ref.config(text=error_message)
        return None, None
    except FileNotFoundError as fnf_error:
        error_message = f"Ошибка: {fnf_error}"
        if "ffmpeg" in str(fnf_error).lower() or "ffprobe" in str(fnf_error).lower():
            error_message = "Ошибка: ffmpeg/ffprobe не найден (нужен для pydub)."
        if status_label_ref:
            status_label_ref.config(text=error_message)
        return None, None
    except Exception as e:
        error_message = f"Ошибка генерации: {type(e).__name__}"
        if "timed out" in str(e).lower():
            error_message += " (Проверьте сеть / доступность gTTS)"
        if status_label_ref:
            status_label_ref.config(text=error_message)
        return None, None


def play_audio(samples, samplerate, device_index=None, status_label_ref=None):
    if samples is None or samplerate is None:
        if status_label_ref:
           status_label_ref.config(text="Ошибка: Нет аудиоданных для воспроизведения.")
        return False

    try:
        device_info = "умолчанию" if device_index is None else f"устройстве {device_index}"
        if status_label_ref:
            status_label_ref.config(text=f"Воспроизведение на {device_info}...")
            status_label_ref.update_idletasks()

        sd.play(samples, samplerate=samplerate, device=device_index)
        sd.wait()

        if status_label_ref:
            current_status = f"Готово (VAC: {vac_index if vac_index is not None else 'не найден'})."
            if window:
                window.after(0, lambda: status_label_ref.config(text=current_status))
            else:
                 status_label_ref.config(text=current_status)

        return True

    except sd.PortAudioError as pae:
        error_message = f"Ошибка PortAudio при воспроизведении: {pae}"
        if status_label_ref and window:
            window.after(0, lambda: status_label_ref.config(text=error_message))
        return False
    except Exception as e:
        error_message = f"Ошибка воспроизведения: {e}"
        if status_label_ref and window:
            window.after(0, lambda: status_label_ref.config(text=error_message))
        return False

def set_buttons_state(state):
    if listen_button:
        listen_button.config(state=state)
    if speak_button:
        if vac_index is not None or state == NORMAL:
             speak_button.config(state=state)
        else:
             speak_button.config(state=DISABLED)


def run_tts_task(text, target_device_index):
    global status_label, window

    samples, samplerate = generate_audio(text, lang='ru', status_label_ref=status_label)

    play_success = play_audio(samples, samplerate, device_index=target_device_index, status_label_ref=status_label)

    if window:
        window.after(0, set_buttons_state, NORMAL)


def on_speak_button_click():
    user_text = text_area.get("1.0", END).strip()
    if not user_text:
        status_label.config(text="Введите текст для озвучивания.")
        return
    if vac_index is None:
        status_label.config(text="Ошибка: VAC устройство не найдено для озвучивания.")
        speak_button.config(state=DISABLED)
        return

    set_buttons_state(DISABLED)
    status_label.config(text="Запуск задачи (озвучивание на VAC)...")
    tts_thread = threading.Thread(target=run_tts_task, args=(user_text, vac_index), daemon=True)
    tts_thread.start()

def on_listen_button_click():
    user_text = text_area.get("1.0", END).strip()
    if not user_text:
        status_label.config(text="Введите текст для прослушивания.")
        return

    set_buttons_state(DISABLED)
    status_label.config(text="Запуск задачи (прослушивание)...")
    listen_thread = threading.Thread(target=run_tts_task, args=(user_text, None), daemon=True)
    listen_thread.start()

def toggle_always_on_top():
    global window, always_on_top_var
    try:
        if window and always_on_top_var:
            is_on_top = always_on_top_var.get()
            window.attributes('-topmost', is_on_top)
    except tk.TclError:
        pass

if __name__ == "__main__":
    VIRTUAL_CABLE_NAME_PART = "Line 1 (Virtual Audio Cable)"

    vac_index = get_vac_device_index(VIRTUAL_CABLE_NAME_PART)

    window = tk.Tk()
    window.title("Текст в Речь -> VAC / Динамики")
    window.geometry("450x380")

    instruction_label = Label(window, text="Введите текст для озвучивания:")
    instruction_label.pack(pady=(10, 0))

    text_area = scrolledtext.ScrolledText(window, wrap=WORD, width=50, height=12, relief=SUNKEN, borderwidth=1)
    text_area.pack(pady=5, padx=10, fill=X, expand=True)

    button_frame = Frame(window)
    button_frame.pack(pady=5)

    listen_button = Button(button_frame, text="Прослушать", command=on_listen_button_click, width=15, height=2)
    listen_button.pack(side=LEFT, padx=5)

    speak_button = Button(button_frame, text="Озвучить (VAC)", command=on_speak_button_click, width=15, height=2)
    speak_button.pack(side=LEFT, padx=5)

    always_on_top_var = BooleanVar(value=False)
    on_top_checkbox = Checkbutton(
        window,
        text="Поверх всех окон",
        variable=always_on_top_var,
        command=toggle_always_on_top
    )
    on_top_checkbox.pack(pady=(5, 0))

    if vac_index is None:
        speak_button.config(state=DISABLED, text="Озвучить (Нет VAC)")
        initial_status = "VAC не найден. 'Озвучить' недоступно."
    else:
       initial_status = f"Готово. VAC найден на устройстве {vac_index}."

    status_label = Label(window, text=initial_status, relief=SUNKEN, anchor=W, padx=5)
    status_label.pack(fill=X, padx=10, pady=(5, 5), ipady=3)

    toggle_always_on_top()

    window.mainloop()
