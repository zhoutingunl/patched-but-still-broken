package com.novelanime.app

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.fragment.app.Fragment

class PlayerFragment : Fragment() {

    private lateinit var webView: WebView

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        val view = inflater.inflate(R.layout.fragment_player, container, false)
        
        webView = view.findViewById(R.id.playerWebView)
        setupWebView()
        
        return view
    }

    private fun setupWebView() {
        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            allowFileAccess = true
            allowContentAccess = true
            mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
            cacheMode = WebSettings.LOAD_DEFAULT
        }

        webView.webViewClient = WebViewClient()
        webView.loadUrl("${MainActivity.SERVER_URL}/home")
    }

    fun loadRecord(sessionId: String) {
        webView.loadUrl("${MainActivity.SERVER_URL}/home?session_id=$sessionId")
    }

    override fun onDestroy() {
        webView.destroy()
        super.onDestroy()
    }
}
