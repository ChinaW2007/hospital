import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:his_mobile/providers/auth_provider.dart';
import 'package:his_mobile/core/network/api_client.dart';
import 'package:his_mobile/core/theme/glass_card.dart';
import 'package:his_mobile/core/widgets/animated_scale_button.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _formKey = GlobalKey<FormState>();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _obscurePassword = true;

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  // 弹出服务器设置框，用于 HTTPS 调试或本地局域网切换
  void _showServerSettings() {
    final controller = TextEditingController(text: ApiClient().baseUrl);
    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('服务器地址设置'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('请输入包含 http/https 的 HIS 后端 API 地址：', style: TextStyle(fontSize: 13, color: Colors.grey)),
              const SizedBox(height: 12),
              TextField(
                controller: controller,
                decoration: const InputDecoration(
                  labelText: 'API 服务器地址',
                  hintText: 'http://192.168.51.133:3001',
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('取消'),
            ),
            ElevatedButton(
              onPressed: () {
                final input = controller.text.trim();
                if (input.isNotEmpty) {
                  context.read<AuthProvider>().updateServerAddress(input);
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('API 服务器已切换至: $input')),
                  );
                }
                Navigator.pop(context);
              },
              child: const Text('保存'),
            ),
          ],
        );
      },
    );
  }

  Future<void> _handleLogin() async {
    if (!_formKey.currentState!.validate()) return;
    
    final auth = context.read<AuthProvider>();
    final success = await auth.login(
      _usernameController.text.trim(),
      _passwordController.text,
    );

    if (success && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('登录成功，欢迎使用智能HIS药房！')),
      );
    } else if (mounted) {
      showDialog(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('登录失败'),
          content: Text(auth.errorMsg ?? '无法连接到服务器'),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('好的'),
            ),
          ],
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final isLoading = context.watch<AuthProvider>().isLoading;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: isDark 
                ? [const Color(0xFF090C15), const Color(0xFF0B1B2A), const Color(0xFF141221)]
                : [const Color(0xFFEAF6FF), const Color(0xFFEDFDF8), const Color(0xFFFFF2F7)],
          ),
        ),
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 16.0),
              child: Form(
                key: _formKey,
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // 顶部设置按钮
                    Align(
                      alignment: Alignment.topRight,
                      child: IconButton(
                        icon: Icon(Icons.settings, color: isDark ? Colors.white70 : Colors.black54),
                        onPressed: _showServerSettings,
                      ),
                    ),
                    const SizedBox(height: 20),
                    
                    // Logo 和应用名称
                    Hero(
                      tag: 'app_logo',
                      child: Image.asset(
                        'assets/app_icon.png',
                        height: 110,
                        fit: BoxFit.contain,
                      ),
                    ),
                    const SizedBox(height: 24),
                    Text(
                      '智能HIS药房系统',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 28,
                        fontWeight: FontWeight.w800,
                        color: isDark ? Colors.white : const Color(0xFF00796B),
                        letterSpacing: 1.2,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      '医院药房自动化配送与复核平台',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 14,
                        color: isDark ? Colors.white60 : Colors.black54,
                      ),
                    ),
                    
                    // 将输入区包裹在宽敞的磨砂玻璃卡片中
                    GlassCard(
                      margin: const EdgeInsets.only(top: 36),
                      padding: const EdgeInsets.all(24.0),
                      borderRadius: 24,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          const Text(
                            '账户安全登录',
                            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: Colors.grey),
                          ),
                          const SizedBox(height: 20),

                          // 用户名输入
                          TextFormField(
                            controller: _usernameController,
                            keyboardType: TextInputType.text,
                            decoration: const InputDecoration(
                              prefixIcon: Icon(Icons.person_outline),
                              labelText: '用户名',
                              hintText: '请输入账号 (如 doctor1)',
                            ),
                            validator: (value) {
                              if (value == null || value.trim().isEmpty) {
                                  return '请输入您的用户名';
                              }
                              return null;
                            },
                          ),
                          const SizedBox(height: 18),

                          // 密码输入
                          TextFormField(
                            controller: _passwordController,
                            obscureText: _obscurePassword,
                            decoration: InputDecoration(
                              prefixIcon: const Icon(Icons.lock_outline),
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
                              labelText: '密码',
                              hintText: '请输入登录密码',
                            ),
                            validator: (value) {
                              if (value == null || value.isEmpty) {
                                return '请输入您的密码';
                              }
                              return null;
                            },
                          ),
                          const SizedBox(height: 28),

                          // 苹果风格弹性登录按钮
                          isLoading
                              ? const Center(child: CircularProgressIndicator())
                              : AnimatedScaleButton(
                                  onTap: _handleLogin,
                                  child: Container(
                                    height: 54,
                                    decoration: BoxDecoration(
                                      color: const Color(0xFF00796B),
                                      borderRadius: BorderRadius.circular(20),
                                      boxShadow: [
                                        BoxShadow(
                                          color: const Color(0xFF00796B).withValues(alpha: 0.25),
                                          blurRadius: 12,
                                          offset: const Offset(0, 4),
                                        ),
                                      ],
                                    ),
                                    alignment: Alignment.center,
                                    child: const Text(
                                      '安全登录',
                                      style: TextStyle(
                                        color: Colors.white,
                                        fontSize: 16,
                                        fontWeight: FontWeight.w800,
                                        letterSpacing: 1.0,
                                      ),
                                    ),
                                  ),
                                ),
                          const SizedBox(height: 20),
                          
                          // 系统提示语
                          Text(
                            '登录代表您已阅读并同意 HIS 安全保密协议',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontSize: 11,
                              color: isDark ? Colors.white30 : Colors.black38,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
