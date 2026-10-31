package com.updatiq.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

private val Night = Color(0xFF080B13)
private val Panel = Color(0xFF111827)
private val Muted = Color(0xFF8C98AE)
private val Violet = Color(0xFF9B72F2)
private val Cyan = Color(0xFF65D6E8)

class NativeMainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = android.graphics.Color.rgb(8, 11, 19)
        window.navigationBarColor = android.graphics.Color.rgb(8, 11, 19)
        window.decorView.systemUiVisibility = 0
        setContent { UpdatiqApp() }
    }
}

private enum class AppTab(val title: String) {
    HOME("Главная"), NEWS("Новости"), META("Мета"), HEROES("Герои"), COACH("Тренер")
}

@Composable
private fun UpdatiqApp() {
    var selected by remember { mutableStateOf(AppTab.HOME) }
    MaterialTheme(
        colorScheme = darkColorScheme(
            primary = Violet,
            secondary = Cyan,
            background = Night,
            surface = Panel,
            onBackground = Color.White,
            onSurface = Color.White
        )
    ) {
        Scaffold(
            containerColor = Night,
            bottomBar = {
                NavigationBar(containerColor = Color(0xFF0D1320), tonalElevation = 0.dp) {
                    AppTab.entries.forEach { tab ->
                        val icon = when (tab) {
                            AppTab.HOME -> Icons.Filled.Home
                            AppTab.NEWS -> Icons.Filled.Newspaper
                            AppTab.META -> Icons.Filled.Insights
                            AppTab.HEROES -> Icons.Filled.Shield
                            AppTab.COACH -> Icons.Filled.SportsEsports
                        }
                        NavigationBarItem(
                            selected = selected == tab,
                            onClick = { selected = tab },
                            icon = { Icon(icon, contentDescription = tab.title) },
                            label = { Text(tab.title, fontSize = 10.sp) },
                            colors = NavigationBarItemDefaults.colors(
                                selectedIconColor = Violet,
                                selectedTextColor = Color.White,
                                indicatorColor = Violet.copy(alpha = .16f),
                                unselectedIconColor = Muted,
                                unselectedTextColor = Muted
                            )
                        )
                    }
                }
            }
        ) { padding ->
            Column(
                Modifier.fillMaxSize().padding(padding)
                    .background(Brush.verticalGradient(listOf(Color(0xFF10182A), Night)))
            ) {
                TopBar()
                when (selected) {
                    AppTab.HOME -> HomeScreen(onOpen = { selected = it })
                    AppTab.NEWS -> ModuleScreen("Новости", "Лента обновлений Mobile Legends", "Официальные новости, патчи и публикации сообщества будут собраны здесь.")
                    AppTab.META -> ModuleScreen("Мета", "Статистика и решения по драфту", "Тир-листы, Meta Radar и Draft Intelligence.")
                    AppTab.HEROES -> ModuleScreen("Герои", "Полная база героев", "Профили, навыки, статистика, сборки и контрпики.")
                    AppTab.COACH -> ModuleScreen("Тренер", "Разбор твоей игры", "Персональные рекомендации и история матчей.")
                }
            }
        }
    }
}

@Composable
private fun TopBar() {
    Row(
        Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 16.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(Modifier.weight(1f)) {
            Text("UPDATIQ", fontSize = 22.sp, fontWeight = FontWeight.Black, letterSpacing = 2.sp)
            Text("MOBILE LEGENDS INTELLIGENCE", color = Muted, fontSize = 9.sp, letterSpacing = 1.5.sp)
        }
        Surface(shape = RoundedCornerShape(50), color = Violet.copy(alpha = .15f)) {
            Text("2.0 · NATIVE", Modifier.padding(horizontal = 11.dp, vertical = 7.dp), color = Violet, fontSize = 10.sp, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun HomeScreen(onOpen: (AppTab) -> Unit) {
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(start = 18.dp, end = 18.dp, bottom = 24.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        item {
            Column(Modifier.padding(top = 12.dp, bottom = 4.dp)) {
                Text("ЦЕНТР УПРАВЛЕНИЯ", color = Cyan, fontSize = 10.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.8.sp)
                Text("Играй умнее.", fontSize = 30.sp, fontWeight = FontWeight.Bold)
                Text("Всё важное по MLBB в одном месте.", color = Muted, fontSize = 13.sp)
            }
        }
        item {
            Surface(
                shape = RoundedCornerShape(22.dp),
                color = Panel,
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(Modifier.background(Brush.linearGradient(listOf(Color(0xFF242044), Panel))).padding(18.dp)) {
                    Text("META RADAR", color = Violet, fontSize = 10.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.5.sp)
                    Spacer(Modifier.height(8.dp))
                    Text("Следи за изменениями меты", fontSize = 20.sp, fontWeight = FontWeight.Bold)
                    Text("Рост и падение эффективности героев, актуальные пики и баны.", color = Muted, fontSize = 12.sp)
                    Spacer(Modifier.height(14.dp))
                    Button(onClick = { onOpen(AppTab.META) }, colors = ButtonDefaults.buttonColors(containerColor = Violet)) {
                        Text("Открыть мету")
                    }
                }
            }
        }
        item { SectionCard("Новости и патчи", "Последние изменения и официальные публикации", Icons.Filled.Newspaper) { onOpen(AppTab.NEWS) } }
        item { SectionCard("Герои и сборки", "Навыки, предметы, контрпики и статистика", Icons.Filled.Shield) { onOpen(AppTab.HEROES) } }
        item { SectionCard("Draft Intelligence", "Подбор пиков под состав противника", Icons.Filled.Psychology) { onOpen(AppTab.META) } }
        item { SectionCard("Персональный тренер", "Разбор матчей и зоны роста", Icons.Filled.SportsEsports) { onOpen(AppTab.COACH) } }
        item {
            Text("UPDATIQ 2.0 · Нативная версия на Kotlin", color = Muted, fontSize = 10.sp, modifier = Modifier.padding(top = 6.dp))
        }
    }
}

@Composable
private fun SectionCard(title: String, subtitle: String, icon: androidx.compose.ui.graphics.vector.ImageVector, onClick: () -> Unit) {
    Surface(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
        shape = RoundedCornerShape(18.dp),
        color = Panel
    ) {
        Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            Surface(shape = RoundedCornerShape(13.dp), color = Violet.copy(alpha = .14f)) {
                Icon(icon, null, Modifier.padding(11.dp).size(22.dp), tint = Violet)
            }
            Spacer(Modifier.width(13.dp))
            Column(Modifier.weight(1f)) {
                Text(title, fontWeight = FontWeight.SemiBold, fontSize = 15.sp)
                Spacer(Modifier.height(3.dp))
                Text(subtitle, color = Muted, fontSize = 11.sp)
            }
            Icon(Icons.Filled.ChevronRight, null, tint = Muted)
        }
    }
}

@Composable
private fun ModuleScreen(title: String, subtitle: String, description: String) {
    Column(Modifier.fillMaxSize().padding(20.dp)) {
        Text(title, fontSize = 28.sp, fontWeight = FontWeight.Bold)
        Text(subtitle, color = Cyan, fontSize = 12.sp)
        Spacer(Modifier.height(18.dp))
        Surface(shape = RoundedCornerShape(18.dp), color = Panel) {
            Column(Modifier.padding(18.dp)) {
                Text("Модуль UPDATIQ 2.0", color = Violet, fontWeight = FontWeight.Bold, fontSize = 11.sp)
                Spacer(Modifier.height(8.dp))
                Text(description, color = Muted, fontSize = 13.sp)
                Spacer(Modifier.height(14.dp))
                Text("Нативная основа готова. Подключение данных и функциональность будут добавляться отдельными модулями.", fontSize = 12.sp)
            }
        }
    }
}
