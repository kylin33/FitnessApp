package com.kylin.fitnessapp.workout

data class SavedPlan(
    val id: String,
    val name: String,
    val text: String,
)

enum class AppTab {
    Home,
    Plans,
    Profile,
}

enum class WorkoutSoundEvent {
    CountdownTick,
    StageTransition,
    SessionComplete,
}

data class WorkoutTask(
    val name: String,
    val setInfo: String,
    val target: WorkoutTarget,
    val restSeconds: Int,
)

sealed interface WorkoutTarget {
    data class Time(val seconds: Int) : WorkoutTarget
    data class Reps(val text: String) : WorkoutTarget
}

enum class WorkoutStage {
    Idle,
    Preparing,
    Ready,
    Working,
    Resting,
    Completed,
    Aborted,
}

data class WorkoutUiState(
    val currentTab: AppTab = AppTab.Home,
    val planText: String = defaultPlanText(),
    val planName: String = PlanParser.inferPlanName(defaultPlanText()),
    val plans: List<SavedPlan> = emptyList(),
    val selectedPlanId: String? = null,
    val parsedTasks: List<WorkoutTask> = emptyList(),
    val activeTaskIndex: Int = 0,
    val stage: WorkoutStage = WorkoutStage.Idle,
    val statusText: String = "准备开始",
    val detailText: String = "点击下方开始训练",
    val planMessage: String? = null,
    val storageError: String? = null,
    val parseError: String? = null,
    val isLoadingPlans: Boolean = true,
    val prepRemainingSeconds: Int? = null,
    val workRemainingSeconds: Int? = null,
    val restRemainingSeconds: Int? = null,
    val isTrainingActive: Boolean = false,
    val isWorkPaused: Boolean = false,
    val isRestPaused: Boolean = false,
    val isSoundEnabled: Boolean = true,
)

val WorkoutUiState.currentTask: WorkoutTask?
    get() = parsedTasks.getOrNull(activeTaskIndex)

val WorkoutUiState.selectedPlan: SavedPlan?
    get() = plans.firstOrNull { it.id == selectedPlanId }

val WorkoutUiState.primaryActionLabel: String
    get() = when (stage) {
        WorkoutStage.Idle -> "解析并开始训练"
        WorkoutStage.Preparing -> "准备中..."
        WorkoutStage.Ready -> "完成本组，开始休息"
        WorkoutStage.Working -> "计时中..."
        WorkoutStage.Resting -> "倒计时中..."
        WorkoutStage.Completed -> "重新开始"
        WorkoutStage.Aborted -> "重新开始"
    }

val WorkoutUiState.isPrimaryActionEnabled: Boolean
    get() = !isLoadingPlans && stage !in setOf(
        WorkoutStage.Preparing,
        WorkoutStage.Working,
        WorkoutStage.Resting,
    )

val WorkoutUiState.currentCountdownLabel: String?
    get() = when (stage) {
        WorkoutStage.Preparing -> prepRemainingSeconds?.let(::formatClock)
        WorkoutStage.Working -> workRemainingSeconds?.let(::formatClock)
        WorkoutStage.Resting -> restRemainingSeconds?.let(::formatClock)
        else -> null
    }

private fun formatClock(seconds: Int): String {
    val mins = seconds / 60
    val secs = seconds % 60
    return "%02d:%02d".format(mins, secs)
}

fun defaultPlanText(): String {
    return "俯卧撑 | 4组 | 力竭 | 休90\n下斜俯卧撑 | 3组 | 15次 | 休60"
}

fun defaultSavedPlan(): SavedPlan {
    return SavedPlan(
        id = "default",
        name = "示例计划",
        text = defaultPlanText(),
    )
}
