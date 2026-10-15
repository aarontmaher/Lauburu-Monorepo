import 'package:flutter/material.dart';
import '../models/customer_profile.dart';
import '../services/shopify_auth_service.dart';

/// Modal dialog for customer authentication with email/password
/// or zero-mock developer token bypass.
class ShopifyLoginDialog extends StatefulWidget {
  final ShopifyAuthService authService;

  const ShopifyLoginDialog({
    super.key,
    required this.authService,
  });

  static Future<AuthSession?> show(BuildContext context, ShopifyAuthService authService) {
    return showDialog<AuthSession>(
      context: context,
      barrierDismissible: true,
      builder: (context) => ShopifyLoginDialog(authService: authService),
    );
  }

  @override
  State<ShopifyLoginDialog> createState() => _ShopifyLoginDialogState();
}

class _ShopifyLoginDialogState extends State<ShopifyLoginDialog> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _firstNameController = TextEditingController();
  final _lastNameController = TextEditingController();
  final _devTokenController = TextEditingController();

  bool _isSignUp = false;
  bool _isLoading = false;
  bool _obscurePassword = true;
  String? _errorMessage;
  String? _infoMessage;
  bool _showDevMode = false;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    _firstNameController.dispose();
    _lastNameController.dispose();
    _devTokenController.dispose();
    super.dispose();
  }

  Future<void> _handleLogin() async {
    setState(() {
      _errorMessage = null;
      _infoMessage = null;
    });

    if (!_formKey.currentState!.validate()) {
      return;
    }

    setState(() {
      _isLoading = true;
    });

    try {
      final session = await widget.authService.login(
        _emailController.text.trim(),
        _passwordController.text,
      );

      if (mounted) {
        if (session != null) {
          Navigator.of(context).pop(session);
        } else {
          setState(() {
            _errorMessage = 'Login failed. Please verify credentials.';
          });
        }
      }
    } catch (e) {
      if (mounted) {
        final errText = e.toString().replaceFirst('Exception: ', '');
        setState(() {
          if (errText.contains('Unidentified customer')) {
            _errorMessage = 'Unidentified customer. If this is your first time or your account is not yet activated, tap "Reset / Activate Password" below.';
          } else {
            _errorMessage = errText;
          }
        });
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _handleSignUp() async {
    setState(() {
      _errorMessage = null;
      _infoMessage = null;
    });

    if (!_formKey.currentState!.validate()) {
      return;
    }

    setState(() {
      _isLoading = true;
    });

    try {
      final session = await widget.authService.createAccount(
        email: _emailController.text.trim(),
        password: _passwordController.text,
        firstName: _firstNameController.text.trim(),
        lastName: _lastNameController.text.trim(),
      );

      if (mounted) {
        if (session != null) {
          Navigator.of(context).pop(session);
        } else {
          setState(() {
            _errorMessage = 'Account created, but automatic login failed. Please log in.';
            _isSignUp = false;
          });
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = e.toString().replaceFirst('Exception: ', '');
        });
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _handlePasswordReset() async {
    final email = _emailController.text.trim();
    if (email.isEmpty || !email.contains('@')) {
      setState(() {
        _errorMessage = 'Please enter a valid email address first.';
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _infoMessage = null;
    });

    try {
      await widget.authService.recoverPassword(email);
      if (mounted) {
        setState(() {
          _infoMessage = 'Password reset & activation link sent to $email. Please check your inbox!';
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = e.toString().replaceFirst('Exception: ', '');
        });
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _handleDevLogin([String? token]) async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final devToken = token ??
          (_devTokenController.text.trim().isNotEmpty
              ? _devTokenController.text.trim()
              : 'shpat_dev_aaron_pro');

      final session = await widget.authService.loginWithDevToken(devToken);
      if (mounted) {
        if (session != null) {
          Navigator.of(context).pop(session);
        } else {
          setState(() {
            _errorMessage = 'Dev login failed.';
          });
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = e.toString().replaceFirst('Exception: ', '');
        });
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 420),
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Form(
            key: _formKey,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Row(
                    children: [
                      Icon(_isSignUp ? Icons.person_add_outlined : Icons.lock_outline, color: Colors.blueAccent),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          _isSignUp ? 'Create Shopify Account' : 'Shopify Account Login',
                          style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.close),
                        onPressed: _isLoading ? null : () => Navigator.of(context).pop(),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    _isSignUp
                        ? 'Register your account to unlock member discounts, orders, and cross-device sync.'
                        : 'Log in to sync your profile, membership entitlements, and orders across devices.',
                    style: const TextStyle(color: Colors.grey, fontSize: 13),
                  ),
                  const SizedBox(height: 20),

                  if (_infoMessage != null) ...[
                    Container(
                      key: const Key('info_banner'),
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.green.shade900.withAlpha(50),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Colors.greenAccent),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.check_circle_outline, color: Colors.greenAccent, size: 20),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              _infoMessage!,
                              style: const TextStyle(color: Colors.greenAccent, fontSize: 13),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],

                  if (_errorMessage != null) ...[
                    Container(
                      key: const Key('error_banner'),
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.red.shade900.withAlpha(50),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Colors.redAccent),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.error_outline, color: Colors.redAccent, size: 20),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              _errorMessage!,
                              style: const TextStyle(color: Colors.redAccent, fontSize: 13),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],

                  if (_isSignUp) ...[
                    Row(
                      children: [
                        Expanded(
                          child: TextFormField(
                            key: const Key('first_name_field'),
                            controller: _firstNameController,
                            textInputAction: TextInputAction.next,
                            enabled: !_isLoading,
                            decoration: const InputDecoration(
                              labelText: 'First Name',
                              prefixIcon: Icon(Icons.badge_outlined),
                              border: OutlineInputBorder(),
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: TextFormField(
                            key: const Key('last_name_field'),
                            controller: _lastNameController,
                            textInputAction: TextInputAction.next,
                            enabled: !_isLoading,
                            decoration: const InputDecoration(
                              labelText: 'Last Name',
                              prefixIcon: Icon(Icons.badge_outlined),
                              border: OutlineInputBorder(),
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                  ],

                  // Email Input Field
                  TextFormField(
                    key: const Key('email_field'),
                    controller: _emailController,
                    keyboardType: TextInputType.emailAddress,
                    textInputAction: TextInputAction.next,
                    enabled: !_isLoading,
                    decoration: const InputDecoration(
                      labelText: 'Email Address',
                      hintText: 'athlete@lauburu.ai',
                      prefixIcon: Icon(Icons.email_outlined),
                      border: OutlineInputBorder(),
                    ),
                    validator: (value) {
                      if (value == null || value.trim().isEmpty) {
                        return 'Please enter your email';
                      }
                      if (!value.contains('@')) {
                        return 'Please enter a valid email';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 16),

                  // Password Input Field
                  TextFormField(
                    key: const Key('password_field'),
                    controller: _passwordController,
                    obscureText: _obscurePassword,
                    textInputAction: TextInputAction.done,
                    enabled: !_isLoading,
                    onFieldSubmitted: (_) => _isSignUp ? _handleSignUp() : _handleLogin(),
                    decoration: InputDecoration(
                      labelText: _isSignUp ? 'Choose Password (min 5 characters)' : 'Password',
                      prefixIcon: const Icon(Icons.lock_clock_outlined),
                      border: const OutlineInputBorder(),
                      suffixIcon: IconButton(
                        icon: Icon(
                          _obscurePassword ? Icons.visibility_off : Icons.visibility,
                        ),
                        onPressed: () {
                          setState(() {
                            _obscurePassword = !_obscurePassword;
                          });
                        },
                      ),
                    ),
                    validator: (value) {
                      if (value == null || value.isEmpty) {
                        return 'Please enter your password';
                      }
                      if (value.length < 5) {
                        return 'Password must be at least 5 characters';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 20),

                  // Submit Button
                  ElevatedButton(
                    key: const Key('login_button'),
                    onPressed: _isLoading ? null : (_isSignUp ? _handleSignUp : _handleLogin),
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                    child: _isLoading
                        ? const SizedBox(
                            height: 20,
                            width: 20,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : Text(_isSignUp ? 'Create Account' : 'Log In', style: const TextStyle(fontSize: 16)),
                  ),
                  const SizedBox(height: 8),

                  // Toggle Login / Sign Up
                  TextButton(
                    key: const Key('toggle_auth_mode_button'),
                    onPressed: _isLoading
                        ? null
                        : () {
                            setState(() {
                              _isSignUp = !_isSignUp;
                              _errorMessage = null;
                              _infoMessage = null;
                            });
                          },
                    child: Text(
                      _isSignUp ? 'Already have an account? Log In' : "Don't have an account? Sign Up",
                      style: const TextStyle(fontSize: 13),
                    ),
                  ),

                  // Forgot Password / Activate Link
                  if (!_isSignUp) ...[
                    TextButton(
                      key: const Key('forgot_password_button'),
                      onPressed: _isLoading ? null : _handlePasswordReset,
                      child: const Text(
                        'Forgot password or need activation email?',
                        style: TextStyle(fontSize: 12, decoration: TextDecoration.underline, color: Colors.blueAccent),
                      ),
                    ),
                  ],

                  // Dev mode toggle / dev token quick-login
                  TextButton.icon(
                    key: const Key('toggle_dev_mode_button'),
                    onPressed: () {
                      setState(() {
                        _showDevMode = !_showDevMode;
                      });
                    },
                    icon: Icon(_showDevMode ? Icons.arrow_drop_up : Icons.arrow_drop_down),
                    label: Text(
                      _showDevMode ? 'Hide Developer Options' : 'Developer Quick-Login Options',
                      style: const TextStyle(fontSize: 12),
                    ),
                  ),

                  if (_showDevMode) ...[
                    const Divider(),
                    const SizedBox(height: 8),
                    const Text(
                      'Zero-Mock Local Developer Bypass',
                      style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.blueGrey),
                    ),
                    const SizedBox(height: 8),
                    TextFormField(
                      key: const Key('dev_token_field'),
                      controller: _devTokenController,
                      enabled: !_isLoading,
                      decoration: const InputDecoration(
                        labelText: 'Dev Token (shpat_dev_... / tok_dev_...)',
                        hintText: 'shpat_dev_aaron_pro',
                        isDense: true,
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 8),
                    OutlinedButton.icon(
                      key: const Key('dev_login_button'),
                      onPressed: _isLoading ? null : () => _handleDevLogin(),
                      icon: const Icon(Icons.developer_mode, size: 18),
                      label: const Text('Quick Dev Login (Pro Tier)'),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
