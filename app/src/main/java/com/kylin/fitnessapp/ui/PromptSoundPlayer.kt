package com.kylin.fitnessapp.ui

import android.content.Context
import android.media.AudioAttributes
import android.media.SoundPool
import com.kylin.fitnessapp.workout.WorkoutSoundEvent

class PromptSoundPlayer(context: Context) {
    private val soundPool: SoundPool
    private var dingSoundId: Int = 0
    private var isLoaded: Boolean = false

    init {
        val attributes = AudioAttributes.Builder()
            .setUsage(AudioAttributes.USAGE_ASSISTANCE_SONIFICATION)
            .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
            .build()

        soundPool = SoundPool.Builder()
            .setMaxStreams(2)
            .setAudioAttributes(attributes)
            .build()

        soundPool.setOnLoadCompleteListener { _, sampleId, status ->
            if (status == 0 && sampleId == dingSoundId) {
                isLoaded = true
            }
        }

        dingSoundId = runCatching {
            context.applicationContext.assets.openFd("ding.wav").use { descriptor ->
                soundPool.load(descriptor, 1)
            }
        }.getOrDefault(0)
    }

    fun play(event: WorkoutSoundEvent) {
        if (!isLoaded || dingSoundId == 0) {
            return
        }

        val (volume, repeat, rate) = when (event) {
            WorkoutSoundEvent.CountdownTick -> Triple(0.7f, 0, 1.0f)
            WorkoutSoundEvent.StageTransition -> Triple(1.0f, 0, 1.08f)
            WorkoutSoundEvent.SessionComplete -> Triple(1.0f, 1, 0.95f)
        }

        soundPool.play(dingSoundId, volume, volume, 1, repeat, rate)
    }

    fun release() {
        soundPool.release()
    }
}
