buildscript {
    val coreOnly = gradle.startParameter.projectProperties.containsKey("coreOnly")
    repositories {
        google {
            content {
                includeGroupByRegex("com\\.android.*")
                includeGroupByRegex("com\\.google.*")
                includeGroupByRegex("androidx.*")
            }
        }
        mavenCentral()
        gradlePluginPortal()
    }
    dependencies {
        classpath("org.jetbrains.kotlin:kotlin-gradle-plugin:2.2.21")
        if (!coreOnly) {
            classpath("com.android.tools.build:gradle:8.7.3")
        }
    }
}
