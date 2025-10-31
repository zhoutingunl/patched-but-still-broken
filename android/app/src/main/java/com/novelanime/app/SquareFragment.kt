package com.novelanime.app

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import kotlinx.coroutines.*
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

class SquareFragment : Fragment() {

    private lateinit var recyclerView: RecyclerView
    private lateinit var adapter: SharedRecordsAdapter
    private val scope = CoroutineScope(Dispatchers.Main + Job())

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        val view = inflater.inflate(R.layout.fragment_square, container, false)
        
        recyclerView = view.findViewById(R.id.recyclerView)
        recyclerView.layoutManager = LinearLayoutManager(context)
        
        adapter = SharedRecordsAdapter { record ->
            onRecordClicked(record)
        }
        recyclerView.adapter = adapter
        
        loadSharedRecords()
        
        return view
    }

    private fun loadSharedRecords() {
        scope.launch {
            try {
                val records = withContext(Dispatchers.IO) {
                    fetchSharedRecords()
                }
                adapter.updateRecords(records)
            } catch (e: Exception) {
                Toast.makeText(context, "加载失败: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun fetchSharedRecords(): List<SharedRecord> {
        val url = URL("${MainActivity.SERVER_URL}/api/shared_records")
        val connection = url.openConnection() as HttpURLConnection
        
        try {
            connection.requestMethod = "GET"
            connection.connectTimeout = 10000
            connection.readTimeout = 10000
            
            val responseCode = connection.responseCode
            if (responseCode == HttpURLConnection.HTTP_OK) {
                val response = connection.inputStream.bufferedReader().use { it.readText() }
                val jsonObject = JSONObject(response)
                val recordsArray = jsonObject.getJSONArray("records")
                
                val records = mutableListOf<SharedRecord>()
                for (i in 0 until recordsArray.length()) {
                    val record = recordsArray.getJSONObject(i)
                    records.add(
                        SharedRecord(
                            sessionId = record.getString("session_id"),
                            username = record.optString("username", "匿名"),
                            filename = record.optString("filename", "未命名"),
                            timestamp = record.optString("upload_timestamp", "")
                        )
                    )
                }
                return records
            }
        } finally {
            connection.disconnect()
        }
        
        return emptyList()
    }

    private fun onRecordClicked(record: SharedRecord) {
        (activity as? MainActivity)?.loadRecordInPlayer(record.sessionId)
    }

    override fun onDestroy() {
        super.onDestroy()
        scope.cancel()
    }
}

data class SharedRecord(
    val sessionId: String,
    val username: String,
    val filename: String,
    val timestamp: String
)
