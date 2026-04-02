package com.kylin.fitnessapp.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.kylin.fitnessapp.workout.AppTab
import com.kylin.fitnessapp.workout.SavedPlan
import com.kylin.fitnessapp.workout.WorkoutStage
import com.kylin.fitnessapp.workout.WorkoutUiState
import com.kylin.fitnessapp.workout.WorkoutViewModel
import com.kylin.fitnessapp.workout.currentCountdownLabel
import com.kylin.fitnessapp.workout.isPrimaryActionEnabled
import com.kylin.fitnessapp.workout.primaryActionLabel
import com.kylin.fitnessapp.workout.selectedPlan
import kotlinx.coroutines.flow.collectLatest

@Composable
fun FitnessApp(workoutViewModel: WorkoutViewModel) {
    val uiState by workoutViewModel.uiState.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val soundPlayer = remember(context) { PromptSoundPlayer(context) }

    DisposableEffect(soundPlayer) {
        onDispose { soundPlayer.release() }
    }

    LaunchedEffect(workoutViewModel, soundPlayer) {
        workoutViewModel.soundEvents.collectLatest { event ->
            soundPlayer.play(event)
        }
    }

    MaterialTheme {
        Scaffold(
            bottomBar = {
                NavigationBar {
                    NavigationBarItem(
                        selected = uiState.currentTab == AppTab.Home,
                        onClick = { workoutViewModel.selectTab(AppTab.Home) },
                        icon = {
                            TabDot(selected = uiState.currentTab == AppTab.Home)
                        },
                        label = { Text("训练") },
                    )
                    NavigationBarItem(
                        selected = uiState.currentTab == AppTab.Plans,
                        onClick = { workoutViewModel.selectTab(AppTab.Plans) },
                        icon = {
                            TabDot(selected = uiState.currentTab == AppTab.Plans)
                        },
                        label = { Text("计划") },
                    )
                    NavigationBarItem(
                        selected = uiState.currentTab == AppTab.Profile,
                        onClick = { workoutViewModel.selectTab(AppTab.Profile) },
                        icon = {
                            TabDot(selected = uiState.currentTab == AppTab.Profile)
                        },
                        label = { Text("我的") },
                    )
                }
            }
        ) { innerPadding ->
            Surface(modifier = Modifier.fillMaxSize()) {
                when (uiState.currentTab) {
                    AppTab.Home -> TrainingScreen(
                        uiState = uiState,
                        innerPadding = innerPadding,
                        onOpenPlansTab = { workoutViewModel.selectTab(AppTab.Plans) },
                        onPrimaryAction = workoutViewModel::onPrimaryAction,
                        onAbortTraining = workoutViewModel::abortTraining,
                        onToggleRestPause = workoutViewModel::toggleRestPause,
                        onSkipRest = workoutViewModel::skipRest,
                        onToggleWorkPause = workoutViewModel::toggleWorkPause,
                        onFinishWorkEarly = workoutViewModel::finishWorkEarly,
                    )

                    AppTab.Plans -> PlansScreen(
                        uiState = uiState,
                        innerPadding = innerPadding,
                        onSelectPlan = workoutViewModel::selectPlan,
                        onLoadSelectedPlan = workoutViewModel::loadSelectedPlan,
                        onSaveAsNew = workoutViewModel::saveCurrentPlanAsNew,
                        onUpdateSelectedPlan = workoutViewModel::updateSelectedPlan,
                        onDeleteSelectedPlan = workoutViewModel::deleteSelectedPlan,
                        onPlanTextChange = workoutViewModel::updatePlanText,
                    )

                    AppTab.Profile -> ProfileScreen(
                        uiState = uiState,
                        innerPadding = innerPadding,
                        onSoundEnabledChange = workoutViewModel::setSoundEnabled,
                    )
                }
            }
        }
    }
}

@Composable
private fun TrainingScreen(
    uiState: WorkoutUiState,
    innerPadding: PaddingValues,
    onOpenPlansTab: () -> Unit,
    onPrimaryAction: () -> Unit,
    onAbortTraining: () -> Unit,
    onToggleRestPause: () -> Unit,
    onSkipRest: () -> Unit,
    onToggleWorkPause: () -> Unit,
    onFinishWorkEarly: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(innerPadding)
            .padding(horizontal = 18.dp, vertical = 20.dp)
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Text(
            text = "自律即自由",
            style = MaterialTheme.typography.labelLarge,
            color = MaterialTheme.colorScheme.primary,
        )
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.primaryContainer,
            ),
        ) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                Text(text = "当前计划", style = MaterialTheme.typography.labelLarge)
                Text(text = uiState.planName, style = MaterialTheme.typography.titleLarge)
                Text(
                    text = "编辑计划请前往“计划”页",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }

        Text(text = uiState.statusText, style = MaterialTheme.typography.headlineMedium)
        Text(text = uiState.detailText, style = MaterialTheme.typography.bodyLarge)

        uiState.currentCountdownLabel?.let { countdown ->
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.secondaryContainer,
                ),
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 24.dp),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(
                        text = countdown,
                        style = MaterialTheme.typography.displayMedium,
                        fontWeight = FontWeight.Bold,
                    )
                }
            }
        }

        if (!uiState.isTrainingActive) {
            OutlinedButton(onClick = onOpenPlansTab) {
                Text("去计划页编辑")
            }
        } else {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.surfaceVariant,
                ),
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    Text(
                        text = "专注模式",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold,
                    )
                    Text(
                        text = "训练进行中，已隐藏计划编辑入口。",
                        style = MaterialTheme.typography.bodyMedium,
                    )
                }
            }
        }

        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Button(
                onClick = onPrimaryAction,
                enabled = uiState.isPrimaryActionEnabled,
            ) {
                Text(uiState.primaryActionLabel)
            }
            OutlinedButton(
                onClick = onAbortTraining,
                enabled = uiState.isTrainingActive,
            ) {
                Text("终止训练")
            }
        }

        when (uiState.stage) {
            WorkoutStage.Resting -> {
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Button(onClick = onToggleRestPause) {
                        Text(if (uiState.isRestPaused) "继续休息" else "暂停休息")
                    }
                    OutlinedButton(onClick = onSkipRest) {
                        Text("跳过休息")
                    }
                }
            }

            WorkoutStage.Working -> {
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Button(onClick = onToggleWorkPause) {
                        Text(if (uiState.isWorkPaused) "继续动作" else "暂停动作")
                    }
                    OutlinedButton(onClick = onFinishWorkEarly) {
                        Text("结束本组")
                    }
                }
            }

            else -> Unit
        }

        uiState.planMessage?.let {
            Text(text = it, color = MaterialTheme.colorScheme.primary)
        }
        uiState.parseError?.let {
            Text(text = it, color = MaterialTheme.colorScheme.error)
        }
        uiState.storageError?.let {
            Text(text = it, color = MaterialTheme.colorScheme.error)
        }
    }
}

@Composable
private fun PlansScreen(
    uiState: WorkoutUiState,
    innerPadding: PaddingValues,
    onSelectPlan: (String) -> Unit,
    onLoadSelectedPlan: () -> Unit,
    onSaveAsNew: () -> Unit,
    onUpdateSelectedPlan: () -> Unit,
    onDeleteSelectedPlan: () -> Unit,
    onPlanTextChange: (String) -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(innerPadding)
            .padding(horizontal = 18.dp, vertical = 20.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Text(text = "计划管理", style = MaterialTheme.typography.headlineSmall)
        Text(
            text = "选择历史计划，加载到训练页后即可直接开始训练。",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        OutlinedTextField(
            value = uiState.planText,
            onValueChange = onPlanTextChange,
            modifier = Modifier.fillMaxWidth(),
            minLines = 6,
            label = { Text("计划文本") },
        )

        uiState.selectedPlan?.let { plan ->
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.primaryContainer,
                ),
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    Text(text = "当前选择", style = MaterialTheme.typography.labelLarge)
                    Text(text = plan.name, style = MaterialTheme.typography.titleLarge)
                    Text(
                        text = plan.text.lineSequence().firstOrNull().orEmpty(),
                        style = MaterialTheme.typography.bodyMedium,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
        }

        LazyColumn(
            modifier = Modifier.weight(1f),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            items(uiState.plans, key = { it.id }) { plan ->
                PlanListItem(
                    plan = plan,
                    isSelected = uiState.selectedPlanId == plan.id,
                    onClick = { onSelectPlan(plan.id) },
                )
            }
        }

        HorizontalDivider()

        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Button(
                onClick = onLoadSelectedPlan,
                enabled = uiState.selectedPlanId != null,
            ) {
                Text("加载到训练页")
            }
            OutlinedButton(onClick = onSaveAsNew, enabled = !uiState.isLoadingPlans) {
                Text("保存为新计划")
            }
        }

        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Button(
                onClick = onUpdateSelectedPlan,
                enabled = uiState.selectedPlanId != null,
            ) {
                Text("保存修改")
            }
            OutlinedButton(
                onClick = onDeleteSelectedPlan,
                enabled = uiState.selectedPlanId != null,
            ) {
                Text("删除计划")
            }
        }

        uiState.planMessage?.let {
            Text(text = it, color = MaterialTheme.colorScheme.primary)
        }
        uiState.storageError?.let {
            Text(text = it, color = MaterialTheme.colorScheme.error)
        }
    }
}

@Composable
private fun ProfileScreen(
    uiState: WorkoutUiState,
    innerPadding: PaddingValues,
    onSoundEnabledChange: (Boolean) -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(innerPadding)
            .padding(horizontal = 18.dp, vertical = 20.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Text(text = "我的", style = MaterialTheme.typography.headlineSmall)

        Card(modifier = Modifier.fillMaxWidth()) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 12.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text("提示音", style = MaterialTheme.typography.titleMedium)
                    Text(
                        text = "倒计时与阶段切换时播放 ding.wav",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                Switch(
                    checked = uiState.isSoundEnabled,
                    onCheckedChange = onSoundEnabledChange,
                )
            }
        }

        Card(modifier = Modifier.fillMaxWidth()) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Text(text = "训练概览", style = MaterialTheme.typography.titleMedium)
                Text(text = "计划总数：${uiState.plans.size}")
                Text(text = "当前计划：${uiState.planName}")
                Text(text = "当前状态：${uiState.statusText}")
            }
        }

        uiState.storageError?.let {
            Text(text = it, color = MaterialTheme.colorScheme.error)
        }
    }
}

@Composable
private fun PlanListItem(
    plan: SavedPlan,
    isSelected: Boolean,
    onClick: () -> Unit,
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        colors = CardDefaults.cardColors(
            containerColor = if (isSelected) {
                MaterialTheme.colorScheme.secondaryContainer
            } else {
                MaterialTheme.colorScheme.surface
            }
        ),
        border = androidx.compose.foundation.BorderStroke(
            width = 1.dp,
            color = if (isSelected) {
                MaterialTheme.colorScheme.primary.copy(alpha = 0.4f)
            } else {
                MaterialTheme.colorScheme.outlineVariant
            }
        ),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(14.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                modifier = Modifier
                    .size(14.dp)
                    .clip(CircleShape)
                    .background(
                        if (isSelected) {
                            MaterialTheme.colorScheme.primary
                        } else {
                            MaterialTheme.colorScheme.outlineVariant
                        }
                    )
            )
            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                Text(text = plan.name, style = MaterialTheme.typography.titleMedium)
                Text(
                    text = plan.text.lineSequence().firstOrNull().orEmpty(),
                    style = MaterialTheme.typography.bodyMedium,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Text(
                text = plan.id,
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun TabDot(selected: Boolean) {
    Box(
        modifier = Modifier
            .size(10.dp)
            .clip(RoundedCornerShape(999.dp))
            .background(
                if (selected) {
                    MaterialTheme.colorScheme.primary
                } else {
                    MaterialTheme.colorScheme.outlineVariant
                }
            )
    )
}
