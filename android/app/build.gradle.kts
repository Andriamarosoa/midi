plugins {
    id("com.android.application")
}

android {
    namespace = "com.guitarmidi.ai"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.guitarmidi.ai"
        minSdk = 23
        targetSdk = 36
        versionCode = 2
        versionName = "2.2.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
    }
    androidResources {
        noCompress += listOf("tflite")
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    implementation("org.tensorflow:tensorflow-lite:2.16.1")
    testImplementation("junit:junit:4.13.2")
}
