#!/usr/bin/env python3
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
        self.lock = threading.Lock()
        self.is_connected = False
        self.running = True

        self.last_text = ""
        self.send_count = 0
        self.recv_count = 0

    def get_win_clipboard(self) -> str:
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
        except Exception:
            pass
        return ""

    def set_win_clipboard(self, text: str) -> bool:
        """WindowsのクリップボードへUTF-8でテキストを書き込み"""
        cmd = [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "[Console]::InputEncoding = [System.Text.Encoding]::UTF8; $input | Set-Clipboard",
        ]
        try:
            # パイプ経由で渡すとPowerShellの$inputが末尾に改行を1つ付与する仕様があるため、
            # 環境変数経由で渡すことで完全一致の文字列をセットする
            ps_script = (
                "$txt = [System.Environment]::GetEnvironmentVariable('WSL_CLIP_DATA', 'Process');"
                "if ($null -ne $txt) { Set-Clipboard -Value $txt }"
            )
            env = {"WSL_CLIP_DATA": text}
            res = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                env=env,
                capture_output=True,
                timeout=3,
            )
            return res.returncode == 0
        except Exception:
            return False

    def toggle_obfuscation(self, data: bytearray) -> None:
        """難読化用（C#版と同じくコメントアウト中）"""
        for i in range(len(data)):
            data[i] ^= 0xFF

    def send_text(self, text: str) -> None:
        """4バイト長プレフィックス(Little Endian) + UTF-8ペイロードを送信"""
        with self.lock:
            if not self.is_connected or self.sock is None:
                return
            try:
                payload = bytearray(text.encode("utf-8"))
                # self.toggle_obfuscation(payload)  # 試作キャンセル

                # C# BitConverter.GetBytes(int) と同じ4バイト・リトルエンディアン
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
                # self.toggle_obfuscation(payload)  # 試作キャンセル
                received_text = payload.decode("utf-8", errors="replace")

                # 無限ループ防止のため先にlast_textを更新
                self.last_text = received_text
                if self.set_win_clipboard(received_text):
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
                    s.settimeout(None)  # 接続後はブロッキングモードに戻す

                    with self.lock:
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
        self.last_text = self.get_win_clipboard()
        while self.running:
            time.sleep(POLL_INTERVAL)
            if not self.is_connected:
                continue

            current_text = self.get_win_clipboard()
            if current_text == self.last_text:
                continue

            self.last_text = current_text
            if not current_text:
                continue

            self.send_text(current_text)

    def close_connection(self) -> None:
        with self.lock:
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