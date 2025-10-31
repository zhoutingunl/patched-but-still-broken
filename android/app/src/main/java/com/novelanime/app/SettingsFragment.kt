package com.novelanime.app

import android.content.Intent
import android.graphics.BitmapFactory
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.ImageView
import android.widget.Toast
import androidx.fragment.app.Fragment
import kotlinx.coroutines.*
import java.net.HttpURLConnection
import java.net.URL

class SettingsFragment : Fragment() {

    private val scope = CoroutineScope(Dispatchers.Main + Job())

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        val view = inflater.inflate(R.layout.fragment_settings, container, false)
        
        val btnSettings = view.findViewById<Button>(R.id.btnSettings)
        val wechatQRCode = view.findViewById<ImageView>(R.id.wechatQRCode)
        val apkQRCode = view.findViewById<ImageView>(R.id.apkQRCode)
        
        btnSettings.setOnClickListener {
            val intent = Intent(activity, SettingsActivity::class.java)
            startActivity(intent)
        }
        
        loadQRCode(wechatQRCode, "${MainActivity.SERVER_URL}/static/qrcode.png")
        loadQRCode(apkQRCode, "${MainActivity.SERVER_URL}/static/apk_qr.png")
        
        return view
    }

    private fun loadQRCode(imageView: ImageView, url: String) {
        scope.launch {
            try {
                val bitmap = withContext(Dispatchers.IO) {
                    val connection = URL(url).openConnection() as HttpURLConnection
                    connection.doInput = true
                    connection.connect()
                    val input = connection.inputStream
                    BitmapFactory.decodeStream(input)
                }
                imageView.setImageBitmap(bitmap)
            } catch (e: Exception) {
                Toast.makeText(context, "加载二维码失败", Toast.LENGTH_SHORT).show()
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        scope.cancel()
    }
}
