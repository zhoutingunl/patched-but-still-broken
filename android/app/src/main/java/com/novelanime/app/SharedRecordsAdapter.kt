package com.novelanime.app

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView

class SharedRecordsAdapter(
    private val onItemClick: (SharedRecord) -> Unit
) : RecyclerView.Adapter<SharedRecordsAdapter.ViewHolder>() {

    private var records = listOf<SharedRecord>()

    class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val tvFilename: TextView = view.findViewById(R.id.tvFilename)
        val tvUsername: TextView = view.findViewById(R.id.tvUsername)
        val tvTimestamp: TextView = view.findViewById(R.id.tvTimestamp)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_shared_record, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val record = records[position]
        holder.tvFilename.text = record.filename
        holder.tvUsername.text = "作者: ${record.username}"
        holder.tvTimestamp.text = formatTimestamp(record.timestamp)
        
        holder.itemView.setOnClickListener {
            onItemClick(record)
        }
    }

    override fun getItemCount() = records.size

    fun updateRecords(newRecords: List<SharedRecord>) {
        records = newRecords
        notifyDataSetChanged()
    }

    private fun formatTimestamp(timestamp: String): String {
        if (timestamp.isEmpty()) return ""
        return try {
            timestamp.substring(0, 16).replace("T", " ")
        } catch (e: Exception) {
            timestamp
        }
    }
}
