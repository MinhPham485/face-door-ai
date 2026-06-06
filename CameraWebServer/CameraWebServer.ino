#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include "esp_camera.h"
#include "esp_sleep.h"

#include "board_config.h"

const char *ssid = "415B9";
const char *password = "10anhdeptrai";

#define uS_TO_S_FACTOR 1000000ULL
#define SLEEP_TIME_SEC 5

// IP máy chạy FastAPI
const char *SERVER_URL =
    "http://192.168.1.14:8000/verify-face";

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

    Serial.println();
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
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
    config.fb_count = 1;

    if (psramFound())
    {
        config.fb_count = 2;
    }

    esp_err_t err = esp_camera_init(&config);

    if (err != ESP_OK)
    {
        Serial.printf(
            "Camera init failed: 0x%x\n",
            err
        );
        return false;
    }

    return true;
}

void captureAndSend()
{
    camera_fb_t *fb = esp_camera_fb_get();

    if (!fb)
    {
        Serial.println("Capture failed");
        return;
    }

    Serial.printf(
        "Image captured: %d bytes\n",
        fb->len
    );

    HTTPClient http;

    String boundary = "ESP32CAMBOUNDARY";

    http.begin(SERVER_URL);

    http.addHeader(
        "Content-Type",
        "multipart/form-data; boundary=" + boundary
    );

    String head =
        "--" + boundary + "\r\n"
        "Content-Disposition: form-data; "
        "name=\"file\"; filename=\"face.jpg\"\r\n"
        "Content-Type: image/jpeg\r\n\r\n";

    String tail =
        "\r\n--" + boundary + "--\r\n";

    int totalLength =
        head.length() +
        fb->len +
        tail.length();

    uint8_t *body =
        (uint8_t *)malloc(totalLength);

    if (!body)
    {
        Serial.println("malloc failed");

        esp_camera_fb_return(fb);
        return;
    }

    memcpy(
        body,
        head.c_str(),
        head.length()
    );

    memcpy(
        body + head.length(),
        fb->buf,
        fb->len
    );

    memcpy(
        body + head.length() + fb->len,
        tail.c_str(),
        tail.length()
    );

    int code =
        http.POST(body, totalLength);

    if (code > 0)
    {
        String response =
            http.getString();

        Serial.println("Response:");

        Serial.println(response);

        if (response.indexOf("\"action\":\"OPEN\"") >= 0)
        {
            Serial.println("OPEN DOOR");
        }
        else
        {
            Serial.println("DENY");
        }
    }
    else
    {
        Serial.printf(
            "HTTP Error: %d\n",
            code
        );
    }

    free(body);

    http.end();

    esp_camera_fb_return(fb);
}

void setup()
{
    Serial.begin(115200);

    delay(1000);

    if (!initCamera())
    {
        esp_deep_sleep_start();
    }

    connectWiFi();

    captureAndSend();

    Serial.println(
        "Going to sleep..."
    );

    esp_sleep_enable_timer_wakeup(
        SLEEP_TIME_SEC *
        uS_TO_S_FACTOR
    );

    delay(100);

    esp_deep_sleep_start();
}

void loop()
{
}