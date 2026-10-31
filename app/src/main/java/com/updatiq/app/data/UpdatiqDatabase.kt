package com.updatiq.app.data

import androidx.room.Dao
import androidx.room.Database
import androidx.room.Entity
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.PrimaryKey
import androidx.room.Query
import androidx.room.RoomDatabase

@Entity(tableName = "cached_game_datasets")
data class CachedDatasetEntity(
    @PrimaryKey val datasetId: String,
    val jsonPayload: String,
    val sourceUpdatedAt: String,
    val cachedAtEpochMs: Long
)

@Dao
interface CachedDatasetDao {
    @Query("SELECT * FROM cached_game_datasets")
    suspend fun getAll(): List<CachedDatasetEntity>

    @Query("SELECT * FROM cached_game_datasets WHERE datasetId = :id LIMIT 1")
    suspend fun get(id: String): CachedDatasetEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun put(dataset: CachedDatasetEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun putAll(datasets: List<CachedDatasetEntity>)

    @Query("DELETE FROM cached_game_datasets WHERE datasetId NOT IN (:keepIds)")
    suspend fun keepOnly(keepIds: List<String>)
}

@Database(
    entities = [CachedDatasetEntity::class],
    version = 1,
    exportSchema = true
)
abstract class UpdatiqDatabase : RoomDatabase() {
    abstract fun cachedDatasetDao(): CachedDatasetDao
}
