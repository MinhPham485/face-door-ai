#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include "esp_camera.h"
#include "esp_sleep.h"
#include <ESP32Servo.h>
#include "board_config.h"

// --- CẤU HÌNH MẠNG & SERVER ---
const char *ssid = "PhamQuangTrung";
const char *password = "h4ymwyx6";
const char *SERVER_URL = "http://10.166.158.244:8000/verify-face";

#define PIR_PIN         14
#define SERVO_PIN       13
#define LED_OPEN_PIN    2 
#define LED_DENY_PIN    12
#define LED_WAIT_PIN    4 

Servo doorServo;

void connectWiFi()
{
    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, password);
    Serial.print("Connecting WiFi");
    while (WiFi.status() != WL_CONNECTED)
    {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nWiFi Connected! IP: ");
    Serial.println(WiFi.localIP());
}

void openDoor()
{
    digitalWrite(LED_WAIT_PIN, LOW);
    digitalWrite(LED_DENY_PIN, LOW);
    digitalWrite(LED_OPEN_PIN, HIGH);

    doorServo.write(90);
    delay(5000);
    doorServo.write(0);
    delay(1000);

    digitalWrite(LED_OPEN_PIN, LOW);
}

void denyDoor()
{
    digitalWrite(LED_WAIT_PIN, LOW);
    digitalWrite(LED_OPEN_PIN, LOW);
    digitalWrite(LED_DENY_PIN, HIGH);

    delay(3000);

    digitalWrite(LED_DENY_PIN, LOW);
}

bool initCamera()
{
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = Y2_GPIO_NUM;
    config.pin_d1 = Y3_GPIO_NUM;
    config.pin_d2 = Y4_GPIO_NUM;
    config.pin_d3 = Y5_GPIO_NUM;
    config.pin_d4 = Y6_GPIO_NUM;
    config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM;
    config.pin_d7 = Y9_GPIO_NUM;
    config.pin_xclk = XCLK_GPIO_NUM;
    config.pin_pclk = PCLK_GPIO_NUM;
    config.pin_vsync = VSYNC_GPIO_NUM;
    config.pin_href = HREF_GPIO_NUM;
    config.pin_sccb_sda = SIOD_GPIO_NUM;
    config.pin_sccb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;
    config.frame_size = FRAMESIZE_VGA; 
    config.jpeg_quality = 10;
    config.fb_count = psramFound() ? 2 : 1;

    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK)
    {
        Serial.printf("Camera init failed: 0x%x\n", err);
        return false;
    }
    return true;
}

void captureAndSend()
{
    // Bật đèn báo hiệu đang xử lý
    digitalWrite(LED_WAIT_PIN, HIGH); 
    delay(500);
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb)
    {
        Serial.println("Capture failed");
        return;
    }
    Serial.printf("Image captured: %d bytes\n", fb->len);

    HTTPClient http;
    String boundary = "ESP32CAMBOUNDARY";
    
    http.begin(SERVER_URL);
    http.addHeader("Content-Type", "multipart/form-data; boundary=" + boundary);

    String head = "--" + boundary + "\r\n"
                  "Content-Disposition: form-data; name=\"file\"; filename=\"face.jpg\"\r\n"
                  "Content-Type: image/jpeg\r\n\r\n";
    String tail = "\r\n--" + boundary + "--\r\n";

    int totalLength = head.length() + fb->len + tail.length();
    uint8_t *body = (uint8_t *)malloc(totalLength);

    if (!body)
    {
        Serial.println("malloc failed");
        digitalWrite(LED_WAIT_PIN, LOW);
        esp_camera_fb_return(fb);
        return;
    }

    memcpy(body, head.c_str(), head.length());
    memcpy(body + head.length(), fb->buf, fb->len);
    memcpy(body + head.length() + fb->len, tail.c_str(), tail.length());

    int code = http.POST(body, totalLength);

    digitalWrite(LED_WAIT_PIN, LOW); 

    if (code > 0)
    {
        String response = http.getString();
        Serial.println("Response: " + response);

        if (response.indexOf("\"action\":\"OPEN\"") >= 0)
        {
            Serial.println("OPEN DOOR");
            openDoor();
        }
        else
        {
            Serial.println("DENY");
            denyDoor();
        }
    }
    else
    {
        Serial.printf("HTTP Error: %d\n", code);
        denyDoor(); 
    }

    free(body);
    http.end();
    esp_camera_fb_return(fb);
}

void setup()
{
    Serial.begin(115200);

    // 1. Khởi tạo chân GPIO
    pinMode(LED_OPEN_PIN, OUTPUT);
    pinMode(LED_DENY_PIN, OUTPUT);
    pinMode(LED_WAIT_PIN, OUTPUT);

    digitalWrite(LED_OPEN_PIN, LOW);
    digitalWrite(LED_DENY_PIN, LOW);
    digitalWrite(LED_WAIT_PIN, LOW);

    doorServo.attach(SERVO_PIN);
    doorServo.write(0);
    delay(500);

    // 2. Kiểm tra lý do mạch thức dậy
    esp_sleep_wakeup_cause_t wakeup_reason = esp_sleep_get_wakeup_cause();
    Serial.printf("Wakeup reason: %d\n", wakeup_reason);

    // Nếu thức dậy do PIR
    if (wakeup_reason == ESP_SLEEP_WAKEUP_EXT0)
    {
        Serial.println("Motion detected! Processing...");
        delay(300); 

        if (initCamera())
        {
            connectWiFi();
            captureAndSend();
        }
    }

    //Deep Sleep
    Serial.println("Disconnecting WiFi & Sleeping...");
    WiFi.disconnect(true);
    WiFi.mode(WIFI_OFF);
    
    // Ngắt Servo để tránh tốn pin và giật motor trong lúc ngủ
    doorServo.detach(); 
    
    digitalWrite(LED_OPEN_PIN, LOW);
    digitalWrite(LED_DENY_PIN, LOW);
    digitalWrite(LED_WAIT_PIN, LOW);

    // Cài đặt ngắt để thức dậy (PIR kích hoạt ở mức HIGH)
    esp_sleep_enable_ext0_wakeup((gpio_num_t)PIR_PIN, 1);

    delay(100);
    esp_deep_sleep_start();
}

void loop()
{
}