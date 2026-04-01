package com.kylin.fitnessapp.workout

object PlanParser {
    fun parse(text: String): List<WorkoutTask> {
        val plan = mutableListOf<WorkoutTask>()
        val lines = text.trim().lines()
        var currentPhase = "训练"

        for (line in lines) {
            val raw = line.trim()
            if (raw.isEmpty()) {
                continue
            }
            if (raw.startsWith("#")) {
                continue
            }
            if (raw.startsWith("[") && raw.endsWith("]")) {
                currentPhase = raw.removePrefix("[").removeSuffix("]").trim().ifEmpty { "训练" }
                continue
            }
            if (!raw.contains("|")) {
                continue
            }

            val parts = raw.split("|").map { it.trim() }
            if (parts.size == 2) {
                val actionName = parts[0]
                val targetRaw = parts[1]
                val seconds = parseDurationSeconds(targetRaw)
                val target = if (seconds > 0) {
                    WorkoutTarget.Time(seconds)
                } else {
                    WorkoutTarget.Reps(targetRaw)
                }
                plan += WorkoutTask(
                    name = actionName,
                    setInfo = "[$currentPhase] 第 1 组 / 共 1 组",
                    target = target,
                    restSeconds = 0,
                )
                continue
            }

            if (parts.size >= 4) {
                val actionName = parts[0]
                val sets = extractInt(parts[1])
                if (sets <= 0) {
                    continue
                }
                val targetRaw = parts[2]
                val restSeconds = parseDurationSeconds(parts[3])

                repeat(sets) { index ->
                    plan += WorkoutTask(
                        name = actionName,
                        setInfo = "[$currentPhase] 第 ${index + 1} 组 / 共 $sets 组",
                        target = parseTarget(targetRaw),
                        restSeconds = restSeconds,
                    )
                }
            }
        }

        return plan
    }

    fun inferPlanName(text: String): String {
        val title = extractPlanTitle(text)
        if (title.isNotEmpty()) {
            return title
        }
        val firstLine = text.trim().lines().firstOrNull()?.trim().orEmpty()
        if (firstLine.isEmpty()) {
            return "训练计划"
        }
        return firstLine.substringBefore("|").trim().ifEmpty { "训练计划" }
    }

    private fun extractPlanTitle(text: String): String {
        return text.lines()
            .firstOrNull { it.trim().startsWith("#") && it.trim().removePrefix("#").trim().isNotEmpty() }
            ?.trim()
            ?.removePrefix("#")
            ?.trim()
            .orEmpty()
    }

    private fun parseTarget(raw: String): WorkoutTarget {
        val normalized = raw.trim().lowercase().replace(" ", "")
        return if ("秒" in normalized || "分" in normalized || normalized.endsWith("s")) {
            WorkoutTarget.Time(parseDurationSeconds(raw))
        } else {
            WorkoutTarget.Reps(raw)
        }
    }

    private fun parseDurationSeconds(raw: String): Int {
        val text = raw.trim().lowercase().replace(" ", "")
        if (text.isEmpty()) {
            return 0
        }
        if (text in setOf("无", "none", "n/a", "na", "-")) {
            return 0
        }
        if ("无" in text && text.none { it.isDigit() }) {
            return 0
        }

        if ("分" in text) {
            val sections = text.split("分", limit = 2)
            val minutes = extractInt(sections[0])
            val seconds = if (sections.size > 1 && ("秒" in sections[1] || sections[1].endsWith("s"))) {
                extractInt(sections[1])
            } else {
                0
            }
            return minutes * 60 + seconds
        }

        if ("秒" in text || text.endsWith("s")) {
            return extractInt(text)
        }

        return extractInt(text)
    }

    private fun extractInt(raw: String, default: Int = 0): Int {
        val digits = raw.filter { it.isDigit() }
        return digits.toIntOrNull() ?: default
    }
}
