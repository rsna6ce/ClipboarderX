using System;
using System.Drawing;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace ClipboarderX
{
    public partial class Form1 : Form
    {
        // Windows API (クリップボード監視用)
        [DllImport("user32.dll", SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool AddClipboardFormatListener(IntPtr hwnd);

        [DllImport("user32.dll", SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool RemoveClipboardFormatListener(IntPtr hwnd);

        private const int WM_CLIPBOARDUPDATE = 0x031D;

        // 通信・状態管理
        private string serverIp;
        private int serverPort;
        private TcpClient tcpClient;
        private NetworkStream netStream;
        private readonly object lockObj = new object();

        private string lastText = "";
        private int sendCount = 0;
        private int recvCount = 0;
        private bool isConnected = false;

        // Visual Studio デザイナー表示用のデフォルトコンストラクタ
        public Form1()
        {
            InitializeComponent();
        }

        // 実際の起動時に使うコンストラクタ
        public Form1(string ip, int port) : this()
        {
            this.serverIp = ip;
            this.serverPort = port;

            labelTarget.Text = string.Format("Target: {0}:{1}", serverIp, serverPort);
            labelStatus.Text = "Status: Waiting to connect...";
            labelStatus.ForeColor = Color.DarkOrange;
            labelSendCount.Text = "Sent: 0";
            labelRecvCount.Text = "Received: 0";
        }

        protected override void OnHandleCreated(EventArgs e)
        {
            base.OnHandleCreated(e);

            // デザイナー上で開いているときは通信処理を実行しない
            if (this.DesignMode) return;

            UpdateInitialClipboardState();
            AddClipboardFormatListener(this.Handle);

            Task.Run(() => ConnectionLoop());
        }

        protected override void OnFormClosing(FormClosingEventArgs e)
        {
            if (!this.DesignMode)
            {
                RemoveClipboardFormatListener(this.Handle);
                CloseConnection();
            }
            base.OnFormClosing(e);
        }

        private void UpdateInitialClipboardState()
        {
            try
            {
                if (Clipboard.ContainsText())
                    lastText = Clipboard.GetText();
                else
                    lastText = "";
            }
            catch { lastText = ""; }
        }

        protected override void WndProc(ref Message m)
        {
            if (m.Msg == WM_CLIPBOARDUPDATE)
            {
                OnClipboardChanged();
            }
            base.WndProc(ref m);
        }

        private void OnClipboardChanged()
        {
            try
            {
                string currentText = "";
                if (Clipboard.ContainsText())
                {
                    currentText = Clipboard.GetText();
                }

                // 状態が変わっていない、または受信直後の自己セットなら無視
                if (currentText == lastText) return;

                lastText = currentText;

                // （空）の場合は送信しない
                if (string.IsNullOrEmpty(currentText)) return;

                SendText(currentText);
            }
            catch
            {
                // 他アプリによるクリップボードロック時の一時エラーを無視
            }
        }

        // ペイロードの難読化・復元（XOR 0xFF による全ビット反転）
        private void ToggleObfuscation(byte[] data)
        {
            for (int i = 0; i < data.Length; i++)
            {
                data[i] ^= 0xFF;
            }
        }

        private void SendText(string text)
        {
            lock (lockObj)
            {
                if (!isConnected || netStream == null) return;
                try
                {
                    byte[] payload = Encoding.UTF8.GetBytes(text);
                    //ToggleObfuscation(payload); // 送信前にビット反転で難読化 (試作キャンセル)

                    byte[] lengthPrefix = BitConverter.GetBytes(payload.Length);

                    netStream.Write(lengthPrefix, 0, 4);
                    netStream.Write(payload, 0, payload.Length);
                    netStream.Flush();

                    sendCount++;
                    UpdateUI();
                }
                catch
                {
                    CloseConnection();
                }
            }
        }

        private void ConnectionLoop()
        {
            while (!this.IsDisposed)
            {
                if (!isConnected)
                {
                    try
                    {
                        UpdateStatus("Connecting...", Color.DarkOrange);
                        var client = new TcpClient();
                        client.Connect(serverIp, serverPort);

                        lock (lockObj)
                        {
                            tcpClient = client;
                            netStream = client.GetStream();
                            isConnected = true;
                        }
                        UpdateStatus("Connected", Color.Green);
                        ReceiveLoop();
                    }
                    catch
                    {
                        CloseConnection();
                        UpdateStatus("Disconnected (Retrying...)", Color.Red);
                        Thread.Sleep(3000);
                    }
                }
                else
                {
                    Thread.Sleep(1000);
                }
            }
        }

        private void ReceiveLoop()
        {
            byte[] lengthBuffer = new byte[4];
            try
            {
                while (isConnected && netStream != null)
                {
                    if (!ReadExact(netStream, lengthBuffer, 4)) break;
                    int length = BitConverter.ToInt32(lengthBuffer, 0);
                    if (length <= 0 || length > 10 * 1024 * 1024) break;

                    byte[] payload = new byte[length];
                    if (!ReadExact(netStream, payload, length)) break;

                    //ToggleObfuscation(payload); // 受信後にビット反転して元のUTF-8バイト列に戻す (試作キャンセル)
                    string receivedText = Encoding.UTF8.GetString(payload);

                    this.Invoke((Action)(() =>
                    {
                        try
                        {
                            // 先にlastTextを更新してからセットすることで無限ループ防止
                            lastText = receivedText;
                            Clipboard.SetText(receivedText);
                            recvCount++;
                            UpdateUI();
                        }
                        catch { }
                    }));
                }
            }
            catch { }
            finally
            {
                CloseConnection();
            }
        }

        private bool ReadExact(NetworkStream stream, byte[] buffer, int count)
        {
            int offset = 0;
            while (offset < count)
            {
                int read = stream.Read(buffer, offset, count - offset);
                if (read == 0) return false;
                offset += read;
            }
            return true;
        }

        private void CloseConnection()
        {
            lock (lockObj)
            {
                isConnected = false;
                try { if (netStream != null) netStream.Close(); } catch { }
                try { if (tcpClient != null) tcpClient.Close(); } catch { }
                netStream = null;
                tcpClient = null;
            }
        }

        private void UpdateStatus(string text, Color color)
        {
            if (this.IsDisposed || !this.IsHandleCreated) return;
            try
            {
                this.BeginInvoke((Action)(() =>
                {
                    labelStatus.Text = "Status: " + text;
                    labelStatus.ForeColor = color;
                }));
            }
            catch { }
        }

        private void UpdateUI()
        {
            if (this.IsDisposed || !this.IsHandleCreated) return;
            try
            {
                this.BeginInvoke((Action)(() =>
                {
                    labelSendCount.Text = "Sent: " + sendCount;
                    labelRecvCount.Text = "Received: " + recvCount;
                }));
            }
            catch { }
        }
    }
}