package com.kylin.fitnessapp

import android.os.Bundle
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import com.kylin.fitnessapp.ui.FitnessApp
import com.kylin.fitnessapp.workout.WorkoutViewModel

class MainActivity : ComponentActivity() {
    private val workoutViewModel: WorkoutViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)

        setContent {
            FitnessApp(workoutViewModel = workoutViewModel)
        }
    }
}
