import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    id("org.jetbrains.kotlin.jvm")
    `java-library`
}

java {
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
}

kotlin {
    compilerOptions {
        jvmTarget.set(JvmTarget.JVM_17)
    }
}

dependencies {
    // 한글 문서(.hwp / .hwpx) 읽기·쓰기 라이브러리 (Apache-2.0)
    api("kr.dogfoot:hwplib:1.1.11")
    api("kr.dogfoot:hwpxlib:1.0.9")

    testImplementation("junit:junit:4.13.2")
}

tasks.test {
    // 저장 결과를 사람이 직접 열어 볼 수 있도록 남긴다.
    systemProperty("hwp.testOutput", layout.buildDirectory.dir("test-output").get().asFile.absolutePath)
    System.getProperty("hwp.bulkDir")?.let { systemProperty("hwp.bulkDir", it) }
    maxHeapSize = "2g"
}
