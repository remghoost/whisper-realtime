# system and hardware
import os
import sys
import tempfile
import pyautogui
import threading
import time
import gc

import keyboard

from datetime import datetime

from tkinter import Tk, Text, END
from tkinter import *

# audio
import pyaudio
import wave

# whisper
import whisper

#-=-# Initialization #-=-#

pid = os.getpid()
print(pid)

# Variables for controlling recording
is_recording = False
recording_finished = False
typing = True
temp_saving = False
audio_engine_active = False
text = ""
gui_active = False
audio = pyaudio.PyAudio()

BAR_LENGTH = 20

# Get the current date and time
now = datetime.now()

# Set up the logging folder and filename scheme
log_folder = "logs"
if not os.path.exists(log_folder):
    os.makedirs(log_folder)
log_file_name = os.path.join(
    log_folder, f"log_{now.strftime('%Y-%m-%d_%H-%M-%S')}.txt")

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-#


# Initialize pyaudio. This thing can be tempremental, so I do it by itself.
def pyaudio_init():
    # Initializing pyaudio settings
    global CHUNK, FORMAT, CHANNELS, RATE, audio
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    audio = pyaudio.PyAudio()


# starting initial server
def activate_audio_engine():
    print("AUDIO ENGINE ACTIVE")
    pyaudio_init()
    global stream, frames
    print(CHANNELS)
    stream = audio.open(format=FORMAT, channels=CHANNELS,
                        rate=RATE, input=True,
                        frames_per_buffer=CHUNK)
    frames = []
    global audio_engine_active
    audio_engine_active = True
    return stream, frames

# Define a context manager to load and unload the model.
# This isn't working to shutdown whisper, but it's probably good to do it this way regardless.
# Instead, we just crash the program. Lmao. No really, go look at on_closing.


class WhisperModel:
    def __init__(self):
        self.model = None

    def __enter__(self):
        self.model = whisper.load_model("base")
        return self.model

    def __exit__(self, exc_type, exc_value, traceback):
        print("this section does nothing lul")
        self.model = None
        # del self.model.encoder
        # del self.model.decoder
        # del self.model


recording_event = threading.Event()

#-=-=-=-=-=-=-=-=-=-=#

#-= Handles the held key


def on_press(event):
    global is_recording
    is_recording = True
    recording_event.set()

#-= Handles the 'on_release" of the key


def on_release(event):
    print("F9 RELEASED")
    global recording_finished
    global is_recording
    is_recording = False
    recording_finished = True
    recording_event.clear()
    # print("is_recording is " + str(is_recording))
    # print("recording_finished is " + str(recording_finished))

#-=-=-=-=-=-=-=-=-=-=-=-#


def update_progress(progress):
    bar = '[' + '#' * int(progress * BAR_LENGTH) + '-' * \
        (BAR_LENGTH - int(progress * BAR_LENGTH)) + ']'
    sys.stdout.write('\r' + bar + ' ' + str(int(progress * 100)) + '%')
    sys.stdout.flush()


#-= Calling the main audio transcription function
def transcribe_audio(file_path):
    model = whisper.load_model("base")
    result = model.transcribe(file_path)
    del model

    if isinstance(result, dict) and 'text' in result:
        result = result['text']
    else:
        result = str(result)

    return result

#-= Audio Processing


def audio_processing():
    start_time = time.time()
    while is_recording and not recording_finished:
        elapsed_time = time.time() - start_time
        data = stream.read(CHUNK)
        frames.append(data)
        progress = elapsed_time
        update_progress(progress)

#-= Recording Processing


def finish_recording():
    global text

    sys.stdout.write('\r' + ' ' * (BAR_LENGTH + 5) + '\r')
    sys.stdout.flush()
    print("Recording Finished")

    # Terminate streams
    print('TERMINATING STREAMS')
    stream.stop_stream()
    stream.close()
    audio.terminate()
    audio_engine_active = False
    print('SAVING TEMP AUDIO')
    # Save the recorded audio as a temporary WAV file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        file_path = f.name
        wf = wave.open(file_path, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()

    # Transcribe the audio to the gui and log
    print('TRANSCRIPTION IN PROGRESS')
    text = transcribe_audio(file_path)

    # This is for the keyboard emulation to "type" the message
    if typing:
        pyautogui.typewrite(text)

    # Write output to textbox
    text_box.config(state="normal")
    text_box.insert(END, text)
    text_box.insert(END, "\n\n")
    text_box.config(state="disabled")

    # Log the transcribed text
    print('WRITING TO LOG FILE')
    with open(log_file_name, "a") as log_file:
        log_file.write(f"{text}\n")
    recording_finished = False

    # Handling the saving/deleting of the temp audio file
    # if temp_saving:
    #     text_short = text[:20]
    #     new_file_name = f"{now.strftime('%Y-%m-%d_%H-%M-%S')}_{text_short}.wav"
    #     audio_destination_path = os.path.join("audio", new_file_name)
    #     if not os.path.exists("audio"):
    #         os.makedirs("audio")
    #     shutil.copy(file_path, audio_destination_path)
    os.remove(file_path)

    activate_audio_engine()
    recording_event.clear


#-= Main audio recording/processing function
def record_audio(key_event=None):
    global is_recording, recording_finished, frames, audio_engine_active, gui_active, stream, text
    print("RECORD AUDIO FUNCTION ACTIVE")

    while True:
        # Activate engine
        if not audio_engine_active:
            activate_audio_engine()

        frames = []
        recording_event.wait()

        # Main Thread
        while recording_event.is_set():
            if not is_recording:
                break

            audio_thread = threading.Thread(target=audio_processing)
            audio_thread.start()

            while is_recording and not recording_finished:
                time.sleep(0.1)  # Give the main thread a chance to continue

            if recording_finished:
                finish_thread = threading.Thread(target=finish_recording)
                finish_thread.start()

                # Wait for the finish_recording thread to complete before continuing
                finish_thread.join()

            # Reset the recording flags for subsequent presses
            recording_finished = False
            is_recording = False
        else:
            print("guess it was nothing")
            pass


#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-#
# This is the kill function for the program.
# It needs to be fixed. Right now I literally just crash the program to close it.
# Before settling on this, my audio device would crash every 2-3 times I opened this script.
# Idk man. It works now though. But probably not the best way to do it.
def on_closing():
    print("HE'S DEAD JIM")
    audio.terminate()
    # recording_thread.join()

    # whisper_hooks = list(self.model._forward_pre_hooks.values()) + list(self.model._forward_hooks.values())
    # for hook in whisper_hooks:
    #     hook.remove()

    # # Fine, guess we gotta do it the hard way.
    # threads = threading.enumerate()
    # for thread in threads:
    #     print(thread.name)
    # for thread in threads:
    #     if thread.name == "Thread-6 (listen)":
    #         thread._stop()

    # DIE DIE DIE DIE DIE
    os.kill(os.getpid(), 9)
    root.destroy()
    sys.exit(0)
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-#


# Start a thread to record audio
print("BEFORE RECORDING THREAD")
recording_thread = threading.Thread(target=record_audio)
recording_thread.start()
print("AFTER RECORTDING THREAD")

#-=-=-=-=-=-=- USER INTERFACE -=-=-=-#
# Start the ui
root = Tk()
print("UI STUFF?")

# Create a label to display recording status
recording_label = Label(root, text="Not recording", fg="red")
recording_label.pack()

# Create the main textbox
text_box = Text(root, state="disabled")
text_box.pack(fill=BOTH, expand=YES, padx=10, pady=10)

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-#
# THIS MIGHT BE FUCKING MY CPU CYCLES
# Check recording status and change label depending on status. I wanna move this but idk if i can. It's ugly here.


def update_recording_status():
    if is_recording and not recording_finished:
        recording_label.config(text="Recording", fg="green")
    else:
        recording_label.config(text="Not recording", fg="red")
    root.after(100, update_recording_status)


update_recording_status()
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-#

# This is for checking whether or not the gui is active. Want to be able to edit the text in the window.
# No longer need it at the moment (since editing text in the window is buggy as heck [which i want to fix])
# Courtesy of BingGPT


def on_focus_in(event):
    global gui_active
    gui_active = True
    print("gui_active is " + str(gui_active))


def on_focus_out(event):
    global gui_active
    gui_active = False
    print("gui_active is " + str(gui_active))


root.bind('<FocusIn>', on_focus_in)
root.bind('<FocusOut>', on_focus_out)

# Create the menu bar
menu_bar = Menu(root)
root.config(menu=menu_bar)

# Create the "Settings" dropdown menu
settings_menu = Menu(menu_bar, tearoff=False)

#-=-# Variable Toggles #-=-#


def toggle_typing():
    global typing
    typing = not typing


def toggle_temp_saving():
    global temp_saving
    temp_saving = not temp_saving
    print("Temp audio saving is " + str(temp_saving))

#-=-# Menu buttons #-=-#


# Keyboard-like "typing" toggle
typing_toggle = BooleanVar(value=typing)
settings_menu.add_checkbutton(
    label="Toggle typing", variable=typing_toggle, command=toggle_typing)

# Saving wav files to directory toggle
temp_saving_toggle = BooleanVar(value=temp_saving)
settings_menu.add_checkbutton(label="Save temp audio files",
                              variable=temp_saving_toggle, command=toggle_temp_saving)

# Add the "Settings" dropdown menu to the menu bar
menu_bar.add_cascade(label="Settings", menu=settings_menu)

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-#
# On close catch
root.protocol("WM_DELETE_WINDOW", on_closing)
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-#

# cProfile.run(record_audio())


root.bind("<KeyPress>", on_press)
root.bind("<KeyRelease>", on_release)

keyboard.on_press_key("f9", on_press)
keyboard.on_release_key("f9", on_release)


# Run main gui loop
print("STARTING MAIN GUI")
root.mainloop()
