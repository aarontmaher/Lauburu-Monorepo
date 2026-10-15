# Production Proguard Rules for Sovereign Lauburu
-keep class com.lauburu.sovereign.** { *; }
-keep class androidx.webkit.** { *; }
-keepclassmembers class * {
    native <methods>;
}
-dontwarn androidx.webkit.**
-keepattributes *Annotation*
-keepattributes Signature
