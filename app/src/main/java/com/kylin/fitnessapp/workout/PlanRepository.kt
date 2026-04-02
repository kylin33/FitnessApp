package com.kylin.fitnessapp.workout

import android.content.Context
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.first
import org.json.JSONArray
import org.json.JSONObject

private val Context.dataStore by preferencesDataStore(name = "fitness_plans")

class PlanRepository(private val context: Context) {
    suspend fun loadSnapshot(): PlanSnapshot {
        val preferences = context.dataStore.data.first()
        return PlanSnapshot(
            plans = decodePlans(preferences[PLANS_KEY]),
            lastPlanId = preferences[LAST_PLAN_ID_KEY],
            isSoundEnabled = preferences[SOUND_ENABLED_KEY] ?: true,
        )
    }

    suspend fun saveSnapshot(plans: List<SavedPlan>, lastPlanId: String?) {
        context.dataStore.edit { preferences ->
            preferences[PLANS_KEY] = encodePlans(plans)
            if (lastPlanId.isNullOrBlank()) {
                preferences.remove(LAST_PLAN_ID_KEY)
            } else {
                preferences[LAST_PLAN_ID_KEY] = lastPlanId
            }
        }
    }

    suspend fun saveSoundEnabled(enabled: Boolean) {
        context.dataStore.edit { preferences ->
            preferences[SOUND_ENABLED_KEY] = enabled
        }
    }

    private fun decodePlans(raw: String?): List<SavedPlan> {
        if (raw.isNullOrBlank()) {
            return emptyList()
        }

        return buildList {
            val jsonArray = JSONArray(raw)
            for (index in 0 until jsonArray.length()) {
                val item = jsonArray.optJSONObject(index) ?: continue
                val id = item.optString("id").trim()
                val name = item.optString("name").trim()
                val text = item.optString("text")
                if (id.isEmpty()) {
                    continue
                }
                add(
                    SavedPlan(
                        id = id,
                        name = name.ifEmpty { PlanParser.inferPlanName(text) },
                        text = text,
                    )
                )
            }
        }
    }

    private fun encodePlans(plans: List<SavedPlan>): String {
        val jsonArray = JSONArray()
        plans.forEach { plan ->
            jsonArray.put(
                JSONObject()
                    .put("id", plan.id)
                    .put("name", plan.name)
                    .put("text", plan.text)
            )
        }
        return jsonArray.toString()
    }

    data class PlanSnapshot(
        val plans: List<SavedPlan>,
        val lastPlanId: String?,
        val isSoundEnabled: Boolean,
    )

    private companion object {
        val PLANS_KEY = stringPreferencesKey("plans_v1")
        val LAST_PLAN_ID_KEY = stringPreferencesKey("last_plan_id_v1")
        val SOUND_ENABLED_KEY = booleanPreferencesKey("sound_enabled_v1")
    }
}
