package com.fetch.controller;

import android.content.Context;
import android.content.SharedPreferences;
import android.os.Build;
import android.os.Bundle;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.view.View;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;

public class MainActivity extends AppCompatActivity {

    private WebView webView;
    private Vibrator vibrator;
    private SharedPreferences prefs;
    private long lastBackPressTime = 0;
    private boolean isDiscovering = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        hideSystemUI();

        vibrator = (Vibrator) getSystemService(Context.VIBRATOR_SERVICE);
        prefs = getSharedPreferences("fetch_prefs", MODE_PRIVATE);

        webView = new WebView(this);
        setContentView(webView);

        WebSettings webSettings = webView.getSettings();
        webSettings.setJavaScriptEnabled(true);
        webSettings.setDomStorageEnabled(true);
        webSettings.setAllowFileAccess(true);
        webSettings.setMediaPlaybackRequiresUserGesture(false);
        webSettings.setCacheMode(WebSettings.LOAD_NO_CACHE);

        webView.setLayerType(View.LAYER_TYPE_HARDWARE, null);

        webView.setWebChromeClient(new WebChromeClient());
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                startDiscovery();
            }
        });

        webView.addJavascriptInterface(new WebAppInterface(), "AndroidBridge");
        webView.loadUrl("file:///android_asset/index.html");
    }

    private void hideSystemUI() {
        View decorView = getWindow().getDecorView();
        decorView.setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                | View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                | View.SYSTEM_UI_FLAG_FULLSCREEN
        );
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) {
            hideSystemUI();
        }
    }

    @Override
    public void onBackPressed() {
        if (System.currentTimeMillis() - lastBackPressTime < 2000) {
            super.onBackPressed();
        } else {
            lastBackPressTime = System.currentTimeMillis();
            Toast.makeText(this, "Press back again to exit", Toast.LENGTH_SHORT).show();
        }
    }

    public void startDiscovery() {
        if (isDiscovering) return;
        isDiscovering = true;

        new Thread(() -> {
            DatagramSocket socket = null;
            try {
                socket = new DatagramSocket();
                socket.setBroadcast(true);
                socket.setSoTimeout(600);

                byte[] sendData = "DISCOVER_FETCH".getBytes();
                DatagramPacket sendPacket = new DatagramPacket(
                        sendData, sendData.length,
                        InetAddress.getByName("255.255.255.255"), 8766
                );

                for (int i = 0; i < 3; i++) {
                    socket.send(sendPacket);
                    Thread.sleep(60);
                }

                long deadline = System.currentTimeMillis() + 2500;
                while (System.currentTimeMillis() < deadline) {
                    try {
                        byte[] recvBuf = new byte[1024];
                        DatagramPacket recvPacket = new DatagramPacket(recvBuf, recvBuf.length);
                        socket.receive(recvPacket);

                        String response = new String(recvPacket.getData(), 0, recvPacket.getLength()).trim();
                        if (response.startsWith("FETCH_OFFER|") || response.startsWith("PC_TOUCH_OFFER|")) {
                            String[] parts = response.split("\\|");
                            if (parts.length >= 4) {
                                final String hostname = parts[1];
                                final String ip = parts[2];
                                final String port = parts[3];
                                final String osName = parts.length >= 5 ? parts[4] : "PC";
                                final String macAddress = parts.length >= 6 ? parts[5] : "";

                                runOnUiThread(() -> {
                                    webView.evaluateJavascript(
                                            "if(window.onServerDiscovered) { window.onServerDiscovered('" + ip + "', '" + port + "', '" + hostname + "', '" + osName + "', '" + macAddress + "'); }",
                                            null
                                    );
                                });
                            }
                        }
                    } catch (java.net.SocketTimeoutException ste) {
                        // socket timeout per receive, continue loop until deadline
                    } catch (Exception e) {
                        break;
                    }
                }
            } catch (Exception e) {
                // Ignore network errors
            } finally {
                if (socket != null && !socket.isClosed()) {
                    socket.close();
                }
                isDiscovering = false;
                runOnUiThread(() -> {
                    webView.evaluateJavascript(
                            "if(window.onDiscoveryComplete) { window.onDiscoveryComplete(); }",
                            null
                    );
                });
            }
        }).start();
    }

    public class WebAppInterface {
        @JavascriptInterface
        public void vibrate(int ms) {
            if (vibrator != null && vibrator.hasVibrator()) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    vibrator.vibrate(VibrationEffect.createOneShot(ms, VibrationEffect.DEFAULT_AMPLITUDE));
                } else {
                    vibrator.vibrate(ms);
                }
            }
        }

        @JavascriptInterface
        public void startDiscovery() {
            MainActivity.this.startDiscovery();
        }

        @JavascriptInterface
        public void saveIp(String ip) {
            prefs.edit().putString("saved_ip", ip).apply();
        }

        @JavascriptInterface
        public String getSavedIp() {
            return prefs.getString("saved_ip", "");
        }

        @JavascriptInterface
        public void wakeOnLan(String mac) {
            new Thread(() -> {
                try {
                    String cleanMac = mac.replaceAll("[:\\- ]", "");
                    if (cleanMac.length() != 12) return;

                    byte[] macBytes = new byte[6];
                    for (int i = 0; i < 6; i++) {
                        macBytes[i] = (byte) Integer.parseInt(cleanMac.substring(i * 2, i * 2 + 2), 16);
                    }

                    byte[] bytes = new byte[6 + 16 * macBytes.length];
                    for (int i = 0; i < 6; i++) {
                        bytes[i] = (byte) 0xff;
                    }
                    for (int i = 6; i < bytes.length; i += macBytes.length) {
                        System.arraycopy(macBytes, 0, bytes, i, macBytes.length);
                    }

                    DatagramPacket packet = new DatagramPacket(
                            bytes, bytes.length,
                            InetAddress.getByName("255.255.255.255"), 9
                    );
                    DatagramSocket socket = new DatagramSocket();
                    socket.setBroadcast(true);
                    socket.send(packet);
                    socket.close();
                } catch (Exception ignored) {}
            }).start();
        }

        @JavascriptInterface
        public void showSoftKeyboard() {
            runOnUiThread(() -> {
                android.view.inputmethod.InputMethodManager imm =
                        (android.view.inputmethod.InputMethodManager) getSystemService(Context.INPUT_METHOD_SERVICE);
                if (imm != null) {
                    webView.requestFocus();
                    imm.showSoftInput(webView, android.view.inputmethod.InputMethodManager.SHOW_IMPLICIT);
                }
            });
        }

        @JavascriptInterface
        public void hideSoftKeyboard() {
            runOnUiThread(() -> {
                android.view.inputmethod.InputMethodManager imm =
                        (android.view.inputmethod.InputMethodManager) getSystemService(Context.INPUT_METHOD_SERVICE);
                if (imm != null) {
                    imm.hideSoftInputFromWindow(webView.getWindowToken(), 0);
                }
            });
        }
    }
}
