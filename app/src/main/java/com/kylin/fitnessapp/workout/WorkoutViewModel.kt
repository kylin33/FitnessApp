package com.kylin.fitnessapp.workout

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

class WorkoutViewModel(application: Application) : AndroidViewModel(application) {
    private val repository = PlanRepository(application.applicationContext)
    private val _uiState = MutableStateFlow(WorkoutUiState())
    val uiState: StateFlow<WorkoutUiState> = _uiState.asStateFlow()
    private val _soundEvents = MutableSharedFlow<WorkoutSoundEvent>(extraBufferCapacity = 16)
    val soundEvents: SharedFlow<WorkoutSoundEvent> = _soundEvents.asSharedFlow()

    private var countdownJob: Job? = null

    init {
        loadSavedPlans()
    }

    fun updatePlanText(text: String) {
        _uiState.update {
            it.copy(
                planText = text,
                planName = PlanParser.inferPlanName(text),
                parseError = null,
                planMessage = null,
            )
        }
    }

    fun selectTab(tab: AppTab) {
        _uiState.update { it.copy(currentTab = tab, planMessage = null, storageError = null) }
    }

    fun selectPlan(planId: String) {
        _uiState.update { it.copy(selectedPlanId = planId, planMessage = null, storageError = null) }
        persistSelectedPlan(planId)
    }

    fun setSoundEnabled(enabled: Boolean) {
        _uiState.update { it.copy(isSoundEnabled = enabled, storageError = null) }
        viewModelScope.launch {
            runCatching {
                repository.saveSoundEnabled(enabled)
            }.onFailure {
                _uiState.update { state ->
                    state.copy(storageError = "提示音设置保存失败")
                }
            }
        }
    }

    fun loadSelectedPlan() {
        val plan = _uiState.value.selectedPlan ?: return
        stopCountdown()
        _uiState.update { state ->
            resetTrainingState(
                state.copy(
                    currentTab = AppTab.Home,
                    selectedPlanId = plan.id,
                    planText = plan.text,
                    planName = plan.name,
                    planMessage = "计划已加载到训练页",
                    storageError = null,
                ),
                statusText = "准备开始",
                detailText = "计划已切换，可直接开始训练",
                stage = WorkoutStage.Idle,
            )
        }
        persistSelectedPlan(plan.id)
    }

    fun saveCurrentPlanAsNew() {
        val state = _uiState.value
        val planId = nextPlanId(state.plans)
        val text = state.planText
        val name = PlanParser.inferPlanName(text)
        val updatedPlans = (state.plans + SavedPlan(planId, name, text)).sortedBy { it.id }
        persistPlans(
            plans = updatedPlans,
            selectedPlanId = planId,
            onSuccess = {
                it.copy(
                    plans = updatedPlans,
                    selectedPlanId = planId,
                    planName = name,
                    planMessage = "已保存为新计划",
                    storageError = null,
                    currentTab = AppTab.Plans,
                )
            }
        )
    }

    fun updateSelectedPlan() {
        val state = _uiState.value
        val selectedPlanId = state.selectedPlanId ?: return
        val name = PlanParser.inferPlanName(state.planText)
        val updatedPlans = state.plans.map { plan ->
            if (plan.id == selectedPlanId) {
                plan.copy(name = name, text = state.planText)
            } else {
                plan
            }
        }.sortedBy { it.id }

        persistPlans(
            plans = updatedPlans,
            selectedPlanId = selectedPlanId,
            onSuccess = {
                it.copy(
                    plans = updatedPlans,
                    planName = name,
                    planMessage = "计划修改已保存",
                    storageError = null,
                    currentTab = AppTab.Plans,
                )
            }
        )
    }

    fun deleteSelectedPlan() {
        val state = _uiState.value
        val selectedPlanId = state.selectedPlanId ?: return
        val remainingPlans = state.plans.filterNot { it.id == selectedPlanId }
        val normalizedPlans = if (remainingPlans.isEmpty()) {
            listOf(defaultSavedPlan())
        } else {
            remainingPlans.sortedBy { it.id }
        }
        val nextSelectedPlan = normalizedPlans.first()

        persistPlans(
            plans = normalizedPlans,
            selectedPlanId = nextSelectedPlan.id,
            onSuccess = { current ->
                resetTrainingState(
                    current.copy(
                        plans = normalizedPlans,
                        selectedPlanId = nextSelectedPlan.id,
                        planText = nextSelectedPlan.text,
                        planName = nextSelectedPlan.name,
                        currentTab = AppTab.Home,
                        planMessage = "计划已删除",
                        storageError = null,
                    ),
                    statusText = "准备开始",
                    detailText = "计划已切换，可直接开始训练",
                    stage = WorkoutStage.Idle,
                )
            }
        )
    }

    fun onPrimaryAction() {
        when (_uiState.value.stage) {
            WorkoutStage.Idle,
            WorkoutStage.Completed,
            WorkoutStage.Aborted,
            -> parseAndStart()

            WorkoutStage.Ready -> completeCurrentTask()
            WorkoutStage.Preparing,
            WorkoutStage.Working,
            WorkoutStage.Resting,
            -> Unit
        }
    }

    fun abortTraining() {
        stopCountdown()
        _uiState.update {
            resetTrainingState(
                it.copy(
                    currentTab = AppTab.Home,
                    planMessage = null,
                    storageError = null,
                ),
                statusText = "已终止",
                detailText = "训练已终止，已返回训练页。",
                stage = WorkoutStage.Aborted,
            )
        }
    }

    fun toggleRestPause() {
        val state = _uiState.value
        if (state.stage != WorkoutStage.Resting) {
            return
        }
        _uiState.update { it.copy(isRestPaused = !it.isRestPaused) }
    }

    fun skipRest() {
        val state = _uiState.value
        if (state.stage != WorkoutStage.Resting) {
            return
        }
        stopCountdown()
        moveToNextTask()
    }

    fun toggleWorkPause() {
        val state = _uiState.value
        if (state.stage != WorkoutStage.Working) {
            return
        }
        _uiState.update { it.copy(isWorkPaused = !it.isWorkPaused) }
    }

    fun finishWorkEarly() {
        val state = _uiState.value
        if (state.stage != WorkoutStage.Working) {
            return
        }
        stopCountdown()
        startRestForCurrentTask()
    }

    private fun parseAndStart() {
        stopCountdown()
        val tasks = PlanParser.parse(_uiState.value.planText)
        if (tasks.isEmpty()) {
            _uiState.update {
                resetTrainingState(
                    it.copy(
                        parsedTasks = emptyList(),
                        activeTaskIndex = 0,
                        parseError = "未能解析出有效训练项",
                        planMessage = null,
                        storageError = null,
                    ),
                    statusText = "准备开始",
                    detailText = "文本格式错误，请检查！",
                    stage = WorkoutStage.Idle,
                )
            }
            return
        }

        _uiState.update {
            it.copy(
                parsedTasks = tasks,
                activeTaskIndex = 0,
                stage = WorkoutStage.Preparing,
                statusText = "准备动作...",
                detailText = prepDetail(tasks.first()),
                prepRemainingSeconds = 3,
                workRemainingSeconds = null,
                restRemainingSeconds = null,
                isTrainingActive = true,
                isWorkPaused = false,
                isRestPaused = false,
                parseError = null,
                planMessage = null,
                storageError = null,
            )
        }
        startPrepCountdown()
    }

    private fun completeCurrentTask() {
        val task = _uiState.value.currentTask ?: return
        when (val target = task.target) {
            is WorkoutTarget.Time -> {
                if (target.seconds > 0) {
                    startWorkTimer(target.seconds)
                } else {
                    startRestForCurrentTask()
                }
            }

            is WorkoutTarget.Reps -> startRestForCurrentTask()
        }
    }

    private fun startPrepCountdown() {
        val task = _uiState.value.currentTask ?: return
        stopCountdown()
        countdownJob = viewModelScope.launch {
            for (remaining in 3 downTo 1) {
                _uiState.update {
                    it.copy(
                        stage = WorkoutStage.Preparing,
                        statusText = "准备动作...",
                        detailText = prepDetail(task),
                        prepRemainingSeconds = remaining,
                        workRemainingSeconds = null,
                        restRemainingSeconds = null,
                    )
                }
                emitSound(WorkoutSoundEvent.CountdownTick)
                delay(1_000)
            }

            _uiState.update {
                it.copy(
                    stage = WorkoutStage.Ready,
                    statusText = task.name,
                    detailText = readyDetail(task),
                    prepRemainingSeconds = null,
                    workRemainingSeconds = null,
                    restRemainingSeconds = null,
                )
            }
        }
    }

    private fun startWorkTimer(seconds: Int) {
        stopCountdown()
        countdownJob = viewModelScope.launch {
            for (remaining in seconds downTo 0) {
                waitIfWorkPaused()
                _uiState.update {
                    it.copy(
                        stage = WorkoutStage.Working,
                        statusText = "动作计时中...",
                        detailText = "保持节奏",
                        prepRemainingSeconds = null,
                        workRemainingSeconds = remaining,
                        restRemainingSeconds = null,
                    )
                }
                if (remaining == 0) {
                    emitSound(WorkoutSoundEvent.StageTransition)
                }
                if (remaining > 0) {
                    delay(1_000)
                }
            }

            countdownJob = null
            startRestForCurrentTask()
        }
    }

    private fun startRestForCurrentTask() {
        val task = _uiState.value.currentTask ?: return
        val seconds = task.restSeconds
        if (seconds <= 0) {
            moveToNextTask()
            return
        }

        stopCountdown()
        countdownJob = viewModelScope.launch {
            for (remaining in seconds downTo 0) {
                waitIfRestPaused()
                _uiState.update {
                    it.copy(
                        stage = WorkoutStage.Resting,
                        statusText = "休息中...",
                        detailText = "深呼吸，准备下一组",
                        prepRemainingSeconds = null,
                        workRemainingSeconds = null,
                        restRemainingSeconds = remaining,
                    )
                }
                if (remaining == 0) {
                    emitSound(WorkoutSoundEvent.StageTransition)
                }
                if (remaining > 0) {
                    delay(1_000)
                }
            }

            countdownJob = null
            moveToNextTask()
        }
    }

    private fun moveToNextTask() {
        val state = _uiState.value
        val nextIndex = state.activeTaskIndex + 1
        val tasks = state.parsedTasks

        if (nextIndex >= tasks.size) {
            emitSound(WorkoutSoundEvent.SessionComplete)
            _uiState.update {
                resetTrainingState(
                    it.copy(activeTaskIndex = tasks.lastIndex.coerceAtLeast(0)),
                    statusText = "训练全部完成！",
                    detailText = "去喝点蛋白粉吧！",
                    stage = WorkoutStage.Completed,
                )
            }
            return
        }

        val nextTask = tasks[nextIndex]
        _uiState.update {
            it.copy(
                activeTaskIndex = nextIndex,
                stage = WorkoutStage.Preparing,
                statusText = "准备动作...",
                detailText = prepDetail(nextTask),
                prepRemainingSeconds = 3,
                workRemainingSeconds = null,
                restRemainingSeconds = null,
                isTrainingActive = true,
                isWorkPaused = false,
                isRestPaused = false,
            )
        }
        startPrepCountdown()
    }

    private suspend fun waitIfWorkPaused() {
        while (_uiState.value.isWorkPaused) {
            delay(100)
        }
    }

    private suspend fun waitIfRestPaused() {
        while (_uiState.value.isRestPaused) {
            delay(100)
        }
    }

    private fun stopCountdown() {
        countdownJob?.cancel()
        countdownJob = null
    }

    private fun loadSavedPlans() {
        viewModelScope.launch {
            try {
                val snapshot = repository.loadSnapshot()
                val resolved = resolvePlans(snapshot.plans, snapshot.lastPlanId)
                if (resolved.shouldPersist) {
                    repository.saveSnapshot(resolved.plans, resolved.selectedPlan.id)
                }
                _uiState.update {
                    resetTrainingState(
                        it.copy(
                            plans = resolved.plans,
                            selectedPlanId = resolved.selectedPlan.id,
                            planText = resolved.selectedPlan.text,
                            planName = resolved.selectedPlan.name,
                            currentTab = AppTab.Home,
                            isLoadingPlans = false,
                            isSoundEnabled = snapshot.isSoundEnabled,
                            planMessage = null,
                            storageError = null,
                            parseError = null,
                        ),
                        statusText = "准备开始",
                        detailText = "点击下方开始训练",
                        stage = WorkoutStage.Idle,
                    )
                }
            } catch (_: Exception) {
                val fallbackPlan = defaultSavedPlan()
                _uiState.update {
                    resetTrainingState(
                        it.copy(
                            plans = listOf(fallbackPlan),
                            selectedPlanId = fallbackPlan.id,
                            planText = fallbackPlan.text,
                            planName = fallbackPlan.name,
                            currentTab = AppTab.Home,
                            isLoadingPlans = false,
                            isSoundEnabled = true,
                            planMessage = null,
                            storageError = "计划存储读取失败，已使用内置默认计划",
                            parseError = null,
                        ),
                        statusText = "准备开始",
                        detailText = "点击下方开始训练",
                        stage = WorkoutStage.Idle,
                    )
                }
            }
        }
    }

    private fun persistSelectedPlan(planId: String) {
        viewModelScope.launch {
            runCatching {
                repository.saveSnapshot(_uiState.value.plans, planId)
            }.onFailure {
                _uiState.update { state ->
                    state.copy(storageError = "计划选择保存失败")
                }
            }
        }
    }

    private fun persistPlans(
        plans: List<SavedPlan>,
        selectedPlanId: String,
        onSuccess: (WorkoutUiState) -> WorkoutUiState,
    ) {
        viewModelScope.launch {
            runCatching {
                repository.saveSnapshot(plans, selectedPlanId)
            }.onSuccess {
                _uiState.update { current ->
                    onSuccess(current).copy(isLoadingPlans = false, parseError = null)
                }
            }.onFailure {
                _uiState.update { current ->
                    current.copy(storageError = "计划存储写入失败")
                }
            }
        }
    }

    private fun resolvePlans(
        plans: List<SavedPlan>,
        lastPlanId: String?,
    ): ResolvedPlans {
        val normalizedPlans = plans
            .distinctBy { it.id }
            .map { plan ->
                plan.copy(name = plan.name.ifEmpty { PlanParser.inferPlanName(plan.text) })
            }
            .sortedBy { it.id }
            .ifEmpty { listOf(defaultSavedPlan()) }

        val selectedPlan = normalizedPlans.firstOrNull { it.id == lastPlanId } ?: normalizedPlans.first()
        val originalNormalizedPlans = plans.distinctBy { it.id }.sortedBy { it.id }
        val shouldPersist = plans.isEmpty() ||
            lastPlanId != selectedPlan.id ||
            normalizedPlans != originalNormalizedPlans

        return ResolvedPlans(
            plans = normalizedPlans,
            selectedPlan = selectedPlan,
            shouldPersist = shouldPersist,
        )
    }

    private fun resetTrainingState(
        state: WorkoutUiState,
        statusText: String,
        detailText: String,
        stage: WorkoutStage,
    ): WorkoutUiState {
        return state.copy(
            parsedTasks = emptyList(),
            activeTaskIndex = 0,
            stage = stage,
            statusText = statusText,
            detailText = detailText,
            prepRemainingSeconds = null,
            workRemainingSeconds = null,
            restRemainingSeconds = null,
            isTrainingActive = false,
            isWorkPaused = false,
            isRestPaused = false,
        )
    }

    private fun prepDetail(task: WorkoutTask): String {
        return "${task.name}  ${task.setInfo}"
    }

    private fun readyDetail(task: WorkoutTask): String {
        return when (val target = task.target) {
            is WorkoutTarget.Time -> "${task.setInfo}  目标: ${target.seconds} 秒"
            is WorkoutTarget.Reps -> "${task.setInfo}  目标: ${target.text}"
        }
    }

    private fun emitSound(event: WorkoutSoundEvent) {
        if (_uiState.value.isSoundEnabled) {
            _soundEvents.tryEmit(event)
        }
    }

    override fun onCleared() {
        stopCountdown()
        super.onCleared()
    }

    private data class ResolvedPlans(
        val plans: List<SavedPlan>,
        val selectedPlan: SavedPlan,
        val shouldPersist: Boolean,
    )

    private fun nextPlanId(plans: List<SavedPlan>): String {
        var suffix = 1
        while (plans.any { it.id == "plan$suffix" }) {
            suffix += 1
        }
        return "plan$suffix"
    }
}
