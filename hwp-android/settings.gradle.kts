pluginManagement {
    repositories {
        gradlePluginPortal()
        mavenCentral()
    }
}

dependencyResolutionManagement {
    repositories {
        google {
            content {
                includeGroupByRegex("com\\.android.*")
                includeGroupByRegex("com\\.google.*")
                includeGroupByRegex("androidx.*")
            }
        }
        mavenCentral()
    }
}

rootProject.name = "hwp-android"

include(":core")

// -PcoreOnly 로 실행하면 안드로이드 SDK 없이 문서 처리 부분만 빌드·시험한다.
if (!providers.gradleProperty("coreOnly").isPresent) {
    include(":app")
}
