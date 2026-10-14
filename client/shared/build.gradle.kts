import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    alias(libs.plugins.kotlinMultiplatform)
    alias(libs.plugins.androidMultiplatformLibrary)
    alias(libs.plugins.composeMultiplatform)
    alias(libs.plugins.composeCompiler)
    alias(libs.plugins.kotlinSerialization)
}

kotlin {
    jvm()

    androidLibrary {
        namespace = "org.example.client.shared"
        compileSdk = libs.versions.android.compileSdk.get().toInt()
        minSdk = libs.versions.android.minSdk.get().toInt()

        compilerOptions {
            jvmTarget = JvmTarget.JVM_11
        }
        androidResources {
            enable = true
        }
        withHostTest {
            isIncludeAndroidResources = true
        }
    }

    sourceSets {
        androidMain.dependencies {
            implementation(libs.compose.uiToolingPreview)
            implementation(libs.kotlinx.coroutine.android)
        }
        jvmMain.dependencies {
            implementation(libs.kotlinx.coroutinesSwing)
        }
        commonMain.dependencies {
            implementation(libs.compose.runtime)
            implementation(libs.compose.foundation)
            implementation(libs.compose.material3)
            implementation(libs.compose.materialIconsCore)
            implementation(libs.compose.ui)
            implementation(libs.compose.components.resources)
            implementation(libs.compose.uiToolingPreview)
            implementation(libs.androidx.lifecycle.viewmodelCompose)
            implementation(libs.androidx.lifecycle.runtimeCompose)
            implementation(libs.androidx.navigation.compose)
            implementation(libs.kotlinx.coroutine.core)
            implementation(libs.kotlinx.datetime)
            implementation(libs.ktor.client.core)
            implementation(libs.ktor.client.cio)
            implementation(libs.ktor.client.content.negotiation)
            implementation(libs.ktor.serialization.kotlinx.json)
        }
        commonTest.dependencies {
            implementation(libs.kotlin.test)
        }
    }
}

dependencies {
    androidRuntimeClasspath(libs.compose.uiTooling)
}

data class BuildConfigField(val type: String, val name: String, val value: String)

val generateAndroidBuildConfig by tasks.registering {
    val outputDir = layout.buildDirectory.dir("generated/buildconfig/androidMain/org/example/client")
    outputs.dir(outputDir)
    doLast {
        outputDir.get().asFile.mkdirs()
        outputDir.get().file("BuildConfig.kt").asFile.writeText(
            """
            |package org.example.client
            |
            |internal object BuildConfig {
            |    const val BASE_URL: String = "http://10.0.2.2:8000"
            |}
            """.trimMargin()
        )
    }
}

val generateJvmBuildConfig by tasks.registering {
    val outputDir = layout.buildDirectory.dir("generated/buildconfig/jvmMain/org/example/client")
    outputs.dir(outputDir)
    doLast {
        outputDir.get().asFile.mkdirs()
        outputDir.get().file("BuildConfig.kt").asFile.writeText(
            """
            |package org.example.client
            |
            |internal object BuildConfig {
            |    const val BASE_URL: String = "http://localhost:8000"
            |}
            """.trimMargin()
        )
    }
}

kotlin {
    sourceSets {
        val androidMain by getting {
            kotlin.srcDir(layout.buildDirectory.dir("generated/buildconfig/androidMain"))
        }
        val jvmMain by getting {
            kotlin.srcDir(layout.buildDirectory.dir("generated/buildconfig/jvmMain"))
        }
    }
}

tasks.configureEach {
    when {
        name == "compileKotlinAndroid" -> dependsOn(generateAndroidBuildConfig)
        name == "compileKotlinJvm" -> dependsOn(generateJvmBuildConfig)
    }
}
