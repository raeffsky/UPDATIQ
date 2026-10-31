package com.updatiq.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

private val Canvas = Color(0xFF080A10)
private val SurfaceA = Color(0xFF111621)
private val SurfaceB = Color(0xFF171E2B)
private val Line = Color(0xFF252E3D)
private val Ink = Color(0xFFF4F6FA)
private val SecondaryInk = Color(0xFF8792A5)
private val Accent = Color(0xFFB5F36A)
private val Blue = Color(0xFF75B9FF)
private val Violet = Color(0xFF9B83FF)

class NativeMainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = android.graphics.Color.rgb(8, 10, 16)
        window.navigationBarColor = android.graphics.Color.rgb(8, 10, 16)
        window.decorView.systemUiVisibility = 0
        setContent { UpdatiqApp() }
    }
}

private enum class AppTab(val label: String, val icon: ImageVector) {
    HOME("Обзор", Icons.Filled.Dashboard),
    NEWS("Лента", Icons.Filled.Bolt),
    META("Мета", Icons.Filled.QueryStats),
    HEROES("Герои", Icons.Filled.Shield),
    COACH("Тренер", Icons.Filled.School)
}

@Composable
private fun UpdatiqApp() {
    var selected by remember { mutableStateOf(AppTab.HOME) }
    MaterialTheme(colorScheme = darkColorScheme(
        primary = Accent, secondary = Blue, background = Canvas, surface = SurfaceA,
        onBackground = Ink, onSurface = Ink
    )) {
        Scaffold(
            containerColor = Canvas,
            bottomBar = { TacticalNavigation(selected) { selected = it } }
        ) { padding ->
            Box(Modifier.fillMaxSize().padding(padding).background(Canvas)) {
                when (selected) {
                    AppTab.HOME -> OverviewScreen(
                        onOpen = { selected = it },
                        onSearch = { selected = AppTab.HEROES }
                    )
                    AppTab.NEWS -> FeedScreen()
                    AppTab.META -> MetaScreen()
                    AppTab.HEROES -> HeroesScreen()
                    AppTab.COACH -> CoachScreen()
                }
            }
        }
    }
}

@Composable
private fun TacticalNavigation(selected: AppTab, onSelect: (AppTab) -> Unit) {
    Row(
        Modifier.fillMaxWidth().background(Color(0xFF0D121B))
            .border(width = 1.dp, color = Line.copy(alpha = .7f))
            .navigationBarsPadding().padding(horizontal = 8.dp, vertical = 9.dp),
        horizontalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        AppTab.entries.forEach { tab ->
            val active = selected == tab
            Column(
                Modifier.weight(1f).clip(RoundedCornerShape(15.dp))
                    .background(if (active) Accent.copy(alpha = .13f) else Color.Transparent)
                    .clickable { onSelect(tab) }.padding(vertical = 8.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                Icon(tab.icon, null, tint = if (active) Accent else SecondaryInk, modifier = Modifier.size(21.dp))
                Text(tab.label, color = if (active) Ink else SecondaryInk, fontSize = 10.sp,
                    fontWeight = if (active) FontWeight.Bold else FontWeight.Medium)
            }
        }
    }
}

@Composable
private fun ScreenHeader(section: String, actionIcon: ImageVector? = null, onAction: (() -> Unit)? = null) {
    Row(Modifier.fillMaxWidth().padding(horizontal = 22.dp, vertical = 18.dp), verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f)) {
            Text("UPDATIQ", color = Ink, fontSize = 22.sp, fontWeight = FontWeight.Black, letterSpacing = 2.2.sp)
            Text(section.uppercase(), color = SecondaryInk, fontSize = 9.sp, fontWeight = FontWeight.Bold, letterSpacing = 2.sp)
        }
        if (actionIcon != null && onAction != null) {
            Box(Modifier.size(42.dp).clip(CircleShape).background(SurfaceB).clickable { onAction() }, contentAlignment = Alignment.Center) {
                Icon(actionIcon, null, tint = Ink, modifier = Modifier.size(19.dp))
            }
        }
    }
}

@Composable
private fun OverviewScreen(onOpen: (AppTab) -> Unit, onSearch: () -> Unit) {
    LazyColumn(
        Modifier.fillMaxSize(),
        contentPadding = PaddingValues(bottom = 22.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp)
    ) {
        item { ScreenHeader("MOBILE LEGENDS INTELLIGENCE", Icons.Filled.Search, onSearch) }
        item {
            Column(Modifier.padding(horizontal = 22.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                    Box(Modifier.size(7.dp).clip(CircleShape).background(Accent))
                    Text("TACTICAL INTELLIGENCE / 02", color = Accent, fontSize = 9.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.5.sp)
                }
                Spacer(Modifier.height(10.dp))
                Text("Побеждай
с пониманием.", color = Ink, fontSize = 34.sp, lineHeight = 38.sp, fontWeight = FontWeight.Black)
                Spacer(Modifier.height(7.dp))
                Text("Мета, пики и аналитика MLBB без лишнего шума.", color = SecondaryInk, fontSize = 13.sp)
            }
        }
        item {
            Box(Modifier.padding(horizontal = 18.dp).fillMaxWidth().clip(RoundedCornerShape(25.dp))
                .background(Brush.linearGradient(listOf(Color(0xFF253328), Color(0xFF18231F), Color(0xFF111923))))
                .border(1.dp, Accent.copy(alpha = .25f), RoundedCornerShape(25.dp))) {
                Column(Modifier.padding(20.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("META RADAR", color = Accent, fontSize = 10.sp, fontWeight = FontWeight.Black, letterSpacing = 2.sp)
                        Spacer(Modifier.weight(1f))
                        Text("LIVE DATA", color = Accent, fontSize = 9.sp, fontWeight = FontWeight.Bold,
                            modifier = Modifier.border(1.dp, Accent.copy(alpha = .35f), CircleShape).padding(horizontal = 9.dp, vertical = 5.dp))
                    }
                    Spacer(Modifier.height(24.dp))
                    Text("Мета меняется.\nБудь на шаг впереди.", color = Ink, fontSize = 24.sp, lineHeight = 28.sp, fontWeight = FontWeight.Bold)
                    Spacer(Modifier.height(8.dp))
                    Text("Отслеживай силу героев, приоритеты пиков и контрпики на основе актуальных данных.", color = Color(0xFFB0BBAF), fontSize = 12.sp, lineHeight = 18.sp)
                    Spacer(Modifier.height(20.dp))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Button(onClick = { onOpen(AppTab.META) }, colors = ButtonDefaults.buttonColors(containerColor = Accent, contentColor = Color(0xFF10170F)),
                            shape = RoundedCornerShape(12.dp), contentPadding = PaddingValues(horizontal = 17.dp, vertical = 11.dp)) {
                            Text("Открыть аналитику", fontWeight = FontWeight.Bold, fontSize = 12.sp)
                            Spacer(Modifier.width(8.dp)); Icon(Icons.Filled.ArrowForward, null, modifier = Modifier.size(15.dp))
                        }
                        Spacer(Modifier.weight(1f))
                        Icon(Icons.Filled.Radar, null, tint = Accent.copy(alpha = .65f), modifier = Modifier.size(48.dp))
                    }
                }
            }
        }
        item { SectionHeading("РАЗВЕДКА", "Инструменты") }
        item { FeatureRow("Лента обновлений", "Патчи, события и новости сообщества", Icons.Filled.Bolt, Blue) { onOpen(AppTab.NEWS) } }
        item { FeatureRow("База героев", "Навыки, сборки и контрпики", Icons.Filled.Shield, Violet) { onOpen(AppTab.HEROES) } }
        item { FeatureRow("Draft Intelligence", "Подбор пиков под вражеский состав", Icons.Filled.Psychology, Accent) { onOpen(AppTab.META) } }
        item { FeatureRow("Персональный тренер", "Разбор матчей и игровые привычки", Icons.Filled.School, Color(0xFFFFB86B)) { onOpen(AppTab.COACH) } }
        item {
            Row(Modifier.fillMaxWidth().padding(horizontal = 22.dp, vertical = 3.dp), verticalAlignment = Alignment.CenterVertically) {
                Text("UPDATIQ 2.0", color = SecondaryInk, fontSize = 9.sp, letterSpacing = 1.5.sp)
                Spacer(Modifier.weight(1f))
                Text("BUILT FOR BETTER DECISIONS", color = SecondaryInk.copy(alpha = .65f), fontSize = 8.sp, letterSpacing = 1.sp)
            }
        }
    }
}

@Composable
private fun SectionHeading(kicker: String, title: String) {
    Column(Modifier.padding(horizontal = 22.dp)) {
        Text(kicker, color = Accent, fontSize = 9.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.8.sp)
        Spacer(Modifier.height(4.dp))
        Text(title, color = Ink, fontSize = 19.sp, fontWeight = FontWeight.Bold)
    }
}

@Composable
private fun FeatureRow(title: String, subtitle: String, icon: ImageVector, tint: Color, onClick: () -> Unit) {
    Row(Modifier.padding(horizontal = 18.dp).fillMaxWidth().clip(RoundedCornerShape(18.dp))
        .background(SurfaceA).border(1.dp, Line.copy(alpha = .65f), RoundedCornerShape(18.dp))
        .clickable { onClick() }.padding(15.dp), verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.size(44.dp).clip(RoundedCornerShape(13.dp)).background(tint.copy(alpha = .13f)), contentAlignment = Alignment.Center) {
            Icon(icon, null, tint = tint, modifier = Modifier.size(22.dp))
        }
        Spacer(Modifier.width(13.dp))
        Column(Modifier.weight(1f)) {
            Text(title, color = Ink, fontWeight = FontWeight.Bold, fontSize = 14.sp)
            Spacer(Modifier.height(4.dp))
            Text(subtitle, color = SecondaryInk, fontSize = 10.sp, maxLines = 2, overflow = TextOverflow.Ellipsis)
        }
        Icon(Icons.Filled.ArrowOutward, null, tint = SecondaryInk, modifier = Modifier.size(17.dp))
    }
}

@Composable
private fun PageIntro(kicker: String, title: String, subtitle: String, icon: ImageVector) {
    ScreenHeader(kicker)
    Column(Modifier.padding(horizontal = 22.dp)) {
        Icon(icon, null, tint = Accent, modifier = Modifier.size(28.dp))
        Spacer(Modifier.height(10.dp))
        Text(title, color = Ink, fontSize = 30.sp, fontWeight = FontWeight.Black)
        Spacer(Modifier.height(5.dp))
        Text(subtitle, color = SecondaryInk, fontSize = 12.sp, lineHeight = 18.sp)
    }
}

@Composable
private fun DataPanel(title: String, subtitle: String, icon: ImageVector, tint: Color = Accent) {
    Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(18.dp)).background(SurfaceA)
        .border(1.dp, Line.copy(alpha = .7f), RoundedCornerShape(18.dp)).padding(16.dp),
        verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.size(42.dp).clip(RoundedCornerShape(12.dp)).background(tint.copy(alpha = .13f)), contentAlignment = Alignment.Center) {
            Icon(icon, null, tint = tint)
        }
        Spacer(Modifier.width(13.dp))
        Column(Modifier.weight(1f)) {
            Text(title, color = Ink, fontWeight = FontWeight.Bold, fontSize = 14.sp)
            Spacer(Modifier.height(4.dp))
            Text(subtitle, color = SecondaryInk, fontSize = 11.sp, lineHeight = 16.sp)
        }
        Icon(Icons.Filled.ChevronRight, null, tint = SecondaryInk)
    }
}

@Composable
private fun FeedScreen() {
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = 24.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        item { PageIntro("INTEL FEED", "Лента событий", "Важные изменения MLBB в одном потоке.", Icons.Filled.Bolt) }
        item { StatusStrip("Источники обновляются автоматически") }
        item { DataPanel("Официальные патчи", "Изменения баланса, обновления клиента и события", Icons.Filled.Campaign, Blue) }
        item { DataPanel("Новости сообщества", "Публикации и материалы UPDATIQ", Icons.Filled.Forum, Violet) }
        item { DataPanel("История обновлений", "Архив изменений и предыдущих версий патчей", Icons.Filled.History, Accent) }
    }
}

@Composable
private fun MetaScreen() {
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = 24.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        item { PageIntro("META LAB", "Анализ меты", "Сравнивай приоритеты и принимай решения на основе данных.", Icons.Filled.QueryStats) }
        item { StatusStrip("Источники статистики подключаются к аналитике") }
        item { DataPanel("Meta Radar", "Изменения эффективности и динамика героев", Icons.Filled.Radar, Accent) }
        item { DataPanel("Тир-листы", "Рейтинги по линиям и игровым ролям", Icons.Filled.Leaderboard, Violet) }
        item { DataPanel("Draft Intelligence", "Контрпики и синергия состава", Icons.Filled.Psychology, Blue) }
        item { DataPanel("Турнирная мета", "Пики и баны профессиональной сцены", Icons.Filled.EmojiEvents, Color(0xFFFFB86B)) }
    }
}

@Composable
private fun HeroesScreen() {
    var query by remember { mutableStateOf("") }
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = 24.dp), verticalArrangement = Arrangement.spacedBy(13.dp)) {
        item { PageIntro("HERO DATABASE", "База героев", "Сборки, навыки и матчапы в одном месте.", Icons.Filled.Shield) }
        item {
            OutlinedTextField(value = query, onValueChange = { query = it }, modifier = Modifier.padding(horizontal = 18.dp).fillMaxWidth(),
                placeholder = { Text("Найти героя", color = SecondaryInk) }, leadingIcon = { Icon(Icons.Filled.Search, null, tint = SecondaryInk) },
                singleLine = true, shape = RoundedCornerShape(14.dp), colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = Accent, unfocusedBorderColor = Line, focusedTextColor = Ink, unfocusedTextColor = Ink))
        }
        item { StatusStrip("Каталог будет заполнен актуальными данными героев") }
        item { DataPanel("Профили героев", "Роли, специализации и способности", Icons.Filled.PersonSearch, Violet) }
        item { DataPanel("Сборки предметов", "Порядок покупки и варианты экипировки", Icons.Filled.Backpack, Accent) }
        item { DataPanel("Контрпики", "Сильные и слабые матчапы", Icons.Filled.CompareArrows, Blue) }
        item { DataPanel("Навыки", "Описание умений и порядок прокачки", Icons.Filled.AutoAwesome, Color(0xFFFFB86B)) }
    }
}

@Composable
private fun CoachScreen() {
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = 24.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        item { PageIntro("PLAYER DEVELOPMENT", "Твой тренер", "Разбирай матчи, находи ошибки и отслеживай прогресс.", Icons.Filled.School) }
        item { StatusStrip("Персональная аналитика строится на твоих разборах матчей") }
        item { DataPanel("Новый разбор", "Добавь результат матча и ключевые детали игры", Icons.Filled.AddChart, Accent) }
        item { DataPanel("История матчей", "Сохраняй разборы и сравнивай результаты", Icons.Filled.History, Blue) }
        item { DataPanel("Зоны роста", "Повторяющиеся ошибки и персональные советы", Icons.Filled.Insights, Violet) }
    }
}

@Composable
private fun StatusStrip(text: String) {
    Row(Modifier.padding(horizontal = 18.dp).fillMaxWidth().clip(RoundedCornerShape(12.dp))
        .background(Color(0xFF151D19)).border(1.dp, Accent.copy(alpha = .2f), RoundedCornerShape(12.dp)).padding(12.dp),
        verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.size(7.dp).clip(CircleShape).background(Accent))
        Spacer(Modifier.width(9.dp))
        Text(text, color = Color(0xFFB7C5B3), fontSize = 10.sp, lineHeight = 14.sp)
    }
}
