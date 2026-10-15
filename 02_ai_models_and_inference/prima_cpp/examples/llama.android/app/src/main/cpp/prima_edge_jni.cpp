// ============================================================================
// prima_edge_jni.cpp — Android JNI Native Interface for prima.cpp Edge Client
// Subsystem: 02_ai_models_and_inference / prima_cpp / examples / llama.android
// Lauburu Mesh Ecosystem — 2026
// ============================================================================

#include <jni.h>
#include <string>
#include "../../../../../include/prima_edge_client.hpp"

extern "C" {

JNIEXPORT jlong JNICALL
Java_com_lauburu_prima_PrimaEdgeService_nativeInitClient(
    JNIEnv* env,
    jobject /* this */,
    jstring model_path_j,
    jstring mesh_url_j,
    jfloat timeout_ms
) {
    const char* model_path = env->GetStringUTFChars(model_path_j, nullptr);
    const char* mesh_url = env->GetStringUTFChars(mesh_url_j, nullptr);

    lauburu::prima::EdgeClientConfig cfg;
    if (model_path) cfg.model_path = model_path;
    if (mesh_url) cfg.mesh_daemon_url = mesh_url;
    if (timeout_ms > 0.0f) cfg.handshake_timeout_ms = timeout_ms;

    auto* client = new lauburu::prima::PrimaEdgeClient(cfg);

    env->ReleaseStringUTFChars(model_path_j, model_path);
    env->ReleaseStringUTFChars(mesh_url_j, mesh_url);

    return reinterpret_cast<jlong>(client);
}

JNIEXPORT void JNICALL
Java_com_lauburu_prima_PrimaEdgeService_nativeDestroyClient(
    JNIEnv* /* env */,
    jobject /* this */,
    jlong client_ptr
) {
    auto* client = reinterpret_cast<lauburu::prima::PrimaEdgeClient*>(client_ptr);
    delete client;
}

JNIEXPORT jboolean JNICALL
Java_com_lauburu_prima_PrimaEdgeService_nativeCheckEnvelope(
    JNIEnv* env,
    jobject /* this */,
    jlong client_ptr,
    jfloatArray margin_out
) {
    auto* client = reinterpret_cast<lauburu::prima::PrimaEdgeClient*>(client_ptr);
    if (!client) return JNI_FALSE;

    float margin_mb = 0.0f;
    bool compliant = client->verify_customer_device_envelope(margin_mb);

    if (margin_out != nullptr) {
        env->SetFloatArrayRegion(margin_out, 0, 1, &margin_mb);
    }
    return compliant ? JNI_TRUE : JNI_FALSE;
}

JNIEXPORT jstring JNICALL
Java_com_lauburu_prima_PrimaEdgeService_nativeGenerateChat(
    JNIEnv* env,
    jobject /* this */,
    jlong client_ptr,
    jstring prompt_j,
    jboolean force_local
) {
    auto* client = reinterpret_cast<lauburu::prima::PrimaEdgeClient*>(client_ptr);
    if (!client) return env->NewStringUTF("Error: Client uninitialized");

    const char* prompt = env->GetStringUTFChars(prompt_j, nullptr);
    auto res = client->generate_chat(prompt, "", force_local == JNI_TRUE);
    env->ReleaseStringUTFChars(prompt_j, prompt);

    return env->NewStringUTF(res.response_text.c_str());
}

} // extern "C"
