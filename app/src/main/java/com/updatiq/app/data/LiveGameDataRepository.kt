package com.updatiq.app.data

import com.google.gson.JsonObject
import com.google.gson.annotations.SerializedName
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.Url

private const val GITHUB_API = "https://api.github.com/"
private const val REPOSITORY = "repos/raeffsky/UPDATIQ/releases/tags/latest"

data class ReleaseAsset(
    val name: String,
    @SerializedName("updated_at") val updatedAt: String,
    val url: String,
    @SerializedName("browser_download_url") val browserDownloadUrl: String
)

data class ReleaseInfo(
    @SerializedName("tag_name") val tagName: String,
    val assets: List<ReleaseAsset>
)

interface UpdatiqReleaseApi {
    @GET(REPOSITORY)
    suspend fun latestRelease(): ReleaseInfo

    @GET
    suspend fun downloadAsset(
        @Url assetUrl: String,
        @Header("Accept") accept: String = "application/octet-stream"
    ): Response<JsonObject>
}

data class HeroMetric(
    val slug: String,
    val name: String,
    val tier: String?,
    val winRate: Double?,
    val pickRate: Double?,
    val banRate: Double?
)

data class LaneStats(
    val heroes: List<HeroMetric> = emptyList()
)

data class RankedDataset(
    @SerializedName("updatedAt") val updatedAt: String?,
    val lanes: Map<String, LaneStats> = emptyMap()
)

data class LiveDatasetResult(
    val ranked: RankedDataset?,
    val tournament: JsonObject?,
    val builds: JsonObject?,
    val counters: JsonObject?,
    val updatedAt: String,
    val sourceTag: String
)

class LiveGameDataRepository(
    private val api: UpdatiqReleaseApi = Retrofit.Builder()
        .baseUrl(GITHUB_API)
        .addConverterFactory(GsonConverterFactory.create())
        .build()
        .create(UpdatiqReleaseApi::class.java)
) {
    suspend fun fetchLatest(): Result<LiveDatasetResult> = withContext(Dispatchers.IO) {
        runCatching {
            val release = api.latestRelease()
            val assets = release.assets.associateBy { it.name }

            suspend fun asset(name: String): JsonObject? {
                val item = assets[name] ?: return null
                val response = api.downloadAsset(item.url)
                check(response.isSuccessful) { "Не удалось загрузить $name: HTTP ${response.code()}" }
                return response.body() ?: error("Пустой файл $name")
            }

            val rankedJson = asset("mlbbnexus-tiers.json")
            val ranked = rankedJson?.let {
                com.google.gson.Gson().fromJson(it, RankedDataset::class.java)
            }

            require(ranked == null || (ranked.lanes["all"]?.heroes?.size ?: 0) >= 20) {
                "Ранговый датасет не прошёл проверку структуры"
            }

            val tournament = asset("mlbb-tournament-tiers.json")
            val builds = asset("mlbb-hero-builds.json")
            val counters = asset("mlbb-hero-counters.json")

            require(tournament != null && builds != null && counters != null) {
                "В релизе отсутствует один из обязательных игровых датасетов"
            }
            require((tournament.getAsJsonArray("heroes")?.size() ?: 0) >= 10) {
                "Турнирный датасет неполный"
            }
            require((builds.getAsJsonArray("heroes")?.size() ?: 0) >= 20) {
                "Датасет сборок неполный"
            }
            require((counters.getAsJsonObject("heroes")?.size() ?: 0) >= 100) {
                "Датасет контрпиков неполный"
            }

            val updatedAt = assets.values.maxOfOrNull { it.updatedAt }.orEmpty()
            LiveDatasetResult(ranked, tournament, builds, counters, updatedAt, release.tagName)
        }
    }

    companion object {
        fun createApi(): UpdatiqReleaseApi = Retrofit.Builder()
            .baseUrl(GITHUB_API)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(UpdatiqReleaseApi::class.java)
    }
}
