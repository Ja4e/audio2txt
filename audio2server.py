import socket
import sounddevice as sd
import numpy as np
import time
import curses
import json
import sys
import signal
import errno
import os

# Server configuration
SERVER_IP = 'localhost'
SERVER_PORT = 5905

# Audio configuration
SAMPLE_RATE = 48000
BLOCK_SIZE = 8192

final_outputs = []
running = True
save_path = ''

def signal_handler(sig, frame):
    global running
    running = False

def get_save_path():
    default_path = os.path.join(os.getcwd(), 'output.txt')
    path = input(f"Enter file path to save output (default: {default_path}): ")
    return path.strip() or default_path

def save_output_to_file(output_line):
    with open(save_path, 'a') as f:
        f.write(output_line + '\n')

def send_audio_to_server(stdscr):
    global running, save_path
    stdscr.clear()
    stdscr.nodelay(1)
    curses.curs_set(0)

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect_to_server():
        retry_delay = 2 
        while True:
            try:
                client_socket.connect((SERVER_IP, SERVER_PORT))
                stdscr.addstr(0, 0, "Connected to the server!")
                stdscr.refresh()
                return
            except ConnectionRefusedError:
                stdscr.addstr(0, 0, f"Could not connect to the server. Retrying in {retry_delay} seconds...")
                stdscr.refresh()
                time.sleep(retry_delay)
                retry_delay = max(1, retry_delay - 1)  # Decrease delay to a minimum of 1 second
            except Exception as e:
                stdscr.addstr(0, 0, f"Error connecting: {str(e)}")
                stdscr.refresh()
                time.sleep(3)

    connect_to_server()

    partial_output = ""
    response_buffer = ""
    audio_buffer = b''

    # Create a new window for displaying the outputs
    output_win = curses.newwin(curses.LINES - 4, curses.COLS, 4, 0)  # Height: total lines - 4, Width: total columns
    output_win.scrollok(True)

    def audio_callback(indata, frames, time, status):
        if status:
            print(status)
        try:
            client_socket.send(indata.tobytes())
        except Exception as e:
            if e.errno == errno.EPIPE:  # Check for broken pipe error
                stdscr.addstr(0, 0, "Broken pipe error. Attempting to reconnect...")
                stdscr.refresh()
                reconnect_to_server()  # Call reconnect function
            else:
                stdscr.addstr(0, 0, f"Error sending audio data: {str(e)}")
                stdscr.refresh()

    def reconnect_to_server():
        nonlocal client_socket
        client_socket.close()
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connect_to_server()

    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE, channels=1, dtype='int16', callback=audio_callback):
            stdscr.addstr(2, 0, "Recording... Press Ctrl+C to stop.")
            stdscr.refresh()
            while running:
                try:
                    data = client_socket.recv(4096)
                    if data:
                        response_buffer += data.decode('utf-8') 

                        while True:
                            try:
                                response_json, index = json.JSONDecoder().raw_decode(response_buffer)
                                response_buffer = response_buffer[index:].lstrip()
                                if 'text' in response_json and response_json['text']:
                                    final_outputs.append(response_json['text'])
                                    save_output_to_file(response_json['text'])
                                elif 'partial' in response_json:  # Check for partial output
                                    partial_output = response_json['partial']

                            except json.JSONDecodeError:
                                break

                    stdscr.addstr(4, 0, "Current Partial Output: ")
                    stdscr.addstr(4, 30, partial_output.ljust(70))

                    output_win.clear()
                    

                    for i, output in enumerate(final_outputs):
                        output_win.addstr(i, 0, output)
                    
                    output_win.refresh()
                    stdscr.refresh()

                except socket.error as e:
                    if e.errno == errno.EPIPE:
                        stdscr.addstr(0, 0, "Broken pipe error. Attempting to reconnect...")
                        stdscr.refresh()
                        reconnect_to_server()
                    else:
                        stdscr.addstr(0, 0, "Connection lost. Stopping updates...")
                        stdscr.refresh()
                        break
                except Exception as e:
                    stdscr.addstr(0, 0, f"Error receiving data: {str(e)}")
                    stdscr.refresh()
                time.sleep(0.1)
    except Exception as e:
        stdscr.addstr(2, 0, f"An unexpected error occurred: {str(e)}")
        stdscr.refresh()
    finally:
        client_socket.close()

if __name__ == '__main__':
    # Register the signal handler
    signal.signal(signal.SIGINT, signal_handler)

    # Ask the user for the save path or use default
    save_path = get_save_path()

    try:
        curses.wrapper(send_audio_to_server)
    finally:
        print(f"Final outputs saved to: {save_path}")
        print("Final Outputs:")
        for output in final_outputs:
            print(output)
