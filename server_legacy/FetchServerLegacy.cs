using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Net;
using System.Net.NetworkInformation;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Windows.Forms;

namespace FetchLegacy
{
    static class Program
    {
        // -------------------------------------------------------------
        // Win32 API Interop (Compatible with Windows XP, Vista, 7, 8, 10, 11)
        // -------------------------------------------------------------
        [DllImport("user32.dll")]
        static extern void mouse_event(uint dwFlags, int dx, int dy, int dwData, UIntPtr dwExtraInfo);

        [DllImport("user32.dll")]
        static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);

        [DllImport("user32.dll")]
        static extern bool LockWorkStation();

        [DllImport("powrprof.dll", SetLastError = true)]
        static extern bool SetSuspendState(bool hibernate, bool forceCritical, bool disableWakeEvent);

        [StructLayout(LayoutKind.Sequential)]
        struct MOUSEINPUT
        {
            public int dx;
            public int dy;
            public uint mouseData;
            public uint dwFlags;
            public uint time;
            public IntPtr dwExtraInfo;
        }

        [StructLayout(LayoutKind.Sequential)]
        struct KEYBDINPUT
        {
            public ushort wVk;
            public ushort wScan;
            public uint dwFlags;
            public uint time;
            public IntPtr dwExtraInfo;
        }

        [StructLayout(LayoutKind.Sequential)]
        struct HARDWAREINPUT
        {
            public uint uMsg;
            public ushort wParamL;
            public ushort wParamH;
        }

        [StructLayout(LayoutKind.Explicit)]
        struct INPUTUNION
        {
            [FieldOffset(0)] public MOUSEINPUT mi;
            [FieldOffset(0)] public KEYBDINPUT ki;
            [FieldOffset(0)] public HARDWAREINPUT hi;
        }

        [StructLayout(LayoutKind.Sequential)]
        struct INPUT
        {
            public uint type;
            public INPUTUNION u;
        }

        [DllImport("user32.dll", SetLastError = true)]
        static extern uint SendInput(uint nInputs, INPUT[] pInputs, int cbSize);

        const uint INPUT_KEYBOARD = 1;
        const uint KEYEVENTF_KEYUP = 0x0002;
        const uint KEYEVENTF_UNICODE = 0x0004;

        const uint MOUSEEVENTF_MOVE = 0x0001;
        const uint MOUSEEVENTF_LEFTDOWN = 0x0002;
        const uint MOUSEEVENTF_LEFTUP = 0x0004;
        const uint MOUSEEVENTF_RIGHTDOWN = 0x0008;
        const uint MOUSEEVENTF_RIGHTUP = 0x0010;
        const uint MOUSEEVENTF_MIDDLEDOWN = 0x0020;
        const uint MOUSEEVENTF_MIDDLEUP = 0x0040;
        const uint MOUSEEVENTF_WHEEL = 0x0800;

        const byte VK_CONTROL = 0x11;
        const byte VK_MENU = 0x12; // Alt
        const byte VK_LWIN = 0x5B;
        const byte VK_ESCAPE = 0x1B;
        const byte VK_RETURN = 0x0D;
        const byte VK_BACK = 0x08;
        const byte VK_TAB = 0x09;
        const byte VK_SPACE = 0x20;
        const byte VK_VOLUME_MUTE = 0xAD;
        const byte VK_VOLUME_DOWN = 0xAE;
        const byte VK_VOLUME_UP = 0xAF;
        const byte VK_MEDIA_NEXT_TRACK = 0xB0;
        const byte VK_MEDIA_PREV_TRACK = 0xB1;
        const byte VK_MEDIA_PLAY_PAUSE = 0xB3;

        static NotifyIcon trayIcon;
        static System.Threading.Timer sleepTimer;
        static readonly object sleepLock = new object();

        [STAThread]
        static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);

            // Setup Tray Icon
            trayIcon = new NotifyIcon();
            trayIcon.Text = "Fetch Server (Legacy Edition)";

            try
            {
                string iconPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "icon.ico");
                if (File.Exists(iconPath))
                    trayIcon.Icon = new Icon(iconPath);
                else
                    trayIcon.Icon = SystemIcons.Application;
            }
            catch
            {
                trayIcon.Icon = SystemIcons.Application;
            }

            ContextMenu menu = new ContextMenu();
            MenuItem titleItem = new MenuItem("🐕 Fetch Server (Legacy XP/Vista)");
            titleItem.Enabled = false;
            menu.MenuItems.Add(titleItem);

            string localIp = GetLocalIp();
            MenuItem ipItem = new MenuItem("IP: " + localIp + " (Port 8765)");
            ipItem.Enabled = false;
            menu.MenuItems.Add(ipItem);

            menu.MenuItems.Add("-");

            MenuItem portalItem = new MenuItem("Open Download Portal (Port 8080)", delegate(object s, EventArgs e) {
                try { Process.Start("http://" + localIp + ":8080"); } catch { }
            });
            menu.MenuItems.Add(portalItem);

            MenuItem exitItem = new MenuItem("Exit Fetch", delegate(object s, EventArgs e) {
                trayIcon.Visible = false;
                Application.Exit();
                Environment.Exit(0);
            });
            menu.MenuItems.Add(exitItem);

            trayIcon.ContextMenu = menu;
            trayIcon.Visible = true;

            trayIcon.ShowBalloonTip(3000, "Fetch Server (Legacy Edition)",
                "Running in background on " + localIp + ". Discoverable on Wi-Fi for XP & Vista.", ToolTipIcon.Info);

            // Start UDP Beacon Thread
            Thread beaconThread = new Thread(RunUdpBeacon);
            beaconThread.IsBackground = true;
            beaconThread.Start();

            // Start WebSocket Server Thread
            Thread wsThread = new Thread(RunWebSocketServer);
            wsThread.IsBackground = true;
            wsThread.Start();

            // Start Download Portal HTTP Thread
            Thread httpThread = new Thread(RunHttpPortal);
            httpThread.IsBackground = true;
            httpThread.Start();

            Application.Run();
        }

        // -------------------------------------------------------------
        // Network Discovery: UDP Beacon (Port 8766)
        // -------------------------------------------------------------
        static void RunUdpBeacon()
        {
            try
            {
                UdpClient udp = new UdpClient();
                udp.Client.SetSocketOption(SocketOptionLevel.Socket, SocketOptionName.ReuseAddress, true);
                udp.Client.Bind(new IPEndPoint(IPAddress.Any, 8766));

                string localIp = GetLocalIp();
                string hostName = Dns.GetHostName();
                string mac = GetMacAddress();

                while (true)
                {
                    try
                    {
                        IPEndPoint remote = new IPEndPoint(IPAddress.Any, 0);
                        byte[] req = udp.Receive(ref remote);
                        string msg = Encoding.UTF8.GetString(req).Trim();

                        if (msg == "DISCOVER_FETCH" || msg == "DISCOVER_PC_TOUCH")
                        {
                            string osName = Environment.OSVersion.Version.Major == 5 ? "Windows XP" :
                                           (Environment.OSVersion.Version.Major == 6 && Environment.OSVersion.Version.Minor == 0 ? "Windows Vista" : "Windows");
                            string offer = string.Format("FETCH_OFFER|{0}|{1}|8765|{2}|{3}", hostName, localIp, osName, mac);
                            byte[] offerBytes = Encoding.UTF8.GetBytes(offer);
                            udp.Send(offerBytes, offerBytes.Length, remote);
                        }
                    }
                    catch
                    {
                        Thread.Sleep(500);
                    }
                }
            }
            catch { }
        }

        // -------------------------------------------------------------
        // WebSocket RFC 6455 Server (Port 8765)
        // -------------------------------------------------------------
        static void RunWebSocketServer()
        {
            try
            {
                TcpListener listener = new TcpListener(IPAddress.Any, 8765);
                listener.Start();

                while (true)
                {
                    try
                    {
                        TcpClient client = listener.AcceptTcpClient();
                        Thread clientThread = new Thread(new ParameterizedThreadStart(HandleWebSocketClientObj));
                        clientThread.IsBackground = true;
                        clientThread.Start(client);
                    }
                    catch { }
                }
            }
            catch { }
        }

        static void HandleWebSocketClientObj(object obj)
        {
            TcpClient client = obj as TcpClient;
            if (client != null) HandleWebSocketClient(client);
        }

        static void HandleWebSocketClient(TcpClient client)
        {
            using (client)
            using (NetworkStream stream = client.GetStream())
            {
                try
                {
                    // Read HTTP Handshake
                    byte[] buffer = new byte[4096];
                    int bytesRead = stream.Read(buffer, 0, buffer.Length);
                    string reqStr = Encoding.UTF8.GetString(buffer, 0, bytesRead);

                    Match match = Regex.Match(reqStr, "Sec-WebSocket-Key: (.*)");
                    if (!match.Success) return;

                    string clientKey = match.Groups[1].Value.Trim();
                    string acceptKey = Convert.ToBase64String(
                        SHA1.Create().ComputeHash(
                            Encoding.UTF8.GetBytes(clientKey + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11")
                        )
                    );

                    string response = "HTTP/1.1 101 Switching Protocols\r\n" +
                                      "Upgrade: websocket\r\n" +
                                      "Connection: Upgrade\r\n" +
                                      "Sec-WebSocket-Accept: " + acceptKey + "\r\n\r\n";
                    byte[] respBytes = Encoding.UTF8.GetBytes(response);
                    stream.Write(respBytes, 0, respBytes.Length);
                    stream.Flush();

                    // Read WebSocket frames
                    while (true)
                    {
                        int b0 = stream.ReadByte();
                        if (b0 == -1) break;
                        int opcode = b0 & 0x0F;

                        if (opcode == 8) break; // Close frame

                        int b1 = stream.ReadByte();
                        if (b1 == -1) break;
                        bool masked = (b1 & 0x80) != 0;
                        int payloadLen = b1 & 0x7F;

                        if (payloadLen == 126)
                        {
                            int len1 = stream.ReadByte();
                            int len2 = stream.ReadByte();
                            payloadLen = (len1 << 8) | len2;
                        }
                        else if (payloadLen == 127)
                        {
                            // 8-byte length, skip top 4
                            for (int i = 0; i < 4; i++) stream.ReadByte();
                            payloadLen = (stream.ReadByte() << 24) | (stream.ReadByte() << 16) | (stream.ReadByte() << 8) | stream.ReadByte();
                        }

                        byte[] maskKey = new byte[4];
                        if (masked)
                        {
                            ReadExact(stream, maskKey, 0, 4);
                        }

                        byte[] payload = new byte[payloadLen];
                        ReadExact(stream, payload, 0, payloadLen);

                        if (masked)
                        {
                            for (int i = 0; i < payloadLen; i++)
                                payload[i] = (byte)(payload[i] ^ maskKey[i % 4]);
                        }

                        if (opcode == 1) // Text frame
                        {
                            string jsonMsg = Encoding.UTF8.GetString(payload);
                            ProcessMessage(jsonMsg);
                        }
                    }
                }
                catch { }
            }
        }

        static void ReadExact(NetworkStream s, byte[] buf, int offset, int count)
        {
            int total = 0;
            while (total < count)
            {
                int r = s.Read(buf, offset + total, count - total);
                if (r <= 0) break;
                total += r;
            }
        }

        // -------------------------------------------------------------
        // Protocol Message Processor
        // -------------------------------------------------------------
        static void ProcessMessage(string json)
        {
            try
            {
                string type = GetJsonValue(json, "type");
                if (string.IsNullOrEmpty(type)) return;

                switch (type)
                {
                    case "move":
                        int dx = (int)Math.Round(GetJsonDouble(json, "dx"));
                        int dy = (int)Math.Round(GetJsonDouble(json, "dy"));
                        mouse_event(MOUSEEVENTF_MOVE, dx, dy, 0, UIntPtr.Zero);
                        break;

                    case "click":
                        string btn = GetJsonValue(json, "btn");
                        if (btn == "right")
                        {
                            mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, UIntPtr.Zero);
                            Thread.Sleep(10);
                            mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, UIntPtr.Zero);
                        }
                        else if (btn == "middle")
                        {
                            mouse_event(MOUSEEVENTF_MIDDLEDOWN, 0, 0, 0, UIntPtr.Zero);
                            Thread.Sleep(10);
                            mouse_event(MOUSEEVENTF_MIDDLEUP, 0, 0, 0, UIntPtr.Zero);
                        }
                        else
                        {
                            mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, UIntPtr.Zero);
                            Thread.Sleep(10);
                            mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, UIntPtr.Zero);
                        }
                        break;

                    case "down":
                        string btnDown = GetJsonValue(json, "btn");
                        if (btnDown == "right")
                            mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, UIntPtr.Zero);
                        else
                            mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, UIntPtr.Zero);
                        break;

                    case "up":
                        string btnUp = GetJsonValue(json, "btn");
                        if (btnUp == "right")
                            mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, UIntPtr.Zero);
                        else
                            mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, UIntPtr.Zero);
                        break;

                    case "scroll":
                        double scrollDy = GetJsonDouble(json, "dy");
                        int scrollAmt = (int)(scrollDy * 120);
                        mouse_event(MOUSEEVENTF_WHEEL, 0, 0, scrollAmt, UIntPtr.Zero);
                        break;

                    case "zoom":
                        double zoomDelta = GetJsonDouble(json, "delta");
                        int zoomAmt = (int)(zoomDelta * 120);
                        keybd_event(VK_CONTROL, 0, 0, UIntPtr.Zero);
                        mouse_event(MOUSEEVENTF_WHEEL, 0, 0, zoomAmt, UIntPtr.Zero);
                        Thread.Sleep(10);
                        keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
                        break;

                    case "key":
                        string key = GetJsonValue(json, "key");
                        HandleKey(key);
                        break;

                    case "text":
                        string text = GetJsonValue(json, "text");
                        TypeUnicodeText(text);
                        break;

                    case "launch_url":
                        string url = GetJsonValue(json, "url");
                        LaunchUrl(url);
                        break;

                    case "power":
                        string action = GetJsonValue(json, "action");
                        double minutes = GetJsonDouble(json, "minutes");
                        HandlePower(action, minutes);
                        break;
                }
            }
            catch { }
        }

        static void HandleKey(string key)
        {
            switch (key)
            {
                case "enter": TapKey(VK_RETURN); break;
                case "backspace": TapKey(VK_BACK); break;
                case "esc": TapKey(VK_ESCAPE); break;
                case "tab": TapKey(VK_TAB); break;
                case "space": TapKey(VK_SPACE); break;
                case "win": TapKey(VK_LWIN); break;
                case "vol_up": TapKey(VK_VOLUME_UP); break;
                case "vol_down": TapKey(VK_VOLUME_DOWN); break;
                case "vol_mute": TapKey(VK_VOLUME_MUTE); break;
                case "play_pause": TapKey(VK_MEDIA_PLAY_PAUSE); break;
                case "next_track": TapKey(VK_MEDIA_NEXT_TRACK); break;
                case "prev_track": TapKey(VK_MEDIA_PREV_TRACK); break;
                case "alt_tab":
                    keybd_event(VK_MENU, 0, 0, UIntPtr.Zero);
                    TapKey(VK_TAB);
                    Thread.Sleep(30);
                    keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
                    break;
            }
        }

        static void TapKey(byte vk)
        {
            keybd_event(vk, 0, 0, UIntPtr.Zero);
            Thread.Sleep(10);
            keybd_event(vk, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
        }

        static void TypeUnicodeText(string text)
        {
            if (string.IsNullOrEmpty(text)) return;
            foreach (char ch in text)
            {
                INPUT[] inputs = new INPUT[2];
                inputs[0].type = INPUT_KEYBOARD;
                inputs[0].u.ki.wVk = 0;
                inputs[0].u.ki.wScan = (ushort)ch;
                inputs[0].u.ki.dwFlags = KEYEVENTF_UNICODE;

                inputs[1].type = INPUT_KEYBOARD;
                inputs[1].u.ki.wVk = 0;
                inputs[1].u.ki.wScan = (ushort)ch;
                inputs[1].u.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP;

                SendInput(2, inputs, Marshal.SizeOf(typeof(INPUT)));
                Thread.Sleep(3);
            }
        }

        static void LaunchUrl(string url)
        {
            if (string.IsNullOrEmpty(url)) return;
            if (!url.StartsWith("http://") && !url.StartsWith("https://"))
                url = "https://" + url;

            // Try Firefox first, then default browser
            try
            {
                string progFiles = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles);
                string ffPath = Path.Combine(progFiles, @"Mozilla Firefox\firefox.exe");
                if (File.Exists(ffPath))
                {
                    Process.Start(ffPath, "\"" + url + "\"");
                    return;
                }
            }
            catch { }

            try { Process.Start(url); } catch { }
        }

        static void HandlePower(string action, double minutes)
        {
            switch (action)
            {
                case "lock":
                    try { LockWorkStation(); } catch { }
                    break;

                case "sleep":
                    try { SetSuspendState(false, true, false); } catch { }
                    break;

                case "restart":
                    try { Process.Start("shutdown.exe", "/r /t 0"); } catch { }
                    break;

                case "shutdown":
                    try { Process.Start("shutdown.exe", "/s /t 0"); } catch { }
                    break;

                case "start_sleep_timer":
                    lock (sleepLock)
                    {
                        if (sleepTimer != null) sleepTimer.Dispose();
                        int ms = (int)(Math.Max(1, minutes) * 60 * 1000);
                        sleepTimer = new System.Threading.Timer(new TimerCallback(OnSleepTimerFired), null, ms, Timeout.Infinite);
                    }
                    break;

                case "cancel_sleep_timer":
                    lock (sleepLock)
                    {
                        if (sleepTimer != null)
                        {
                            sleepTimer.Dispose();
                            sleepTimer = null;
                        }
                    }
                    break;
            }
        }

        static void OnSleepTimerFired(object state)
        {
            try { SetSuspendState(false, true, false); } catch { }
        }

        // -------------------------------------------------------------
        // HTTP Download Portal Server (Port 8080)
        // -------------------------------------------------------------
        static void RunHttpPortal()
        {
            try
            {
                TcpListener httpListener = new TcpListener(IPAddress.Any, 8080);
                httpListener.Start();

                while (true)
                {
                    try
                    {
                        TcpClient client = httpListener.AcceptTcpClient();
                        Thread t = new Thread(new ParameterizedThreadStart(HandleHttpClientObj));
                        t.IsBackground = true;
                        t.Start(client);
                    }
                    catch { }
                }
            }
            catch { }
        }

        static void HandleHttpClientObj(object obj)
        {
            TcpClient client = obj as TcpClient;
            if (client != null) HandleHttpClient(client);
        }

        static void HandleHttpClient(TcpClient client)
        {
            using (client)
            using (NetworkStream s = client.GetStream())
            {
                try
                {
                    byte[] buf = new byte[2048];
                    int r = s.Read(buf, 0, buf.Length);
                    if (r <= 0) return;
                    string req = Encoding.UTF8.GetString(buf, 0, r);

                    string firstLine = req.Split('\n')[0];
                    string[] parts = firstLine.Split(' ');
                    string path = parts.Length > 1 ? parts[1] : "/";

                    if (path == "/" || path == "/index.html")
                    {
                        string html = "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Fetch Legacy Server</title>" +
                            "<style>body{background:#070b14;color:#f1f5f9;font-family:sans-serif;text-align:center;padding:50px;}" +
                            ".card{background:#0f172a;border:1px solid #1e293b;border-radius:18px;max-width:400px;margin:auto;padding:30px;}" +
                            ".btn{display:block;background:#0284c7;color:#fff;text-decoration:none;padding:12px;border-radius:10px;font-weight:bold;margin-top:15px;}</style>" +
                            "</head><body><div class='card'><h2>🐕 Fetch Server (Legacy Edition)</h2>" +
                            "<p>Running natively on Windows XP &amp; Vista.</p>" +
                            "<a class='btn' href='/Fetch.apk'>📱 Download Mobile App (.apk)</a></div></body></html>";
                        byte[] body = Encoding.UTF8.GetBytes(html);
                        string header = "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: " + body.Length + "\r\n\r\n";
                        byte[] hBytes = Encoding.UTF8.GetBytes(header);
                        s.Write(hBytes, 0, hBytes.Length);
                        s.Write(body, 0, body.Length);
                    }
                    else if (path == "/Fetch.apk")
                    {
                        string apkPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Fetch.apk");
                        if (!File.Exists(apkPath))
                            apkPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, @"..\Fetch.apk");

                        if (File.Exists(apkPath))
                        {
                            byte[] fileBytes = File.ReadAllBytes(apkPath);
                            string header = "HTTP/1.1 200 OK\r\nContent-Type: application/vnd.android.package-archive\r\n" +
                                            "Content-Disposition: attachment; filename=\"Fetch.apk\"\r\n" +
                                            "Content-Length: " + fileBytes.Length + "\r\n\r\n";
                            byte[] hBytes = Encoding.UTF8.GetBytes(header);
                            s.Write(hBytes, 0, hBytes.Length);
                            s.Write(fileBytes, 0, fileBytes.Length);
                        }
                        else
                        {
                            byte[] err = Encoding.UTF8.GetBytes("HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n");
                            s.Write(err, 0, err.Length);
                        }
                    }
                }
                catch { }
            }
        }

        // -------------------------------------------------------------
        // Helpers
        // -------------------------------------------------------------
        static string GetLocalIp()
        {
            try
            {
                using (Socket s = new Socket(AddressFamily.InterNetwork, SocketType.Dgram, ProtocolType.Udp))
                {
                    s.Connect("8.8.8.8", 80);
                    IPEndPoint ep = s.LocalEndPoint as IPEndPoint;
                    if (ep != null) return ep.Address.ToString();
                }
            }
            catch { }
            return "127.0.0.1";
        }

        static string GetMacAddress()
        {
            try
            {
                foreach (NetworkInterface nic in NetworkInterface.GetAllNetworkInterfaces())
                {
                    if (nic.OperationalStatus == OperationalStatus.Up &&
                        nic.NetworkInterfaceType != NetworkInterfaceType.Loopback)
                    {
                        string mac = nic.GetPhysicalAddress().ToString();
                        if (mac.Length == 12)
                        {
                            List<string> parts = new List<string>();
                            for (int i = 0; i < 12; i += 2) parts.Add(mac.Substring(i, 2));
                            return string.Join(":", parts.ToArray());
                        }
                    }
                }
            }
            catch { }
            return "00:00:00:00:00:00";
        }

        static string GetJsonValue(string json, string key)
        {
            Match m = Regex.Match(json, "\"" + key + "\":\\s*\"([^\"]*)\"");
            if (m.Success) return m.Groups[1].Value;
            Match mNum = Regex.Match(json, "\"" + key + "\":\\s*([^,}]+)");
            if (mNum.Success) return mNum.Groups[1].Value.Trim();
            return null;
        }

        static double GetJsonDouble(string json, string key)
        {
            Match m = Regex.Match(json, "\"" + key + "\":\\s*(-?[0-9\\.]+)");
            if (m.Success)
            {
                double d;
                if (double.TryParse(m.Groups[1].Value, System.Globalization.NumberStyles.Any, System.Globalization.CultureInfo.InvariantCulture, out d))
                    return d;
            }
            return 0;
        }
    }
}
