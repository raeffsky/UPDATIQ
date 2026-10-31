package com.updatiq.app.data

import android.content.Context
import androidx.room.Room
import com.google.gson.Gson
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class GameDataStore(context: Context) {
    private val database = Room.databaseBuilder(
        context.applicationContext,
        UpdatiqDatabase::class.java,
        "updatiq-game-data.db"
    ).build()
    private val dao = database.cachedDatasetDao()
    private val gson = Gson()

    suspend fun cachedDataset(id: String): String? = withContext(Dispatchers.IO) {
        dao.get(id)?.jsonPayload
    }

    suspend fun allCachedDatasets(): Map<String, String> = withContext(Dispatchers.IO) {
        dao.getAll().associate { it.datasetId to it.jsonPayload }
    }

    suspend fun refresh(repository: LiveGameDataRepository): Result<LiveDatasetResult> {
        val result = repository.fetchLatest()
        result.onSuccess { data ->
            withContext(Dispatchers.IO) {
                val now = System.currentTimeMillis()
                val updated = listOf(
                    CachedDatasetEntity("ranked", gson.toJson(data.ranked), data.updatedAt, now),
                    CachedDatasetEntity("tournament", data.tournament.toString(), data.updatedAt, now),
                    CachedDatasetEntity("builds", data.builds.toString(), data.updatedAt, now),
                    CachedDatasetEntity("counters", data.counters.toString(), data.updatedAt, now)
                )
                dao.putAll(updated)
            }
        }
        return result
    }

    suspend fun close() = withContext(Dispatchers.IO) { database.close() }
}
