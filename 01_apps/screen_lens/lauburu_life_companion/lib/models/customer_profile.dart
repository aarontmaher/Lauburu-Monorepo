import 'dart:convert';

/// Membership tiers available for Shopify customers.
enum CustomerTier {
  free,
  pro,
  elite;

  String get displayName {
    switch (this) {
      case CustomerTier.elite:
        return '👑 ELITE';
      case CustomerTier.pro:
        return '⚡ PRO';
      case CustomerTier.free:
        return '🌱 FREE';
    }
  }

  String get badgeText {
    switch (this) {
      case CustomerTier.elite:
        return 'ELITE';
      case CustomerTier.pro:
        return 'PRO';
      case CustomerTier.free:
        return 'FREE';
    }
  }

  static CustomerTier fromString(String? value) {
    if (value == null) return CustomerTier.free;
    final lower = value.toLowerCase().trim();
    if (lower.contains('elite')) return CustomerTier.elite;
    if (lower.contains('pro')) return CustomerTier.pro;
    return CustomerTier.free;
  }

  static CustomerTier fromTags(List<String> tags) {
    final lowerTags = tags.map((t) => t.toLowerCase().trim()).toList();
    if (lowerTags.any((t) => t == 'lauburu_elite' || t == 'elite' || t == 'tier_elite')) {
      return CustomerTier.elite;
    }
    if (lowerTags.any((t) => t == 'lauburu_pro' || t == 'pro' || t == 'tier_pro')) {
      return CustomerTier.pro;
    }
    return CustomerTier.free;
  }
}

/// Represents a customer's profile retrieved from Shopify Storefront API.
class CustomerProfile {
  final String id;
  final String email;
  final String? firstName;
  final String? lastName;
  final List<String> tags;
  final CustomerTier tier;
  final DateTime? createdAt;
  final int orderCount;

  CustomerProfile({
    required this.id,
    required this.email,
    this.firstName,
    this.lastName,
    required this.tags,
    required this.tier,
    this.createdAt,
    this.orderCount = 0,
  });

  String get fullName {
    final first = firstName ?? '';
    final last = lastName ?? '';
    final combined = '$first $last'.trim();
    return combined.isNotEmpty ? combined : email;
  }

  CustomerProfile copyWith({
    String? id,
    String? email,
    String? firstName,
    String? lastName,
    List<String>? tags,
    CustomerTier? tier,
    DateTime? createdAt,
    int? orderCount,
  }) {
    return CustomerProfile(
      id: id ?? this.id,
      email: email ?? this.email,
      firstName: firstName ?? this.firstName,
      lastName: lastName ?? this.lastName,
      tags: tags ?? List<String>.from(this.tags),
      tier: tier ?? this.tier,
      createdAt: createdAt ?? this.createdAt,
      orderCount: orderCount ?? this.orderCount,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'email': email,
      'firstName': firstName,
      'lastName': lastName,
      'tags': tags,
      'tier': tier.name,
      'createdAt': createdAt?.toIso8601String(),
      'orderCount': orderCount,
    };
  }

  factory CustomerProfile.fromJson(Map<String, dynamic> json) {
    final rawTags = json['tags'];
    final List<String> parsedTags;
    if (rawTags is List) {
      parsedTags = rawTags.map((e) => e.toString()).toList();
    } else {
      parsedTags = [];
    }

    final rawTier = json['tier'] as String?;
    final tier = rawTier != null
        ? CustomerTier.fromString(rawTier)
        : CustomerTier.fromTags(parsedTags);

    DateTime? parsedCreatedAt;
    if (json['createdAt'] != null) {
      parsedCreatedAt = DateTime.tryParse(json['createdAt'].toString());
    }

    return CustomerProfile(
      id: json['id'] as String? ?? '',
      email: json['email'] as String? ?? '',
      firstName: json['firstName'] as String?,
      lastName: json['lastName'] as String?,
      tags: parsedTags,
      tier: tier,
      createdAt: parsedCreatedAt,
      orderCount: (json['orderCount'] as num?)?.toInt() ?? 0,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is CustomerProfile &&
          runtimeType == other.runtimeType &&
          id == other.id &&
          email == other.email &&
          tier == other.tier;

  @override
  int get hashCode => id.hashCode ^ email.hashCode ^ tier.hashCode;

  @override
  String toString() =>
      'CustomerProfile(id: $id, email: $email, name: $fullName, tier: ${tier.name})';
}

/// Authentication session containing access token, expiration, and user profile.
class AuthSession {
  final String accessToken;
  final DateTime expiresAt;
  final CustomerProfile profile;
  final DateTime lastSyncedAt;

  AuthSession({
    required this.accessToken,
    required this.expiresAt,
    required this.profile,
    DateTime? lastSyncedAt,
  }) : lastSyncedAt = lastSyncedAt ?? DateTime.now();

  bool get isExpired => DateTime.now().isAfter(expiresAt);

  CustomerProfile get customerProfile => profile;

  AuthSession copyWith({
    String? accessToken,
    DateTime? expiresAt,
    CustomerProfile? profile,
    DateTime? lastSyncedAt,
  }) {
    return AuthSession(
      accessToken: accessToken ?? this.accessToken,
      expiresAt: expiresAt ?? this.expiresAt,
      profile: profile ?? this.profile,
      lastSyncedAt: lastSyncedAt ?? this.lastSyncedAt,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'accessToken': accessToken,
      'expiresAt': expiresAt.toIso8601String(),
      'profile': profile.toJson(),
      'lastSyncedAt': lastSyncedAt.toIso8601String(),
    };
  }

  factory AuthSession.fromJson(Map<String, dynamic> json) {
    return AuthSession(
      accessToken: json['accessToken'] as String? ?? '',
      expiresAt: DateTime.parse(
        json['expiresAt'] as String? ?? DateTime.now().add(const Duration(days: 30)).toIso8601String(),
      ),
      profile: CustomerProfile.fromJson(
        json['profile'] is Map<String, dynamic>
            ? json['profile'] as Map<String, dynamic>
            : (json['customerProfile'] is Map<String, dynamic>
                ? json['customerProfile'] as Map<String, dynamic>
                : <String, dynamic>{}),
      ),
      lastSyncedAt: json['lastSyncedAt'] != null
          ? DateTime.parse(json['lastSyncedAt'] as String)
          : DateTime.now(),
    );
  }

  String toJsonString() => jsonEncode(toJson());

  factory AuthSession.fromJsonString(String jsonString) {
    final Map<String, dynamic> map = jsonDecode(jsonString) as Map<String, dynamic>;
    return AuthSession.fromJson(map);
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is AuthSession &&
          runtimeType == other.runtimeType &&
          accessToken == other.accessToken;

  @override
  int get hashCode => accessToken.hashCode;

  @override
  String toString() =>
      'AuthSession(token: ${accessToken.length > 8 ? accessToken.substring(0, 8) : accessToken}..., expires: $expiresAt, user: ${profile.email})';
}
