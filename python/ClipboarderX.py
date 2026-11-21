#!/usr/bin/env python3
import base64
import socket
import struct
import subprocess
import threading
import time
import sys

# ==========================================
# 設定（起動引数で上書き可能）
# ==========================================
DEFAULT_IP = "192.168.1.50"
DEFAULT_PORT = 50000
POLL_INTERVAL = 0.5  # クリップボード監視間隔（秒）
MAX_PAYLOAD_SIZE = 10 * 1024 * 1024  # 10MB


class ClipboardSyncClient:
    def __init__(self, server_ip: str, server_port: int):
        self.server_ip = server_ip
        self.server_port = server_port

        self.sock: socket.socket | None = None
        self.net_lock = threading.Lock()
        self.clip_lock = threading.Lock()
        self.is_connected = False
        self.running = True

        self.last_text = ""
        self.send_count = 0
        self.recv_count = 0

    def get_win_clipboard(self) -> str | None:
        """WindowsのクリップボードからUTF-8でテキストを取得"""
        cmd = [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Get-Clipboard -Raw",
        ]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=3,
            )
            if res.returncode == 0 and res.stdout is not None:
                return res.stdout
        except Exception as e:
            print(f"[Clipboard Read Error] {e}")
        return None

    def set_win_clipboard(self, text: str) -> bool:
        """Base64経由でWindowsのクリップボードへUTF-8テキストを確実に書き込む"""
        # UTF-8バイト列をBase64化し、PowerShell側でデコードしてSet-Clipboardに渡す
        b64_text = base64.b64encode(text.encode("utf-8")).decode("ascii")
        ps_script = (
            f"$bytes = [System.Convert]::FromBase64String('{b64_text}');"
            "$txt = [System.Text.Encoding]::UTF8.GetString($bytes);"
            "Set-Clipboard -Value $txt"
        )
        try:
            res = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=3,
            )
            if res.returncode != 0:
                print(f"[Clipboard Write Error] {res.stderr.strip()}")
                return False
            return True
        except Exception as e:
            print(f"[Clipboard Write Exception] {e}")
            return False

    def toggle_obfuscation(self, data: bytearray) -> None:
        """難読化用（C#版と同じくコメントアウト中）"""
        for i in range(len(data)):
            data[i] ^= 0xFF

    def send_text(self, text: str) -> None:
        """4バイト長プレフィックス(Little Endian) + UTF-8ペイロードを送信"""
        with self.net_lock:
            if not self.is_connected or self.sock is None:
                return
            try:
                payload = bytearray(text.encode("utf-8"))
                # self.toggle_obfuscation(payload)

                length_prefix = struct.pack("<i", len(payload))
                self.sock.sendall(length_prefix + payload)
                self.send_count += 1
                print(f"[Sent #{self.send_count}] {len(payload)} bytes")
            except Exception as e:
                print(f"[Send Error] {e}")
                self.close_connection()

    def read_exact(self, num_bytes: int) -> bytes | None:
        """指定バイト数を確実に読み込む"""
        buf = bytearray()
        while len(buf) < num_bytes:
            if self.sock is None:
                return None
            chunk = self.sock.recv(num_bytes - len(buf))
            if not chunk:
                return None
            buf.extend(chunk)
        return bytes(buf)

    def receive_loop(self) -> None:
        """サーバーからのデータ受信ループ"""
        try:
            while self.is_connected and self.running:
                length_bytes = self.read_exact(4)
                if not length_bytes:
                    break

                length = struct.unpack("<i", length_bytes)[0]
                if length <= 0 or length > MAX_PAYLOAD_SIZE:
                    print(f"[Recv Error] Invalid payload length: {length}")
                    break

                payload_bytes = self.read_exact(length)
                if not payload_bytes:
                    break

                payload = bytearray(payload_bytes)
                # self.toggle_obfuscation(payload)
                received_text = payload.decode("utf-8", errors="replace")

                with self.clip_lock:
                    if self.set_win_clipboard(received_text):
                        # 書き込み直後に実際にOSにセットされた値を再取得して同期する
                        actual_text = self.get_win_clipboard()
                        self.last_text = actual_text if actual_text is not None else received_text
                        self.recv_count += 1
                        print(f"[Received #{self.recv_count}] {length} bytes")
        except Exception as e:
            if self.running:
                print(f"[Receive Loop Error] {e}")
        finally:
            self.close_connection()

    def connection_loop(self) -> None:
        """TCP接続・自動再接続ループ"""
        while self.running:
            if not self.is_connected:
                try:
                    print(f"[Status] Connecting to {self.server_ip}:{self.server_port}...")
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(5.0)
                    s.connect((self.server_ip, self.server_port))
                    s.settimeout(None)

                    with self.net_lock:
                        self.sock = s
                        self.is_connected = True

                    print("[Status] Connected!")
                    self.receive_loop()
                except Exception:
                    self.close_connection()
                    print("[Status] Disconnected (Retrying in 3s...)")
                    time.sleep(3)
            else:
                time.sleep(1)

    def clipboard_monitor_loop(self) -> None:
        """クリップボード監視ループ"""
        initial = self.get_win_clipboard()
        if initial is not None:
            self.last_text = initial

        while self.running:
            time.sleep(POLL_INTERVAL)
            if not self.is_connected:
                continue

            with self.clip_lock:
                current_text = self.get_win_clipboard()
                if current_text is None:
                    continue

                if current_text == self.last_text:
                    continue

                self.last_text = current_text
                if not current_text:
                    continue

                self.send_text(current_text)

    def close_connection(self) -> None:
        with self.net_lock:
            self.is_connected = False
            if self.sock is not None:
                try:
                    self.sock.close()
                except Exception:
                    pass
                self.sock = None

    def start(self) -> None:
        conn_thread = threading.Thread(target=self.connection_loop, daemon=True)
        clip_thread = threading.Thread(target=self.clipboard_monitor_loop, daemon=True)

        conn_thread.start()
        clip_thread.start()

        try:
            while self.running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n[Status] Shutting down...")
            self.running = False
            self.close_connection()


if __name__ == "__main__":
    ip = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_IP
    port = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PORT

    client = ClipboardSyncClient(ip, port)
    client.start()