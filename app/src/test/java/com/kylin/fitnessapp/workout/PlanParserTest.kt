package com.kylin.fitnessapp.workout

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class PlanParserTest {
    @Test
    fun inferPlanNameUsesMarkdownTitleFirst() {
        val text = """
            # 上肢训练
            俯卧撑 | 4组 | 力竭 | 休90
        """.trimIndent()

        assertEquals("上肢训练", PlanParser.inferPlanName(text))
    }

    @Test
    fun parseExpandsSetsAndRestSeconds() {
        val text = """
            [热身]
            开合跳 | 1分钟
            [训练]
            俯卧撑 | 2组 | 15次 | 休60
        """.trimIndent()

        val tasks = PlanParser.parse(text)

        assertEquals(3, tasks.size)
        assertTrue(tasks[0].target is WorkoutTarget.Time)
        assertEquals(60, (tasks[0].target as WorkoutTarget.Time).seconds)
        assertEquals(60, tasks[1].restSeconds)
        assertEquals("[训练] 第 2 组 / 共 2 组", tasks[2].setInfo)
    }
}
