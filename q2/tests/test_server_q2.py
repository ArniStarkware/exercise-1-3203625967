import datetime as dt
import io
import multiprocessing
import pathlib
import signal
import socket
import struct
import subprocess
import sys
import threading
import time

import pytest

import server


_SERVER_ADDRESS = '127.0.0.1', 5000
_SERVER_PATH = pathlib.Path(__file__).absolute().parent.parent / 'server.py'

_HEADER_FORMAT = 'LLI'

_USER_1 = 1
_USER_2 = 2
_TIMESTAMP_1 = int(dt.datetime(2019, 10, 25, 15, 12, 5, 228000).timestamp())
_TIMESTAMP_2 = int(dt.datetime(2019, 10, 25, 15, 15, 2, 304000).timestamp())
_THOUGHT_1 = "I'm hungry"
_THOUGHT_2 = "I'm sleepy"


@pytest.fixture
def get_output():
    parent, child = multiprocessing.Pipe()
    process = multiprocessing.Process(target=_run_server, args=(child,))
    process.start()
    parent.recv()
    try:
        yield lambda: parent.recv()
    finally:
        process.terminate()
        process.join()


def test_connection(get_output):
    _upload_thought(_USER_1, _TIMESTAMP_1, _THOUGHT_1)
    output = get_output()
    assert output


def test_user_id(get_output):
    _upload_thought(_USER_1, _TIMESTAMP_1, _THOUGHT_1)
    output = get_output()
    assert f'user {_USER_1}' in output
    _upload_thought(_USER_2, _TIMESTAMP_1, _THOUGHT_1)
    output = get_output()
    assert f'user {_USER_2}' in output


def test_thought(get_output):
    _upload_thought(_USER_1, _TIMESTAMP_1, _THOUGHT_1)
    output = get_output()
    assert _THOUGHT_1 in output
    _upload_thought(_USER_2, _TIMESTAMP_1, _THOUGHT_2)
    output = get_output()
    assert _THOUGHT_2 in output


def test_timestamp(get_output):
    _upload_thought(_USER_1, _TIMESTAMP_1, _THOUGHT_1)
    output = get_output()
    assert _format_timestamp(_TIMESTAMP_1) in output
    _upload_thought(_USER_1, _TIMESTAMP_2, _THOUGHT_1)
    output = get_output()
    assert _format_timestamp(_TIMESTAMP_2) in output


def test_partial_data(get_output):
    message = _serialize_thought(_USER_1, _TIMESTAMP_1, _THOUGHT_1)
    with socket.socket() as connection:
        time.sleep(0.1) # Wait for server to start listening.
        connection.connect(_SERVER_ADDRESS)
        for c in message:
            connection.sendall(bytes([c]))
            time.sleep(0.01)
    output = get_output()
    assert f'user {_USER_1}' in output
    assert _format_timestamp(_TIMESTAMP_1) in output
    assert _THOUGHT_1 in output


def test_performance(get_output):
    started = time.time()
    _upload_thought(_USER_1, _TIMESTAMP_1, _THOUGHT_1)
    _upload_thought(_USER_2, _TIMESTAMP_2, _THOUGHT_2)
    output_1 = get_output()
    elapsed = time.time() - started
    assert 1 < elapsed < 2
    output_2 = get_output()
    elapsed = time.time() - started
    assert 1 < elapsed < 2
    assert (
        (_THOUGHT_1 in output_1 and _THOUGHT_2 in output_2)
        or (_THOUGHT_1 in output_2 and _THOUGHT_2 in output_1)
    )


def test_cli():
    host, port = _SERVER_ADDRESS
    process = subprocess.Popen(
        ['python', _SERVER_PATH, f'{host}:{port}'],
        stdout = subprocess.PIPE,
    )
    stdout = None
    def run_server():
        nonlocal stdout
        stdout, _ = process.communicate()
    thread = threading.Thread(target=run_server)
    thread.start()
    time.sleep(0.1)
    _upload_thought(_USER_1, _TIMESTAMP_1, _THOUGHT_1)
    _upload_thought(_USER_2, _TIMESTAMP_2, _THOUGHT_2)
    time.sleep(3)
    process.send_signal(signal.SIGINT)
    thread.join()
    stdout = stdout.decode()
    assert f'user {_USER_1}' in stdout
    assert f'user {_USER_2}' in stdout
    assert _format_timestamp(_TIMESTAMP_1) in stdout
    assert _format_timestamp(_TIMESTAMP_2) in stdout
    assert _THOUGHT_1 in stdout
    assert _THOUGHT_2 in stdout


def test_cli_error():
    host, port = _SERVER_ADDRESS
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(_SERVER_ADDRESS)
    server.listen()
    process = subprocess.Popen(
        ['python', _SERVER_PATH, f'{host}:{port}'],
        stdout = subprocess.PIPE,
    )
    stdout, _ = process.communicate()
    assert b'error' in stdout.lower()


def _run_server(pipe):
    pipe.send('read')
    class StandardOutput:
        def write(self, data):
            if not data.strip():
                return
            pipe.send(data)
    sys.stdout = StandardOutput()
    server.run_server(_SERVER_ADDRESS)


def _upload_thought(user_id, timestamp, thought):
    message = _serialize_thought(user_id, timestamp, thought)
    with socket.socket() as connection:
        time.sleep(0.1) # Wait for server to start listening.
        connection.settimeout(2)
        connection.connect(_SERVER_ADDRESS)
        connection.sendall(message)


def _serialize_thought(user_id, timestamp, thought):
    header = struct.pack(_HEADER_FORMAT, user_id, timestamp, len(thought))
    return header + thought.encode()


def _format_timestamp(timestamp):
    datetime = dt.datetime.fromtimestamp(timestamp)
    return f'[{datetime:%Y-%m-%d %H:%M:%S}]'
