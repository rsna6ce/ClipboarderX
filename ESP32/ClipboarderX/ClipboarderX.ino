#include <WiFi.h>
#include <Preferences.h>

const uint16_t SERVER_PORT = 50000;
const int LED_PIN = 2; // ESP32 DevKit v1 オンボード青色LED

Preferences preferences;
WiFiServer server(SERVER_PORT);
WiFiClient client1;
WiFiClient client2;

String wifiSsid = "";
String wifiPass = "";
unsigned long lastBlink = 0;

// シリアルから1行読み取る関数（改行コード CR/LF 両対応・バックスペース対応）
String readSerialLine(bool maskInput = false) {
  String input = "";
  while (true) {
    while (Serial.available() > 0) {
      char c = Serial.read();
      if (c == '\r' || c == '\n') {
        if (input.length() > 0) {
          Serial.println();
          return input;
        }
      } else if (c == '\b' || c == 127) {
        if (input.length() > 0) {
          input.remove(input.length() - 1);
          Serial.print("\b \b");
        }
      } else {
        input += c;
        Serial.print(maskInput ? '*' : c);
      }
    }
    delay(10);
  }
}

// シリアル対話でSSIDとパスワードを入力・保存する処理
void configureWiFiViaSerial() {
  Serial.println("\n========================================");
  Serial.println(" Wi-Fi 接続設定モード");
  Serial.println("========================================");
  
  Serial.print("SSID を入力してください: ");
  wifiSsid = readSerialLine(false);
  wifiSsid.trim();

  Serial.print("パスワードを入力してください: ");
  wifiPass = readSerialLine(true);
  wifiPass.trim();

  // 不揮発性メモリ(NVS)に保存
  preferences.begin("wifi-config", false);
  preferences.putString("ssid", wifiSsid);
  preferences.putString("pass", wifiPass);
  preferences.end();

  Serial.println("設定を保存しました。再起動して接続します...\n");
  delay(1000);
  ESP.restart();
}

// 現在のステータス表示
void printStatus() {
  Serial.println("----------------------------------------");
  Serial.print("SSID        : "); Serial.println(wifiSsid);
  Serial.print("IPアドレス  : "); Serial.println(WiFi.localIP());
  Serial.print("待ち受けPort: "); Serial.println(SERVER_PORT);
  Serial.print("1番席 接続  : "); Serial.println((client1 && client1.connected()) ? client1.remoteIP().toString() : "空き");
  Serial.print("2番席 接続  : "); Serial.println((client2 && client2.connected()) ? client2.remoteIP().toString() : "空き");
  Serial.println("コマンド    : 'setup' でWi-Fi再設定 / 'status' で状態確認");
  Serial.println("----------------------------------------");
}

// Wi-Fi接続処理
void connectToWiFi() {
  WiFi.disconnect(true);
  delay(200);
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false); // 通信レスポンスの遅延を防止
  WiFi.begin(wifiSsid.c_str(), wifiPass.c_str());

  Serial.print("Wi-Fiに接続中 (" + wifiSsid + ")");
  int retryCount = 0;

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    digitalWrite(LED_PIN, !digitalRead(LED_PIN));
    retryCount++;

    // 接続待ち中でもシリアルから "setup" が打たれたら設定モードへ移行
    if (Serial.available() > 0) {
      String cmd = Serial.readStringUntil('\n');
      cmd.trim();
      if (cmd.equalsIgnoreCase("setup") || cmd.equalsIgnoreCase("reset")) {
        configureWiFiViaSerial();
      }
    }

    if (retryCount == 60) {
      Serial.println("\n[警告] 接続に時間がかかっています。SSID/パスワードをやり直す場合は 'setup' と送信してください。");
    }
  }

  digitalWrite(LED_PIN, LOW);
  Serial.println("\n\nWi-Fi接続完了！");
  printStatus();
}

// 稼働中のシリアルコマンド監視
void checkSerialCommand() {
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.equalsIgnoreCase("setup") || cmd.equalsIgnoreCase("reset")) {
      if (client1) client1.stop();
      if (client2) client2.stop();
      configureWiFiViaSerial();
    } else if (cmd.equalsIgnoreCase("status")) {
      printStatus();
    }
  }
}

// 相手がいない間に送られてきたデータを読み捨ててバッファ溢れを防ぐ（/dev/null 処理）
void drainBuffer(WiFiClient& src) {
  while (src.available() > 0) {
    src.read();
  }
}

// 受信バッファにあるデータをまとめてもう片方へ転送する関数
void relayData(WiFiClient& src, WiFiClient& dst) {
  int avail = src.available();
  if (avail > 0) {
    uint8_t buf[1024];
    int toRead = (avail > (int)sizeof(buf)) ? (int)sizeof(buf) : avail;
    int len = src.read(buf, toRead);
    if (len > 0) {
      dst.write(buf, len);
    }
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  delay(500);

  Serial.println("\nClipboarderX Relay Server (ESP32 Core 2.0.x)");

  // 保存済みのWi-Fi設定を読み込む
  preferences.begin("wifi-config", true);
  wifiSsid = preferences.getString("ssid", "");
  wifiPass = preferences.getString("pass", "");
  preferences.end();

  // 未設定ならシリアル設定モードへ
  if (wifiSsid.length() == 0) {
    configureWiFiViaSerial();
  }

  connectToWiFi();
  server.begin();
}

void loop() {
  checkSerialCommand();

  // Wi-Fi切断時の自動復帰
  if (WiFi.status() != WL_CONNECTED) {
    digitalWrite(LED_PIN, LOW);
    Serial.println("Wi-Fiが切断されました。再接続します...");
    connectToWiFi();
    return;
  }

  // 1. 切断済みのクライアントがあれば、その席だけを解放する（もう片方は維持）
  if (client1 && !client1.connected()) {
    Serial.println("[切断] 1番席が切断されました（2番席は維持）");
    client1.stop();
  }
  if (client2 && !client2.connected()) {
    Serial.println("[切断] 2番席が切断されました（1番席は維持）");
    client2.stop();
  }

  // 2. 新しい接続要求があれば空いている席に入れる（Core 2.0.x 仕様: server.available()）
  WiFiClient newClient = server.available();
  if (newClient) {
    newClient.setNoDelay(true);
    if (!client1 || !client1.connected()) {
      client1 = newClient;
      Serial.print("[接続] 1番席に着席: ");
      Serial.println(client1.remoteIP());
    } else if (!client2 || !client2.connected()) {
      client2 = newClient;
      Serial.print("[接続] 2番席に着席: ");
      Serial.println(client2.remoteIP());
    } else {
      // 満席時のゴースト再接続対策：古い1番席を解放して新しい接続を受け入れる
      Serial.println("[再接続] 満席のため古い接続を解放して受け入れます");
      client1.stop();
      client1 = newClient;
      Serial.print("[接続] 1番席に着席: ");
      Serial.println(client1.remoteIP());
    }
  }

  // 3. 接続台数に応じたデータ処理とLED状態表示
  bool c1Ready = (client1 && client1.connected());
  bool c2Ready = (client2 && client2.connected());

  if (c1Ready && c2Ready) {
    // 2台接続中：LED常時点灯＆双方向リレー
    digitalWrite(LED_PIN, HIGH);
    relayData(client1, client2);
    relayData(client2, client1);
  } else if (c1Ready || c2Ready) {
    // 1台だけ待機中：LEDゆっくり点滅（送信データは破棄してメモリ詰まり防止）
    if (millis() - lastBlink > 1000) {
      lastBlink = millis();
      digitalWrite(LED_PIN, !digitalRead(LED_PIN));
    }
    if (c1Ready) drainBuffer(client1);
    if (c2Ready) drainBuffer(client2);
    delay(10);
  } else {
    // 0台：LED消灯
    digitalWrite(LED_PIN, LOW);
    delay(10);
  }
}