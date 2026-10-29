package com.updatiq.app;

import android.app.Activity;
import android.os.Bundle;
import android.graphics.Color;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.JavascriptInterface;
import android.os.Build;
import android.widget.Toast;

public class MainActivity extends Activity {
    private WebView webView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        Window window = getWindow();
        window.setStatusBarColor(Color.rgb(11, 17, 33));
        window.setNavigationBarColor(Color.rgb(7, 12, 26));
        window.getDecorView().setSystemUiVisibility(0);
        window.addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS);

        webView = new WebView(this);
        webView.setBackgroundColor(Color.rgb(7, 12, 26));
        webView.setLayerType(View.LAYER_TYPE_HARDWARE, null);
        webView.setOverScrollMode(View.OVER_SCROLL_NEVER);
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setLoadsImagesAutomatically(true);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            settings.setOffscreenPreRaster(true);
        }
        webView.addJavascriptInterface(new AndroidNavigation(), "AndroidNavigation");
        webView.addJavascriptInterface(new AndroidExternal(), "AndroidExternal");
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, android.webkit.WebResourceRequest request) {
                Uri uri = request.getUrl();
                String scheme = uri.getScheme() == null ? "" : uri.getScheme().toLowerCase();
                if ("file".equals(scheme) || "about".equals(scheme) || "javascript".equals(scheme)) return false;
                if ("http".equals(scheme) || "https".equals(scheme) || "market".equals(scheme) || "mailto".equals(scheme)) {
                    openExternalUrl(uri.toString());
                    return true;
                }
                return true;
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                Uri uri = Uri.parse(url);
                String scheme = uri.getScheme() == null ? "" : uri.getScheme().toLowerCase();
                if ("file".equals(scheme) || "about".equals(scheme) || "javascript".equals(scheme)) return false;
                if ("http".equals(scheme) || "https".equals(scheme) || "market".equals(scheme) || "mailto".equals(scheme)) {
                    openExternalUrl(url);
                }
                return true;
            }
        });
        webView.setWebChromeClient(new WebChromeClient());
        setContentView(webView);
        if (savedInstanceState != null) webView.restoreState(savedInstanceState);
        else webView.loadUrl("file:///android_asset/index.html");
    }


    @Override
    protected void onResume() {
        super.onResume();
        if (webView != null) {
            webView.onResume();
            webView.resumeTimers();
            webView.post(() -> {
                if (webView == null) return;
                webView.requestLayout();
                webView.invalidate();
                webView.evaluateJavascript(
                    "if(document.visibilityState==='visible'){window.dispatchEvent(new Event('resize'));}",
                    null
                );
            });
        }
    }

    @Override
    protected void onPause() {
        if (webView != null) webView.onPause();
        super.onPause();
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        if (webView != null) webView.saveState(outState);
        super.onSaveInstanceState(outState);
    }

    private void openExternalUrl(String url) {
        try {
            Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(intent);
        } catch (Exception e) {
            runOnUiThread(() -> Toast.makeText(MainActivity.this, "Не удалось открыть ссылку во внешнем приложении.", Toast.LENGTH_SHORT).show());
        }
    }

    private class AndroidExternal {
        @JavascriptInterface
        public void open(String url) {
            if (url == null || url.trim().isEmpty()) return;
            Uri uri = Uri.parse(url.trim());
            String scheme = uri.getScheme() == null ? "" : uri.getScheme().toLowerCase();
            if (!"https".equals(scheme) && !"http".equals(scheme) && !"market".equals(scheme) && !"mailto".equals(scheme)) return;
            runOnUiThread(() -> openExternalUrl(uri.toString()));
        }
    }

    private class AndroidNavigation {
        @JavascriptInterface
        public void exitApp() {
            runOnUiThread(() -> finish());
        }
    }

    @Override
    public void onBackPressed() {
        if (webView != null) {
            webView.evaluateJavascript(
                "(function(){return window.handleAppBack?window.handleAppBack():false})()",
                value -> {
                    if ("false".equals(value) || value == null) finish();
                }
            );
        } else {
            super.onBackPressed();
        }
    }
}
