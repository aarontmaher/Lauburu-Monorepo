import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/customer_profile.dart';

/// Contract for persistent authentication session storage.
abstract class SessionStorage {
  Future<void> saveSession(AuthSession session);
  Future<AuthSession?> loadSession();
  Future<void> clearSession();
  Future<bool> hasSession();
}

/// SharedPreferences implementation of persistent session storage.
/// Ensures session state survives app restarts across all platforms.
class PreferencesSessionStorage implements SessionStorage {
  static const String keyAccessToken = 'lauburu_shopify_access_token';
  static const String keyTokenExpiresAt = 'lauburu_shopify_token_expires_at';
  static const String keyProfileJson = 'lauburu_shopify_customer_profile_json';
  static const String keyFullSession = 'lauburu_shopify_auth_session';
  static const String keyLastSyncedAt = 'lauburu_shopify_last_synced_at';

  final SharedPreferences? _customPrefs;

  PreferencesSessionStorage({SharedPreferences? prefs}) : _customPrefs = prefs;

  Future<SharedPreferences?> _getPrefs() async {
    if (_customPrefs != null) return _customPrefs;
    try {
      return await SharedPreferences.getInstance();
    } catch (_) {
      // SharedPreferences channel unavailable (e.g. macOS standalone binary)
      return null;
    }
  }

  @override
  Future<void> saveSession(AuthSession session) async {
    final prefs = await _getPrefs();
    if (prefs == null) return;
    await prefs.setString(keyAccessToken, session.accessToken);
    await prefs.setString(keyTokenExpiresAt, session.expiresAt.toIso8601String());
    await prefs.setString(keyProfileJson, jsonEncode(session.profile.toJson()));
    await prefs.setString(keyLastSyncedAt, session.lastSyncedAt.toIso8601String());
    await prefs.setString(keyFullSession, session.toJsonString());
  }

  @override
  Future<AuthSession?> loadSession() async {
    final prefs = await _getPrefs();
    if (prefs == null) return null;

    // Priority 1: Full serialized session string
    final fullSessionJson = prefs.getString(keyFullSession);
    if (fullSessionJson != null && fullSessionJson.isNotEmpty) {
      try {
        return AuthSession.fromJsonString(fullSessionJson);
      } catch (_) {
        // Fall back to discrete keys if deserialization fails
      }
    }

    // Priority 2: Reconstruct from discrete keys
    final token = prefs.getString(keyAccessToken);
    if (token == null || token.isEmpty) {
      return null;
    }

    final expiresStr = prefs.getString(keyTokenExpiresAt);
    final expiresAt = expiresStr != null
        ? DateTime.tryParse(expiresStr) ?? DateTime.now().add(const Duration(days: 30))
        : DateTime.now().add(const Duration(days: 30));

    final profileStr = prefs.getString(keyProfileJson);
    CustomerProfile profile;
    if (profileStr != null && profileStr.isNotEmpty) {
      try {
        final profileMap = jsonDecode(profileStr) as Map<String, dynamic>;
        profile = CustomerProfile.fromJson(profileMap);
      } catch (_) {
        profile = CustomerProfile(
          id: '',
          email: '',
          tags: [],
          tier: CustomerTier.free,
        );
      }
    } else {
      profile = CustomerProfile(
        id: '',
        email: '',
        tags: [],
        tier: CustomerTier.free,
      );
    }

    final syncedStr = prefs.getString(keyLastSyncedAt);
    final lastSyncedAt = syncedStr != null
        ? DateTime.tryParse(syncedStr) ?? DateTime.now()
        : DateTime.now();

    return AuthSession(
      accessToken: token,
      expiresAt: expiresAt,
      profile: profile,
      lastSyncedAt: lastSyncedAt,
    );
  }

  @override
  Future<void> clearSession() async {
    final prefs = await _getPrefs();
    if (prefs == null) return;
    await prefs.remove(keyAccessToken);
    await prefs.remove(keyTokenExpiresAt);
    await prefs.remove(keyProfileJson);
    await prefs.remove(keyFullSession);
    await prefs.remove(keyLastSyncedAt);
  }

  @override
  Future<bool> hasSession() async {
    final prefs = await _getPrefs();
    if (prefs == null) return false;
    final token = prefs.getString(keyAccessToken);
    return token != null && token.isNotEmpty;
  }
}
